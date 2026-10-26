"""Complementos ARCA al30/09: avisos del estudio, VEP y correcciones de clasificación.

No genera pagos ni compensa deuda para forzar cero. Restituye el importe fiscal CCMA
de Lucy y conserva como pendiente cualquier financiación no probada.
"""
import argparse
from datetime import date
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

RULE = 'arca-complementos-documentados-20261026-036'


def prepare():
    mails = json.loads((OUT / 'correo-tributario-recuperado.json').read_text(encoding='utf-8-sig'))
    docs = json.loads((OUT / 'correo-pdf-textos.json').read_text(encoding='utf-8'))
    certs = json.loads((OUT / 'retenciones-cruce.json').read_text(encoding='utf-8'))['documentos']
    obligations = []
    def email(fecha, asunto, amount, prueba, period):
        matches = [m for m in mails if m['Fecha'] == fecha and m['Asunto'] == asunto and prueba in m['Cuerpo']]
        assert len(matches) == 1
        m = matches[0]
        obligations.append({'fecha': fecha, 'periodo': period, 'numero': 'AVISO SICORE ' + fecha,
                            'importe': D(amount), 'fuenteCorreo': m,
                            'sha256Correo': hashlib.sha256(m['Cuerpo'].encode('utf-8')).hexdigest()})
    email('2018-01-03', 'retenciones de ganancias', '2305', '$ 2305', '12 2017')
    email('2018-08-16', 'RETENCIONES DE GANANCIAS', '2410.56', '$ 2410.56', '08 2018')
    email('2023-10-06', 'RETENCIONES 2º QUINCENA DE SEPTIEMBRE', '219450.10', '$ 219.450,10', '09 2023')
    # Complemento de la obligación informada por el estudio: 26.292,65 menos
    # certificados ya incorporados 25.920,00. No modificar la retención del proveedor.
    email('2021-11-17', 'RETENCIONES 1º QUINCENA, NOVIEMBRE 2021', '372.65', '$ 26.292,65', '11 2021')
    previous = read("SELECT SUM(Importe) total FROM dbo.Impuestos WHERE IdOrganismo=119 AND [Numero de documento] IN ('CERT 0000-2021-000032','CERT 0000-2021-000033')")
    # Verificar por el vínculo exacto de auditoría, sin depender de numeración supuesta.
    base = json.loads((OUT / 'retenciones-cruce.json').read_text(encoding='utf-8'))
    rs = [r for r in base['retenciones'] if r['Fecha'][:7] == '2021-11' and r['IdRetencionSQL'] != 35]
    assert sum((D(r['Importe']) for r in rs), D(0)) == D('25920.00')
    for r in rs:
        assert read('SELECT Importe FROM dbo.Impuestos WHERE IdOrganismo=119 AND [Numero de documento]=?', ('CERT ' + r['Numero Certificado'],)) == [{'Importe': D(r['Importe'])}]
    for vep, amount, period, fecha in [('552657181','968.40','04 2019','2019-05-07'),('565510591','3553.00','05 2019','2019-06-06')]:
        ds = [p for p in docs if f'Nro. VEP: {vep}' in p.get('texto','') and 'SICORE-IMPTO.A LAS GANANCIAS (217)' in p['texto'] and '30-71211460-2' in p['texto']]
        assert len(ds) == 1
        d = ds[0]
        obligations.append({'fecha': fecha, 'periodo': period, 'numero': 'VEP ' + vep, 'importe': D(amount),
                            'pdf': d['Ruta'], 'sha256': d['Sha256'], 'texto': d['texto']})
    ds = [d for d in certs if d['numero'] == '0000-2023-000050' and d['importe'] == '7787.68' and d['fecha'] == '2023-12-27' and d['agenteCorrecto']]
    assert len(ds) == 1
    d = ds[0]
    obligations.append({'fecha': d['fecha'], 'periodo': '12 2023', 'numero': 'CERT ' + d['numero'], 'importe': D('7787.68'), 'pdf': d['ruta'], 'sha256': d['sha256'], 'nota': 'Archivo rotulado000049; número real del PDF000050. No cambiar cuenta cerrada de Bayá.'})
    rows, marks = arca.cargar()
    bykey = {(r['origen'],r['idOrigen']):r for r in rows}
    changes = []
    def classify(origin, ident, parts, reason):
        f = bykey[(origin, ident)]
        arca.validar_partes(parts, f['deuda'], f['credito'])
        changes.append({'origen': origin, 'idOrigen': ident, 'version': marks.get((origin,ident),{}).get('version',0), 'partes': parts, 'motivo': reason})
    pending = arca.construir(rows, marks, hasta=date(2026,9,30), subcuenta='por-identificar', size=1000)['items']
    ret_ids = {'Banco Nacion': {15856,15861,15866,15872,15875,15881,15883,15888,15891,15894}, 'Pagos efectivo': {217}, 'Galicia': {54,297,1449,1647,1937}}
    for f in pending:
        if f['idOrigen'] not in ret_ids.get(f['origen'],set()):
            continue
        parts = []
        for p in f['partes']:
            p = dict(p)
            if p['subcuenta'] == 'por-identificar':
                p['subcuenta'] = 'sicore-ganancias'
                if f['origen'] == 'Galicia' and f['idOrigen'] == 54:
                    p['credito'] = D('78062.26')
            parts.append(p)
        if f['origen'] == 'Galicia' and f['idOrigen'] == 54:
            parts.append({'subcuenta': 'por-identificar', 'deuda': D(0), 'credito': D('0.0015')})
        classify(f['origen'],f['idOrigen'],parts,'Retenciones SICORE emitidas según registro WC, quincena y pago existente; certificados/avisos/VEP en informe036. Los originales históricos faltantes quedan individualizados, sin atribuir un crédito fiscal ni crear pago nuevo.')
    for origin, ident in [('Banco Nacion',15879),('Galicia',1478)]:
        f = next(f for f in pending if f['origen'] == origin and f['idOrigen'] == ident)
        parts = [dict(p, subcuenta='otros-impuestos') if p['subcuenta']=='por-identificar' else p for p in f['partes']]
        classify(origin,ident,parts,'Intereses registrados en Impuestos: mismo día, VEP, desglose exacto del débito (BNA15879: Impuestos841–848; Galicia1478: Impuesto813 y anticipo814). Solo reparto, sin ajuste monetario.')
    sicore_pdf = next(p for p in docs if 'Nro. VEP Consolidado: 606788107' in p.get('texto',''))
    assert 'SICORE-IMPTO.A LAS GANANCIAS (217) $7.962,72' in sicore_pdf['texto']
    for origin,ident in [('Impuestos',839),('Impuestos',838),('Banco Nacion',15901)]:
        f = bykey[(origin,ident)]
        classify(origin,ident,[{'subcuenta':'sicore-ganancias','deuda':f['deuda'],'credito':f['credito']}], 'VEP oficial606788107: SICORE217 $7.962,72 = capital7.950,19 + intereses12,53. No es Ganancias propio. Original recuperado de correo09–10/09/2019.')
    lucy = read('SELECT * FROM dbo.Impuestos WHERE IdImpuesto=4593')[0]
    assert lucy['Importe'] == D('38313.90')
    ccma = Path(lucy['Documento Original'])
    ccma_sha = hashlib.sha256(ccma.read_bytes()).hexdigest()
    official = json.loads((OUT.parent/'arca-continuacion-20261025/CCMA-Lucy-202409-202609-filas.json').read_text(encoding='utf-8'))
    assert any(r[2]=='11/2024' and r[6]=='Obligacion Mensual Autonomo.' and r[8]=='43,318.70' for r in official if len(r)>9)
    classify('Pago por socio',2680,[{'subcuenta':'autonomos-lucy','deuda':D(0),'credito':D('39344.54')}], 'Reversión del reparto artificial de11,16: CCMA acredita pago03/01/2025 por39.344,54 en12/2024. Se conserva nominal y financiación del socio; no forzar cierre deLucy.')
    return {'obligaciones':obligations,'clasificaciones':changes,'lucyAntes':lucy,'ccmaSha256':ccma_sha,'sicorePdf':sicore_pdf}, rows, marks


