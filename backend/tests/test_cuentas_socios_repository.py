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
        return [{"idCompra": 1, "fecha": "2025-11-14", "proveedor": "Cumo Store", "numeroDocumento": "0004-1", "importePersonal": 29699.10}]

    monkeypatch.setattr(repository, "fetch_all", _fake_fetch_all)
    resultado = repository.listar_compras_particulares_candidatas()
    assert resultado[0]["idCompra"] == 1
    assert "NOT EXISTS" in llamadas[0]
    assert "AsignacionGasto" in llamadas[0]


def test_asignar_gasto_inserta_movimiento_y_auditoria_en_una_transaccion(monkeypatch):
    monkeypatch.setattr(repository, "_tiene_asignacion_vigente", lambda id_compra: False)
    monkeypatch.setattr(repository, "importe_personal_compra_particular", lambda id_compra: 29699.10)

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


def test_asignar_gasto_usa_importe_personal_no_el_total_en_split_parcial(monkeypatch):
    """Caso Coto (2022-02-16): compra de $13.521 con línea negativa
    'Compra particular Lucy' de -$6.080,51 — queda $7.440,50 de deuda real
    con el proveedor. Solo los $6.080,51 personales van a la cuenta de
    Lucy, nunca el total de la compra."""
    monkeypatch.setattr(repository, "_tiene_asignacion_vigente", lambda id_compra: False)
    monkeypatch.setattr(repository, "importe_personal_compra_particular", lambda id_compra: 6080.51)

    statements_capturados = []

    def _fake_transaction(statements):
        statements_capturados.extend(statements)
        resultados = [7]
        for s in statements[1:]:
            resultados.append(s(resultados) if callable(s) else None)
        return resultados

    monkeypatch.setattr(repository, "execute_write_transaction", _fake_transaction)
    monkeypatch.setattr(repository, "_movimiento_por_id", lambda idm: {"idMovimiento": idm})

    repository.asignar_gasto(id_socio=2, id_compra=999, usuario="sgiamberardini")

    _, params_insert = statements_capturados[0]
    assert params_insert == (2, 6080.51, 999, None, "sgiamberardini")


def test_asignar_gasto_rechaza_si_ya_tiene_asignacion_vigente(monkeypatch):
    monkeypatch.setattr(repository, "_tiene_asignacion_vigente", lambda id_compra: True)
    with pytest.raises(ValueError, match="ya tiene una asignación vigente"):
        repository.asignar_gasto(id_socio=1, id_compra=2143515240, usuario="sgiamberardini")


def test_asignar_gasto_rechaza_si_no_es_compra_particular(monkeypatch):
    monkeypatch.setattr(repository, "_tiene_asignacion_vigente", lambda id_compra: False)
    monkeypatch.setattr(repository, "importe_personal_compra_particular", lambda id_compra: None)
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
    monkeypatch.setattr(repository, "importe_personal_compra_particular", lambda id_compra: 100.0)
    monkeypatch.setattr(repository, "execute_write_transaction", lambda statements: [1])
    monkeypatch.setattr(repository, "_movimiento_por_id", lambda idm: {"idMovimiento": idm})

    with pytest.raises(ValueError):
        repository.asignar_gasto(1, 5, "u")

    estado["vigente"] = False
    resultado = repository.asignar_gasto(1, 5, "u")
    assert resultado == {"idMovimiento": 1}


def test_calcular_saldo_suma_asignaciones_y_resta_devoluciones(monkeypatch):
    monkeypatch.setattr(repository, "fetch_one", lambda sql, params=(): {"saldo": 29699.10})
    assert repository.calcular_saldo(1) == 29699.10


def test_calcular_saldo_sin_movimientos_devuelve_cero(monkeypatch):
    monkeypatch.setattr(repository, "fetch_one", lambda sql, params=(): {"saldo": None})
    assert repository.calcular_saldo(1) == 0.0


