"""Hectáreas aplicadas en una orden ejecutada (04/11/2026, orden 162)."""

import pytest

from src.features.ordenes import repository as repo


def _orden():
    return {"estado": "Ejecutada", "insumos": [{
        "idOrdenInsumo": 1, "idProducto": 9, "producto": "GLIFO", "unidad": "LTS", "cantidadTotal": 100.0,
        "ajusteRecuento": -10.0, "devoluciones": [],
        "distribuciones": [
            {"idDistrib": 11, "idLote": 1, "cultivo": "Soja", "dosisHa": 2.0, "superficie": 50.0, "aplicar": True, "cantidadAsignada": 50.0},
            {"idDistrib": 12, "idLote": 2, "cultivo": "Trigo", "dosisHa": 2.0, "superficie": 50.0, "aplicar": True, "cantidadAsignada": 50.0},
        ]}]}


@pytest.fixture
def escrito(monkeypatch):
    out = []
    monkeypatch.setattr(repo, "obtener_orden", lambda _id: _orden())
    monkeypatch.setattr(repo, "execute_write_transaction", lambda fs: out.extend(f([]) for f in fs))
    monkeypatch.setattr(repo, "_recalcular_imputacion_por_productos", lambda _ids: None)
    monkeypatch.setattr(repo, "reparto_por_cultivo", lambda _id: [])
    return out


def test_reparte_el_mismo_total_con_las_hectareas_reales(escrito):
    repo.corregir_hectareas(162, {1: 30.0})
    asignado = {p[2]: (p[0], p[1]) for _, p in escrito}
    assert asignado[11] == (30.0, 37.5)  # 100 × 60/160
    assert asignado[12] == (50.0, 62.5)
    assert sum(a for _, a in asignado.values()) == 100.0


def test_lote_ajeno_se_rechaza(escrito):
    with pytest.raises(ValueError):
        repo.corregir_hectareas(162, {99: 10.0})


def test_reparto_por_cultivo_suma_el_ajuste_del_recuento(monkeypatch):
    monkeypatch.setattr(repo, "obtener_orden", lambda _id: _orden())
    filas = {f["cultivo"]: f["cantidad"] for f in repo.reparto_por_cultivo(162)}
    assert filas == {"Soja": 45.0, "Trigo": 45.0}  # (100 − 10) en partes iguales
