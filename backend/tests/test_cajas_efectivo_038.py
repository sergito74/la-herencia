from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from uuid import uuid4

from tests.cajas_038_helpers import CajaSimulada, request, guardar
from src.features.cajas_efectivo import service, operaciones as db
from src.features.cajas_efectivo.schemas import OperacionCaja, ConfirmarOperacion
from src.features.aplicaciones_pago import repository as apps


def test_dos_confirmaciones_concurrentes_una_operacion(monkeypatch):
    store = CajaSimulada(monkeypatch)
    op = OperacionCaja.model_validate(request())
    preview = service.previsualizar(op)
    body = ConfirmarOperacion(operacion=op, previewVersion=preview["previewVersion"])
    key = uuid4()
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(service.crear, body, key, "prueba") for _ in range(2)]
        results = [f.result() for f in futures]
    assert sorted(created for result, created in results) == [False, True]
    assert len(store.state["ops"]) == len(store.rows("Pagos efectivo")) == 1


def test_compra_particular_dolares_y_total_original(monkeypatch):
    function = apps._importe_total_documento
    store = CajaSimulada(monkeypatch)
    original = store.one

    def one(sql, params=()):
        if "c.IdContacto contacto" in sql:
            return {"contacto": 17, "moneda": "Dolares", "tc": Decimal(2)}
        return original(sql, params)

    monkeypatch.setattr(db, "one", one)
    op = request(
        importe="200",
        compraParticular={"idCompra": 10, "idSocio": 1},
        aplicaciones=[
            {"tipoDocumento": "CompraDeuda", "idDocumento": 10, "importeAplicado": "200"}
        ],
    )
    response = guardar(store, op)
    assert response.status_code == 201, response.text
    assert [r["params"][-1] for r in store.rows("Pagos efectivo")] == [200, -200]
    monkeypatch.setattr(
        apps,
        "fetch_all",
        lambda *a: [{"total": 0, "particular": -100, "moneda": "Dolares", "tc": 2}],
    )
    monkeypatch.setattr(
        apps,
        "fetch_all",
        lambda *a: [{"total": 0, "particular": -100, "moneda": "Dolares", "tc": 2}],
    )
    assert function("CompraDeuda", 10) == 200


def test_datetime2_texto_y_minimo_posterior(monkeypatch):
    monkeypatch.setattr(
        db,
        "read",
        lambda sql, params=(): (
            []
            if "Arqueos" in sql
            else [
                {
                    "id": 1,
                    "fecha": "2026-10-21 00:00:00",
                    "importe": Decimal(100),
                    "anulada": False,
                },
                {
                    "id": 2,
                    "fecha": "2026-10-23 00:00:00",
                    "importe": Decimal(-90),
                    "anulada": False,
                },
                {
                    "id": 3,
                    "fecha": "2026-10-24 00:00:00",
                    "importe": Decimal(100),
                    "anulada": False,
                },
            ]
        ),
    )
    context = db.caja_context("giamigli-sa", date(2026, 10, 22))
    assert context["saldoActual"] == 110 and context["minimoPosterior"] == 10
    monkeypatch.setattr(service, "_references", lambda op: {})
    preview = service.previsualizar(
        OperacionCaja.model_validate(request("traspaso_cajas", importe="20"))
    )
    assert "SALDO_NEGATIVO" in preview["advertencias"]


def test_particular_dos_pagos_un_solo_gasto_y_asiento(monkeypatch):
    store = CajaSimulada(monkeypatch)
    op = request(
        importe="50",
        compraParticular={"idCompra": 10, "idSocio": 1},
        aplicaciones=[{"tipoDocumento": "CompraDeuda", "idDocumento": 10, "importeAplicado": "50"}],
    )
    assert guardar(store, op).status_code == 201
    assert guardar(store, op).status_code == 201
    assert len(store.rows("MovimientosCuentaSocio")) == 1
    assert store.rows("MovimientosCuentaSocio")[0]["params"][2] == 100
    assert [x["params"][-1] for x in store.rows("Pagos efectivo")] == [50, -100, 50]
    assert (
        store.client.post(
            "/api/cajas-efectivo/operaciones/1/anular",
            json={"motivo": "Error", "versionEsperada": 0},
        ).status_code
        == 409
    )
    assert (
        store.client.post(
            "/api/cajas-efectivo/operaciones/2/anular",
            json={"motivo": "Error", "versionEsperada": 0},
        ).status_code
        == 200
    )
    assert (
        store.client.post(
            "/api/cajas-efectivo/operaciones/1/anular",
            json={"motivo": "Error", "versionEsperada": 0},
        ).status_code
        == 200
    )


def test_saldo_de_anulacion_excluye_en_orden_real(monkeypatch):
    rows=[{'id':1,'fecha':'2026-10-22 00:00:00','importe':Decimal(100),'anulada':False,'operacion':1},
          {'id':2,'fecha':'2026-10-22 00:00:00','importe':Decimal(-80),'anulada':False,'operacion':2}]
    monkeypatch.setattr(db,'read',lambda sql,params=():[] if 'Arqueos' in sql else rows)
    context=db.caja_context('giamigli-sa',date(2026,10,22),excluir_operacion=1)
    assert context['saldoActual']==-80 and context['minimoPosterior']==-80
    assert context['movimientosExcluidos']==1
