"""Separa `Movimientos BNA` en sus 3 cuentas bancarias reales (2026-09-24).

Contexto: `Movimientos BNA` es un extracto único en WC que en realidad
mezcla movimientos de 3 cuentas del Banco Nación que se fueron
sucediendo en el tiempo (una se cerró y se abrió la siguiente). El
matching contra el Excel de origen (`Extracto Access.xlsm`, hojas
"Extracto Banco 01709/29280/11899") por clave (Fecha, Importe
redondeado, Concepto normalizado) + desempate posicional en las
ventanas de solape, ya fue validado en un turno anterior:
- 9.386 filas, 100% asignadas con CertezaCuenta='Alta', 0 Media/Baja.
- Distribución: 001709=1314, 029280=7263, 6150111899=809.
- Cierre de saldo de 001709 (apertura -24219.37 + suma importes)
  = -32.15, coincide exactamente con el cierre esperado (según el
  Excel de origen).

Ver script de matching (descartable, no forma parte del repo) que
generó `assignment_bna.json` en el scratchpad de la sesión que diseñó
esta migración.

Idempotente: crea la tabla `CuentasBancarias` solo si no existe, puebla
las cuentas solo si no existen (por Banco+NumeroCuenta), agrega las
columnas nuevas a `Movimientos BNA` solo si no existen, y solo actualiza
IdCuentaBancaria/CertezaCuenta en filas que todavía estén NULL (para
poder re-correr el script sin duplicar trabajo).

Nunca corre contra `LaHerencia` (`_assert_target_is_wc`).

Uso (desde backend/):  .venv\\Scripts\\python.exe -m scripts.separar_cuentas_bna
"""

import json
import os

import pyodbc

from src.db.connection import CONNECTION_STRING, DATABASE, _assert_target_is_wc

ASSIGNMENT_JSON = os.path.join(
    os.path.dirname(__file__), "..", "..", "docs", "migraciones", "assignment_bna.json"
)

DDL_CUENTAS_BANCARIAS = """
IF OBJECT_ID('dbo.CuentasBancarias', 'U') IS NULL
CREATE TABLE dbo.CuentasBancarias (
    IdCuentaBancaria      int           NOT NULL IDENTITY PRIMARY KEY,
    Banco                 varchar(30)   NOT NULL,
    NumeroCuenta          varchar(30)   NOT NULL,
    Alias                 nvarchar(80)  NULL,
    FechaApertura         datetime      NULL,
    FechaBaja             datetime      NULL,
    SaldoApertura          money         NOT NULL DEFAULT 0,
    Moneda                varchar(3)    NOT NULL DEFAULT 'ARS',
    FechaCreacionRegistro datetime2     NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_CuentasBancarias_Banco_Numero UNIQUE (Banco, NumeroCuenta)
)
"""

DDL_COLUMNAS_MOVIMIENTOS_BNA = """
IF COL_LENGTH('dbo.[Movimientos BNA]', 'IdCuentaBancaria') IS NULL
    ALTER TABLE dbo.[Movimientos BNA] ADD IdCuentaBancaria int NULL;
IF COL_LENGTH('dbo.[Movimientos BNA]', 'CertezaCuenta') IS NULL
    ALTER TABLE dbo.[Movimientos BNA] ADD CertezaCuenta varchar(10) NULL;
"""

DDL_FK_MOVIMIENTOS_BNA = """
IF NOT EXISTS (
    SELECT 1 FROM sys.foreign_keys WHERE name = 'FK_MovimientosBNA_CuentaBancaria'
)
ALTER TABLE dbo.[Movimientos BNA]
    ADD CONSTRAINT FK_MovimientosBNA_CuentaBancaria
    FOREIGN KEY (IdCuentaBancaria) REFERENCES dbo.CuentasBancarias (IdCuentaBancaria)
"""

