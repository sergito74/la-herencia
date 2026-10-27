"""Solo el Administrador accede a /api/boveda (042, T010)."""

from __future__ import annotations

import pytest

from src.features.boveda.router import router

from .conftest import iniciar_sesion

RUTAS = sorted(
    {(m, r.path) for r in router.routes for m in r.methods}
)


def _url(path: str) -> str:
    return path.replace("{id_portal}", "1").replace("{id_credencial}", "1").replace("{id_corrida}", "1").replace(
        "{id_foto}", "1")


def test_hay_rutas():
    assert len(RUTAS) >= 10


@pytest.mark.parametrize("rol", ["Lectura", "Operador", "Contador", ""])
def test_otros_roles_reciben_403(client, rol):
    iniciar_sesion(client, rol)
    for metodo, path in RUTAS:
        resp = client.request(metodo, _url(path), json={})
        assert resp.status_code == 403, f"{metodo} {path} con rol {rol!r} devolvió {resp.status_code}"
        assert "contrase" not in resp.text.lower()


def test_sin_sesion_401(client):
    for metodo, path in RUTAS:
        assert client.request(metodo, _url(path), json={}).status_code == 401
