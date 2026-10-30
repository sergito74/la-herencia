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
    with pytest.raises(ValueError,match='orden emitida'):r.vincular(3,recibo(idOrdenPago=2),'test')
    assert calls==[]


def test_pdf_modificado_rechazado(monkeypatch,tmp_path):
    path=tmp_path/'a.pdf';path.write_bytes(b'%PDF-test')
    monkeypatch.setattr(r,'documento_recibo',lambda *a:dict(ruta=str(path),sha256='a'*64))
    with pytest.raises(ValueError,match='cambió'):r.pdf_recibo(1)