# (Banco, NumeroCuenta, Alias, FechaApertura, FechaBaja, SaldoApertura, Moneda)
CUENTAS = [
    ("BNA", "12301640001709", "BNA 001709", "2010-08-31", "2012-06-29", -24219.37, "ARS"),
    ("BNA", "12301640029280", "BNA 029280", "2012-03-30", "2022-07-05", 0, "ARS"),
    ("BNA", "6150111899", "BNA 6150111899", "2022-02-25", None, 0, "ARS"),
    # Galicia: número de cuenta y saldo de apertura no confirmados en este
    # relevamiento (la tabla `Movimientos Galicia` no trae número de cuenta
    # en sus columnas). Se deja con SaldoApertura=0 hasta confirmar — no
    # bloquea esta migración, que es específicamente sobre BNA.
    ("Galicia", "PENDIENTE-CONFIRMAR", "Galicia (pendiente confirmar numero/saldo)", None, None, 0, "ARS"),
]

SQL_INSERT_CUENTA = """
IF NOT EXISTS (SELECT 1 FROM dbo.CuentasBancarias WHERE Banco = ? AND NumeroCuenta = ?)
INSERT INTO dbo.CuentasBancarias (Banco, NumeroCuenta, Alias, FechaApertura, FechaBaja, SaldoApertura, Moneda)
VALUES (?, ?, ?, ?, ?, ?, ?)
"""


def _crear_estructura(cursor) -> None:
    cursor.execute(DDL_CUENTAS_BANCARIAS)
    cursor.execute(DDL_COLUMNAS_MOVIMIENTOS_BNA)
    cursor.execute(DDL_FK_MOVIMIENTOS_BNA)


def _poblar_cuentas(cursor) -> dict:
    """Inserta las cuentas si faltan y devuelve NumeroCuenta -> IdCuentaBancaria."""
    for banco, numero, alias, apertura, baja, saldo, moneda in CUENTAS:
        cursor.execute(
            SQL_INSERT_CUENTA,
            (banco, numero, banco, numero, alias, apertura, baja, saldo, moneda),
        )
    cursor.execute("SELECT IdCuentaBancaria, Banco, NumeroCuenta FROM dbo.CuentasBancarias")
    return {(row[1], row[2]): row[0] for row in cursor.fetchall()}


def main() -> None:
    _assert_target_is_wc()

    with open(ASSIGNMENT_JSON, "r", encoding="utf-8") as f:
        assignment = json.load(f)
    # assignment: {"<IdMovimientoBNA>": {"cuenta": "001709"|"029280"|"6150111899", "certeza": "Alta"}}

    numero_por_clave = {
        "001709": "12301640001709",
        "029280": "12301640029280",
        "6150111899": "6150111899",
    }

    conn = pyodbc.connect(CONNECTION_STRING, autocommit=False)
    try:
        cursor = conn.cursor()
        _crear_estructura(cursor)
        ids_por_numero = _poblar_cuentas(cursor)
        conn.commit()

        id_por_cuenta = {
            clave: ids_por_numero[("BNA", numero_real)]
            for clave, numero_real in numero_por_clave.items()
        }

        actualizados = 0
        cursor.execute(
            "SELECT IdMovimientoBNA FROM dbo.[Movimientos BNA] WHERE IdCuentaBancaria IS NULL"
        )
        pendientes = {row[0] for row in cursor.fetchall()}

        for id_str, info in assignment.items():
            idmov = int(id_str)
            if idmov not in pendientes:
                continue
            cuenta = info["cuenta"]
            certeza = info["certeza"]
            if cuenta is None:
                continue
            id_cuenta = id_por_cuenta[cuenta]
            cursor.execute(
                "UPDATE dbo.[Movimientos BNA] SET IdCuentaBancaria = ?, CertezaCuenta = ? "
                "WHERE IdMovimientoBNA = ? AND IdCuentaBancaria IS NULL",
                (id_cuenta, certeza, idmov),
            )
            actualizados += cursor.rowcount
        conn.commit()
        print(f"OK: {actualizados} filas de 'Movimientos BNA' actualizadas en {DATABASE}.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
