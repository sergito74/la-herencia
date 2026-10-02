"""Ajustes internos de cuenta corriente y cobros de seguro en la vista (2026-10-01).

1. **`AjustesCuentaCorriente`**: documento interno para saldos iniciales y
   cierres de cuentas viejas, con motivo y usuario. Lado 'Deuda' (le
   debemos) o 'Credito' (nos debe o cancela deuda). Lo pidió Sergio para:
   - **Aquaro Agrorepuestos (76)**: saldo inicial de 2010 por $942,22.
   - **ASP (17)**: cierre de notas de ajuste que el proveedor nunca envió.
     Son $192.501,60, valuados al TC de cada factura. El proveedor ya no
     trabaja con la empresa.
2. **Vista `vw_MovimientosCuenta_Base`**: suma dos ramas nuevas.
   - **'Cobro Seguro'**: `Cultivos_Seguros_Cobros`, el módulo de Access para
     cobros de granizo. Cada cobro va en Crédito, como una venta, para el
     contacto de la póliza (`IdDeuda`). El cobro en el banco queda en Deuda.
   - **'Ajuste Interno'**: los ajustes de la tabla anterior.

Es idempotente y hace un respaldo verificado antes de cambiar algo.

Uso (desde backend/):  .venv/Scripts/python.exe -m scripts.ajustes_y_cobros_seguro_en_cuenta
"""

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc
from src.features.vinculos.backup import backup_verificado

DDL_TABLA = """
IF OBJECT_ID('dbo.AjustesCuentaCorriente', 'U') IS NULL
CREATE TABLE dbo.AjustesCuentaCorriente (
    IdAjuste   int IDENTITY(1,1) NOT NULL PRIMARY KEY,
    IdContacto int           NOT NULL,
    Fecha      date          NOT NULL,
    Lado       varchar(10)   NOT NULL CONSTRAINT CK_ACC_Lado CHECK (Lado IN ('Deuda', 'Credito')),
    Importe    money         NOT NULL CONSTRAINT CK_ACC_Importe CHECK (Importe > 0),
    Motivo     nvarchar(400) NOT NULL,
    Usuario    nvarchar(100) NOT NULL,
    FechaAlta  datetime2     NOT NULL DEFAULT SYSDATETIME()
)
"""

AJUSTES = [
    (76, "2010-04-19", "Deuda", 942.22,
     "Saldo inicial al comienzo de la administración en el sistema (2010). Confirmado por Sergio el 2026-10-01: "
     "hoy no se debe nada."),
    (17, "2016-07-31", "Credito", 192501.60,
     "Cierre de cuenta: notas de débito/crédito de ajuste que ASP nunca envió (documentos de 2014-2016). "
     "Proveedor inactivo. Aprobado por Sergio el 2026-10-01."),
]

RAMAS = """

UNION ALL

SELECT
    sc.FechaCobro AS Fecha,
    c.IdContacto,
    ct.[Razon Social],
    CAST('Cobro Seguro' AS varchar(50)) AS Documento,
    CAST(sc.NroSiniestro AS varchar(50)) AS [Nro Documento],
    CAST(0 AS money) AS Deuda,
    CAST(sc.ImportePesos AS money) AS Credito,
    CAST('Cobro Seguro' AS varchar(50)) AS Origen,
    CAST(sc.IdSeguroCobro AS bigint) AS IdOrigen
FROM dbo.Cultivos_Seguros_Cobros AS sc
INNER JOIN dbo.Compras AS c ON c.IdDeuda = sc.IdDeuda
INNER JOIN dbo.Contactos AS ct ON ct.IdContacto = c.IdContacto
WHERE ISNULL(sc.ImportePesos, 0) <> 0

UNION ALL

SELECT
    CAST(aj.Fecha AS datetime) AS Fecha,
    aj.IdContacto,
    ct.[Razon Social],
    CAST('Ajuste Interno' AS varchar(50)) AS Documento,
    CAST(aj.IdAjuste AS varchar(50)) AS [Nro Documento],
    CASE WHEN aj.Lado = 'Deuda' THEN aj.Importe ELSE CAST(0 AS money) END AS Deuda,
    CASE WHEN aj.Lado = 'Credito' THEN aj.Importe ELSE CAST(0 AS money) END AS Credito,
    CAST('Ajuste Interno' AS varchar(50)) AS Origen,
    CAST(aj.IdAjuste AS bigint) AS IdOrigen
FROM dbo.AjustesCuentaCorriente AS aj
INNER JOIN dbo.Contactos AS ct ON ct.IdContacto = aj.IdContacto
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
        falta_vista = "'Cobro Seguro'" not in definicion
        existe_tabla = cur.execute("SELECT OBJECT_ID('dbo.AjustesCuentaCorriente', 'U')").fetchone()[0] is not None
        cargados = set()
        if existe_tabla:
            cargados = {(r[0], round(float(r[1]), 2)) for r in cur.execute(
                "SELECT IdContacto, Importe FROM dbo.AjustesCuentaCorriente").fetchall()}
        faltan = [a for a in AJUSTES if (a[0], a[3]) not in cargados]
        if not falta_vista and not faltan:
            print("Nada para hacer: la vista y los ajustes ya están.")
            return
        print(f"Respaldo verificado: {backup_verificado('ajustes-cobros-seguro')}")
        cur.execute(DDL_TABLA)
        for id_contacto, fecha, lado, importe, motivo in faltan:
            cur.execute("INSERT INTO dbo.AjustesCuentaCorriente (IdContacto, Fecha, Lado, Importe, Motivo, Usuario) "
                        "VALUES (?, ?, ?, ?, ?, ?)", (id_contacto, fecha, lado, importe, motivo, "Sergio (vía Claude)"))
            print(f"Ajuste cargado: contacto {id_contacto}, {lado} ${importe:,.2f}")
        if falta_vista:
            if definicion.count(MARCA_FIN) != 1:
                raise RuntimeError("No se encontró el cierre de la unión en la vista.")
            nueva = definicion.replace(MARCA_FIN, RAMAS + MARCA_FIN).replace("CREATE VIEW", "ALTER VIEW", 1)
            cur.execute(nueva)
            print("Vista ampliada con cobros de seguro y ajustes internos.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
