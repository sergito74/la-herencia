"""Control de integridad de tarjetas con fixtures puros — 034 (T031)."""

from datetime import date

from src.features.tarjetas_cuenta import control as c

HOY = date(2026, 10, 6)


def _raw(**kw):
    raw = {"hoy": HOY, "tarjetas": [{"idTarjeta": 1, "nombre": "T1", "activa": True, "idContacto": 10}],
           "contactosTarjeta": {10}, "pagos": [], "movimientosTarjeta": [], "debitosTarjeta": [], "creditosSinContacto": [],
           "crucesVigentes": set(), "resumenes": [], "consumos": [], "saldos": []}
    raw.update(kw)
    return raw


def _cats(raw):
    return [h["categoria"] for h in c.hallazgos(raw)]


def _pago(**kw):
    p = {"idPago": 1, "idResumen": 5, "idTarjeta": 1, "fecha": date(2026, 1, 1), "importe": 100.0, "medio": "bna",
         "idMovimientoOrigen": 7, "importeMovimiento": -100.0, "contactoMovimiento": 10, "estadoResumen": "Abierto"}
    p.update(kw)
    return p


def test_pago_correcto_no_da_hallazgos():
    assert _cats(_raw(pagos=[_pago()])) == []


def test_pago_en_proveedor_sin_origen_e_importe():
    assert _cats(_raw(pagos=[_pago(contactoMovimiento=99)])) == ["pago-en-proveedor"]
    assert _cats(_raw(pagos=[_pago(idMovimientoOrigen=None, importeMovimiento=None)])) == ["pago-sin-origen-o-importe"]
    assert _cats(_raw(pagos=[_pago(importeMovimiento=-150.0)])) == ["pago-sin-origen-o-importe"]


def test_pago_repartido_entre_resumenes_es_valido():
    pagos = [_pago(idPago=1, importe=60.0), _pago(idPago=2, idResumen=6, importe=40.0)]
    assert _cats(_raw(pagos=pagos)) == []


def test_saldo_inicial_con_pagos():
    assert _cats(_raw(pagos=[_pago(estadoResumen="Cerrado")])) == ["saldo-inicial-con-pagos"]


def test_movimiento_sin_resumen_y_cruzado():
    m = {"idTarjeta": 1, "medio": "bna", "idMovimiento": 3, "fecha": date(2025, 9, 1), "importe": -50.0,
         "tieneResumen": False, "esCruzado": False}
    assert _cats(_raw(movimientosTarjeta=[m])) == ["movimiento-sin-resumen"]
    assert _cats(_raw(movimientosTarjeta=[{**m, "esCruzado": True}])) == []


def test_resumen_con_pendiente_respeta_tolerancia():
    r = {"idResumen": 1, "idTarjeta": 1, "fechaCierre": date(2026, 9, 20), "estado": "Abierto", "pendiente": 299.0}
    assert _cats(_raw(resumenes=[r])) == []
    assert _cats(_raw(resumenes=[{**r, "pendiente": 500.0}])) == ["resumen-con-pendiente", "continuidad-de-resumenes"]


def test_devolucion_sin_cruzar():
    deb = {"idTarjeta": 1, "fecha": date(2025, 9, 1), "importe": 966654.20}
    cr = {"medio": "bna", "idMovimiento": 9, "fecha": date(2025, 9, 17), "importe": 966654.20}
    assert _cats(_raw(debitosTarjeta=[deb], creditosSinContacto=[cr])) == ["devolucion-sin-cruzar"]
    assert _cats(_raw(debitosTarjeta=[deb], creditosSinContacto=[cr], crucesVigentes={("bna", 9)})) == []
    assert _cats(_raw(debitosTarjeta=[deb], creditosSinContacto=[{**cr, "fecha": date(2025, 12, 1)}])) == []


def test_consumos_sin_proveedor_con_deuda_abierta_y_moneda():
    base = {"idTarjeta": 1, "idLineaConsumo": 1, "idResumen": 5, "fecha": date(2026, 1, 1), "detalle": "Compra",
            "observaciones": None, "importe": 1000.0, "vinculado": 0.0, "tieneProveedor": False, "cruzado": False,
            "proveedorDebe": False}
    assert _cats(_raw(consumos=[base])) == ["consumo-sin-proveedor"]
    assert _cats(_raw(consumos=[{**base, "cruzado": True}])) == []
    assert _cats(_raw(consumos=[{**base, "tieneProveedor": True, "proveedorDebe": True}])) == ["consumo-sin-vinculo-con-deuda-abierta"]
    assert _cats(_raw(consumos=[{**base, "tieneProveedor": True, "vinculado": 1000.0, "detalle": "Pago USD 100"}])) == ["indicios-de-otra-moneda"]


def test_diferencia_y_sin_contacto():
    assert _cats(_raw(saldos=[{"idTarjeta": 1, "saldo": 10.0, "pendienteNeto": -10.0}])) == []
    assert _cats(_raw(saldos=[{"idTarjeta": 1, "saldo": 500.0, "pendienteNeto": 0.0}])) == ["diferencia-contrapartida"]
    assert _cats(_raw(tarjetas=[{"idTarjeta": 1, "nombre": "T1", "activa": True, "idContacto": None}])) == ["tarjeta-sin-contacto"]


def test_continuidad_solo_para_tarjetas_activas_con_ultimo_resumen_viejo():
    viejo = {"idResumen": 1, "idTarjeta": 1, "fechaCierre": date(2018, 1, 1), "estado": "Abierto", "pendiente": 0.0}
    assert _cats(_raw(resumenes=[viejo])) == ["continuidad-de-resumenes"]
    inactiva = _raw(resumenes=[viejo], tarjetas=[{"idTarjeta": 1, "nombre": "T1", "activa": False, "idContacto": 10}])
    assert _cats(inactiva) == []
    # tarjeta sin resúmenes: no se señalan meses vacíos
    assert _cats(_raw()) == []
