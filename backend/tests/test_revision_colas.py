"""Pruebas de las funciones puras de `colas.py` — 036 (T026). No leen la base."""

from __future__ import annotations

from src.features.revision_cuentas import colas


def _ctx(**cambios) -> dict:
    ctx = {"es_h": False, "pagos_pendientes": 0, "detector_cierra": True, "hallazgos": set(), "retenciones_sin_certificado": 0,
           "gobierna": "Pesos", "saldo_revision": 0.0, "tolerancia": None, "causa": "coincide", "cuenta_a_revisar": False,
           "imputaciones_sanas": True}
    ctx.update(cambios)
    return ctx


def test_una_cuenta_sin_pendientes_va_a_la_cola_a():
    assert colas.asignar_cola(_ctx()) == ("A", [])


def test_pago_sin_factura_y_doble_descuento_va_a_la_d_y_lista_el_doble_descuento():
    cola, otros = colas.asignar_cola(_ctx(pagos_pendientes=3, hallazgos={"doble-descuento-tarjeta"}))
    assert cola == "D" and otros == ["C"]


def test_una_entidad_va_siempre_a_la_h_aunque_tenga_otros_problemas():
    cola, otros = colas.asignar_cola(_ctx(es_h=True, pagos_pendientes=2, hallazgos={"contacto-duplicado"}))
    assert cola == "H" and otros == ["D", "E"]


def test_la_precedencia_es_h_d_e_c_g_f_i_b_a():
    assert colas.PRECEDENCIA == ("H", "D", "E", "C", "G", "F", "I", "B", "A")
    todo = _ctx(es_h=True, pagos_pendientes=1, hallazgos={"contacto-duplicado", "doble-descuento-tarjeta", "impuesto-sin-boleta", "sobrepago"},
                gobierna="Mixta", causa="otros")
    cola, otros = colas.asignar_cola(todo)
    assert cola == "H" and otros == ["D", "E", "C", "G", "F", "I", "B"]


def test_cada_problema_cae_en_su_cola():
    assert colas.asignar_cola(_ctx(hallazgos={"contacto-duplicado"}))[0] == "E"
    assert colas.asignar_cola(_ctx(hallazgos={"movimiento-sin-contacto"}))[0] == "E"
    assert colas.asignar_cola(_ctx(hallazgos={"doble-descuento-tarjeta"}))[0] == "C"
    assert colas.asignar_cola(_ctx(retenciones_sin_certificado=1))[0] == "G"
    assert colas.asignar_cola(_ctx(hallazgos={"impuesto-sin-boleta"}))[0] == "G"
    assert colas.asignar_cola(_ctx(gobierna="Mixta"))[0] == "F"
    assert colas.asignar_cola(_ctx(causa="otros"))[0] == "I"
    assert colas.asignar_cola(_ctx(cuenta_a_revisar=True))[0] == "I"
    for hallazgo in ("aplicacion-fuera-de-plazo", "sobrepago", "nota-sin-imputar"):
        assert colas.asignar_cola(_ctx(hallazgos={hallazgo}))[0] == "B"
    assert colas.asignar_cola(_ctx(imputaciones_sanas=False))[0] == "B"


def test_una_cuenta_en_dolares_solo_va_a_la_f_si_no_cierra():
    assert colas.asignar_cola(_ctx(gobierna="Dolares", saldo_revision=0.2, tolerancia=1.0))[0] == "A"
    assert colas.asignar_cola(_ctx(gobierna="Dolares", saldo_revision=900.0, tolerancia=1.0))[0] == "F"


def test_el_hallazgo_informativo_de_pagos_decididos_por_fifo_no_manda_a_la_cola_b():
    """`fuera-de-plazo-decidido` (pagos que el FIFO ya aplicó) no cuenta como excepción: la cuenta sigue en la A."""
    assert colas.asignar_cola(_ctx(hallazgos={"fuera-de-plazo-decidido"})) == ("A", [])


def test_la_diferencia_con_el_access_deja_de_ser_excepcion_cuando_hay_evidencia_externa():
    """Gana el proveedor con documento: el Access discrepa (causa `otros`) pero el saldo está respaldado por un saldo externo."""
    assert colas.asignar_cola(_ctx(causa="otros"))[0] == "I"
    assert colas.asignar_cola(_ctx(causa="otros", evidencia_externa=True)) == ("A", [])
    assert colas.asignar_cola(_ctx(causa="otros", evidencia_externa=True, cuenta_a_revisar=True))[0] == "I"


def test_el_detector_sin_cerrar_manda_a_la_d():
    assert colas.asignar_cola(_ctx(detector_cierra=False))[0] == "D"


def test_orden_de_dificultad_menos_movimientos_primero_y_a_igual_cantidad_menor_importe():
    cuentas = [
        {"idContacto": 1, "razonSocial": "Z", "movimientos": 50, "importe": 10.0},
        {"idContacto": 2, "razonSocial": "B", "movimientos": 5, "importe": 9000.0},
        {"idContacto": 3, "razonSocial": "A", "movimientos": 5, "importe": 100.0},
        {"idContacto": 4, "razonSocial": "C", "movimientos": 20, "importe": 1.0},
    ]
    assert [c["idContacto"] for c in colas.orden_de_dificultad(cuentas)] == [3, 2, 4, 1]


def test_el_orden_desempata_por_razon_social():
    cuentas = [{"idContacto": 9, "razonSocial": "b", "movimientos": 3, "importe": 5.0},
               {"idContacto": 8, "razonSocial": "A", "movimientos": 3, "importe": 5.0}]
    assert [c["idContacto"] for c in colas.orden_de_dificultad(cuentas)] == [8, 9]


def test_las_imputaciones_de_tarjeta_duplicadas_mandan_a_la_cola_c():
    assert colas.asignar_cola(_ctx(tarjetas_duplicadas=3))[0] == "C"
    assert colas.asignar_cola(_ctx(tarjetas_duplicadas=0))[0] == "A"
