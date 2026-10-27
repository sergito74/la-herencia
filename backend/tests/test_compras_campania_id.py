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


@pytest.fixture
def validacion(catalogo, monkeypatch):
    monkeypatch.setattr(repository, "existe_contacto_valido_para_compra", lambda i: True)
    monkeypatch.setattr(repository, "existe_rubro", lambda i: True)
    monkeypatch.setattr(repository, "existe_centro_costo", lambda i: True)
    monkeypatch.setattr(repository, "existe_destino", lambda i: True)
    monkeypatch.setattr(repository, "campanias_validas_por_destino", lambda: {1: {20}, 6: {24}, 16: {20, 24}})
    original = repository.fetch_all

    def fetch_all(sql, params=()):
        if "DestinoCompras" in sql:
            return [{"id": 1, "n": "General"}, {"id": 6, "n": "Soja primera"}, {"id": 16, "n": "Stock"}]
        return original(sql, params)

    monkeypatch.setattr(repository, "fetch_all", fetch_all)


def _linea(**kw):
    return {"idRubro": 1, "idCentroCosto": 1, **kw}


def test_rechaza_linea_sin_rubro_o_centro_costo(validacion):
    errores = repository.validar_compra(1, "Pesos", None, [{}])
    assert any("rubro asignado" in e for e in errores)
    assert any("centro de costos asignado" in e for e in errores)


def test_rechaza_campania_fuera_del_catalogo(validacion):
    errores = repository.validar_compra(1, "Pesos", None, [_linea(**{"campaña": "2025-2026"})])
    assert len(errores) == 1 and "no existe en el catálogo" in errores[0]


def test_rechaza_id_que_no_corresponde_al_texto(validacion):
    errores = repository.validar_compra(1, "Pesos", None, [_linea(**{"campaña": "2025/2026", "idCampania": 20})])
    assert len(errores) == 1 and "no corresponde" in errores[0]


def test_acepta_campania_del_plan_o_vacia_en_general(validacion):
    assert repository.validar_compra(1, "Pesos", None, [_linea(**{"campaña": "2025/2026", "idDestino": 6}), _linea(**{"campaña": "", "idDestino": 1}), _linea()]) == []


def test_rechaza_campania_fuera_del_plan_para_el_cultivo(validacion):
    errores = repository.validar_compra(1, "Pesos", None, [_linea(**{"campaña": "No Aplica", "idDestino": 6})])
    assert len(errores) == 1 and "plan agrícola" in errores[0] and "Soja primera" in errores[0]


def test_general_solo_admite_no_aplica(validacion):
    assert repository.validar_compra(1, "Pesos", None, [_linea(**{"campaña": "2025/2026", "idDestino": 1})])


def test_stock_admite_campania_del_plan_y_no_aplica(validacion):
    assert repository.validar_compra(1, "Pesos", None, [_linea(**{"campaña": "2025/2026", "idDestino": 16}), _linea(**{"campaña": "No Aplica", "idDestino": 16})]) == []


def test_al_editar_se_conserva_una_combinacion_ya_guardada(validacion):
    assert repository.validar_compra(1, "Pesos", None, [_linea(**{"campaña": "No Aplica", "idDestino": 6})], {(6, 20)}) == []