def run(apply=False):
    _assert_target_is_wc()
    if read("SELECT 1 x FROM dbo.AuditoriaCorrecciones WHERE Regla=? AND Estado='aplicada'",(RULE,)):
        assert read('SELECT Importe FROM dbo.Impuestos WHERE IdImpuesto=4593') == [{'Importe':D('43318.70')}]
        return {'estado':'ya_aplicado_sin_escrituras'}
    p, originals, marks = prepare()
    if not apply:
        (OUT/'complementos-plan.json').write_text(json.dumps(p,default=str,ensure_ascii=False,indent=2),encoding='utf-8')
        return {'estado':'inspeccion','obligaciones':len(p['obligaciones']),'total':sum(o['importe'] for o in p['obligaciones']),'clasificaciones':len(p['clasificaciones']),'lucyRestituir':'43318.70'}
    backup = backup_verificado(RULE)
    result={'estado':'respaldado','plan':p,'backup':backup,'insertadas':[]}
    log=OUT/'complementos-aplicados.json'
    log.write_text(json.dumps(result,default=str,ensure_ascii=False,indent=2),encoding='utf-8')
    with reconciliation_transaction():
        c=_reconciliation_connection.get().cursor()
        c.execute('SELECT IdImpuesto FROM dbo.Impuestos WITH (UPDLOCK,HOLDLOCK) WHERE IdOrganismo=119').fetchall()
        fresh,fresh_marks=arca.cargar()
        assert fresh==originals and fresh_marks==marks
        before=control(c)
        for o in p['obligaciones']:
            assert not read('SELECT 1 x FROM dbo.Impuestos WHERE IdOrganismo=119 AND [Numero de documento]=?',(o['numero'],))
            target=None
            if o.get('pdf'):
                assert hashlib.sha256(Path(o['pdf']).read_bytes()).hexdigest()==o['sha256']
                target=RAIZ/'SICORE'/'Complementos'/Path(o['pdf']).name
                target.parent.mkdir(parents=True,exist_ok=True)
                if not target.exists():shutil.copy2(o['pdf'],target)
                verificar_archivo(target,o['sha256'])
            c.execute('INSERT INTO dbo.Impuestos (Fecha,IdOrganismo,IdTipoImpuesto,[Periodo liquidado],[Numero de documento],Importe,[Documento Original]) OUTPUT INSERTED.IdImpuesto VALUES (?,119,20,?,?,?,?)',o['fecha'],o['periodo'],o['numero'],o['importe'],str(target) if target else None)
            new_id=c.fetchone()[0]
            arca.guardar('Impuestos',new_id,0,[{'subcuenta':'sicore-ganancias','deuda':o['importe'],'credito':D(0)}],f"Obligación SICORE omitida; fuente {o['numero']}, período{o['periodo']}; evidencia original en auditoría{RULE}. Sin pago nuevo.",'Codex036')
            if target:
                c.execute("INSERT INTO dbo.ArcaDocumentos (Origen,IdOrigen,Tipo,Periodo,Numero,Ruta,Sha256,EsOriginal,Usuario,Fecha) VALUES ('Impuestos',?,'Original SICORE',?,?,?,?,1,'Codex036',SYSDATETIME())",new_id,o['periodo'],o['numero'],str(target),o['sha256'])
            result['insertadas'].append({'idImpuesto':new_id,'importe':o['importe'],'numero':o['numero']})
        c.execute('UPDATE dbo.Impuestos SET IdTipoImpuesto=20 WHERE IdImpuesto=839 AND IdTipoImpuesto=3')
        assert read('SELECT * FROM dbo.Impuestos WHERE IdImpuesto=4593')[0]==p['lucyAntes']
        assert hashlib.sha256(Path(p['lucyAntes']['Documento Original']).read_bytes()).hexdigest()==p['ccmaSha256']
        c.execute('UPDATE dbo.Impuestos SET Importe=43318.70 WHERE IdImpuesto=4593')
        for q in p['clasificaciones']:
            arca.guardar(q['origen'],q['idOrigen'],q['version'],q['partes'],q['motivo'],'Codex036')
        arca.guardar('Impuestos',4593,marks[('Impuestos',4593)]['version'],[{'subcuenta':'autonomos-lucy','deuda':D('43318.70'),'credito':D(0)}], 'Restituye importe fiscal original CCMA11/2024:43.318,70.38.313,90 era un pago, no la obligación. No forzar cero; reimputaciones y financiación siguen documentándose.','Codex036')
        after=control(c)
        assert before['cajas']==after['cajas'] and before['socios']==after['socios']
        assert [r for r in before['cuentas'] if r[0]!=119]==[r for r in after['cuentas'] if r[0]!=119]
        delta=-sum(o['importe'] for o in p['obligaciones'])-D('5004.80')
        assert next(r[1] for r in after['cuentas'] if r[0]==119)-next(r[1] for r in before['cuentas'] if r[0]==119)==delta
        result.update(estado='aplicado',antes=before,despues=after)
        c.execute("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) VALUES (?,'aplicada',?,'Codex036',SYSDATETIME(),'Codex036',SYSDATETIME(),?,?)",RULE,json.dumps({'informe':str(log),'insertadas':result['insertadas'],'lucyAntes':p['lucyAntes']},default=str),backup,'Complementos SICORE documentados; reclasificación de pagos existentes/intereses y VEP2019; restituido importe fiscalLucy sin inventar financiación.')
    log.write_text(json.dumps(result,default=str,ensure_ascii=False,indent=2),encoding='utf-8')
    return {'estado':'aplicado','backup':backup,'informe':str(log),'obligaciones':len(result['insertadas'])}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--aplicar',action='store_true')
    print(json.dumps(run(parser.parse_args().aplicar),default=str,ensure_ascii=False))
