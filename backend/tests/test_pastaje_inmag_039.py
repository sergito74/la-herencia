"""039: parseo y actualización idempotente del INMAG (sin red ni base)."""

from datetime import date
from decimal import Decimal as D
from pathlib import Path

import pytest

from src.db import connection
from src.features.pastaje import inmag

HTML = (Path(__file__).parent / "fixtures" / "inmag_20260925_30.html").read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def sin_base(monkeypatch):
    monkeypatch.setattr(connection.pyodbc, "connect", lambda *a, **k: (_ for _ in ()).throw(AssertionError("conexión")))


def test_parsea_inmag_real_con_miles():
    assert inmag.parsear(HTML) == [
        (date(2026, 9, 25), 6316, D("4068.212")),
        (date(2026, 9, 29), 5009, D("4241.828")),
        (date(2026, 9, 30), 2284, None),
    ]


def test_actualizar_es_idempotente_y_omite_dias_sin_indice(monkeypatch):
    guardadas = {}
    monkeypatch.setattr(inmag, "fetch_all", lambda sql, p: [{"Fecha": f} for f in guardadas])

    def escribir(stmts):
        for _, params in stmts:
            guardadas[params[0]] = params[1]
    monkeypatch.setattr(inmag, "execute_write_transaction", escribir)
    bajar = lambda d, h: inmag.parsear(HTML)
    r1 = inmag.actualizar(date(2026, 9, 25), date(2026, 9, 30), bajar)
    r2 = inmag.actualizar(date(2026, 9, 25), date(2026, 9, 30), bajar)
    assert r1["agregados"] == 2 and r2["agregados"] == 0 and r1["sinIndice"] == ["2026-09-30"]
    assert guardadas == {"2026-09-25": "4068.212", "2026-09-29": "4241.828"}


def test_correccion_manual_exige_nota():
    with pytest.raises(ValueError):
        inmag.corregir(date(2026, 9, 30), D("4000"), " ", "sergio")
