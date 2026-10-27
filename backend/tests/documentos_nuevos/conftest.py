"""Fixtures de 043: repositorio de documentos nuevos en memoria; cualquier conexión a `WC` falla."""

from __future__ import annotations

import os

os.environ.setdefault("LA_HERENCIA_SIN_PLANIFICADOR", "1")

import pytest
from fastapi.testclient import TestClient

from src.auth.tokens import crear_token
from src.db import connection
from src.features.auth.router import COOKIE_NAME
from src.features.documentos_nuevos import repository as repo
from src.main import app

PENDIENTES = ("cargado_solo", "para_cargar")


class RepoSimulado:
    def __init__(self, monkeypatch):
        self.docs: dict[int, dict] = {}
        self.marcas: dict[str, object] = {}
        self.corridas: list[dict] = []
        self.prog = {"horarios": "07:00,14:00", "proxima": None, "activa": True}

        def prohibido(*a, **k):
            raise AssertionError("Prueba 043 intentó conectarse a WC")
        monkeypatch.setattr(connection.pyodbc, "connect", prohibido)
        for nombre in ("existente", "adjunto_procesado", "mismo_comprobante", "registrar_documento", "resumen_pendientes",
                       "listar_pendientes", "obtener", "renglones_compras", "marcar_revisado", "cambiar_modulo",
                       "abrir_corrida", "cerrar_corrida", "ultima_corrida", "programacion", "fijar_proxima",
                       "marca_mails", "fijar_marca_mails", "portales_sincronizables"):
            monkeypatch.setattr(repo, nombre, getattr(self, nombre))

    def _pendiente(self, d):
        return d["estado"] in PENDIENTES and d.get("revisado") is None

    def existente(self, sha, modulo=None):
        for i, d in self.docs.items():
            if d["sha256"] == sha and (modulo is None or d["modulo"] == modulo):
                return {"id": i, "estado": d["estado"], "ruta": d["ruta"]}
        return None

    def mismo_comprobante(self, id_contacto, numero, modulo):
        return any(d.get("idContacto") == id_contacto and d.get("numero") == numero and d["modulo"] == modulo
                   for d in self.docs.values())

    def adjunto_procesado(self, entry_id, sha):
        return any(d.get("mailEntryId") == entry_id and d["sha256"] == sha for d in self.docs.values())

    def registrar_documento(self, d):
        previo = self.existente(d["sha256"], d["modulo"])
        if previo:
            return previo["id"], False
        i = len(self.docs) + 1
        self.docs[i] = {**d, "revisado": None}
        return i, True

    def resumen_pendientes(self):
        n: dict[str, int] = {}
        for d in self.docs.values():
            if self._pendiente(d):
                n[d["modulo"]] = n.get(d["modulo"], 0) + 1
        return n

    def _fila(self, i):
        d = self.docs[i]
        return {"idDocumentoNuevo": i, "origen": d["origen"], "portal": "Allianz" if d["origen"] == "portal" else None,
                "mailRemitente": d.get("mailRemitente"), "mailAsunto": d.get("mailAsunto"),
                "mailRecibido": d.get("mailRecibido"), "creado": "2026-10-27 14:03:00", "tipo": d["tipo"],
                "modulo": d["modulo"], "estado": d["estado"], "motivo": d.get("motivo"),
                "idContacto": d.get("idContacto"), "contacto": "Allianz" if d.get("idContacto") else None,
                "fecha": d.get("fecha"), "numero": d.get("numero"), "total": d.get("total"), "ruta": d["ruta"],
                "idRegistro": d.get("idRegistro")}

    def listar_pendientes(self, modulo, limite=50, desde=0):
        ids = [i for i, d in sorted(self.docs.items()) if d["modulo"] == modulo and self._pendiente(d)]
        return [self._fila(i) for i in ids[desde:desde + limite]], len(ids)

    def obtener(self, i):
        return self._fila(i) if i in self.docs else None

    def renglones_compras(self, ids):
        return [{"idCompra": i, "detalle": "Prima", "cantidad": 1, "precioUnitario": 124693.56, "iva": 21.0,
                 "rubro": "Seguros Generales", "centroCosto": "Adm. General"} for i in ids]

    def marcar_revisado(self, i, usuario):
        d = self.docs.get(i)
        if not d or not self._pendiente(d):
            return 0
        d["revisado"], d["revisadoPor"] = "ahora", usuario
        return 1

    def cambiar_modulo(self, i, modulo, usuario):
        d = self.docs.get(i)
        if not d or not self._pendiente(d) or d["modulo"] == modulo or self.existente(d["sha256"], modulo):
            return 0
        d["moduloAnterior"], d["modulo"], d["moduloCambiadoPor"] = d["modulo"], modulo, usuario
        return 1

    def abrir_corrida(self, origen="programada"):
        if any(c["estado"] == "en_curso" for c in self.corridas):
            return None
        self.corridas.append({"estado": "en_curso", "origen": origen})
        return len(self.corridas)

    def cerrar_corrida(self, i, estado, r, mensaje):
        self.corridas[i - 1].update(estado=estado, mensaje=mensaje, **r)

    def ultima_corrida(self):
        return self.corridas[-1] if self.corridas else None

    def programacion(self):
        return dict(self.prog)

    def fijar_proxima(self, p):
        self.prog["proxima"] = p

    def marca_mails(self, almacen):
        return self.marcas.get(almacen)

    def fijar_marca_mails(self, almacen, ultimo):
        self.marcas[almacen] = ultimo

    def portales_sincronizables(self):
        return []


@pytest.fixture
def repo_sim(monkeypatch):
    return RepoSimulado(monkeypatch)


@pytest.fixture
def client():
    c = TestClient(app)
    yield c
    c.cookies.clear()


def iniciar_sesion(client: TestClient, rol: str) -> None:
    client.cookies.set(COOKIE_NAME, crear_token(id_usuario=1, rol=rol))
