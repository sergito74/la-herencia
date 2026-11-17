"""050 (17/11/2026): precio del proveedor para los remitos todavía sin factura (Bayá Casal, Insumos → mercadería
remitida pendiente de facturar: artículo, cantidad, TC y precio en US$). Valoriza el remito mientras no llega la factura,
sin cargar una compra provisoria: cuando se vincula la factura, manda su precio. Solo WC. Re-corrible.
"""
from __future__ import annotations

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc


def main() -> None:
    _assert_target_is_wc()
    with pyodbc.connect(CONNECTION_STRING) as conn:
        cur = conn.cursor()
        if cur.execute("SELECT DB_NAME()").fetchone()[0] != "WC":
            raise RuntimeError("Solo WC")
        cur.execute("""
            IF OBJECT_ID('dbo.RemitoValorProveedor') IS NULL
            CREATE TABLE dbo.RemitoValorProveedor (
                IdDetalleRemito int NOT NULL PRIMARY KEY,
                Fuente nvarchar(40) NOT NULL,
                Articulo nvarchar(200) NULL,
                Cantidad decimal(18,4) NULL,
                PrecioUSD decimal(18,6) NOT NULL,
                TipoCambio decimal(18,4) NOT NULL,
                FechaConsulta datetime2 NOT NULL CONSTRAINT DF_RemitoValorProveedor_Fecha DEFAULT SYSDATETIME()
            )""")
        conn.commit()
        print("ok")


if __name__ == "__main__":
    main()
