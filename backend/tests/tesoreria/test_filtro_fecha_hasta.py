"""TEC-001: la fecha final incluye todo el último día y excluye desde la medianoche siguiente.

Datos sintéticos; SQL simulado (pyodbc bloqueado). El predicado capturado de la consulta se aplica
en Python sobre los movimientos sintéticos para verificar qué entra al listado, al recuento y a
«Solo pendientes».
"""

from __future__ import annotations

import operator
import re
from datetime import date, datetime

import pyodbc
import pytest

from src.features.conciliacion_tesoreria.repository import _info
from src.features.tesoreria import estado_resolucion, repository

DESDE = HASTA = date(2026, 8, 5)
SINTETICOS = {
    1: datetime(2026, 8, 5, 0, 0),    # medianoche del último día: entra
    2: datetime(2026, 8, 5, 14, 0),   # tarde del último día: entra
    3: datetime(2026, 8, 6, 0, 0),    # medianoche del día siguiente: queda fuera
}
_OPS = {">=": operator.ge, "<": operator.lt, "<=": operator.le}


@pytest.fixture(autouse=True)
def sin_sql(monkeypatch):
    intentos: list = []
    monkeypatch.setattr(pyodbc, "connect", lambda *a, **k: intentos.append(a) or (_ for _ in ()).throw(RuntimeError("SQL bloqueado")))
    yield
    assert intentos == []


def _filtrar(sql: str, params: tuple, columna: str) -> list[int]:
    """Aplica los predicados de fecha capturados a los movimientos sintéticos."""
    comparaciones = re.findall(rf"{re.escape(columna)} (>=|<=|<) \?", sql)
    assert comparaciones == [">=", "<"], comparaciones
    fechas = [p for p in params if isinstance(p, datetime)]
    assert len(fechas) == 2
    return [i for i, f in SINTETICOS.items()
            if all(_OPS[op](f, lim) for op, lim in zip(comparaciones, fechas))]


@pytest.mark.parametrize("medio", ["bna", "galicia"])
def test_listado_y_recuento_incluyen_el_dia_final(medio, monkeypatch):
    columna = repository.MEDIOS_CONFIG[medio].date_column
    capturas: dict = {}

    def fake_one(sql, params):
        capturas["count"] = _filtrar(sql, params, columna)
        return {"total": len(capturas["count"])}

    def fake_all(sql, params):
        capturas["list"] = _filtrar(sql, params[:-2], columna)
        return [{"id": i} for i in capturas["list"]]

    monkeypatch.setattr(repository, "fetch_one", fake_one)
    monkeypatch.setattr(repository, "fetch_all", fake_all)

    filas, total = repository.get_movimientos(medio, DESDE, HASTA, 1, 25)

    assert capturas["count"] == capturas["list"] == [1, 2]
    assert total == len(filas) == 2


@pytest.mark.parametrize("medio", ["bna", "galicia"])
def test_solo_pendientes_incluye_el_dia_final(medio, monkeypatch):
    columna = f"m.{_info(medio).fecha_col}"

    def fake_all(sql, params):
        return [{"id": i} for i in _filtrar(sql, params, columna)]

    monkeypatch.setattr(repository, "fetch_all", fake_all)
    monkeypatch.setattr(estado_resolucion, "esta_resuelto", lambda m, i: "sin_conciliar")

    assert repository.ids_pendientes(medio, DESDE, HASTA) == [1, 2]
