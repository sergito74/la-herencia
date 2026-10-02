"""Reintegros de tarjeta (líneas negativas) y signo de las Notas de Crédito.

Caso real 2026-10-02, Luvik S.A.: un reintegro de -$11.998 no aparecía como
pendiente, no se podía vincular ("ya está completamente vinculada") y su Nota
de Crédito estaba cargada en positivo (sumaba como deuda).
"""

import pytest

from src.features.compras.repository import normalizar_signo_nota_credito
from src.features.conciliacion_tesoreria import documentos_adapter
from src.features.tarjetas_resumenes.conciliacion_documentos import calcular_imputacion


def _doc(importe, id_compra=1):
    return {"idCompra": id_compra, "idImpuesto": None, "moneda": "Pesos", "tipoDeCambio": 1,
            "importeOriginal": importe}


def _linea(precio, cantidad=1, iva=21):
    return {"cantidad": cantidad, "precioUnitario": precio, "iva": iva}


def test_reintegro_contra_nota_credito_exacta():
    r = calcular_imputacion(-11998.0, [_doc(-11998.0)])
    assert r["estado"] == "exacta"
    assert r["imputados"][0]["importeImputado"] == -11998.0


def test_reintegro_menor_que_la_nota_es_pago_parcial_de_la_nota():
    r = calcular_imputacion(-100.0, [_doc(-300.0)])
    assert r["pagoParcial"] is True
    assert r["permiteParcial"] is False
    assert r["imputados"][0]["importeImputado"] == -100.0


def test_reintegro_mayor_que_la_nota_queda_pendiente_sin_forzar():
    r = calcular_imputacion(-300.0, [_doc(-100.0)])
    assert r["pagoParcial"] is False
    assert r["permiteParcial"] is True
    assert r["imputados"][0]["importeImputado"] == -100.0


def test_linea_positiva_sin_cambios():
    r = calcular_imputacion(100.0, [_doc(300.0)])
    assert r["pagoParcial"] is True and r["imputados"][0]["importeImputado"] == 100.0


def test_adaptador_exige_mismo_signo_que_la_linea():
    nc = [{"origen": "Compras", "idOrigen": 7, "saldoPendiente": -50.0, "moneda": "Pesos"}]
    assert documentos_adapter.calcular(-50.0, nc)["estado"] == "exacta"
    with pytest.raises(ValueError):
        documentos_adapter.calcular(50.0, nc)


def test_nota_credito_cargada_en_positivo_se_guarda_negativa():
    cab, lineas = normalizar_signo_nota_credito(
        {"tipoDocumento": "Nota de Crédito", "ingresosBrutos": 10.0}, [_linea(4957.85, 2)])
    assert lineas[0]["precioUnitario"] == -4957.85 and lineas[0]["cantidad"] == 2
    assert cab["ingresosBrutos"] == -10.0


def test_nota_credito_ya_negativa_y_factura_no_se_tocan():
    cab, lineas = normalizar_signo_nota_credito({"tipoDocumento": "Nota de Crédito"}, [_linea(-100.0)])
    assert lineas[0]["precioUnitario"] == -100.0
    cab, lineas = normalizar_signo_nota_credito({"tipoDocumento": "Factura"}, [_linea(100.0)])
    assert lineas[0]["precioUnitario"] == 100.0


def test_numero_sin_digitos_no_se_controla_como_duplicado(monkeypatch):
    from src.features.compras import repository as C
    llamadas = []
    monkeypatch.setattr(C, "fetch_one", lambda sql, params: llamadas.append(params) or {"idCompra": 1})
    for marca in ("SIN DOCUMENTO", "S/D", "SIN FACTURA", "FALTA FACTURA"):
        assert C.buscar_documento_duplicado(626, marca) is None
    assert llamadas == []
    assert C.buscar_documento_duplicado(626, "0002-01277521") == {"idCompra": 1}
