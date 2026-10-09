"""Pruebas de `lotes.py`, `dobles.py` y del cierre en bloque de `fichas.py` — 036 (T027). La base está sustituida: no lee ni escribe WC."""

from __future__ import annotations

import json
from datetime import date

import pytest

from src.features.revision_cuentas import dobles, fichas, lotes

CORTE = date(2026, 9, 30)


def _ctx(id_contacto: int, razon: str, movimientos: int = 10, volumen: float = 1000.0, saldo: float = 0.0, **cambios) -> dict:
    criterios_ctx = {"pagos_pendientes": 0, "pagos_importe_pendiente": 0.0, "pagos_antiguos": 0, "detector_cierra": True, "hallazgos": set(),
                     "retenciones_sin_certificado": 0, "imputaciones": {"sanas": True}, "tiene_inventario": False, "reabierta": False,
                     "referencia_access": {"tiene": True, "explica": True, "diferencia": 0.0}, "saldo_externo": None, "sin_estado": False, "saldo": saldo}
    colas_ctx = {"es_h": False, "pagos_pendientes": 0, "detector_cierra": True, "hallazgos": set(), "retenciones_sin_certificado": 0,
                 "gobierna": "Pesos", "saldo_revision": saldo, "tolerancia": None, "causa": "coincide", "cuenta_a_revisar": False, "imputaciones_sanas": True}
    criterios_ctx.update(cambios.get("criterios", {}))
    colas_ctx.update(cambios.get("colas", {}))
    return {"idContacto": id_contacto, "corte": CORTE, "fila": cambios.get("fila"), "saldo": saldo, "gobierna": "Pesos", "sentido": "proveedor",
            "cuenta": {"razonSocial": razon}, "movimientos": movimientos, "volumen": volumen, "criterios_ctx": criterios_ctx, "colas_ctx": colas_ctx,
            "externos": [], "reabierta": False}


# ---- reglas

def test_cada_regla_corresponde_a_una_cola():
    lotes.validar_regla("A", "aprobar-cierre")
    lotes.validar_regla("B", "fifo-tandas")
    lotes.validar_regla("C", "anular-doble-descuento")
    for cola, regla in (("B", "aprobar-cierre"), ("A", "fifo-tandas"), ("D", "anular-doble-descuento"), ("A", "inventada")):
        with pytest.raises(lotes.LoteError) as e:
            lotes.validar_regla(cola, regla)
        assert e.value.codigo == 422
    assert {r["regla"] for r in lotes.reglas_disponibles()} == {"aprobar-cierre", "fifo-tandas", "anular-doble-descuento"}


def test_el_nombre_de_la_correccion_guarda_la_cola_y_la_regla():
    assert lotes.regla_de_correccion("lote-A-aprobar-cierre") == ("A", "aprobar-cierre")
    assert lotes.regla_de_correccion("lote-C-anular-doble-descuento") == ("C", "anular-doble-descuento")


# ---- candidatas de la cola A

def test_la_cola_a_lista_solo_cuentas_de_la_a_de_la_mas_facil_a_la_mas_compleja():
    contextos = {
        1: _ctx(1, "Grande", movimientos=300, volumen=9e6),
        2: _ctx(2, "Chica", movimientos=4, volumen=500.0),
        3: _ctx(3, "Con pagos sin factura", colas={"pagos_pendientes": 2}, criterios={"pagos_pendientes": 2, "pagos_importe_pendiente": 10.0}),
    }
    cuentas = lotes.candidatas_aprobar_cierre(contextos, {})
    assert [c["idContacto"] for c in cuentas] == [2, 1]          # la 3 es de la cola D
    assert all(c["cumple"] for c in cuentas)
    assert cuentas[0]["extra"]["evidencia"] == "access"


def test_una_cuenta_sin_evidencia_figura_pero_no_cumple_y_dice_por_que():
    contextos = {5: _ctx(5, "Sin referencia", criterios={"referencia_access": {"tiene": False, "explica": False, "diferencia": None}})}
    (c,) = lotes.candidatas_aprobar_cierre(contextos, {})
    assert c["cumple"] is False
    assert any("C3" in m for m in c["extra"]["motivos"])


