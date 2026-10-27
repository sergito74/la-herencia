"""Corrida de la rutina (043, T020) con cuentas y Outlook simulados."""

from __future__ import annotations

from datetime import datetime

import pytest

from src.features.documentos_nuevos import mails, rutina


@pytest.fixture
def sin_cuentas(monkeypatch):
    monkeypatch.setattr(rutina, "_cuentas", lambda r, p: None)
    monkeypatch.setattr(rutina, "_contar_portal", lambda i, r: None)


def _almacen(nombre, n_mails, ultimo):
    ms = [mails.Mail(f"e{i}", "Proveedor", "Factura", ultimo, [mails.Adjunto("f.pdf", b"%PDF")]) for i in range(n_mails)]
    return mails.Almacen(nombre, datetime(2026, 10, 28, 7), ms, ultimo)


def test_proxima_corrida():
    assert rutina.proxima("07:00,14:00", datetime(2026, 10, 28, 6, 59)) == datetime(2026, 10, 28, 7, 0)
    assert rutina.proxima("07:00,14:00", datetime(2026, 10, 28, 7, 0)) == datetime(2026, 10, 28, 14, 0)
    assert rutina.proxima("07:00,14:00", datetime(2026, 10, 28, 15, 0)) == datetime(2026, 10, 29, 7, 0)


def test_no_se_lanza_otra_en_curso(repo_sim):
    repo_sim.abrir_corrida()
    assert rutina.correr() is None


def test_marca_avanza_aunque_una_cuenta_falle(repo_sim, monkeypatch):
    monkeypatch.setattr(rutina, "_cuentas", lambda r, p: (p.append("Cargill: revisar en la bóveda"),
                                                          r.__setitem__("cuentasConProblemas", 1)))
    monkeypatch.setattr(rutina, "_contar_portal", lambda i, r: None)
    ultimo = datetime(2026, 10, 28, 12)
    monkeypatch.setattr(mails, "nuevos", lambda marca_de, ahora: iter([_almacen("Outlook", 1, ultimo)]))
    monkeypatch.setattr(rutina, "procesar_adjunto", lambda i, m, a: "para_cargar")
    rutina.correr()
    c = repo_sim.corridas[-1]
    assert c["estado"] == "con_problemas" and c["documentosNuevos"] == 1 and c["paraCargarAMano"] == 1
    assert repo_sim.marcas["Outlook"] == ultimo


def test_adjunto_que_falla_no_adelanta_la_marca(repo_sim, monkeypatch, sin_cuentas):
    monkeypatch.setattr(mails, "nuevos", lambda marca_de, ahora: iter([_almacen("Outlook", 1, datetime(2026, 10, 28, 12))]))

    def falla(*a):
        raise RuntimeError("PDF dañado")
    monkeypatch.setattr(rutina, "procesar_adjunto", falla)
    monkeypatch.setattr(rutina, "sin_procesar", falla)
    rutina.correr()
    assert "Outlook" not in repo_sim.marcas
    assert repo_sim.corridas[-1]["estado"] == "con_problemas"


def test_adjunto_ilegible_queda_pendiente_y_la_marca_avanza(repo_sim, monkeypatch, sin_cuentas):
    ultimo = datetime(2026, 10, 28, 12)
    monkeypatch.setattr(mails, "nuevos", lambda marca_de, ahora: iter([_almacen("Outlook", 1, ultimo)]))

    def falla(*a):
        raise RuntimeError("PDF dañado")
    monkeypatch.setattr(rutina, "procesar_adjunto", falla)
    monkeypatch.setattr(rutina, "_guardar", lambda carpeta, nombre, contenido, sha: str(carpeta / nombre))
    rutina.correr()
    assert repo_sim.marcas["Outlook"] == ultimo
    (doc,) = repo_sim.docs.values()
    assert doc["modulo"] == "sin_clasificar" and doc["motivo"].startswith("Documento pendiente de procesamiento")


def test_outlook_caido_no_corta_la_rutina(repo_sim, monkeypatch, sin_cuentas):
    def caido(*a):
        raise OSError("Outlook no responde")
    monkeypatch.setattr(mails, "nuevos", caido)
    rutina.correr()
    c = repo_sim.corridas[-1]
    assert c["estado"] == "con_problemas" and "Outlook no respondió" in c["mensaje"]


def test_tick_activacion_no_corre_y_recuperacion_unica(repo_sim, monkeypatch, sin_cuentas):
    corridas = []
    monkeypatch.setattr(rutina, "correr", lambda origen="programada": corridas.append(origen))
    assert not rutina.tick(datetime(2026, 10, 28, 10))
    assert repo_sim.prog["proxima"] == datetime(2026, 10, 28, 14)
    # El sistema estuvo apagado dos horarios: corre una sola vez.
    assert rutina.tick(datetime(2026, 10, 29, 16))
    assert not rutina.tick(datetime(2026, 10, 29, 16, 1))
    assert corridas == ["programada"]
