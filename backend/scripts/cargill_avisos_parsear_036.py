"""Solo lectura: parsea los avisos de pago de Cargill (PDF del portal) y arma la lista de
documentos cancelados por cada cobro. Uso: python cargill_avisos_parsear_036.py <carpeta backups>"""
import json
import re
import sys
from pathlib import Path

import pdfplumber

NUM = r"-?[\d.]+,\d{2}"


def _dec(s: str) -> float:
    return float(s.replace(".", "").replace(",", "."))


def parsear(pdf: Path) -> dict:
    with pdfplumber.open(pdf) as p:
        texto = "\n".join((pg.extract_text() or "") for pg in p.pages)
    aviso = {"archivo": pdf.name, "voucher": pdf.name.split("_")[0], "transferencias": [], "documentos": [], "otros": []}
    m = re.search(r"Fecha: (\d{2}/\d{2}/\d{4})", texto)
    aviso["fecha"] = m.group(1) if m else None
    seccion = None
    for linea in texto.splitlines():
        l = linea.strip()
        if l.startswith("Transferencias bancarias"):
            seccion = "transf"; continue
        if l.startswith("Documentos cancelados"):
            seccion = "docs"; continue
        if l.startswith("TP N") or l.startswith("Banco Cuenta"):
            continue
        if seccion == "docs":
            m = re.match(rf"^(\S\S) (.+?) (\S+) ({NUM})$", l)
            if m:
                aviso["documentos"].append({"tp": m.group(1), "desc": m.group(2), "numero": m.group(3), "importe": _dec(m.group(4))})
            elif m := re.match(rf"^(\S\S) ?(.*?) ({NUM})$", l):  # sin número: H9 redondeo, RU recibo
                aviso["documentos"].append({"tp": m.group(1), "desc": m.group(2) or "REDONDEO", "numero": None,
                                            "importe": _dec(m.group(3))})
            elif l:
                aviso["otros"].append(l)
        elif seccion == "transf":
            m = re.search(rf"(\d{{3}}-\d+).*? ({NUM})$", l)
            if m:
                aviso["transferencias"].append({"cuenta": m.group(1), "importe": _dec(m.group(2))})
    return aviso


if __name__ == "__main__":
    base = Path(sys.argv[1])
    avisos = [parsear(f) for f in sorted((base / "avisos").glob("*.pdf"))]
    json.dump(avisos, open(base / "avisos.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    for a in avisos:
        neto = round(sum(d["importe"] for d in a["documentos"]), 2)
        tr = round(sum(t["importe"] for t in a["transferencias"]), 2)
        print(a["voucher"], a["fecha"], len(a["documentos"]), "docs", neto, "transf", tr, "OTROS" if a["otros"] else "")
