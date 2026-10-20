"""Las líneas de compra guardan IdCampaña además del texto (auditoría de campañas 036), sin DB."""

import pytest

from src.features.compras import repository


@pytest.fixture
def catalogo(monkeypatch):
    camp = {"2025/2026": 24, "No Aplica": 20}

    def fetch_all(sql, params=()):
        assert "Campañas" in sql
        return [{"id": camp[params[0]]}] if params[0] in camp else []

    monkeypatch.setattr(repository, "fetch_all", fetch_all)
    monkeypatch.setattr(repository, "get_id_centro_costo_por_nombre", lambda n: 1)
    monkeypatch.setattr(repository, "get_id_destino_por_nombre", lambda n: 1)


def test_texto_de_campania_resuelve_su_id(catalogo):
    linea = repository.resolver_defaults_lineas([{"campaña": " 2025/2026 "}])[0]
    assert linea["idCampania"] == 24


def test_campania_por_defecto_tambien_lleva_id(catalogo, monkeypatch):
    monkeypatch.setattr(repository, "DEFAULT_CAMPANIA", "No Aplica")
    assert repository.resolver_defaults_lineas([{}])[0]["idCampania"] == 20


def test_texto_desconocido_queda_sin_id_y_no_se_inventa(catalogo):
    assert repository.resolver_defaults_lineas([{"campaña": "2099"}])[0]["idCampania"] is None


def test_id_explicito_se_respeta(catalogo):
    assert repository.resolver_defaults_lineas([{"campaña": "2025/2026", "idCampania": 7}])[0]["idCampania"] == 7


def test_insert_incluye_id_campania():
    sql, params = repository._linea_insert_statement(
        {"productoServicio": "x", "cantidad": 1, "precioUnitario": 1, "iva": 21, "campaña": "2025/2026", "idCampania": 24})([99])
    assert "IdCampaña" in sql and sql.count("?") == len(params) and 24 in params
