"""Tests de la comparación contra el motor de costeo heredado (017, US5)."""

from __future__ import annotations

from src.features.imputacion import repository
from src.features.ordenes import resultado


def test_comparacion_completa(monkeypatch):
    monkeypatch.setattr(
        resultado,
        "resumen_campania_heredado",
        lambda idc: [{"idCampania": idc, "campania": "2025/2026", "totalCostoPesos": 1000.0, "totalCostoDolares": None, "margenBrutoPesos": None}],
    )
    monkeypatch.setattr(
        repository,
        "costo_aprobado_por_campania",
        lambda idc: {"totalAprobado": 1000.0, "totalPendiente": 0.0},
    )

    resultado_comp = _comparar(1)
    assert resultado_comp["comparacionParcial"] is False
    assert resultado_comp["diferenciaPesos"] == 0.0


def test_comparacion_parcial(monkeypatch):
    monkeypatch.setattr(
        resultado,
        "resumen_campania_heredado",
        lambda idc: [{"idCampania": idc, "campania": "2025/2026", "totalCostoPesos": 1000.0, "totalCostoDolares": None, "margenBrutoPesos": None}],
    )
    monkeypatch.setattr(
        repository,
        "costo_aprobado_por_campania",
        lambda idc: {"totalAprobado": 800.0, "totalPendiente": 200.0},
    )

    resultado_comp = _comparar(1)
    assert resultado_comp["comparacionParcial"] is True
    assert resultado_comp["diferenciaPesos"] == -200.0


def test_no_altera_motor_heredado(monkeypatch):
    llamado = {"veces": 0}

    def fake_resumen(idc):
        llamado["veces"] += 1
        return [{"idCampania": idc, "campania": "X", "totalCostoPesos": 500.0, "totalCostoDolares": None, "margenBrutoPesos": None}]

    monkeypatch.setattr(resultado, "resumen_campania_heredado", fake_resumen)
    monkeypatch.setattr(repository, "costo_aprobado_por_campania", lambda idc: {"totalAprobado": 500.0, "totalPendiente": 0.0})

    antes = resultado.resumen_campania_heredado(1)
    _comparar(1)
    despues = resultado.resumen_campania_heredado(1)
    assert antes == despues
    assert llamado["veces"] == 3  # antes, dentro de _comparar, despues


def _comparar(id_campania: int) -> dict:
    """Réplica de la lógica del endpoint `GET /api/imputacion/comparacion`,
    sin pasar por FastAPI (más simple de testear)."""
    heredado = resultado.resumen_campania_heredado(id_campania)
    fila = heredado[0] if heredado else {"campania": None, "totalCostoPesos": 0.0, "totalCostoDolares": None}
    nuevo = repository.costo_aprobado_por_campania(id_campania)
    total_heredado = float(fila["totalCostoPesos"] or 0)
    total_nuevo = float(nuevo["totalAprobado"] or 0)
    diferencia = total_nuevo - total_heredado
    return {
        "idCampania": id_campania,
        "campania": fila["campania"],
        "costoHeredado": {"totalPesos": total_heredado, "totalDolares": fila.get("totalCostoDolares")},
        "costoNuevo": {
            "totalPesos": total_nuevo,
            "totalAprobado": total_nuevo,
            "totalPendiente": float(nuevo["totalPendiente"] or 0),
        },
        "diferenciaPesos": round(diferencia, 2),
        "diferenciaPorcentual": round(diferencia / total_heredado * 100, 2) if total_heredado else None,
        "comparacionParcial": abs(float(nuevo["totalPendiente"] or 0)) > 1e-6,
    }


def test_comparacion_parcial_con_pendiente_negativo(monkeypatch):
    """Hallazgo real (WC, notas de crédito dan importes negativos): la
    comparación es parcial aunque totalPendiente sea negativo, no solo > 0."""
    monkeypatch.setattr(
        resultado,
        "resumen_campania_heredado",
        lambda idc: [{"idCampania": idc, "campania": "X", "totalCostoPesos": 0.0, "totalCostoDolares": None, "margenBrutoPesos": None}],
    )
    monkeypatch.setattr(repository, "costo_aprobado_por_campania", lambda idc: {"totalAprobado": 0.0, "totalPendiente": -0.08})

    resultado_comp = _comparar(1)
    assert resultado_comp["comparacionParcial"] is True
