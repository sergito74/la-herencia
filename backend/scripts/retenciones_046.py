"""046 retenciones: respaldo verificado antes del DDL. Sin --aplicar solo inspecciona."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.db.connection import fetch_all, get_connection, reconciliation_transaction
from src.features.vinculos.backup import backup_verificado


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--aplicar', action='store_true')
    args = parser.parse_args()
    tables = fetch_all("SELECT name FROM sys.tables WHERE name LIKE 'RetencionesGanancias%' OR name = 'OrdenesPago_Retenciones'")
    if not args.aplicar:
        print(json.dumps({'tablasExistentes': tables}))
        return
    backup = backup_verificado('retenciones-046')
    report = Path(__file__).resolve().parents[2] / 'backups' / 'retenciones-046'
    report.mkdir(parents=True, exist_ok=True)
    result = {'backup': backup, 'verificado': True, 'aplicado': False}
    (report / 'migracion.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    with reconciliation_transaction():
        with get_connection(readonly=False) as conn:
            cursor = conn.cursor()
            cursor.execute(Path(__file__).with_name('retenciones_046.sql').read_text(encoding='utf-8'))
            while cursor.nextset():
                pass
    result['aplicado'] = True
    (report / 'migracion.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
