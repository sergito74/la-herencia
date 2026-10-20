"""Cargill (258): cierre al centavo de cada comprobante contra los pesos del libro del portal (Sergio 20/10/2026: las
cuentas con saldo vivo se cierran contra el proveedor, sin umbral).

Cargill pesifica las facturas en US$ con el importe sin redondear x TC; el sistema tiene el US$ del PDF (2 decimales).
- Notas sin renglones (solo percepción): se ajusta la percepción.
- Se mantiene el TC fiscal del PDF y se escalan los precios de los renglones para que importe x TC = pesos de Cargill
  (en US$ la diferencia con el PDF es menor a un centavo: es el US$ sin redondear que usa Cargill).
Solo comprobantes que están en el portal (desde 04/06/2020). Idempotente.
"""
import collections
import csv
import json
from datetime import datetime
from pathlib import Path

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.vinculos.backup import backup_verificado

ROOT = Path(__file__).resolve().parents[2] / 'backups/cargill-conciliacion-20261020'


def sistema():
    return {x['n']: x for x in fetch_all(
        "SELECT c.IdDeuda i,c.[Nro Documento] n,c.Moneda m,c.[Tipo de Cambio] tc,t.GranTotal g,t.TotalDetalleCompra d FROM dbo.Compras c "
        "JOIN dbo.vw_Cns_Total_Compra t ON t.IdDeuda=c.IdDeuda WHERE c.IdContacto=258 AND c.Fecha>='2020-06-04'")}


def main():
    _assert_target_is_wc()
    portal = collections.defaultdict(float)
    for x in csv.DictReader(open(ROOT / 'portal-ledger-completo.csv', encoding='utf-8')):
        if x['documentType'].strip().startswith(('FACT', 'NOTA')):
            ld = x['legalDocument']
            portal[ld[:4] + '-' + ld[-8:]] += float(x['cargillBalance']) - float(x['customerBalance'])  # + = deuda nuestra
    S = sistema()
    plan = {}
    for n, p in portal.items():
        s = S.get(n)
        if s and abs(s['g'] * (s['tc'] if s['m'] == 'Dolares' else 1) - p) >= 0.005:
            plan[n] = (s, round(p, 2))
    if not plan:
        print('Nada pendiente.'); return
    audit = {'plan': {k: v for k, v in plan.items()}, 'backup': backup_verificado('cargill-centavos-036')}
    (ROOT / f'centavos-{datetime.now():%Y%m%d_%H%M%S}.json').write_text(json.dumps(audit, default=str, indent=1), encoding='utf-8')
    with reconciliation_transaction():
        for n, (s, p) in plan.items():
            k = s['tc'] if s['m'] == 'Dolares' else 1
            objetivo = p / k - (s['g'] - s['d'])
            if abs(s['d']) > 1e-9:
                execute_write_transaction([('UPDATE dbo.Det_Compras SET [Precio Unitario]=[Precio Unitario]*? WHERE IdCompra=?', (objetivo / s['d'], s['i']))])
            else:  # nota sin renglones (solo percepción): se ajusta la percepción
                execute_write_transaction([('UPDATE dbo.Compras SET PercepcionIVA=PercepcionIVA+? WHERE IdDeuda=?', (p / k - s['g'], s['i']))])
        S = sistema()
        malos = {n: (round(S[n]['g'] * (S[n]['tc'] if S[n]['m'] == 'Dolares' else 1), 4), p) for n, (s, p) in plan.items()
                 if abs(S[n]['g'] * (S[n]['tc'] if S[n]['m'] == 'Dolares' else 1) - p) >= 0.005}
        assert not malos, malos
    print(len(plan), 'comprobantes al centavo')


if __name__ == '__main__': main()
