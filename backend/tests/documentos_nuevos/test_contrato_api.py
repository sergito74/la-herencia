"""Contrato de /api/documentos-nuevos (043, T007) con datos simulados."""

from __future__ import annotations

import pytest

from src.features.boveda import router as boveda_router

from .conftest import iniciar_sesion


def _doc(repo, **k):
    base = {"origen": "portal", "sha256": "a" * 64, "ruta": r"C:\x\20261013_Allianz.pdf", "tipo": "factura",
            "modulo": "compras", "estado": "cargado_solo", "idContacto": 515, "idRegistro": 2143524139,
            "numero": "260040606375 10", "fecha": "2026-10-13", "total": 0}
    return repo.registrar_documento({**base, **k})[0]


@pytest.fixture(autouse=True)
def _usuario(monkeypatch):
    monkeypatch.setattr(boveda_router, "get_usuario_por_id", lambda i: {"NombreUsuario": "sergio"})


def test_resumen_por_modulo(client, repo_sim):
    _doc(repo_sim)
    _doc(repo_sim, sha256="b" * 64, modulo="sin_clasificar", estado="para_cargar")
    _doc(repo_sim, sha256="c" * 64, estado="ya_estaba")
    iniciar_sesion(client, "Lectura")
    r = client.get("/api/documentos-nuevos/resumen").json()
    assert r == {"compras": 1, "impuestos": 0, "ventas": 0, "tesoreria": 0, "cuentasCorrientes": 0, "pagos": 0,
                 "sinClasificar": 1, "total": 2}


def test_lista_con_renglones_y_enlace(client, repo_sim):
    _doc(repo_sim)
    iniciar_sesion(client, "Lectura")
    r = client.get("/api/documentos-nuevos/", params={"modulo": "compras"}).json()
    assert r["total"] == 1
    item = r["items"][0]
    assert item["origen"] == "Portal Allianz"
    assert item["tipo"] == "Factura"
    assert item["enlace"] == "/compras/2143524139/editar"
    assert item["archivo"] == "20261013_Allianz.pdf"
    assert item["renglones"][0]["rubro"] == "Seguros Generales"


def test_modulo_invalido(client, repo_sim):
    iniciar_sesion(client, "Administrador")
    assert client.get("/api/documentos-nuevos/", params={"modulo": "x"}).status_code == 400


def test_revisado_baja_el_numero(client, repo_sim):
    i = _doc(repo_sim)
    iniciar_sesion(client, "Administrador")
    assert client.post(f"/api/documentos-nuevos/{i}/revisado").json() == {"ok": True}
    assert client.get("/api/documentos-nuevos/resumen").json()["compras"] == 0
    assert repo_sim.docs[i]["revisadoPor"] == "sergio"
    assert client.post(f"/api/documentos-nuevos/{i}/revisado").status_code == 404


def test_mover_sin_clasificar_queda_auditado(client, repo_sim):
    i = _doc(repo_sim, modulo="sin_clasificar", estado="para_cargar")
    iniciar_sesion(client, "Administrador")
    r = client.post(f"/api/documentos-nuevos/{i}/modulo", json={"modulo": "impuestos"})
    assert r.status_code == 200 and r.json()["modulo"] == "impuestos"
    assert repo_sim.docs[i]["moduloAnterior"] == "sin_clasificar"
    assert repo_sim.docs[i]["moduloCambiadoPor"] == "sergio"


@pytest.mark.parametrize("rol", ["Lectura", "Operador", "Contador"])
def test_escritura_solo_administrador(client, repo_sim, rol):
    i = _doc(repo_sim)
    iniciar_sesion(client, rol)
    assert client.post(f"/api/documentos-nuevos/{i}/revisado").status_code == 403
    assert client.post(f"/api/documentos-nuevos/{i}/modulo", json={"modulo": "ventas"}).status_code == 403
    assert client.get("/api/documentos-nuevos/rutina").status_code == 403


def test_sin_sesion_401(client, repo_sim):
    assert client.get("/api/documentos-nuevos/resumen").status_code == 401
