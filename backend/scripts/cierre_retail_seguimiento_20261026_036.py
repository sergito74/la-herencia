"""Actualiza cierre documental y pendientes al30/09, por instrucción de Sergio26/10.

No usa Access para certificar saldos; registra explícitamente ausencia de resumen
externo general y residuos históricos. No ajusta dinero para forzar cero.
"""
import argparse
from datetime import date
import json

from scripts.relevar_retenciones_arca_cierre_036 import OUT
from scripts.vincular_tres_pagos_condominio_036 import control
from src.db.connection import _assert_target_is_wc, _reconciliation_connection, reconciliation_transaction
from src.features.cajas_efectivo.operaciones import read
from src.features.revision_cuentas import fichas, criterios
from src.features.vinculos.backup import backup_verificado

RULE = 'cierre-retail-seguimiento-20261026-036'
NOTES = {
 22: {'estado':'cerrada-con-excepcion', 'nota':'26/10: pendiente puntual Cooperativa resuelto: ticket2253,03, pago503 y créditoLucy coincidentes; financiación confirmada sin reintegro. Corrección24/10 verificada; no repetir pago ni volver a pedir titular. Cierre documental al30/09/2026 con excepción histórica explícita; ver revision-estado-20261026.md.', 'motivoExcepcion':'Sin resumen externo general actualizado: no se afirma saldo confirmado por proveedor ni se usa Access como prueba. Residuo nominal histórico -$0,0231, no ajustado. BNA14411/2015: detector conserva $260,69 sin aplicación documental completa, anterior2021; no es deuda nueva. Pendiente de tarjeta503 ya resuelto.'},
 29: {'estado':'cerrada-con-excepcion', 'nota':'26/10: Easy561 pagado con tarjetaLucy sin reintegro, confirmado porSergio. Ticket1361,54=tarjeta1362 menos vuelto0,46; pago y créditoLucy corregidos24/10 y aplicados a factura propia. No reiterar pedido de titular/resumen de ese documento. Cierre al30/09 con excepción histórica.', 'motivoExcepcion':'Sin resumen externo general actualizado: cierre documental contra originales y pagos; no se certifica saldo externo ni se usa Access como prueba. Residuo nominal histórico -$0,0052, conservado sin ajuste artificial.'},
 60: {'estado':'cerrada-con-excepcion', 'nota':'26/10: Jumbo, original511,79 y débitoHSBC comprobados. Aplicaciones completadas por ejecuciónFIFO104, sin cambiar importes. La nota sobre titularSodimac era ajena a esta cuenta y quedó resuelta24/10. Cierre documental al30/09; no repetir pago.', 'motivoExcepcion':'Sin resumen externo general actualizado: cierre documental contra original/débito, no pruebaAccess. Residuo nominal histórico +$0,0060 conservado. FIFO104 completa aplicaciones manteniendo vínculos fijos; no crea crédito nuevo.'},
 91: {'estado':'cerrada-con-excepcion', 'nota':'26/10: Sodimac88, titularLucy y pago íntegro624,29 sin reintegro confirmados porSergio24/10; importe y créditoLucy aplicados y verificados. Aplicaciones completadasFIFO104 sin dinero nuevo. Cierre documental al30/09; pedido antiguo de titular/resumen resuelto.', 'motivoExcepcion':'Sin resumen externo general actualizado: cierre documental con original y confirmación expresa del pagoLucy, no pruebaAccess. Residuo subcentavo histórico +$0,0002 conservado sin alterar factura ni pago.'},
 119: {'estado':'esperando-evidencia', 'nota':'26/10: corte30/09 confirmado. Incorporadas164 obligaciones SICORE documentadas; pagos existentes clasificados, OtrosImpuestos0, SIEP608 trasladado aMinisterioTrabajo con tickets y saldo0. Lucy: restituido original43318,70, pendiente financiar/reimputar4993,64; consulta aSergio por pagos05/05/2025. No confundir neto contable con crédito fiscal. Detalle y respaldos: revision-estado-20261026.md.'},
 210: {'estado':'esperando-evidencia', 'nota':'26/10 Sergio confirma NC2665608,21 todavía NO recibida: dejar pendiente, no sustituir con ajuste ni volver a buscarla como disponible. Corte30/09 confirmado; eCheq125 $884932,61 pertenece aoctubre y se revisará después. Transferencia275500 aDPPJ resuelta: no repetirla. Evidencia y decisión: revision-estado-20261026.md.'},
}


def run(apply=False):
    _assert_target_is_wc()
    if read("SELECT 1 x FROM dbo.AuditoriaCorrecciones WHERE Regla=? AND Estado='aplicada'",(RULE,)):
        return {'estado':'ya_aplicado_sin_escrituras'}
    assert fichas.corte_vigente()['corte'] == date(2026,9,30)
    before_rows=read('SELECT * FROM dbo.RevisionFichas WHERE IdContacto IN (22,29,60,91,119,210) ORDER BY IdContacto')
    contexts=fichas.cargar_contextos(date(2026,9,30),[22,29,60,91])
    for i in (22,29,60,91):
        ctx=contexts[i]
        assert abs(ctx['saldo']) < 0.04
        evaluated=criterios.evaluar(ctx['criterios_ctx'])
        assert all(c['cumple'] is not False for c in evaluated if c['codigo'] != 'C3')
    result={'estado':'inspeccion','antes':before_rows,'cambios':NOTES}
    if not apply:
        return result
    result['backup']=backup_verificado(RULE)
    log=OUT/'cierre-retail-seguimiento-aplicado.json'
    log.write_text(json.dumps(result,default=str,ensure_ascii=False,indent=2),encoding='utf-8')
    with reconciliation_transaction():
        c=_reconciliation_connection.get().cursor()
        assert read('SELECT * FROM dbo.RevisionFichas WITH (UPDLOCK,HOLDLOCK) WHERE IdContacto IN (22,29,60,91,119,210) ORDER BY IdContacto')==before_rows
        before=control(c)
        for contact,change in NOTES.items():
            fichas.cambiar_estado(contact,change,'Codex036 por instrucciónSergio26/10')
        after=control(c)
        assert before==after
        result.update(estado='aplicado',controlesAntes=before,controlesDespues=after,despues=read('SELECT * FROM dbo.RevisionFichas WHERE IdContacto IN (22,29,60,91,119,210) ORDER BY IdContacto'))
        c.execute("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) VALUES (?,'aplicada',?,'Codex036',SYSDATETIME(),'Codex036',SYSDATETIME(),?,?)",RULE,json.dumps({'informe':str(log)}),result['backup'],'Cuatro cierres documentales históricos con excepción explícita; ARCA y Criado siguen pendientes individualizados. Sin cambios financieros.')
    log.write_text(json.dumps(result,default=str,ensure_ascii=False,indent=2),encoding='utf-8')
    return {'estado':'aplicado','informe':str(log),'backup':result['backup'],'cerradasConExcepcion':[22,29,60,91],'pendientes':[119,210]}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--aplicar',action='store_true')
    print(json.dumps(run(p.parse_args().aplicar),default=str,ensure_ascii=False))
