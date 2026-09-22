"""Traducción de claves heredadas (mapeo.py), sin tocar la base real."""

from src.features.resultado_cultivo import mapeo


def test_idCultivo_a_destino_encontrado(monkeypatch):
    monkeypatch.setattr(mapeo, "fetch_one", lambda sql, params: {"IdDestino": 6})
    assert mapeo.idCultivo_a_destino(3) == 6


def test_idCultivo_a_destino_inexistente(monkeypatch):
    monkeypatch.setattr(mapeo, "fetch_one", lambda sql, params: None)
    assert mapeo.idCultivo_a_destino(999) is None


def test_idCultivo_a_grano_pastura_es_null(monkeypatch):
    monkeypatch.setattr(mapeo, "fetch_one", lambda sql, params: {"IdGrano": None})
    assert mapeo.idCultivo_a_grano(7) is None


def test_campania_texto_a_id_y_su_inversa(monkeypatch):
    filas = {"2026/2027": 32}

    def fake_fetch_one(sql, params):
        if "WHERE Campaña" in sql:
            texto = params[0]
            idx = filas.get(texto)
            return {"id": idx} if idx is not None else None
        if "WHERE IdCampaña" in sql:
            idc = params[0]
            for t, i in filas.items():
                if i == idc:
                    return {"texto": t}
            return None
        return None

    monkeypatch.setattr(mapeo, "fetch_one", fake_fetch_one)
    idx = mapeo.campania_texto_a_id("2026/2027")
    assert idx == 32
    assert mapeo.campania_id_a_texto(idx) == "2026/2027"


def test_campania_texto_inexistente_devuelve_none(monkeypatch):
    monkeypatch.setattr(mapeo, "fetch_one", lambda sql, params: None)
    assert mapeo.campania_texto_a_id("no existe") is None
