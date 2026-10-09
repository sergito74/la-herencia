"""Amplía las marcas de pagos sin factura (036) para que un pago se pueda respaldar con una venta de hacienda o de granos.

Agrega `TipoVenta` ('venta-hacienda' | 'venta-granos') e `IdVenta` a `dbo.RevisionPagosSinFactura` y el estado `venta-cargada`
al CHECK de `Estado`. Idempotente: si ya está aplicado no hace nada. Con respaldo verificado antes de escribir. Opera solo sobre `WC`.

Uso (desde backend/):
    python -m scripts.ampliar_marcas_ventas_036 --verificar   # no escribe
    python -m scripts.ampliar_marcas_ventas_036               # respaldo verificado y cambio
"""

from __future__ import annotations

import sys

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc, fetch_all

NUEVO_CHECK = "CHECK (Estado IN ('pendiente', 'factura-cargada', 'sin-documento', 'anticipo', 'venta-cargada'))"


def _columnas() -> set[str]:
    return {f["c"] for f in fetch_all("SELECT COLUMN_NAME AS c FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'RevisionPagosSinFactura'")}


def _check_actual() -> str:
    filas = fetch_all("SELECT definition AS d FROM sys.check_constraints WHERE name = 'CK_RevisionPagosSinFactura_Estado'")
    return filas[0]["d"] if filas else ""


def pendiente() -> list[str]:
    cols = _columnas()
    faltan = [c for c in ("TipoVenta", "IdVenta") if c not in cols]
    if "venta-cargada" not in _check_actual():
        faltan.append("CHECK de Estado")
    return faltan


def main(verificar: bool) -> None:
    _assert_target_is_wc()
    faltan = pendiente()
    print("Falta aplicar:", faltan or "nada (ya está aplicado)")
    if verificar or not faltan:
        return
    from src.features.vinculos.backup import backup_verificado
    print(f"Respaldo verificado: {backup_verificado('ampliar-marcas-ventas-036')}")
    cols = _columnas()
    check_ok = "venta-cargada" in _check_actual()  # se lee antes de abrir la transacción: dentro se bloquearía a sí mismo
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=False)
    try:
        cur = conn.cursor()
        if cur.execute("SELECT DB_NAME()").fetchone()[0] != "WC":
            raise RuntimeError("Solo sobre WC")
        if "TipoVenta" not in cols:
            cur.execute("ALTER TABLE dbo.RevisionPagosSinFactura ADD TipoVenta varchar(20) NULL")
        if "IdVenta" not in cols:
            cur.execute("ALTER TABLE dbo.RevisionPagosSinFactura ADD IdVenta int NULL")
        if not check_ok:
            cur.execute("ALTER TABLE dbo.RevisionPagosSinFactura DROP CONSTRAINT CK_RevisionPagosSinFactura_Estado")
            cur.execute(f"ALTER TABLE dbo.RevisionPagosSinFactura ADD CONSTRAINT CK_RevisionPagosSinFactura_Estado {NUEVO_CHECK}")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    print("Falta ahora:", pendiente() or "nada")


if __name__ == "__main__":
    main(verificar="--verificar" in sys.argv)
