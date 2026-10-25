"""Leer originales VEP descargados y conservar copias locales verificadas; sin SQL."""
from pathlib import Path
import hashlib
import json
import re
import shutil
from decimal import Decimal as D

import pdfplumber

ROOT=Path(__file__).resolve().parents[2]/"backups/arca-continuacion-20261025"
RAIZ=Path.home()/"Documents/La Herencia/Administracion y gestion/Impuestos y Sociedades/ARCA/Giamigli/VEP"


def run():
    out=[]
    for v in json.loads((ROOT/"veps-generales-pdf.json").read_text(encoding="utf-8")):
        p=ROOT/v["archivo"]
        if hashlib.sha256(p.read_bytes()).hexdigest()!=v["sha256"]:raise ValueError("Cambió un PDF original")
        with pdfplumber.open(p) as pdf:text="\n".join(s.extract_text() or "" for s in pdf.pages)
        if "30-71211460-2" not in text or not re.search(r"Nro\. VEP(?: Consolidado)?:\s*"+v["numero"]+r"\b",text):
            raise ValueError("PDF de otro CUIT/VEP")
        m=re.search(r"IMPORTE PAGADO\s*\$([\d.,]+)",text)
        if not m:raise ValueError("Sin importe pagado "+v["numero"])
        total=D(m[1].replace(".","").replace(",","."))
        fecha=re.search(r"Fecha de Pago:\s*(\d{4}-\d{2}-\d{2})",text)[1]
        cu=re.search(r"Concepto:\s*(\d+)",text)
        per=re.search(r"Período:\s*([\d-]+)",text)
        cuota=re.search(r"ANTICIPO/CUOTA:\s*(\d+)",text)
        sub="cargas-sociales" if "Empleadores SICOSS" in text else "sicore-ganancias" if "SICORE-IMPTO.A LAS GANANCIAS" in text else "ganancias" if "GANANCIAS SOCIEDADES (10)" in text else "por-identificar"
        destino=RAIZ/fecha[:4]/p.name
        destino.parent.mkdir(parents=True,exist_ok=True)
        if destino.exists() and hashlib.sha256(destino.read_bytes()).hexdigest()!=v["sha256"]:
            raise ValueError("Cambió una copia existente")
        if not destino.exists():shutil.copy2(p,destino)
        out.append({**v,"texto":text,"total":str(total),"fechaPago":fecha,"concepto":cu[1] if cu else None,
                    "periodo":per[1] if per else None,"cuota":cuota[1] if cuota else None,"subcuenta":sub,"ruta":str(destino),
                    "consolidado":"Datos del VEP Consolidado" in text})
    (ROOT/"veps-generales-extraidos.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
    print("VEP oficiales verificados y copiados:",len(out))


if __name__=="__main__":run()
