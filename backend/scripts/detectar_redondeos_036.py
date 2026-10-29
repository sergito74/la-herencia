"""036 — facturas cargadas con centavos de más o de menos respecto del comprobante (solo lectura).

Sergio 29/10/2026: los centavos no se cancelan con pagos; se redondea la factura al total del comprobante. Para cada
factura busca el pago de casi el mismo importe (diferencia de hasta $1, ±60 días) y compara el total cargado con el
TOTAL impreso en el PDF. Solo se corrigen las que el PDF confirma. Uso (desde backend/):
python -m scripts.detectar_redondeos_036 <idContacto> [salida.xlsx]
"""

from __future__ import annotations

import re
import sys

import pdfplumber
from openpyxl import Workbook

from src.db.connection import fetch_all
from src.features.recalculo_fifo import entrada

DIFERENCIA_MAXIMA = 1.0
NUMERO = r"\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2}|\d+\.\d{2}"


def _num(s: str) -> float:
    return float(s.replace(".", "").replace(",", ".")) if "," in s else float(s)


def total_pdf(ruta: str | None) -> float | None:
    """TOTAL del comprobante: el número en la línea del título TOTAL o, si es encabezado de tabla, el último de la
    línea siguiente. None si el PDF es una imagen o no se lee."""
    if not ruta:
        return None
    try:
        with pdfplumber.open(ruta.split("#")[0]) as pdf:
            lineas = "\n".join(p.extract_text() or "" for p in pdf.pages[:2]).splitlines()
    except Exception:
        return None
    for n, linea in enumerate(lineas):
        if not re.search(r"(?<!SUB)\bTOTAL\b(?!\s*(NETO|OTROS|IMP))", linea, re.I):
            continue
        en_linea = re.findall(NUMERO, linea)
        if en_linea:
            return _num(en_linea[-1])
        if n + 1 < len(lineas) and (siguiente := re.findall(NUMERO, lineas[n + 1])):
            return _num(siguiente[-1])
    return None


def casos(ct: int) -> list[dict]:
    e = entrada.armar([ct])[ct]
    docs = [i for i in e["items"] if i["clave"][0] == "Compras" and i["lado"] == "D"]
    pagos = [i for i in e["items"] if i["lado"] == "C" and i["clase"] == "dinero"]
    rutas = {r["i"]: r["d"] for r in fetch_all("SELECT IdDeuda AS i, [Documento Original] AS d FROM dbo.Compras WHERE IdContacto = ?", (ct,))}
    salida = []
    for d in sorted(docs, key=lambda x: x["fecha"]):
        total = round(float(d["importe"]), 2)
        cerca = [p for p in pagos if 0 < abs(round(total - float(p["importe"]), 2)) <= DIFERENCIA_MAXIMA
                 and abs((p["fecha"] - d["fecha"]).days) <= 60]
        if not cerca:
            continue
        p = min(cerca, key=lambda p: abs((p["fecha"] - d["fecha"]).days))
        pdf = total_pdf(rutas.get(d["clave"][1]))
        pagado = round(float(p["importe"]), 2)
        if pdf is None:
            estado = "PDF no legible: ver a ojo"
        elif abs(pdf - pagado) < 0.005:
            estado = "Corregir: el comprobante dice lo pagado"
        elif abs(pdf - total) < 0.005:
            estado = "Bien cargada: la diferencia es del pago"
        else:
            estado = "El comprobante no coincide con ninguno"
        salida.append({"id": d["clave"][1], "nro": d["nro"], "fecha": d["fecha"], "total": total, "pago": f"{p['clave'][0]} {p['fecha']:%d/%m/%Y}",
                       "pagado": pagado, "dif": round(total - pagado, 2), "pdf": pdf, "estado": estado})
    return salida


if __name__ == "__main__":
    filas = casos(int(sys.argv[1]))
    for f in filas:
        print(f["nro"], f["fecha"], f["total"], f["pago"], f["pagado"], f["dif"], f["pdf"], f["estado"])
    if len(sys.argv) > 2:
        libro = Workbook()
        hoja = libro.active
        hoja.append(["Factura", "Emisión", "Total cargado", "Pago", "Importe pagado", "Diferencia", "TOTAL del comprobante", "Resultado"])
        for f in filas:
            hoja.append([f["nro"], f["fecha"], f["total"], f["pago"], f["pagado"], f["dif"], f["pdf"], f["estado"]])
        libro.save(sys.argv[2])
