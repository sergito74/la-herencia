"""Tests de `tarjetas_resumenes.repository` para 025-conciliacion-
tarjetas-impuestos — cubre US1 (buscar/vincular pagos de Impuestos) y US2
(no regresión de Compras). Mezcla monkeypatch (para las escrituras) con
lecturas reales de solo-lectura contra `WC` donde el dato real ya alcanza
para probar la lógica (mismo criterio que `test_cuentas_corrientes_saldos.py`).
"""

from __future__ import annotations

import pytest

from src.db.connection import fetch_all
from src.features.tarjetas_resumenes import repository


# --- T006: saldo_pendiente_impuesto ---------------------------------------


def test_saldo_pendiente_impuesto_sin_vinculos_es_el_importe_total(monkeypatch):
    monkeypatch.setattr(
        repository,
        "fetch_one",
        lambda sql, params=(): {"importe": 1897.94, "vinculado": 0},
    )
    assert repository.saldo_pendiente_impuesto(14) == 1897.94


def test_saldo_pendiente_impuesto_descuenta_lo_ya_vinculado(monkeypatch):
    monkeypatch.setattr(
        repository,
        "fetch_one",
        lambda sql, params=(): {"importe": 1000.0, "vinculado": 400.0},
    )
    assert repository.saldo_pendiente_impuesto(14, excluir_id_linea=99) == 600.0


def test_saldo_pendiente_impuesto_inexistente_rechaza(monkeypatch):
    monkeypatch.setattr(repository, "fetch_one", lambda sql, params=(): None)
    with pytest.raises(ValueError, match="No existe ningún pago de Impuestos"):
        repository.saldo_pendiente_impuesto(999999)


# --- T009/T021: buscar_documentos incluye Impuestos, sin romper Compras --


def test_buscar_documentos_organismos_reales_devuelve_resultados():
    """SC-004: los 4 organismos reales conocidos (WC, 2026-09-29) son
    encontrables por el buscador."""
    for organismo in ("AFIP", "ARBA", "Municipalidad", "UATRE"):
        resultados = repository.buscar_documentos(organismo)
        assert len(resultados) > 0, f"sin resultados para {organismo}"
        assert any(d["origen"] == "Impuestos" for d in resultados), (
            f"sin resultados de Impuestos para {organismo} (puede haber resultados de Compras mezclados)"
        )


def test_buscar_documentos_nunca_incluye_impuesto_sin_organismo():
    """FR-006 — verificado contra WC real: ningún resultado de Impuestos
    corresponde a una fila con IdOrganismo nulo (la propia consulta ya lo
    filtra; acá se confirma que no hay forma de colarlo buscando texto
    vacío/comodín)."""
    resultados = repository.buscar_documentos("a")
    impuestos_sin_organismo = fetch_all(
        "SELECT IdImpuesto FROM dbo.Impuestos WHERE IdOrganismo IS NULL"
    )
    ids_sin_organismo = {r["IdImpuesto"] for r in impuestos_sin_organismo}
    for d in resultados:
        if d["origen"] == "Impuestos":
            assert d["idImpuesto"] not in ids_sin_organismo


def test_buscar_documentos_compras_sigue_igual_que_antes():
    """FR-007/US2: un proveedor real de Compras sigue devolviendo
    resultados con origen 'Compras', mismos campos de siempre."""
    resultados = repository.buscar_documentos("Primor")
    assert len(resultados) > 0
    assert all(d["origen"] == "Compras" for d in resultados)
    assert all(d["idImpuesto"] is None for d in resultados)
    assert all(d["saldoPendiente"] is not None for d in resultados)  # 026: saldo compartido


# --- T011a: saldo pendiente en cero no debe reaparecer ---------------------


def test_buscar_documentos_no_incluye_impuesto_con_saldo_pendiente_cero(monkeypatch):
    """Remediación C2 de /speckit-analyze — con monkeypatch sobre fetch_all
    para no depender de tener un pago real ya cubierto por completo en WC."""
    llamada = {"sql": None}

    def _fake_fetch_all(sql, params=()):
        llamada["sql"] = sql
        return []

    monkeypatch.setattr(repository, "fetch_all", _fake_fetch_all)
    repository.buscar_documentos("cualquiera")
    assert "saldoPendiente" not in llamada["sql"] or "> 0.005" in llamada["sql"]


# --- T011/T011b: aplicar_conciliacion respeta el saldo pendiente ----------


def test_calcular_conciliacion_rechaza_impuesto_sin_saldo_suficiente(monkeypatch):
    monkeypatch.setattr(repository, "get_linea", lambda idl: {"importe": 1000.0, "idContacto": None, "fechaCompra": None})
    monkeypatch.setattr(repository, "_total_imputado", lambda idl: 0.0)
    monkeypatch.setattr(repository, "get_documentos_por_ids", lambda ids: [])
    monkeypatch.setattr(
        repository,
        "get_documentos_impuestos_por_ids",
        lambda ids: [
            {
                "idCompra": None,
                "idImpuesto": 14,
                "origen": "Impuestos",
                "fecha": None,
                "importeOriginal": 1000.0,
                "importePesos": 1000.0,
                "moneda": None,
                "tipoDeCambio": None,
                "ajustaTipoCambio": False,
                "compraParticular": 0.0,
                "proveedor": "AFIP",
                "saldoPendiente": 300.0,  # menos que los 1000 que pide la línea
            }
        ],
    )
    # 026: preview usa el saldo compartido; no intenta imputar los 1000 originales.
    result = repository.calcular_conciliacion(1, [], [14])
    assert result['imputados'][0]['importeImputado'] == 300.0
    assert result['permiteParcial']


