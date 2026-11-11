"""Cargas sociales de Irma Miranda (Casas Particulares, a cargo de Giamigli), 11/11/2026: detalles de pago bajados de ARCA
con la clave de Lucy (solo lectura, scripts/arca_casas_particulares.py). Octubre 2026 se carga en Impuestos (ARCA 119,
tipo 2) como septiembre; ambos quedan con su detalle en ArcaDocumentos y Documento Original. Idempotente."""
import hashlib
import shutil
import sys
from pathlib import Path

from src.db.connection import _assert_target_is_wc, execute_write, execute_write_transaction, fetch_one

CARPETA = Path(r"C:\Users\Sergio\Documents\La Herencia\Administracion y gestion\Impuestos y Sociedades\ARCA\Giamigli\Casas Particulares")
NUMERO = "Servicio Domestico (Casas Particulares, a cargo de Giamigli)"
USUARIO = "Claude (ARCA 11/11/2026)"


def main(origen: str):
    _assert_target_is_wc()
    CARPETA.mkdir(parents=True, exist_ok=True)
    docs = {}
    for n, per in ((0, "202610"), (1, "202609")):
        dst = CARPETA / f"Irma-Miranda-detalle-pago-{per}.pdf"
        if not dst.exists():
            shutil.copyfile(Path(origen) / f"detalle-{n}.pdf", dst)
        docs[per] = (str(dst), hashlib.sha256(dst.read_bytes()).hexdigest())
    # Septiembre ya cargado (4898): se le asocia el detalle.
    ruta, sha = docs["202609"]
    execute_write("UPDATE dbo.Impuestos SET [Documento Original]=? WHERE IdImpuesto=4898 AND [Documento Original] IS NULL", (ruta,))
    if not fetch_one("SELECT 1 x FROM dbo.ArcaDocumentos WHERE Origen='Impuestos' AND IdOrigen=4898"):
        execute_write("INSERT INTO dbo.ArcaDocumentos (Origen,IdOrigen,Tipo,Periodo,Numero,Ruta,Sha256,EsOriginal,Usuario) "
                      "VALUES ('Impuestos',4898,'Detalle de pago Casas Particulares','09/2026','Irma Miranda',?,?,1,?)", (ruta, sha, USUARIO))
    ruta, sha = docs["202610"]
    if fetch_one("SELECT 1 x FROM dbo.Impuestos WHERE IdOrganismo=119 AND IdTipoImpuesto=2 AND [Periodo liquidado]='10 2026' AND [Numero de documento]=?", (NUMERO,)):
        print("octubre ya estaba"); return
    i = execute_write_transaction([
        ("INSERT INTO dbo.Impuestos (Fecha,IdOrganismo,IdTipoImpuesto,[Periodo liquidado],[Numero de documento],Importe,[Documento Original]) "
         "OUTPUT INSERTED.IdImpuesto VALUES ('2026-11-10',119,2,'10 2026',?,13144.07,?)", (NUMERO, ruta)),
        lambda r: ("INSERT INTO dbo.ArcaDocumentos (Origen,IdOrigen,Tipo,Periodo,Numero,Ruta,Sha256,EsOriginal,Usuario) "
                   "VALUES ('Impuestos',?,'Detalle de pago Casas Particulares','10/2026','Irma Miranda',?,?,1,?)", (r[0], ruta, sha, USUARIO)),
    ])[0]
    print("cargado", i)


if __name__ == "__main__":
    main(sys.argv[1])
