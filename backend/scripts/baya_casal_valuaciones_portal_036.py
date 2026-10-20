"""Bayá: créditos USD de 13 grupos de pago iguales al libro bimonetario del portal.

Fuente: cuenta corriente del portal con aplicaciones (consulta solo lectura 20/10/2026,
backups/baya-conciliacion-20261019/portal-ctacte-completo-20261020.txt). Por cada fuente
se registra el USD que el proveedor acreditó (RI/CA/RG); las retenciones que el proveedor
tomó solo en pesos quedan en 0 USD. Si un CA aplicó banco y retención juntos sin separar,
se reparte proporcional a los pesos. Banco, tarjetas, certificados y aplicaciones intactos.
"""
import hashlib
import json
from datetime import date, datetime
from decimal import Decimal as D
from pathlib import Path

from src.db.connection import fetch_all, execute_write_transaction, reconciliation_transaction
from src.features.vinculos.backup import backup_verificado
from src.features.auditoria_cuentas.bimonetaria import cargar_cuenta, invalidar

ROOT = Path(__file__).resolve().parents[2] / 'backups/baya-conciliacion-20261019'
PORTAL = ROOT / 'portal-ctacte-completo-20261020.txt'
Q = D('0.01')


def prop(total, parte, todo):
    return (D(total) * D(parte) / D(todo)).quantize(Q)


R234 = prop('11680.98', '348743.53', '16181773.08')
R240 = prop('26116.21', '621445.56', '37584098.97')
# (origen, id, USD proveedor, fecha efecto, documento)
PLAN = [
    ('Banco Nacion', 16333, D('1324.04'), date(2021, 4, 23), 'RI0006-00000888'),
    ('Galicia', 5, D('8094.74') - D('84.35'), date(2021, 6, 1), 'CA0006-00004114'),
    ('Retenciones', 9, D('84.35'), date(2021, 6, 1), 'RG0001-00000005'),
    ('Galicia', 423, D('2438.00'), date(2021, 7, 2), 'CA0006-00007430'),
    ('Galicia', 466, D('31282.53') - D('512.32'), date(2021, 6, 11), 'CA0006-00005213'),
    ('Retenciones', 13, D('512.32'), date(2021, 6, 11), 'RG0001-00000009'),
    ('Tarjetas', 5583, D('4659.47') - D('39.16'), date(2022, 5, 26), 'RI0006-00016209'),
    ('Retenciones', 49, D('39.16'), date(2022, 5, 20), 'RG0001-00000010'),
    ('Tarjetas', 654, D('17877.10'), date(2022, 7, 4), 'RI0006-00017648'),
    ('Galicia', 719, D('820.81'), date(2022, 10, 14), 'RI0006-00019407/CA0006-00059135'),
    ('Galicia', 1268, D('2185.86'), date(2023, 8, 2), 'CA0006-00085473'),
    ('Retenciones', 100, D('0'), date(2023, 6, 22), 'RG0001-00000026 (solo pesos)'),
    ('Galicia', 1324, D('1191.15'), date(2023, 8, 2), 'CA0006-00085478'),
    ('Galicia', 1673, D('624.41'), date(2024, 1, 18), 'RI0006-00037873'),
    ('Galicia', 2979, D('885.89') - D('11.80'), date(2025, 12, 30), 'RI0006-00069101'),
    ('Retenciones', 221, D('11.80'), date(2025, 12, 30), 'RG0001-00000039'),
    ('Galicia', 3251, D('11680.98') - R234, date(2026, 5, 29), 'CA0006-00144661'),
    ('Retenciones', 234, R234, date(2026, 5, 29), 'CA0006-00144661'),
    ('Retenciones', 240, R240, date(2026, 6, 10), 'CA0006-00145870'),
]
# Galicia 3274: eventos según CA del portal (CA145870 sin la parte de RG19).
EVENTOS_3274 = [('CA0006-00145870', date(2026, 6, 10), D('26116.21') - R240),
                ('CA0006-00145871', date(2026, 6, 10), D('182.49')),
                ('CA0006-00146076', date(2026, 6, 16), D('2312.47'))]
FUENTE = 'Libro bimonetario portal Bayá 20/10/2026'


