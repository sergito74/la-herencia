from datetime import date
from decimal import Decimal

import pytest
from tests.cajas_038_helpers import CajaSimulada, request, guardar
from src.features.cuentas_socios.valuacion import calcular


@pytest.mark.parametrize(
    "tipo,sign,socio_tipo",
    [("aporte", 100, "Devolucion"), ("retiro_a_cuenta", -100, "AsignacionGasto")],
)
def test_aporte_retiro_signo_y_valuacion(monkeypatch, tipo, sign, socio_tipo):
    store = CajaSimulada(monkeypatch)
    r = guardar(store, request(tipo))
    assert r.status_code == 201, r.text
    assert store.rows("MovimientosCajaEfectivo")[0]["params"][4] == sign
    s = store.rows("MovimientosCuentaSocio")[0]["params"]
    assert s[1] == socio_tipo and s[-2:] == (Decimal(".5000"), Decimal(".250"))


def test_condominio_y_pago_directo(monkeypatch):
    store = CajaSimulada(monkeypatch)
    r = guardar(
        store,
        request(
            "aporte", idSocio=3, cajaContraparte="condominio-lsc", motivoRelacionGiamigli="Aporte"
        ),
    )
    assert r.status_code == 201, r.text
    assert [x["params"][4] for x in store.rows("MovimientosCajaEfectivo")] == [100, -100]
    assert len(store.rows("MovimientosCuentaSocio")) == 1 and not store.rows("Pagos efectivo")
    r = guardar(store, request(caja="condominio-lsc", motivoRelacionGiamigli="Gasto de Giamigli"))
    assert r.status_code == 201, r.text
    assert len(store.rows("MovimientosCajaEfectivo")) == 3
    assert len(store.rows("MovimientosCuentaSocio")) == 2 and len(store.rows("Pagos efectivo")) == 1


def test_ganancias_sin_deuda(monkeypatch):
    store = CajaSimulada(monkeypatch)
    assert guardar(store, request("retiro_ganancias")).status_code == 201
    assert not store.rows("MovimientosCuentaSocio")


def test_formula_historica_y_cotizacion_faltante():
    assert calcular(100, date(2020, 3, 15), 10, 20) == {
        "importeUSD": Decimal("5.0000"), "importeKgCarne": Decimal("2.500"),
    }
    with pytest.raises(ValueError):
        calcular(100, date(2011, 3, 21), 10)
    assert calcular(100, date(2020, 3, 16), 10, 20) == {
        "importeUSD": Decimal("5.0000"),
        "importeKgCarne": Decimal("2.500"),
    }
    with pytest.raises(ValueError):
        calcular(100, date(2026, 1, 1), 10, None)
