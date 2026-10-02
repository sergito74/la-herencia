"""033-alta-impuestos: catálogo, validación, duplicado y baja bloqueada (con mocks)."""

from datetime import date

from src.features.impuestos import repository as R

TIPOS = [
    {"idTipoImpuesto": 1, "codigo": 1, "nombre": "IVA"},
    {"idTipoImpuesto": 15, "codigo": 1, "nombre": "Aporte Sindical"},
    {"idTipoImpuesto": 20, "codigo": 1, "nombre": "Retenciones Ganancias"},
    {"idTipoImpuesto": 6, "codigo": 2, "nombre": "Impuesto Inmobiliario"},
    {"idTipoImpuesto": 24, "codigo": 12, "nombre": "Sin identificar (generada desde el pago)"},
    {"idTipoImpuesto": 26, "codigo": 2, "nombre": "Patentes"},
]


def _catalogo(monkeypatch):
    monkeypatch.setattr(R, "fetch_all", lambda sql, params=(): TIPOS)
    return {o["nombre"]: [t["idTipoImpuesto"] for t in o["tipos"]] for o in R.get_catalogo()["organismos"]}


def test_catalogo_filtra_por_organismo_y_excluye_retenciones(monkeypatch):
    cat = _catalogo(monkeypatch)
    assert cat["AFIP / ARCA"] == [1]  # sin Aporte Sindical (UATRE) ni Retenciones Ganancias
    assert sorted(cat["ARBA"]) == [6, 26]
    assert cat["UATRE"] == [15]


def test_validar_tipo_de_otro_organismo_y_obligatorios(monkeypatch):
    _catalogo(monkeypatch)
    ok = {"idOrganismo": 12, "idTipoImpuesto": 26, "fecha": date(2024, 2, 29), "importe": 312351.20}
    assert R.validar(ok) == []
    assert R.validar({**ok, "idTipoImpuesto": 1})  # IVA no es de ARBA
    assert R.validar({**ok, "importe": 0})
    assert R.validar({**ok, "idOrganismo": 999})


def test_duplicado_solo_con_numero_real(monkeypatch):
    llamadas = []
    monkeypatch.setattr(R, "fetch_one", lambda sql, params: llamadas.append(params) or {"idImpuesto": 7})
    assert R.buscar_duplicado(12, "SIN COPIA") is None
    assert R.buscar_duplicado(12, None) is None
    assert llamadas == []
    assert R.buscar_duplicado(12, "0012345", excluir_id=3) == {"idImpuesto": 7}
    assert llamadas[0] == (12, "0012345", 3)


def test_vinculos_bloquean_la_baja(monkeypatch):
    respuestas = iter([{"n": 1}, {"n": 0}, {"n": 2}])
    monkeypatch.setattr(R, "fetch_one", lambda sql, params: next(respuestas))
    usos = R.vinculos(5)
    assert usos == ["1 consumo(s) de tarjeta", "2 vínculo(s) de pago del backfill"]
