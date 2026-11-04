"""Facturas a pagar (04/11/2026, v3): manda el saldo conciliado de la cuenta; lo impago son los documentos más
nuevos hasta cubrirlo (los pagos van a lo más viejo). No se usan las imputaciones factura por factura."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from src.features.cuentas_corrientes import repository as cuentas
from src.features.ordenes_pago import repository as repo


def _f(id_, fecha, total, saldo_vinculos=None, suspendida=False):
    return {"idCompra": id_, "numero": f"0001-{id_:08d}", "fecha": fecha, "fechaVto": None, "moneda": "Pesos", "tc": None,
            "total": Decimal(total), "pagado": 0, "saldo": Decimal(saldo_vinculos if saldo_vinculos is not None else total),
            "reservado": Decimal(0), "disponible": Decimal(total), "suspendida": suspendida}


def test_manda_el_saldo_de_la_cuenta(monkeypatch):
    monkeypatch.setattr(cuentas, "get_saldos_todos", lambda: [
        {"idContacto": 1, "razonSocial": "Imputaciones incompletas", "saldoParcial": -150.0},
        {"idContacto": 2, "razonSocial": "En cero", "saldoParcial": 0.0},
        {"idContacto": 3, "razonSocial": "Con tarjeta", "saldoParcial": -100.0},
        {"idContacto": 4, "razonSocial": "Banco Galicia", "saldoParcial": -10.0}])
    facturas = {1: [_f(10, date(2026, 1, 1), 300), _f(11, date(2026, 9, 1), 100), _f(12, date(2026, 10, 1), 100, suspendida=True)],
                2: [_f(20, date(2026, 1, 1), 500)],
                3: [_f(30, date(2026, 8, 1), 100)],
                4: [_f(40, date(2026, 8, 1), 10)]}
    monkeypatch.setattr(repo, "facturas", lambda c, *a, **k: facturas[c])
    monkeypatch.setattr(repo, "_otros_documentos", lambda c: [])
    monkeypatch.setattr(repo, "medio_habitual", lambda c: "tarjetas" if c == 3 else "galicia")
    filas = {f["idCompra"]: f for f in repo._pendientes()}
    assert (filas[12]["saldo"], filas[11]["saldo"]) == (Decimal(100), Decimal(50))  # las más nuevas hasta 150
    assert 10 not in filas and 20 not in filas  # la vieja se pagó; cuenta en cero no muestra nada
    assert filas[12]["suspendida"] and filas[11]["ajustado"]
    assert filas[30]["estado"] == "tarjeta" and filas[40]["estado"] == "debito"
