"""Facturas a pagar (rehecho 04/11/2026): saldo por factura según sus pagos, sin repartos supuestos; la diferencia
con la cuenta corriente se muestra; se separan las que se pagan con tarjeta y los restos chicos viejos."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from src.features.cuentas_corrientes import repository as cuentas
from src.features.ordenes_pago import repository as repo


def _f(id_, fecha, saldo, vto=None, total=None, suspendida=False):
    return {"idCompra": id_, "numero": f"0001-{id_:08d}", "fecha": fecha, "fechaVto": vto, "moneda": "Pesos", "tc": None,
            "total": total or saldo, "pagado": 0, "saldo": Decimal(str(saldo)), "reservado": Decimal(0),
            "disponible": Decimal(str(saldo)), "suspendida": suspendida}


def test_no_reparte_y_muestra_la_diferencia_con_la_cuenta(monkeypatch):
    hoy = date.today()
    monkeypatch.setattr(cuentas, "get_saldos_todos", lambda: [
        {"idContacto": 1, "razonSocial": "Con pagos sin imputar", "saldoParcial": -150.0},
        {"idContacto": 2, "razonSocial": "En cero", "saldoParcial": 0.0},
        {"idContacto": 3, "razonSocial": "Con tarjeta", "saldoParcial": -100.0},
        {"idContacto": 4, "razonSocial": "Suspendida", "saldoParcial": -500.0}])
    facturas = {1: [_f(10, hoy - timedelta(days=400), 50, total=100000), _f(11, hoy - timedelta(days=10), 200)],
                2: [_f(20, date(2026, 1, 1), 500)],
                3: [_f(30, hoy - timedelta(days=5), 100, vto=hoy + timedelta(days=30))],
                4: [_f(40, hoy - timedelta(days=60), 500, suspendida=True)]}
    monkeypatch.setattr(repo, "facturas", lambda c, *a, **k: facturas[c])
    monkeypatch.setattr(repo, "medio_habitual", lambda c: "tarjetas" if c == 3 else "galicia")
    filas = {f["idCompra"]: f for f in repo._pendientes()}
    assert filas[10]["estado"] == "diferencia"  # resto chico de una factura vieja
    assert filas[11]["estado"] == "a pagar" and filas[11]["saldo"] == Decimal(200)  # saldo propio, sin recortar
    assert filas[11]["difCuenta"] == Decimal(-100)  # 150 de cuenta − 250 de facturas: pagos sin imputar
    assert 20 not in filas  # cuenta en cero: nada que pagar
    assert filas[30]["estado"] == "tarjeta"
    assert filas[40]["suspendida"] and filas[40]["estado"] == "a pagar"  # la suspendida aparece
