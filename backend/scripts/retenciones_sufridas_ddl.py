"""Retenciones y percepciones sufridas por Giamigli (pago a cuenta de impuestos), 19/11/2026.

Sergio pidió cargar las 5 percepciones de Ganancias (impuesto 217) que el Banco Galicia (CUIT 30500001735) le practicó a
Giamigli entre el 20/09/2023 y el 15/11/2023. Fuente: ARCA, "Mis Retenciones" (clave de Lucy, representando a Giamigli),
consultado el 19/11/2026 en modo lectura. Idempotente; respaldo verificado antes de escribir.
Uso (desde backend/):  python -m scripts.retenciones_sufridas_ddl
"""
import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc
from src.features.vinculos.backup import backup_verificado

DDL = """
IF OBJECT_ID('dbo.RetencionesSufridas', 'U') IS NULL
CREATE TABLE dbo.RetencionesSufridas (
    IdRetencionSufrida int IDENTITY(1,1) NOT NULL PRIMARY KEY,
    Impuesto      int           NOT NULL,          -- 217 = Ganancias (SICORE)
    Regimen       int           NULL,
    Tipo          varchar(20)   NOT NULL,          -- RETENCION | PERCEPCION
    CuitAgente    varchar(11)   NOT NULL,
    IdContactoAgente int        NULL,
    Fecha         date          NOT NULL,
    Certificado   nvarchar(40)  NULL,
    Comprobante   nvarchar(40)  NULL,
    Importe       money         NOT NULL CONSTRAINT CK_RetSuf_Importe CHECK (Importe > 0),
    Fuente        nvarchar(300) NOT NULL,
    Usuario       nvarchar(100) NOT NULL,
    FechaAlta     datetime2     NOT NULL DEFAULT SYSDATETIME(),
    CONSTRAINT UQ_RetSuf UNIQUE (CuitAgente, Impuesto, Certificado)
)
"""
FUENTE = "ARCA Mis Retenciones (representando a Giamigli), consulta del 19/11/2026"
CARGA = [  # régimen, fecha, certificado, importe, comprobante
    (592, "2023-09-20", "2076854", 33210.00, "0000000112195480"),
    (517, "2023-10-12", "7257500", 18450.00, "0000000151405049"),
    (592, "2023-10-12", "2876644", 33210.00, "0000000151405049"),
    (517, "2023-11-15", "6542609", 18600.00, "0000000121389977"),
    (592, "2023-11-15", "6542610", 33480.00, "0000000121389977"),
]


def main() -> None:
    _assert_target_is_wc()
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=True)
    try:
        cur = conn.cursor()
        if cur.execute("SELECT DB_NAME()").fetchone()[0] != "WC":
            raise RuntimeError("Solo sobre WC")
        existe = cur.execute("SELECT OBJECT_ID('dbo.RetencionesSufridas', 'U')").fetchone()[0] is not None
        hechos = {r[0] for r in cur.execute("SELECT Certificado FROM dbo.RetencionesSufridas").fetchall()} if existe else set()
        faltan = [c for c in CARGA if c[2] not in hechos]
        if not faltan:
            print("Nada para hacer.")
            return
        print(f"Respaldo verificado: {backup_verificado('retenciones-sufridas')}")
        cur.execute(DDL)
        galicia = cur.execute("SELECT TOP 1 IdContacto FROM dbo.Contactos WHERE [Razon Social] = 'Banco Galicia'").fetchone()
        for reg, fecha, cert, imp, comp in faltan:
            cur.execute("INSERT INTO dbo.RetencionesSufridas (Impuesto, Regimen, Tipo, CuitAgente, IdContactoAgente, Fecha, Certificado, "
                        "Comprobante, Importe, Fuente, Usuario) VALUES (217, ?, 'PERCEPCION', '30500001735', ?, ?, ?, ?, ?, ?, ?)",
                        (reg, galicia[0] if galicia else None, fecha, cert, comp, imp, FUENTE, "Sergio (vía Claude)"))
            print(f"Cargada: {fecha} régimen {reg} certificado {cert} $ {imp:,.2f}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
