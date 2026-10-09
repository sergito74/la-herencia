"""Pruebas de `fichas.py` — 036 (T019). Datos simulados: no leen ni escriben la base."""

from __future__ import annotations

from datetime import date

import pytest

from src.features.revision_cuentas import criterios, fichas

CORTE = date(2026, 9, 30)


def _ctx(estado: str | None = None, **cambios_criterios) -> dict:
    base = {"pagos_pendientes": 0, "pagos_importe_pendiente": 0.0, "pagos_antiguos": 0, "detector_cierra": True, "hallazgos": set(),
            "retenciones_sin_certificado": 0, "imputaciones": {"sanas": True}, "tiene_inventario": True, "reabierta": False,
            "referencia_access": {"tiene": True, "explica": True, "diferencia": 0.0}, "saldo_externo": None, "sin_estado": False, "saldo": -1.31}
    base.update(cambios_criterios)
    fila = None if estado is None else {"Estado": estado, "InventarioFuentes": '[{"tipo": "access", "disponible": true}]', "Corte": CORTE,
                                          "SaldoAlCierre": -1.31, "Moneda": "Pesos", "UsuarioCierre": "Sergio", "FechaCierre": None,
                                          "PreguntaBloqueante": None, "MotivoExcepcion": None}
    return {"idContacto": 48, "corte": CORTE, "fila": fila or {"InventarioFuentes": '[{"tipo": "access", "disponible": true}]'}, "saldo": -1.31,
            "gobierna": "Pesos", "sentido": "proveedor", "cuenta": {"razonSocial": "Jauregui y Morales"}, "pagos": [], "marcas": {},
            "consistencia": {"cierra": True}, "criterios_ctx": base, "externos": [], "reabierta": base["reabierta"],
            "colas_ctx": {"es_h": False, "pagos_pendientes": base["pagos_pendientes"], "detector_cierra": True, "hallazgos": base["hallazgos"],
                          "retenciones_sin_certificado": 0, "gobierna": "Pesos", "saldo_revision": -1.31, "tolerancia": None,
                          "causa": "coincide", "cuenta_a_revisar": False, "imputaciones_sanas": True}}


@pytest.fixture
def simulada(monkeypatch):
    """Sustituye la base: registra lo que se guardaría y el historial."""
    guardado: list = []
    historial: list = []
    contexto = {"ctx": _ctx()}
    monkeypatch.setattr(fichas, "corte_vigente", lambda: {"corte": CORTE})
    monkeypatch.setattr(fichas, "cargar_contexto", lambda id_contacto, corte: contexto["ctx"])
    monkeypatch.setattr(fichas, "_asegurar_fila", lambda *a, **k: None)
    monkeypatch.setattr(fichas, "_guardar_estado", lambda *args: guardado.append(args))
    monkeypatch.setattr(fichas, "_registrar", lambda id_contacto, accion, detalle, usuario: historial.append((accion, detalle, usuario)))
    monkeypatch.setattr(fichas, "calcular_ficha", lambda id_contacto, corte=None: {"idContacto": id_contacto, "devuelta": True})
    return {"guardado": guardado, "historial": historial, "contexto": contexto}


# ---- cerrar

def test_cerrar_con_los_siete_criterios_guarda_corte_saldo_moneda_y_usuario(simulada):
    r = fichas.cambiar_estado(48, {"estado": "cerrada", "nota": "Cuenta de Jauregui"}, "Sergio")
    assert r["devuelta"] is True
    id_contacto, estado, nota, pregunta, motivo, usuario, cierre = simulada["guardado"][0]
    assert (id_contacto, estado, usuario) == (48, "cerrada", "Sergio")
    assert cierre == {"corte": CORTE, "saldo": -1.31, "moneda": "Pesos"}
    accion, detalle, _ = simulada["historial"][0]
    assert accion == "ficha-cierre" and detalle["saldoAlCierre"] == -1.31 and detalle["evidencia"] == "access"


