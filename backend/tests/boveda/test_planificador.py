"""Planificador y corridas de la bóveda (042, T024), con repositorio y conectores simulados."""

from __future__ import annotations

import os
from datetime import date, datetime, time
from decimal import Decimal

import pytest

from src.features.boveda import planificador, repository, servicio
from src.features.boveda.conectores import (
    CredencialesRechazadas, Credencial, DocumentoPortal, RequiereIntervencion,
)
from src.features.boveda.cifrado import Secreto

H7 = time(7, 0)


@pytest.mark.parametrize("frecuencia,dia_s,dia_m,desde,esperado", [
    ("diaria", None, None, datetime(2026, 10, 27, 6, 0), datetime(2026, 10, 27, 7, 0)),
    ("diaria", None, None, datetime(2026, 10, 27, 7, 0), datetime(2026, 10, 28, 7, 0)),
    ("semanal", 1, None, datetime(2026, 10, 27, 9, 0), datetime(2026, 11, 2, 7, 0)),   # martes → lunes siguiente
    ("semanal", 2, None, datetime(2026, 10, 27, 6, 0), datetime(2026, 10, 27, 7, 0)),  # martes antes de hora
    ("semanal", 2, None, datetime(2026, 10, 27, 8, 0), datetime(2026, 11, 3, 7, 0)),
    ("mensual", 28, None, datetime(2026, 10, 27, 8, 0), None),
    ("mensual", None, 28, datetime(2026, 10, 27, 8, 0), datetime(2026, 10, 28, 7, 0)),
    ("mensual", None, 1, datetime(2026, 12, 15, 8, 0), datetime(2027, 1, 1, 7, 0)),
    ("mensual", None, 28, datetime(2026, 2, 28, 7, 0), datetime(2026, 3, 28, 7, 0)),
    ("desactivada", None, None, datetime(2026, 10, 27), None),
])
def test_proxima_corrida(frecuencia, dia_s, dia_m, desde, esperado):
    if frecuencia == "mensual" and dia_m is None:
        with pytest.raises(ValueError):
            planificador.proxima_corrida(frecuencia, dia_s, dia_m, H7, desde)
        return
    assert planificador.proxima_corrida(frecuencia, dia_s, dia_m, H7, desde) == esperado


def test_tick_recupera_una_sola_vez(monkeypatch):
    vencidos = [{"idPortal": 1, "codigoConector": "x"}]
    corridas, proximas = [], []
    monkeypatch.setattr(repository, "portales_vencidos", lambda ahora: list(vencidos))
    monkeypatch.setattr(servicio, "correr_portal",
                        lambda idp, origen, usuario: (corridas.append((idp, origen)), (1, "ok"))[1])
    monkeypatch.setattr(repository, "obtener_programacion", lambda idp: {
        "frecuencia": "diaria", "diaSemana": None, "diaMes": None, "hora": H7})
    monkeypatch.setattr(repository, "fijar_proxima", lambda idp, prox: (proximas.append(prox), vencidos.clear()))
    # La app estuvo cerrada varios días: corre una vez y reprograma desde ahora.
    assert planificador.tick(datetime(2026, 10, 30, 9, 0)) == [1]
    assert planificador.tick(datetime(2026, 10, 30, 9, 1)) == []
    assert corridas == [(1, "programada")]
    assert len(proximas) == 1 and proximas[0] > datetime.now()


# --- Corrida de un portal -------------------------------------------------------

class ConectorFalso:
    codigo = "falso"
    nombre = "Falso"
    tiene_estado_cuenta = False
    tiene_carga_compras = False
    mapeo_proveedores: dict = {}

    def __init__(self, error=None, docs=None):
        self.error, self.docs = error, docs or []

    def ingresar(self, pw, credencial):
        assert credencial.clave.valor() == "clave"
        if self.error:
            raise self.error
        return object()

    def listar_documentos(self, sesion):
        return self.docs

    def estado_cuenta(self, sesion):
        return []

    def leer_comprobante(self, doc, pdf):
        return None

    def cerrar(self, sesion):
        pass


@pytest.fixture
def entorno(monkeypatch, tmp_path):
    estado = {"autorizado": True, "cerrada": None, "suspendido": None, "rechazada": False, "docs": []}
    monkeypatch.setattr(repository, "portal_para_correr", lambda idp: {
        "idPortal": idp, "nombre": "P", "idContacto": None, "idCredencial": 5, "codigoConector": "falso"})
    monkeypatch.setattr(repository, "autorizacion_vigente", lambda idp: {"fecha": date(2026, 10, 27)} if estado["autorizado"] else None)
    monkeypatch.setattr(repository, "cerrar_corrida", lambda idc, est, **kw: estado.update(cerrada=(est, kw)))
    monkeypatch.setattr(repository, "auditar", lambda *a, **k: None)
    monkeypatch.setattr(repository, "suspender", lambda idp, motivo: estado.update(suspendido=motivo))
    monkeypatch.setattr(repository, "marcar_rechazada", lambda idc: estado.update(rechazada=True))
    monkeypatch.setattr(repository, "existe_documento", lambda idp, clave: False)
    monkeypatch.setattr(repository, "existe_equivalente", lambda patrones: False)
    monkeypatch.setattr(repository, "existe_sha", lambda sha: None)
    monkeypatch.setattr(repository, "insertar_documento", lambda d: estado["docs"].append(d) or 1)
    # Sin esto los avisos (043) se escribían en la base real.
    monkeypatch.setattr(servicio.avisos, "desde_portal", lambda *a, **k: None)
    monkeypatch.setattr(servicio, "credencial_de", lambda idc: Credencial(usuario="u", clave=Secreto("clave")))
    monkeypatch.setattr(servicio, "COMPRAS", tmp_path)
    monkeypatch.setattr(servicio, "_carpeta", lambda tipo, f: tmp_path)
    monkeypatch.setattr(servicio, "_soltar_lock", lambda lock, id_portal=None: None)

    class PwFalso:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    import playwright.sync_api
    monkeypatch.setattr(playwright.sync_api, "sync_playwright", lambda: PwFalso())
    return estado


