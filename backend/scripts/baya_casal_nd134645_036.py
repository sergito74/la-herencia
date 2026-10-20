"""Corrección in situ de ND134645: fiscal, financiera y reparto conservado."""
import json
import hashlib
from pathlib import Path
from datetime import datetime
from decimal import Decimal, ROUND_DOWN

from src.db.connection import fetch_all, execute_write_transaction, reconciliation_transaction
from src.features.vinculos.backup import backup_verificado
from src.features.compras.repository import agregar_documento_relacionado, get_documentos_relacionados
from src.features.auditoria_cuentas.bimonetaria import construir, cotizacion_bna

ID = 2143517463
ORIGIN = 2143515104
ROOT = Path(__file__).resolve().parents[2] / 'backups/baya-conciliacion-20261019'
PDF = Path(r'C:\Users\Sergio\Dropbox\Giamigli de Bolivar SA\Compras\04 2026 - 03 2027\20260616_BayaCasal.pdf')
D = Decimal


def state(i):
    return {'cabecera': fetch_all('SELECT * FROM dbo.Compras WHERE IdDeuda=?',(i,)),
            'lineas': fetch_all('SELECT * FROM dbo.Det_Compras WHERE IdCompra=? ORDER BY IdDetalleCompra',(i,)),
            'relaciones': get_documentos_relacionados(i)}


def main():
    before, original = state(ID), state(ORIGIN)
    h = before['cabecera'][0]
    assert h['IdContacto']==226 and h['Nro Documento']=='0020-00134645'
    if h['Tipo documento']=='Nota de Débito' and h['Ajusta Tipo Cambio']:
        assert round(fetch_all('SELECT ImporteDocumento FROM dbo.vw_Compras_ImporteDocumento WHERE IdDeuda=?',(ID,))[0]['ImporteDocumento'],2)==356756.32
        print('Correccion ya aplicada; sin cambios.');return
    assert h['Tipo documento']=='Factura' and len(before['lineas'])==2
    rows=before['lineas']
    weights=[D(str(r['Cantidad']))*D(str(r['Precio Unitario'])) for r in rows]
    raw=[D('294839.93')*w/sum(weights) for w in weights]
    amounts=[v.quantize(D('.01'),rounding=ROUND_DOWN) for v in raw]
    for j in sorted(range(len(rows)),key=lambda j:raw[j]-amounts[j],reverse=True)[:int((D('294839.93')-sum(amounts))*100)]:amounts[j]+=D('.01')
    assert sum(amounts)==D('294839.93')
    audit={'autorizacion':'Sergio20/10/2026: adelante con las correcciones',
           'respaldo':backup_verificado('baya-nd134645-036'),'antes':before,'facturaOrigenAntes':original,
           'pdf':str(PDF),'sha256':hashlib.sha256(PDF.read_bytes()).hexdigest(),
           'criterio':'Neto fiscal294839.93; prorrata de pesos de lineas existentes, mayores restos a centavos. Cantidad1 ARS; sin nuevos kilos. Portal neto294842.64 difiere2.71; prevalece fiscal.',
           'netosAsignados':amounts}
    path=ROOT/f'nd134645-correccion-{datetime.now():%Y%m%d_%H%M%S}.json'
    path.write_text(json.dumps(audit,default=str,ensure_ascii=False,indent=2),encoding='utf-8')
    with reconciliation_transaction():
        assert state(ID)==before and state(ORIGIN)==original
        statements=[('UPDATE dbo.Compras SET [Tipo documento]=?,[Ajusta Tipo Cambio]=?,[Fecha Vto]=? WHERE IdDeuda=?',
                     ('Nota de Débito',True,datetime(2026,6,16),ID))]
        for r,amount in zip(rows,amounts):
            statements.append(('UPDATE dbo.Det_Compras SET Cantidad=?,Unidad=?,[Precio Unitario]=?,[Ajuste financiero]=? WHERE IdDetalleCompra=? AND IdCompra=?',
                               (1,'ARS',amount,True,r['IdDetalleCompra'],ID)))
        execute_write_transaction(statements)
        agregar_documento_relacionado(ID,ORIGIN)
        after=state(ID)
        total=fetch_all('SELECT ImporteDocumento FROM dbo.vw_Compras_ImporteDocumento WHERE IdDeuda=?',(ID,))[0]['ImporteDocumento']
        assert round(total,2)==356756.32
        origin_after=state(ORIGIN)
        assert origin_after['cabecera']==original['cabecera'] and origin_after['lineas']==original['lineas']
        for new,old,amount in zip(after['lineas'],rows,amounts):
            for key in ['IdDetalleCompra','Producto/Servicio','IVA','IdRubro','IdCentroCostos','IdDestino','IdCampaña','Campaña','IdFormulado']:
                assert new[key]==old[key]
            assert new['Cantidad']==1 and new['Unidad']=='ARS' and new['Ajuste financiero']
            assert abs(D(str(new['Precio Unitario']))-amount)<D('.00001')
        assert ORIGIN in [r['idCompra'] for r in after['relaciones']]
        movements=fetch_all('SELECT * FROM dbo.vw_MovimientosCuenta_Base WHERE Origen=? AND IdOrigen=?',('Compras',ID))
        usd=construir(movements,{ID:{'moneda':'Pesos','tc':1,'ajusta':True}},cotizacion_bna())
        assert usd['saldoDolares']==0
        costs=fetch_all('SELECT IdDetalleCompra,IdDestino,IdCampaña,Pesos,Dolares FROM dbo.vw_ResultadosCultivo_CostosBase WHERE IdCompra=?',(ID,))
        assert len(costs)==2 and round(sum(c['Pesos'] for c in costs),2)==294839.93
        assert all(c['Dolares']==0 for c in costs)
        audit.update({'despues':after,'total':total,'efectoUSD':usd['saldoDolares'],'costos':costs})
    assert state(ID)==after
    path.write_text(json.dumps(audit,default=str,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'IdDeuda':ID,'total':total,'netos':amounts,'USD':usd['saldoDolares'],'respaldo':audit['respaldo']},default=str))


if __name__=='__main__':main()
