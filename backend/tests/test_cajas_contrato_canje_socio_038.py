"""Una carga y dos disponibilidades: no se conectan ni escriben datos reales."""
import json
from copy import deepcopy
from uuid import uuid4

import pytest

from src.features.cajas_efectivo import operaciones as db
from src.features.traspasos_internos_tesoreria import repository as transfers
from tests.cajas_038_helpers import CajaSimulada, guardar, request


def canje(**kwargs):
    return request('canje_socio', idSocio=1, banco={'medio':'bna','idMovimiento':7}, **kwargs)


def test_un_canje_incrementa_caja_vincula_banco_y_no_crea_deuda(monkeypatch):
    store = CajaSimulada(monkeypatch)
    store.bank_contacts = [{'IdContacto':5670}]
    p = store.client.post('/api/cajas-efectivo/operaciones/previsualizar', json=canje())
    assert p.status_code == 200, p.text
    assert p.json()['contexto']['canjeSocio']['saldoSocioSinCambios'] is True
    assert p.json()['efectosPrevistos'][0]['importe'] == '100.00'
    key = uuid4()
    assert guardar(store, canje(), key).status_code == 201
    assert store.rows('MovimientosCajaEfectivo')[0]['params'][4] == 100
    bridge = store.rows('Pagos efectivo')[0]['params']
    assert bridge[0] is None and bridge[-1] == -100
    assert len(store.state['banks']) == len(store.rows('TraspasosInternosTesoreria')) == 1
    assert not store.rows('MovimientosCuentaSocio') and not store.rows('GastoCajaEfectivo')
    before = deepcopy(store.state)
    assert guardar(store, canje(), key).status_code == 200
    assert store.state == before


@pytest.mark.parametrize('cambios', [
    {'idSocio':None}, {'banco':None}, {'caja':'giamigli-dolares'},
    {'caja':'condominio-lsc'}, {'idContacto':5670},
    {'cajaContraparte':'condominio-lsc'},
])
def test_canje_exige_socio_banco_y_caja_en_pesos(monkeypatch, cambios):
    store = CajaSimulada(monkeypatch)
    op = canje();op.update(cambios)
    assert store.client.post('/api/cajas-efectivo/operaciones/previsualizar',json=op).status_code == 422
    assert not store.state['records']


@pytest.mark.parametrize('contacto', [375,390,17])
def test_no_acepta_transferencia_de_empleado_otro_socio_o_proveedor(monkeypatch,contacto):
    store = CajaSimulada(monkeypatch)
    store.bank_contacts = [{'IdContacto':contacto}]
    r = store.client.post('/api/cajas-efectivo/operaciones/previsualizar',json=canje())
    assert r.status_code == 422 and 'otra persona' in r.text


@pytest.mark.parametrize('importe,fecha', [(100,'2026-10-22'),(-99,'2026-10-22')])
def test_rechaza_signo_importe_o_fecha_distintos(monkeypatch,importe,fecha):
    store = CajaSimulada(monkeypatch)
    monkeypatch.setattr(transfers,'_movimiento_referencia',lambda *a:{'importe':importe,'fecha':fecha})
    assert store.client.post('/api/cajas-efectivo/operaciones/previsualizar',json=canje()).status_code == 422


@pytest.mark.parametrize('tipo_previo',['AsignacionGasto','Devolucion'])
def test_revalida_aporte_o_retiro_previo_al_confirmar_y_no_deja_media_operacion(monkeypatch,tipo_previo):
    store = CajaSimulada(monkeypatch)
    p = store.client.post('/api/cajas-efectivo/operaciones/previsualizar',json=canje()).json()
    store.socio_withdrawals = [{'IdMovimiento':90,'Tipo':tipo_previo}]
    r = store.client.post('/api/cajas-efectivo/operaciones',headers={'Idempotency-Key':str(uuid4())},
                          json={'operacion':canje(),'previewVersion':p['previewVersion']})
    assert r.status_code == 409 and 'movimiento registrado' in r.text
    assert not store.state['records'] and not store.state['ops']


