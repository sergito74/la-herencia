from fastapi.testclient import TestClient

from src.features.tarjetas_resumenes import repository
from src.main import app

client = TestClient(app)


def test_pendientes_no_se_confunde_con_un_id_de_resumen(monkeypatch):
    monkeypatch.setattr(repository, "get_pendientes", lambda *a, **k: [])
    r = client.get("/api/tarjetas-resumenes/pendientes")
    assert r.status_code == 200 and r.json()["total"] == 0


def test_pendientes_pagina_y_cuenta_las_que_tienen_sugerencia(monkeypatch):
    def item(i, sug):
        return {
            "idLineaConsumo": i, "idResumen": 1, "idTarjeta": 1, "importe": 10.0, "cantidadDocumentos": 1,
            "sugerencia": {"idsCompra": [i], "estado": "exacta", "unica": True, "documentos": []} if sug else None,
        }

    monkeypatch.setattr(repository, "get_pendientes", lambda *a, **k: [item(1, True), item(2, False), item(3, True)])
    body = client.get("/api/tarjetas-resumenes/pendientes?pageSize=2").json()
    assert (body["total"], body["totalConSugerencia"], len(body["items"])) == (3, 2, 2)
    solo = client.get("/api/tarjetas-resumenes/pendientes?soloConSugerencia=true").json()
    assert solo["total"] == 2


def test_sin_documento_traduce_el_error_de_validacion_a_400(monkeypatch):
    def falla(*a):
        raise ValueError(["Motivo inválido"])

    monkeypatch.setattr(repository, "marcar_sin_documento", falla)
    r = client.post("/api/tarjetas-resumenes/lineas/5/sin-documento", json={"motivo": "x"})
    assert r.status_code == 400


def test_lote_pasa_la_diferencia_aceptada_al_repositorio(monkeypatch):
    visto = {}

    def fake(id_linea, ids, aceptar):
        visto.update(id=id_linea, ids=ids, aceptar=aceptar)
        return []

    monkeypatch.setattr(repository, "vincular_compras_lote", fake)
    r = client.post(
        "/api/tarjetas-resumenes/lineas/7/compras/lote",
        json={"idsCompra": [1, 2], "aceptarDiferencia": {"motivo": "Redondeo"}},
    )
    assert r.status_code == 201
    assert visto == {"id": 7, "ids": [1, 2], "aceptar": {"motivo": "Redondeo", "detalle": None}}


def test_motivos_y_validacion():
    import pytest

    repository._validar_motivo("SinDocumento", "Impuesto", None)
    repository._validar_motivo("DiferenciaAceptada", "Otro", "diferencia de cambio")
    with pytest.raises(ValueError):
        repository._validar_motivo("SinDocumento", "Redondeo", None)
    with pytest.raises(ValueError):
        repository._validar_motivo("DiferenciaAceptada", "Otro", "  ")
