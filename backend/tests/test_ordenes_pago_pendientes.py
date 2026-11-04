"""Facturas a pagar (03/11/2026): por proveedor solo las que explican el saldo real de la cuenta."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from src.features.cuentas_corrientes import repository as cuentas
from src.features.ordenes_pago import repository as repo


def _f(id_, fecha, saldo, vto=None):
    return {"idCompra": id_, "numero": f"0001-{id_:08d}", "fecha": fecha, "fechaVto": vto, "moneda": "Pesos", "tc": None,
            "total": saldo, "pagado": 0, "saldo": Decimal(str(saldo)), "reservado": Decimal(0), "disponible": Decimal(str(saldo))}


def test_ajusta_al_saldo_de_la_cuenta_y_ordena_por_vencimiento(monkeypatch):
    monkeypatch.setattr(cuentas, "get_saldos_todos", lambda: [
        {"idContacto": 1, "razonSocial": "Con pagos sin vincular", "saldoParcial": -150.0},
        {"idContacto": 2, "razonSocial": "En cero", "saldoParcial": 0.0},
        {"idContacto": 3, "razonSocial": "Al día", "saldoParcial": -100.0}])
    facturas = {1: [_f(10, date(2026, 1, 1), 300), _f(11, date(2026, 9, 1), 100), _f(12, date(2026, 10, 1), 100)],
                2: [_f(20, date(2026, 1, 1), 500)],
                3: [_f(30, date(2026, 8, 1), 100, vto=date(2026, 12, 31))]}
    monkeypatch.setattr(repo, "facturas", lambda c, *a: facturas[c])
    filas = repo._pendientes()
    # Proveedor 1 debe 150: la más nueva entera (100) y 50 de la anterior; la vieja de 300 se da por pagada.
    assert [(f["idCompra"], f["saldo"], f["ajustado"]) for f in filas if f["idContacto"] == 1] == \
        [(11, Decimal(50), True), (12, Decimal(100), True)]
    assert not [f for f in filas if f["idContacto"] == 2]  # cuenta en cero: nada que pagar
    assert filas[-1]["idCompra"] == 30 and filas[-1]["vencimiento"] == date(2026, 12, 31)  # orden por vencimiento
