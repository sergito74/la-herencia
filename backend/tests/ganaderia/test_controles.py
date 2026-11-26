"""052 T038: controles ganaderos (funciones puras)."""

from datetime import date

from src.features.ganaderia import controles

TERNERO = 7


def _r(i, cant, peso, idv=1, precio=1000.0, unidad="Cabezas"):
    return {"idVenta": idv, "idDetalle": i, "fecha": date(2025, 5, 1), "doc": "0001-1", "tipo": TERNERO,
            "producto": "Terneros", "cantidad": cant, "unidad": unidad, "peso": peso, "precio": precio}


def _tipos(rs):
    return sorted(c["tipo"] for c in controles.controles_ventas(rs, {TERNERO: 180.0}))


def test_venta_correcta_sin_casos():
    assert _tipos([_r(1, 10, 1800)]) == []


def test_venta_sin_kg():
    assert _tipos([_r(1, 10, None)]) == ["venta_sin_dato"]


def test_kg_por_cabeza_fuera_de_rango():
    assert _tipos([_r(1, 10, 9000)]) == ["venta_kg_cabeza"]


def test_renglones_identicos():
    assert _tipos([_r(1, 10, 1800), _r(2, 10, 1800)]) == ["venta_renglon_repetido"]


def test_negativo_con_y_sin_par():
    assert _tipos([_r(1, 10, 1800), _r(2, -10, -1800, precio=900)]) == []
    assert "venta_negativo_sin_par" in _tipos([_r(1, 10, 1800), _r(2, -3, -540, precio=900)])


def test_aceptado_oculta_el_caso():
    grupos = [{"grupo": "Ventas", "items": [{"tipo": "venta_sin_dato", "clave": "5"}, {"tipo": "venta_sin_dato", "clave": "6"}]}]
    f = controles.filtrar(grupos, [{"tipo": "venta_sin_dato", "clave": "5"}])
    assert [i["clave"] for i in f[0]["items"]] == ["6"]
