"""Tests de `cuentas_socios.repository` — mismo criterio que 019/020/021:
monkeypatch sobre los puntos de entrada a `WC`, no se escribe contra la
base real en tests automatizados (docstring de
`test_aplicaciones_pago_endpoints.py`)."""

from __future__ import annotations

import pytest

from src.features.cuentas_socios import repository


def test_listar_compras_particulares_candidatas_filtra_asignadas(monkeypatch):
    llamadas = []

    def _fake_fetch_all(sql, params=()):
        llamadas.append(sql)
        return [{"idCompra": 1, "fecha": "2025-11-14", "proveedor": "Cumo Store", "numeroDocumento": "0004-1", "importeBruto": 29699.10}]

    monkeypatch.setattr(repository, "fetch_all", _fake_fetch_all)
    resultado = repository.listar_compras_particulares_candidatas()
    assert resultado[0]["idCompra"] == 1
    assert "NOT EXISTS" in llamadas[0]
    assert "AsignacionGasto" in llamadas[0]


def test_asignar_gasto_inserta_movimiento_y_auditoria_en_una_transaccion(monkeypatch):
    monkeypatch.setattr(repository, "_tiene_asignacion_vigente", lambda id_compra: False)
    monkeypatch.setattr(repository, "importe_bruto_compra_particular", lambda id_compra: 29699.10)

    statements_capturados = []

    def _fake_transaction(statements):
        statements_capturados.extend(statements)
        resultados = [42]
        for s in statements[1:]:
            resultados.append(s(resultados) if callable(s) else None)
        return resultados

    monkeypatch.setattr(repository, "execute_write_transaction", _fake_transaction)
    monkeypatch.setattr(repository, "_movimiento_por_id", lambda idm: {"idMovimiento": idm})

    resultado = repository.asignar_gasto(id_socio=1, id_compra=2143515240, usuario="sgiamberardini")

    assert resultado == {"idMovimiento": 42}
    assert len(statements_capturados) == 2
    sql_insert, params_insert = statements_capturados[0]
    assert "AsignacionGasto" in sql_insert
    assert params_insert == (1, 29699.10, 2143515240, None, "sgiamberardini")
    sql_auditoria, params_auditoria = statements_capturados[1]([42])
    assert "Asignacion" in sql_auditoria
    assert params_auditoria[0] == 42


def test_asignar_gasto_rechaza_si_ya_tiene_asignacion_vigente(monkeypatch):
    monkeypatch.setattr(repository, "_tiene_asignacion_vigente", lambda id_compra: True)
    with pytest.raises(ValueError, match="ya tiene una asignación vigente"):
        repository.asignar_gasto(id_socio=1, id_compra=2143515240, usuario="sgiamberardini")


def test_asignar_gasto_rechaza_si_no_es_compra_particular(monkeypatch):
    monkeypatch.setattr(repository, "_tiene_asignacion_vigente", lambda id_compra: False)
    monkeypatch.setattr(repository, "importe_bruto_compra_particular", lambda id_compra: None)
    with pytest.raises(ValueError, match="no es una compra particular"):
        repository.asignar_gasto(id_socio=1, id_compra=999, usuario="sgiamberardini")


def test_anular_movimiento_marca_anulada_sin_tocar_importe(monkeypatch):
    monkeypatch.setattr(
        repository,
        "fetch_one",
        lambda sql, params=(): {"idMovimiento": 42, "idSocio": 1, "tipo": "AsignacionGasto", "anulada": False},
    )
    statements_capturados = []

    def _fake_transaction(statements):
        statements_capturados.extend(statements)
        return [1, 1]

    monkeypatch.setattr(repository, "execute_write_transaction", _fake_transaction)
    monkeypatch.setattr(repository, "_movimiento_por_id", lambda idm: {"idMovimiento": idm, "anulada": True})

    resultado = repository.anular_movimiento(42, "Se asignó al socio equivocado", "sgiamberardini")

    assert resultado["anulada"] is True
    sql_update, params_update = statements_capturados[0]
    assert "SET Anulada = 1" in sql_update
    assert "Importe" not in sql_update  # nunca toca el importe original
    sql_auditoria, params_auditoria = statements_capturados[1]
    assert "ReversionAsignacion" in params_auditoria


def test_anular_movimiento_rechaza_si_ya_esta_anulado(monkeypatch):
    monkeypatch.setattr(
        repository,
        "fetch_one",
        lambda sql, params=(): {"idMovimiento": 42, "idSocio": 1, "tipo": "AsignacionGasto", "anulada": True},
    )
    with pytest.raises(ValueError, match="ya está anulado"):
        repository.anular_movimiento(42, "motivo", "sgiamberardini")


def test_permite_reasignar_tras_anular(monkeypatch):
    """Confirma el flujo completo: anular libera la compra para una
    nueva asignación (FR-009 solo bloquea asignaciones *vigentes*)."""
    estado = {"vigente": True}
    monkeypatch.setattr(repository, "_tiene_asignacion_vigente", lambda id_compra: estado["vigente"])
    monkeypatch.setattr(repository, "importe_bruto_compra_particular", lambda id_compra: 100.0)
    monkeypatch.setattr(repository, "execute_write_transaction", lambda statements: [1])
    monkeypatch.setattr(repository, "_movimiento_por_id", lambda idm: {"idMovimiento": idm})

    with pytest.raises(ValueError):
        repository.asignar_gasto(1, 5, "u")

    estado["vigente"] = False
    resultado = repository.asignar_gasto(1, 5, "u")
    assert resultado == {"idMovimiento": 1}
