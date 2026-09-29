"""Tests de `traspasos_internos_tesoreria.repository` — monkeypatch sobre
los puntos de entrada a `WC`, mismo criterio que 023/022/021: no se escribe
contra la base real en tests automatizados."""

from __future__ import annotations

from datetime import date

import pytest

from src.features.tesoreria import estado_resolucion
from src.features.traspasos_internos_tesoreria import repository


def _fake_movimiento(fecha=date(2024, 10, 10), importe=17595.82, descripcion="algo"):
    return {"fecha": fecha, "descripcion": descripcion, "importe": importe}


# --- Foundational: esta_resuelto (T009) ------------------------------------


def test_esta_resuelto_devuelve_traspaso_interno_si_hay_vinculo_activo_y_sin_conciliar(monkeypatch):
    monkeypatch.setattr(
        estado_resolucion.conciliacion_repository, "calcular_estado", lambda medio, idm: {"estado": "sin_conciliar"}
    )
    monkeypatch.setattr(
        estado_resolucion,
        "fetch_one",
        lambda sql, params=(): {"Accion": "Vincular"},
    )

    assert estado_resolucion.esta_resuelto("mercado-libre", 25) == "traspaso_interno"


def test_esta_resuelto_prioriza_conciliado_sobre_traspaso_interno(monkeypatch):
    monkeypatch.setattr(
        estado_resolucion.conciliacion_repository, "calcular_estado", lambda medio, idm: {"estado": "conciliado"}
    )

    def fail_if_called(*a, **k):
        raise AssertionError("no debe consultar el vínculo si ya está resuelto por otra vía")

    monkeypatch.setattr(estado_resolucion, "fetch_one", fail_if_called)

    assert estado_resolucion.esta_resuelto("bna", 1) == "conciliado"


def test_esta_resuelto_sin_conciliar_ni_vinculo_es_sin_conciliar(monkeypatch):
    monkeypatch.setattr(
        estado_resolucion.conciliacion_repository, "calcular_estado", lambda medio, idm: {"estado": "sin_conciliar"}
    )
    monkeypatch.setattr(estado_resolucion, "fetch_one", lambda sql, params=(): None)

    assert estado_resolucion.esta_resuelto("bna", 1) == "sin_conciliar"


# --- US1: vincular / sugerir (T011, T012) -----------------------------------


def test_vincular_inserta_evento_y_vinculo_activo_lo_refleja_para_ambos_lados(monkeypatch):
    monkeypatch.setattr(repository, "_movimiento_referencia", lambda medio, idm: _fake_movimiento())
    monkeypatch.setattr(estado_resolucion, "esta_resuelto", lambda medio, idm: "sin_conciliar")

    statements_capturados = []

    def _fake_transaction(statements):
        statements_capturados.extend(statements)
        return [42]

    monkeypatch.setattr(repository, "execute_write_transaction", _fake_transaction)
    monkeypatch.setattr(repository, "fetch_one", lambda sql, params=(): {"f": "2026-09-29T12:00:00"})

    resultado = repository.vincular("mercado-libre", 25, "galicia", 2151, "sgiamberardini")

    assert resultado["vinculado"] and resultado["idEvento"] == 42
    sql, params = statements_capturados[0]
    assert "INSERT INTO dbo.TraspasosInternosTesoreria" in sql and "'Vincular'" in sql
    assert params == ("mercado-libre", 25, "galicia", 2151, "sgiamberardini")

    # `vinculo_activo` ve el mismo evento reflejado para el lado B también.
    monkeypatch.setattr(
        repository,
        "fetch_one",
        lambda sql, params=(): {
            "IdEvento": 42, "MedioA": "mercado-libre", "IdMovimientoA": 25,
            "MedioB": "galicia", "IdMovimientoB": 2151, "Accion": "Vincular",
            "Usuario": "sgiamberardini", "Fecha": "2026-09-29T12:00:00",
        },
    )
    assert repository.vinculo_activo("galicia", 2151) is not None


def test_vincular_rechaza_movimiento_consigo_mismo():
    with pytest.raises(ValueError, match="consigo mismo"):
        repository.vincular("bna", 1, "bna", 1, "u")