def test_banco_no_puede_reutilizarse_y_anulacion_revierte_todo(monkeypatch):
    store = CajaSimulada(monkeypatch)
    assert guardar(store,canje()).status_code == 201
    assert store.client.post('/api/cajas-efectivo/operaciones/previsualizar',json=canje()).status_code == 409
    r = store.client.post('/api/cajas-efectivo/operaciones/1/anular',json={'motivo':'Corregir','versionEsperada':0})
    assert r.status_code == 200, r.text
    assert store.rows('MovimientosCajaEfectivo')[0]['anulada']
    assert store.rows('TraspasosInternosTesoreria')[0]['anulada']
    assert not store.rows('MovimientosCuentaSocio')
    assert store.client.post('/api/cajas-efectivo/operaciones/previsualizar',json=canje()).status_code == 200


def test_fallo_al_crear_vinculo_revierte_caja_y_puente(monkeypatch):
    store = CajaSimulada(monkeypatch)
    store.fail_table = 'TraspasosInternosTesoreria'
    assert guardar(store,canje()).status_code == 500
    assert not store.state['ops'] and not store.state['records'] and not store.state['banks']


def test_aplicaciones_previas_del_banco_impiden_el_canje(monkeypatch):
    store = CajaSimulada(monkeypatch)
    read = db.read
    monkeypatch.setattr(db,'read',lambda sql,params=():[{'IdAplicacion':5}] if 'WHERE OrigenMovimiento=?' in sql else read(sql,params))
    assert store.client.post('/api/cajas-efectivo/operaciones/previsualizar',json=canje()).status_code == 409



def pendiente():
    op = canje(); op.pop('banco'); op['bancoPendiente'] = 'bna'
    return op


def conciliar(store, id=7, medio='bna', version=0):
    return store.client.post('/api/cajas-efectivo/operaciones/1/conciliar-banco', json={
        'banco': {'medio': medio, 'idMovimiento': id}, 'versionEsperada': version})


def test_pendiente_sin_extracto_y_conciliacion_posterior_sin_duplicados(monkeypatch):
    store = CajaSimulada(monkeypatch)
    lookup = transfers._movimiento_referencia
    monkeypatch.setattr(transfers, '_movimiento_referencia', lambda *a: (_ for _ in ()).throw(AssertionError('No debe pedir extracto')))
    key = uuid4()
    assert guardar(store, pendiente(), key).status_code == 201
    assert len(store.rows('MovimientosCajaEfectivo')) == len(store.rows('Pagos efectivo')) == 1
    assert not store.state['banks'] and not store.rows('TraspasosInternosTesoreria')
    monkeypatch.setattr(transfers, '_movimiento_referencia', lookup)
    r = conciliar(store)
    assert r.status_code == 200, r.text
    assert r.json()['version'] == 1
    before = deepcopy(store.state)
    assert conciliar(store).status_code == 200  # Retry after lost response
    assert guardar(store, pendiente(), key).status_code == 200
    assert store.state == before
    assert len(store.rows('MovimientosCajaEfectivo')) == len(store.rows('Pagos efectivo')) == len(store.rows('TraspasosInternosTesoreria')) == 1
    assert not store.rows('MovimientosCuentaSocio')
    assert conciliar(store, id=8).status_code == 409
    assert store.client.post('/api/cajas-efectivo/operaciones/1/anular', json={'motivo':'Corregir','versionEsperada':1}).status_code == 200
    assert store.rows('TraspasosInternosTesoreria')[0]['anulada']


def test_pendiente_admite_fecha_de_contabilizacion_bancaria_distinta(monkeypatch):
    store = CajaSimulada(monkeypatch)
    assert guardar(store, pendiente()).status_code == 201
    monkeypatch.setattr(transfers, '_movimiento_referencia', lambda *a: {'importe':-100,'fecha':'2026-10-23'})
    assert conciliar(store).status_code == 200


@pytest.mark.parametrize('caso', ['banco','importe','destinatario','version','fallo'])
def test_conciliacion_rechaza_y_revierte_sin_tocar_efectivo(monkeypatch, caso):
    store = CajaSimulada(monkeypatch)
    assert guardar(store, pendiente()).status_code == 201
    if caso == 'importe':
        monkeypatch.setattr(transfers, '_movimiento_referencia', lambda *a: {'importe':-99,'fecha':'2026-10-22'})
    if caso == 'destinatario': store.bank_contacts = [{'IdContacto':375}]
    if caso == 'fallo': store.fail_table = 'TraspasosInternosTesoreria'
    before = deepcopy(store.state)
    r = conciliar(store, medio='galicia' if caso == 'banco' else 'bna', version=1 if caso == 'version' else 0)
    assert r.status_code == (500 if caso == 'fallo' else 409 if caso == 'version' else 422), r.text
    assert store.state == before


