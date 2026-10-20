"""Cargill (258): contacto de movimientos bancarios cruzados contra el libro del portal (PAGO/COBRO).

- BNA 9400 (10/07/2025 $1.024.835,52), 9406 (01/08/2025 $900.000) y 9358 (02/01/2025 $5.133.234,13):
  transferencias de Cargill (pagos 51240-X1-01444552, 01466504 y 01264892 del portal) sin contacto -> 258.
- Galicia 442 (15/03/2022) y 2172 (17/10/2024): "SNP Pago a proveedores AFIP 5000 625" son devoluciones de
  AFIP (retenciones de IVA de granos), no de Cargill -> AFIP (119).
Idempotente.
"""
import json
from datetime import datetime
from pathlib import Path

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.vinculos.backup import backup_verificado

ROOT = Path(__file__).resolve().parents[2] / 'backups/cargill-conciliacion-20261020'
BNA = {9400: 1024835.52, 9406: 900000.0, 9358: 5133234.13}
GALICIA_AFIP = {442: 60187.88, 2172: 226305.67}


def main():
    _assert_target_is_wc()
    bna = fetch_all(f"SELECT * FROM dbo.[Movimientos BNA] WHERE IdMovimientoBNA IN ({','.join(map(str, BNA))})")
    gal = fetch_all(f"SELECT * FROM dbo.[Movimientos Galicia] WHERE IdMovimiento IN ({','.join(map(str, GALICIA_AFIP))})")
    assert all(abs(r['Importe'] - BNA[r['IdMovimientoBNA']]) < 0.01 and r['IdContacto'] in (0, None, 258) for r in bna)
    assert all(abs(r['Créditos'] - GALICIA_AFIP[r['IdMovimiento']]) < 0.01 and r['IdContacto'] in (258, 119) for r in gal)
    if all(r['IdContacto'] == 258 for r in bna) and all(r['IdContacto'] == 119 for r in gal):
        print('Nada pendiente.'); return
    audit = {'autorizacion': 'Sergio 20/10/2026: conciliación Cargill', 'bna': bna, 'galicia': gal,
             'backup': backup_verificado('cargill-bancos-contacto-036')}
    (ROOT / f'bancos-contacto-{datetime.now():%Y%m%d_%H%M%S}.json').write_text(json.dumps(audit, default=str, ensure_ascii=False, indent=1), encoding='utf-8')
    with reconciliation_transaction():
        execute_write_transaction(
            [('UPDATE dbo.[Movimientos BNA] SET IdContacto=258 WHERE IdMovimientoBNA=?', (i,)) for i in BNA] +
            [('UPDATE dbo.[Movimientos Galicia] SET IdContacto=119 WHERE IdMovimiento=? AND IdContacto=258', (i,)) for i in GALICIA_AFIP])
    print('ok')


if __name__ == '__main__': main()
