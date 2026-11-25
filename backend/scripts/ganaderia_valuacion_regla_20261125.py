"""052: tabla GanValuacionRegla (reglas de Sergio para valuar el stock) con su dato inicial. Idempotente.
Uso (desde backend/): python -m scripts.ganaderia_valuacion_regla_20261125 [--aplicar]"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.ganaderia_tablas_20261125 import _backup  # noqa: E402
from src.db.connection import fetch_all, get_connection  # noqa: E402

DDL = """CREATE TABLE dbo.GanValuacionRegla (
    IdCategoria int NOT NULL CONSTRAINT PK_GanValuacionRegla PRIMARY KEY
        CONSTRAINT FK_GanValReg_Cat REFERENCES dbo.GanCategoria(IdCategoria),
    KgValuacion decimal(7,1) NULL,
    CoefFijo decimal(6,3) NULL,
    Motivo nvarchar(200) NOT NULL)"""
SEED = [("Toros", 500, 1.0, "Toro usado = 500 kg de novillo (Sergio, mail al Estudio 10/08/2023)")]

if __name__ == "__main__":
    existe = fetch_all("SELECT OBJECT_ID('dbo.GanValuacionRegla') i")[0]["i"]
    print("Tabla existe:", bool(existe), "| reglas:", SEED)
    if "--aplicar" not in sys.argv:
        sys.exit("Simulación (usar --aplicar)")
    print("BACKUP_VERIFICADO=" + _backup())
    with get_connection(readonly=False) as cn:
        cn.autocommit = False
        cur = cn.cursor()
        if not existe:
            cur.execute(DDL)
        for nombre, kg, coef, motivo in SEED:
            cur.execute("IF NOT EXISTS (SELECT 1 FROM dbo.GanValuacionRegla r JOIN dbo.GanCategoria c ON c.IdCategoria = "
                        "r.IdCategoria WHERE c.Nombre = ?) INSERT INTO dbo.GanValuacionRegla (IdCategoria, KgValuacion, "
                        "CoefFijo, Motivo) SELECT IdCategoria, ?, ?, ? FROM dbo.GanCategoria WHERE Nombre = ?",
                        (nombre, kg, coef, motivo, nombre))
        cn.commit()
    print(fetch_all("SELECT * FROM dbo.GanValuacionRegla"))
