"""Percepciones al pie: cálculo, persistencia parametrizada y contrato, sin DB."""

from copy import deepcopy
import re

from fastapi import FastAPI
import httpx
import pytest

from src.features.compras import repository, repository_locks
from src.features.compras.router import router
from src.features.compras.schemas import CompraAltaRequest, CompraEditRequest


BODY = {
    "idContacto": 1,
    "fecha": "2026-10-02",
    "tipo": "A",
    "tipoDocumento": "Factura",
    "numeroDocumento": "0001-00001234",
    "moneda": "Pesos",
    "ingresosBrutos": 13.25,
    "percepcionIva": 27.50,
    "lineas": [{"productoServicio": "Insumo", "cantidad": 2,
                "precioUnitario": 100, "iva": 21}],
}


@pytest.fixture(autouse=True)
def sin_base_de_datos(monkeypatch):
    def prohibido(*args, **kwargs):
        pytest.fail("Esta prueba no debe acceder a una base real")

    for nombre in ("fetch_one", "fetch_all", "execute_write_transaction"):
        monkeypatch.setattr(repository, nombre, prohibido)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.parametrize("modelo", [CompraAltaRequest, CompraEditRequest])
def test_payload_anterior_asume_percepcion_iva_cero(modelo):
    anterior = {k: v for k, v in BODY.items() if k != "percepcionIva"}
    assert modelo(**anterior).model_dump()["percepcionIva"] == 0


def test_percepciones_suman_una_vez_sin_alterar_base_ni_iva():
    cabecera = {**BODY, "comision": 10}
    resultado = repository.calcular_totales(BODY["lineas"], cabecera)
    assert resultado["subtotalNeto"] == 200
    assert resultado["ivaCabecera"] == pytest.approx(43.05)
    assert resultado["importeTotal"] == pytest.approx(293.80)
    assert resultado["lineas"][0]["importeIva"] == 42
    sin_iibb = repository.calcular_totales(BODY["lineas"], {**cabecera, "ingresosBrutos": 0})
    assert resultado["importeTotal"] - sin_iibb["importeTotal"] == pytest.approx(13.25)


def test_percepcion_iva_se_pesifica_con_el_documento():
    resultado = repository.calcular_totales(
        BODY["lineas"], {**BODY, "moneda": "Dolares", "tipoDeCambio": 1200}
    )
    assert resultado["importeTotal"] == 282.75
    assert resultado["pesificado"] == {
        "subtotalNeto": 240000, "ivaCabecera": 50400, "importeTotal": 339300,
    }


def test_nota_credito_invierte_ambas_percepciones_una_sola_vez():
    original = {**deepcopy(BODY), "tipoDocumento": "Nota de Crédito"}
    cabecera, lineas = repository.normalizar_signo_nota_credito(original, original["lineas"])
    assert cabecera["ingresosBrutos"] == -13.25
    assert cabecera["percepcionIva"] == -27.50
    assert repository.calcular_totales(lineas, cabecera)["importeTotal"] == -282.75
    assert repository.normalizar_signo_nota_credito(cabecera, lineas) == (cabecera, lineas)
    assert original["percepcionIva"] == 27.50


@pytest.mark.parametrize("operacion", ["insert", "update"])
@pytest.mark.parametrize("valor", [27.50, None])
def test_sql_parametriza_percepcion_iva_independiente_de_iibb(operacion, valor):
    cabecera = {**BODY}
    if valor is None:
        cabecera.pop("percepcionIva")
    else:
        cabecera["percepcionIva"] = valor
    if operacion == "insert":
        sql, params = repository._cabecera_insert_statement(cabecera)([])
        campos = sql.split("(", 1)[1].split(")", 1)[0].split(",")
    else:
        sql, params = repository._cabecera_update_statement(123, cabecera)
        campos = re.split(r"\bSET\b", sql, flags=re.I)[1].split("WHERE")[0].split(",")
        campos = [campo.split("=")[0] for campo in campos]
        assert params[-1] == 123
    valores = dict(zip((campo.strip().strip("[]") for campo in campos), params))
    assert valores["PercepcionIVA"] == (valor or 0)
    assert valores["Ingresos Brutos"] == 13.25
    assert sql.count("?") == len(params)


@pytest.mark.anyio
async def test_post_put_get_conservan_percepciones_separadas(monkeypatch):
    almacen = {}

    def guardar(cabecera, lineas, vencimientos):
        almacen.update(idCompra=123, **cabecera)
        return 123

    monkeypatch.setattr(repository, "create_compra", guardar)
    monkeypatch.setattr(repository, "update_compra", lambda id_compra, *args: guardar(*args))
    monkeypatch.setattr(repository, "get_compra_cabecera", lambda _: almacen.copy())
    monkeypatch.setattr(repository, "get_lineas_compra", lambda _: [])
    monkeypatch.setattr(repository, "get_vencimientos_compra", lambda _: [])
    monkeypatch.setattr(repository, "buscar_documento_duplicado", lambda *args: None)
    monkeypatch.setattr(repository, "resolver_defaults_lineas", lambda lineas: lineas)
    monkeypatch.setattr(repository_locks, "verificar_lock", lambda *args: True)
    app = FastAPI()
    app.include_router(router)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        alta = await client.post("/api/compras", json=BODY)
        assert alta.status_code == 201
        assert alta.json()["percepcionIva"] == 27.50
        assert alta.json()["ingresosBrutos"] == 13.25
        assert alta.json()["importeTotal"] == 282.75
        assert almacen["percepcionIva"] == 27.50

        editada = await client.put("/api/compras/123", json={**BODY, "percepcionIva": 50},
                                   headers={"X-Lock-Token": "fixture"})
        assert editada.status_code == 200
        assert editada.json()["percepcionIva"] == 50
        assert editada.json()["importeTotal"] == 305.25
        detalle = await client.get("/api/compras/123")
        assert detalle.status_code == 200
        assert detalle.json()["percepcionIva"] == 50
        assert detalle.json()["ingresosBrutos"] == 13.25
