"""Una carga y dos disponibilidades: no se conectan ni escriben datos reales."""
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


@pytest.mark.parametrize('importe,fecha', [(100,'2026-10-22'),(-99,'2026-10-22'),(-100,'2026-10-21')])
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
