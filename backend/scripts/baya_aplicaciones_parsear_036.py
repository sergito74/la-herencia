"""036 — grupo 1: lee los recibos (RI) y aplicaciones (CA) de Bayá Casal bajados con `baya_aplicaciones_bajar_036`.

De cada comprobante saca: número, fecha, TC, valores recibidos y retenciones (RI), y la lista de comprobantes que
cancela con su importe a cancelar en pesos. En las CA, "Origen" son los créditos que se usan y "Aplicación" los
débitos que cancelan. Solo lectura. Uso (desde backend/): python -m scripts.baya_aplicaciones_parsear_036 <carpeta>
→ <carpeta>/aplicaciones.json
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pdfplumber

NUM = r"-?\d{1,3}(?:\.\d{3})*,\d{2}"
FILA = re.compile(rf"^([A-Z]{{2}}) (\d{{4}}) (\d{{8}}) (.*?)\s+({NUM}) ({NUM})$")


def _n(s: str) -> float:
    return float(s.replace(".", "").replace(",", "."))


def leer(ruta: Path) -> dict:
    texto = "\n".join(p.extract_text() or "" for p in pdfplumber.open(ruta).pages)
    lineas = texto.splitlines()
    nro = re.search(r"Número: (\d{4}) (\d{8})", texto)
    fecha = re.search(r"Fecha: (\d\d/\d\d/\d{4})", texto)
    tc = re.findall(r"Tipo de Cambio: ([\d.,]+)", texto)
    seccion, origen, aplic = ("aplic" if ruta.name.startswith("RI") else None), [], []
    for ln in lineas:
        if ln.startswith("Origen"):
            seccion = "origen"
        elif ln.startswith("Aplicación") or ln.startswith("Se aplican en Pago"):
            seccion = "aplic"
        m = FILA.match(ln.strip())
        if m and seccion:
            (origen if seccion == "origen" else aplic).append(
                {"comp": f"{m[1]} {m[2]} {m[3]}", "concepto": m[4], "aCancelar": _n(m[6])})
        elif seccion == "aplic" and (a := re.match(rf"^Anticipo ({NUM})$", ln.strip())):
            aplic.append({"comp": "Anticipo", "concepto": "", "aCancelar": _n(a[1])})
    valores = re.search(rf"Total Pesos Recibidos: ({NUM})", texto)
    ret = re.search(rf"Total Retenciones: ({NUM})", texto)
    obs = texto.split("Observaciones:")[-1].splitlines()[1:2] if "Observaciones:" in texto else []
    return {"archivo": ruta.name, "tipo": ruta.name[:2], "nro": f"{nro[1]} {nro[2]}" if nro else None,
            "fecha": fecha[1] if fecha else None, "tc": tc[-1] if tc else None,
            "valores": _n(valores[1]) if valores else 0.0, "retenciones": _n(ret[1]) if ret else 0.0,
            "origen": origen, "aplicacion": aplic, "observaciones": obs[0] if obs else ""}


if __name__ == "__main__":
    carpeta = Path(sys.argv[1])
    comps = [leer(p) for p in sorted(carpeta.glob("*.pdf"))]
    json.dump(comps, open(carpeta / "aplicaciones.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for c in comps:
        print(c["archivo"], c["fecha"], "valores", c["valores"], "ret", c["retenciones"], "| origen", len(c["origen"]),
              "| aplica", [(a["comp"], a["aCancelar"]) for a in c["aplicacion"]], "|", c["observaciones"])
