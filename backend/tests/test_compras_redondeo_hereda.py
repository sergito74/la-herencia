"""20/11/2026: el renglón de redondeo sin destino hereda la imputación del renglón de mayor importe."""
from src.features.compras.repository import heredar_imputacion_redondeos


def test_redondeo_hereda_del_mayor():
    lineas = [
        {"productoServicio": "A", "cantidad": 1, "precioUnitario": 10, "idDestino": 1, "idCentroCosto": 2, "idCampania": 19, "campaña": "x"},
        {"productoServicio": "B", "cantidad": 2, "precioUnitario": 30, "idDestino": 6, "idCentroCosto": 1, "idCampania": 17, "campaña": "2022/2023"},
        {"productoServicio": "Redondeo IVA", "cantidad": 1, "precioUnitario": 0.01, "idDestino": None, "idRubro": 9},
    ]
    r = heredar_imputacion_redondeos(lineas)[2]
    assert (r["idDestino"], r["idCentroCosto"], r["idCampania"], r["idRubro"]) == (6, 1, 17, 9)


def test_redondeo_con_destino_no_se_toca():
    lineas = [{"productoServicio": "A", "cantidad": 1, "precioUnitario": 10, "idDestino": 1},
              {"productoServicio": "Redondeo", "cantidad": 1, "precioUnitario": 0.01, "idDestino": 3}]
    assert heredar_imputacion_redondeos(lineas)[1]["idDestino"] == 3
