"""Auditoría de solo lectura de todas las tablas operativas con texto e ID de campaña."""
import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from src.db.connection import fetch_all
from src.features.revision_cuentas.auditoria_campanias import clasificar

# Lista cerrada de tablas operativas; excluye respaldos y resúmenes derivados.
TABLAS = ('Det_Compras', 'Labores Maquinaria propia')


def auditar():
    catalogo = fetch_all('SELECT [IdCampaña], [Campaña] FROM dbo.[Campañas]')
    hallazgos, cobertura = [], []
    for tabla in TABLAS:
        columns = fetch_all('SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=? AND TABLE_NAME=?', ('dbo', tabla))
        names = {r['COLUMN_NAME'] for r in columns}
        assert {'Campaña', 'IdCampaña'} <= names, tabla
        keys = fetch_all('SELECT c.name FROM sys.indexes i JOIN sys.index_columns ic ON ic.object_id=i.object_id AND ic.index_id=i.index_id JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id WHERE i.object_id=OBJECT_ID(?) AND i.is_primary_key=1 ORDER BY ic.key_ordinal', ('dbo.' + tabla,))
        selected = list(dict.fromkeys([r['name'] for r in keys] + [n for n in ('IdDetalleCompra', 'IdCompra', 'IdContacto', 'Fecha', 'IdDestino', 'Campaña', 'IdCampaña') if n in names]))
        # Identificadores provienen de metadatos SQL y de la lista cerrada anterior.
        fields = ','.join('[' + n.replace(']', ']]') + ']' for n in selected)
        rows = fetch_all(f'SELECT {fields} FROM dbo.[{tabla}]')
        count = 0
        for row in rows:
            tipo, candidatos = clasificar(row['Campaña'], row['IdCampaña'], catalogo)
            if tipo is not None:
                hallazgos.append(dict(tabla=tabla, tipo=tipo, candidatos=candidatos, **row)); count += 1
        cobertura.append(dict(tabla=tabla, renglones=len(rows), hallazgos=count, clave=[r['name'] for r in keys]))
    # Identifica proveedor/documento para todos los detalles de compras afectados.
    docs = {r['IdDeuda']: r for r in fetch_all('SELECT IdDeuda,IdContacto,[Nro Documento],Fecha FROM dbo.Compras')}
    for row in hallazgos:
        if row['tabla'] == 'Det_Compras':
            doc = docs.get(row['IdCompra'], {})
            row.update(IdContacto=doc.get('IdContacto'), documento=doc.get('Nro Documento'), fechaDocumento=doc.get('Fecha'))
    return dict(fecha=datetime.now().isoformat(), cobertura=cobertura,
                resumen=dict(Counter(r['tipo'] for r in hallazgos)), hallazgos=hallazgos)


def main():
    report = auditar()
    root = Path(__file__).resolve().parents[2] / 'backups/auditoria-campanias'
    root.mkdir(parents=True, exist_ok=True)
    base = root / f'auditoria-{datetime.now():%Y%m%d_%H%M%S}'
    base.with_suffix('.json').write_text(json.dumps(report, default=str, ensure_ascii=False, indent=2), encoding='utf-8')
    fields = list(dict.fromkeys(k for r in report['hallazgos'] for k in r))
    with base.with_suffix('.csv').open('w', encoding='utf-8-sig', newline='') as out:
        writer = csv.DictWriter(out, fieldnames=fields or ['tabla', 'tipo'])
        writer.writeheader(); writer.writerows(report['hallazgos'])
    print(json.dumps({k: v for k, v in report.items() if k != 'hallazgos'}, ensure_ascii=True))
    print(str(base.with_suffix('.json')))


if __name__ == '__main__': main()
