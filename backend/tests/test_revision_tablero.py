"""Pruebas de `tablero.py` — 036 (T047). Funciones puras y fotos en memoria: no leen ni escriben la base."""

from __future__ import annotations

from datetime import date

import pytest

from src.features.revision_cuentas import tablero


def _r(i: int, cola: str, etapa: str, estado: str = "pendiente", importe: float = 100.0, **extra) -> dict:
    return {"idContacto": i, "razonSocial": f"Cuenta {i}", "cola": cola, "etapa": etapa, "estado": estado, "importeEnJuego": importe,
            "movimientos": 10, "importe": 1000.0, "pregunta": None, **extra}


def _cuentas() -> list[dict]:
    return [_r(1, "A", "E0"), _r(2, "A", "E0", importe=50.0), _r(3, "D", "E1", importe=1000.0), _r(4, "I", "E4", estado="esperando-sergio"),
            _r(5, "A", "E6", estado="cerrada"), _r(6, "B", "E5", estado="cerrada-con-excepcion"), _r(7, "A", "E6", estado="reabierta")]


def test_cada_cuenta_cae_en_una_sola_casilla_y_la_suma_es_el_total():
    a = tablero.agregar(_cuentas())
    assert a["totalCuentas"] == 7
    assert sum(c["cuentas"] for c in a["casillas"]) == 7
    assert sum(t["cuentas"] for t in a["totalesPorCola"].values()) == 7
    assert sum(a["porEstado"].values()) == 7


def test_las_casillas_suman_cuentas_e_importe_en_juego_y_vienen_en_el_orden_de_las_colas():
    a = tablero.agregar(_cuentas())
    cola_a_e0 = next(c for c in a["casillas"] if c["cola"] == "A" and c["etapa"] == "E0")
    assert cola_a_e0 == {"cola": "A", "etapa": "E0", "cuentas": 2, "importe": 150.0}
    assert [c["cola"] for c in a["casillas"]] == ["D", "I", "B", "A", "A"]      # precedencia H, D, E, C, G, F, I, B, A
    assert a["totalesPorCola"]["A"] == {"cuentas": 4, "importe": 350.0}


def test_el_recuento_por_estado_incluye_todos_los_estados_aunque_esten_en_cero():
    a = tablero.agregar(_cuentas())
    assert set(a["porEstado"]) == set(tablero.ESTADOS)
    assert a["porEstado"]["cerrada"] == 1 and a["porEstado"]["cerrada-con-excepcion"] == 1 and a["porEstado"]["reabierta"] == 1
    assert a["porEstado"]["en-proceso"] == 0


def test_la_semana_empieza_el_lunes():
    assert tablero.semana_de(date(2026, 10, 9)) == date(2026, 10, 5)      # viernes
    assert tablero.semana_de(date(2026, 10, 5)) == date(2026, 10, 5)      # lunes
    assert tablero.semana_de(date(2026, 10, 11)) == date(2026, 10, 5)     # domingo


def test_sin_foto_anterior_no_hay_comparacion():
    assert tablero.comparar(tablero.agregar(_cuentas()), None, None) is None


def test_con_una_foto_anterior_informa_las_cuentas_cerradas_y_la_variacion_de_la_cola_i():
    anterior = tablero.datos_de_foto(tablero.agregar([_r(1, "A", "E0"), _r(2, "I", "E4"), _r(3, "I", "E4"), _r(4, "A", "E6", estado="cerrada")]))
    actual = tablero.agregar([_r(1, "A", "E6", estado="cerrada"), _r(2, "I", "E4"), _r(3, "A", "E6", estado="cerrada-con-excepcion"), _r(4, "A", "E6", estado="cerrada")])
    c = tablero.comparar(actual, anterior, date(2026, 10, 5))
    assert c == {"semanaAnterior": date(2026, 10, 5), "cerradasEnLaSemana": 2, "variacionExcepciones": -1}


def test_la_foto_guarda_totales_no_las_cuentas():
    foto = tablero.datos_de_foto(tablero.agregar(_cuentas()))
    assert set(foto) == {"totalCuentas", "porEstado", "casillas", "totalesPorCola"}


def test_las_preguntas_son_una_por_cuenta_en_el_orden_de_las_colas():
    cuentas = [_r(1, "I", "E4", estado="esperando-sergio", pregunta="¿Hay estado de cuenta?", movimientos=50),
               _r(2, "D", "E1", estado="esperando-sergio", pregunta="¿Cuál es la factura?", movimientos=5), _r(3, "A", "E0")]
    p = tablero.preguntas_de(cuentas)
    assert [x["idContacto"] for x in p] == [2, 1] and p[0]["pregunta"] == "¿Cuál es la factura?"
    assert set(p[0]) == {"idContacto", "razonSocial", "cola", "etapa", "pregunta", "desde"}


# ---- La foto de la semana se crea una sola vez

@pytest.fixture
def fotos(monkeypatch):
    estado = {"fotos": {}, "guardadas": []}
    monkeypatch.setattr(tablero, "_foto_de_semana", lambda semana: estado["fotos"].get(semana))
    monkeypatch.setattr(tablero, "_guardar_foto", lambda semana, corte, datos, usuario: estado["fotos"].setdefault(semana, {"Semana": semana}) and estado["guardadas"].append((semana, usuario)) or len(estado["guardadas"]))
    return estado


def test_la_foto_de_la_semana_se_crea_una_sola_vez(fotos):
    a = tablero.agregar(_cuentas())
    primera = tablero.crear_foto(a, date(2026, 9, 30), "sistema", hoy=date(2026, 10, 9))
    assert primera["semana"] == date(2026, 10, 5) and primera["totalCuentas"] == 7
    assert tablero.crear_foto(a, date(2026, 9, 30), "sistema", hoy=date(2026, 10, 9)) is None       # al abrir el tablero no se repite
    assert len(fotos["guardadas"]) == 1
    otra_semana = tablero.crear_foto(a, date(2026, 9, 30), "sistema", hoy=date(2026, 10, 12))
    assert otra_semana["semana"] == date(2026, 10, 12)


def test_la_foto_manual_de_una_semana_que_ya_tiene_foto_devuelve_409(fotos):
    a = tablero.agregar(_cuentas())
    tablero.crear_foto(a, date(2026, 9, 30), "sistema", hoy=date(2026, 10, 9))
    with pytest.raises(tablero.TableroError) as e:
        tablero.crear_foto(a, date(2026, 9, 30), "Sergio", hoy=date(2026, 10, 9), manual=True)
    assert e.value.codigo == 409