def _usar(monkeypatch, conector):
    from src.features.boveda import conectores
    monkeypatch.setitem(conectores.CONECTORES, "falso", conector)
    monkeypatch.setattr(servicio, "cargar_conectores", lambda: conectores.CONECTORES)


def test_sin_autorizacion_no_entra(monkeypatch, entorno):
    _usar(monkeypatch, ConectorFalso(error=AssertionError("no debería ingresar")))
    entorno["autorizado"] = False
    assert servicio.ejecutar(1, "manual", "s", None, 10) == "sin_autorizacion"


def test_credenciales_rechazadas_suspende(monkeypatch, entorno):
    _usar(monkeypatch, ConectorFalso(error=CredencialesRechazadas()))
    assert servicio.ejecutar(1, "programada", "sistema", None, 10) == "credenciales_rechazadas"
    assert entorno["rechazada"] and entorno["suspendido"]


def test_requiere_intervencion(monkeypatch, entorno):
    _usar(monkeypatch, ConectorFalso(error=RequiereIntervencion("captcha")))
    assert servicio.ejecutar(1, "manual", "s", None, 10) == "requiere_intervencion"
    assert entorno["suspendido"] is None


def test_documentos_guardados_y_no_comprobante_no_aplica(monkeypatch, entorno, tmp_path):
    docs = [DocumentoPortal(clave="c1", fecha=date(2026, 10, 1), tipo="resumen", proveedor="Prov",
                            bajar=lambda: b"%PDF-1.4 x", total=Decimal("10")),
            DocumentoPortal(clave="c2", fecha=date(2026, 10, 2), tipo="factura", proveedor="Prov",
                            bajar=lambda: b"<html>no</html>")]
    _usar(monkeypatch, ConectorFalso(docs=docs))
    assert servicio.ejecutar(1, "manual", "s", None, 10) == "error"  # el 2º no es PDF
    assert [d["clave"] for d in entorno["docs"]] == ["c1"]
    assert entorno["docs"][0]["estadoCarga"] == "no_aplica"
    assert (tmp_path / "20261001_Prov.pdf").read_bytes().startswith(b"%PDF")
    est, kw = entorno["cerrada"]
    assert kw["nuevos"] == 1 and "no devolvió un PDF" in kw["mensaje"]


def test_revocacion_durante_la_corrida_detiene(monkeypatch, entorno):
    def bajar():
        entorno["autorizado"] = False
        return b"%PDF-1.4"
    docs = [DocumentoPortal(clave=f"c{i}", fecha=date(2026, 10, 1), tipo="resumen", proveedor="P", bajar=bajar)
            for i in range(3)]
    _usar(monkeypatch, ConectorFalso(docs=docs))
    assert servicio.ejecutar(1, "manual", "s", None, 10) == "sin_autorizacion"
    assert len(entorno["docs"]) == 1


def test_salteada_no_reprograma(monkeypatch):
    proximas = []
    monkeypatch.setattr(repository, "portales_vencidos", lambda ahora: [{"idPortal": 1, "codigoConector": "x"}])
    monkeypatch.setattr(servicio, "correr_portal", lambda idp, origen, usuario: (2, "salteada"))
    monkeypatch.setattr(repository, "fijar_proxima", lambda idp, prox: proximas.append(prox))
    monkeypatch.setattr(repository, "obtener_programacion", lambda idp: {
        "frecuencia": "diaria", "diaSemana": None, "diaMes": None, "hora": H7})
    planificador.tick(datetime(2026, 10, 30, 9, 0))
    assert proximas == []


def test_mensajes_sin_credenciales():
    cred = Credencial(usuario="usuario-x", clave=Secreto("Clave-Secreta"), datos={"PIN": Secreto("4321")})
    texto = "Timeout llenando Clave-Secreta para usuario-x con PIN 4321"
    assert servicio._enmascarar(texto, cred) == "Timeout llenando *** para *** con PIN ***"


def test_ingreso_fallido_de_peaje_es_rechazo():
    from src.features.boveda.conectores.peajes import ConectorPeaje
    from src.features.descarga_peajes import portales

    def listar(pw, cred):
        raise portales.ErrorIngreso("no se pudo entrar")

    con = ConectorPeaje("x", "X", listar)
    sesion = con.ingresar(object(), Credencial(usuario="u", clave=Secreto("clave")))
    assert "clave" not in repr(sesion)
    with pytest.raises(CredencialesRechazadas):
        con.listar_documentos(sesion)


@pytest.mark.skipif(os.environ.get("LA_HERENCIA_TEST_WC") != "1", reason="Usa la conexión real a WC (solo applock, sin escrituras)")
def test_lock_real_se_libera_al_soltar():
    lock = servicio.tomar_lock(999999)
    assert lock is not None
    assert servicio.tomar_lock(999999) is None
    servicio._soltar_lock(lock, 999999)
    otro = servicio.tomar_lock(999999)
    assert otro is not None
    servicio._soltar_lock(otro, 999999)
