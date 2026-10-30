from contextlib import nullcontext
from decimal import Decimal
import pytest
from pydantic import ValidationError
from src.db import connection
from src.features.ordenes_pago import repository as r
from src.features.ordenes_pago.schemas import OrdenInput,VincularInput


@pytest.fixture(autouse=True)
def aislado(monkeypatch):
    monkeypatch.setattr(connection.pyodbc,'connect',lambda *a,**k:pytest.fail('La prueba no debe acceder a WC'))
    monkeypatch.setattr(connection,'reconciliation_transaction',nullcontext)


def body(**changes):
    data=dict(idContacto=7,fecha='2026-10-30',fechaPago='2026-11-01',facturas=[{'idCompra':1,'importe':100}],
              medios=[{'medio':'Transferencia','cuenta':'Galicia','importe':100}])
    return OrdenInput(**(data|changes))


def recibo(**changes):
    return VincularInput(**(dict(idContacto=7,numero='0001-00000001',fecha='2026-10-30',total=100,
        aplicaciones=[dict(origenMovimiento='galicia',idMovimiento=5,idCompra=1,importe=100)])|changes))


@pytest.mark.parametrize('changes',[
 {'facturas':[{'idCompra':1,'importe':-1}]},
 {'facturas':[{'idCompra':1,'importe':100},{'idCompra':1,'importe':100}]},
 {'medios':[{'medio':'Transferencia','cuenta':'Galicia','importe':99.99}]},
 {'moneda':'USD'},
 {'medios':[{'medio':'Transferencia','cuenta':'  ','importe':100}]}])
def test_solicitudes_invalidas(changes):
    with pytest.raises(ValidationError):body(**changes)


def test_saldo_reservado_y_contacto(monkeypatch):
    monkeypatch.setattr(r,'facturas',lambda *a:[{'idCompra':1,'disponible':Decimal('99.99')}])
    with pytest.raises(ValueError,match='saldo'):r.validar_facturas(body())
    monkeypatch.setattr(r,'facturas',lambda *a:[])
    with pytest.raises(ValueError):r.validar_facturas(body())


def test_edicion_obsoleta_y_emitida(monkeypatch):
    for estado,version in [('Emitida',1),('Borrador',2)]:
        monkeypatch.setattr(r,'obtener',lambda *a:{'estado':estado,'version':version})
        with pytest.raises(ValueError,match='cambió'):r.guardar(body(version=1),'test',1)


def test_no_anula_pagada(monkeypatch):
    monkeypatch.setattr(r,'obtener',lambda *a:{'estado':'Pagada'})
    with pytest.raises(ValueError):r.cambiar_estado(1,'Anulada','test')


def test_recibo_no_repite_aplicaciones():
    a=dict(origenMovimiento='galicia',idMovimiento=5,idCompra=1,importe=50)
    with pytest.raises(ValidationError):recibo(aplicaciones=[a,a])


def preparar(monkeypatch,disponible=100,usado=0,existentes=None):
    calls=[]
    monkeypatch.setattr(r,'documento_recibo',lambda *a:dict(idContacto=7,revisado=None,ruta='original.pdf',sha256='a'*64))
    monkeypatch.setattr(r,'pdf_recibo',lambda *a:None)
    monkeypatch.setattr(r,'fetch_one',lambda *a:None)
    monkeypatch.setattr(r,'facturas',lambda *a,**k:[dict(idCompra=1,disponible=Decimal(str(disponible)))])
    monkeypatch.setattr(r,'_vinculos',lambda:[])
    monkeypatch.setattr(r,'_usado',lambda *a:Decimal(str(usado)))
    monkeypatch.setattr(r,'movimiento',lambda *a:({},Decimal('100')))
    monkeypatch.setattr(r.aplicaciones,'aplicaciones_vigentes_de_movimiento',lambda *a:existentes or [])
    monkeypatch.setattr(r,'execute_insert_returning_id',lambda *a:10)
    monkeypatch.setattr(r,'execute_write',lambda *a:calls.append(a))
    monkeypatch.setattr(r,'auditar',lambda *a:None)
    monkeypatch.setattr(r.aplicaciones,'insertar_aplicaciones',lambda *a:calls.append(('aplicar',a)) or [20])
    return calls


