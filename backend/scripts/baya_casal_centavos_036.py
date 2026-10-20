"""Bayá: comprobantes al centavo contra sus PDF originales (portal / Dropbox).

- FC357850: precios a 4 decimales del original (56,0004 / 103,0007 / 115,0008) -> USD 7.296,35.
- ND63227, NC78177, ND83045, ND92923, NC133873 (diferencias de cambio en pesos): neto del PDF
  repartido proporcionalmente entre sus renglones (mayores restos a centavos), como renglones
  financieros (Cantidad 1, ARS, Ajuste financiero) conservando destino, cultivo, campaña y rubro.
"""
import json
from datetime import datetime
from decimal import Decimal as D, ROUND_FLOOR
from pathlib import Path

from src.db.connection import fetch_all, execute_write_transaction, reconciliation_transaction
from src.features.vinculos.backup import backup_verificado
from src.features.auditoria_cuentas.bimonetaria import invalidar

ROOT = Path(__file__).resolve().parents[2] / 'backups/baya-conciliacion-20261019'
FC357850 = (2143514336, {'CRIPTON': 56.0004, 'FIERCE': 103.0007, 'CARFENTRAZONE': 115.0008}, 7296.35)
# IdDeuda: (neto PDF con signo, total PDF con signo)
NOTAS = {2143513252: (D('992.83'), 1201.32), 2143513254: (D('-14063.16'), -17016.42),
         2143513760: (D('1232.22'), 1490.99), 2143514112: (D('459994.48'), 556593.32),
         2143517445: (D('-2746775.40'), -3035186.82)}


def lineas(i):
    return fetch_all('SELECT * FROM dbo.Det_Compras WHERE IdCompra=? ORDER BY IdDetalleCompra', (i,))


def total(i):
    return fetch_all('SELECT GranTotal FROM dbo.vw_Cns_Total_Compra WHERE IdDeuda=?', (i,))[0]['GranTotal']


def reparto(rows, objetivo):
    netos = [D(str(r['Cantidad'])) * D(str(r['Precio Unitario'])) for r in rows]
    base = sum(netos)
    crudo = [n * objetivo / base for n in netos]
    cent = [(c * 100).to_integral_value(ROUND_FLOOR) / 100 for c in crudo]
    resto = int(((objetivo - sum(cent)) * 100).to_integral_value())
    orden = sorted(range(len(rows)), key=lambda k: crudo[k] - cent[k], reverse=True)
    for k in orden[:resto]:
        cent[k] += D('0.01')
    assert sum(cent) == objetivo
    return cent


def main():
    ids = [FC357850[0], *NOTAS]
    before = {i: {'lineas': lineas(i), 'total': total(i)} for i in ids}
    audit = {'autorizacion': 'Sergio 20/10/2026: investigar diferencias menores a $300, comprobantes al centavo',
             'antes': before, 'backup': backup_verificado('baya-centavos-036')}
    path = ROOT / f'centavos-{datetime.now():%Y%m%d_%H%M%S}.json'
    path.write_text(json.dumps(audit, default=str, ensure_ascii=False, indent=2), encoding='utf-8')
    stmts = []
    i, precios, _ = FC357850
    for r in before[i]['lineas']:
        clave = next(k for k in precios if r['Producto/Servicio'].startswith(k))
        stmts.append(('UPDATE dbo.Det_Compras SET [Precio Unitario]=? WHERE IdDetalleCompra=? AND IdCompra=?', (precios[clave], r['IdDetalleCompra'], i)))
    for i, (neto, _) in NOTAS.items():
        rows = before[i]['lineas']
        for r, imp in zip(rows, reparto(rows, neto)):
            stmts.append(('UPDATE dbo.Det_Compras SET Cantidad=1,Unidad=?,[Precio Unitario]=?,[Ajuste financiero]=1 WHERE IdDetalleCompra=? AND IdCompra=?',
                          ('ARS', float(imp), r['IdDetalleCompra'], i)))
    with reconciliation_transaction():
        assert all(lineas(i) == before[i]['lineas'] for i in ids)
        execute_write_transaction(stmts)
        despues = {i: total(i) for i in ids}
        assert round(despues[FC357850[0]], 2) == FC357850[2], despues[FC357850[0]]
        for i, (_, tot) in NOTAS.items():
            assert round(despues[i], 2) == tot, (i, despues[i])
        for i in ids:
            for a, b in zip(before[i]['lineas'], lineas(i)):
                for k in ('IdCentroCostos', 'IdDestino', 'IdRubro', 'IdCampaña', 'Campaña', 'IdFormulado', 'IVA'):
                    assert a.get(k) == b.get(k)
    audit['totalesDespues'] = despues
    path.write_text(json.dumps(audit, default=str, ensure_ascii=False, indent=2), encoding='utf-8')
    invalidar()
    print(json.dumps({str(k): round(v, 2) for k, v in despues.items()}), flush=True)


if __name__ == '__main__': main()
