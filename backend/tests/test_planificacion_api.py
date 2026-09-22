"""Planificación Agrícola: alta/baja de qué lote se destina a qué Cultivo/Campaña."""

import pytest

from src.features.planificacion import repository


def test_crear_duplicado_falla(monkeypatch):
    monkeypatch.setattr(repository, "fetch_one", lambda sql, params: {"x": 1})
    with pytest.raises(ValueError):
        repository.crear({"idLote": 1, "idCultivo": 2, "idCampania": 32})


def test_crear_inserta_y_devuelve_id(monkeypatch):
    monkeypatch.setattr(repository, "fetch_one", lambda sql, params: None)
    llamadas = []
    monkeypatch.setattr(repository, "execute_write_transaction", lambda stmts: llamadas.append(stmts) or [42])
    idx = repository.crear({"idLote": 1, "idCultivo": 2, "idCampania": 32})
    assert idx == 42
    sql, params = llamadas[0][0]
    assert "INSERT INTO dbo.PlanAgricola" in sql
    assert params == (1, 2, 32, "1-2-32")


def test_eliminar_inexistente_falla(monkeypatch):
    monkeypatch.setattr(repository, "fetch_one", lambda sql, params: None)
    with pytest.raises(ValueError):
        repository.eliminar(999)


def test_eliminar_existente(monkeypatch):
    monkeypatch.setattr(repository, "fetch_one", lambda sql, params: {"x": 1})
    llamadas = []
    monkeypatch.setattr(repository, "execute_write", lambda sql, params: llamadas.append((sql, params)))
    repository.eliminar(1)
    assert "DELETE FROM dbo.PlanAgricola" in llamadas[0][0]
