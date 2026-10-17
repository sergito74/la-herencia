"""036 — Cierre de Pavón Arriba Cereales (508), 17/10/2026 (decisión de Sergio).

Venta directa 00003-00000012 (28/06/2023, 7 vacas de invernada desde San Pedro, 2.590 kg): A $445.480 + IVA 10,5 %
= $492.255,40 (cobrado por BNA en dos transferencias) y B $111.370 (cobrada en efectivo el 05/08/2023).
- La liquidación no tiene comisión: se saca el 2,5 % cargado en la venta.
- La parte B se cobró completa: el cobro en efectivo de Pavón pasa de $100.250 a $111.370.
- Los $11.120 que salieron de esa caja el mismo día (egreso "Pago proveedor", movimiento 1361 de Pagos efectivo) fueron la
  comisión de un intermediario no identificado (Sergio, 17/10/2026); quedan como están.

Uso (desde backend/): python -m scripts.cierre_pavon_20261017
"""

from __future__ import annotations

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc, fetch_all
from src.features.revision_cuentas import evidencia, fichas
from src.features.vinculos.backup import backup_verificado

U = "Sergio (036, Pavón 2026-10-17)"
C, VENTA = 508, 101


def saldo() -> float:
    return round(float(fetch_all("SELECT SUM(ISNULL(Credito,0)-ISNULL(Deuda,0)) s FROM dbo.vw_MovimientosCuenta_Base WHERE IdContacto=?",
                                 (C,))[0]["s"] or 0), 2)


if __name__ == "__main__":
    print("Saldo antes:", saldo())
    print("Respaldo verificado:", backup_verificado("cierre-pavon-036"))
    _assert_target_is_wc()
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=False)
    cur = conn.cursor()
    try:
        cur.execute("UPDATE dbo.[Venta Hacienda] SET [Porc Comision] = 0 WHERE IdVenta = ? AND [Porc Comision] = 2.5", VENTA)
        assert cur.rowcount == 1
        cur.execute("UPDATE dbo.[Pagos efectivo] SET [Importe imputado] = -111370.00 WHERE IdPagoEfectivo = 495 "
                    "AND IdContacto = ? AND [Importe imputado] = -100250.00", C)
        assert cur.rowcount == 1
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    print("Saldo después:", saldo())
    for medio, mov in (("bna", 18626), ("bna", 18627), ("efectivo", 495)):
        evidencia.guardar_marca(C, medio, mov, "venta-cargada", None, None,
                                "Cobro de la venta directa 00003-00000012 (cierre 17/10/2026)", U, "venta-hacienda", VENTA)
    fichas.confirmar_inventario(C, [{"tipo": "dropbox", "disponible": True, "detalle": "Liquidación de venta directa 00003-12 (PDF)"},
                                    {"tipo": "extracto", "disponible": True, "detalle": "BNA 28/07 y 28/08/2023; caja La Herencia 05/08/2023"}], U)
    f = fichas.cambiar_estado(C, {"estado": "cerrada", "nota": "Venta directa sin comisión (se sacó el 2,5 %); parte B cobrada completa "
                                  "($111.370). Los $11.120 del egreso de caja del 05/08/2023 fueron la comisión de un intermediario no "
                                  "identificado. Decisión de Sergio 17/10/2026."}, U)
    print(f["estado"], f.get("saldoAlCorte"))