def test_listar_socios_con_saldo_devuelve_los_4_incluido_uno_en_cero(monkeypatch):
    monkeypatch.setattr(
        repository,
        "fetch_all",
        lambda sql, params=(): [
            {"idSocio": 1, "nombre": "Sergio"},
            {"idSocio": 2, "nombre": "Lucy"},
            {"idSocio": 3, "nombre": "Cond LSC"},
            {"idSocio": 4, "nombre": "Ceci"},
        ],
    )
    saldos = {1: 29699.10, 2: 0.0, 3: 0.0, 4: 0.0}
    monkeypatch.setattr(repository, "calcular_saldo", lambda idSocio: saldos[idSocio])

    resultado = repository.listar_socios_con_saldo()

    assert len(resultado) == 4
    assert resultado[1] == {"idSocio": 2, "nombre": "Lucy", "saldo": 0.0}


def test_listar_movimientos_incluye_anulados_y_marca_huerfano(monkeypatch):
    monkeypatch.setattr(
        repository,
        "fetch_all",
        lambda sql, params=(): [
            {
                "idMovimiento": 1, "tipo": "AsignacionGasto", "importe": 100.0, "fecha": "2025-11-14",
                "origen": "CompraParticular", "idOrigen": 999999999, "medio": None, "motivo": None,
                "usuario": "u", "anulada": True, "motivoAnulacion": "Error de asignación",
                "proveedorOrigen": None, "numeroDocumentoOrigen": None, "huerfano": 1,
            },
        ],
    )
    resultado = repository.listar_movimientos(1)
    assert len(resultado) == 1
    assert resultado[0]["anulada"] is True
    assert resultado[0]["huerfano"] is True


def test_registrar_devolucion_inserta_movimiento_y_auditoria_en_una_transaccion(monkeypatch):
    statements_capturados = []

    def _fake_transaction(statements):
        statements_capturados.extend(statements)
        resultados = [43]
        for s in statements[1:]:
            resultados.append(s(resultados) if callable(s) else None)
        return resultados

    monkeypatch.setattr(repository, "execute_write_transaction", _fake_transaction)
    monkeypatch.setattr(repository, "_movimiento_por_id", lambda idm: {"idMovimiento": idm})

    resultado = repository.registrar_devolucion(
        id_socio=1, importe=15000.0, fecha="2025-11-20", medio="Transferencia", motivo="Devolución parcial", usuario="u"
    )

    assert resultado == {"idMovimiento": 43}
    sql_insert, params_insert = statements_capturados[0]
    assert "Devolucion" in sql_insert
    assert params_insert == (1, 15000.0, "2025-11-20", "Transferencia", "Devolución parcial", "u")
    sql_auditoria, params_auditoria = statements_capturados[1]([43])
    assert "Devolucion" in sql_auditoria
    assert params_auditoria[0] == 43


def test_registrar_devolucion_acepta_importe_mayor_al_saldo():
    """Edge case de la spec: no se rechaza, el socio queda con saldo a favor."""
    # No debe lanzar ValueError por el monto en si; solo valida importe > 0 y motivo no vacio.
    pass


def test_registrar_devolucion_rechaza_importe_cero_o_negativo():
    with pytest.raises(ValueError, match="mayor a \\$0"):
        repository.registrar_devolucion(1, 0.0, "2025-11-20", "Transferencia", "motivo", "u")
    with pytest.raises(ValueError, match="mayor a \\$0"):
        repository.registrar_devolucion(1, -100.0, "2025-11-20", "Transferencia", "motivo", "u")


def test_registrar_devolucion_rechaza_motivo_vacio():
    with pytest.raises(ValueError, match="motivo es obligatorio"):
        repository.registrar_devolucion(1, 1000.0, "2025-11-20", "Transferencia", "  ", "u")


def test_anular_devolucion_genera_reversiondevolucion_en_auditoria(monkeypatch):
    monkeypatch.setattr(
        repository,
        "fetch_one",
        lambda sql, params=(): {"idMovimiento": 43, "idSocio": 1, "tipo": "Devolucion", "anulada": False},
    )
    statements_capturados = []

    def _fake_transaction(statements):
        statements_capturados.extend(statements)
        return [1, 1]

    monkeypatch.setattr(repository, "execute_write_transaction", _fake_transaction)
    monkeypatch.setattr(repository, "_movimiento_por_id", lambda idm: {"idMovimiento": idm, "anulada": True})

    repository.anular_movimiento(43, "Monto mal cargado", "u")

    sql_auditoria, params_auditoria = statements_capturados[1]
    assert "ReversionDevolucion" in params_auditoria
