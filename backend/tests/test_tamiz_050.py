"""Tamiz por rubro (050): cada renglón decide solo, con la prioridad acordada."""

from __future__ import annotations

from src.features.imputacion import tamiz

HERB, FUMIG, VIATICOS, ANALISIS, FLETE_INS, FINANC, SILO, SEGURO = 1, 2, 3, 4, 5, 6, 7, 8
REGLAS = {
    HERB: {"destino": "CultivoStock", "idParte": 3, "regla": None},
    FUMIG: {"destino": "Cultivo", "idParte": 4, "regla": None},
    VIATICOS: {"destino": "Estructura", "idParte": None, "regla": None},
    ANALISIS: {"destino": "Depende", "idParte": None, "regla": "AnalisisLaboratorio"},
    FLETE_INS: {"destino": "CultivoStock", "idParte": 6, "regla": "FleteInsumo"},
    FINANC: {"destino": "Depende", "idParte": None, "regla": "Financiamiento"},
    SILO: {"destino": "Depende", "idParte": None, "regla": "SegunUsoOrden"},
    SEGURO: {"destino": "Cultivo", "idParte": 7, "regla": None},
}
SIN_CTX = {"particular": None, "tieneInsumos": False}


def _r(id_, rubro, producto="x", formulado=None, cultivo=None, campania=None, cantidad=1, precio=100):
    return {"idDetalleCompra": id_, "idRubro": rubro, "producto": producto, "idFormulado": formulado,
            "idCultivo": cultivo, "idCampania": campania, "cantidad": cantidad, "precio": precio}


def test_factura_mixta_cada_renglon_decide_solo():
    renglones = [_r(1, HERB, "Glifosato", formulado=10), _r(2, VIATICOS, "Nafta"), _r(3, FUMIG, cultivo=3, campania=32)]
    ctx = tamiz._contexto(renglones, REGLAS)
    res = [tamiz.clasificar_renglon(r, REGLAS, [], ctx) for r in renglones]
    assert [x["destino"] for x in res] == ["CultivoStock", "Estructura", "Cultivo"]
    assert all(x["estado"] == "Aprobada" for x in res)
    assert res[2]["idCultivo"] == 3 and res[2]["origen"] == "Manual"


def test_insumo_con_imputacion_manual_igual_va_a_stock():
    res = tamiz.clasificar_renglon(_r(1, HERB, formulado=10, cultivo=3, campania=32), REGLAS, [], SIN_CTX)
    assert res["destino"] == "CultivoStock" and res["idCultivo"] is None


def test_insumo_sin_producto_va_a_revision():
    res = tamiz.clasificar_renglon(_r(1, HERB, "GLIFO 20L"), REGLAS, [], SIN_CTX)
    assert res["estado"] == "Pendiente" and "catálogo" in res["motivo"]


def test_labor_sin_campania_o_con_no_aplica_va_a_revision():
    res = tamiz.clasificar_renglon(_r(1, FUMIG, cultivo=3, campania=20), REGLAS, [], SIN_CTX)
    assert res["estado"] == "Pendiente" and res["motivo"] == "Falta campaña"


def test_rubro_general_con_campania_cargada_se_contradice():
    res = tamiz.clasificar_renglon(_r(1, VIATICOS, cultivo=3, campania=32), REGLAS, [], SIN_CTX)
    assert res["estado"] == "Pendiente"


def test_rubro_sin_regla_va_a_revision():
    res = tamiz.clasificar_renglon(_r(1, 999), REGLAS, [], SIN_CTX)
    assert res["estado"] == "Pendiente" and res["destino"] is None


def test_regla_por_producto_gana_sobre_rubro():
    reglas_prod = [{"idFormulado": 10, "texto": None, "destino": "Ganaderia", "idParte": None}]
    res = tamiz.clasificar_renglon(_r(1, HERB, formulado=10), REGLAS, reglas_prod, SIN_CTX)
    assert res["destino"] == "Ganaderia" and res["origen"] == "Producto"


def test_analisis_laboratorio_por_palabra_clave():
    suelo = tamiz.clasificar_renglon(_r(1, ANALISIS, "Análisis de suelo", cultivo=1, campania=32), REGLAS, [], SIN_CTX)
    hacienda = tamiz.clasificar_renglon(_r(2, ANALISIS, "Brucelosis rodeo"), REGLAS, [], SIN_CTX)
    otro = tamiz.clasificar_renglon(_r(3, ANALISIS, "Análisis varios"), REGLAS, [], SIN_CTX)
    assert (suelo["destino"], suelo["idParte"]) == ("Cultivo", 8)
    assert hacienda["destino"] == "Ganaderia"
    assert otro["estado"] == "Pendiente"


def test_flete_de_insumos_acompania_a_los_insumos_de_la_factura():
    renglones = [_r(1, HERB, formulado=10), _r(2, FLETE_INS, "Flete")]
    ctx = tamiz._contexto(renglones, REGLAS)
    assert ctx["tieneInsumos"] is True
    res = tamiz.clasificar_renglon(renglones[1], REGLAS, [], ctx)
    assert res["estado"] == "Aprobada" and res["idParte"] == 6


