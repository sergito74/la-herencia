"""052 T040: flujo de caja filtrado por centro (reparto aproximado)."""

from src.features.flujo_caja.repository import centro_de_ingreso, filtrar_centro

TIPOS = {"vacas", "terneros", "toros"}


def test_ingresos_por_rubro():
    assert centro_de_ingreso("Venta Vacas", TIPOS) == "Ganaderia"
    assert centro_de_ingreso("Pastaje", TIPOS) == "Ganaderia"
    assert centro_de_ingreso("Venta Maiz", TIPOS) == "Agricultura"
    assert centro_de_ingreso("Cuenta de socios", TIPOS) is None


def test_filtra_egresos_ingresos_y_saca_internos():
    partes = [{"seccion": "egresos", "centroCosto": "Ganaderia", "rubro": "Vacunas"},
              {"seccion": "egresos", "centroCosto": "Agricultura", "rubro": "Semillas"},
              {"seccion": "ingresos", "centroCosto": None, "rubro": "Venta Terneros"},
              {"seccion": "ingresos", "centroCosto": None, "rubro": "Venta Soja"},
              {"seccion": "internos", "centroCosto": None, "rubro": "Traspaso"}]
    assert [p["rubro"] for p in filtrar_centro(partes, "Ganaderia", TIPOS)] == ["Vacunas", "Venta Terneros"]
