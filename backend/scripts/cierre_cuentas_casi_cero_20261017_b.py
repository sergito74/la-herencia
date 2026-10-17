"""036 — Segunda parte del cierre de cuentas casi en cero (Sergio, 2026-10-17).

- Bidcom (522): +$2,52 prorrateado solo en el precio del producto comprado (contadora de billetes,
  factura 0014-00001421); descuento y cupón no se tocan.
- YPF Debenedetti (282): −$2,46 prorrateado en el ticket 07298-00041965 para que la cuenta cierre en 0.

Uso (desde backend/):  python -m scripts.cierre_cuentas_casi_cero_20261017_b [--aplicar]
"""

from __future__ import annotations

import sys

import pyodbc

from scripts.cierre_cuentas_casi_cero_20261017 import prorratear, saldo
from src.db.connection import CONNECTION_STRING, _assert_target_is_wc

CUENTAS = {522: "Bidcom", 282: "YPF Debenedetti"}


def aplicar() -> None:
    from src.features.vinculos.backup import backup_verificado

    # Los saldos se leen antes de abrir la transacción (la vista lee Det_Compras).
    deltas = {522: saldo(522), 282: saldo(282)}
    print("Respaldo verificado:", backup_verificado("cierre-casi-cero-036-b"))
    _assert_target_is_wc()
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=False)
    cur = conn.cursor()
    try:
        prorratear(cur, 2143514418, deltas[522], ("Descuento", "Cupon"))
        prorratear(cur, 2143515046, deltas[282], ())
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    antes = {c: saldo(c) for c in CUENTAS}
    if "--aplicar" in sys.argv:
        aplicar()
    for c, n in CUENTAS.items():
        print(f"{n:18} {antes[c]:>8,.2f} -> {saldo(c):>8,.2f}")
