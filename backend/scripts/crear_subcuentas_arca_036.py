"""Crear metadatos analíticos ARCA sobre WC con respaldo verificado; no mueve dinero."""
import json
from pathlib import Path
import sys
import pyodbc

from src.db.connection import _assert_target_is_wc, CONNECTION_STRING
from src.features.cajas_efectivo.operaciones import read
from src.features.vinculos.backup import backup_verificado

DDL = """IF OBJECT_ID('dbo.ArcaClasificaciones','U') IS NULL
BEGIN
 CREATE TABLE dbo.ArcaClasificaciones (
  IdClasificacion int IDENTITY(1,1) NOT NULL PRIMARY KEY,
  Origen nvarchar(80) NOT NULL, IdOrigen int NOT NULL,
  Reparto nvarchar(max) NOT NULL CHECK(ISJSON(Reparto)=1),
  Motivo nvarchar(500) NOT NULL, Usuario nvarchar(100) NOT NULL,
  Fecha datetime2 NOT NULL DEFAULT SYSDATETIME()
 );
 CREATE INDEX IX_ArcaClasificaciones_Origen ON dbo.ArcaClasificaciones(Origen,IdOrigen,IdClasificacion DESC);
END"""


def estado():
    return read("SELECT COUNT(*) cantidad,SUM(Credito-Deuda) saldo FROM dbo.vw_MovimientosCuenta_Base WHERE IdContacto=119")


def main():
    _assert_target_is_wc()
    existe = read("SELECT OBJECT_ID('dbo.ArcaClasificaciones','U') id")[0]["id"]
    if existe or "--aplicar" not in sys.argv:
        print(json.dumps({"existe": bool(existe), "arca": estado()}, default=str))
        return
    antes = estado()
    backup = backup_verificado("arca-subcuentas-036")
    with pyodbc.connect(CONNECTION_STRING, autocommit=True) as conn:
        cur = conn.cursor()
        if cur.execute("SELECT DB_NAME()").fetchone()[0] != "WC":
            raise RuntimeError("Solo WC")
        cur.execute("BEGIN TRANSACTION")
        try:
            cur.execute(DDL)
            cur.execute("COMMIT TRANSACTION")
        except Exception:
            cur.execute("IF @@TRANCOUNT>0 ROLLBACK TRANSACTION")
            raise
    despues = estado()
    if antes != despues:
        raise RuntimeError("El saldo o la cantidad de ARCA cambió durante la creación; revisar concurrencia")
    result = {"backup": backup, "antes": antes, "despues": despues, "sinCambiosContables": True}
    p = Path(__file__).resolve().parents[2] / "backups/arca-analisis-20261025/subcuentas-esquema.json"
    p.parent.mkdir(exist_ok=True, parents=True)
    p.write_text(json.dumps(result, default=str, indent=2), encoding="utf-8")
    print(json.dumps(result, default=str))


if __name__ == "__main__":
    main()
