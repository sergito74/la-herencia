from tests.cajas_038_helpers import CajaSimulada, request, guardar
from src.features.cajas_efectivo import operaciones as db


def test_dependencias_de_socio_y_reasignacion_no_se_borran(monkeypatch):
    store = CajaSimulada(monkeypatch)
    assert guardar(store, request("aporte")).status_code == 201
    original = store.read
    monkeypatch.setattr(
        db,
        "read",
        lambda sql, params=(): (
            [{"id": 999, "contacto": 17}]
            if "FROM dbo.PagosSocioProveedor" in sql
            else original(sql, params)
        ),
    )
    response = store.client.post(
        "/api/cajas-efectivo/operaciones/1/anular", json={"motivo": "Error", "versionEsperada": 0}
    )
    assert response.status_code == 409 and "999" in response.text
    assert store.rows("MovimientosCuentaSocio")[0]["anulada"] is False


def test_operacion_ajena_inexistente_no_crea_historia(monkeypatch):
    store = CajaSimulada(monkeypatch)
    assert (
        store.client.post(
            "/api/cajas-efectivo/operaciones/999/anular",
            json={"motivo": "Error", "versionEsperada": 0},
        ).status_code
        == 404
    )
    assert not store.state["records"]


def test_costo_gasto_caja_incluido_una_vez_y_usd_no_valuado(monkeypatch):
    from src.features.resultado_cultivo import costos

    monkeypatch.setattr(costos, "costos_heredados", lambda *a: [])
    monkeypatch.setattr(costos, "costo_ordenes_trabajo", lambda *a: [])
    monkeypatch.setattr(costos.mapeo, "idCultivo_a_destino", lambda *a: 6)

    def fetch(sql, params):
        assert "g.Anulada=0 AND op.Estado='Vigente'" in sql
        assert params == (6, 32)
        return [
            {
                "concepto": "Gasto",
                "montoPesos": 100,
                "montoDolares": None,
                "origen": "GastoCaja",
                "idGasto": 1,
                "idReparto": 1,
                "idOperacion": 1,
            }
        ]

    monkeypatch.setattr(costos, "fetch_all", fetch)
    result = costos.costo_total(3, 32)
    assert result["pesos"] == 100 and len(result["lineas"]) == 1
    assert result["lineas"][0]["montoDolares"] is None


def test_anular_entrada_pide_confirmar_saldo_negativo(monkeypatch):
    from decimal import Decimal
    from src.features.cajas_efectivo import service
    store=CajaSimulada(monkeypatch)
    assert guardar(store,request('aporte')).status_code==201
    monkeypatch.setattr(db,'caja_context',lambda *a,**k:{'saldoActual':Decimal('-80'),
        'minimoPosterior':Decimal('-80'),'arqueos':[],'movimientosExcluidos':1})
    preview=service.previsualizar_anulacion(1)
    body={'motivo':'Error','versionEsperada':0}
    assert store.client.post('/api/cajas-efectivo/operaciones/1/anular',json=body).status_code==409
    body.update(previewVersion=preview['previewVersion'],advertenciasAceptadas=['SALDO_NEGATIVO'])
    assert store.client.post('/api/cajas-efectivo/operaciones/1/anular',json=body).status_code==200


def test_gasto_sin_clasificar_expone_usd_incompleto(monkeypatch):
    from src.features.resultado_cultivo import resultado
    monkeypatch.setattr(resultado,'fetch_one',lambda sql,params:{'pesos':100,'dolares':None,'noValuados':1} if 'GastoCajaEfectivo' in sql else None)
    result=resultado.costo_sin_clasificar(32)
    assert result['montoPesos']==100 and result['valuacionDolaresIncompleta'] is True
    assert 'pendientes de valuar' in result['motivo']
