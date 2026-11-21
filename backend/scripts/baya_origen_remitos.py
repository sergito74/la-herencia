"""Bayá Casal: remito de origen de cada renglón de factura, leído del PDF (columna «Origen», p. ej. 0043 00017804).

Regla de oro (el comprobante del proveedor manda): la factura de Bayá dice qué remito factura cada renglón; la
auditoría de vínculos (auditoria_vinculos_remitos.py) usa este archivo como verdad para Bayá.

Solo lectura. Salida: backups/baya-origen-remitos.json (no va a git):
  {IdDeuda: {"nro": ..., "renglones": [{"articulo", "descripcion", "remito": "0043-00017804", "cantidad"}]}}
Uso (desde backend/): python -m scripts.baya_origen_remitos
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db.connection import fetch_all  # noqa: E402

BAYA = 226
COMPRAS = Path(r"C:\Users\Sergio\Dropbox\Giamigli de Bolivar SA\Compras")
SALIDA = Path(__file__).resolve().parents[2] / "backups" / "baya-origen-remitos.json"
# 1904 2,4 D 97% HERBIFEN ADVANCE x 20 L 0043 00058274 140,00 Litros 21 5,4375 761,25
RENGLON = re.compile(r"^(\d{3,5})\s+(.+?)\s+(\d{4})[\s-]+(\d{8})\s+(-?[\d.]+,\d+)\s+(\S+)")


def ruta(doc: str | None) -> Path | None:
    if not doc:
        return None
    d = doc.strip("#").split("#")[0].strip()
    p = Path(d)
    if not p.is_absolute():
        p = COMPRAS / d
    return p if p.exists() else None


def leer(p: Path) -> list[dict]:
    import pdfplumber
    out = []
    with pdfplumber.open(p) as pdf:
        for pg in pdf.pages:
            for linea in (pg.extract_text() or "").splitlines():
                m = RENGLON.match(linea.strip())
                if m:
                    out.append({"articulo": m.group(1), "descripcion": m.group(2).strip(), "remito": f"{m.group(3)}-{m.group(4)}",
                                "cantidad": float(m.group(5).replace(".", "").replace(",", "."))})
    return out


def main():
    previo = json.loads(SALIDA.read_text(encoding="utf-8")) if SALIDA.exists() else {}
    docs = fetch_all("SELECT IdDeuda AS id, [Nro Documento] AS nro, [Documento Original] AS doc FROM dbo.Compras "
                     "WHERE IdContacto = ? AND [Tipo documento] = 'Factura'", (BAYA,))
    res, sin_pdf, sin_origen = {}, 0, 0
    for c in docs:
        clave = str(c["id"])
        if clave in previo and previo[clave].get("renglones"):
            res[clave] = previo[clave]
            continue
        p = ruta(c["doc"])
        if p is None:
            sin_pdf += 1
            continue
        try:
            r = leer(p)
        except Exception as e:  # noqa: BLE001
            print("error", c["nro"], e)
            continue
        if not r:
            sin_origen += 1
        res[clave] = {"nro": c["nro"], "pdf": str(p), "renglones": r}
    SALIDA.parent.mkdir(exist_ok=True)
    SALIDA.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    con = sum(1 for v in res.values() if v["renglones"])
    print(f"facturas Bayá: {len(docs)}; con PDF leído: {len(res)}; con origen: {con}; sin PDF: {sin_pdf}; sin columna origen: {sin_origen}")


if __name__ == "__main__":
    main()
