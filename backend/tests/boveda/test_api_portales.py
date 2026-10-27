"""Contrato de portales y credenciales (042, T013) con repositorio simulado: no toca `WC`."""

from __future__ import annotations

import pytest

from src.features.boveda import cifrado, repository, router

from .conftest import iniciar_sesion

CLAVE = "Clave-Muy-Secreta-123"
PIN = "4321-pin"


class RepoFalso:
    def __init__(self):
        self.credenciales: dict[int, dict] = {}
        self.portales: dict[int, dict] = {}
        self.auditoria: list[tuple] = []

    # credenciales
    def crear_credencial(self, nombre, titular, id_socio, usuario, clave, datos):
        idc = len(self.credenciales) + 1
        self.credenciales[idc] = {
            "idCredencial": idc, "nombre": nombre, "titular": titular, "idSocio": id_socio, "usuario": usuario,
            "blob": cifrado.cifrar(clave, cifrado.aad_clave(idc)) if clave else None, "rechazada": False,
            "datos": [{"nombre": d["nombre"], "secreto": d["secreto"],
                       "valorTexto": None if d["secreto"] else d["valor"],
                       "valorCifrado": cifrado.cifrar(d["valor"], cifrado.aad_dato(idc, d["nombre"])) if d["secreto"] else None}
                      for d in datos],
        }
        return idc

    def obtener_credencial(self, idc):
        c = self.credenciales.get(idc)
        return c and {k: c[k] for k in ("idCredencial", "nombre", "usuario", "rechazada")}

    def listar_credenciales(self):
        return [{"idCredencial": c["idCredencial"], "nombre": c["nombre"], "titular": c["titular"], "idSocio": c["idSocio"],
                 "usuario": c["usuario"], "claveConfigurada": c["blob"] is not None, "rechazada": c["rechazada"],
                 "datos": [{"nombre": d["nombre"], "secreto": d["secreto"], "valor": d["valorTexto"]} for d in c["datos"]],
                 "portales": [p["idPortal"] for p in self.portales.values() if p["idCredencial"] == c["idCredencial"]]}
                for c in self.credenciales.values()]

    def leer_clave_cifrada(self, idc):
        return self.credenciales[idc]["blob"]

    def leer_datos(self, idc):
        return self.credenciales[idc]["datos"]

    def cambiar_clave(self, idc, clave):
        if idc not in self.credenciales:
            return 0
        self.credenciales[idc]["blob"] = cifrado.cifrar(clave, cifrado.aad_clave(idc))
        return 1

    # portales
    def existe_nombre_portal(self, nombre, excepto=None):
        return any(p["nombre"] == nombre and p["idPortal"] != excepto for p in self.portales.values())

    def existe_contacto(self, idc):
        return True

    def crear_portal(self, nombre, url, tipo, id_contacto, id_credencial, codigo, notas):
        idp = len(self.portales) + 1
        self.portales[idp] = {"idPortal": idp, "nombre": nombre, "url": url, "tipo": tipo, "idContacto": id_contacto,
                              "idCredencial": id_credencial, "codigoConector": codigo, "notas": notas}
        return idp

    def _fila(self, p):
        c = self.credenciales.get(p["idCredencial"]) or {}
        return {**p, "contacto": None, "credencialNombre": c.get("nombre"), "credencialUsuario": c.get("usuario"),
                "claveConfigurada": c.get("blob") is not None, "credencialRechazada": c.get("rechazada", False),
                "autFecha": None, "autPor": None, "autFuente": None, "frecuencia": None, "diaSemana": None,
                "diaMes": None, "hora": None, "proximaCorrida": None, "suspendida": False, "motivoSuspension": None,
                "ucId": None, "ucInicio": None, "ucEstado": None, "ucNuevos": None, "ufFechaCorte": None,
                "ufMoneda": None, "ufSaldoPortal": None, "ufSaldoSistema": None, "ufDiferencia": None}

    def listar_portales(self):
        return [self._fila(p) for p in self.portales.values()]

    def obtener_portal(self, idp):
        p = self.portales.get(idp)
        return self._fila(p) if p else None

    def auditar(self, accion, usuario, **kw):
        self.auditoria.append((accion, kw))


