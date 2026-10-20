"""Cargill (258): facturas y notas existentes ajustadas al PDF original del portal (24 comprobantes).

- Percepción IVA RG 2408 (3%) e IIBB BA (0,1%) del PDF en Compras.PercepcionIVA / [Ingresos Brutos] (negativas en NC).
- Precios de los renglones escalados en proporción para que el total sea el del PDF (cantidades, destinos y campañas intactos).
- FC 5850-00002563 estaba en pesos: es US$ 5.279,98 a TC 98,47 (precios / TC).
Fuente: backups/cargill-conciliacion-20261020/docs_cruce.json + docs_parseados.json. Idempotente.
"""
import json
from datetime import datetime
from pathlib import Path

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.vinculos.backup import backup_verificado

ROOT = Path(__file__).resolve().parents[2] / 'backups/cargill-conciliacion-20261020'


def total(i):
    return fetch_all('SELECT GranTotal g,TotalDetalleCompra d FROM dbo.vw_Cns_Total_Compra WHERE IdDeuda=?', (i,))[0]


def main():
    _assert_target_is_wc()
    cruce = json.load(open(ROOT / 'docs_cruce.json'))
    docs = {v['nro']: v for v in json.load(open(ROOT / 'docs_parseados.json', encoding='utf-8')).values()}
    plan = {}
    for x in cruce['percep']:
        plan[x[1]] = docs[x[0]]
    for x in cruce['otro']:
        plan[x[11]] = docs[x[1]]
    for x in cruce['moneda']:
        plan[x[8]] = docs[x[0]]
    ids = list(plan)
    m = ','.join(map(str, ids))
    antes = {'compras': fetch_all(f'SELECT * FROM dbo.Compras WHERE IdDeuda IN ({m})'),
             'lineas': fetch_all(f'SELECT * FROM dbo.Det_Compras WHERE IdCompra IN ({m})')}
    assert all(c['IdContacto'] == 258 for c in antes['compras'])
    audit = {'autorizacion': 'Sergio 20/10/2026: Cargill, comprobantes al PDF', 'plan': {str(k): v for k, v in plan.items()},
             'antes': antes, 'backup': backup_verificado('cargill-comprobantes-pdf-036')}
    path = ROOT / f'comprobantes-pdf-{datetime.now():%Y%m%d_%H%M%S}.json'
    path.write_text(json.dumps(audit, default=str, ensure_ascii=False, indent=2), encoding='utf-8')
    res = {}
    with reconciliation_transaction():
        for i, d in plan.items():
            signo = -1 if d['tipo'] == 'NC' else 1
            st = []
            if d['nro'] == '5850-00002563':
                st += [("UPDATE dbo.Compras SET Moneda='Dolares',[Tipo de Cambio]=? WHERE IdDeuda=?", (d['tc'], i)),
                       ('UPDATE dbo.Det_Compras SET [Precio Unitario]=[Precio Unitario]/? WHERE IdCompra=?', (d['tc'], i))]
            st.append(('UPDATE dbo.Compras SET PercepcionIVA=?,[Ingresos Brutos]=? WHERE IdDeuda=?', (signo * d['percIVA'], signo * d['percIIBB'], i)))
            execute_write_transaction(st)
            t = total(i)
            objetivo = signo * d['total'] - signo * (d['percIVA'] + d['percIIBB']) - (t['g'] - t['d'] - signo * (d['percIVA'] + d['percIIBB']))
            if abs(t['d']) > 1e-9 and abs(objetivo - t['d']) > 0.004:
                execute_write_transaction([('UPDATE dbo.Det_Compras SET [Precio Unitario]=[Precio Unitario]*? WHERE IdCompra=?', (objetivo / t['d'], i))])
            res[i] = (d['nro'], round(total(i)['g'], 4), signo * d['total'])
        malos = {i: r for i, r in res.items() if abs(r[1] - r[2]) > 0.005}
        assert not malos, malos
    audit['resultado'] = res
    path.write_text(json.dumps(audit, default=str, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(res, default=str))


if __name__ == '__main__': main()
