"""Autónomos 10/2026 de Sergio y Lucy (11/11/2026): copias CCMA bajadas de ARCA (solo lectura, scripts/arca_ccma_descargar.py)
guardadas en la carpeta de Autónomos; obligaciones cargadas en Impuestos (ARCA 119, tipo 5) con su CCMA en ArcaDocumentos,
igual que 09/2026. Idempotente."""
import hashlib
import shutil
import sys
from pathlib import Path

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_one

CARPETA = Path(r"C:\Users\Sergio\Documents\La Herencia\Administracion y gestion\Impuestos y Sociedades\ARCA\Giamigli\Autonomos")
# (titular, fecha, período, importe, archivo fuente)
OBLIG = [("Sergio", "2026-11-12", "10 2026", 156541.75), ("Lucy", "2026-11-10", "10 2026", 66041.63),
         ("Lucy", "2026-11-11", "Intereses CCMA 10 2026", 18.27)]


def main(origen: str):
    _assert_target_is_wc()
    rutas = {}
    for t in ("Sergio", "Lucy"):
        dst = CARPETA / f"CCMA-{t}-202409-202610.pdf"
        if not dst.exists():
            shutil.copyfile(Path(origen) / f"{t.lower()}.pdf", dst)
        rutas[t] = (str(dst), hashlib.sha256(dst.read_bytes()).hexdigest())
    for t, f, per, imp in OBLIG:
        num = f"CCMA {t}"
        if fetch_one("SELECT 1 x FROM dbo.Impuestos WHERE IdOrganismo=119 AND [Numero de documento]=? AND [Periodo liquidado]=? AND Importe=?",
                     (num, per, imp)):
            print("ya estaba", t, per); continue
        ruta, sha = rutas[t]
        i = execute_write_transaction([
            ("INSERT INTO dbo.Impuestos (Fecha,IdOrganismo,IdTipoImpuesto,[Periodo liquidado],[Numero de documento],Importe,[Documento Original]) "
             "OUTPUT INSERTED.IdImpuesto VALUES (?,119,5,?,?,?,?)", (f, per, num, imp, ruta)),
            lambda r: ("INSERT INTO dbo.ArcaDocumentos (Origen,IdOrigen,Tipo,Periodo,Numero,Ruta,Sha256,EsOriginal,Usuario) "
                       "VALUES ('Impuestos',?,'Estado de cuenta CCMA','10/2026',?,?,?,0,'Claude (ARCA 11/11/2026)')", (r[0], num, ruta, sha)),
        ])[0]
        print("cargado", i, t, per, imp)


if __name__ == "__main__":
    main(sys.argv[1])
