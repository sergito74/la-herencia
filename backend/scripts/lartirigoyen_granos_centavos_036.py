"""036 — Lartirigoyen (61), 28/10/2026: seis ventas de granos con $0,01 de más respecto del importe de la LPG con que Lartirigoyen
las acreditó (TCC 34987, 35178, 36138, 37375, 54515 y 55869). Se ajustan al centavo de la LPG. Idempotente.

Uso (desde backend/): python -m scripts.lartirigoyen_granos_centavos_036
"""

from __future__ import annotations

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all
from src.features.vinculos.backup import backup_verificado

C = 61
LPG = {88: 384918.63, 91: 9096.29, 94: 202168.32, 96: 3986.10, 111: 284736.25, 113: 6728.81}


def credito(id_venta: int) -> float:
    return fetch_all("SELECT ROUND(Credito, 2) c FROM dbo.vw_MovimientosCuenta_Saldo WHERE IdContacto = ? AND Origen = 'Venta Granos' "
                     "AND IdOrigen = ?", (C, id_venta))[0]["c"]


if __name__ == "__main__":
    _assert_target_is_wc()
    st = []
    for v, objetivo in LPG.items():
        dif = round(objetivo - credito(v), 2)
        if abs(dif) < 0.005:
            continue
        iva = float(fetch_all("SELECT AlicuotaIVA a FROM dbo.[Venta Granos] WHERE IdVenta = ?", (v,))[0]["a"] or 0)
        if iva == 0:  # el crédito es el ajuste "A cuenta de calidad": se corrige ese importe
            st.append(("UPDATE dbo.[Venta Granos_Ajustes] SET Importe = Importe + ? WHERE IdVenta = ? AND Concepto LIKE 'A cuenta de calidad'",
                       (dif, v)))
        else:
            st.append(("INSERT INTO dbo.[Venta Granos_Ajustes] (IdVenta, Concepto, Importe, AlicuotaIVA) VALUES (?, 'Redondeo segun LPG', ?, 0)",
                       (v, round(dif / (1 + iva / 100), 4))))
    if not st:
        raise SystemExit("Nada que corregir.")
    print("Respaldo verificado:", backup_verificado("lartirigoyen-granos-centavos-036"))
    execute_write_transaction(st)
    for v, objetivo in LPG.items():
        print(v, "LPG", objetivo, "WC", credito(v))
    print("Saldo:", fetch_all("SELECT ROUND(SUM(Credito - Deuda), 2) s FROM dbo.vw_MovimientosCuenta_Saldo WHERE IdContacto = ?", (C,))[0]["s"])
