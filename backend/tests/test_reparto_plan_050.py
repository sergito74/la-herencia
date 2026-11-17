"""050 US4 (T033): reparto por superficie del plan agrícola."""

from src.features.imputacion import reparto_plan, tamiz
from src.features.imputacion.progresivo import fracciones_directo


def test_reparte_por_superficie_y_suma_al_centavo():
    assert reparto_plan.repartir(1_000_000, {1: 60, 2: 40}) == {1: 600_000.0, 2: 400_000.0}
    partes = reparto_plan.repartir(100, {1: 1, 2: 1, 3: 1})
    assert round(sum(partes.values()), 2) == 100 and partes[3] == 33.34


def test_fracciones_directo_sin_cultivo_reparte_sin_lote():
    t = {"destino": "Cultivo", "idCultivo": None, "idCampania": 50, "idParte": 8}
    fr = fracciones_directo(t, 1_000_000, None, {1: 60, 2: 40})
    assert [(f["idCultivo"], f["importe"]) for f in fr] == [(1, 600_000.0), (2, 400_000.0)]
    assert all(f["idCampania"] == 50 and "idLote" not in f for f in fr)


def _renglon():
    return {"idDetalleCompra": 1, "producto": "ASESORAMIENTO AGRONOMICO OCTUBRE", "idRubro": 10,
            "idCultivo": None, "idCampania": 50, "idFormulado": None}


def _ctx(superficie):
    return {"cultivos": {1: "Trigo", 2: "Soja primera"}, "cultivosPorCampania": {50: [1, 2]},
            "superficiePlan": {50: superficie}}


def test_tamiz_aprueba_reparto_con_plan():
    reglas = {10: {"destino": "Cultivo", "idParte": 8, "regla": None}}
    c = tamiz.clasificar_renglon(_renglon(), reglas, [], _ctx({1: 60, 2: 40}))
    assert c["estado"] == "Aprobada" and c["idCultivo"] is None and c["idCampania"] == 50 and "plan agrícola" in c["motivo"]


def test_plan_sin_superficie_va_a_revision():
    reglas = {10: {"destino": "Cultivo", "idParte": 8, "regla": None}}
    c = tamiz.clasificar_renglon(_renglon(), reglas, [], _ctx({}))
    assert c["estado"] == "Pendiente" and "plan agrícola" in c["motivo"]


def test_labor_de_contratista_no_se_reparte_por_plan():
    reglas = {10: {"destino": "Cultivo", "idParte": 4, "regla": None}}
    c = tamiz.clasificar_renglon(_renglon(), reglas, [], _ctx({1: 60, 2: 40}))
    assert c["estado"] == "Pendiente" and "Repartido" not in (c["motivo"] or "")


def test_doble_cultivo_trigo_soja_segunda_va_50_y_50():
    filas = [{"idLote": 1, "idCultivo": 8, "superficie": 40}, {"idLote": 1, "idCultivo": 4, "superficie": 40},
             {"idLote": 2, "idCultivo": 6, "superficie": 60}]
    assert reparto_plan.superficies_de_lotes(filas) == {8: 20.0, 4: 20.0, 6: 60.0}