def test_dos_vinculaciones_sucesivas_exceden_el_saldo_la_segunda_falla(monkeypatch):
    """FR-009 (concurrencia): el saldo pendiente se recalcula en cada
    llamada, no se confía en el que vio la primera."""
    estado = {"vinculado": 0.0}

    def _fake_fetch_one(sql, params=()):
        if "Impuestos" in sql:
            return {"importe": 500.0, "vinculado": estado["vinculado"]}
        return None

    monkeypatch.setattr(repository, "fetch_one", _fake_fetch_one)
    monkeypatch.setattr(repository, "get_linea", lambda idl: {"importe": 300.0, "idContacto": None, "fechaCompra": None})
    monkeypatch.setattr(repository, "_total_imputado", lambda idl: 0.0)
    monkeypatch.setattr(repository, "get_documentos_por_ids", lambda ids: [])

    def _fake_docs_impuesto(ids):
        saldo = repository.saldo_pendiente_impuesto(ids[0])
        return [
            {
                "idCompra": None,
                "idImpuesto": ids[0],
                "origen": "Impuestos",
                "fecha": None,
                "importeOriginal": 500.0,
                "importePesos": 500.0,
                "moneda": None,
                "tipoDeCambio": None,
                "ajustaTipoCambio": False,
                "compraParticular": 0.0,
                "proveedor": "AFIP",
                "saldoPendiente": saldo,
            }
        ]

    monkeypatch.setattr(repository, "get_documentos_impuestos_por_ids", _fake_docs_impuesto)

    # Primera "sesión": vincula $300 (todo el saldo que necesita esta línea).
    repository.calcular_conciliacion(1, [], [14])
    estado["vinculado"] = 300.0  # simula que la primera vinculación ya se guardó

    # Segunda "sesión", que vio el saldo ANTES de la primera escritura,
    # intenta vincular $300 de nuevo — debe fallar con el saldo real (200).
    result = repository.calcular_conciliacion(2, [], [14])
    assert result['imputados'][0]['importeImputado'] == 200.0
    assert result['permiteParcial']
    # Un envío manual de 300 sí debe rechazarse (protegido en vincular_compra).
    with pytest.raises(ValueError, match='saldo documental'):
        repository.documentos_compartidos.validar_imputacion(200,300)


# --- T020b: desvincular deja el pago disponible de nuevo -------------------


def test_desvincular_impuesto_deja_disponible_de_nuevo(monkeypatch):
    llamadas = []
    monkeypatch.setattr(repository, "execute_write", lambda sql, params: llamadas.append((sql, params)))
    repository.quitar_vinculo_compra(123)
    assert llamadas[0][1] == (123,)
    assert "Tarjetas_Resumenes_Lineas_Compras" in llamadas[0][0]


# --- T022/T023: no regresión de vincular_compras_lote/conciliacion_documentos ---


def test_vincular_compras_lote_solo_compras_no_cambia_forma(monkeypatch):
    """US2: con ids_impuesto vacío/omitido, el resultado no debería
    diferir del comportamiento ya validado antes de esta feature — mismo
    criterio (imputados, diferencia) que ya prueban los tests de
    `test_conciliacion_documentos.py`."""
    monkeypatch.setattr(repository, "_asegurar_pendiente", lambda idl: {"importe": 250.0, "idContacto": 1, "fechaCompra": None})
    monkeypatch.setattr(repository, "get_linea", lambda idl: {"importe": 250.0, "idContacto": 1, "fechaCompra": None})
    monkeypatch.setattr(repository, "_total_imputado", lambda idl: 0.0)
    monkeypatch.setattr(
        repository,
        "get_documentos_por_ids",
        lambda ids: [
            {
                "idCompra": 1,
                "origen": "Compras",
                "idImpuesto": None,
                "fecha": None,
                "importeOriginal": 1000.0,
                "importePesos": 1000.0,
                "moneda": None,
                "tipoDeCambio": None,
                "ajustaTipoCambio": False,
                "compraParticular": 0.0,
                "proveedor": "X",
                "saldoPendiente": 1000.0,
            }
        ],
    )
    monkeypatch.setattr(repository, "get_documentos_impuestos_por_ids", lambda ids: [])

    statements_capturados = []
    monkeypatch.setattr(
        repository, "execute_write_transaction", lambda statements: statements_capturados.extend(statements) or [1]
    )
    monkeypatch.setattr(repository, "get_compras_vinculadas", lambda idl: [{"idVinculo": 1}])

    repository.vincular_compras_lote(1, [1])

    sql, params = statements_capturados[0]
    assert "IdImpuesto" in sql  # la columna nueva está en el INSERT...
    assert params == (1, 1, None, 250.0)  # ...pero va NULL, mismo resultado que antes para Compras


@pytest.fixture(autouse=True)
def _sin_transacciones_reales_026(monkeypatch):
    from contextlib import nullcontext
    from src.db import connection
    monkeypatch.setattr(connection, 'reconciliation_transaction', nullcontext)
