"""Lector de resúmenes de Visa Galicia (043, T034), desde `scripts/cargar_resumen_visa_galicia_pdf.py`.

Carga el resumen en `Tarjetas_Resumenes` + `Tarjetas_Resumenes_Lineas` solo si consumos + cargos dan el
"TOTAL A PAGAR" del PDF al centavo y el código de resumen no existe. El contacto de cada línea sale de la tabla
explícita (comercios ya confirmados en resúmenes previos); las demás quedan sin contacto para vincular a mano,
nunca se adivinan.
"""

from __future__ import annotations

import io
import re
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

ID_TARJETA = 4  # Visa Galicia
CONTACTOS = [
    ("PINTESPANA", 3654), ("WAGEN", 636), ("Starlink", 567), ("CAMINO PQUE", 314), ("AUTOPISTA DEL OE", 306),
    ("RUTAS SUR", 2657), ("TELEPEAJE", 328), ("MARGENES", 346),
]
LINEA = re.compile(r"^(\d\d-\d\d-\d\d) [*K] (.+?)\s+(-?[\d.]+,\d\d)(-?)$")
CUOTA_COMPROBANTE = re.compile(r"\s+(\d{2}/\d{2})?\s*\d{6}$")
MESES = {"Ene": 1, "Feb": 2, "Mar": 3, "Abr": 4, "May": 5, "Jun": 6, "Jul": 7, "Ago": 8, "Sep": 9, "Oct": 10,
         "Nov": 11, "Dic": 12}
CENTAVO = Decimal("0.01")


def _num(s: str) -> Decimal:
    return Decimal(s.replace(".", "").replace(",", "."))


def es_visa_galicia(texto: str) -> bool:
    """Resumen Visa Galicia **de la empresa**: el titular es Giamigli. Un resumen personal de un socio no entra
    (se guardaría como de Giamigli por no traer CUIT, y se cargaría en la tarjeta de la empresa)."""
    t = texto.upper()
    return bool(re.search(r"Resumen N\S+\s+VI\d+", texto)) and "GALICIA" in t and "GIAMIGLI" in t


def leer(texto: str) -> dict | None:
    codigo = re.search(r"Resumen N\S+\s+(VI\d+)", texto)
    fechas = re.search(r"(\d\d-\w{3}-\d\d) (\d\d-\w{3}-\d\d) (\d\d-\w{3}-\d\d) (\d\d-\w{3}-\d\d)", texto)
    if not (codigo and fechas):
        return None

    def f(s):
        dd, mm, yy = s.split("-")
        return datetime(2000 + int(yy), MESES[mm], int(dd))

    lineas = []
    for linea in texto.splitlines():
        m = LINEA.match(linea.strip())
        if not m or "TARJETA" in linea:
            continue
        resto = m.group(2)
        cuota = re.search(r"\s(\d{2}/\d{2})\s+\d{6}$", resto)
        detalle = re.sub(r"\s+\d{6}$", "", CUOTA_COMPROBANTE.sub("", resto).strip())
        importe = _num(m.group(3)) * (-1 if m.group(4) == "-" else 1)
        lineas.append({"fechaCompra": datetime.strptime(m.group(1), "%d-%m-%y"), "detalle": detalle[:255],
                       "importe": importe, "cuota": cuota.group(1) if cuota else None})

    def tomar(patron):
        m = re.search(patron, texto)
        return _num(m.group(1)) if m else Decimal(0)

    cargos = {
        "ImpuestoSellos": tomar(r"IMPUESTO DE SELLOS \$ ([\d.]+,\d\d)"),
        "MantCuenta": tomar(r"COMISI\S+ MANT DE CTA\. ([\d.]+,\d\d)"),
        "IVA21": tomar(r"DB IVA \$ RESP INSC\. 21% [\d.]+,\d\d ([\d.]+,\d\d)"),
        "PercepIVA21": tomar(r"PERCEP\.IVA RG2408 [\d,.%]+ B\. [\d.,]+ ([\d.]+,\d\d)"),
    }
    return {"codigo": codigo.group(1), "cierre": f(fechas.group(3)), "vencimiento": f(fechas.group(4)),
            "lineas": lineas, "cargos": cargos, "totalPagar": tomar(r"TOTAL A PAGAR ([\d.]+,\d\d)")}


def contacto_de(detalle: str) -> int | None:
    for frag, c in CONTACTOS:
        if frag.lower() in detalle.lower():
            return c
    return None


def total_calculado(r: dict) -> Decimal:
    return (sum((l["importe"] for l in r["lineas"]), Decimal(0)) + sum(r["cargos"].values())).quantize(
        CENTAVO, ROUND_HALF_UP)


def cargar(pdf: bytes, ruta: str) -> dict:
    """`{estadoCarga, motivo, idRegistro}` con los estados de `boveda.carga` (cargado_auto, ya_cargado, pendiente)."""
    import pdfplumber

    from src.db.connection import execute_write_transaction, fetch_one

    with pdfplumber.open(io.BytesIO(pdf)) as d:
        texto = "\n".join((p.extract_text() or "") for p in d.pages)
    r = leer(texto)
    if r is None:
        return {"estadoCarga": "pendiente", "motivo": "Formato de resumen no reconocido", "idRegistro": None}
    ya = fetch_one("SELECT IdResumen AS id FROM dbo.Tarjetas_Resumenes WHERE IdTarjeta = ? AND ResumenCodigo = ?",
                   (ID_TARJETA, r["codigo"]))
    if ya:
        return {"estadoCarga": "ya_cargado", "motivo": None, "idRegistro": ya["id"]}
    calculado, impreso = total_calculado(r), r["totalPagar"].quantize(CENTAVO)
    if calculado != impreso:
        return {"estadoCarga": "pendiente", "idRegistro": None,
                "motivo": f"No cierra al centavo: calculado {calculado}, impreso {impreso}: importar a mano"}
    cols = list(r["cargos"])
    stmts: list = [(
        f"INSERT INTO dbo.Tarjetas_Resumenes (IdTarjeta, ResumenCodigo, FechaCierre, FechaVencimiento, EstadoResumen, "
        f"SoloCabecera, Observaciones, ArchivoOrigen, {', '.join(cols)}) OUTPUT INSERTED.IdResumen "
        f"VALUES (?, ?, ?, ?, ?, ?, ?, ?, {', '.join('?' for _ in cols)})",
        (ID_TARJETA, r["codigo"], r["cierre"], r["vencimiento"], "Cargado", None,
         f"Cargado solo desde el PDF el {datetime.now():%Y-%m-%d} (rutina 043)", ruta) + tuple(r["cargos"][c] for c in cols),
    )]
    for l in r["lineas"]:
        stmts.append(lambda res, l=l: (
            "INSERT INTO dbo.Tarjetas_Resumenes_Lineas (IdResumen, FechaCompra, Detalle, Importe, IdContacto, NroDocumento) "
            "VALUES (?, ?, ?, ?, ?, ?)", (res[0], l["fechaCompra"], l["detalle"], l["importe"], contacto_de(l["detalle"]), None)))
    id_resumen = execute_write_transaction(stmts)[0]
    return {"estadoCarga": "cargado_auto", "motivo": None, "idRegistro": id_resumen}
