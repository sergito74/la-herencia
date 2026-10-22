from tests.cajas_038_helpers import CajaSimulada, request, guardar


def test_traspaso_sin_terceros(monkeypatch):
    store = CajaSimulada(monkeypatch)
    r = guardar(store, request("traspaso_cajas"))
    assert r.status_code == 201, r.text
    assert [x["params"][4] for x in store.rows("MovimientosCajaEfectivo")] == [-100, 100]
    assert not store.rows("Pagos efectivo") and not store.rows("MovimientosCuentaSocio")


def test_banco_puente_sin_contacto_y_reversion(monkeypatch):
    store = CajaSimulada(monkeypatch)
    r = guardar(store, request("extraccion_banco", intermediario="Sergio", evidencia="Extracto"))
    assert r.status_code == 201, r.text
    assert store.rows("Pagos efectivo")[0]["params"][0] is None
    assert len(store.state["banks"]) == len(store.rows("TraspasosInternosTesoreria")) == 1
    assert not store.rows("MovimientosCuentaSocio")
    r = store.client.post(
        "/api/cajas-efectivo/operaciones/1/anular",
        json={"motivo": "Corregir", "versionEsperada": 0},
    )
    assert r.status_code == 200, r.text
    assert store.rows("TraspasosInternosTesoreria")[0]["anulada"]


def test_opcion_a_no_cobrado_cero_aporte(monkeypatch):
    store = CajaSimulada(monkeypatch)
    r = guardar(
        store, request("retorno_sueldo_opcion_a", idSalario=123, evidencia="Retorno documentado")
    )
    assert r.status_code == 201, r.text
    assert len(store.rows("AjustesCuentaCorriente")) == 1
    assert len(store.rows("MovimientosCajaEfectivo")) == 1 and not store.rows(
        "MovimientosCuentaSocio"
    )
    assert any(e["TipoEfecto"] == "AjusteNoCobrado" for e in store.state["effects"])
