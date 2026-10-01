"""031 — revisión por proveedor: antes/después por factura (función pura)."""

from __future__ import annotations

from datetime import date

from src.features.vinculos import cadenas, revision


def test_detalle_muestra_quitar_agregar_pesificar_y_pagos_libres():
    raw = {"aplicaciones": [
               {"idAplicacion": 1, "origenMovimiento": "bna", "idMovimiento": 1, "tipoDocumento": "CompraDeuda", "idDocumento": 10,
                "importe": 1000, "origenCarga": "automatica-exacta"},
               {"idAplicacion": 2, "origenMovimiento": "galicia", "idMovimiento": 2, "tipoDocumento": "CompraDeuda", "idDocumento": 11,
                "importe": 10, "origenCarga": "automatica-exacta"}],
           "lineasCompras": [], "tesoreria": [], "backfill": [], "lineas": {}, "pagosResumen": [], "valores": [],
           "fechasOtros": {}, "importesOtros": {},
           "movimientos": {("bna", 1): {"fecha": date(2019, 4, 11), "importe": -1000, "concepto": "TRANSF. 30695542476"},
                           ("bna", 3): {"fecha": date(2023, 5, 20), "importe": -1000, "concepto": "TRANSF. PROVEEDOR"},
                           ("galicia", 2): {"fecha": date(2026, 5, 28), "importe": -5000, "concepto": "Trf Inmed Proveed"}},
           "documentos": {("CompraDeuda", 10): {"fecha": date(2023, 5, 1), "totalArs": 1000, "numero": "Factura 0007-00043556"},
                          ("CompraDeuda", 11): {"fecha": date(2026, 5, 1), "totalArs": 2000, "numero": "Factura 0001-1",
                                                "moneda": "Dolares", "tc": 200}}}
    raw["vinculos"] = cadenas.construir_vinculos(raw)
    items = [
        {"idItem": 1, "accion": "anular", "idAplicacion": 1, "origenMovimiento": "bna", "idMovimientoOrigen": 1,
         "tipoDocumento": "CompraDeuda", "idDocumento": 10, "importe": 1000, "motivo": "El pago es 1481 días anterior a la factura",
         "candidatos": None, "elegido": False},
        {"idItem": 2, "accion": "reemplazo", "idAplicacion": None, "origenMovimiento": "bna", "idMovimientoOrigen": 3,
         "tipoDocumento": "CompraDeuda", "idDocumento": 10, "importe": 1000, "motivo": "Otro pago", "candidatos": None, "elegido": True},
        {"idItem": 3, "accion": "pesificar", "idAplicacion": 2, "origenMovimiento": "galicia", "idMovimientoOrigen": 2,
         "tipoDocumento": "CompraDeuda", "idDocumento": 11, "importe": 2000, "motivo": "us$", "candidatos": None, "elegido": False},
    ]
    d = revision.armar_detalle(raw, items)
    f10 = next(f for f in d["facturas"] if f["idDocumento"] == 10)
    assert [(p["cambio"], p["fecha"], p["concepto"]) for p in f10["pagos"]] == [
        ("se quita", "2019-04-11", "TRANSF. 30695542476"), ("se agrega", "2023-05-20", "TRANSF. PROVEEDOR")]
    assert (f10["pagadoAntes"], f10["pagadoDespues"], f10["saldoDespues"]) == (1000, 1000, 0)
    f11 = next(f for f in d["facturas"] if f["idDocumento"] == 11)
    assert (f11["pagos"][0]["cambio"], f11["pagos"][0]["imputado"], f11["pagos"][0]["imputadoDespues"]) == ("se pesifica", 10, 2000)
    assert [(l["fecha"], l["liberado"]) for l in d["pagosLibres"]] == [("2019-04-11", 1000)]