def test_los_movimientos_posteriores_a_la_referencia_del_access_se_muestran_en_el_lote():
    contextos = {7: _ctx(7, "Con movimientos nuevos")}
    (c,) = lotes.candidatas_aprobar_cierre(contextos, {7: {"movimientos": 3, "importe": 4500.0}})
    assert c["extra"]["posteriores"] == {"movimientos": 3, "importe": 4500.0}
    assert "3 movimientos posteriores a la referencia del Access" in lotes._texto(c["extra"])


def test_c7_no_impide_el_cierre_en_bloque_porque_la_regla_confirma_el_inventario():
    (c,) = lotes.candidatas_aprobar_cierre({9: _ctx(9, "Sin inventario")}, {})
    assert c["cumple"] is True


# ---- tildar

def _cuentas_del_lote() -> list[dict]:
    return [{"idContacto": 1, "cumple": True}, {"idContacto": 2, "cumple": True}, {"idContacto": 3, "cumple": False}]


def test_tildar_todas_marca_solo_las_que_cumplen():
    assert lotes.elegir_a_tildar(_cuentas_del_lote(), None, True) == {1, 2}


def test_tildar_por_ids_marca_exactamente_esas_y_permite_desmarcar():
    assert lotes.elegir_a_tildar(_cuentas_del_lote(), [1], False) == {1}
    assert lotes.elegir_a_tildar(_cuentas_del_lote(), [], False) == set()


def test_no_se_puede_tildar_una_cuenta_que_no_cumple_o_que_no_esta_en_el_lote():
    for ids in ([3], [99]):
        with pytest.raises(lotes.LoteError) as e:
            lotes.elegir_a_tildar(_cuentas_del_lote(), ids, False)
        assert e.value.codigo == 422


# ---- validaciones de aplicar, revertir y descartar

def _tildada(i: int, saldo: float = 100.0) -> dict:
    return {"idContacto": i, "saldoAntes": saldo, "tildada": True}


def test_aplicar_sin_cuentas_tildadas_devuelve_409():
    with pytest.raises(lotes.LoteError) as e:
        lotes.validar_aplicacion("simulada", [], {})
    assert e.value.codigo == 409


def test_aplicar_un_lote_ya_aplicado_devuelve_409():
    with pytest.raises(lotes.LoteError) as e:
        lotes.validar_aplicacion("aplicada", [_tildada(1)], {1: 100.0})
    assert e.value.codigo == 409


def test_aplicar_con_el_saldo_cambiado_desde_la_simulacion_devuelve_409():
    with pytest.raises(lotes.LoteError) as e:
        lotes.validar_aplicacion("simulada", [_tildada(1)], {1: 5000.0})
    assert e.value.codigo == 409 and "cambió" in e.value.mensaje
    lotes.validar_aplicacion("simulada", [_tildada(1)], {1: 100.4})      # un redondeo no cuenta


def test_revertir_solo_un_lote_aplicado_y_descartar_solo_uno_simulado():
    lotes.validar_reversion("aplicada")
    with pytest.raises(lotes.LoteError):
        lotes.validar_reversion("simulada")
    lotes.validar_descarte("simulada")
    with pytest.raises(lotes.LoteError):
        lotes.validar_descarte("aplicada")


# ---- flujo completo con la base sustituida

