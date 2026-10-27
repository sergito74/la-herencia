"""Reglas de registro de documentos nuevos (043, T008), sobre el repositorio simulado y los avisos de portal."""

from __future__ import annotations

from src.features.documentos_nuevos import avisos


def _d(**k):
    return {"origen": "mail", "sha256": "a" * 64, "ruta": "x.pdf", "tipo": "factura", "modulo": "compras",
            "estado": "para_cargar", **k}


def test_mismo_archivo_mismo_modulo_un_solo_aviso(repo_sim):
    i, nuevo = repo_sim.registrar_documento(_d())
    j, otra = repo_sim.registrar_documento(_d(origen="portal"))
    assert nuevo and not otra and i == j
    assert repo_sim.resumen_pendientes() == {"compras": 1}


def test_ya_estaba_no_avisa(repo_sim):
    repo_sim.registrar_documento(_d(estado="ya_estaba"))
    assert repo_sim.resumen_pendientes() == {}


def test_para_cargar_con_registro_sigue_pendiente(repo_sim):
    i, _ = repo_sim.registrar_documento(_d(idRegistro=99))
    assert repo_sim.resumen_pendientes() == {"compras": 1}
    repo_sim.marcar_revisado(i, "sergio")
    assert repo_sim.resumen_pendientes() == {}


def test_aviso_desde_portal(repo_sim):
    fila = {"sha256": "b" * 64, "ruta": "f.pdf", "estadoCarga": "cargado_auto", "idCompra": 7, "idContacto": 71,
            "numeroDocumento": "0001-00000001", "totalImpreso": 100, "fecha": None, "motivo": None}
    assert avisos.desde_portal(19, 5, "factura", fila) == {"estado": "cargado_solo", "nuevo": True}
    fila2 = {**fila, "sha256": "c" * 64, "estadoCarga": "pendiente"}
    assert avisos.desde_portal(19, 6, "certificado", fila2)["estado"] == "para_cargar"
    modulos = {d["modulo"]: d for d in repo_sim.docs.values()}
    assert modulos["compras"]["idRegistro"] == 7
    assert modulos["impuestos"]["tipo"] == "retencion"
    assert modulos["impuestos"]["motivo"] == "Revisar y cargar a mano"


def test_aviso_desde_portal_ya_cargado_sin_aviso(repo_sim):
    fila = {"sha256": "d" * 64, "ruta": "f.pdf", "estadoCarga": "ya_cargado", "idCompra": 7}
    assert avisos.desde_portal(19, 5, "factura", fila)["estado"] == "ya_estaba"
    assert repo_sim.resumen_pendientes() == {}
