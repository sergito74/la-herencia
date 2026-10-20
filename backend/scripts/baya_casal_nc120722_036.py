"""NC120722: conserva crédito fiscal y distribución, elimina cantidades físicas."""
import json
import hashlib
from pathlib import Path
from datetime import datetime
from decimal import Decimal, ROUND_DOWN

from src.db.connection import fetch_all, execute_write_transaction, reconciliation_transaction
from src.features.vinculos.backup import backup_verificado
from src.features.compras.repository import agregar_documento_relacionado
from src.features.auditoria_cuentas.bimonetaria import construir, cotizacion_bna
from scripts.baya_casal_nd134645_036 import state

ID, ORIGIN = 2143515167, 2143514876
ROOT = Path(__file__).resolve().parents[2] / 'backups/baya-conciliacion-20261019'
PDF = Path(r'C:\Users\Sergio\Dropbox\Giamigli de Bolivar SA\Compras\04 2025 - 03 2026\20250522_BayaCasal.pdf')
D = Decimal


def main():
    before, original = state(ID), state(ORIGIN)
    h=before['cabecera'][0]
    assert h['IdContacto']==226 and h['Nro Documento']=='0020-00120722'
    if h['Ajusta Tipo Cambio'] and all(r['Ajuste financiero'] for r in before['lineas']):
        assert round(fetch_all('SELECT ImporteDocumento FROM dbo.vw_Compras_ImporteDocumento WHERE IdDeuda=?',(ID,))[0]['ImporteDocumento'],2)==-16252.67
        print('Correccion ya aplicada; sin cambios.');return
    assert h['Tipo documento']=='Nota de Crédito' and h['Moneda']=='Pesos'
    rows=before['lineas']
    assert len(rows)==19 and all(r['Precio Unitario']<0 and r['IVA']==21 for r in rows)
    assert original['cabecera'][0]['Nro Documento']=='0020-00401515'
    def keys(lines):
        return sorted((r['Producto/Servicio'],r['IdCentroCostos'],r['IdDestino'],r['IdCampaña'],r['Campaña']) for r in lines)
    assert keys(rows)==keys(original['lineas'])
    weights=[abs(D(str(r['Cantidad']))*D(str(r['Precio Unitario']))) for r in rows]
    raw=[D('13431.96')*w/sum(weights) for w in weights]
    amounts=[v.quantize(D('.01'),rounding=ROUND_DOWN) for v in raw]
    remaining=int((D('13431.96')-sum(amounts))*100)
    for j in sorted(range(len(rows)),key=lambda j:(raw[j]-amounts[j],-rows[j]['IdDetalleCompra']),reverse=True)[:remaining]:amounts[j]+=D('.01')
    assert sum(amounts)==D('13431.96')
    audit={'autorizacion':'Sergio20/10/2026: adelante con correcciones NC120722',
           'respaldo':backup_verificado('baya-nc120722-036'),'antes':before,'facturaOrigenAntes':original,
           'pdf':str(PDF),'sha256':hashlib.sha256(PDF.read_bytes()).hexdigest(),
           'criterio':'Neto fiscal13431.96; prorrata del neto de cada linea existente, mayores restos. Creditos negativos; cantidad1ARS; conserva dimensiones. Portal/observacion13427.83 difiere4.13 del pie fiscal.',
           'netosCredito':[-a for a in amounts]}
    path=ROOT/f'nc120722-correccion-{datetime.now():%Y%m%d_%H%M%S}.json'
    path.write_text(json.dumps(audit,default=str,ensure_ascii=False,indent=2),encoding='utf-8')
    with reconciliation_transaction():
        assert state(ID)==before and state(ORIGIN)==original
        statements=[('UPDATE dbo.Compras SET [Ajusta Tipo Cambio]=?,[Fecha Vto]=? WHERE IdDeuda=?',
                     (True,datetime(2025,5,22),ID))]
        for r,amount in zip(rows,amounts):
            statements.append(('UPDATE dbo.Det_Compras SET Cantidad=?,Unidad=?,[Precio Unitario]=?,[Ajuste financiero]=? WHERE IdDetalleCompra=? AND IdCompra=?',
                               (1,'ARS',-amount,True,r['IdDetalleCompra'],ID)))
        execute_write_transaction(statements)
        agregar_documento_relacionado(ID,ORIGIN)
        after=state(ID)
        total=fetch_all('SELECT ImporteDocumento FROM dbo.vw_Compras_ImporteDocumento WHERE IdDeuda=?',(ID,))[0]['ImporteDocumento']
        assert round(total,2)==-16252.67
        orig_after=state(ORIGIN)
        assert orig_after['cabecera']==original['cabecera'] and orig_after['lineas']==original['lineas']
        for new,old,amount in zip(after['lineas'],rows,amounts):
            for key in ['IdDetalleCompra','Producto/Servicio','IVA','IdRubro','IdCentroCostos','IdDestino','IdCampaña','Campaña','IdFormulado']:
                assert new[key]==old[key]
            assert new['Cantidad']==1 and new['Unidad']=='ARS' and new['Ajuste financiero']
            assert abs(D(str(new['Precio Unitario']))+amount)<D('.00001')
        assert ORIGIN in [r['idCompra'] for r in after['relaciones']]
        movements=fetch_all('SELECT * FROM dbo.vw_MovimientosCuenta_Base WHERE Origen=? AND IdOrigen=?',('Compras',ID))
        usd=construir(movements,{ID:{'moneda':'Pesos','tc':1,'ajusta':True}},cotizacion_bna())
        assert usd['saldoDolares']==0
        costs=fetch_all('SELECT IdDetalleCompra,IdDestino,IdCampaña,Pesos,Dolares,Signo FROM dbo.vw_ResultadosCultivo_CostosBase WHERE IdCompra=?',(ID,))
        assert len(costs)==19 and round(sum(abs(c['Pesos'])*c['Signo'] for c in costs),2)==-13431.96
        assert all(c['Dolares']==0 for c in costs)
        audit.update({'despues':after,'total':total,'efectoUSD':usd['saldoDolares'],'costos':costs})
    assert state(ID)==after
    path.write_text(json.dumps(audit,default=str,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'IdDeuda':ID,'credito':round(-total,2),'lineas':19,'USD':usd['saldoDolares'],'respaldo':audit['respaldo']},default=str))


if __name__=='__main__':main()
