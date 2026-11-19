"""Retenciones de Ganancias sufridas en inversiones (19/11/2026, Inversiones etapa 2).

El banco descuenta la retención del interés antes de acreditarlo; no aparece como movimiento. Es pago a cuenta de
Ganancias de la sociedad. Se cargan las que constan en documentos (constancias del plazo fijo / liquidación SICORE).
Las constancias del Nación desde 2018 dicen "RETENCIONES: 0,00".

Es idempotente y hace un respaldo verificado antes de cambiar algo.
Uso (desde backend/):  python -m scripts.inversiones_retenciones_ddl
"""
import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc
from src.features.vinculos.backup import backup_verificado

DDL = """
IF OBJECT_ID('dbo.InversionesRetenciones', 'U') IS NULL
CREATE TABLE dbo.InversionesRetenciones (
    IdRetencion   int IDENTITY(1,1) NOT NULL PRIMARY KEY,
    Cuenta        nvarchar(40)  NOT NULL,   -- 'Plazo fijo Nación' | 'Plazo fijo Galicia' | 'Fondo Fima'
    Medio         varchar(20)   NOT NULL,   -- bna | galicia
    IdMovimiento  int           NULL,       -- acreditación del banco a la que corresponde
    Certificado   nvarchar(40)  NULL,
    Fecha         date          NOT NULL,
    Importe       money         NOT NULL CONSTRAINT CK_InvRet_Importe CHECK (Importe > 0),
    Fuente        nvarchar(300) NOT NULL,
    Usuario       nvarchar(100) NOT NULL,
    FechaAlta     datetime2     NOT NULL DEFAULT SYSDATETIME()
)
"""

CARGA = [
    ("Plazo fijo Nación", "bna", 12178, "5983", "2016-11-03", 117.95,
     "Comprobantes/Giamigli/2016/Plazos Fijos/20160921_PlazoFijoBNA.pdf (SICORE 010 0048340981)"),
    ("Plazo fijo Galicia", "galicia", 1446, "809257500586", "2023-10-05", 10947.95,
     "Dropbox/Bancos/Galicia/Plazos Fijos/comprobante_169776488.pdf"),
    ("Plazo fijo Galicia", "galicia", 2054, "809259034553", "2023-10-12", 12316.44,
     "Dropbox/Bancos/Galicia/Plazos Fijos/PlazoFijo_Comprobante_170601523.pdf (primer tramo; renovado hasta el 14/08/2024)"),
    ("Plazo fijo Galicia", "galicia", 1541, "809263965018", "2023-11-10", 4926.58,
     "Dropbox/Bancos/Galicia/Plazos Fijos/PlazoFijo_Comprobante_173911553.pdf"),
]


def main() -> None:
    _assert_target_is_wc()
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=True)
    try:
        cur = conn.cursor()
        if cur.execute("SELECT DB_NAME()").fetchone()[0] != "WC":
            raise RuntimeError("Solo sobre WC")
        existe = cur.execute("SELECT OBJECT_ID('dbo.InversionesRetenciones', 'U')").fetchone()[0] is not None
        cargados = set()
        if existe:
            cargados = {(r[0], str(r[1])) for r in cur.execute("SELECT Certificado, Fecha FROM dbo.InversionesRetenciones").fetchall()}
        faltan = [c for c in CARGA if (c[3], c[4]) not in cargados]
        if existe and not faltan:
            print("Nada para hacer.")
            return
        print(f"Respaldo verificado: {backup_verificado('inversiones-retenciones')}")
        cur.execute(DDL)
        for cuenta, medio, idm, cert, fecha, imp, fuente in faltan:
            cur.execute("INSERT INTO dbo.InversionesRetenciones (Cuenta, Medio, IdMovimiento, Certificado, Fecha, Importe, Fuente, Usuario) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (cuenta, medio, idm, cert, fecha, imp, fuente, "Sergio (vía Claude)"))
            print(f"Cargada: {cuenta} {cert} {fecha} $ {imp:,.2f}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