def vals():
    keys = [(o, i) for o, i, *_ in PLAN] + [('Galicia', 3274)]
    rows = fetch_all('SELECT * FROM dbo.ValuacionProveedor WHERE IdContacto=226')
    return [r for r in rows if (r['Origen'], int(r['IdOrigen'])) in keys]


def eventos():
    return fetch_all("SELECT * FROM dbo.ValuacionProveedorEventos WHERE Origen='Galicia' AND IdOrigen=3274 ORDER BY IdEvento")


def main():
    before = cargar_cuenta(226, refrescar=True)
    fechas = {(r['origenTipo'], r['idOrigen']): r['fecha'] for r in before['filas']}
    for o, i, *_ in PLAN:
        assert (o, i) in fechas, (o, i)
    old_vals, old_ev = vals(), eventos()
    existentes = {(r['Origen'], int(r['IdOrigen'])) for r in old_vals}
    assert existentes <= {('Galicia', 3274), ('Retenciones', 240)}, existentes
    audit = {'autorizacion': 'Sergio 20/10/2026: replicar la cuenta del proveedor con todo lo facturado; portal solo lectura autorizado',
             'portalSha256': hashlib.sha256(PORTAL.read_bytes()).hexdigest(), 'plan': PLAN, 'eventos3274': EVENTOS_3274,
             'valuacionesAntes': old_vals, 'eventosAntes': old_ev,
             'cuentaAntes': {k: v for k, v in before.items() if k != 'filas'},
             'backup': backup_verificado('baya-valuaciones-portal-036')}
    path = ROOT / f'valuaciones-portal-{datetime.now():%Y%m%d_%H%M%S}.json'
    path.write_text(json.dumps(audit, default=str, ensure_ascii=False, indent=2), encoding='utf-8')
    with reconciliation_transaction():
        assert vals() == old_vals and eventos() == old_ev
        stmts = []
        for o, i, usd, f, doc in PLAN:
            efecto = f if f >= fechas[(o, i)] else None
            if (o, i) in existentes:
                stmts.append(('UPDATE dbo.ValuacionProveedor SET Dolares=?,Fuente=?,FechaEfectoUSD=?,DocumentoEfectoUSD=? WHERE Origen=? AND IdOrigen=?',
                              (usd, FUENTE, efecto, doc if efecto else None, o, i)))
            else:
                stmts.append(('INSERT INTO dbo.ValuacionProveedor (Origen,IdOrigen,IdContacto,Dolares,Fuente,Nota,Usuario,FechaEfectoUSD,DocumentoEfectoUSD) VALUES (?,?,226,?,?,?,?,?,?)',
                              (o, i, usd, FUENTE, f'USD acreditado por el proveedor ({doc}).', 'sergio', efecto, doc if efecto else None)))
        total = sum(e[2] for e in EVENTOS_3274)
        stmts.append(("UPDATE dbo.ValuacionProveedor SET Dolares=?,Fuente=? WHERE Origen='Galicia' AND IdOrigen=3274", (total, FUENTE)))
        stmts.append(("DELETE FROM dbo.ValuacionProveedorEventos WHERE Origen='Galicia' AND IdOrigen=3274", ()))
        stmts += [('INSERT INTO dbo.ValuacionProveedorEventos (Origen,IdOrigen,IdContacto,Fecha,Documento,Dolares,Fuente,Usuario) VALUES (?,?,226,?,?,?,?,?)',
                   ('Galicia', 3274, f, doc, d, FUENTE, 'sergio')) for doc, f, d in EVENTOS_3274]
        execute_write_transaction(stmts)
        audit['valuacionesDespues'] = vals()
        audit['eventosDespues'] = eventos()
    path.write_text(json.dumps(audit, default=str, ensure_ascii=False, indent=2), encoding='utf-8')
    invalidar()
    after = cargar_cuenta(226, refrescar=True)
    assert after['saldoPesos'] == before['saldoPesos']
    audit['cuentaDespues'] = {k: v for k, v in after.items() if k != 'filas'}
    audit['variacionSaldoUSD'] = round(after['saldoDolares'] - before['saldoDolares'], 2)
    path.write_text(json.dumps(audit, default=str, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'variacionSaldoUSD': audit['variacionSaldoUSD'], 'saldoUSD': after['saldoDolares'],
                      'backup': audit['backup']}, default=str), flush=True)


if __name__ == '__main__': main()
