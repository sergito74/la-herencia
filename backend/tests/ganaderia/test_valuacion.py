"""052 FR-008 etapa 1: valuación estimada (funciones puras)."""

from src.features.ganaderia.valuacion import coeficientes_desde_ventas, valuar

CATS = {1: {"sexo": "H", "orden": 10}, 3: {"sexo": "H", "orden": 20}, 11: {"sexo": "H", "orden": 41},
        14: {"sexo": "M", "orden": 44}}


def test_coeficiente_sin_ventas_toma_la_categoria_de_origen():
    c = coeficientes_desde_ventas({1: [1.1, 1.2, 1.15, 1.1, 1.2], 11: [0.6] * 5, 14: [0.7]}, CATS)
    assert c[1] == 1.15 and c[3] == 1.15 and c[11] == 0.6 and c[14] == 1.0


def test_valuar_con_regla_de_toro_y_gastos():
    filas = [{"idCategoria": 11, "categoria": "Vacas", "cabezas": 10, "kg": 4500, "ev": 10},
             {"idCategoria": 14, "categoria": "Toros", "cabezas": 2, "kg": 1500, "ev": 2.6}]
    r = valuar(filas, 1000.0, {11: 0.6, 14: 0.75}, {14: {"kg": 500, "coef": 1.0, "motivo": "toro"}}, 0.1)
    assert r["valor"] == round(10 * 450 * 600 * 0.9 + 2 * 500 * 1000 * 0.9, 2)
    assert r["kg"] == 6000 and r["ev"] == 12.6
