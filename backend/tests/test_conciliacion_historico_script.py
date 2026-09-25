"""Tests de la conciliación histórica (020) — mismo criterio que
test_aplicaciones_pago_endpoints.py: monkeypatch sobre los puntos de
entrada a `WC`, no se escribe contra la base real en tests automatizados.
La validación end-to-end contra datos reales se hace a mano (dry-run del
script) antes de correr `--apply` sobre el histórico completo."""

from __future__ import annotations

from src.features.aplicaciones_pago import sugerencia
from src.features.conciliacion_historico import repository


def _sugerencia(tipo_documento="CompraDeuda", id_documento=1, saldo_pendiente=1000.0, importe_sugerido=1000.0):
    return {
        "tipoDocumento": tipo_documento,
        "idDocumento": id_documento,
        "fecha": "2020-01-01",
        "saldoPendiente": saldo_pendiente,
        "importeSugerido": importe_sugerido,
    }


def test_clasificar_movimiento_exacto(monkeypatch):
    monkeypatch.setattr(sugerencia, "_contacto_e_importe", lambda origen, id_mov: (123, -1000.0))
    monkeypatch.setattr(
        sugerencia,
        "sugerir",
        lambda origen, id_mov: {
            "importeMovimiento": 1000.0,
            "sugerencias": [_sugerencia()],
            "saldoSinAsignar": 0.0,
        },
    )
    resultado = repository.clasificar_movimiento("bna", 1)
    assert resultado["clasificacion"] == "automatica-exacta"
    assert resultado["notaConciliacion"] is None


def test_clasificar_movimiento_mejor_esfuerzo_dentro_del_2_por_ciento(monkeypatch):
    monkeypatch.setattr(sugerencia, "_contacto_e_importe", lambda origen, id_mov: (123, -1000.0))
    monkeypatch.setattr(
        sugerencia,
        "sugerir",
        lambda origen, id_mov: {
            "importeMovimiento": 1000.0,
            "sugerencias": [_sugerencia(saldo_pendiente=985.0, importe_sugerido=985.0)],
            "saldoSinAsignar": 15.0,  # 1.5% de 1000, dentro de tolerancia
        },
    )
    resultado = repository.clasificar_movimiento("bna", 1)
    assert resultado["clasificacion"] == "automatica-mejor-esfuerzo"
    assert "1.5%" in resultado["notaConciliacion"] or "15.00" in resultado["notaConciliacion"]


def test_clasificar_movimiento_excepcion_por_diferencia_excesiva(monkeypatch):
    monkeypatch.setattr(sugerencia, "_contacto_e_importe", lambda origen, id_mov: (123, -1000.0))
    monkeypatch.setattr(
        sugerencia,
        "sugerir",
        lambda origen, id_mov: {
            "importeMovimiento": 1000.0,
            "sugerencias": [_sugerencia(saldo_pendiente=500.0, importe_sugerido=500.0)],
            "saldoSinAsignar": 500.0,  # 50%, excede el 2%
        },
    )
    resultado = repository.clasificar_movimiento("bna", 1)
    assert resultado["clasificacion"] == "excepcion"
    assert resultado["motivo"] == "sin documentos candidatos"


def test_clasificar_movimiento_excepcion_sin_documentos(monkeypatch):
    monkeypatch.setattr(sugerencia, "_contacto_e_importe", lambda origen, id_mov: (123, -1000.0))
    monkeypatch.setattr(
        sugerencia,
        "sugerir",
        lambda origen, id_mov: {"importeMovimiento": 1000.0, "sugerencias": [], "saldoSinAsignar": 1000.0},
    )
    resultado = repository.clasificar_movimiento("bna", 1)
    assert resultado["clasificacion"] == "excepcion"
    assert resultado["motivo"] == "sin documentos candidatos"


def test_clasificar_movimiento_excepcion_sin_contacto(monkeypatch):
    monkeypatch.setattr(sugerencia, "_contacto_e_importe", lambda origen, id_mov: (None, None))
    resultado = repository.clasificar_movimiento("valores-propios", 1)
    assert resultado["clasificacion"] == "excepcion"
    assert resultado["motivo"] == "sin contacto identificable"


def test_aplicar_clasificacion_inserta_una_fila_por_sugerencia(monkeypatch):
    llamadas = []

    def _fake_insert(sql, params):
        llamadas.append(params)
        return len(llamadas)

    monkeypatch.setattr(repository, "execute_insert_returning_id", _fake_insert)
    clasificacion = {
        "clasificacion": "automatica-mejor-esfuerzo",
        "notaConciliacion": "Diferencia de $15.00 (1.5%) contra combinación FIFO de 1 documento(s): CompraDeuda #1",
        "sugerencias": [_sugerencia(saldo_pendiente=985.0, importe_sugerido=985.0)],
    }
    ids = repository.aplicar_clasificacion("bna", 42, clasificacion)
    assert ids == [1]
    assert llamadas[0][0] == "bna"
    assert llamadas[0][1] == 42
    assert llamadas[0][2] == "CompraDeuda"
    assert llamadas[0][6] == "automatica-mejor-esfuerzo"


def test_movimientos_sin_aplicar_excluye_los_que_ya_tienen_aplicacion_vigente(monkeypatch):
    monkeypatch.setattr(
        repository,
        "_movimientos_del_medio",
        lambda medio, desde, hasta: [{"idMovimientoOrigen": 1}, {"idMovimientoOrigen": 2}] if medio == "bna" else [],
    )
    monkeypatch.setattr(
        repository,
        "aplicaciones_vigentes_de_movimiento",
        lambda medio, id_mov: [{"idAplicacion": 99}] if id_mov == 1 else [],
    )
    from datetime import date

    resultado = repository.movimientos_sin_aplicar(date(2015, 1, 1), date(2026, 12, 31))
    assert resultado == [{"origenMovimiento": "bna", "idMovimientoOrigen": 2}]


def test_movimientos_sin_aplicar_es_idempotente_tras_aplicar(monkeypatch):
    """Simula una segunda corrida: si el movimiento 2 ya quedó con una
    aplicación vigente (generada por la corrida anterior), la segunda
    corrida no lo vuelve a listar — evita duplicar aplicaciones (FR-006)."""
    monkeypatch.setattr(
        repository,
        "_movimientos_del_medio",
        lambda medio, desde, hasta: [{"idMovimientoOrigen": 2}] if medio == "bna" else [],
    )
    monkeypatch.setattr(repository, "aplicaciones_vigentes_de_movimiento", lambda medio, id_mov: [{"idAplicacion": 100}])
    from datetime import date

    resultado = repository.movimientos_sin_aplicar(date(2015, 1, 1), date(2026, 12, 31))
    assert resultado == []
