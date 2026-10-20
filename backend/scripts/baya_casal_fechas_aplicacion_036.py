"""Bayá: fechas en que el proveedor reconoció y aplicó cada pago (libro del portal).

Cheques diferidos: Bayá los acredita al recibirlos y el banco los debita después. Se registra
FechaReconocimientoPesos (recibo RI) y FechaEfectoUSD (aplicación CA/RI); el débito bancario y
los importes en pesos quedan intactos. Así el saldo coincide con el portal en cada fecha.
"""
import json
from datetime import date, datetime
from pathlib import Path

from src.db.connection import fetch_all, execute_write_transaction, reconciliation_transaction
from src.features.vinculos.backup import backup_verificado
from src.features.auditoria_cuentas.bimonetaria import cargar_cuenta, invalidar

ROOT = Path(__file__).resolve().parents[2] / 'backups/baya-conciliacion-20261019'
FUENTE = 'Libro bimonetario portal Bayá 20/10/2026 (fechas)'
# (origen, id): (USD o None para conservar, reconocimiento pesos, efecto USD, documento)
PLAN = {
    ('Galicia', 423): (None, date(2021, 6, 11), date(2021, 6, 11), 'RI0006-00003225'),
    ('Galicia', 466): (None, date(2021, 6, 11), date(2021, 6, 11), 'RI0006-00003209/CA0006-00005213'),
    ('Galicia', 719): (None, None, date(2022, 8, 22), 'RI0006-00019407'),
    ('Retenciones', 106): (3.86, None, date(2024, 1, 11), 'RG0001-00000033'),
    ('Galicia', 1621): (910.21, None, date(2024, 1, 2), 'CA0006-00095307'),
    ('Retenciones', 122): (9.65, None, date(2024, 1, 2), 'CA0006-00095307'),
    ('Galicia', 2580): (2287.13, date(2024, 8, 1), date(2024, 8, 1), 'RI0006-00046164'),
    ('Galicia', 2581): (3522.49, date(2024, 8, 1), date(2024, 8, 1), 'RI0006-00046164'),
    ('Galicia', 3251): (None, date(2026, 4, 15), date(2026, 5, 29), 'RI0006-00074242/CA0006-00144661'),
}
EVENTOS_423 = [(date(2021, 6, 11), 'RI0006-00003225', 2435.91), (date(2021, 7, 2), 'CA0006-00007430', 2.09)]
EVENTOS_719 = [(date(2022, 8, 22), 'RI0006-00019407', 822.80), (date(2022, 10, 14), 'CA0006-00059135', -1.99)]


def vals():
    rows = fetch_all('SELECT * FROM dbo.ValuacionProveedor WHERE IdContacto=226')
    return {(r['Origen'], int(r['IdOrigen'])): r for r in rows if (r['Origen'], int(r['IdOrigen'])) in PLAN}


def main():
    before = cargar_cuenta(226, refrescar=True)
    old = vals()
    assert abs(float(old[('Galicia', 719)]['Dolares']) - sum(e[2] for e in EVENTOS_719)) < 1e-6
    assert not fetch_all("SELECT 1 x FROM dbo.ValuacionProveedorEventos WHERE Origen='Galicia' AND IdOrigen=719")
    audit = {'autorizacion': 'Sergio 20/10/2026: cuenta Bayá replicada antes de pendientes', 'antes': {str(k): v for k, v in old.items()},
             'backup': backup_verificado('baya-fechas-aplicacion-036')}
    path = ROOT / f'fechas-aplicacion-{datetime.now():%Y%m%d_%H%M%S}.json'
    path.write_text(json.dumps(audit, default=str, ensure_ascii=False, indent=2), encoding='utf-8')
    stmts = []
    for (o, i), (usd, rec, ef, doc) in PLAN.items():
        if (o, i) in old:
            stmts.append(('UPDATE dbo.ValuacionProveedor SET Dolares=COALESCE(?,Dolares),FechaReconocimientoPesos=?,FechaEfectoUSD=?,DocumentoEfectoUSD=? WHERE Origen=? AND IdOrigen=? AND IdContacto=226',
                          (usd, rec, ef, doc, o, i)))
        else:
            assert usd is not None, (o, i)
            stmts.append(('INSERT INTO dbo.ValuacionProveedor (Origen,IdOrigen,IdContacto,Dolares,Fuente,Nota,Usuario,FechaEfectoUSD,DocumentoEfectoUSD,FechaReconocimientoPesos) VALUES (?,?,226,?,?,?,?,?,?,?)',
                          (o, i, usd, FUENTE, f'USD y fechas del proveedor ({doc}).', 'sergio', ef, doc, rec)))
    stmts += [('INSERT INTO dbo.ValuacionProveedorEventos (Origen,IdOrigen,IdContacto,Fecha,Documento,Dolares,Fuente,Usuario) VALUES (?,?,226,?,?,?,?,?)',
               (o, i, f, d, u, FUENTE, 'sergio')) for (o, i), ev in ((('Galicia', 719), EVENTOS_719), (('Galicia', 423), EVENTOS_423)) for f, d, u in ev]
    with reconciliation_transaction():
        assert vals() == old
        execute_write_transaction(stmts)
    invalidar()
    after = cargar_cuenta(226, refrescar=True)
    assert after['saldoPesos'] == before['saldoPesos']
    audit['despues'] = {str(k): v for k, v in vals().items()}
    audit['saldoUSD'] = (before['saldoDolares'], after['saldoDolares'])
    path.write_text(json.dumps(audit, default=str, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'saldoUSD': audit['saldoUSD'], 'backup': audit['backup']}, default=str), flush=True)


if __name__ == '__main__': main()
