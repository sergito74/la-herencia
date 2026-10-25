"""Documentos ARCA registrados: rutas locales acotadas, sin rutas del cliente."""
import hashlib
from pathlib import Path

from src.features.cajas_efectivo.operaciones import read

RAIZ = Path.home() / "Documents/La Herencia/Administracion y gestion/Impuestos y Sociedades/ARCA/Giamigli"


def por_movimiento():
    docs = read("""SELECT d.IdDocumento idDocumento,d.Origen origen,d.IdOrigen idOrigen,
        d.Tipo tipo,d.Periodo periodo,d.Numero numero,d.EsOriginal esOriginal
        FROM dbo.ArcaDocumentos d WHERE EXISTS(SELECT 1 FROM dbo.vw_MovimientosCuenta_Base b
          WHERE b.IdContacto=119 AND b.Origen=d.Origen AND b.IdOrigen=d.IdOrigen)
        ORDER BY d.IdDocumento""")
    grupos = {}
    for d in docs:
        grupos.setdefault((d["origen"], d["idOrigen"]), []).append(d)
    return grupos


def verificar_archivo(ruta, sha256):
    p = Path(ruta).resolve()
    if not p.is_relative_to(RAIZ.resolve()) or p.suffix.lower() != ".pdf" or not p.is_file():
        raise FileNotFoundError("El documento no está disponible en la carpeta registrada")
    contenido = p.read_bytes()
    if not contenido.startswith(b"%PDF-") or hashlib.sha256(contenido).hexdigest() != sha256:
        raise ValueError("El archivo cambió respecto del comprobante registrado")
    return p


def archivo(id_documento):
    filas = read("""SELECT d.Ruta ruta,d.Sha256 sha256 FROM dbo.ArcaDocumentos d
        WHERE d.IdDocumento=? AND EXISTS(SELECT 1 FROM dbo.vw_MovimientosCuenta_Base b
          WHERE b.IdContacto=119 AND b.Origen=d.Origen AND b.IdOrigen=d.IdOrigen)""", (id_documento,))
    if not filas:
        raise FileNotFoundError("Documento de ARCA no encontrado")
    return verificar_archivo(filas[0]["ruta"], filas[0]["sha256"])
