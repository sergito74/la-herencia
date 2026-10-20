"""Bayá: 16 comprobantes cuyo total no redondea al centavo del PDF original (portal).

Se escalan proporcionalmente los precios de todos sus renglones para que el total del
detalle sea el del PDF menos percepciones. Cantidades, IVA, destinos y campañas intactos.
Diferencias de origen: precios guardados con menos decimales que el original.
"""
import json
from datetime import datetime
from pathlib import Path

from src.db.connection import fetch_all, execute_write_transaction, reconciliation_transaction
from src.features.vinculos.backup import backup_verificado
from src.features.auditoria_cuentas.bimonetaria import invalidar

ROOT = Path(__file__).resolve().parents[2] / 'backups/baya-conciliacion-20261019'
# número -> total PDF (valor absoluto)
PDF = {'316796': 667.96, '316797': 12288.96, '357848': 835.01, '357849': 2167.88, '373600': 2320.68,
       '423769': 349.02, '432399': 885.89, '451187': 5591.17, '451189': 6861.45, '451191': 4389.28,
       '451193': 2553.81, '00077711': 63444.35, '00079316': 1148.75, '00107275': 94.13,
       '00101092': 338369.77, '00108915': 788300.99}
# (se agregan por número exacto para no confundir con otros documentos)


def doc(num):
    rows = fetch_all("SELECT c.IdDeuda,c.[Nro Documento],v.GranTotal,v.TotalDetalleCompra FROM dbo.Compras c JOIN dbo.vw_Cns_Total_Compra v ON v.IdDeuda=c.IdDeuda "
                     "WHERE c.IdContacto=226 AND c.[Nro Documento] LIKE ? AND c.[Nro Documento] NOT LIKE 'PEN%'", ('%' + num,))
    assert len(rows) == 1, (num, rows)
    return rows[0]


def lineas(i):
    return fetch_all('SELECT * FROM dbo.Det_Compras WHERE IdCompra=? ORDER BY IdDetalleCompra', (i,))


def main():
    docs = {n: doc(n) for n in PDF}
    before = {d['IdDeuda']: lineas(d['IdDeuda']) for d in docs.values()}
    audit = {'autorizacion': 'Sergio 20/10/2026: comprobantes hasta el centavo', 'docs': docs, 'antes': before,
             'backup': backup_verificado('baya-centavos2-036')}
    path = ROOT / f'centavos2-{datetime.now():%Y%m%d_%H%M%S}.json'
    path.write_text(json.dumps(audit, default=str, ensure_ascii=False, indent=2), encoding='utf-8')
    stmts = []
    for n, d in docs.items():
        signo = 1 if d['GranTotal'] > 0 else -1
        extras = d['GranTotal'] - d['TotalDetalleCompra']
        objetivo = signo * PDF[n] - extras
        f = objetivo / d['TotalDetalleCompra']
        assert abs(f - 1) < 0.002, (n, f)
        stmts += [('UPDATE dbo.Det_Compras SET [Precio Unitario]=? WHERE IdDetalleCompra=? AND IdCompra=?',
                   (r['Precio Unitario'] * f, r['IdDetalleCompra'], d['IdDeuda'])) for r in before[d['IdDeuda']]]
    with reconciliation_transaction():
        assert all(lineas(i) == l for i, l in before.items())
        execute_write_transaction(stmts)
        despues = {n: doc(n)['GranTotal'] for n in PDF}
        for n, t in despues.items():
            assert round(abs(t), 2) == PDF[n], (n, t)
    audit['despues'] = despues
    path.write_text(json.dumps(audit, default=str, ensure_ascii=False, indent=2), encoding='utf-8')
    invalidar()
    print(json.dumps({n: round(t, 4) for n, t in despues.items()}), flush=True)


if __name__ == '__main__': main()
