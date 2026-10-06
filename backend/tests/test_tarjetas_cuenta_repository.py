"""Funciones puras de la cuenta de tarjetas — 034."""

from datetime import date

from src.features.tarjetas_cuenta import repository as r


def _v(fecha, origen, id_origen, deuda=0, credito=0, doc=None):
    return {"Fecha": fecha, "Origen": origen, "IdOrigen": id_origen, "Deuda": deuda, "Credito": credito,
            "Documento": doc, "nro": None}


def test_estado_vinculo():
    assert r.estado_vinculo(100, 100, True, False) == "vinculado"
    assert r.estado_vinculo(100, 40, True, False) == "resto-con-proveedor"
    assert r.estado_vinculo(100, 0, False, False) == "sin-proveedor"
    assert r.estado_vinculo(100, 0, False, True) == "cruzado-con-devolucion"


def test_filas_acumulado_y_detalle_saldo():
    vista = [
        _v(date(2025, 1, 10), "Tarjeta consumo", 1, deuda=100),
        _v(date(2025, 2, 5), "Tarjeta consumo", 2, deuda=50),
        _v(date(2025, 1, 31), "Tarjeta cargo", 1001, deuda=10),
        _v(date(2025, 2, 20), "Banco Nacion", 7, credito=110),
    ]
    vista.sort(key=lambda x: (x["Fecha"], x["Origen"], x["IdOrigen"]))
    consumos = {1: {"idResumen": 1, "importe": 100, "vinculado": 100, "tieneProveedor": True},
                2: {"idResumen": 2, "importe": 50, "vinculado": 0, "tieneProveedor": False}}
    filas = r.construir_filas(vista, consumos, {("BNA", 7): 1}, {})
    ini, per, fin = r.acumular(filas, None, date(2025, 2, 28))
    assert (ini, fin) == (0.0, -50.0)
    cierres = {1: date(2025, 1, 31), 2: date(2025, 3, 31)}
    d = r.detalle_saldo(filas, cierres, date(2025, 2, 28), fin)
    assert d == {"exigible": 0.0, "noResumido": -50.0}
    ini2, per2, fin2 = r.acumular(filas, date(2025, 2, 1), date(2025, 2, 28))
    assert ini2 == -110.0 and fin2 == -50.0 and len(per2) == 2
    agr = r.agrupar_por_resumen(filas, cierres, {})
    # por resumen solo cuenta resúmenes cerrados a la fecha: coincide con el exigible
    assert r.acumular(agr, None, date(2025, 2, 28))[2] == d["exigible"]
