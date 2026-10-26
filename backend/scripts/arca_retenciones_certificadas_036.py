"""Obligaciones SICORE omitidas respaldadas por certificados emitidos; no duplica pagos.

Inspección por defecto. --aplicar requiere huellas, respaldo verificado, transacción,
control de concurrencia y conservación de los demás libros. No reemplaza DDJJ SCT.
"""
import argparse
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path
import shutil

from scripts.relevar_retenciones_arca_cierre_036 import OUT
from scripts.vincular_tres_pagos_condominio_036 import control
from src.db.connection import _assert_target_is_wc, _reconciliation_connection, reconciliation_transaction
from src.features.cajas_efectivo.operaciones import read
from src.features.cuentas_corrientes import arca
from src.features.cuentas_corrientes.arca_documentos import RAIZ, verificar_archivo
from src.features.vinculos.backup import backup_verificado

RULE = 'arca-retenciones-certificadas-2017-2024-036'


def plan():
    evidence = json.loads((OUT / 'retenciones-cruce.json').read_text(encoding='utf-8'))
    taxes = read('SELECT * FROM dbo.Impuestos WHERE IdOrganismo=119 ORDER BY IdImpuesto')
    originals, marks = arca.cargar()
    current = arca.construir(originals, marks, hasta=date(2026, 9, 30), subcuenta='por-identificar', size=1000)['items']
    proposals, excluded = [], []
    for r in evidence['retenciones']:
        if D(r['Importe']) <= 0 or r['Fecha'] >= '2024-12-16':
            continue  # DDJJ12/2024 segunda quincena ya incorporada: no duplicar.
        docs = r['documentosCompatibles']
        if len(docs) != 1:
            excluded.append({'retencion': r['IdRetencionSQL'], 'motivo': 'sin original univoco', 'importe': r['Importe']})
            continue
        doc = docs[0]
        if hashlib.sha256(Path(doc['ruta']).read_bytes()).hexdigest() != doc['sha256']:
            raise ValueError('Cambió un original')
        # Evitar duplicar una obligación existente aunque tenga un tipo mal clasificado.
        existing = [t for t in taxes if t['Importe'] == D(r['Importe'])
                    and abs((t['Fecha'].date() - date.fromisoformat(r['Fecha'][:10])).days) <= 45]
        if existing:
            excluded.append({'retencion': r['IdRetencionSQL'], 'motivo': 'obligacion existente candidata',
                             'impuestos': [t['IdImpuesto'] for t in existing], 'importe': r['Importe']})
            continue
        proposals.append({'retencion': r, 'documento': doc, 'importe': D(r['Importe']),
                          'fecha': doc['fecha'], 'numero': 'CERT ' + doc['numero']})
    # Vincular solo quincenas con todos los certificados verificados y un único pago exacto.
    by_id = {p['retencion']['IdRetencionSQL']: p for p in proposals}
    groups = defaultdict(list)
    for r in evidence['retenciones']:
        if r['IdRetencionSQL'] in by_id:
            f = date.fromisoformat(r['Fecha'][:10])
            groups[(f.year, f.month, 1 if f.day <= 15 else 2)].append(r)
    payments = []
    used = set()
    for key, rs in groups.items():
        all_rs = [r for r in evidence['retenciones'] if D(r['Importe']) > 0
                  and (int(r['Fecha'][:4]), int(r['Fecha'][5:7]), 1 if int(r['Fecha'][8:10]) <= 15 else 2) == key]
        if len(all_rs) != len(rs):
            continue
        total = sum((D(r['Importe']) for r in rs), D(0))
        last = max(date.fromisoformat(r['Fecha'][:10]) for r in rs)
        candidates = [f for f in current if f['credito'] == total and not f['deuda']
                      and f['origen'] in ('Galicia', 'Banco Nacion', 'Pagos efectivo')
                      and 0 <= (f['fecha'] - last).days <= 45]
        if len(candidates) != 1:
            continue
        f = candidates[0]
        ident = (f['origen'], f['idOrigen'])
        if ident in used:
            raise ValueError('Pago candidato repetido')
        used.add(ident)
        parts = []
        for part in f['partes']:
            part = dict(part)
            if part['subcuenta'] == 'por-identificar':
                part['subcuenta'] = 'sicore-ganancias'
            parts.append(part)
        payments.append({'origen': f['origen'], 'idOrigen': f['idOrigen'], 'version': f['version'],
                         'partes': parts, 'importe': total, 'retenciones': [r['IdRetencionSQL'] for r in rs],
                         'motivo': f"SICORE quincena {key}: certificados emitidos verificados {','.join(r['Numero Certificado'] for r in rs)}; pago bancario/efectivo existente y suma exacta. No es anticipo propio ni pago nuevo."})
    return {'obligaciones': proposals, 'pagos': payments, 'excluidas': excluded,
            'totalObligaciones': sum((p['importe'] for p in proposals), D(0)),
            'totalPagosClasificar': sum((p['importe'] for p in payments), D(0))}, originals, marks, taxes


