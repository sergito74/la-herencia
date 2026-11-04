"""Facturas a pagar (04/11/2026): con portal manda el portal; sin portal, saldo de cada factura según sus pagos,
sin repartos; cuenta en cero no muestra nada; bancos fuera."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from src.features.cuentas_corrientes import repository as cuentas
from src.features.ordenes_pago import repository as repo


def _f(id_, fecha, saldo):
    return {"idCompra": id_, "numero": f"0001-{id_:08d}", "fecha": fecha, "fechaVto": None, "moneda": "Pesos", "tc": None,
            "total": Decimal(saldo), "pagado": 0, "saldo": Decimal(saldo), "reservado": Decimal(0),
            "disponible": Decimal(saldo), "suspendida": False}


def test_portal_manda_y_sin_portal_no_reparte(monkeypatch):
    monkeypatch.setattr(cuentas, "get_saldos_todos", lambda: [
        {"idContacto": 258, "razonSocial": "Cargill", "saldoParcial": -9_000_000.0},
        {"idContacto": 1, "razonSocial": "Sin portal", "saldoParcial": -150.0},
        {"idContacto": 2, "razonSocial": "En cero", "saldoParcial": 0.0},
        {"idContacto": 3, "razonSocial": "Banco Galicia", "saldoParcial": -10.0}])
    monkeypatch.setattr(repo, "_portal_pendientes", lambda: {258: [
        {"numero": "ND 1", "fecha": date(2026, 6, 10), "importe": Decimal("570.54"), "moneda": "Pesos"}]})
    facturas = {1: [_f(10, date(2026, 1, 1), 300)], 2: [_f(20, date(2026, 1, 1), 500)], 3: [_f(30, date(2026, 1, 1), 10)],
                258: [_f(40, date(2022, 1, 1), 9_000_000)]}
    monkeypatch.setattr(repo, "facturas", lambda c, *a, **k: facturas[c])
    monkeypatch.setattr(repo, "medio_habitual", lambda c: "galicia")
    filas = repo._pendientes()
    cargill = [f for f in filas if f["idContacto"] == 258]
    assert [f["numero"] for f in cargill] == ["ND 1"]  # las facturas viejas de Cargill no aparecen: manda el portal
    sin = [f for f in filas if f["idContacto"] == 1]
    assert sin[0]["saldo"] == Decimal(300) and sin[0]["difCuenta"] == Decimal(-150)  # no se recorta, se muestra
    assert not [f for f in filas if f["idContacto"] in (2, 3)]
