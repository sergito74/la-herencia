"""052 T025: validación de valores de configuración (sin base)."""

import pytest

from src.features.ganaderia import configuracion as cf


def test_valores_por_tipo():
    c = {c["key"]: c for c in cf.SECCIONES["reparto"]["campos"]}
    assert cf._valor(c["PctGanaderia"], "70") == 70.0 and cf._valor(c["Ejercicio"], " 2025/26 ") == "2025/26"
    assert cf._valor(c["PctGanaderia"], "") is None


def test_texto_largo_rechazado():
    c = {c["key"]: c for c in cf.SECCIONES["reparto"]["campos"]}
    with pytest.raises(ValueError):
        cf._valor(c["Ejercicio"], "2025/2026/27")


def test_ajuste_de_superficie_sin_motivo():
    with pytest.raises(ValueError):
        cf.guardar("ajustes_superficie", None, {"IdLote": 1, "Ejercicio": "2025/26", "MesesGanaderos": 6, "Motivo": " "}, None)


def test_categorias_no_admiten_alta_ni_borrar():
    assert cf.SECCIONES["categorias"]["alta"] is False
    with pytest.raises(ValueError):
        cf.borrar("categorias", 1)