def test_cerrar_con_un_criterio_sin_cumplir_devuelve_409_con_la_lista(simulada):
    simulada["contexto"]["ctx"] = _ctx(pagos_pendientes=2, pagos_importe_pendiente=500.0)
    with pytest.raises(fichas.FichaError) as e:
        fichas.cambiar_estado(48, {"estado": "cerrada"}, "Sergio")
    assert e.value.codigo == 409
    assert [c["codigo"] for c in e.value.detalle["criterios"]][0] == "C1"
    assert simulada["guardado"] == []


def test_cerrar_con_excepcion_exige_motivo_y_registra_los_criterios_sin_cumplir(simulada):
    simulada["contexto"]["ctx"] = _ctx(pagos_pendientes=2, pagos_importe_pendiente=500.0)
    with pytest.raises(fichas.FichaError) as e:
        fichas.cambiar_estado(48, {"estado": "cerrada-con-excepcion"}, "Sergio")
    assert e.value.codigo == 422
    fichas.cambiar_estado(48, {"estado": "cerrada-con-excepcion", "motivoExcepcion": "Cheques de 2015: no hay comprobante"}, "Sergio")
    *_, motivo, usuario, cierre = simulada["guardado"][0]
    assert motivo == "Cheques de 2015: no hay comprobante" and cierre is not None
    _, detalle, _ = simulada["historial"][0]
    assert "C1" in detalle["criteriosSinCumplir"]


def test_esperando_sergio_exige_la_pregunta(simulada):
    with pytest.raises(fichas.FichaError) as e:
        fichas.cambiar_estado(48, {"estado": "esperando-sergio"}, "Sergio")
    assert e.value.codigo == 422
    fichas.cambiar_estado(48, {"estado": "esperando-sergio", "pregunta": "¿Hay estado de cuenta del proveedor?"}, "Sergio")
    assert simulada["guardado"][0][3] == "¿Hay estado de cuenta del proveedor?"
    assert simulada["guardado"][0][-1] is None   # no es un cierre
    assert simulada["historial"][0][0] == "ficha-estado"


def test_la_pregunta_solo_se_guarda_cuando_se_espera_a_sergio(simulada):
    fichas.cambiar_estado(48, {"estado": "en-proceso", "pregunta": "no debería guardarse"}, "Sergio")
    assert simulada["guardado"][0][3] is None


def test_la_diferencia_menor_al_umbral_se_registra_con_su_importe_al_cerrar(simulada):
    simulada["contexto"]["ctx"] = _ctx(saldo_externo={"clasificacion": "menor-al-umbral", "fuente": "portal", "diferencia": 3.3, "fechaSaldo": "2026-09-30"})
    fichas.cambiar_estado(48, {"estado": "cerrada"}, "Sergio")
    _, detalle, _ = simulada["historial"][0]
    assert detalle["diferenciaMenorAlUmbral"] == 3.3 and detalle["evidencia"] == "portal"


def test_cerrar_cuando_la_cuenta_esta_reabierta_es_posible_si_los_criterios_cumplen(simulada):
    simulada["contexto"]["ctx"] = _ctx(estado="cerrada")
    simulada["contexto"]["ctx"]["reabierta"] = True
    simulada["contexto"]["ctx"]["criterios_ctx"]["reabierta"] = True
    with pytest.raises(fichas.FichaError):      # C7 no cumple mientras esté reabierta
        fichas.cambiar_estado(48, {"estado": "cerrada"}, "Sergio")


# ---- reapertura al corte

def _fila(estado="cerrada", saldo=-1.31, moneda="Pesos") -> dict:
    return {"Estado": estado, "SaldoAlCierre": saldo, "Moneda": moneda, "Corte": CORTE}


def test_un_cambio_de_redondeo_no_reabre_la_cuenta():
    assert fichas.esta_reabierta(_fila(), -1.9) is False


def test_un_cambio_de_saldo_al_corte_mayor_a_un_peso_reabre_la_cuenta():
    assert fichas.esta_reabierta(_fila(), 1500.0) is True


def test_los_movimientos_posteriores_al_corte_no_reabren_porque_el_saldo_se_mide_al_corte_del_cierre():
    # el mismo saldo al corte aunque la cuenta tenga movimientos nuevos después: no cambia
    assert fichas.esta_reabierta(_fila(), -1.31) is False


