"""Valúa canjes al crédito USD documentado por el proveedor; no cambia ventas."""
import hashlib
import json
from datetime import datetime
from pathlib import Path
from src.db.connection import fetch_all, execute_write_transaction, reconciliation_transaction
from src.features.vinculos.backup import backup_verificado
from src.features.auditoria_cuentas.bimonetaria import cargar_cuenta, invalidar

ROOT = Path(__file__).resolve().parents[2] / 'backups/baya-conciliacion-20261019'
DOCS = Path(r'C:\Users\Sergio\Documents\La Herencia\Administracion y gestion\Auditoria cuentas corrientes\Baya Casal\20261019')
PLAN = [(177, '330223253060', 3134051.64, 14020.94, '00078185'),
        (1230, '330223253039', 187546.31, 818.20, '00078182')]


def ventas():
    return fetch_all('SELECT * FROM dbo.[Venta Granos] WHERE IdVenta IN (177,1230) ORDER BY IdVenta')


def vals():
    return fetch_all("SELECT * FROM dbo.ValuacionProveedor WHERE Origen='Venta Granos' AND IdOrigen IN (177,1230) ORDER BY IdOrigen")


def main():
    before = ventas()
    assert len(before) == 2
    for row, (i, number, *_) in zip(before, PLAN):
        assert row['IdVenta'] == i and str(row['Nro Documento']) == number
    existing = vals()
    if existing:
        assert len(existing) == 2 and all(r['IdContacto'] == 226 and r['Dolares'] == p[3] for r, p in zip(existing, PLAN))
        print('Valuaciones ya aplicadas; sin cambios.'); return
    account_before = cargar_cuenta(226, refrescar=True)
    sources = [r for r in account_before['filas'] if r['origenTipo']=='Venta Granos' and r['idOrigen'] in (177,1230)]
    assert len(sources) == 2
    for row in sources:
        plan = next(p for p in PLAN if p[0] == row['idOrigen'])
        assert round(row['creditoOriginal'], 2) == plan[2] and str(row['fecha']) == '2023-05-03'
    audit = {'antes': before, 'cuentaAntes': account_before, 'plan': PLAN,
             'fuentes': {p[4]: hashlib.sha256((DOCS/f'CA_0006_{p[4]}.pdf').read_bytes()).hexdigest() for p in PLAN},
             'criterio': 'CA78185 crédito USD14020.94 incluye NC100961 parcial; CA78182 USD818.20 y3737.68 pesos deND90696. No cambiar netos ni convertir íntegramente porTCgenérico.',
             'autorizacion': 'Sergio: terminar auditoría y reproducir libro proveedor',
             'backup': backup_verificado('baya-canjes-valuacion-036')}
    path = ROOT/f'canjes-valuacion-{datetime.now():%Y%m%d_%H%M%S}.json'
    path.write_text(json.dumps(audit, default=str, ensure_ascii=False, indent=2), encoding='utf-8')
    with reconciliation_transaction():
        assert ventas() == before and not vals()
        execute_write_transaction([
            ('INSERT INTO dbo.ValuacionProveedor (Origen,IdOrigen,IdContacto,Dolares,Fuente,Nota,Usuario) VALUES (?,?,?,?,?,?,?)',
             ('Venta Granos', i, 226, usd, f'CA0006-{ca} 03/05/2023',
              'Libro USD del proveedor; neto comercial y componentes en pesos intactos. No representa nuevo cobro.', 'sergio'))
            for i, numero, neto, usd, ca in PLAN])
        assert ventas() == before
        audit['valuacionesDespues'] = vals()
    invalidar()
    after = cargar_cuenta(226, refrescar=True)
    assert after['saldoPesos'] == account_before['saldoPesos']
    for row in after['filas']:
        if row['origenTipo'] == 'Venta Granos' and row['idOrigen'] in (177,1230):
            old = next(r for r in sources if r['idOrigen']==row['idOrigen'])
            assert row['creditoOriginal'] == old['creditoOriginal'] and row['creditoPesos'] == old['creditoPesos']
    audit.update(cuentaDespues=after, variacionSaldoUSD=round(after['saldoDolares']-account_before['saldoDolares'],2))
    path.write_text(json.dumps(audit, default=str, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'variacionSaldoUSD': audit['variacionSaldoUSD'], 'netosSinCambios': True, 'backup': audit['backup']}, default=str))


if __name__ == '__main__': main()
