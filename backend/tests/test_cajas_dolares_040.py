from datetime import date
from decimal import Decimal
from io import BytesIO
from uuid import uuid4

import pytest
from tests.test_cajas_contrato_arqueos_038 import count as count_fixture
from openpyxl import Workbook
from pydantic import ValidationError
from src.features.cajas_efectivo.schemas import OperacionCaja
from src.features.cajas_efectivo import service, importacion
from src.features.cuentas_socios import valuacion
from tests.cajas_038_helpers import CajaSimulada, guardar, request


def test_no_cruza_monedas_ni_circuitos_pesos():
    for payload in [
        request("traspaso_cajas", cajaDestino="giamigli-dolares"),
        request(
            "pago",
            caja="giamigli-dolares",
            idContacto=17,
            aplicaciones=[
                {"tipoDocumento": "CompraDeuda", "idDocumento": 10, "importeAplicado": "100.00"}
            ],
        ),
        request("ingreso_dolares", caja="giamigli-sa"),
    ]:
        with pytest.raises(ValidationError):
            OperacionCaja.model_validate(payload)


def test_ingreso_egreso_usd_reintento_y_anulacion(monkeypatch):
    store = CajaSimulada(monkeypatch)
    key = uuid4()
    payload = request("ingreso_dolares", caja="giamigli-dolares")
    a = guardar(store, payload, key)
    b = guardar(store, payload, key)
    assert a.status_code == 201 and b.status_code == 200
    cash = store.rows("MovimientosCajaEfectivo")
    assert len(cash) == 1 and cash[0]["params"][4] == Decimal("100")
    assert not store.rows("Pagos efectivo") and not store.rows("MovimientosCuentaSocio")
    r = store.client.post(
        "/api/cajas-efectivo/operaciones/1/anular",
        json={"motivo": "Correccion", "versionEsperada": 0},
    )
    assert r.status_code == 200, r.text
    assert store.rows("MovimientosCajaEfectivo")[0]["anulada"]
    op = OperacionCaja.model_validate(request("egreso_dolares", caja="giamigli-dolares"))
    assert service.piernas(op) == {"giamigli-dolares": Decimal("-100")}


def test_valuacion_usd_no_usa_inmag(monkeypatch):
    calls = []

    def quote(sql, params):
        calls.append(sql)
        return {"fecha": date(2026, 10, 23), "valor": 1400}

    monkeypatch.setattr(valuacion, "fetch_one", quote)
    v = valuacion.dolares_a_fecha(Decimal("123.45"), date(2026, 10, 23))
    assert v["importeUSD"] == Decimal("123.45") and v["importeKgCarne"] == 0
    assert v["importePesos"] == Decimal("172830.00")
    assert len(calls) == 1 and "Dolar BNA" in calls[0]


def test_importa_columna_usd_no_pesos():
    w = Workbook()
    s = w.active
    s.title = "Caja Efectivo Dolares"
    s.append(
        ["Fecha", "Concepto", "Cuenta", "Razon Social", "PC", "Importe $", "Importe u$s", "Saldo"]
    )
    s.append([date(2023, 4, 27), "Venta Dolares", "B", "Referencia", None, 122590, -260, 360])
    b = BytesIO()
    w.save(b)
    rows = importacion.parse(b.getvalue(), "CajasGiamigli", date(2026, 10, 23))
    assert rows[0]["normalizada"]["importe"] == "-260.00"
    assert rows[0]["normalizada"]["caja"] == "giamigli-dolares"
    assert rows[0]["normalizada"]["numeroDocumento"] is None


@pytest.mark.parametrize(
    "tipo,tipo_socio", [("aporte", "Devolucion"), ("retiro_a_cuenta", "AsignacionGasto")]
)
def test_aporte_retiro_preserva_dolares_y_anula_juntos(monkeypatch, tipo, tipo_socio):
    store = CajaSimulada(monkeypatch)
    monkeypatch.setattr(
        valuacion,
        "dolares_a_fecha",
        lambda amount, fecha: {
            "importeUSD": amount,
            "importeKgCarne": Decimal(0),
            "importePesos": amount * Decimal(1400),
            "dolar": {"fecha": fecha, "valor": 1400},
            "fuenteDolar": "Dolar BNA.Prom_billete",
        },
    )
    r = guardar(store, request(tipo, caja="giamigli-dolares"))
    assert r.status_code == 201, r.text
    a = store.rows("MovimientosCuentaSocio")[0]["params"]
    assert a[1] == tipo_socio and a[2] == Decimal("140000")
    assert a[9] == Decimal("100") and a[10] == 0
    assert not store.rows("Pagos efectivo")
    r = store.client.post(
        "/api/cajas-efectivo/operaciones/1/anular",
        json={"motivo": "Correccion", "versionEsperada": 0},
    )
    assert r.status_code == 200, r.text
    assert all(
        x["anulada"]
        for x in store.rows("MovimientosCuentaSocio") + store.rows("MovimientosCajaEfectivo")
    )


def test_sin_cotizacion_no_inventa_equivalencia(monkeypatch):
    monkeypatch.setattr(valuacion, "fetch_one", lambda *args: None)
    with pytest.raises(ValueError, match="No hay dólar BNA"):
        valuacion.dolares_a_fecha(Decimal(100), date(2026, 10, 23))


count = count_fixture


def test_arqueo_usd_compara_billetes_sin_convertir(count):
    client, state = count
    state["saldo"] = Decimal("360.00")
    r = client.post(
        "/api/cajas-efectivo/giamigli-dolares/arqueos",
        json={
            "fechaCorte": "2026-10-23",
            "denominaciones": [{"valor": "100", "cantidad": 3}, {"valor": "20", "cantidad": 3}],
        },
    )
    assert r.status_code == 201, r.text
    a = r.json()
    assert Decimal(a["totalContado"]) == 360 and Decimal(a["diferencia"]) == 0
    r = client.post(
        "/api/cajas-efectivo/giamigli-dolares/arqueos/1/confirmar",
        json={
            "versionEsperada": a["version"],
            "previewVersion": a["previewVersion"],
            "aceptarDiferencia": True,
        },
    )
    assert r.status_code == 200, r.text
    assert state["ops"] == 0
