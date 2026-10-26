"""Pago adicional Autónomos Lucy05/05/2025: extracto personal, socio y ARCA.

No crea débito bancario de la empresa ni gasto nuevo. Guarda extracto/huella,
financiación histórica50/50 y vínculo único al mayorARCA. Inspección por defecto.
"""
import argparse
from datetime import date
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path
import shutil

import pdfplumber

from scripts.relevar_retenciones_arca_cierre_036 import OUT
from scripts.vincular_tres_pagos_condominio_036 import control
from src.db.connection import _assert_target_is_wc, _reconciliation_connection, reconciliation_transaction
from src.features.cajas_efectivo.operaciones import read
from src.features.cuentas_corrientes import arca
from src.features.cuentas_corrientes.arca_documentos import RAIZ, verificar_archivo
from src.features.cuentas_socios.valuacion import a_fecha
from src.features.vinculos.backup import backup_verificado

RULE='arca-lucy-galicia-20250505-1487-036'
SOURCE=Path.home()/'Documents/Estudio Contable/DDJJ Fisicas 2025/Lucy/Galicia/CA Pesos/RESUMEN_EXTRACTOS CONSOLIDADOS - CAJA DE AHORRO 19-08-2025.pdf'
AMOUNT=D('1487.91')


def run(apply=False):
    _assert_target_is_wc()
    applied=read("SELECT Parametros FROM dbo.AuditoriaCorrecciones WHERE Regla=? AND Estado='aplicada'",(RULE,))
    if applied:
        record=json.loads(applied[0]['Parametros'])
        assert read('SELECT Importe FROM dbo.MovimientosCuentaSocio WHERE IdMovimiento=? AND Anulada=0',(record['idMovimiento'],))==[{'Importe':AMOUNT}]
        return {'estado':'ya_aplicado_sin_escrituras','idMovimiento':record['idMovimiento']}
    with pdfplumber.open(SOURCE) as pdf:
        text=pdf.pages[0].extract_text()
        next_page=pdf.pages[1].extract_text()
    assert all(s in text for s in ['ALBINA LUCILA IGLINA','27-04862094-4','05/05/25 PAGO DE SERVICIOS -1.487,91','IMP.AFIP','270486209440'])
    assert '05/05/25 PAGO DE SERVICIOS -43.318,70' in next_page
    previous=read('SELECT * FROM dbo.MovimientosCuentaSocio WHERE Importe=? OR (IdSocio=2 AND Fecha>=? AND Fecha<?) ORDER BY IdMovimiento',(AMOUNT,'2025-05-01','2025-05-10'))
    assert not [r for r in previous if not r['Anulada'] and r['Importe']==AMOUNT]
    assert not read('SELECT 1 x FROM dbo.[Pagos efectivo] WHERE ABS([Importe imputado])=?',(AMOUNT,))
    valuation=a_fecha(AMOUNT,date(2025,5,5))
    result={'estado':'inspeccion','fuente':str(SOURCE),'sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'pagina':1,
            'importe':AMOUNT,'fecha':'2025-05-05','valuacion':valuation,'candidatosPrevios':previous,
            'capitalCCMA':'1134.42','interesesCCMA':'353.49','nota':'Pago real separado del mensual43.318,70; no compensación del estudio. El desglose fiscal no crea un gasto nuevo en esta operación.'}
    if not apply:return result
    result['backup']=backup_verificado(RULE)
    OUT.mkdir(parents=True,exist_ok=True)
    log=OUT/'lucy-pago-galicia-20250505-aplicado.json'
    log.write_text(json.dumps(result,default=str,ensure_ascii=False,indent=2),encoding='utf-8')
    dst=RAIZ/'Autonomos'/'Galicia-Lucy-extracto-20250819.pdf'
    if not dst.exists():shutil.copy2(SOURCE,dst)
    verificar_archivo(dst,result['sha256'])
    with reconciliation_transaction():
        c=_reconciliation_connection.get().cursor()
        assert read('SELECT * FROM dbo.MovimientosCuentaSocio WITH (UPDLOCK,HOLDLOCK) WHERE Importe=? OR (IdSocio=2 AND Fecha>=? AND Fecha<?) ORDER BY IdMovimiento',(AMOUNT,'2025-05-01','2025-05-10'))==previous
        before=control(c)
        c.execute("INSERT INTO dbo.MovimientosCuentaSocio (IdSocio,Tipo,Importe,ImporteUSD,ImporteKgCarne,Fecha,Origen,IdOrigen,Medio,Motivo,Usuario,Anulada) OUTPUT INSERTED.IdMovimiento VALUES (2,'Devolucion',?,?,?,'2025-05-05','ArcaGaliciaLucy036',20250505,'Galicia Lucy',?,'Codex036',0)",AMOUNT,valuation['importeUSD'],valuation['importeKgCarne'],'ARCA - Autónomos Lucy11/2024, capital e intereses: débito personalGalicia05/05/2025 $1487,91. Extracto19/08/2025 pág1; distinto del mensual43318,70.')
        new_id=c.fetchone()[0]
        c.execute("INSERT INTO dbo.PagosSocioProveedor (IdMovimientoSocio,IdContacto,Criterio,FechaAlta) VALUES (?,119,'documental',SYSDATETIME())",new_id)
        arca.guardar('Pago por socio',new_id,0,[{'subcuenta':'autonomos-lucy','deuda':D(0),'credito':AMOUNT}], 'Extracto personalGaliciaLucy05/05/2025 pág1 yCCMA: pago real adicional1487,91; no compensación ni banco de la empresa. Financiación50/50 a fecha histórica.','Codex036')
        c.execute("INSERT INTO dbo.ArcaDocumentos (Origen,IdOrigen,Tipo,Periodo,Numero,Ruta,Sha256,EsOriginal,Usuario,Fecha) VALUES ('Pago por socio',?,'Extracto bancario original','11 2024','Galicia05/05/2025',?,?,1,'Codex036',SYSDATETIME())",new_id,str(dst),result['sha256'])
        after=control(c)
        assert before['cajas']==after['cajas']
        assert [r for r in before['cuentas'] if r[0]!=119]==[r for r in after['cuentas'] if r[0]!=119]
        assert next(r[1] for r in after['cuentas'] if r[0]==119)-next(r[1] for r in before['cuentas'] if r[0]==119)==AMOUNT
        assert [r for r in before['socios'] if r[0]!=2]==[r for r in after['socios'] if r[0]!=2]
        old=next(r for r in before['socios'] if r[0]==2);new=next(r for r in after['socios'] if r[0]==2)
        assert new[1]-old[1]==1 and new[2]-old[2]==AMOUNT and new[3]-old[3]==valuation['importeUSD'] and new[4]-old[4]==valuation['importeKgCarne']
        result.update(estado='aplicado',idMovimiento=new_id,antes=before,despues=after)
        c.execute("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) VALUES (?,'aplicada',?,'Codex036',SYSDATETIME(),'Codex036',SYSDATETIME(),?,?)",RULE,json.dumps({'informe':str(log),'idMovimiento':new_id}),result['backup'],'Pago personalLucy1487,91 comprobado enGalicia; financiación50/50 y créditoARCA únicos, sin egreso empresa ni gasto nuevo.')
    log.write_text(json.dumps(result,default=str,ensure_ascii=False,indent=2),encoding='utf-8')
    return {'estado':'aplicado','idMovimiento':new_id,'backup':result['backup'],'informe':str(log),'valuacion':valuation}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--aplicar',action='store_true')
    print(json.dumps(run(p.parse_args().aplicar),default=str,ensure_ascii=False))