def test_una_cuenta_no_cerrada_o_sin_ficha_nunca_figura_reabierta():
    assert fichas.esta_reabierta(_fila(estado="en-proceso"), 9999.0) is False
    assert fichas.esta_reabierta(None, 9999.0) is False
    assert fichas.esta_reabierta({"Estado": "cerrada", "SaldoAlCierre": None}, 9999.0) is False


def test_en_dolares_la_tolerancia_es_relativa():
    fila = _fila(saldo=-100000.0, moneda="Dolares")
    assert fichas.esta_reabierta(fila, -100200.0) is False   # 0,2 %
    assert fichas.esta_reabierta(fila, -101000.0) is True    # 1 %
    assert fichas.tolerancia_de_reapertura("Pesos", 100000.0) == 1.0


# ---- ficha armada

def test_la_ficha_de_una_cuenta_sana_con_inventario_queda_en_e6_cola_a():
    ficha = fichas.armar_ficha(_ctx())
    assert ficha["etapa"] == "E6" and ficha["cola"] == "A" and ficha["estado"] == "pendiente" and ficha["estadoEfectivo"] == "pendiente"
    assert len(ficha["criterios"]) == 7 and ficha["cierre"] is None


def test_la_ficha_sin_inventario_esta_en_e0():
    ctx = _ctx()
    ctx["fila"] = {}
    ctx["criterios_ctx"]["tiene_inventario"] = False
    assert fichas.armar_ficha(ctx)["etapa"] == "E0"


def test_la_ficha_de_una_cuenta_cerrada_trae_los_datos_del_cierre_y_se_muestra_reabierta_si_cambio_el_saldo():
    ficha = fichas.armar_ficha(_ctx(estado="cerrada"))
    assert ficha["estado"] == "cerrada" and ficha["cierre"]["corte"] == CORTE and ficha["cierre"]["saldoAlCierre"] == -1.31
    assert ficha["estadoEfectivo"] == "cerrada"
    ctx = _ctx(estado="cerrada")
    ctx["reabierta"] = True
    assert fichas.armar_ficha(ctx)["estadoEfectivo"] == "reabierta"


def test_la_ficha_con_pagos_sin_factura_esta_en_e1_cola_d():
    ficha = fichas.armar_ficha(_ctx(pagos_pendientes=8, pagos_importe_pendiente=1872243.0))
    assert ficha["etapa"] == "E1" and ficha["cola"] == "D" and ficha["pagosSinFactura"] == 8


def test_validar_cambio_rechaza_los_pedidos_incompletos():
    for cambio in ({"estado": "cerrada-con-excepcion"}, {"estado": "esperando-sergio"}, {"estado": "esperando-sergio", "pregunta": "  "}):
        with pytest.raises(fichas.FichaError) as e:
            fichas.validar_cambio(cambio)
        assert e.value.codigo == 422
    fichas.validar_cambio({"estado": "en-proceso"})


def test_decisiones_exigen_texto_y_evidencia_para_descartar_el_access(monkeypatch):
    monkeypatch.setattr(fichas, "_registrar", lambda *a, **k: None)
    monkeypatch.setattr(fichas, "fetch_one", lambda *a, **k: {"id": 7, "fecha": None})
    with pytest.raises(fichas.FichaError) as e:
        fichas.registrar_decision(48, "otro", "  ", None, "Sergio")
    assert e.value.codigo == 422
    with pytest.raises(fichas.FichaError) as e:
        fichas.registrar_decision(48, "descartar-access", "El Access está mal", None, "Sergio")
    assert e.value.codigo == 422
    with pytest.raises(fichas.FichaError):
        fichas.registrar_decision(48, "tipo-raro", "texto", None, "Sergio")
    r = fichas.registrar_decision(48, "descartar-access", "El Access está mal", "Estado de cuenta del proveedor al 09/10/2026", "Sergio")
    assert r["tipo"] == "descartar-access" and r["idDecision"] == 7


def test_las_etapas_de_la_ficha_son_las_de_los_criterios():
    assert criterios.etapa_de(criterios.evaluar(_ctx()["criterios_ctx"]), True) == "E6"
