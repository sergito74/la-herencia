"""031 — FR-012: bloqueo > 2%, advertencia ≤ 2%, todas las vías sin duplicar."""

from __future__ import annotations

import pytest

from src.features.vinculos import fuente, validacion


def test_sin_exceso_no_advierte():
    assert validacion.evaluar(1000, 400, 600, "X") is None


def test_exceso_dentro_del_2_por_ciento_advierte():
    assert "dentro del 2%" in validacion.evaluar(1000, 400, 615, "X")


def test_exceso_mayor_al_2_por_ciento_bloquea():
    with pytest.raises(validacion.ExcesoVinculo):
        validacion.evaluar(1000, 400, 625, "X")


def test_verificar_suma_todas_las_vias_y_acumula_en_el_mismo_pedido(monkeypatch):
    monkeypatch.setattr(fuente, "pagado_de_documentos", lambda claves: {k: 900.0 for k in claves})
    with pytest.raises(validacion.ExcesoVinculo):
        validacion.verificar_documentos([{"tipoDocumento": "CompraDeuda", "idDocumento": 1, "importe": 70},
                                         {"tipoDocumento": "CompraDeuda", "idDocumento": 1, "importe": 70}], lambda t, i: 1000)
