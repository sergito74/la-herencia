"""052 T031: existencia por eventos (funciones puras de stock.py)."""

from datetime import date

import pytest

from src.features.ganaderia import stock

VACAS, TERNEROS, TERNERAS, VAQ = 11, 2, 1, 5
SAN_JUSTO = 5671


def _rec(fecha, detalle, est=1, i=1):
    return {"id": i, "fecha": fecha, "establecimiento": est, "origen": "Recuento",
            "detalle": [{"categoria": c, "dueno": du, "cabezas": n} for c, du, n in detalle]}


def _mov(fecha, tipo, cat, cab, est=1, **kw):
    return {"fecha": fecha, "tipo": tipo, "categoria": cat, "cabezas": cab, "establecimiento": est, "dueno": None, **kw}


def test_recuento_mas_venta_y_nacimiento():
    rec = [_rec(date(2026, 4, 1), [(VACAS, None, 100), (TERNEROS, None, 10)])]
    movs = [_mov(date(2026, 5, 1), "Venta", VACAS, 2), _mov(date(2026, 9, 1), "Nacimiento", TERNEROS, 30),
            _mov(date(2027, 1, 1), "Venta", VACAS, 50)]
    st = stock.existencia(rec, movs, date(2026, 10, 1), [1])[1]["stock"]
    assert st[(None, VACAS)] == 98 and st[(None, TERNEROS)] == 40


def test_movimientos_anteriores_al_recuento_no_cuentan():
    rec = [_rec(date(2026, 4, 1), [(VACAS, None, 100)])]
    movs = [_mov(date(2026, 3, 1), "Venta", VACAS, 5), _mov(date(2026, 4, 1), "Muerte", VACAS, 1)]
    assert stock.existencia(rec, movs, date(2026, 5, 1), [1])[1]["stock"][(None, VACAS)] == 100


def test_diferencia_entre_recuentos_queda_sin_explicar():
    rec = [_rec(date(2026, 4, 1), [(VACAS, None, 100)]), _rec(date(2026, 10, 1), [(VACAS, None, 95)], i=2)]
    movs = [_mov(date(2026, 5, 1), "Venta", VACAS, 2)]
    r = stock.existencia(rec, movs, date(2026, 10, 2), [1])[1]
    assert r["stock"][(None, VACAS)] == 95
    assert r["sinExplicar"] == {(None, VACAS): -3}


def test_terceros_separados_de_la_propia():
    rec = [_rec(date(2026, 10, 15), [(VAQ, None, 30), (VAQ, SAN_JUSTO, 70)])]
    st = stock.existencia(rec, [], date(2026, 11, 1), [1])[1]["stock"]
    assert st[(None, VAQ)] == 30 and st[(SAN_JUSTO, VAQ)] == 70


def test_cambio_de_categoria_y_traslado():
    rec = [_rec(date(2026, 4, 1), [(TERNERAS, None, 50)]), _rec(date(2026, 4, 1), [], est=2, i=2)]
    movs = [_mov(date(2026, 6, 1), "CambioCategoria", TERNERAS, 20, categoriaDestino=VAQ),
            _mov(date(2026, 7, 1), "Traslado", VAQ, 5, establecimientoDestino=2)]
    r = stock.existencia(rec, movs, date(2026, 8, 1), [1, 2])
    assert r[1]["stock"][(None, TERNERAS)] == 30 and r[1]["stock"][(None, VAQ)] == 15
    assert r[2]["stock"][(None, VAQ)] == 5


def test_salida_que_deja_negativo_se_detecta():
    rec = [_rec(date(2026, 4, 1), [(VACAS, None, 3)])]
    nuevo = _mov(date(2026, 5, 1), "Muerte", VACAS, 4)
    assert stock.faltantes(rec, [], nuevo)[0]["existencia"] == -1
    assert stock.faltantes(rec, [], _mov(date(2026, 5, 1), "Muerte", VACAS, 3)) == []


def test_salida_que_deja_negativo_un_movimiento_posterior():
    rec = [_rec(date(2026, 4, 1), [(VACAS, None, 10)])]
    movs = [_mov(date(2026, 9, 1), "Venta", VACAS, 8)]
    assert stock.faltantes(rec, movs, _mov(date(2026, 5, 1), "Muerte", VACAS, 3))


def test_ajuste_sin_motivo_es_rechazado():
    with pytest.raises(stock.MotivoFaltante):
        stock.registrar_movimiento({"tipo": "AjusteRecuento", "cabezas": -2, "categoria": VACAS, "fecha": date.today(),
                                    "establecimiento": 1, "motivo": "  "}, None)


def test_venta_no_se_carga_a_mano():
    with pytest.raises(ValueError):
        stock.registrar_movimiento({"tipo": "Venta", "cabezas": 2, "categoria": VACAS, "fecha": date.today(),
                                    "establecimiento": 1}, None)