def test_flete_aparte_queda_pendiente():
    res = tamiz.clasificar_renglon(_r(1, FLETE_INS, "Flete"), REGLAS, [], SIN_CTX)
    assert res["estado"] == "Pendiente"


def test_financiamiento_sin_insumo_va_a_financiero_y_silobolsa_segun_uso():
    assert tamiz.clasificar_renglon(_r(1, FINANC), REGLAS, [], SIN_CTX)["destino"] == "Financiero"
    silo = tamiz.clasificar_renglon(_r(2, SILO, "Silobolsa 9 pies"), REGLAS, [], SIN_CTX)
    assert silo["destino"] == "CultivoStock" and silo["estado"] == "Aprobada"


def test_compra_particular_total_no_se_imputa():
    renglones = [_r(1, HERB, formulado=10, precio=100), _r(2, VIATICOS, "Compra particular", precio=-100)]
    ctx = tamiz._contexto(renglones, REGLAS)
    assert ctx["particular"] == "total"
    assert all(tamiz.clasificar_renglon(r, REGLAS, [], ctx)["destino"] == "NoImputa" for r in renglones)


def test_tamizar_compra_fuera_de_alcance_no_hace_nada(monkeypatch):
    monkeypatch.setattr(tamiz.repo, "compra_en_alcance", lambda i: False)
    assert tamiz.tamizar_compra(5) == []


def test_tamizar_compra_guarda_una_clasificacion_por_renglon(monkeypatch):
    guardado = []
    monkeypatch.setattr(tamiz.repo, "compra_en_alcance", lambda i: True)
    monkeypatch.setattr(tamiz.repo, "renglones_de_compra", lambda i: [_r(1, HERB, formulado=10), _r(2, SEGURO)])
    monkeypatch.setattr(tamiz.repo, "reglas_rubro", lambda: REGLAS)
    monkeypatch.setattr(tamiz.repo, "reglas_producto", lambda: [])
    monkeypatch.setattr(tamiz.repo, "guardar_clasificaciones", lambda c, usuario=None: guardado.extend(c))
    res = tamiz.tamizar_compra(5)
    assert len(res) == 2 and len(guardado) == 2
    assert res[1]["estado"] == "Pendiente"


def test_linea_particular_resta_en_el_destino_del_resto_de_la_factura():
    renglones = [_r(1, VIATICOS, "Almacen", precio=300), _r(2, VIATICOS, "Compra particular", precio=-100)]
    ctx = tamiz._contexto(renglones, REGLAS)
    assert ctx["particular"] == "parcial"
    res = [tamiz.clasificar_renglon(r, REGLAS, [], ctx) for r in renglones]
    assert [x["destino"] for x in res] == ["Estructura", "Estructura"]
    assert all(x["estado"] == "Aprobada" for x in res)


def test_linea_particular_con_renglones_de_cultivo_va_a_revision():
    renglones = [_r(1, FUMIG, cultivo=3, campania=32, precio=300), _r(2, VIATICOS, "Gasto particular", precio=-100)]
    ctx = tamiz._contexto(renglones, REGLAS)
    assert tamiz.clasificar_renglon(renglones[1], REGLAS, [], ctx)["estado"] == "Pendiente"


def test_error_del_tamiz_no_impide_guardar_la_compra(monkeypatch):
    def falla(i):
        raise RuntimeError("base caída")
    monkeypatch.setattr(tamiz.repo, "compra_en_alcance", falla)
    tamiz.tamizar_al_guardar(5)  # no levanta


def test_correccion_a_cultivo_exige_campania_real(monkeypatch):
    import pytest
    with pytest.raises(ValueError):
        tamiz.corregir_renglon(1, "Cultivo", 4, 3, 20, False, None)
    guardado = []
    monkeypatch.setattr(tamiz.repo, "guardar_clasificaciones", lambda c, u=None: guardado.extend(c))
    res = tamiz.corregir_renglon(1, "Cultivo", 4, 3, 32, False, "sergio")
    assert res["estado"] == "Aprobada" and guardado[0]["origen"] == "Manual"


def test_campania_vigente_por_anio_agricola():
    from datetime import date
    assert tamiz.campania_vigente(date(2026, 8, 15)) == "2026/2027"
    assert tamiz.campania_vigente(date(2026, 3, 10)) == "2025/2026"


def test_labor_sin_campania_propone_la_vigente_pero_queda_pendiente():
    ctx = {**SIN_CTX, "campaniaVigente": 32, "campaniaVigenteNombre": "2026/2027"}
    res = tamiz.clasificar_renglon(_r(1, FUMIG, cultivo=3), REGLAS, [], ctx)
    assert res["estado"] == "Pendiente" and res["idCampania"] == 32 and "2026/2027" in res["motivo"]
