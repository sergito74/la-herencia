"""052 FR-009 / R4: cabezas y kg según la unidad de medida."""

from src.features.ganaderia.categorias import cabezas_y_kg


def test_kilos_cantidad_kg_peso_total_cabezas():
    # 0003-00010318 (PDF de la liquidación): 1 vaca de 440 kg por renglón
    r = cabezas_y_kg(440, "Kilos", 1, 450)
    assert (r["cabezas"], r["kg"], r["kgEstimado"]) == (1, 440, False)


def test_unidades_cantidad_cabezas_peso_total_kg():
    r = cabezas_y_kg(20, "Unidades", 6790, 190)
    assert (r["cabezas"], r["kg"], r["kgEstimado"]) == (20, 6790, False)


def test_unidades_sin_kg_estima_con_peso_tipico():
    r = cabezas_y_kg(19, "Unidades", None, 400)
    assert (r["cabezas"], r["kg"], r["kgEstimado"]) == (19, 7600, True)


def test_pesos_no_es_hacienda():
    assert cabezas_y_kg(1, "Pesos", 0, 450)["esHacienda"] is False


def test_correccion_negativa_conserva_signo():
    r = cabezas_y_kg(-8788, "Kilos", -52, 200)
    assert (r["cabezas"], r["kg"]) == (-52, -8788)


def test_unidades_cargadas_al_reves():
    r = cabezas_y_kg(170, "Unidades", 1, 190)
    assert r["cabezas"] == 1 and r["kg"] == 170 and not r["kgEstimado"]
