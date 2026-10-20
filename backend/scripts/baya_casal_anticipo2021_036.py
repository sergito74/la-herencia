"""Anticipo BNA 16334 / RI3114: dolarizado en CA7479, CA7480 (02/07/2021) y CA53679 (17/08/2022).

Fuente: libro bimonetario del portal con aplicaciones (sin PDF de CA7479/7480 en el portal)
y PDF CA53679. Banco y pesos intactos; RI3114 del 09/06/2021 como fecha de reconocimiento.
"""
import hashlib
import json
from datetime import date, datetime
from decimal import Decimal as D
from pathlib import Path

from src.db.connection import fetch_all, execute_write_transaction, reconciliation_transaction, _reconciliation_connection
from src.features.vinculos.backup import backup_verificado
from src.features.auditoria_cuentas.bimonetaria import cargar_cuenta, invalidar

ROOT = Path(__file__).resolve().parents[2] / 'backups/baya-conciliacion-20261019'
RI = date(2021, 6, 9)
PARTES = [('CA0006-00007479', date(2021, 7, 2), D('488899.45'), D('95')),
          ('CA0006-00007480', date(2021, 7, 2), D('6457.72'), D('95.5')),
          ('CA0006-00053679', date(2022, 8, 17), D('8920.97'), D('130'))]
PORTAL_USD = [D('5146.31'), D('67.62'), D('68.62')]
FUENTES = ['portal-ctacte-2021-2022-aplicaciones-20261020.html', 'CA_0006_00053679.pdf']


def vals():
    return fetch_all("SELECT * FROM dbo.ValuacionProveedor WHERE Origen='Banco Nacion' AND IdOrigen=16334")


def main():
    before = cargar_cuenta(226, refrescar=True)
    fila = [r for r in before['filas'] if r['origenTipo'] == 'Banco Nacion' and r['idOrigen'] == 16334]
    assert len(fila) == 1 and D(str(fila[0]['creditoPesos'])) == sum(p[2] for p in PARTES)
    if vals():
        print('Valuación ya aplicada; sin cambios.'); return
    eventos = [(doc, f, (p / tc).quantize(D('0.01'))) for doc, f, p, tc in PARTES]
    assert [e[2] for e in eventos] == PORTAL_USD
    total = sum(PORTAL_USD)
    audit = {'autorizacion': 'Sergio 20/10/2026: puntos 1-3 de Bayá; portal solo lectura autorizado',
             'fila': fila, 'eventos': eventos, 'totalUSD': total,
             'fuentes': {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in FUENTES},
             'criterio': 'RI3114 $504.278,14 (09/06/2021) dolarizado en tres aplicaciones; CA53680 es neutra (-68,62/+68,62). Sin cambios en pesos.',
             'cuentaAntes': {k: v for k, v in before.items() if k != 'filas'},
             'backup': backup_verificado('baya-anticipo2021-036')}
    path = ROOT / f'anticipo2021-{datetime.now():%Y%m%d_%H%M%S}.json'
    path.write_text(json.dumps(audit, default=str, ensure_ascii=False, indent=2), encoding='utf-8')
    with reconciliation_transaction():
        assert not vals()
        if fetch_all("SELECT COL_LENGTH('dbo.ValuacionProveedor','FechaReconocimientoPesos') AS n")[0]['n'] is None:
            _reconciliation_connection.get().cursor().execute('ALTER TABLE dbo.ValuacionProveedor ADD FechaReconocimientoPesos date NULL')
        fuente = 'Bayá RI3114, CA7479/7480 (libro portal), CA53679'
        stmts = [('INSERT INTO dbo.ValuacionProveedor (Origen,IdOrigen,IdContacto,Dolares,Fuente,Nota,Usuario,FechaEfectoUSD,DocumentoEfectoUSD,FechaReconocimientoPesos) '
                  'VALUES (?,?,226,?,?,?,?,?,?,?)',
                  ('Banco Nacion', 16334, total, fuente, 'Anticipo en pesos dolarizado en tres aplicaciones; detalle en ValuacionProveedorEventos.',
                   'sergio', PARTES[0][1], PARTES[0][0], RI))]
        stmts += [('INSERT INTO dbo.ValuacionProveedorEventos (Origen,IdOrigen,IdContacto,Fecha,Documento,Dolares,Fuente,Usuario) VALUES (?,?,226,?,?,?,?,?)',
                   ('Banco Nacion', 16334, f, doc, d, fuente, 'sergio')) for doc, f, d in eventos]
        execute_write_transaction(stmts)
        audit['valuacionDespues'] = vals()
    invalidar()
    after = cargar_cuenta(226, refrescar=True)
    assert after['saldoPesos'] == before['saldoPesos']
    audit['cuentaDespues'] = {k: v for k, v in after.items() if k != 'filas'}
    audit['variacionSaldoUSD'] = round(after['saldoDolares'] - before['saldoDolares'], 2)
    path.write_text(json.dumps(audit, default=str, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'totalUSD': total, 'variacionSaldoUSD': audit['variacionSaldoUSD'],
                      'saldoUSD': after['saldoDolares'], 'backup': audit['backup']}, default=str))


if __name__ == '__main__': main()
