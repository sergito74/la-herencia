"""Bayá 2015-2020 (anterior al libro del portal): pagos en pesos valuados al TC de lo que cancelan.

El portal arranca en 2020 con saldo 0 (solo documentos migrados SD). Cada ciclo previo cierra
exacto en pesos al TC de sus facturas en dólares; el sistema pasaba cada movimiento en pesos con
el BNA del día y acumulaba USD 5.685 a favor. Por ciclo: TC = pesos netos / USD de las facturas,
y cada fila en pesos del ciclo se valúa a ese TC (el redondeo se absorbe en el mayor crédito).
Bancos, ventas, certificados y comprobantes intactos.
"""
import json
import sys
from datetime import date, datetime
from decimal import Decimal as D
from pathlib import Path

from src.db.connection import fetch_all, execute_write_transaction, reconciliation_transaction
from src.features.vinculos.backup import backup_verificado
from src.features.auditoria_cuentas.bimonetaria import cargar_cuenta, invalidar

ROOT = Path(__file__).resolve().parents[2] / 'backups/baya-conciliacion-20261019'
Q = D('0.01')
# (desde, hasta, USD de facturas que cancela, descripción)
CICLOS = [
    (date(2015, 11, 17), date(2015, 11, 20), None, 'FC106994 en pesos pagada con BNA 2810: neutro en USD'),
    (date(2017, 7, 17), date(2018, 6, 19), D('11308.87'), 'FC134770/134771 TC 17,50: canje granos 2017 + hacienda 2018 - devoluciones Bayá'),
    (date(2019, 5, 30), date(2019, 5, 30), D('8529.98'), 'FC168812 TC 45, FC183135/183136 TC 47'),
    (date(2019, 12, 27), date(2019, 12, 27), D('2890.09'), 'FC196397 TC 66'),
    (date(2020, 4, 2), date(2020, 6, 2), D('10280.22'), 'FC202518/202519 TC 70, FC202520 TC 65'),
    (date(2020, 6, 25), date(2020, 6, 25), D('6502.78'), 'FC215282 TC 73'),
]
FUENTE = 'Historia Bayá previa al portal: TC de las facturas canceladas'


def plan(filas):
    out = []
    for desde, hasta, usd, desc in CICLOS:
        rows = [r for r in filas if desde <= r['fecha'] <= hasta and r['moneda'] == 'Pesos']
        neto = sum(D(str(r['creditoOriginal'])) - D(str(r['deudaOriginal'])) for r in rows)
        if usd is None:
            vals = [(r, D('3647.75')) for r in rows]  # USD con que el sistema ya valuaba la factura
            out.append((desc, None, vals)); continue
        k = neto / usd
        vals = [(r, (D(str(r['creditoOriginal'] or r['deudaOriginal'])) / k).quantize(Q)) for r in rows]
        firmado = sum(v if r['creditoOriginal'] else -v for r, v in vals)
        mayor = max(range(len(vals)), key=lambda i: vals[i][0]['creditoOriginal'])
        r, v = vals[mayor]
        vals[mayor] = (r, v + (usd - firmado))
        assert sum(v if r['creditoOriginal'] else -v for r, v in vals) == usd
        out.append((desc, k.quantize(D('0.0001')), vals))
    return out


def main():
    before = cargar_cuenta(226, refrescar=True)
    filas = [r for r in before['filas'] if r['fecha'] < date(2020, 8, 1)]
    p = plan(filas)
    if len(sys.argv) > 1 and sys.argv[1] == '--dry':
        for d, k, vals in p:
            print(d, k)
            for r, v in vals: print('   ', r['fecha'], r['documento'][:14], r['numeroDocumento'], r['origenTipo'], r['idOrigen'], r['creditoOriginal'] or -r['deudaOriginal'], v)
        return
    keys = [(r['origenTipo'], r['idOrigen']) for _, _, vals in p for r, _ in vals]
    assert len(keys) == len(set(keys))
    existentes = fetch_all('SELECT Origen,IdOrigen FROM dbo.ValuacionProveedor WHERE IdContacto=226')
    assert not {(e['Origen'], int(e['IdOrigen'])) for e in existentes} & set(keys)
    audit = {'autorizacion': 'Sergio 20/10/2026: analizar y ajustar el período anterior al saldo inicial 2020 de Bayá',
             'plan': [(d, k, [(r['fecha'], r['documento'], r['numeroDocumento'], r['origenTipo'], r['idOrigen'],
                               r['creditoOriginal'] or -r['deudaOriginal'], v) for r, v in vals]) for d, k, vals in p],
             'cuentaAntes': {k: v for k, v in before.items() if k != 'filas'},
             'backup': backup_verificado('baya-historia-pre2020-036')}
    path = ROOT / f'historia-pre2020-{datetime.now():%Y%m%d_%H%M%S}.json'
    path.write_text(json.dumps(audit, default=str, ensure_ascii=False, indent=2), encoding='utf-8')
    with reconciliation_transaction():
        stmts = []
        for desc, k, vals in p:
            for r, v in vals:
                stmts.append(('INSERT INTO dbo.ValuacionProveedor (Origen,IdOrigen,IdContacto,Dolares,Fuente,Nota,Usuario) VALUES (?,?,226,?,?,?,?)',
                              (r['origenTipo'], r['idOrigen'], v, FUENTE, f'{desc}; TC del ciclo {k}', 'sergio')))
        execute_write_transaction(stmts)
    invalidar()
    after = cargar_cuenta(226, refrescar=True)
    assert after['saldoPesos'] == before['saldoPesos']
    corte = [r for r in after['filas'] if r['fecha'] <= date(2020, 6, 30)][-1]['saldoDolares']
    audit['cuentaDespues'] = {k: v for k, v in after.items() if k != 'filas'}
    audit['saldoUSD20200630'] = corte
    audit['variacionSaldoUSD'] = round(after['saldoDolares'] - before['saldoDolares'], 2)
    path.write_text(json.dumps(audit, default=str, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'saldoUSD20200630': corte, 'variacionSaldoUSD': audit['variacionSaldoUSD'],
                      'saldoUSD': after['saldoDolares'], 'backup': audit['backup']}, default=str), flush=True)


if __name__ == '__main__': main()