@pytest.fixture
def repo(monkeypatch, keyring_falso):
    falso = RepoFalso()
    for nombre in dir(falso):
        if not nombre.startswith("_") and hasattr(repository, nombre):
            monkeypatch.setattr(repository, nombre, getattr(falso, nombre))
    monkeypatch.setattr(router, "usuario_actual", lambda request: "sergio")
    return falso


def _alta(client):
    return client.post("/api/boveda/portales", json={
        "nombre": "Portal X", "url": "https://x.example", "tipo": "proveedor",
        "credencialNueva": {"nombre": "Cred X", "usuario": "giamigli", "clave": CLAVE,
                            "datos": [{"nombre": "PIN", "secreto": True, "valor": PIN},
                                      {"nombre": "CUIT", "secreto": False, "valor": "30-1"}]},
    })


def test_alta_y_listado_sin_secretos(client, repo):
    iniciar_sesion(client, "Administrador")
    resp = _alta(client)
    assert resp.status_code == 201
    textos = [resp.text]
    for path in ("/api/boveda/portales", "/api/boveda/portales/1", "/api/boveda/credenciales", "/api/boveda/conectores"):
        r = client.get(path)
        assert r.status_code == 200, path
        textos.append(r.text)
    for t in textos:
        assert CLAVE not in t and PIN not in t
    portal = client.get("/api/boveda/portales").json()["items"][0]
    assert portal["credencial"]["estado"] == "ok"
    assert portal["conector"]["disponible"] is False  # solo bóveda
    cred = client.get("/api/boveda/credenciales").json()[0]
    assert {"nombre": "PIN", "secreto": True, "valor": None} in cred["datos"]
    assert {"nombre": "CUIT", "secreto": False, "valor": "30-1"} in cred["datos"]


def test_revelar_devuelve_y_audita(client, repo):
    iniciar_sesion(client, "Administrador")
    _alta(client)
    r = client.post("/api/boveda/credenciales/1/revelar", json={"campo": "clave"})
    assert r.status_code == 200 and r.json() == {"valor": CLAVE}
    assert r.headers["cache-control"] == "no-store"
    assert client.post("/api/boveda/credenciales/1/revelar", json={"campo": "dato:PIN"}).json() == {"valor": PIN}
    assert client.post("/api/boveda/credenciales/1/revelar", json={"campo": "dato:CUIT"}).status_code == 404
    assert [a for a, _ in repo.auditoria].count("revelar") == 2


def test_cambiar_clave(client, repo):
    iniciar_sesion(client, "Administrador")
    _alta(client)
    assert client.put("/api/boveda/credenciales/1/clave", json={"clave": "otra"}).status_code == 204
    assert client.post("/api/boveda/credenciales/1/revelar", json={"campo": "clave"}).json() == {"valor": "otra"}
    assert client.put("/api/boveda/credenciales/9/clave", json={"clave": "x"}).status_code == 404


@pytest.mark.parametrize("cambio,detalle", [
    ({"url": "ftp://x"}, None),
    ({"codigoConector": "inexistente"}, "Conector desconocido"),
])
def test_validaciones(client, repo, cambio, detalle):
    iniciar_sesion(client, "Administrador")
    body = {"nombre": "P", "url": "https://p.example", "tipo": "otro", **cambio}
    r = client.post("/api/boveda/portales", json=body)
    assert r.status_code in (400, 422)
    if detalle:
        assert r.json()["detail"] == detalle


def test_nombre_repetido(client, repo):
    iniciar_sesion(client, "Administrador")
    _alta(client)
    r = client.post("/api/boveda/portales", json={"nombre": "Portal X", "url": "https://y.example", "tipo": "otro"})
    assert r.status_code == 400
