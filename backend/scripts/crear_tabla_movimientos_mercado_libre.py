"""Crea la cuenta y la tabla de movimientos de Mercado Libre (2026-09-26).

Mercado Libre/Mercado Pago es una cuenta virtual (CVU) más de la empresa,
usada para transferencias y algún pago de servicio — corresponde tratarla
como una cuenta bancaria más, igual que BNA/Galicia (`CuentasBancarias`,
`separar_cuentas_bna.py`).

A diferencia de BNA/Galicia, acá no hay flujo de carga por Excel: el banco
sólo exporta resúmenes en PDF (`cargar_resumenes_mercado_libre_pdf.py` los
parsea e inserta). Este script solo crea la estructura (idempotente:
`IF OBJECT_ID(...) IS NULL` / `IF NOT EXISTS`).

Uso (desde backend/):  .venv\\Scripts\\python.exe -m scripts.crear_tabla_movimientos_mercado_libre
"""

from __future__ import annotations

import pyodbc

from src.db.connection import CONNECTION_STRING, DATABASE, _assert_target_is_wc

CVU_MERCADO_LIBRE = "0000003100045405413930"

DDL_TABLA = """
IF OBJECT_ID('dbo.[Movimientos Mercado Libre]', 'U') IS NULL
CREATE TABLE dbo.[Movimientos Mercado Libre] (
    IdMovimiento          int           NOT NULL IDENTITY PRIMARY KEY,
    Fecha                 date          NOT NULL,
    Descripcion           nvarchar(255) NULL,
    IdOperacion           varchar(20)   NULL,
    Importe               money         NOT NULL,
    Saldo                 money         NULL,
    IdCuentaBancaria       int           NOT NULL,
    IdContacto            int           NULL,
    FechaCreacionRegistro datetime2     NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_MovimientosMercadoLibre_Clave
        UNIQUE (Fecha, IdOperacion, Importe, Saldo),
    CONSTRAINT FK_MovimientosMercadoLibre_CuentaBancaria
        FOREIGN KEY (IdCuentaBancaria) REFERENCES dbo.CuentasBancarias (IdCuentaBancaria),
    CONSTRAINT FK_MovimientosMercadoLibre_Contacto
        FOREIGN KEY (IdContacto) REFERENCES dbo.Contactos (IdContacto)
)
"""

SQL_INSERT_CUENTA = """
IF NOT EXISTS (SELECT 1 FROM dbo.CuentasBancarias WHERE Banco = ? AND NumeroCuenta = ?)
INSERT INTO dbo.CuentasBancarias (Banco, NumeroCuenta, Alias, SaldoApertura, Moneda)
VALUES (?, ?, ?, ?, ?)
"""


def main() -> None:
    _assert_target_is_wc()

    conn = pyodbc.connect(CONNECTION_STRING, autocommit=False)
    try:
        cursor = conn.cursor()
        cursor.execute(
            SQL_INSERT_CUENTA,
            (
                "Mercado Libre",
                CVU_MERCADO_LIBRE,
                "Mercado Libre",
                CVU_MERCADO_LIBRE,
                "Mercado Libre (CVU)",
                0,
                "ARS",
            ),
        )
        cursor.execute(DDL_TABLA)
        conn.commit()
        cursor.execute(
            "SELECT IdCuentaBancaria FROM dbo.CuentasBancarias WHERE Banco = ? AND NumeroCuenta = ?",
            ("Mercado Libre", CVU_MERCADO_LIBRE),
        )
        id_cuenta = cursor.fetchone()[0]
        print(f"OK: cuenta Mercado Libre (IdCuentaBancaria={id_cuenta}) y tabla lista en {DATABASE}.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