@pytest.fixture
def lote_en_memoria(monkeypatch):
    """Un lote `aprobar-cierre` guardado en memoria: simular, tildar, aplicar y revertir sin tocar WC."""
    estado = {"corrs": {}, "siguiente": 100, "llamadas": []}

    def crear(cola, regla, parametros, cuentas, usuario):
        i = estado["siguiente"]
        estado["corrs"][i] = {"idCorreccion": i, "regla": regla, "cola": cola, "estado": "simulada", "respaldo": None, "parametros": parametros,
                              "cuentas": [{"idContacto": c["idContacto"], "razonSocial": c["razonSocial"], "tildada": False, "cumple": c["cumple"], "saldoAntes": c["saldo"],
                                           "saldoDespues": c["saldo"], "detalle": "", "extra": c["extra"], "idsAplicacion": None} for c in cuentas]}
        estado["siguiente"] += 1
        return i

    monkeypatch.setattr(lotes, "_crear", crear)
    monkeypatch.setattr(lotes, "_leer", lambda i: estado["corrs"][i])
    monkeypatch.setattr(lotes, "_marcar_tildadas", lambda i, ids: [c.update(tildada=c["idContacto"] in ids) for c in estado["corrs"][i]["cuentas"]])
    monkeypatch.setattr(lotes, "_poner_estado", lambda i, e, usuario=None, respaldo=None, aplicacion=False, reversion=False:
                        estado["corrs"][i].update(estado=e, respaldo=respaldo or estado["corrs"][i]["respaldo"]) or estado["llamadas"].append((i, e, usuario)))
    monkeypatch.setattr(fichas, "corte_vigente", lambda: {"corte": CORTE})
    monkeypatch.setattr(lotes, "_candidatas", lambda cola, regla, corte, usuario: (
        lotes.candidatas_aprobar_cierre({1: _ctx(1, "Uno", saldo=1.0), 2: _ctx(2, "Dos", saldo=-1.5)}, {}), {}))
    monkeypatch.setattr("src.features.vinculos.backup.backup_verificado", lambda etiqueta: f"C:\\respaldos\\{etiqueta}.bak")
    monkeypatch.setattr(lotes.datos, "saldos_al_corte", lambda corte: {1: 1.0, 2: -1.5})
    estado["cierres"] = []
    monkeypatch.setattr(lotes, "_aplicar_cierre", lambda lote, tildadas, corte, usuario: estado["cierres"].append([c["idContacto"] for c in tildadas]))
    estado["reversiones"] = []
    monkeypatch.setattr(fichas, "revertir_cierre_en_bloque", lambda i, tildadas, usuario: estado["reversiones"].append([c["idContacto"] for c in tildadas]))
    return estado


def test_simular_crea_un_lote_con_una_fila_por_cuenta_y_ninguna_tildada(lote_en_memoria):
    lote = lotes.simular("A", "aprobar-cierre", "Sergio")
    assert lote["estado"] == "simulada" and lote["regla"] == "aprobar-cierre" and lote["cola"] == "A"
    assert sorted(c["idContacto"] for c in lote["cuentas"]) == [1, 2]
    assert all(c["tildada"] is False for c in lote["cuentas"])


def test_simular_rechaza_una_regla_que_no_corresponde_a_la_cola(lote_en_memoria):
    with pytest.raises(lotes.LoteError) as e:
        lotes.simular("B", "aprobar-cierre", "Sergio")
    assert e.value.codigo == 422


def test_aplicar_sin_tildar_devuelve_409_y_aplicar_deja_el_saldo_identico(lote_en_memoria):
    i = lotes.simular("A", "aprobar-cierre", "Sergio")["idCorreccion"]
    with pytest.raises(lotes.LoteError) as e:
        lotes.aplicar(i, "Sergio")
    assert e.value.codigo == 409
    lotes.tildar(i, None, True)
    lote = lotes.aplicar(i, "Sergio")
    assert lote["estado"] == "aplicada" and lote["respaldo"].endswith(f"lote-036-{i}.bak")
    assert [sorted(x) for x in lote_en_memoria["cierres"]] == [[1, 2]]
    assert all(c["saldoAntes"] == c["saldoDespues"] for c in lote["cuentas"])      # el cierre no cambia ningún saldo


def test_aplicar_dos_veces_devuelve_409(lote_en_memoria):
    i = lotes.simular("A", "aprobar-cierre", "Sergio")["idCorreccion"]
    lotes.tildar(i, [1], False)
    lotes.aplicar(i, "Sergio")
    with pytest.raises(lotes.LoteError) as e:
        lotes.aplicar(i, "Sergio")
    assert e.value.codigo == 409


