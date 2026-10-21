"""Cargill (258): cada nota de crédito o débito (US$ o pesos) vinculada a la factura que cita (CompraDocumentosRelacionados).
Fuente: el PDF de la NC ("Factura por ventas A 1125-000002786" / "FACTURA A 5850-00009578"); si el sistema no tiene el
PDF se usa el bajado del portal (backups/cargill-conciliacion-20261020/portal_docs). La NC 1125-1549 anula la ND 1126-14654 (reajuste de la FC 2786). La NC 9759-1116 anula la ND
9759-2352 y la 9759-1323 la 9759-2850 (mismo día, mismo importe). Con el vínculo, la valuación en dólares aplica la NC
a su factura (regla usd-tc-comprobante). Idempotente.
"""
import json
import os
import re
from pathlib import Path

import pdfplumber

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction

ROOT = Path(__file__).resolve().parents[2] / 'backups/cargill-conciliacion-20261020'
FIJAS = {'9759-00001116': '9759-00002352', '9759-00001323': '9759-00002850', '1125-00001549': '1125-00002786'}  # 1549 anula la ND 14654 (reajuste FC 2786)


def pdf(doc, nro, portal):
    p = (doc or '').split('#')[0]
    if p:
        q = os.path.normpath(os.path.join(r'C:\dev\LaHerencia\backend', p)) if not os.path.isabs(p) else p
        if os.path.exists(q):
            return q
    d = portal.get(nro)
    if d:
        q = Path(d['archivo'])
        return str(q if q.is_absolute() else (Path(__file__).resolve().parents[1] / q).resolve())
    return None


def main():
    _assert_target_is_wc()
    portal = {v['nro']: v for v in json.load(open(ROOT / 'docs_parseados.json', encoding='utf-8')).values() if v.get('nro')}
    ids = {x['n']: x['i'] for x in fetch_all('SELECT IdDeuda i,[Nro Documento] n FROM dbo.Compras WHERE IdContacto=258')}
    pares, sin = [], []
    for x in fetch_all("SELECT IdDeuda i,[Nro Documento] n,[Documento Original] d FROM dbo.Compras WHERE IdContacto=258 "
                       "AND [Tipo documento] LIKE 'Nota de%' AND [Nro Documento] NOT LIKE 'X%' AND [Nro Documento] NOT LIKE 'R%' AND [Nro Documento] NOT LIKE 'AJ%'"):
        ref = FIJAS.get(x['n'])
        if not ref:
            p = pdf(x['d'], x['n'], portal)
            if p:
                t = '\n'.join(pg.extract_text() or '' for pg in pdfplumber.open(p).pages)
                m = (re.search(r'Factura por ventas A (\d{4})-0*(\d+)', t) or re.search(r'FACTURA A (\d{4})-0*(\d+)', t)
                     or re.search(r'Nota de (?:Cr.dito|D.bito) (?:por ventas )?A (\d{4})-0*(\d+)', t))
                if m:
                    ref = f'{m.group(1)}-{int(m.group(2)):08d}'
        if not ref:  # notas cargadas en esta revisión citan la factura en el renglón ("Dif. tipo cambio FC 5850-1569")
            r = fetch_all("SELECT TOP 1 [Producto/Servicio] p FROM dbo.Det_Compras WHERE IdCompra=?", (x['i'],))
            m = re.search(r'(?:FC|ND) (\d{4})-0*(\d+)', r[0]['p']) if r else None
            if m:
                ref = f'{m.group(1)}-{int(m.group(2)):08d}'
        if ref and ref in ids:
            pares.append((x['i'], ids[ref], x['n'], ref))
        else:
            sin.append((x['n'], ref))
    nuevos = [p for p in pares if not fetch_all('SELECT 1 x FROM dbo.CompraDocumentosRelacionados WHERE IdCompra=? AND IdCompraRelacionada=?', p[:2])]
    if nuevos:
        with reconciliation_transaction():
            execute_write_transaction([('INSERT INTO dbo.CompraDocumentosRelacionados (IdCompra,IdCompraRelacionada,CreatedAt) VALUES (?,?,SYSDATETIME())', p[:2]) for p in nuevos])
    print(len(nuevos), 'vínculos nuevos de', len(pares), '; sin factura:', sin)


if __name__ == '__main__': main()
