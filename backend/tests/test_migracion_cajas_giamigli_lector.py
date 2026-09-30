"""Tests de parseo/normalización de `scripts/migracion_cajas_giamigli/lector_excel.py`
(027-migracion-cajas-giamigli). Usa workbooks armados en memoria con
openpyxl — nunca abre el Excel real del usuario."""

from __future__ import annotations

from datetime import date

import openpyxl
import pytest

from scripts.migracion_cajas_giamigli.lector_excel import leer_hoja_caja, leer_hoja_socio


def _crear_hoja_socio(tmp_path, filas: list[list]) -> str:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Cuenta Prueba"
    ws.append(["(placeholder fila 1, ignorada por el lector)"])
    ws.append(
        [
            "Fecha", "Proveedor / Servicio", "Detalle", "Nro. Documento",
            "AR$", "Kg. Carne", "Dolares", "AR$", "Kg. Carne", "Dolares",
            "Kg. Carne", "Dolares", "Forma Pago", "Saldo",
        ]
    )
    for fila in filas:
        ws.append(fila)
    ruta = tmp_path / "cajas_giamigli_test.xlsx"
    wb.save(ruta)
    return str(ruta)


def _crear_hoja_caja(tmp_path, nombre_hoja: str, encabezado: list, filas: list[list]) -> str:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = nombre_hoja
    ws.append(encabezado)
    for fila in filas:
        ws.append(fila)
    ruta = tmp_path / "cajas_giamigli_test.xlsx"
    wb.save(ruta)
    return str(ruta)


def test_fila_con_debe_es_asignacion_gasto(tmp_path):
    ruta = _crear_hoja_socio(
        tmp_path,
        [[date(2018, 6, 13), "DER S.A.", "Bateria", None, 2685.83, None, None, None, None, None, None, None, "Efectivo", 2685.83]],
    )
    filas, casos = leer_hoja_socio(ruta, "Cuenta Prueba")
    assert casos == []
    assert len(filas) == 1
    assert filas[0].tipo == "AsignacionGasto"
    assert filas[0].importe_pesos == 2685.83
    assert filas[0].importe_usd == 0.0
    assert filas[0].importe_kg_carne == 0.0


def test_fila_con_haber_es_devolucion(tmp_path):
    ruta = _crear_hoja_socio(
        tmp_path,
        [[date(2026, 4, 2), "El Luchador", "Compra campo", None, None, None, None, 83548.50, 9.69, 30.05, None, None, "Galicia", -724210.65]],
    )
    filas, casos = leer_hoja_socio(ruta, "Cuenta Prueba")
    assert casos == []
    assert len(filas) == 1
    assert filas[0].tipo == "Devolucion"
    assert filas[0].importe_pesos == 83548.50
    assert filas[0].importe_kg_carne == 9.69
    assert filas[0].importe_usd == 30.05


def test_fila_solo_usd_o_kg_carne_sin_pesos_se_migra_igual(tmp_path):
    ruta = _crear_hoja_socio(
        tmp_path,
        [[date(2020, 1, 1), "Trueque puro", None, None, None, 5.0, None, None, None, None, None, None, "Trueque", 0]],
    )
    filas, casos = leer_hoja_socio(ruta, "Cuenta Prueba")
    assert casos == []
    assert len(filas) == 1
    assert filas[0].importe_pesos == 0.0
    assert filas[0].importe_kg_carne == 5.0


def test_fila_sin_fecha_va_a_revision(tmp_path):
    ruta = _crear_hoja_socio(
        tmp_path,
        [[None, "AFIP", "Autonomos", None, 1000.0, None, None, None, None, None, None, None, "Efectivo", 1000.0]],
    )
    filas, casos = leer_hoja_socio(ruta, "Cuenta Prueba")
    assert filas == []
    assert len(casos) == 1
    assert casos[0].motivo == "Sin fecha"


def test_fila_sin_ningun_importe_va_a_revision(tmp_path):
    ruta = _crear_hoja_socio(
        tmp_path,
        [[date(2020, 1, 1), "AFIP", "Autonomos", None, None, None, None, None, None, None, None, None, "Efectivo", 0]],
    )
    filas, casos = leer_hoja_socio(ruta, "Cuenta Prueba")
    assert filas == []
    assert len(casos) == 1
    assert casos[0].motivo == "Sin ningún importe"


def test_fila_completamente_vacia_se_ignora_en_silencio(tmp_path):
    ruta = _crear_hoja_socio(tmp_path, [[None] * 14, [None] * 14])
    filas, casos = leer_hoja_socio(ruta, "Cuenta Prueba")
    assert filas == []
    assert casos == []


def test_invariante_cobertura_sc004_socio(tmp_path):
    """SC-004: ninguna fila leída se pierde sin contar — filas_leidas ==
    migradas + a_revisar (acá no hay deduplicadas, eso lo agrega dedup.py)."""
    ruta = _crear_hoja_socio(
        tmp_path,
        [
            [date(2018, 6, 13), "DER S.A.", "Bateria", None, 2685.83, None, None, None, None, None, None, None, "Efectivo", 2685.83],
            [None, "AFIP", "Autonomos", None, 1000.0, None, None, None, None, None, None, None, "Efectivo", 1000.0],
            [date(2020, 1, 1), "AFIP", "Autonomos", None, None, None, None, None, None, None, None, None, "Efectivo", 0],
            [None] * 14,
        ],
    )
    filas, casos = leer_hoja_socio(ruta, "Cuenta Prueba")
    filas_leidas_no_vacias = len(filas) + len(casos)
    assert filas_leidas_no_vacias == 3  # la fila completamente vacía no cuenta


def test_caja_giamigli_sa_normaliza_columnas(tmp_path):
    ruta = _crear_hoja_caja(
        tmp_path,
        "Caja Efectivo Pesos",
        ["Fecha", "Concepto", "Cuenta", "Razon Social", "PC", "Nro. Documento", "Importe", "Saldo", "Recuento"],
        [[date(2011, 2, 17), "AFIP", "White", None, None, None, -1214.19, None, None]],
    )
    filas, casos = leer_hoja_caja(ruta, "Caja Efectivo Pesos", "GiamigliSA")
    assert casos == []
    assert len(filas) == 1
    assert filas[0].importe == -1214.19
    assert filas[0].cuenta == "White"
    assert filas[0].forma_pago is None


def test_caja_chica_campo_normaliza_debe_haber_a_importe_con_signo(tmp_path):
    ruta = _crear_hoja_caja(
        tmp_path,
        "Caja chica campo",
        ["Fecha", "Proveedor / Servicio", "Detalle", "Debe", "Haber", "Forma Pago", "Saldo"],
        [
            [date(2020, 10, 7), "Aporte Efectivo", None, None, 800, "Efectivo", 800],
            [date(2020, 10, 9), "XXXXXXXX", "2 Garrafas", 800, None, "Efectivo", 0],
        ],
    )
    filas, casos = leer_hoja_caja(ruta, "Caja chica campo", "CampoChica")
    assert casos == []
    assert len(filas) == 2
    assert filas[0].importe == 800  # Haber sin Debe → ingreso positivo
    assert filas[1].importe == -800  # Debe sin Haber → egreso negativo
    assert filas[0].cuenta is None
    assert filas[0].forma_pago == "Efectivo"


def test_caja_invalida_lanza_error(tmp_path):
    ruta = _crear_hoja_caja(tmp_path, "Hoja", ["Fecha"], [])
    with pytest.raises(ValueError):
        leer_hoja_caja(ruta, "Hoja", "OtraCosa")