def test_aplicar_con_un_saldo_cambiado_devuelve_409_y_no_cierra_nada(lote_en_memoria, monkeypatch):
    i = lotes.simular("A", "aprobar-cierre", "Sergio")["idCorreccion"]
    lotes.tildar(i, [1], False)
    monkeypatch.setattr(lotes.datos, "saldos_al_corte", lambda corte: {1: 9999.0})
    with pytest.raises(lotes.LoteError) as e:
        lotes.aplicar(i, "Sergio")
    assert e.value.codigo == 409 and lote_en_memoria["cierres"] == []


def test_revertir_devuelve_las_cuentas_tildadas_y_rechaza_un_lote_no_aplicado(lote_en_memoria):
    i = lotes.simular("A", "aprobar-cierre", "Sergio")["idCorreccion"]
    with pytest.raises(lotes.LoteError) as e:
        lotes.revertir(i, "Sergio")
    assert e.value.codigo == 409
    lotes.tildar(i, [2], False)
    lotes.aplicar(i, "Sergio")
    lote = lotes.revertir(i, "Sergio")
    assert lote["estado"] == "revertida" and lote_en_memoria["reversiones"] == [[2]]


def test_descartar_solo_un_lote_simulado(lote_en_memoria):
    i = lotes.simular("A", "aprobar-cierre", "Sergio")["idCorreccion"]
    lotes.descartar(i)
    assert lote_en_memoria["corrs"][i]["estado"] == "descartada"
    with pytest.raises(lotes.LoteError):
        lotes.descartar(i)


def test_tildar_un_lote_ya_aplicado_devuelve_409(lote_en_memoria):
    i = lotes.simular("A", "aprobar-cierre", "Sergio")["idCorreccion"]
    lotes.tildar(i, [1], False)
    lotes.aplicar(i, "Sergio")
    with pytest.raises(lotes.LoteError) as e:
        lotes.tildar(i, [2], False)
    assert e.value.codigo == 409


# ---- regla de doble descuento (cola C)

def test_las_imputaciones_duplicadas_se_agrupan_por_cuenta_sin_repetir_ids():
    hallazgos = [
        {"causa": "doble-descuento-tarjeta", "idContacto": 61, "importe": 100.0, "idsAplicacion": [5, 6]},
        {"causa": "doble-descuento-tarjeta", "idContacto": 61, "importe": 50.5, "idsAplicacion": [6, 7]},
        {"causa": "doble-descuento-tarjeta", "idContacto": 22, "importe": 10.0, "idsAplicacion": [9]},
        {"causa": "aplicacion-fuera-de-plazo", "idContacto": 61, "importe": 999.0, "idsAplicacion": [1]},
    ]
    r = dobles.ids_por_cuenta(hallazgos)
    assert r[61] == {"ids": [5, 6, 7], "pagos": 2, "importe": 150.5}
    assert r[22]["ids"] == [9]


def test_aplicar_doble_descuento_anula_las_imputaciones_de_las_cuentas_tildadas_y_guarda_los_ids(monkeypatch):
    operaciones: list = []
    monkeypatch.setattr(dobles, "execute_write_transaction", lambda ops: operaciones.extend(ops))
    lote = {"idCorreccion": 41}
    tildadas = [{"idContacto": 61, "extra": {"idsPropuestos": [5, 6, 7]}}, {"idContacto": 22, "extra": {"idsPropuestos": []}}]
    dobles.aplicar(lote, tildadas, "Sergio")
    assert len(operaciones) == 2                              # la cuenta sin imputaciones no genera operaciones
    anula, guarda = operaciones
    assert "Anulada = 1" in anula[0] and anula[1][-3:] == (5, 6, 7)
    assert guarda[1] == (json.dumps([5, 6, 7]), 41, 61)


# ---- cierre en bloque de la ficha

def _tilde(i: int) -> dict:
    return {"idContacto": i, "extra": {"cumple": True, "evidencia": "access"}}


