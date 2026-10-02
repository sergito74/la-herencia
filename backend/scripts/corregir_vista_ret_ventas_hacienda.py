"""Corrige el lado de las retenciones de ventas de hacienda en vw_MovimientosCuenta_Base (2026-10-01).

La retención que practica el consignatario sobre una venta de hacienda
reduce lo que nos debe, igual que un cobro, así que va del lado Deuda. La
vista la ponía en Crédito, el mismo lado que la venta, y la cuenta quedaba
descuadrada por el doble de la retención.

Con la corrección, 5 cuentas pasan a saldo 0 exacto: Agropecuaria Bienvenidos,
Sarciat Gómez, San Carlos Pirovano, Explotación del Río Bermejo y Swift
(0,28). Es idempotente y hace un respaldo verificado antes de cambiar la vista.

Uso (desde backend/):  .venv/Scripts/python.exe -m scripts.corregir_vista_ret_ventas_hacienda
"""

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc
from src.features.vinculos.backup import backup_verificado

ANTES = """    CAST(0 AS money) AS Deuda,
    CAST(rvh.Importe AS money) AS Credito,
    CAST('Ret. Ventas Hacienda' AS varchar(50)) AS Origen,"""
DESPUES = """    CAST(rvh.Importe AS money) AS Deuda,
    CAST(0 AS money) AS Credito,
    CAST('Ret. Ventas Hacienda' AS varchar(50)) AS Origen,"""


def main() -> None:
    _assert_target_is_wc()
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=True)
    try:
        cur = conn.cursor()
        if cur.execute("SELECT DB_NAME()").fetchone()[0] != "WC":
            raise RuntimeError("Solo sobre WC")
        definicion = cur.execute("SELECT OBJECT_DEFINITION(OBJECT_ID('dbo.vw_MovimientosCuenta_Base'))").fetchone()[0]
        definicion = definicion.replace("\r\n", "\n")
        if DESPUES in definicion:
            print("La vista ya está corregida.")
            return
        if definicion.count(ANTES) != 1:
            raise RuntimeError("No se encontró exactamente un bloque de Ret. Ventas Hacienda para corregir.")
        print(f"Respaldo verificado: {backup_verificado('vista-ret-ventas-hacienda')}")
        nueva = definicion.replace(ANTES, DESPUES).replace("CREATE VIEW", "ALTER VIEW", 1)
        cur.execute(nueva)
        print("Vista corregida.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
