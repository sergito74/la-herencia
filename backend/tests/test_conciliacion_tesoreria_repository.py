"""Tests de `conciliacion_tesoreria.repository` — monkeypatch sobre los
puntos de entrada a `WC` (mismo criterio que 022/021: no se escribe contra
la base real en tests automatizados), salvo el test de esquema al final,
que hace una lectura real de solo-lectura contra `WC` para confirmar que
el `ALTER VIEW` aplicado (T004-T006) expone la forma esperada."""

from __future__ import annotations

import pytest

from src.features.conciliacion_tesoreria import repository


def _fake_movimiento_bna(importe=60500.0, id_contacto=None):
    return {"importe": importe, "fecha": "2026-08-05", "idContacto": id_contacto}


# --- US1: conciliación simple -------------------------------------------


def test_calcular_estado_sin_conciliaciones_es_sin_conciliar(monkeypatch):
    monkeypatch.setattr(repository, "_movimiento_original", lambda medio, idm: _fake_movimiento_bna())
    monkeypatch.setattr(repository, "listar_conciliaciones", lambda medio, idm: [])

    estado = repository.calcular_estado("bna", 555)

    assert estado["estado"] == "sin_conciliar"
    assert estado["importeTotal"] == 60500.0
    assert estado["saldoPendiente"] == 60500.0


def test_calcular_estado_con_suma_igual_al_total_es_conciliado(monkeypatch):
    monkeypatch.setattr(repository, "_movimiento_original", lambda medio, idm: _fake_movimiento_bna())
    monkeypatch.setattr(
        repository, "listar_conciliaciones", lambda medio, idm: [{"importe": 60500.0}]
    )

    estado = repository.calcular_estado("bna", 555)

    assert estado["estado"] == "conciliado"
    assert estado["saldoPendiente"] == 0.0


def test_aplicar_conciliacion_inserta_fila_con_medio_movimiento_contacto_importe(monkeypatch):
    monkeypatch.setattr(
        repository, "calcular_estado", lambda medio, idm: {"estado": "sin_conciliar", "saldoPendiente": 60500.0}
    )
    monkeypatch.setattr(repository, "fetch_one", lambda sql, params=(): {"x": 1})

    statements_capturados = []

    def _fake_transaction(statements):
        statements_capturados.extend(statements)
        return [88]

    monkeypatch.setattr(repository, "execute_write_transaction", _fake_transaction)
    monkeypatch.setattr(
        repository,
        "fetch_one",
        lambda sql, params=(): {"idConciliacion": 88, "idContacto": 42, "contacto": "X", "importe": 60500.0,
                                 "usuario": "u", "fecha": "2026-09-28"}
        if "IdConciliacion = ?" in sql
        else {"x": 1},
    )

    resultado = repository.aplicar_conciliacion("bna", 555, 42, 60500.0, "u")

    assert resultado["idConciliacion"] == 88
    sql, params = statements_capturados[0]
    assert "INSERT INTO dbo.ConciliacionesTesoreria" in sql
    assert params == ("bna", 555, 42, 60500.0, "u")


def test_aplicar_conciliacion_rechaza_importe_no_positivo():
    with pytest.raises(ValueError, match="mayor a cero"):
        repository.aplicar_conciliacion("bna", 555, 42, 0, "u")
    with pytest.raises(ValueError, match="mayor a cero"):
        repository.aplicar_conciliacion("bna", 555, 42, -10, "u")


def test_aplicar_conciliacion_rechaza_contacto_inexistente(monkeypatch):
    monkeypatch.setattr(repository, "fetch_one", lambda sql, params=(): None)
    with pytest.raises(ValueError, match="no existe"):
        repository.aplicar_conciliacion("bna", 555, 999999, 100.0, "u")


# --- US3: evitar doble conteo --------------------------------------------


def test_calcular_estado_movimiento_con_contacto_original_es_ya_reconocido(monkeypatch):
    monkeypatch.setattr(
        repository, "_movimiento_original", lambda medio, idm: _fake_movimiento_bna(id_contacto=605)
    )
    monkeypatch.setattr(repository, "listar_conciliaciones", lambda medio, idm: [])
    monkeypatch.setattr(repository, "fetch_one", lambda sql, params=(): {"n": "Carbajo"})

    estado = repository.calcular_estado("bna", 555)

    assert estado["estado"] == "ya_reconocido"


def test_aplicar_conciliacion_rechaza_movimiento_ya_reconocido(monkeypatch):
    monkeypatch.setattr(
        repository, "calcular_estado", lambda medio, idm: {"estado": "ya_reconocido", "saldoPendiente": 0.0}
    )
    monkeypatch.setattr(repository, "fetch_one", lambda sql, params=(): {"x": 1})

    with pytest.raises(ValueError, match="ya tiene un contacto reconocido"):
        repository.aplicar_conciliacion("bna", 555, 42, 100.0, "u")


def test_aplicar_conciliacion_rechaza_importe_que_excede_saldo_pendiente_recalculado(monkeypatch):
    """FR-010: el saldo pendiente se recalcula en el momento de escribir,
    no se confía en el que el cliente vio al abrir la pantalla — cubre el
    caso de dos usuarios conciliando el mismo movimiento a la vez."""
    monkeypatch.setattr(
        repository, "calcular_estado", lambda medio, idm: {"estado": "parcialmente_conciliado", "saldoPendiente": 300.0}
    )
    monkeypatch.setattr(repository, "fetch_one", lambda sql, params=(): {"x": 1})

    with pytest.raises(ValueError, match="excede el saldo pendiente"):
        repository.aplicar_conciliacion("mercado-libre", 1, 42, 500.0, "u")