def test_cerrar_en_bloque_guarda_el_inventario_access_la_ficha_previa_y_el_historial(monkeypatch):
    operaciones: list = []
    monkeypatch.setattr(fichas, "execute_write_transaction", lambda ops: operaciones.extend(ops))
    contextos = {1: _ctx(1, "Sin ficha", saldo=-1.31), 2: _ctx(2, "Con ficha", saldo=0.0, fila={"Estado": "en-proceso", "InventarioFuentes": None, "Nota": "x"})}
    fichas.cerrar_en_bloque(100, contextos, [_tilde(1), _tilde(2)], CORTE, "Sergio")
    sqls = [o[0] for o in operaciones]
    assert sum(1 for s in sqls if s.startswith("INSERT INTO dbo.RevisionFichas")) == 1 and sum(1 for s in sqls if s.startswith("UPDATE dbo.RevisionFichas")) == 1
    insertar = next(o for o in operaciones if o[0].startswith("INSERT INTO dbo.RevisionFichas"))
    assert "access" in insertar[1][1] and insertar[1][3] == CORTE and insertar[1][4] == -1.31
    previas = [json.loads(o[1][0]).get("previa") for o in operaciones if o[0].startswith("UPDATE dbo.AuditoriaCorreccionesCuentas")]
    assert previas[0] is None and previas[1]["Estado"] == "en-proceso"
    hist = [json.loads(o[1][1]) for o in operaciones if "AuditoriaRevisionesHistorial" in o[0]]
    assert all(h["estado"] == "cerrada" and h["lote"] == 100 and h["evidencia"] == "access" for h in hist)


def test_cerrar_en_bloque_rechaza_una_cuenta_que_ya_no_cumple(monkeypatch):
    monkeypatch.setattr(fichas, "execute_write_transaction", lambda ops: pytest.fail("no debe escribir"))
    contextos = {1: _ctx(1, "Cambió", criterios={"pagos_pendientes": 3, "pagos_importe_pendiente": 99.0})}
    with pytest.raises(fichas.FichaError) as e:
        fichas.cerrar_en_bloque(100, contextos, [_tilde(1)], CORTE, "Sergio")
    assert e.value.codigo == 409


def test_revertir_el_cierre_restaura_la_ficha_previa_o_vuelve_a_pendiente(monkeypatch):
    operaciones: list = []
    monkeypatch.setattr(fichas, "execute_write_transaction", lambda ops: operaciones.extend(ops))
    previa = {"Estado": "en-proceso", "InventarioFuentes": None, "Nota": "x", "PreguntaBloqueante": None, "Corte": None, "SaldoAlCierre": None,
              "Moneda": None, "MotivoExcepcion": None, "UsuarioCierre": None, "FechaCierre": None}
    fichas.revertir_cierre_en_bloque(100, [{"idContacto": 1, "extra": {"previa": None}}, {"idContacto": 2, "extra": {"previa": previa}}], "Sergio")
    restaurar = [o for o in operaciones if o[0].startswith("UPDATE dbo.RevisionFichas")]
    assert "Estado = 'pendiente'" in restaurar[0][0]
    assert restaurar[1][1][0] == "en-proceso" and restaurar[1][1][2] == "x"


# ---- T042: imputaciones de tarjeta duplicadas que el FIFO no reemplaza

def test_las_imputaciones_de_tarjeta_que_sobran_se_suman_al_detalle_de_la_regla_sin_repetir_ids():
    por_cuenta = {61: {"ids": [5, 6], "pagos": 1, "importe": 100.0}}
    r = dobles.combinar_tarjetas_duplicadas(por_cuenta, {61: {"ids": [6, 7], "importe": 40.0}, 282: {"ids": [9], "importe": 1270.5}})
    assert r[61]["ids"] == [5, 6, 7] and r[61]["importe"] == 140.0
    assert r[282] == {"ids": [9], "pagos": 0, "importe": 1270.5}
    assert por_cuenta[61]["ids"] == [5, 6]                      # no modifica lo que recibe
    assert dobles.combinar_tarjetas_duplicadas({}, {})  == {}
