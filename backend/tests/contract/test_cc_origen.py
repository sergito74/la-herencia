"""Contract tests for the `origen` field in GET .../movimientos — 4 casos
(compra, tesoreria, fuera_de_alcance, no_disponible), per
contracts/cuentas-corrientes-api.md. Unit tests for origen_resolver.py
plus one end-to-end check through the router with a stubbed repository.
"""

from __future__ import annotations

import httpx
import pytest

from src.features.cuentas_corrientes import origen_resolver, repository
from src.main import app


def test_resolve_origen_compra(monkeypatch):
    monkeypatch.setattr(
        repository,
        "get_compra_referencia",
        lambda id_compra: {
            "idCompra": 12345,
            "numeroDocumento": "0001-00012345",
            "proveedor": "Rutas Sur Atlantico S.A.",
        },
    )
    result = origen_resolver.resolve_origen("Compras", 12345)
    assert result == {
        "tipo": "compra",
        "idCompra": 12345,
        "numeroDocumento": "0001-00012345",
        "proveedor": "Rutas Sur Atlantico S.A.",
    }


def test_resolve_origen_compra_no_encontrada(monkeypatch):
    monkeypatch.setattr(repository, "get_compra_referencia", lambda id_compra: None)
    result = origen_resolver.resolve_origen("Compras", 999)
    assert result == {"tipo": "no_disponible", "motivo": "registro de origen no encontrado"}


@pytest.mark.parametrize(
    ("origen_tipo", "medio", "lookup_name"),
    [
        ("Banco Nacion", "bna", "get_bna_referencia"),
        ("Galicia", "galicia", "get_galicia_referencia"),
        ("Pagos efectivo", "efectivo", "get_efectivo_referencia"),
        ("Cobros Valores Recibidos", "valores_recibidos", "get_valores_recibidos_referencia"),
        ("Pagos Valores Recibidos", "valores_recibidos", "get_valores_recibidos_referencia"),
    ],
)
def test_resolve_origen_tesoreria(monkeypatch, origen_tipo, medio, lookup_name):
    monkeypatch.setattr(
        repository,
        lookup_name,
        lambda id_mov: {"idMovimiento": id_mov, "fecha": "2026-08-12", "importe": 15000.0},
    )
    result = origen_resolver.resolve_origen(origen_tipo, 987)
    assert result == {
        "tipo": "tesoreria",
        "medio": medio,
        "idMovimiento": 987,
        "fecha": "2026-08-12",
        "importe": 15000.0,
    }


def test_resolve_origen_tesoreria_no_encontrado(monkeypatch):
    monkeypatch.setattr(repository, "get_bna_referencia", lambda id_mov: None)
    result = origen_resolver.resolve_origen("Banco Nacion", 999)
    assert result == {"tipo": "no_disponible", "motivo": "registro de origen no encontrado"}


@pytest.mark.parametrize(
    "origen_tipo",
    [
        "Alquileres",
        "Impuestos",
        "Remuneraciones",
        "Retenciones",
        "Ret. IVA Granos",
        "Ret. Ventas Hacienda",
    ],
)
def test_resolve_origen_fuera_de_alcance(origen_tipo):
    result = origen_resolver.resolve_origen(origen_tipo, 42)
    assert result == {"tipo": "fuera_de_alcance", "origenTipo": origen_tipo}


def test_resolve_origen_no_disponible_sin_id_origen():
    result = origen_resolver.resolve_origen("Compras", None)
    assert result == {"tipo": "no_disponible", "motivo": "IdOrigen sin cargar"}


def test_resolve_origen_tipo_no_relevado_es_fuera_de_alcance():
    result = origen_resolver.resolve_origen("Valores propios", 1)
    assert result == {"tipo": "fuera_de_alcance", "origenTipo": "Valores propios"}


@pytest.fixture
def client():
    return httpx.ASGITransport(app=app)


@pytest.mark.anyio
async def test_movimientos_endpoint_includes_resolved_origen(client, monkeypatch):
    def fake_movimientos(id_contacto, fecha_desde, fecha_hasta, page, page_size):
        return (
            [
                {
                    "fecha": "2026-08-05",
                    "documento": "Factura A",
                    "numeroDocumento": "0001-00012345",
                    "deuda": 60500.00,
                    "credito": 0,
                    "origenTipo": "Compras",
                    "idOrigen": 12345,
                },
                {
                    "fecha": "2026-08-15",
                    "documento": "Alquiler",
                    "numeroDocumento": "ALQ-0042",
                    "deuda": 0,
                    "credito": 85000.00,
                    "origenTipo": "Alquileres",
                    "idOrigen": 55,
                },
            ],
            2,
        )

    monkeypatch.setattr(repository, "get_movimientos", fake_movimientos)
    monkeypatch.setattr(
        repository,
        "get_compra_referencia",
        lambda id_compra: {
            "idCompra": 12345,
            "numeroDocumento": "0001-00012345",
            "proveedor": "Rutas Sur Atlantico S.A.",
        },
    )

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.get("/api/cuentas-corrientes/contactos/42/movimientos")

    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["origen"]["tipo"] == "compra"
    assert body["items"][0]["origen"]["idCompra"] == 12345
    assert body["items"][1]["origen"] == {
        "tipo": "fuera_de_alcance",
        "idCompra": None,
        "proveedor": None,
        "medio": None,
        "idMovimiento": None,
        "fecha": None,
        "importe": None,
        "numeroDocumento": None,
        "origenTipo": "Alquileres",
        "motivo": None,
    }


@pytest.fixture
def anyio_backend():
    return "asyncio"
