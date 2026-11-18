"""18/11/2026: tabla de pagos de liquidaciones de sueldo. Vincula cada liquidación con el egreso que la pagó (asiento
del socio, débito del banco de Giamigli u operación de caja). Un mismo egreso puede pagar varias liquidaciones.
Solo WC. Re-corrible."""

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
            IF OBJECT_ID('dbo.RemuneracionesPagos') IS NULL
            CREATE TABLE dbo.RemuneracionesPagos (
                IdPagoRemuneracion int IDENTITY(1,1) PRIMARY KEY,
                IdSalario int NOT NULL,
                Medio varchar(10) NOT NULL,
                IdMovimientoSocio int NULL,
                IdMovimientoBanco int NULL,
                IdOperacion int NULL,
                Fecha date NOT NULL,
                Importe decimal(18,2) NOT NULL,
                Usuario nvarchar(100) NOT NULL,
                Creado datetime2 NOT NULL CONSTRAINT DF_RemuneracionesPagos_Creado DEFAULT SYSDATETIME(),
                CONSTRAINT CK_RemuneracionesPagos_Medio CHECK (Medio IN ('socio','galicia','bna','caja'))
            )""")
        cur.execute("IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_RemuneracionesPagos_Salario') "
                    "CREATE INDEX IX_RemuneracionesPagos_Salario ON dbo.RemuneracionesPagos (IdSalario)")
        conn.commit()
        print("ok")


if __name__ == "__main__":
    main()
