"""Unit tests: valores-propios resuelve el contacto por texto libre de
`Comentarios` (revisado 2026-09-28 — antes devolvía siempre
"sin_coincidencia" sin consultar nada; ver matching.py para el porqué).
"""

from __future__ import annotations

from datetime import date

from src.features.tesoreria import matching


def test_valores_propios_sin_coincidencia_si_comentario_no_resuelve_contacto(monkeypatch):
    monkeypatch.setattr(
        matching,
        "get_movimiento",
        lambda medio, id_mov: {
            "comentarios": "xyz-texto-sin-contacto-asociado",
            "fechaEmision": date(2026, 8, 1),
            "importe": 100.0,
        },
    )

    def fail_if_called(*args, **kwargs):
        raise AssertionError("no debe buscar candidatas si no resolvió un único contacto")

    monkeypatch.setattr(matching, "_buscar_candidatas", fail_if_called)
    monkeypatch.setattr(
        matching,
        "_resolver_contacto_por_texto",
        lambda comentario: None,
    )

    resultado = matching.buscar_referencia("valores-propios", 999)

    assert resultado == {"estado": "sin_coincidencia", "candidatas": []}


def test_valores_propios_busca_candidatas_si_comentario_resuelve_un_contacto(monkeypatch):
    monkeypatch.setattr(
        matching,
        "get_movimiento",
        lambda medio, id_mov: {
            "comentarios": "Gentos",
            "fechaEmision": date(2026, 8, 1),
            "importe": 357161.08,
        },
    )
    monkeypatch.setattr(matching, "_resolver_contacto_por_texto", lambda comentario: 442)

    llamadas = {}

    def spy(id_contacto, fecha, importe):
        llamadas["args"] = (id_contacto, fecha, importe)
        return []

    monkeypatch.setattr(matching, "_buscar_candidatas", spy)

    resultado = matching.buscar_referencia("valores-propios", 999)

    assert llamadas["args"] == (442, date(2026, 8, 1), 357161.08)
    assert resultado == {"estado": "sin_coincidencia", "candidatas": []}