def run(apply=False):
    _assert_target_is_wc()
    previous = read("SELECT Parametros FROM dbo.AuditoriaCorrecciones WHERE Regla=? AND Estado='aplicada'", (RULE,))
    if previous:
        applied = json.loads(previous[0]['Parametros'])
        for p in applied['insertadas']:
            rows = read('SELECT Importe,[Numero de documento] numero FROM dbo.Impuestos WHERE IdImpuesto=?', (p['idImpuesto'],))
            assert rows == [{'Importe': D(p['importe']), 'numero': p['numero']}]
        return {'estado': 'ya_aplicado_sin_escrituras', 'obligacionesVerificadas': len(applied['insertadas'])}
    proposal, originals, marks, taxes = plan()
    if not apply:
        (OUT / 'retenciones-plan.json').write_text(json.dumps(proposal, default=str, ensure_ascii=False, indent=2), encoding='utf-8')
        return {'estado': 'inspeccion', 'obligaciones': len(proposal['obligaciones']), 'pagos': len(proposal['pagos']),
                'totalObligaciones': proposal['totalObligaciones'], 'totalPagosClasificar': proposal['totalPagosClasificar'], 'excluidas': len(proposal['excluidas'])}
    backup = backup_verificado(RULE)
    log = OUT / f'retenciones-aplicadas-{datetime.now():%Y%m%d-%H%M%S}.json'
    result = {'estado': 'respaldado', 'backup': backup, 'plan': proposal, 'insertadas': [], 'originalesAntes': originals, 'marcasAntes': [{**v, 'origen': k[0], 'idOrigen': k[1]} for k,v in marks.items()]}
    log.write_text(json.dumps(result, default=str, ensure_ascii=False, indent=2), encoding='utf-8')
    # Copias documentales sin reemplazar ni modificar originales.
    for p in proposal['obligaciones']:
        d = p['documento']
        target = RAIZ / 'SICORE' / 'Certificados' / p['fecha'][:4] / Path(d['ruta']).name
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            shutil.copy2(d['ruta'], target)
        verificar_archivo(target, d['sha256'])
        p['rutaAdministrada'] = str(target)
    with reconciliation_transaction():
        c = _reconciliation_connection.get().cursor()
        c.execute('SELECT IdImpuesto FROM dbo.Impuestos WITH (UPDLOCK,HOLDLOCK) WHERE IdOrganismo=119').fetchall()
        fresh, fresh_marks = arca.cargar()
        assert fresh == originals and fresh_marks == marks
        assert read('SELECT * FROM dbo.Impuestos WHERE IdOrganismo=119 ORDER BY IdImpuesto') == taxes
        before = control(c)
        for p in proposal['obligaciones']:
            period = f"{p['fecha'][5:7]} {p['fecha'][:4]}"
            c.execute('INSERT INTO dbo.Impuestos (Fecha,IdOrganismo,IdTipoImpuesto,[Periodo liquidado],[Numero de documento],Importe,[Documento Original]) OUTPUT INSERTED.IdImpuesto VALUES (?,119,20,?,?,?,?)', p['fecha'], period, p['numero'], p['importe'], p['rutaAdministrada'])
            tax_id = c.fetchone()[0]
            arca.guardar('Impuestos', tax_id, 0, [{'subcuenta': 'sicore-ganancias', 'deuda': p['importe'], 'credito': D(0)}],
                         f"Obligacion por retencion emitida {p['documento']['numero']}, Retenciones[{p['retencion']['IdRetencionSQL']}], original verificado. No nueva compra/gasto/pago ni DDJJ presentada.", 'Codex036')
            c.execute('INSERT INTO dbo.ArcaDocumentos (Origen,IdOrigen,Tipo,Periodo,Numero,Ruta,Sha256,EsOriginal,Usuario,Fecha) VALUES (\'Impuestos\',?,\'Certificado retencion emitida\',?,?,?,?,1,\'Codex036\',SYSDATETIME())', tax_id, period, p['documento']['numero'], p['rutaAdministrada'], p['documento']['sha256'])
            result['insertadas'].append({'idImpuesto': tax_id, 'retencion': p['retencion']['IdRetencionSQL'], 'numero': p['numero'], 'importe': p['importe']})
        for p in proposal['pagos']:
            arca.guardar(p['origen'], p['idOrigen'], p['version'], p['partes'], p['motivo'], 'Codex036')
        after = control(c)
        assert before['cajas'] == after['cajas'] and before['socios'] == after['socios']
        assert [r for r in before['cuentas'] if r[0] != 119] == [r for r in after['cuentas'] if r[0] != 119]
        assert next(r[1] for r in after['cuentas'] if r[0] == 119) == next(r[1] for r in before['cuentas'] if r[0] == 119) - proposal['totalObligaciones']
        final_rows, final_marks = arca.cargar()
        assert [r for r in final_rows if (r['origen'],r['idOrigen']) in {(f['origen'],f['idOrigen']) for f in originals}] == originals
        result.update(estado='aplicado', antes=before, despues=after, resumenArca=arca.construir(final_rows, final_marks, hasta=date(2026,9,30))['resumen'])
        c.execute("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) VALUES (?,'aplicada',?,'Codex036',SYSDATETIME(),'Codex036',SYSDATETIME(),?,?)", RULE, json.dumps({'informe': str(log), 'insertadas': result['insertadas']}, default=str), backup,
                  f"{len(result['insertadas'])} obligaciones SICORE por certificados originales omitidas; {len(proposal['pagos'])} pagos existentes clasificados. Sin cambios en otros contactos/cajas/socios.")
    log.write_text(json.dumps(result, default=str, ensure_ascii=False, indent=2), encoding='utf-8')
    return {'estado': 'aplicado', 'informe': str(log), 'backup': backup, 'obligaciones': len(result['insertadas']), 'pagos': len(proposal['pagos']), 'total': proposal['totalObligaciones']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--aplicar', action='store_true')
    print(json.dumps(run(parser.parse_args().aplicar), default=str, ensure_ascii=False))
