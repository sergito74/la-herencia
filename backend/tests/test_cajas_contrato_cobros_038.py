import pytest
from tests.cajas_038_helpers import CajaSimulada, request, guardar


@pytest.mark.parametrize("documento", ["VentaHacienda", "VentaGranos", "Alquiler"])
def test_cobro_con_signos_y_aplicacion(monkeypatch, documento):
    store = CajaSimulada(monkeypatch)
    r = guardar(
        store,
        request(
            "cobro",
            aplicaciones=[
                {"tipoDocumento": documento, "idDocumento": 10, "importeAplicado": "100"}
            ],
        ),
    )
    assert r.status_code == 201, r.text
    assert store.rows("Pagos efectivo")[0]["params"][-1] == -100
    assert store.rows("MovimientosCajaEfectivo")[0]["params"][4] == 100
    assert len(store.rows("AplicacionesPago")) == 1
