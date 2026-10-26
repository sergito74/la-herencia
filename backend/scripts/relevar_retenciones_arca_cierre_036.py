"""Cruce de solo lectura: certificados emitidos, obligaciones ARCA y pagos sin clasificar."""
import hashlib
import json
from collections import defaultdict
from datetime import date
from decimal import Decimal as D
from pathlib import Path
import re

import pdfplumber

from src.features.cajas_efectivo.operaciones import read
from src.features.cuentas_corrientes import arca

OUT = Path(__file__).resolve().parents[2] / 'backups/cierre-cuentas-20261026'
CERTS = Path.home() / 'Documents/La Herencia/Administracion y gestion/Cuentas a pagar/Certificados Retenciones'
# Campos leídos visualmente el26/10 en los ocho PDF escaneados; la huella fija la fuente.
VISUALES = {
    'f51868641bef28c85475d3d7de3f966dbdaf23c25c5a8ca26b395cf6deb440c5': ('0000-2017-000001', '435.94', '2017-09-19'),
    'b75800994eb9a77cb708419e082328a661f5c3c121cc8011ed7cb31d8df16364': ('0000-2017-000002', '1928.91', '2017-09-20'),
    '63273d0149b2a6a9c56d0d5ca2deb7f35405677c23627e03c4eeabeb015d97ee': ('0000-2019-000007', '1313.80', '2019-07-01'),
    '9a9f99c70938cf527b09bd3ca6c1a883f92d621a506048c7d3d2b0a1f5b938ff': ('0000-2019-000006', '3481.60', '2019-07-01'),
    '0ab707ab998e6901804c9b2016d45bf7304a51abaa64eb16fa93247ee74f70fd': ('0000-2019-000008', '453.96', '2019-07-11'),
    '6108c4e48b1b34629f31a3a3a9cb946dcc1fb535e9c45d4f42acbc5a47a91c5e': ('0000-2019-000009', '7950.19', '2019-08-23'),
    '419c97d8a9de2d7a3b0e0b6371f3097a0339056d3aa5ac92f70be9a6416e621a': ('0000-2020-000004', '3366.33', '2020-06-25'),
    'ab0b46932492fd71037df32985bd730f993da3b285bba4dced90c0b29800b365': ('0000-2020-000005', '3900.60', '2020-07-02'),
}


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    paths = sorted(p for p in CERTS.rglob('*.pdf') if p.parent.name.isdigit() and int(p.parent.name) <= 2024)
    documents = []
    for p in paths:
        with pdfplumber.open(p) as pdf:
            text = '\n'.join(page.extract_text() or '' for page in pdf.pages)
        num = re.search(r'Certificado N.\s*:\s*([\d-]+)', text)
        amount = re.search(r'Monto de la Retenci.n\s*:\s*\$\s*([\d.,]+)', text)
        fecha = re.search(r'Fecha\s*:\s*(\d{2})/(\d{2})/(\d{4})', text)
        documents.append({'ruta': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
                          'numero': num[1] if num else None,
                          'importe': str(D(amount[1].replace('.', '').replace(',', '.'))) if amount else None,
                          'fecha': f'{fecha[3]}-{fecha[2]}-{fecha[1]}' if fecha else None,
                          'agenteCorrecto': '30-71211460-2' in text.split('B. - Datos')[0],
                          'texto': text})
        if documents[-1]['sha256'] in VISUALES:
            num_v, amount_v, fecha_v = VISUALES[documents[-1]['sha256']]
            documents[-1].update(numero=num_v, importe=amount_v, fecha=fecha_v, agenteCorrecto=True, lecturaVisual=True)
    retenciones = read("SELECT * FROM dbo.Retenciones WHERE Fecha<'2025-01-01' ORDER BY Fecha,IdRetencionSQL")
    for r in retenciones:
        r['documentosExactos'] = [p for p in documents if p['numero'] == r['Numero Certificado']
                                 and p['importe'] is not None and D(p['importe']) == r['Importe']
                                 and p['fecha'] == str(r['Fecha'])[:10] and p['agenteCorrecto']]
        r['documentosCompatibles'] = [p for p in documents if p['numero'] == r['Numero Certificado'].removesuffix(' B')
                                      and p['importe'] is not None and D(p['importe']) == r['Importe'] and p['agenteCorrecto']]
    pending = arca.cuenta(hasta=date(2026, 9, 30), subcuenta='por-identificar', size=1000)['items']
    grouped = defaultdict(list)
    for r in retenciones:
        f = r['Fecha']
        grouped[(f.year, f.month, 1 if f.day <= 15 else 2)].append(r)
    matches = []
    for key, rs in grouped.items():
        total = sum((r['Importe'] for r in rs), D(0))
        end = max(r['Fecha'].date() for r in rs)
        candidates = [f for f in pending if f['credito'] == total and not f['deuda']
                      and 0 <= (f['fecha'] - end).days <= 45]
        matches.append({'periodoQuincena': key, 'total': total, 'retenciones': [r['IdRetencionSQL'] for r in rs],
                        'originalesCompletos': all(len(r['documentosExactos']) == 1 for r in rs),
                        'candidatos': [{'origen': f['origen'], 'idOrigen': f['idOrigen'], 'fecha': f['fecha']} for f in candidates]})
    result = {'soloLectura': True, 'retenciones': retenciones, 'documentos': documents,
              'quincenas': matches, 'porIdentificar': pending,
              'obligacionesSicore': read('SELECT * FROM dbo.Impuestos WHERE IdOrganismo=119 AND IdTipoImpuesto=20 ORDER BY Fecha')}
    target = OUT / 'retenciones-cruce.json'
    target.write_text(json.dumps(result, default=str, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'archivo': str(target), 'certificadosPdf': len(documents), 'retenciones': len(retenciones),
                      'conOriginalExacto': sum(len(r['documentosExactos']) == 1 for r in retenciones),
                      'quincenas': [{k: v for k, v in q.items()} for q in matches]}, default=str))


if __name__ == '__main__':
    run()
