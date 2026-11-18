from datetime import date

from src.features.ordenes import planilla_matias as P


def test_potreros_a_lotes():
    plan = ["1B1", "3C", "6", "6A", "6B", "6C", "8A", "3AL", "3AB"]
    assert P.potreros_a_lotes("1B", plan) == ["1B1"]
    assert P.potreros_a_lotes("6/6A", plan) == ["6", "6A"]
    assert P.potreros_a_lotes("6BC", plan) == ["6B", "6C"]
    assert P.potreros_a_lotes("3A LOMA", plan) == ["3AL"]
    assert P.potreros_a_lotes("3A Bajo", plan) == ["3AB"]
    assert P.potreros_a_lotes("9B", plan) == []


def test_productos_por_principio_activo_y_concentracion():
    c = P.producto_coincide
    assert c(P.PRODUCTOS["GLIFOSATO"], "POWER PLUS II", "GLIFOSATO")
    assert not c(P.PRODUCTOS["BIFENTRIN 10%"], "BIFENTRIN 25 SIGMA", "BIFENTRIN")
    assert c(P.PRODUCTOS["BIFENTRIN 10%"], "BIFENTRIN ARN EBC", "BIFENTRIN")
    assert not c(P.PRODUCTOS["FLUMIOXAZIN"], "FIERCE RM", "FLUMIOXAZIN + PIROXASULFONE")
    assert c(P.PRODUCTOS["SULFENTRAZONE"], "LIDER 50% EBC", "SULFENTRAZONE")
    assert c(P.PRODUCTOS["AMISTAR XTRA"], "AZOXY PRO", "CYPROCONAZOLE + AZOXISTROBINA")
    assert c(P.PRODUCTOS["LAMBDA 25%"], "LAMBDA 25 EBC", "LAMBDACIALOTRINA 25")
    assert c(P.PRODUCTOS["CRIPTON XPRO"], "CRIPTON XPRO", "BIXAFEN + PROTIOCONAZOLE + TRIFLOXISTROBIN")


def test_fifo_entre_productos_y_faltante():
    cands = [{"idProducto": 2, "disponible": 50, "desde": date(2026, 5, 1)}, {"idProducto": 1, "disponible": 30, "desde": date(2025, 9, 1)}]
    assert P.asignar_fifo(60, cands) == ([(1, 30), (2, 30)], 0)
    assert P.asignar_fifo(100, cands) == ([(1, 30), (2, 50)], 20)


def test_planilla_que_no_cierra_no_se_carga():
    filas = [{"fila": 1, "potrero": "1B", "cultivo": "GR", "sup": 2, "producto": "PULV", "dosis": 1, "total": 20, "momento": "G Post"},
             {"fila": 2, "potrero": "1B", "cultivo": "GR", "sup": 2, "producto": "CLETODIM", "dosis": 0.8, "total": 16, "momento": "G Post"},
             {"fila": 3, "potrero": "1B", "cultivo": "GR", "sup": 3, "producto": "PULV", "dosis": 1, "total": 3, "momento": "G Post"}]
    p = P.problemas_de_planilla(filas)
    assert any("16" in x for x in p) and any("más de una vez" in x for x in p)
    assert P.problemas_de_planilla([filas[0], {**filas[1], "total": 1.6}]) == []


def test_soja_primera_o_segunda_por_momento():
    assert P.cultivo_de("Sj", "S1 Prem") == "Soja primera" and P.cultivo_de("Sj", "S2 Post") == "Soja segunda"
    assert P.cultivo_de("Mz Dif", "MzDif prem") == "Maiz diferido"
