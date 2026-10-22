from datetime import date
import pytest
from tests.cajas_038_helpers import CajaSimulada, request, guardar
from src.features.cuentas_socios.valuacion import calcular, proporciones


@pytest.mark.parametrize(
    "fecha", [date(2011, 1, 1), date(2020, 3, 15), date(2020, 3, 16), date(2026, 10, 22)]
)
def test_formula_compartida_preserva_regla_036(fecha):
    for amount in (100, 134724.39, 1800000):
        kg_part, usd_part = proporciones(fecha)
        legacy_usd = amount / 1000 if fecha < date(2020, 3, 16) else amount * 0.5 / 1000
        legacy_kg = 0 if fecha < date(2020, 3, 16) else amount * 0.5 / 2000
        assert amount * usd_part / 1000 == legacy_usd
        assert (amount * kg_part / 2000 if kg_part else 0) == legacy_kg
        new = calcular(amount, fecha, 1000, 2000)
        assert abs(float(new["importeUSD"]) - legacy_usd) <= 0.000051
        assert abs(float(new["importeKgCarne"]) - legacy_kg) <= 0.00051


@pytest.mark.parametrize("tipo", ["aporte", "retiro_a_cuenta"])
def test_socio_anula_y_condominio_no_duplica(monkeypatch, tipo):
    store = CajaSimulada(monkeypatch)
    response = guardar(
        store,
        request(
            tipo,
            idSocio=3,
            cajaContraparte="condominio-lsc",
            motivoRelacionGiamigli="Aporte/devolución",
        ),
    )
    assert response.status_code == 201
    assert sum(r["params"][4] for r in store.rows("MovimientosCajaEfectivo")) == 0
    response = store.client.post(
        "/api/cajas-efectivo/operaciones/1/anular",
        json={"motivo": "Corregir", "versionEsperada": 0},
    )
    assert response.status_code == 200, response.text
    assert all(
        r["anulada"]
        for r in store.rows("MovimientosCuentaSocio") + store.rows("MovimientosCajaEfectivo")
    )
