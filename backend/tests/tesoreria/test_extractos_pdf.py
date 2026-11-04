"""Lector del resumen PDF de Galicia (04/11/2026)."""

import pytest

from src.features.tesoreria import extractos_pdf as x

LINEAS = [
    "Resumen de Cuenta Corriente en Pesos", "GIAMIGLI DE BOLIVAR SA", "Datos de la cuenta Período de movimientos Saldos",
    "$1.000,00", "CBU 30/09/2026 30/10/2026", "0070383120000000798846",
    "Fecha Descripción Origen Crédito Débito Saldo",
    "01/10/26 PAGO DE SERVICIOS 0001 -100,50 899,50", "MOVISTAR", "042004161793",
    "01/10/26 SERVICIO ACREDITAMIENTO DE -400,00 499,50", "HABERES", "ACRED.HABERES",
    "07/10/26 SERVICIO PAGO A PROVEEDORES 1.000,00 1.499,50", "GANADERA SAN JUSTO S", "30715943278",
    "Resumen de Cuenta Corriente en Pesos Página 1 / 5", "20261030046193054H",
    "Total de impuestos 0,00",
]


def test_reconoce_galicia():
    assert x.detectar_banco(LINEAS) == "galicia"


def test_lee_movimientos_y_leyendas(monkeypatch):
    monkeypatch.setattr(x, "_lineas", lambda _pdf: LINEAS)
    movs = x.leer_galicia_pdf(b"%PDF", "prueba.pdf")
    assert [(m["debitos"], m["creditos"], m["saldo"]) for m in movs] == [(100.5, None, 899.5), (400.0, None, 499.5),
                                                                      (None, 1000.0, 1499.5)]
    assert movs[0]["descripcion"] == "Pago De Servicios" and movs[0]["leyendas"] == ["MOVISTAR", "042004161793"]
    assert movs[1]["descripcion"] == "Servicio Acreditamiento De Haberes"
    assert movs[2]["leyendas"] == ["GANADERA SAN JUSTO S", "30715943278"]


def test_saldo_que_no_cierra_frena_todo(monkeypatch):
    malas = [l.replace("899,50", "899,00") for l in LINEAS]
    monkeypatch.setattr(x, "_lineas", lambda _pdf: malas)
    with pytest.raises(RuntimeError):
        x.leer_galicia_pdf(b"%PDF", "prueba.pdf")


def test_transferencia_de_canje_va_al_contacto_del_socio(monkeypatch):
    from datetime import date

    monkeypatch.setattr(x, "canjes_pendientes", lambda _b: [
        {"id": 3, "fecha": date(2026, 10, 28), "socio": 2, "version": 0, "importe": 810000.0, "contacto": 390}])
    nuevos = [{"fecha": date(2026, 10, 28), "debitos": 810000.0, "creditos": None, "idContacto": None},
              {"fecha": date(2026, 10, 28), "debitos": 830000.0, "creditos": None, "idContacto": 375}]
    x._marcar_canjes("galicia", nuevos)
    assert nuevos[0]["idContacto"] == 390 and nuevos[0]["canje"]["id"] == 3
    assert nuevos[1]["idContacto"] == 375 and "canje" not in nuevos[1]
