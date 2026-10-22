import pytest
from tests.cajas_038_helpers import CajaSimulada, request, guardar


@pytest.mark.parametrize("tipo", ["VentaHacienda", "VentaGranos", "Alquiler"])
def test_cobro_anulado_libera_aplicacion(monkeypatch, tipo):
    store = CajaSimulada(monkeypatch)
    response = guardar(
        store,
        request(
            "cobro",
            aplicaciones=[{"tipoDocumento": tipo, "idDocumento": 10, "importeAplicado": "100"}],
        ),
    )
    assert response.status_code == 201
    response = store.client.post(
        "/api/cajas-efectivo/operaciones/1/anular", json={"motivo": "Error", "versionEsperada": 0}
    )
    assert response.status_code == 200, response.text
    assert all(
        r["anulada"] for r in store.rows("AplicacionesPago") + store.rows("MovimientosCajaEfectivo")
    )
