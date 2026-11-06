"""Corrida de la rutina (043, T020) con cuentas y Outlook simulados."""

from __future__ import annotations

from datetime import datetime

import pytest

from src.features.documentos_nuevos import mails, rutina


@pytest.fixture
def sin_cuentas(monkeypatch):
    monkeypatch.setattr(rutina, "_cuentas", lambda r, p: None)
    monkeypatch.setattr(rutina, "_contar_portal", lambda i, r: None)
    monkeypatch.setattr(rutina, "_carpetas", lambda i, r, p: None)
    monkeypatch.setattr(rutina, "_reevaluar", lambda p: None)
    monkeypatch.setattr(rutina, "_carpetas", lambda i, r, p: None)
    monkeypatch.setattr(rutina, "_reevaluar", lambda p: None)


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
    monkeypatch.setattr(rutina, "_carpetas", lambda i, r, p: None)
    monkeypatch.setattr(rutina, "_reevaluar", lambda p: None)
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


def test_tick_corre_solo_lo_que_lleva_2_dias_sin_correr(repo_sim, monkeypatch):
    from datetime import timedelta

    hoy = datetime(2026, 11, 6, 10)
    repo_sim.corridas = [{"estado": "ok", "alcance": "documentos", "inicio": hoy - timedelta(hours=47)},
                         {"estado": "ok", "alcance": "portales", "inicio": hoy - timedelta(days=2, minutes=1)}]
    corridas = []
    monkeypatch.setattr(rutina, "correr", lambda origen="programada", alcance="todo": corridas.append(alcance))
    assert rutina.tick(hoy)
    assert corridas == ["portales"]
    repo_sim.corridas.append({"estado": "ok", "alcance": "portales", "inicio": hoy})
    assert not rutina.tick(hoy + timedelta(minutes=1))  # documentos todavía no cumple 2 días


def test_xml_de_arca_junto_a_su_pdf_se_ignora():
    from src.features.documentos_nuevos import mails, rutina

    pdf = mails.Adjunto(nombre="factura.pdf", contenido=b"%PDF-1.4")
    xml = mails.Adjunto(nombre="factura.xml", contenido=b"<?xml version='1.0'?><FEV1Authorize/>")
    mail = mails.Mail(entry_id="x", remitente="Starlink", asunto="Recibo", recibido=datetime(2026, 11, 4),
                      adjuntos=[pdf, xml])
    assert rutina.procesar_adjunto(None, mail, xml) is None


def test_xml_se_guarda_con_su_extension(tmp_path):
    from src.features.documentos_nuevos import rutina

    ruta = rutina._guardar(tmp_path, "20261104_Starlink.pdf", b"<?xml version='1.0'?><a/>", "sha")
    assert ruta.endswith(".xml")


@pytest.mark.parametrize("alcance,esperado", [
    ("documentos", ["mails", "carpetas"]),
    ("portales", ["cuentas"]),
    ("todo", ["mails", "cuentas", "carpetas"]),
])
def test_cada_busqueda_hace_solo_su_parte(repo_sim, monkeypatch, alcance, esperado):
    hecho = []
    monkeypatch.setattr(rutina, "_mails", lambda i, r, p, a: hecho.append("mails"))
    monkeypatch.setattr(rutina, "_cuentas", lambda r, p: hecho.append("cuentas"))
    monkeypatch.setattr(rutina, "_contar_portal", lambda i, r: None)
    monkeypatch.setattr(rutina, "_carpetas", lambda i, r, p: hecho.append("carpetas"))
    monkeypatch.setattr(rutina, "_reevaluar", lambda p: None)
    rutina.correr("programada", alcance)
    assert hecho == esperado


def test_pedidos_desde_la_pantalla_se_atienden_en_orden(monkeypatch):
    corridas = []
    monkeypatch.setattr(rutina, "correr", lambda origen="programada", alcance="todo": corridas.append(alcance))
    rutina.pedir("portales")
    rutina.pedir("documentos")
    rutina.pedir("portales")  # repetido: no se encola dos veces
    assert rutina.tick() and rutina.tick()
    assert corridas == ["portales", "documentos"] and rutina.pedidos_pendientes() == []
