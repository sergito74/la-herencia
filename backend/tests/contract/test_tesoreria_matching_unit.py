"""Unit test: valores-propios never runs a matching query at all (FR-005).

This exercises the real `matching.buscar_referencia`, not a mock, since the
guarantee under test is precisely that no repository/DB call happens for
this medio — mocking the function itself (as the router contract test
does) can't prove that.
"""

from __future__ import annotations

from src.features.tesoreria import matching


def test_valores_propios_sin_coincidencia_sin_consultar(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("valores-propios must not query the DB for matching")

    monkeypatch.setattr(matching, "get_movimiento", fail_if_called)
    monkeypatch.setattr(matching, "_buscar_candidatas", fail_if_called)

    resultado = matching.buscar_referencia("valores-propios", 999)

    assert resultado == {"estado": "sin_coincidencia", "candidatas": []}
