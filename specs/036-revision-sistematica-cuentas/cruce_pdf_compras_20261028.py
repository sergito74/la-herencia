"""Cruce completo: todos los PDFs de Compras por número de comprobante contra WC. Solo lectura.

Uso (desde backend/): python claude_total.py <carpeta Compras> <salida.json>
"""
import json
import os
import re
import sys
from collections import Counter
from datetime import date, datetime

import pdfplumber

sys.path.insert(0, '.')
from src.db.connection import fetch_all  # noqa: E402

RAIZ, SALIDA = sys.argv[1], sys.argv[2]

idx = {}
for w in fetch_all(
        "SELECT c.IdDeuda, c.IdContacto, c.Fecha, c.[Nro Documento] nro, c.[Tipo documento] td, v.ImporteDocumento tot, "
        "k.[Razon Social] rs FROM dbo.Compras c JOIN dbo.vw_Compras_ImporteDocumento v ON v.IdDeuda = c.IdDeuda "
        "LEFT JOIN dbo.Contactos k ON k.IdContacto = c.IdContacto", ()):
    m = re.findall(r'\d+', w['nro'] or '')
    if len(m) >= 2:
        idx.setdefault((int(m[-2]), int(m[-1])), []).append(w)

ETIQUETAS = [
    r'Fecha de Emisi.n:?\s*(\d{2}/\d{2}/\d{4})',
    r'Fecha Emisi.n:?\s*(\d{2}/\d{2}/\d{4})',
    r'C.digo N.?\s*\d+\s*Fecha:?\s*(\d{2}/\d{2}/\d{4})',
    r'\d{4,5}-\d{8}\s*(?:A\s*)?Fecha:?\s*(\d{2}/\d{2}/\d{2,4})',
    r'\bFECHA:?\s*(\d{2}/\d{2}/\d{2,4})',
    r'\bFecha:\s*(\d{2}/\d{2}/\d{4})',
]


def fecha_pdf(t):
    for p in ETIQUETAS:
        m = re.search(p, t)
        if m:
            s = m.group(1)
            fmt = '%d/%m/%Y' if len(s) == 10 else '%d/%m/%y'
            try:
                return datetime.strptime(s, fmt).date(), p
            except ValueError:
                pass
    return None, None


def nro_pdf(t):
    m = re.search(r'Punto de Venta:?\s*(\d+)\s*Comp\.? ?Nro:?\s*(\d+)', t)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r'\b(\d{4,5})\s?-\s?(\d{8})\b', t)
    return (int(m.group(1)), int(m.group(2))) if m else None


res, cuenta = [], Counter()
for carpeta, _, nombres in os.walk(RAIZ):
    for n in nombres:
        if not n.lower().endswith('.pdf'):
            continue
        ruta = os.path.join(carpeta, n)
        try:
            with pdfplumber.open(ruta) as pdf:
                t = pdf.pages[0].extract_text() or ''
        except Exception:  # noqa: BLE001
            cuenta['ilegible'] += 1
            continue
        nro = nro_pdf(t)
        if not nro:
            cuenta['sin_numero'] += 1
            continue
        hits = idx.get(nro, [])
        if not hits:
            cuenta['numero_no_en_wc'] += 1
            res.append({'estado': 'NO_EN_WC', 'archivo': os.path.relpath(ruta, RAIZ), 'nro': nro})
            continue
        f, patron = fecha_pdf(t)
        if not f:
            cuenta['sin_fecha'] += 1
            continue
        for w in hits:
            fw = w['Fecha'].date() if w['Fecha'] else None
            if fw != f:
                cuenta['fecha_distinta'] += 1
                res.append({'estado': 'FECHA_DISTINTA', 'archivo': os.path.relpath(ruta, RAIZ), 'nro': nro,
                            'fechaPdf': str(f), 'patron': patron, 'idDeuda': w['IdDeuda'], 'ct': w['IdContacto'],
                            'rs': w['rs'], 'fechaWc': str(fw), 'nroWc': w['nro'], 'tot': float(w['tot'] or 0),
                            'totEnPdf': any(s in t for s in {
                                f"{float(w['tot'] or 0):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                                f"{float(w['tot'] or 0):.2f}".replace('.', ',')}),
                            'dias': (fw - f).days if fw else None, 'multiples': len(hits)})
            else:
                cuenta['ok'] += 1
json.dump(res, open(SALIDA, 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
print(dict(cuenta))
