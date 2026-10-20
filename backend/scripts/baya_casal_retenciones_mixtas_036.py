"""Replica porción USD de RG25/2023 y RG22/2024 sin reducir certificados."""
import hashlib
import json
from datetime import datetime
from pathlib import Path

from src.db.connection import fetch_all, execute_write_transaction, reconciliation_transaction
from src.features.vinculos.backup import backup_verificado
from src.features.auditoria_cuentas.bimonetaria import cargar_cuenta, invalidar

ROOT = Path(__file__).resolve().parents[2] / 'backups/baya-conciliacion-20261019'
PLAN = [(99, '0000-2023-000025', 157357.15, 245.89, 96598.84, 'RG00000025_recibo.pdf', 'RI30422/RG25 14/06/2023'),
        (153, '0000-2024-000022', 139879.45, 3.36, 136812.57, 'RG00000022_recibo.pdf', 'RI44686/RG22 28/06/2024')]


def retenciones():
    return fetch_all('SELECT * FROM dbo.Retenciones WHERE IdRetencionSQL IN (99,153) ORDER BY IdRetencionSQL')


def vals():
    return fetch_all("SELECT * FROM dbo.ValuacionProveedor WHERE Origen='Retenciones' AND IdOrigen IN (99,153) ORDER BY IdOrigen")


def main():
    before = retenciones()
    for row, (i, cert, importe, *_) in zip(before, PLAN):
        assert row['IdRetencionSQL'] == i and row['IdContacto'] == 226
        assert row['Numero Certificado'] == cert and row['Importe'] == importe
    existing = vals()
    if existing:
        assert len(existing) == 2 and all(r['IdContacto'] == 226 and r['Dolares'] == p[3] for r, p in zip(existing, PLAN))
        print('Valuaciones ya aplicadas; sin cambios.'); return
    account_before = cargar_cuenta(226, refrescar=True)
    audit = {'antes': before, 'cuentaAntes': account_before, 'plan': PLAN,
             'fuentes': {p[5]: hashlib.sha256((ROOT/p[5]).read_bytes()).hexdigest() for p in PLAN},
             'criterio': 'Importe nominal íntegro. Solo USD reconocido en libro RG25/RG22; resto cancela ND en pesos. Sin nuevos pagos ni cambios de aplicaciones.',
             'autorizacion': 'Sergio: continuar correcciones necesarias y terminar auditoría Bayá',
             'backup': backup_verificado('baya-retenciones-mixtas-036')}
    path = ROOT / f'retenciones-mixtas-{datetime.now():%Y%m%d_%H%M%S}.json'
    path.write_text(json.dumps(audit, default=str, ensure_ascii=False, indent=2), encoding='utf-8')
    with reconciliation_transaction():
        assert retenciones() == before and not vals()
        execute_write_transaction([
            ('INSERT INTO dbo.ValuacionProveedor (Origen,IdOrigen,IdContacto,Dolares,Fuente,Nota,Usuario) VALUES (?,?,?,?,?,?,?)',
             ('Retenciones', i, 226, usd, fuente,
              f'Libro proveedor: USD {usd}; componente pesos {pesos}. Certificado nominal {importe} intacto.', 'sergio'))
            for i, cert, importe, usd, pesos, pdf, fuente in PLAN])
        assert retenciones() == before
        audit['valuacionesDespues'] = vals()
    invalidar()
    account_after = cargar_cuenta(226, refrescar=True)
    assert account_after['saldoPesos'] == account_before['saldoPesos']
    prev = {(r['origenTipo'], r['idOrigen']): r for r in account_before['filas']}
    assert len(account_after['filas']) == len(account_before['filas'])
    for row in account_after['filas']:
        old = prev[(row['origenTipo'], row['idOrigen'])]
        for k in ('deudaOriginal', 'creditoOriginal', 'deudaPesos', 'creditoPesos', 'fecha'):
            assert row[k] == old[k]
    audit['cuentaDespues'] = account_after
    audit['variacionSaldoUSD'] = round(account_after['saldoDolares'] - account_before['saldoDolares'], 2)
    path.write_text(json.dumps(audit, default=str, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'variacionSaldoUSD': audit['variacionSaldoUSD'], 'saldoPesosSinCambios': True, 'backup': audit['backup']}, default=str))


if __name__ == '__main__': main()
