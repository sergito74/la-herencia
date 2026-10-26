"""Copiar y registrar en dbo.ArcaDocumentos los 20 certificados de retención de IVA Granos (Cargill 2020-2022).
"""
import hashlib
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db.connection import get_connection
from src.features.cajas_efectivo.operaciones import read
from src.features.cuentas_corrientes.arca_documentos import RAIZ

DESTINO = RAIZ / "IVA" / "Devoluciones"
DESTINO.mkdir(parents=True, exist_ok=True)

IDS = [
    291, 292, 293, 294, 295, 296, 297, 299, 301, 302,
    303, 304, 305, 306, 307, 308, 309, 310, 311, 312,
]

certs = read(
    f"SELECT rig.IdRetencion, rig.IdLiquidacion, rig.[Nro Certificado], rig.Imagen, vg.Fecha "
    f"FROM dbo.[Retenciones IVA Granos] rig JOIN dbo.[Venta Granos] vg ON rig.IdLiquidacion=vg.IdVenta "
    f"WHERE rig.IdRetencion IN ({','.join(str(i) for i in IDS)})"
)

with get_connection(readonly=False) as conn:
    cur = conn.cursor()
    for c in certs:
        orig = Path(c["Imagen"])
        dest = DESTINO / orig.name
        if not dest.exists():
            shutil.copy2(orig, dest)
        sha = hashlib.sha256(dest.read_bytes()).hexdigest()
        per = f"{c['Fecha'].month:02d}/{c['Fecha'].year}"
        cur.execute(
            "INSERT INTO dbo.ArcaDocumentos (Origen, IdOrigen, Tipo, Periodo, Numero, Ruta, Sha256, EsOriginal, Usuario) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            "Ret. IVA Granos", c["IdLiquidacion"], "Certificado Retención IVA Granos", per, c["Nro Certificado"], str(dest), sha, 1, "Gemini036"
        )
    print("VINCULADOS:", len(certs))

