"""Cargill (258): la conciliación masiva del 29/09/2026 (IdConciliacion 1272) vinculó el cheque propio 5607688 del
12/07/2010 ($3.600, "Bigatti") con la ND 9759-00002423 de Cargill (27/04/2018, $3.600). Cargill no existía como
contacto en 2010 (su cuenta corriente arranca en 0 al 31/03/2015) y esa ND se anula con la NC 9759-00001134 del mismo
día. Se borra el vínculo; el cheque queda sin imputar a Cargill. Idempotente.
"""
import json
from datetime import datetime
from pathlib import Path

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.vinculos.backup import backup_verificado

ROOT = Path(__file__).resolve().parents[2] / 'backups/cargill-conciliacion-20261020'


def main():
    _assert_target_is_wc()
    fila = fetch_all("SELECT * FROM dbo.ConciliacionesTesoreria WHERE IdConciliacion=1272 AND IdContacto=258 AND Medio='valores-propios' AND IdMovimiento=20")
    if not fila:
        print('Nada pendiente.'); return
    audit = {'fila': fila, 'backup': backup_verificado('cargill-conciliacion-bigatti-036')}
    (ROOT / f'conciliacion-bigatti-{datetime.now():%Y%m%d_%H%M%S}.json').write_text(json.dumps(audit, default=str, indent=1), encoding='utf-8')
    with reconciliation_transaction():
        execute_write_transaction([('DELETE FROM dbo.ConciliacionesTesoreria WHERE IdConciliacion=1272', ())])
    print('ok')


if __name__ == '__main__': main()