def test_vinculacion_nueva_y_aviso_al_final(monkeypatch):
    calls=preparar(monkeypatch)
    assert r.vincular(3,recibo(),'test')=={'idRecibo':10,'aplicaciones':[20]}
    assert calls[0][0]=='aplicar'
    assert 'UPDATE dbo.DocumentosNuevos' in calls[-1][0]


def test_confirma_existente_sin_duplicar(monkeypatch):
    calls=preparar(monkeypatch,0,100,[dict(tipoDocumento='CompraDeuda',idDocumentoAplicado=1,importeAplicado=100,idAplicacion=4)])
    assert r.vincular(3,recibo(),'test')['aplicaciones']==[4]
    assert all(c[0]!='aplicar' for c in calls)


@pytest.mark.parametrize('disponible,usado',[(99.99,0),(100,.01)])
def test_rechaza_exceso_al_centavo(monkeypatch,disponible,usado):
    calls=preparar(monkeypatch,disponible,usado)
    with pytest.raises(ValueError):r.vincular(3,recibo(),'test')
    assert calls==[]


def test_reintento_no_duplica(monkeypatch):
    calls=preparar(monkeypatch)
    monkeypatch.setattr(r,'fetch_one',lambda *a:{'id':10})
    with pytest.raises(ValueError,match='ya está vinculado'):r.vincular(3,recibo(),'test')
    assert calls==[]


def test_orden_otro_proveedor_o_importes(monkeypatch):
    calls=preparar(monkeypatch)
    monkeypatch.setattr(r,'obtener',lambda *a:dict(estado='Emitida',idContacto=8,facturas=[dict(idCompra=1,importe=100)]))
    with pytest.raises(ValueError,match='orden emitida o pagada'):r.vincular(3,recibo(idOrdenPago=2),'test')
    assert calls==[]


def test_pdf_modificado_rechazado(monkeypatch,tmp_path):
    path=tmp_path/'a.pdf';path.write_bytes(b'%PDF-test')
    monkeypatch.setattr(r,'documento_recibo',lambda *a:dict(ruta=str(path),sha256='a'*64))
    with pytest.raises(ValueError,match='cambió'):r.pdf_recibo(1)


def test_orden_con_retencion_pagos_por_el_neto(monkeypatch):
    calls=preparar(monkeypatch)
    orden=lambda *a:dict(estado='Emitida',idContacto=7,retencionGanancias=Decimal('20'),facturas=[dict(idCompra=1,importe=Decimal('120'))])
    monkeypatch.setattr(r,'obtener',orden)
    pago=[dict(origenMovimiento='galicia',idMovimiento=5,idCompra=1,importe=100)]
    assert r.vincular(3,recibo(idOrdenPago=2,total=120,retencion=20,aplicaciones=pago),'test')['idRecibo']==10
    assert any('Pagada' in c[0] for c in calls if isinstance(c[0],str))
    with pytest.raises(ValueError,match='retención'):
        r.vincular(3,recibo(idOrdenPago=2,total=100,aplicaciones=pago),'test')


def test_retencion_sin_orden_pide_certificado(monkeypatch):
    preparar(monkeypatch)
    pago=[dict(origenMovimiento='galicia',idMovimiento=5,idCompra=1,importe=100)]
    with pytest.raises(ValueError,match='certificado'):r.vincular(3,recibo(total=120,retencion=20,aplicaciones=pago),'test')
    monkeypatch.setattr(r,'fetch_one',lambda sql,*a:{'i':Decimal('20')} if 'Retenciones' in sql else None)
    assert r.vincular(3,recibo(total=120,retencion=20,certificadoRetencion='0000-2026-000050',aplicaciones=pago),'test')['idRecibo']==10
    monkeypatch.setattr(r,'fetch_one',lambda sql,*a:{'i':Decimal('19')} if 'Retenciones' in sql else None)
    with pytest.raises(ValueError,match='no coincide'):
        r.vincular(3,recibo(total=120,retencion=20,certificadoRetencion='0000-2026-000050',aplicaciones=pago),'test')


