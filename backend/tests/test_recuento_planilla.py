"""Lectura de la planilla de recuento físico completada (recuento.leer_planilla)."""

import io

from openpyxl import Workbook

from src.features.remitos.recuento import leer_planilla


def _planilla(con_id: bool) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.append(["Recuento físico de stock"])
    ws.append(["Generado: 12/10/2026", None, None, None, None, "Fecha del recuento: 14/10/2026"])
    ws.append([])
    ws.append([])
    encabezado = ["N°", "Producto", "Principio activo", "Unidad", "Stock sistema", "Cantidad contada", "Diferencia", "Observaciones"]
    ws.append(encabezado + (["Id producto"] if con_id else []))
    ws.append(["Herbicida"])
    ws.append([1, "GOTEN", "ATRAZINA", "KGS", 50, 48, None, "bolsa rota"] + ([123] if con_id else []))
    ws.append([2, "TALIS", "FLUROCLORIDONA", "LTS", 39, None, None, None] + ([456] if con_id else []))
    ws.append([3, "DARREN", "FLUMIOXAZIN", "LTS", 1, "0,5", None, None] + ([789] if con_id else []))
    ws.append([])
    ws.append(["Firma del responsable: ____"])
    b = io.BytesIO()
    wb.save(b)
    return b.getvalue()


def test_lee_filas_contadas_fecha_e_id():
    r = leer_planilla(_planilla(con_id=True))
    assert r["fecha"].isoformat() == "2026-10-14"
    assert [(f["idProducto"], f["producto"], f["contada"]) for f in r["filas"]] == [(123, "GOTEN", 48.0), (456, "TALIS", None), (789, "DARREN", 0.5)]
    assert r["filas"][0]["observaciones"] == "bolsa rota"


def test_planilla_anterior_sin_id_se_resuelve_por_nombre():
    r = leer_planilla(_planilla(con_id=False))
    assert all(f["idProducto"] is None for f in r["filas"])
    assert [f["producto"] for f in r["filas"]] == ["GOTEN", "TALIS", "DARREN"]


def test_reparte_faltante_proporcional_a_lo_usado():
    from src.features.remitos.recuento import _repartir

    ordenes = [{"idOrdenInsumo": 1, "cantidad": 300.0}, {"idOrdenInsumo": 2, "cantidad": 100.0}]
    ajustes, sin_imputar = _repartir(-20.0, ordenes)  # contado 20 menos que el sistema
    assert [a["ajuste"] for a in ajustes] == [15.0, 5.0]
    assert sin_imputar == 0.0


def test_sobrante_no_deja_ordenes_en_negativo_y_el_resto_queda_sin_imputar():
    from src.features.remitos.recuento import _repartir

    ajustes, sin_imputar = _repartir(50.0, [{"idOrdenInsumo": 1, "cantidad": 30.0}])
    assert [a["ajuste"] for a in ajustes] == [-30.0]
    assert sin_imputar == 20.0


def test_sin_ordenes_todo_queda_sin_imputar():
    from src.features.remitos.recuento import _repartir

    assert _repartir(-7.5, []) == ([], -7.5)