def test_anular_pendiente_y_rechazar_conciliacion_y_lectura(monkeypatch):
    store = CajaSimulada(monkeypatch)
    assert guardar(store, pendiente()).status_code == 201
    r = store.client.post('/api/cajas-efectivo/operaciones/1/conciliar-banco', headers={'X-Test-Role':'Lectura'}, json={'banco':{'medio':'bna','idMovimiento':7},'versionEsperada':0})
    assert r.status_code == 403
    assert store.client.post('/api/cajas-efectivo/operaciones/1/anular', json={'motivo':'Corregir','versionEsperada':0}).status_code == 200
    assert conciliar(store).status_code == 409
    assert not store.rows('TraspasosInternosTesoreria')


def test_pendiente_no_admite_banco_doble_ni_otros_tipos(monkeypatch):
    store = CajaSimulada(monkeypatch)
    for op in [dict(canje(), bancoPendiente='bna'), dict(pendiente(),tipo='aporte')]:
        assert store.client.post('/api/cajas-efectivo/operaciones/previsualizar',json=op).status_code == 422



def test_banco_ya_usado_no_se_puede_vincular_a_un_pendiente(monkeypatch):
    store = CajaSimulada(monkeypatch)
    assert guardar(store, pendiente()).status_code == 201
    assert guardar(store, canje()).status_code == 201
    before = deepcopy(store.state)
    assert conciliar(store).status_code == 409
    assert store.state == before


def test_pendiente_tambien_rechaza_aporte_o_retiro_previo(monkeypatch):
    store = CajaSimulada(monkeypatch)
    store.socio_withdrawals = [{'IdMovimiento':90}]
    assert store.client.post('/api/cajas-efectivo/operaciones/previsualizar', json=pendiente()).status_code == 409
    assert not store.state['ops']


def test_lista_pendientes_contrato_paginado_y_consulta_acotada(monkeypatch):
    store = CajaSimulada(monkeypatch)
    calls = []
    def read(sql, params=()):
        calls.append((sql,params))
        return [{'total':21}] if 'COUNT(*)' in sql else [{'idOperacion':5,'fecha':'2026-10-22','socio':'Sergio','importe':'100.00','banco':'bna'}]
    monkeypatch.setattr(db,'read',read)
    monkeypatch.setattr(db,'one',lambda sql,params=(): read(sql,params)[0])
    r = store.client.get('/api/cajas-efectivo/giamigli-sa/transferencias-pendientes?page=2&pageSize=20')
    assert r.status_code == 200 and r.json()['total'] == 21 and r.json()['items'][0]['idOperacion'] == 5
    assert calls[-1][1] == ('giamigli-sa',20,20)
    assert all("o.Estado='Vigente'" in sql and 'NOT EXISTS' in sql and '$.bancoPendiente' in sql for sql,_ in calls)
    assert store.client.get('/api/cajas-efectivo/inexistente/transferencias-pendientes').status_code == 404
    assert store.client.get('/api/cajas-efectivo/giamigli-sa/transferencias-pendientes?pageSize=1000').status_code == 422


def test_numero_de_transaccion_queda_en_el_asiento_de_caja(monkeypatch):
    store = CajaSimulada(monkeypatch)
    assert guardar(store, dict(pendiente(), numeroTransaccion='000123456')).status_code == 201
    [mov] = store.rows('MovimientosCajaEfectivo')
    assert mov['params'][3] == 'Transacción bancaria N° 000123456'
    [op] = store.state['ops'].values()
    assert json.loads(op['Solicitud'])['numeroTransaccion'] == '000123456'
    for bad in [dict(request('aporte', idSocio=1), numeroTransaccion='1'), dict(pendiente(), numeroTransaccion='x'*61)]:
        assert store.client.post('/api/cajas-efectivo/operaciones/previsualizar', json=bad).status_code == 422


def test_numero_de_transaccion_en_extraccion_y_deposito():
    from src.features.cajas_efectivo.schemas import OperacionCaja
    for tipo in ('extraccion_banco', 'deposito_banco'):
        op = OperacionCaja.model_validate(request(tipo, banco={'medio': 'bna', 'idMovimiento': 7}, numeroTransaccion='987'))
        assert op.numeroTransaccion == '987'