def test_recibo_solo_retencion(monkeypatch):
    calls=preparar(monkeypatch)
    monkeypatch.setattr(r,'fetch_one',lambda sql,*a:{'i':Decimal('348743.53')} if 'Retenciones' in sql else None)
    res=r.vincular(95,recibo(total=348743.53,retencion=348743.53,certificadoRetencion='0000-2026-000013',aplicaciones=[]),'test')
    assert res=={'idRecibo':10,'aplicaciones':[]} and all(c[0]!='aplicar' for c in calls)


def test_anticipo_sin_factura(monkeypatch):
    calls=preparar(monkeypatch)
    assert r.vincular(3,recibo(total=500,anticipo=500,aplicaciones=[]),'test')=={'idRecibo':10,'aplicaciones':[]}
    assert all(c[0]!='aplicar' for c in calls)
    with pytest.raises(ValidationError):recibo(total=500,aplicaciones=[])
    with pytest.raises(ValidationError):recibo(total=500,anticipo=400,aplicaciones=[])


def orden_op(**k):
    return dict(idOrdenPago=2,idContacto=7,fecha=__import__('datetime').date(2026,10,1),estado='Emitida',
                retencionGanancias=Decimal('20'),facturas=[dict(idCompra=1,importe=Decimal('70')),dict(idCompra=2,importe=Decimal('50'))])|k


def test_reparto_neto_descuenta_retencion_de_la_ultima():
    assert [(p['idCompra'],p['importe']) for p in r.reparto_neto(orden_op())]==[(1,Decimal('70')),(2,Decimal('30'))]


def conciliar(monkeypatch,movs):
    calls=[]
    monkeypatch.setattr(r,'fetch_all',lambda *a:[{'id':2}])
    monkeypatch.setattr(r,'obtener',lambda *a:orden_op())
    monkeypatch.setattr(r,'_vinculos',lambda:[])
    monkeypatch.setattr(r,'movimientos',lambda *a:movs)
    monkeypatch.setattr(r.aplicaciones,'insertar_aplicaciones',lambda *a:calls.append(('aplicar',a)) or [30,31])
    monkeypatch.setattr(r,'execute_write',lambda *a:calls.append(a))
    monkeypatch.setattr(r,'auditar',lambda *a:calls.append(('auditar',a)))
    return calls


def mov(i,importe=100,disp=100,fecha=(2026,10,5)):
    return dict(origenMovimiento='galicia',idMovimiento=i,importe=Decimal(str(importe)),disponible=Decimal(str(disp)),
                fecha=__import__('datetime').date(*fecha))


def test_op_pagada_por_debito_unico(monkeypatch):
    calls=conciliar(monkeypatch,[mov(5),mov(6,importe=120,disp=120),mov(7,fecha=(2026,9,30))])
    assert r.conciliar_emitidas('test')=={'pagadas':[2],'ambiguas':[]}
    aplicar=[c for c in calls if c[0]=='aplicar'][0][1]
    assert aplicar[:2]==('galicia',5) and [a['importeAplicado'] for a in aplicar[2]]==[70.0,30.0]
    assert any("Estado='Pagada'" in c[0] for c in calls if isinstance(c[0],str))


@pytest.mark.parametrize('movs,ambiguas',[([mov(5),mov(6)],[2]),([mov(5,disp=50)],[]),([],[])])
def test_op_sin_debito_claro_no_cambia(monkeypatch,movs,ambiguas):
    calls=conciliar(monkeypatch,movs)
    assert r.conciliar_emitidas('test')=={'pagadas':[],'ambiguas':ambiguas}
    assert calls==[]
