"""Cargill (258): comprobantes 2016 - 05/2020 ajustados al PDF original (Dropbox/Compras).

- Facturas/NC en US$ con la percepción IVA RG 2459 (1%) cargada como "Conceptos no gravados" con importes que no
  existen en el PDF (p.ej. FC 1125-45: 1.198,42 en lugar de 77,87): CNG 0 y PercepcionIVA = la del PDF.
- FC 1079-1972 cargada en pesos: es US$ 2.613,15 a TC 44,65. FC 1079-3151: TC 68,36 (no 68,18).
- Si después de eso el total no da, los precios de los renglones se escalan (centavos de 1126-11601 y 12180).
Coincide con el listado de cuenta corriente de Cargill del 04/05/2018 (FC 1125-1084 $ 51.725,59 = US$ 2.563,21 x 20,18).
Fuente: backups/cargill-conciliacion-20261020/pre2020_docs.json. Idempotente.
"""
import json
import re
from datetime import datetime
from pathlib import Path

import pdfplumber

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.vinculos.backup import backup_verificado

ROOT = Path(__file__).resolve().parents[2] / 'backups/cargill-conciliacion-20261020'
SIN_PDF = {'9759-00002352', '9759-00001116', '1080-00003327', '1126-00003235'}  # coinciden con la cuenta de Cargill


def total(i):
    return fetch_all('SELECT GranTotal g,TotalDetalleCompra d FROM dbo.vw_Cns_Total_Compra WHERE IdDeuda=?', (i,))[0]


def leer_pdf(path):
    t = '\n'.join(p.extract_text() or '' for p in pdfplumber.open(path).pages)
    perc = re.search(r'PERC\.IVA[^\n]*Base Sujeta\s*[\d.,]+\s*([\d.,]+)', t)
    iibb = re.search(r'PERC\.?\s*I(?:\.)?I(?:\.)?B(?:\.)?B[^\n]*Base Sujeta\s*[\d.,]+\s*([\d.,]+)', t)
    tc = re.search(r'fines fiscales es de \$\s*([\d.]+)', t)
    tot = re.search(r'TOTAL\s*(U\$S|\$)\s*([\d,]+\.\d\d)', t)
    num = lambda m: float(m.group(1).replace(',', '')) if m else 0.0
    return {'usd': tot.group(1) == 'U$S', 'total': float(tot.group(2).replace(',', '')), 'perc': num(perc), 'iibb': num(iibb),
            'tc': float(tc.group(1).rstrip('.')) if tc else None}


def main():
    _assert_target_is_wc()
    docs = json.load(open(ROOT / 'pre2020_docs.json'))
    plan = {}
    for r in docs:
        if r['n'] in SIN_PDF or not r['pdf']:
            continue
        p = leer_pdf(r['pdf'])
        signo = -1 if r['t'] == 'No' and r['g'] < 0 else 1
        if abs(total(r['id'])['g'] - signo * p['total']) > 0.005:
            plan[r['id']] = (r['n'], signo, p)
    if not plan:
        print('Nada pendiente.'); return
    m = ','.join(map(str, plan))
    antes = {'compras': fetch_all(f'SELECT * FROM dbo.Compras WHERE IdDeuda IN ({m})'), 'lineas': fetch_all(f'SELECT * FROM dbo.Det_Compras WHERE IdCompra IN ({m})')}
    assert all(c['IdContacto'] == 258 for c in antes['compras'])
    cab = {c['IdDeuda']: c for c in antes['compras']}
    audit = {'autorizacion': 'Sergio 20/10/2026: reconstruir Cargill hasta 2020 al centavo', 'plan': {str(k): v for k, v in plan.items()},
             'antes': antes, 'backup': backup_verificado('cargill-comprobantes-pre2020-036')}
    path = ROOT / f'comprobantes-pre2020-{datetime.now():%Y%m%d_%H%M%S}.json'
    path.write_text(json.dumps(audit, default=str, ensure_ascii=False, indent=1), encoding='utf-8')
    res = {}
    with reconciliation_transaction():
        for i, (nro, signo, p) in plan.items():
            st = []
            if p['usd'] and cab[i]['Moneda'] != 'Dolares':
                st += [("UPDATE dbo.Compras SET Moneda='Dolares' WHERE IdDeuda=?", (i,)),
                       ('UPDATE dbo.Det_Compras SET [Precio Unitario]=[Precio Unitario]/? WHERE IdCompra=?', (p['tc'], i))]
            if p['usd'] and p['tc']:
                st.append(('UPDATE dbo.Compras SET [Tipo de Cambio]=? WHERE IdDeuda=?', (p['tc'], i)))
            st.append(('UPDATE dbo.Compras SET [Conceptos no gravados]=0,PercepcionIVA=?,[Ingresos Brutos]=? WHERE IdDeuda=?',
                       (signo * p['perc'], signo * p['iibb'], i)))
            execute_write_transaction(st)
            t = total(i)
            objetivo = signo * p['total'] - (t['g'] - t['d'])
            if abs(objetivo - t['d']) > 0.004:
                execute_write_transaction([('UPDATE dbo.Det_Compras SET [Precio Unitario]=[Precio Unitario]*? WHERE IdCompra=?', (objetivo / t['d'], i))])
            res[i] = (nro, round(total(i)['g'], 4), signo * p['total'])
        malos = {i: r for i, r in res.items() if abs(r[1] - r[2]) > 0.005}
        assert not malos, malos
    audit['resultado'] = res
    path.write_text(json.dumps(audit, default=str, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(res))


if __name__ == '__main__': main()
