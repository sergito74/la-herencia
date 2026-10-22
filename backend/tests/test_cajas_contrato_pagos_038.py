import pytest
from tests.cajas_038_helpers import CajaSimulada, request, guardar


def test_asientos_particulares_consulta_validada(monkeypatch):
    store = CajaSimulada(monkeypatch)
    response = store.client.get(
        "/api/cajas-efectivo/particulares/asientos",
        params={"idContacto": 17, "fecha": "2026-10-22", "importe": "100.00"},
    )
    assert response.status_code == 200 and response.json() == {"items": []}
    assert (
        store.client.get(
            "/api/cajas-efectivo/particulares/asientos",
            params={"idContacto": 17, "fecha": "2026-10-22", "importe": "NaN"},
        ).status_code
        == 422
    )


def test_pago_un_efectivo_una_salida_y_aplicacion(monkeypatch):
    store = CajaSimulada(monkeypatch)
    response = guardar(store, request())
    assert response.status_code == 201, response.text
    assert (
        len(store.rows("Pagos efectivo"))
        == len(store.rows("MovimientosCajaEfectivo"))
        == len(store.rows("AplicacionesPago"))
        == 1
    )
    assert store.rows("Pagos efectivo")[0]["params"][-1] == 100
    assert store.rows("MovimientosCajaEfectivo")[0]["params"][4] == -100
    assert (
        store.rows("MovimientosCajaEfectivo")[0]["params"][8]
        == store.rows("Pagos efectivo")[0]["id"]
    )


def test_pago_parcial_multiples_y_contacto_ajeno(monkeypatch):
    store = CajaSimulada(monkeypatch)
    op = request(
        aplicaciones=[
            {"tipoDocumento": "CompraDeuda", "idDocumento": 10, "importeAplicado": "40"},
            {"tipoDocumento": "CompraDeuda", "idDocumento": 11, "importeAplicado": "60"},
        ]
    )
    assert guardar(store, op).status_code == 201
    assert len(store.rows("AplicacionesPago")) == 2
    store.doc_contact = 18
    r = store.client.post("/api/cajas-efectivo/operaciones/previsualizar", json=request())
    assert r.status_code == 422
    store.doc_contact, store.paid = 17, 50
    assert (
        store.client.post(
            "/api/cajas-efectivo/operaciones/previsualizar", json=request()
        ).status_code
        == 409
    )


def test_gasto_sin_deuda_y_anulacion_conjunta(monkeypatch):
    store = CajaSimulada(monkeypatch)
    r = guardar(store, request("gasto_sin_comprobante"))
    assert r.status_code == 201, r.text
    assert len(store.rows("GastoCajaEfectivo")) == 1 and not store.rows("Pagos efectivo")
    assert any("RepartosGastoCaja" in sql for sql, p in store.state["writes"])
    a = store.client.post(
        "/api/cajas-efectivo/operaciones/1/anular",
        json={"motivo": "Corrección", "versionEsperada": 0},
    )
    assert a.status_code == 200, a.text
    assert (
        store.rows("GastoCajaEfectivo")[0]["anulada"]
        and store.rows("MovimientosCajaEfectivo")[0]["anulada"]
    )
    assert (
        store.client.post(
            "/api/cajas-efectivo/operaciones/1/anular",
            json={"motivo": "Corrección", "versionEsperada": 0},
        ).json()
        == a.json()
    )


def test_particular_pago_asiento_y_socio(monkeypatch):
    store = CajaSimulada(monkeypatch)
    r = guardar(store, request(compraParticular={"idCompra": 10, "idSocio": 1}))
    assert r.status_code == 201, r.text
    assert [x["params"][-1] for x in store.rows("Pagos efectivo")] == [100, -100]
    assert (
        len(store.rows("MovimientosCuentaSocio")) == len(store.rows("MovimientosCajaEfectivo")) == 1
    )


@pytest.mark.parametrize(
    "table",
    ["Pagos efectivo", "AplicacionesPago", "MovimientosCajaEfectivo", "EfectosOperacionCaja"],
)
def test_fallo_en_cada_paso_revierte_todo(monkeypatch, table):
    store = CajaSimulada(monkeypatch)
    store.fail_table = table
    r = guardar(store, request())
    assert r.status_code == 500
    assert not store.state["ops"] and not store.state["records"] and not store.state["effects"]
