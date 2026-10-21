"""Vincula notas de crédito/débito en dólares con el comprobante que anulan o ajustan (CompraDocumentosRelacionados),
para la valuación en dólares al TC del comprobante (regla usd-tc-comprobante, Sergio 21/10/2026).

Por cada NC/ND en US$ del contacto, en este orden:
  1. referencia en el PDF: "anula ND 5210", "Factura por ventas A 1125-000002786", "FACTURA A 5850-00009578";
  2. si no hay, el comprobante en US$ de signo contrario con el mismo importe en dólares y el mismo tipo de cambio,
     anterior o del mismo día, si es único.
Solo agrega vínculos que no existan. Uso: python -m scripts.vincular_notas_usd_036 <IdContacto> [--aplicar]
"""
import os
import re
import sys

import pdfplumber

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction

HOME = r'C:\Users\Sergio'


def ruta(d):
    p = (d or '').split('#')[0]
    if not p:
        return None
    if not os.path.isabs(p):
        p = os.path.normpath(os.path.join(r'C:\dev\LaHerencia\backend', p))
    if os.path.exists(p):
        return p
    for k in ('Dropbox', 'Documents'):
        i = p.find(k)
        if i >= 0 and os.path.exists(os.path.join(HOME, p[i:])):
            return os.path.join(HOME, p[i:])
    return None


def numero(n):
    m = re.search(r'(\d{1,5})\s*-\s*0*(\d+)', n or '')
    return (int(m.group(1)), int(m.group(2))) if m else None


def main(contacto, aplicar):
    _assert_target_is_wc()
    docs = fetch_all("SELECT c.IdDeuda i,c.Fecha f,c.[Tipo documento] t,c.[Nro Documento] n,c.Moneda m,c.[Tipo de Cambio] tc,c.[Documento Original] d,"
                     "t.GranTotal g FROM dbo.Compras c JOIN dbo.vw_Cns_Total_Compra t ON t.IdDeuda=c.IdDeuda WHERE c.IdContacto=?", (contacto,))
    por_num = {numero(x['n']): x for x in docs if numero(x['n'])}
    pares = []
    for x in docs:
        if x['m'] != 'Dolares' or not (x['t'] or '').startswith('Nota'):
            continue
        ref = None
        p = ruta(x['d'])
        if p:
            t = '\n'.join(pg.extract_text() or '' for pg in pdfplumber.open(p).pages)
            m = (re.search(r'(?i)anula\s+(?:la\s+)?(?:ND|NC|FC|factura|nota de d.bito|nota de cr.dito)\s*(?:N.\s*)?(\d{1,5}\s*-\s*\d+|\d+)', t)
                 or re.search(r'Factura por ventas A (\d{4}-\d+)', t) or re.search(r'FACTURA A (\d{4,5}-\d+)', t))
            if m:
                g = m.group(1)
                if '-' in g:
                    ref = por_num.get(numero(g))
                else:  # solo el número: el comprobante en US$ con ese número
                    cand = [y for y in docs if numero(y['n']) and numero(y['n'])[1] == int(g) and y['i'] != x['i']]
                    ref = cand[0] if len(cand) == 1 else None
        if ref is None:
            cand = [y for y in docs if y['i'] != x['i'] and y['m'] == 'Dolares' and y['f'] <= x['f'] and abs(abs(y['g']) - abs(x['g'])) < 0.005
                    and abs((y['tc'] or 0) - (x['tc'] or 0)) < 0.0001 and (y['g'] > 0) != (x['g'] > 0)]
            ref = cand[0] if len(cand) == 1 else None
        if ref is not None:
            pares.append((x['i'], ref['i'], x['n'], ref['n']))
    nuevos = [p for p in pares if not fetch_all('SELECT 1 x FROM dbo.CompraDocumentosRelacionados WHERE (IdCompra=? AND IdCompraRelacionada=?) '
                                                'OR (IdCompra=? AND IdCompraRelacionada=?)', (p[0], p[1], p[1], p[0]))]
    for p in nuevos:
        print('  ', p[2], '->', p[3])
    if aplicar and nuevos:
        with reconciliation_transaction():
            execute_write_transaction([('INSERT INTO dbo.CompraDocumentosRelacionados (IdCompra,IdCompraRelacionada,CreatedAt) VALUES (?,?,SYSDATETIME())', p[:2])
                                       for p in nuevos])
    print(len(nuevos), 'vínculos nuevos', '(aplicados)' if aplicar else '(simulación)')


if __name__ == '__main__':
    main(int(sys.argv[1]), '--aplicar' in sys.argv)
