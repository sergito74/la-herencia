"""Pagos de trabajos eventuales desde una caja (04/11/2026): vincula cada trabajo con su pago: en efectivo (operación "pago" de la caja,
que descuenta el saldo) o por transferencia (movimiento del banco ya cargado). Sin recibo obligatorio. Re-corrible. Uso: python -m scripts.trabajos_eventuales_pagos_047"""

from src.db.connection import get_connection

SQL = """IF OBJECT_ID('dbo.TrabajosEventualesPagos','U') IS NULL CREATE TABLE dbo.TrabajosEventualesPagos (
    IdPagoTrabajo int IDENTITY(1,1) PRIMARY KEY,
    IdTrabajo int NOT NULL REFERENCES dbo.TrabajosEventuales(IdTrabajo),
    Medio varchar(20) NOT NULL,              -- 'caja' (efectivo) | 'galicia' | 'bna' (transferencia ya cargada del extracto)
    IdOperacion bigint NULL REFERENCES dbo.OperacionesCajaEfectivo(IdOperacion),
    IdMovimientoBanco int NULL,
    Caja varchar(40) NULL,
    Fecha date NOT NULL,
    Importe decimal(19,2) NOT NULL,
    Usuario nvarchar(100) NOT NULL,
    Creado datetime2 NOT NULL DEFAULT SYSDATETIME(),
    CONSTRAINT CK_TrabajosEventualesPagos_Medio CHECK (
        (Medio='caja' AND IdOperacion IS NOT NULL) OR (Medio IN ('galicia','bna') AND IdMovimientoBanco IS NOT NULL)))"""

# 04/11/2026: las transferencias las hacen los socios desde sus cuentas, no Giamigli -> medio 'socio'.
SQL_SOCIO = [
    "IF COL_LENGTH('dbo.TrabajosEventualesPagos','IdMovimientoSocio') IS NULL "
    "ALTER TABLE dbo.TrabajosEventualesPagos ADD IdMovimientoSocio int NULL",
    "IF OBJECT_ID('dbo.CK_TrabajosEventualesPagos_Medio','C') IS NOT NULL "
    "ALTER TABLE dbo.TrabajosEventualesPagos DROP CONSTRAINT CK_TrabajosEventualesPagos_Medio",
    "ALTER TABLE dbo.TrabajosEventualesPagos ADD CONSTRAINT CK_TrabajosEventualesPagos_Medio CHECK ("
    "(Medio='caja' AND IdOperacion IS NOT NULL) OR (Medio IN ('galicia','bna') AND IdMovimientoBanco IS NOT NULL) "
    "OR (Medio='socio' AND IdMovimientoSocio IS NOT NULL))",
]

if __name__ == "__main__":
    with get_connection() as conn:
        conn.cursor().execute(SQL)
        conn.commit()
        for sql in SQL_SOCIO:
            conn.cursor().execute(sql)
            conn.commit()
    print("ok")
