from datetime import datetime
from tests.cajas_038_helpers import CajaSimulada, request, guardar


def test_banco_no_puede_vincularse_dos_veces(monkeypatch):
    store = CajaSimulada(monkeypatch)
    assert guardar(store, request("extraccion_banco")).status_code == 201
    preview = store.client.post(
        "/api/cajas-efectivo/operaciones/previsualizar", json=request("extraccion_banco")
    )
    assert preview.status_code == 409
    assert len(store.state["ops"]) == 1
    payment = store.rows("Pagos efectivo")[0]["id"]
    assert store.rows("MovimientosCajaEfectivo")[0]["params"][8] == payment


def test_retorno_parcial_y_periodo_historico_bloqueados(monkeypatch):
    store = CajaSimulada(monkeypatch)
    store.salary_date = datetime(2017, 12, 1)
    op = request("retorno_sueldo_opcion_a", idSalario=123, evidencia="Retorno")
    assert (
        store.client.post("/api/cajas-efectivo/operaciones/previsualizar", json=op).status_code
        == 409
    )
    store.salary_date = datetime(2026, 10, 22)
    op["importe"] = "50"
    assert (
        store.client.post("/api/cajas-efectivo/operaciones/previsualizar", json=op).status_code
        == 422
    )
    assert not store.state["ops"]


def test_fallo_ajuste_no_cobrado_revierte_banco_y_caja(monkeypatch):
    store = CajaSimulada(monkeypatch)
    store.fail_table = "AjustesCuentaCorriente"
    response = guardar(
        store, request("retorno_sueldo_opcion_a", idSalario=123, evidencia="Retorno")
    )
    assert response.status_code == 500
    assert not store.state["ops"] and not store.state["records"] and not store.state["banks"]


def test_opcion_a_por_diez_mil_y_anulacion(monkeypatch):
    from decimal import Decimal
    from src.features.traspasos_internos_tesoreria import repository as transfers
    store=CajaSimulada(monkeypatch)
    store.salary_total=Decimal('10000')
    monkeypatch.setattr(transfers,'_movimiento_referencia',lambda medio,id:{'medio':medio,
        'idMovimiento':id,'importe':-10000,'fecha':'2026-10-22'})
    response=guardar(store,request('retorno_sueldo_opcion_a',importe='10000',idSalario=123,evidencia='Retorno documentado'))
    assert response.status_code==201,response.text
    assert store.rows('AjustesCuentaCorriente')[0]['params'][1]==10000
    assert store.rows('MovimientosCajaEfectivo')[0]['params'][4]==10000
    assert not store.rows('MovimientosCuentaSocio')
    response=store.client.post('/api/cajas-efectivo/operaciones/1/anular',json={'motivo':'Corregir','versionEsperada':0})
    assert response.status_code==200,response.text
    assert all(o['Estado']=='Anulada' for o in store.state['ops'].values())
