"""Consumos de tarjeta sin imputar en la cuenta corriente (2026-10-01).

`vw_MovimientosCuenta_Base` solo veía los consumos de tarjeta ya imputados
a una factura (`Tarjetas_Resumenes_Lineas_Compras`). Un consumo con
proveedor asignado pero sin imputar es un pago real a ese proveedor, y no
aparecía en ninguna cuenta. Afectaba a 21 proveedores (Lartirigoyen,
Galicia Seguros, ASP, Neumáticos Corral, entre otros).

Se agrega una rama 'Tarjeta sin imputar'. En cuanto el consumo se imputa,
deja de salir por esta rama y sale por la de 'Tarjetas', así que no se
duplica. Es idempotente y hace un respaldo verificado antes del cambio.

Uso (desde backend/):  .venv/Scripts/python.exe -m scripts.vista_tarjeta_sin_imputar
"""

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc
from src.features.vinculos.backup import backup_verificado

RAMA = """

UNION ALL

SELECT
    l.FechaCompra AS Fecha,
    l.IdContacto,
    ct.[Razon Social],
    CAST('Tarjeta sin imputar' AS varchar(50)) AS Documento,
    CAST(rs.ResumenCodigo AS varchar(50)) AS [Nro Documento],
    CASE WHEN l.Importe < 0 THEN -l.Importe ELSE CAST(0 AS money) END AS Deuda,
    CASE WHEN l.Importe > 0 THEN l.Importe ELSE CAST(0 AS money) END AS Credito,
    CAST('Tarjeta sin imputar' AS varchar(50)) AS Origen,
    CAST(l.IdLineaConsumo AS bigint) AS IdOrigen
FROM dbo.Tarjetas_Resumenes_Lineas AS l
INNER JOIN dbo.Contactos AS ct ON ct.IdContacto = l.IdContacto
LEFT JOIN dbo.Tarjetas_Resumenes AS rs ON rs.IdResumen = l.IdResumen
WHERE ISNULL(l.Importe, 0) <> 0
  AND NOT EXISTS (SELECT 1 FROM dbo.Tarjetas_Resumenes_Lineas_Compras lc WHERE lc.IdLineaConsumo = l.IdLineaConsumo)
"""

MARCA_FIN = "\n\n) AS base\nOUTER APPLY ("


def main() -> None:
    _assert_target_is_wc()
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=True)
    try:
        cur = conn.cursor()
        if cur.execute("SELECT DB_NAME()").fetchone()[0] != "WC":
            raise RuntimeError("Solo sobre WC")
        definicion = cur.execute("SELECT OBJECT_DEFINITION(OBJECT_ID('dbo.vw_MovimientosCuenta_Base'))").fetchone()[0]
        definicion = definicion.replace("\r\n", "\n")
        if "'Tarjeta sin imputar'" in definicion:
            print("La vista ya incluye los consumos sin imputar.")
            return
        if definicion.count(MARCA_FIN) != 1:
            raise RuntimeError("No se encontró el cierre de la unión en la vista.")
        print(f"Respaldo verificado: {backup_verificado('vista-tarjeta-sin-imputar')}")
        cur.execute(definicion.replace(MARCA_FIN, RAMA + MARCA_FIN).replace("CREATE VIEW", "ALTER VIEW", 1))
        print("Vista ampliada con consumos de tarjeta sin imputar.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
