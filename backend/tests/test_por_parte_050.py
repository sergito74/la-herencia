"""Informe por parte de la estructura (050 US7)."""

from src.features.resultado_cultivo import por_parte as pp

PARTES = {1: "Semilla", 3: "Agroquímicos", 4: "Labores", 7: "Seguro agrícola"}
RUBRO = {"Herbicidas": 3, "Semillas": 1}


def test_cada_linea_va_a_su_parte():
    lineas = [
        {"idParte": 3, "montoPesos": 840_000, "montoDolares": 800},
        {"rubro": "Semillas", "origen": "Compra", "montoPesos": 100, "montoDolares": 1},
        {"concepto": "Contratista", "origen": "OrdenTrabajo", "montoPesos": 50, "montoDolares": None},
        {"origen": "Seguro", "montoPesos": 10, "montoDolares": 0},
        {"rubro": "Raro", "origen": "Compra", "montoPesos": 5, "montoDolares": 0},
    ]
    out = pp.agrupar(lineas, PARTES, RUBRO, 100)
    assert [p["parte"] for p in out] == ["Semilla", "Agroquímicos", "Labores", "Seguro agrícola", "Sin clasificar"]
    agro = out[1]
    assert agro["pesos"] == 840_000 and agro["pesosHa"] == 8_400 and agro["dolaresHa"] == 8


def test_sin_superficie_no_divide():
    out = pp.agrupar([{"idParte": 3, "montoPesos": 1, "montoDolares": 1}], PARTES, RUBRO, 0)
    assert out[0]["pesosHa"] is None