def test_sugerir_candidatas_encuentra_contraparte_por_fecha_e_importe(monkeypatch):
    monkeypatch.setattr(repository, "_movimiento_referencia", lambda medio, idm: _fake_movimiento())

    def _fake_fetch_all(sql, params=()):
        if "[Movimientos Galicia]" in sql:
            return [{"idMovimiento": 2151, "fecha": _fake_movimiento()["fecha"], "descripcion": "Debito Debin", "importe": 17595.82}]
        return []

    monkeypatch.setattr(repository, "fetch_all", _fake_fetch_all)

    candidatas = repository.sugerir_candidatas("mercado-libre", 25)

    assert len(candidatas) == 1
    assert candidatas[0]["medio"] == "galicia" and candidatas[0]["idMovimiento"] == 2151


# --- US2: guarda simétrica (T022-T025a) -------------------------------------


def test_vincular_rechaza_si_medio_a_ya_esta_resuelto(monkeypatch):
    monkeypatch.setattr(repository, "_movimiento_referencia", lambda medio, idm: _fake_movimiento())
    monkeypatch.setattr(estado_resolucion, "esta_resuelto", lambda medio, idm: "conciliado" if medio == "bna" else "sin_conciliar")

    with pytest.raises(ValueError, match="ya está resuelto"):
        repository.vincular("bna", 1, "galicia", 2, "u")


def test_vincular_rechaza_si_medio_b_la_contraparte_ya_esta_resuelto(monkeypatch):
    monkeypatch.setattr(repository, "_movimiento_referencia", lambda medio, idm: _fake_movimiento())
    monkeypatch.setattr(estado_resolucion, "esta_resuelto", lambda medio, idm: "traspaso_interno" if medio == "galicia" else "sin_conciliar")

    with pytest.raises(ValueError, match="la contraparte elegida"):
        repository.vincular("bna", 1, "galicia", 2, "u")


def test_vincular_rechaza_si_ya_tiene_vinculo_activo_con_un_tercero(monkeypatch):
    """FR-008: `esta_resuelto` ya cubre este caso (traspaso_interno activo),
    así que el mensaje de error debe identificar la contraparte actual."""
    monkeypatch.setattr(repository, "_movimiento_referencia", lambda medio, idm: _fake_movimiento())
    monkeypatch.setattr(estado_resolucion, "esta_resuelto", lambda medio, idm: "traspaso_interno" if (medio, idm) == ("bna", 1) else "sin_conciliar")

    with pytest.raises(ValueError, match="ya está resuelto"):
        repository.vincular("bna", 1, "galicia", 999, "u")


def test_deshacer_y_volver_a_vincular_no_queda_bloqueado_por_el_vinculo_viejo(monkeypatch):
    """quickstart.md Escenario 3: tras deshacer, `vinculo_activo` ya no ve la
    fila vieja como activa (la más reciente pasa a ser `Deshacer`)."""
    monkeypatch.setattr(
        repository,
        "fetch_one",
        lambda sql, params=(): {
            "IdEvento": 5, "MedioA": "mercado-libre", "IdMovimientoA": 25,
            "MedioB": "galicia", "IdMovimientoB": 2151, "Accion": "Vincular",
            "Usuario": "u", "Fecha": "2026-09-29T10:00:00",
        },
    )
    statements = []
    monkeypatch.setattr(repository, "execute_write_transaction", lambda s: (statements.extend(s), [6])[1])

    resultado = repository.deshacer("mercado-libre", 25, "u2")
    assert not resultado["vinculado"]
    sql, params = statements[0]
    assert "'Deshacer'" in sql
    assert params == ("mercado-libre", 25, "galicia", 2151, "u2")

    # Tras el Deshacer, la fila de mayor IdEvento para ese par es la nueva.
    monkeypatch.setattr(
        repository,
        "fetch_one",
        lambda sql, params=(): {
            "IdEvento": 6, "MedioA": "mercado-libre", "IdMovimientoA": 25,
            "MedioB": "galicia", "IdMovimientoB": 2151, "Accion": "Deshacer",
            "Usuario": "u2", "Fecha": "2026-09-29T11:00:00",
        },
    )
    assert repository.vinculo_activo("mercado-libre", 25) is None


def test_deshacer_rechaza_si_no_hay_vinculo_activo(monkeypatch):
    monkeypatch.setattr(repository, "fetch_one", lambda sql, params=(): None)
    with pytest.raises(ValueError, match="no tiene ningún vínculo"):
        repository.deshacer("bna", 1, "u")


@pytest.fixture(autouse=True)
def _sin_transacciones_reales_026(monkeypatch):
    # Los tests de negocio simulan escrituras; el contexto común se verifica
    # aparte con conexiones simuladas, no obteniendo locks en producción.
    from contextlib import nullcontext
    from src.db import connection
    monkeypatch.setattr(connection, 'reconciliation_transaction', nullcontext)
