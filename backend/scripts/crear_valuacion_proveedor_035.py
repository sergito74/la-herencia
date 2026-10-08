"""035 — Tabla `ValuacionProveedor`: los dólares que el proveedor acreditó o debitó en su propio libro por una fila de la cuenta.

La pesificación de los proveedores no tiene un criterio unificado (decisión de Sergio, 08/10/2026): cada proveedor convierte
a dólares con su propio tipo de cambio (el de la factura, el del vencimiento de un cheque, el de la venta, etc.). Cuando se
tiene su libro en dólares, se carga acá la cifra que él usó para una fila (un pago, una liquidación, una nota) y el motor
bimonetario la respeta en vez de convertir con el dólar BNA. No toca los pesos.

Uso (desde backend/):
    python -m scripts.crear_valuacion_proveedor_035 --verificar   # no escribe
    python -m scripts.crear_valuacion_proveedor_035               # respaldo verificado y creación
"""

from __future__ import annotations

import sys

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc

DDL = """
IF OBJECT_ID('dbo.ValuacionProveedor', 'U') IS NULL
CREATE TABLE dbo.ValuacionProveedor (
    Origen varchar(50) NOT NULL,
    IdOrigen bigint NOT NULL,
    IdContacto int NOT NULL,
    Dolares money NOT NULL,
    Fuente varchar(200) NULL,
    Nota nvarchar(400) NULL,
    Usuario varchar(60) NULL,
    Fecha datetime2 NOT NULL CONSTRAINT DF_ValuacionProveedor_Fecha DEFAULT SYSDATETIME(),
    CONSTRAINT PK_ValuacionProveedor PRIMARY KEY (Origen, IdOrigen)
)
"""


def main(solo_verificar: bool) -> None:
    _assert_target_is_wc()
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=True)
    try:
        cur = conn.cursor()
        if cur.execute("SELECT DB_NAME()").fetchone()[0] != "WC":
            raise RuntimeError("Solo sobre WC")
        existe = cur.execute("SELECT OBJECT_ID('dbo.ValuacionProveedor', 'U')").fetchone()[0] is not None
        print("La tabla ValuacionProveedor", "ya existe." if existe else "no existe todavía.")
        if solo_verificar or existe:
            return
        from src.features.vinculos.backup import backup_verificado

        print(f"Respaldo verificado: {backup_verificado('valuacion-proveedor-035')}")
        cur.execute(DDL)
        print("Tabla creada.")
    finally:
        conn.close()


if __name__ == "__main__":
    main("--verificar" in sys.argv)
