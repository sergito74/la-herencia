"""Contract tests for /api/contactos (list/detail/create/update)."""

from __future__ import annotations

import httpx
import pytest

from src.features.contactos import repository
from src.main import app

FIXTURE_CONTACTO = {
    "idContacto": 461,
    "razonSocial": "Acopio Central S.A.",
    "tipoContacto": "Proveedor",
    "cuit": "30123456789",
    "esContratistaLabores": False,
}


@pytest.fixture
def client():
    return httpx.ASGITransport(app=app)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_list_contactos_by_query(client, monkeypatch):
    def fake_search(q, tipo_contacto, page, page_size):
        assert q == "Acopio"
        assert tipo_contacto == ["Proveedor"]
        return [FIXTURE_CONTACTO], 1

    monkeypatch.setattr(repository, "search_contactos", fake_search)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.get("/api/contactos?q=Acopio&tipoContacto=Proveedor")

    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["razonSocial"] == "Acopio Central S.A."


@pytest.mark.anyio
async def test_list_contactos_by_multiple_tipos(client, monkeypatch):
    """`tipoContacto` repetible (006) — ej. selector de proveedor de Compras
    acepta varios tipos válidos, no solo uno."""
    captured = {}

    def fake_search(q, tipo_contacto, page, page_size):
        captured["tipo_contacto"] = tipo_contacto
        return [], 0

    monkeypatch.setattr(repository, "search_contactos", fake_search)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.get(
            "/api/contactos?tipoContacto=Proveedor&tipoContacto=Multiple&tipoContacto=Banco"
        )

    assert response.status_code == 200
    assert captured["tipo_contacto"] == ["Proveedor", "Multiple", "Banco"]


@pytest.mark.anyio
async def test_get_contacto_by_id(client, monkeypatch):
    monkeypatch.setattr(repository, "get_contacto", lambda id_contacto: FIXTURE_CONTACTO)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.get("/api/contactos/461")

    assert response.status_code == 200
    assert response.json()["idContacto"] == 461


@pytest.mark.anyio
async def test_get_contacto_not_found(client, monkeypatch):
    monkeypatch.setattr(repository, "get_contacto", lambda id_contacto: None)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.get("/api/contactos/999999")

    assert response.status_code == 404


@pytest.mark.anyio
async def test_create_contacto(client, monkeypatch):
    captured = {}

    def fake_create(razon_social, tipo_contacto, cuit, es_contratista_labores):
        captured["args"] = (razon_social, tipo_contacto, cuit, es_contratista_labores)
        return 9999

    monkeypatch.setattr(repository, "create_contacto", fake_create)
    monkeypatch.setattr(
        repository, "get_contacto", lambda id_contacto: {**FIXTURE_CONTACTO, "idContacto": 9999}
    )

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.post(
            "/api/contactos",
            json={
                "razonSocial": "Nuevo Proveedor S.A.",
                "tipoContacto": "Proveedor",
                "cuit": "30987654321",
                "esContratistaLabores": False,
            },
        )

    assert response.status_code == 201
    assert response.json()["idContacto"] == 9999
    assert captured["args"] == (
        "Nuevo Proveedor S.A.",
        "Proveedor",
        "30987654321",
        False,
    )


@pytest.mark.anyio
async def test_create_contacto_rechaza_tipo_invalido(client):
    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.post(
            "/api/contactos",
            json={"razonSocial": "X", "tipoContacto": "NoExiste"},
        )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_update_contacto(client, monkeypatch):
    monkeypatch.setattr(repository, "update_contacto", lambda *args: True)
    monkeypatch.setattr(repository, "get_contacto", lambda id_contacto: FIXTURE_CONTACTO)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.patch(
            "/api/contactos/461",
            json={
                "razonSocial": "Acopio Central S.A.",
                "tipoContacto": "Proveedor",
                "cuit": "30123456789",
                "esContratistaLabores": False,
            },
        )

    assert response.status_code == 200


@pytest.mark.anyio
async def test_update_contacto_no_encontrado(client, monkeypatch):
    monkeypatch.setattr(repository, "update_contacto", lambda *args: False)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.patch(
            "/api/contactos/999999",
            json={
                "razonSocial": "X",
                "tipoContacto": "Proveedor",
                "cuit": None,
                "esContratistaLabores": False,
            },
        )

    assert response.status_code == 404


@pytest.mark.anyio
async def test_contactos_rejects_delete(client):
    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.delete("/api/contactos/461")

    assert response.status_code in (404, 405)