def test_valores_recibidos_ya_reconocido_se_consulta_en_la_vista(monkeypatch):
    """valores-recibidos no tiene columna de contacto propia — se resuelve
    hoy vía las dos ramas de endoso ya existentes en
    vw_MovimientosCuenta_Base; se consulta esa vista en vez de reimplementar
    el join acá."""
    llamadas = []

    def _fake_fetch_one(sql, params=()):
        llamadas.append((sql, params))
        if "vw_MovimientosCuenta_Base" in sql:
            return {"IdContacto": 605}
        if "Razon Social" in sql:
            return {"n": "Gentos S.A."}
        return {"importe": 500.0, "fecha": "2026-08-01"}

    monkeypatch.setattr(repository, "fetch_one", _fake_fetch_one)
    monkeypatch.setattr(repository, "listar_conciliaciones", lambda medio, idm: [])

    estado = repository.calcular_estado("valores-recibidos", 17)

    assert estado["estado"] == "ya_reconocido"
    assert estado["idContactoReconocido"] == 605
    assert estado["contactoReconocido"] == "Gentos S.A."
    assert any("vw_MovimientosCuenta_Base" in sql for sql, _ in llamadas)


def test_valores_propios_nunca_es_ya_reconocido_por_columna_propia(monkeypatch):
    """valores-propios no tiene ninguna columna de contacto — solo puede
    quedar sin_conciliar/parcial/conciliado según sus propias conciliaciones."""
    monkeypatch.setattr(repository, "fetch_one", lambda sql, params=(): {"importe": 980000.0, "fecha": "2021-04-16"})
    monkeypatch.setattr(repository, "listar_conciliaciones", lambda medio, idm: [])

    estado = repository.calcular_estado("valores-propios", 1152)

    assert estado["estado"] == "sin_conciliar"


def test_medio_tarjetas_no_soportado(monkeypatch):
    with pytest.raises(ValueError, match="no se concilia desde este módulo"):
        repository.calcular_estado("tarjetas", 1)


# --- US2: reparto incremental ---------------------------------------------


def test_calcular_estado_con_suma_parcial_es_parcialmente_conciliado(monkeypatch):
    monkeypatch.setattr(repository, "_movimiento_original", lambda medio, idm: _fake_movimiento_bna())
    monkeypatch.setattr(
        repository, "listar_conciliaciones", lambda medio, idm: [{"importe": 45000.0}]
    )

    estado = repository.calcular_estado("bna", 555)

    assert estado["estado"] == "parcialmente_conciliado"
    assert estado["saldoPendiente"] == 15500.0


def test_calcular_estado_con_varias_conciliaciones_suma_todas(monkeypatch):
    monkeypatch.setattr(repository, "_movimiento_original", lambda medio, idm: _fake_movimiento_bna())
    monkeypatch.setattr(
        repository,
        "listar_conciliaciones",
        lambda medio, idm: [{"importe": 300.0}, {"importe": 200.0}],
    )
    monkeypatch.setattr(repository, "_movimiento_original", lambda medio, idm: _fake_movimiento_bna(importe=500.0))

    estado = repository.calcular_estado("bna", 1)

    assert estado["estado"] == "conciliado"
    assert estado["saldoPendiente"] == 0.0


# --- 024: rechazo si hay traspaso interno activo (FR-007) ------------------


def test_aplicar_conciliacion_rechaza_movimiento_con_traspaso_interno_activo(monkeypatch):
    monkeypatch.setattr(
        repository, "calcular_estado", lambda medio, idm: {"estado": "sin_conciliar", "saldoPendiente": 60500.0}
    )
    monkeypatch.setattr(
        repository,
        "fetch_one",
        lambda sql, params=(): {"Accion": "Vincular"} if "TraspasosInternosTesoreria" in sql else {"x": 1},
    )

    with pytest.raises(ValueError, match="traspaso interno"):
        repository.aplicar_conciliacion("mercado-libre", 25, 42, 100.0, "u")


# --- Esquema real (solo lectura contra WC) --------------------------------


def test_vista_cuenta_corriente_expone_la_rama_de_conciliacion_tesoreria():
    """Lectura real de solo-lectura contra WC (sin insertar nada): confirma
    que vw_MovimientosCuenta_Base compila con la rama nueva y resuelve sus
    columnas/tipos sin error (T004-T006 ya aplicados contra WC — ver
    scripts/crear_tabla_conciliaciones_tesoreria.py). No asume que la tabla
    esté vacía: desde que la funcionalidad se usa en producción (primeras
    conciliaciones reales confirmadas 2026-09-29), puede haber filas."""
    from src.db.connection import fetch_all

    filas = fetch_all(
        "SELECT TOP 5 Fecha, IdContacto, [Razon Social], Documento, [Nro Documento], Deuda, Credito, Origen, IdOrigen "
        "FROM dbo.vw_MovimientosCuenta_Base WHERE Origen = 'Conciliación Tesorería'"
    )
    for fila in filas:
        assert fila["Documento"] == "Conciliación Tesorería"
        assert fila["IdContacto"] is not None
        assert (fila["Deuda"] or 0) > 0 or (fila["Credito"] or 0) > 0


@pytest.fixture(autouse=True)
def _sin_transacciones_reales_026(monkeypatch):
    # Los tests de negocio simulan escrituras; el contexto común se verifica
    # aparte con conexiones simuladas, no obteniendo locks en producción.
    from contextlib import nullcontext
    from src.db import connection
    monkeypatch.setattr(connection, 'reconciliation_transaction', nullcontext)
    monkeypatch.setattr(repository, '_estado_vigente', lambda *args: None)
