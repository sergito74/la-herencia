"""Lee originales HSBC con Python del sistema (pdfplumber); no escribe fuentes ni DB.

Ejecutar desde la raíz: python backend/scripts/rastrear_resumenes_hsbc_condominio_036.py
Genera evidencia local ignorada. Una coincidencia no atribuye automáticamente el pago.
"""

import hashlib
import json
import re
from pathlib import Path

import pdfplumber

BASE = Path("C:/Users/Sergio/Documents")
ROOTS = (
    BASE / "Alquileres urbanos/Estacion de Servicio/Condiminio/Resumenes de cuenta/HSBC",
    BASE / "Resumenes Bancarios/HSBC",
)
MONTHS = {
    "2011-04",
    "2011-05",
    "2011-06",
    "2011-08",
    "2011-09",
    "2011-10",
    "2012-09",
    "2012-11",
    "2013-03",
    "2013-07",
    "2013-09",
    "2013-12",
    "2014-03",
}
OUT = Path(__file__).resolve().parents[2] / "backups/condominio-15-medios-036"
AMOUNTS = re.compile(r"10,004\.70|\b95\.00\b|1,361\.54|1,362\.00|1,250\.97|2,253\.0[34]|1,578\.00")


def run():
    folder = OUT / "hsbc-extraidos"
    folder.mkdir(parents=True, exist_ok=True)
    coverage = []
    matched = []
    for source, root in enumerate(ROOTS):
        for path in sorted(root.rglob("*.pdf")):
            iso = re.search(r"(201[1-4])-([01][0-9])-[0-3][0-9]", path.name)
            local = re.search(r"([0-3][0-9])-([01][0-9])-(1[1-4])", path.name)
            month = f"{iso[1]}-{iso[2]}" if iso else (f"20{local[3]}-{local[2]}" if local else None)
            if month not in MONTHS:
                continue
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            with pdfplumber.open(path) as pdf:
                pages = [p.extract_text() or "" for p in pdf.pages]
            extracted = folder / f"{source}-{month}.txt"
            text = "\n\n".join(f"PAGINA {i}\n{t}" for i, t in enumerate(pages, 1))
            extracted.write_text(text, encoding="utf-8")
            coverage.append(
                {
                    "origen": source,
                    "mes": month,
                    "pdf": str(path),
                    "sha256": digest,
                    "paginas": len(pages),
                    "texto": sum(map(len, pages)),
                    "extraido": str(extracted),
                }
            )
            lines = text.splitlines()
            current_day = None
            page_number = None
            for i, line in enumerate(lines):
                if line.startswith("PAGINA "):
                    page_number = int(line.split()[1])
                date_match = re.match(r"(\d\d-[A-Z]{3})\b", line)
                if date_match:
                    current_day = date_match[1]
                if not AMOUNTS.search(line):
                    continue
                context = "\n".join(lines[i : i + 4])
                matched.append(
                    {
                        "origen": source,
                        "mes": month,
                        "dia": current_day,
                        "pagina": page_number,
                        "linea": line,
                        "contexto": context,
                        "pdf": str(path),
                        "sha256": digest,
                        "partidaARBA": "0079575" in re.sub(r"[^0-9]", "", context),
                        "servicioDA95": "SERVICIO: DA95" in context,
                    }
                )
            assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
    for name, data in (
        ("hsbc-cobertura-verificada.json", coverage),
        ("hsbc-coincidencias.json", matched),
    ):
        (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "documentos": len(coverage),
        "paginas": sum(r["paginas"] for r in coverage),
        "coincidenciasImporte": len(matched),
    }


if __name__ == "__main__":
    print(json.dumps(run()))
