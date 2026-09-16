"""Contract tests for the `origen` field in GET .../movimientos — 9 casos
(compra, tesoreria, impuesto, retencion, remuneracion, arrendamiento,
venta_hacienda, fuera_de_alcance, no_disponible), per
contracts/cuentas-corrientes-api.md and
contracts/egresos-y-ventas-menores-api.md. Unit tests for
origen_resolver.py plus one end-to-end check through the router with a
stubbed repository.
"""

from __future__ import annotations

import httpx
import pytest

from src.features.arrendamientos import repository as arrendamientos_repository
from src.features.cuentas_corrientes import origen_resolver, repository
from src.features.impuestos import repository as impuestos_repository
from src.features.remuneraciones import repository as remuneraciones_repository
from src.features.ventas_hacienda import repository as ventas_hacienda_repository
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


# --- specs/005-egresos-y-ventas-menores: 5 nuevos tipos de origen ---


def test_resolve_origen_impuesto(monkeypatch):
    monkeypatch.setattr(
        impuestos_repository,
        "get_impuesto_referencia",
        lambda id_impuesto: {
            "idImpuesto": 14,
            "tipoImpuesto": "Ingresos Brutos",
            "importe": 1500.0,
        },
    )
    result = origen_resolver.resolve_origen("Impuestos", 14)
    assert result == {
        "tipo": "impuesto",
        "idImpuesto": 14,
        "tipoImpuesto": "Ingresos Brutos",
        "importe": 1500.0,
    }


def test_resolve_origen_impuesto_no_encontrado(monkeypatch):
    monkeypatch.setattr(impuestos_repository, "get_impuesto_referencia", lambda id_impuesto: None)
    result = origen_resolver.resolve_origen("Impuestos", 999)
    assert result == {"tipo": "no_disponible", "motivo": "registro de origen no encontrado"}


def test_resolve_origen_retencion(monkeypatch):
    monkeypatch.setattr(
        impuestos_repository,
        "get_retencion_referencia",
        lambda id_retencion: {
            "idRetencion": 1,
            "numeroCertificado": "0000-2017-000001",
            "importe": 435.94,
        },
    )
    result = origen_resolver.resolve_origen("Retenciones", 1)
    assert result == {
        "tipo": "retencion",
        "idRetencion": 1,
        "numeroCertificado": "0000-2017-000001",
        "importe": 435.94,
    }


def test_resolve_origen_remuneracion(monkeypatch):
    monkeypatch.setattr(
        remuneraciones_repository,
        "get_remuneracion_referencia",
        lambda id_salario: {
            "idSalario": 1829633151,
            "periodoLiquidado": "Mayo 2024",
            "empleado": "Juan Pérez",
        },
    )
    result = origen_resolver.resolve_origen("Remuneraciones", 1829633151)
    assert result == {
        "tipo": "remuneracion",
        "idSalario": 1829633151,
        "periodoLiquidado": "Mayo 2024",
        "empleado": "Juan Pérez",
    }


def test_resolve_origen_arrendamiento(monkeypatch):
    monkeypatch.setattr(
        arrendamientos_repository,
        "get_arrendamiento_referencia",
        lambda id_alquiler: {
            "idAlquiler": 138210671,
            "contacto": "Estancia El Rincón",
            "importeTotalContrato": 500000.0,
        },
    )
    result = origen_resolver.resolve_origen("Alquileres", 138210671)
    assert result == {
        "tipo": "arrendamiento",
        "idAlquiler": 138210671,
        "contacto": "Estancia El Rincón",
        "importeTotalContrato": 500000.0,
    }


def test_resolve_origen_venta_hacienda(monkeypatch):
    """Referencia a la retención de venta de hacienda, no a la venta en sí."""
    monkeypatch.setattr(
        ventas_hacienda_repository,
        "get_retencion_venta_hacienda_referencia",
        lambda id_retencion: {
            "idRetencion": 1,
            "numeroDocumento": "2023-OP-1760",
            "importe": 555520.0,
        },
    )
    result = origen_resolver.resolve_origen("Ret. Ventas Hacienda", 1)
    assert result == {
        "tipo": "venta_hacienda",
        "idRetencion": 1,
        "numeroDocumento": "2023-OP-1760",
        "importe": 555520.0,
    }


@pytest.mark.parametrize(
    ("origen_tipo", "module", "lookup_name"),
    [
        ("Impuestos", impuestos_repository, "get_impuesto_referencia"),
        ("Retenciones", impuestos_repository, "get_retencion_referencia"),
        ("Remuneraciones", remuneraciones_repository, "get_remuneracion_referencia"),
        ("Alquileres", arrendamientos_repository, "get_arrendamiento_referencia"),
        (
            "Ret. Ventas Hacienda",
            ventas_hacienda_repository,
            "get_retencion_venta_hacienda_referencia",
        ),
    ],
)
def test_resolve_origen_nuevos_tipos_no_encontrado(monkeypatch, origen_tipo, module, lookup_name):
    monkeypatch.setattr(module, lookup_name, lambda id_origen: None)
    result = origen_resolver.resolve_origen(origen_tipo, 999)
    assert result == {"tipo": "no_disponible", "motivo": "registro de origen no encontrado"}


@pytest.mark.parametrize(
    "origen_tipo",
    ["Ret. IVA Granos"],
)
def test_resolve_origen_fuera_de_alcance(origen_tipo):
    """Único valor de `Origen` que sigue fuera de alcance (dominio de Agricultura)."""
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
                {
                    "fecha": "2026-08-20",
                    "documento": "Retencion IVA Granos",
                    "numeroDocumento": None,
                    "deuda": 0,
                    "credito": 1000.00,
                    "origenTipo": "Ret. IVA Granos",
                    "idOrigen": 7,
                },
            ],
            3,
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
    monkeypatch.setattr(
        arrendamientos_repository,
        "get_arrendamiento_referencia",
        lambda id_alquiler: {
            "idAlquiler": 55,
            "contacto": "Estancia El Rincón",
            "importeTotalContrato": 500000.0,
        },
    )

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.get("/api/cuentas-corrientes/contactos/42/movimientos")

    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["origen"]["tipo"] == "compra"
    assert body["items"][0]["origen"]["idCompra"] == 12345
    assert body["items"][1]["origen"]["tipo"] == "arrendamiento"
    assert body["items"][1]["origen"]["idAlquiler"] == 55
    assert body["items"][2]["origen"]["tipo"] == "fuera_de_alcance"
    assert body["items"][2]["origen"]["origenTipo"] == "Ret. IVA Granos"


@pytest.fixture
def anyio_backend():
    return "asyncio"
