"""Solo lectura de HSBC: cruza importe, fecha +/-5 días y comercio para68 pagos.

Python del sistema con pdfplumber; ejecutar desde raíz. No escribe WC ni originales.
La elección de comercio queda explícita; coincidencias ambiguas no se aplican.
"""

import argparse
import hashlib
import json
import re
from datetime import date
from decimal import Decimal
from pathlib import Path

import pdfplumber

OUT = Path(__file__).resolve().parents[2] / "backups/condominio-15-medios-036"
ROOT = Path("C:/Users/Sergio/Documents/Resumenes Bancarios/HSBC")
ROOTS = (
    ROOT,
    Path(
        "C:/Users/Sergio/Documents/Alquileres urbanos/Estacion de Servicio/Condiminio/"
        "Resumenes de cuenta/HSBC"
    ),
)
MONTHS = dict(
    zip("ENE FEB MAR ABR MAY JUN JUL AGO SEP OCT NOV DIC".split(), range(1, 13), strict=True)
)
MERCHANT = {
    30: "OPESSA SALADILLO",
    142: "OPESSA NORDELTA",
    110: "PEUMAN",
    112: "PACHECO GROC",
    91: "SODIMAC",
    60: "JUMBO",
    63: "LIOCA SANITARIOS",
}


def run(explorar_centavos=False):
    targets = json.loads((OUT / "puentes-68-pagos.json").read_text(encoding="utf-8"))
    cache_root = OUT / "hsbc-68"
    cache_root.mkdir(exist_ok=True)
    coverage, transactions = [], {}
    files = [(i, p) for i, root in enumerate(ROOTS) for p in sorted(root.rglob("*.pdf"))]
    for source_index, path in files:
        n = re.search(r"([0-3][0-9])-([01][0-9])-(1[1-5])", path.name)
        iso = re.search(r"(201[1-5])-([01][0-9])-[0-3][0-9]", path.name)
        if not n and not iso:
            continue
        year, month = (int(iso[1]), int(iso[2])) if iso else (int("20" + n[3]), int(n[2]))
        if year == 2015 and month > 8:
            continue
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        cache = cache_root / (sha[:16] + ".txt")
        if cache.exists():
            text = cache.read_text(encoding="utf-8")
        else:
            with pdfplumber.open(path) as pdf:
                text = "\n\n".join(
                    f"PAGINA {i}\n" + (p.extract_text() or "") for i, p in enumerate(pdf.pages, 1)
                )
            cache.write_text(text, encoding="utf-8")
        coverage.append({"pdf": str(path), "sha256": sha, "extraido": str(cache)})
        current, page = None, None
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if line.startswith("PAGINA "):
                page = int(line.split()[1])
            dm = re.match(r"(\d\d)-([A-Z]{3})\b", line)
            if dm and dm[2] in MONTHS:
                yy = year - 1 if MONTHS[dm[2]] > month + 1 else year
                current = date(yy, MONTHS[dm[2]], int(dm[1]))
            purchase = re.search(r"- COMPRA\s+(\d+)\s+([\d,]+\.\d\d)\s+", line)
            if not current or not purchase:
                continue
            # Sigue el comercio aunque el detalle continúe en la página siguiente.
            context = [line]
            for after in lines[i + 1 : i + 35]:
                if re.match(r"(?:\d\d-[A-Z]{3}\s+)?- \S", after):
                    break
                context.append(after)
            content = "\n".join(context)
            merchant = re.search(r"ESTABLECIMIENTO:\s*(.+)", content)
            operation = re.search(r"OPERACION:\s*(\d+)", content)
            key = (
                source_index,
                current.isoformat(),
                purchase[1],
                purchase[2],
                operation[1] if operation else None,
            )
            tx = transactions.setdefault(
                key,
                {
                    "fecha": current.isoformat(),
                    "numero": purchase[1],
                    "operacion": operation[1] if operation else None,
                    "importe": str(Decimal(purchase[2].replace(",", ""))),
                    "comercio": merchant[1].strip() if merchant else None,
                    "debitoExplicito": "TARJETA DE DEBITO" in content,
                    "fuentes": [],
                },
            )
            tx["fuentes"].append({"pdf": str(path), "sha256": sha, "pagina": page})
        assert hashlib.sha256(path.read_bytes()).hexdigest() == sha
    matrix = []
    for p in targets:
        candidates = []
        for tx in transactions.values():
            diff = (date.fromisoformat(tx["fecha"]) - date.fromisoformat(p["fecha"][:10])).days
            difference = Decimal(tx["importe"]) - Decimal(p["importe"])
            tolerance = Decimal("0.03") if explorar_centavos else Decimal(0)
            if abs(difference) > tolerance or abs(diff) > 5:
                continue
            expected = MERCHANT.get(p["contacto"])
            candidates.append(
                {
                    **tx,
                    "dias": diff,
                    "diferenciaImporte": str(difference),
                    "comercioCoincide": bool(
                        expected and tx["comercio"] and expected in tx["comercio"].upper()
                    ),
                }
            )
        valid = [x for x in candidates if x["comercioCoincide"] and x["debitoExplicito"]]
        matrix.append(
            {
                "pago": p,
                "candidatos": candidates,
                "estado": (
                    "candidato_diferencia_centavos"
                    if len(valid) == 1 and Decimal(valid[0]["diferenciaImporte"]) != 0
                    else "debito_comercio_unico" if len(valid) == 1 else "pendiente"
                ),
                "evidencia": valid[0] if len(valid) == 1 else None,
            }
        )
    result = {
        "cobertura": coverage,
        "matriz": matrix,
        "titularidadFondos": "Sergio24/10/2026: HSBC Oscar administrada como fondos Condominio LSC.",
    }
    filename = "puentes-68-hsbc-explorar-centavos.json" if explorar_centavos else "puentes-68-hsbc-verificado.json"
    path = OUT / filename
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    good = [r for r in matrix if r["estado"] == "debito_comercio_unico"]
    print(
        json.dumps(
            {
                "pdf": len(coverage),
                "confirmados": len(good),
                "importe": str(sum((Decimal(r["pago"]["importe"]) for r in good), Decimal(0))),
                "pendientes": len(matrix) - len(good),
                "informe": str(path),
            }
        )
    )
    for r in matrix:
        if r["estado"] == "pendiente":
            print(
                json.dumps(
                    {
                        "pago": r["pago"]["id"],
                        "contacto": r["pago"]["contacto"],
                        "candidatos": [
                            {k: c[k] for k in ("fecha", "comercio", "dias")}
                            for c in r["candidatos"]
                        ],
                    }
                )
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--explorar-centavos", action="store_true")
    run(parser.parse_args().explorar_centavos)
