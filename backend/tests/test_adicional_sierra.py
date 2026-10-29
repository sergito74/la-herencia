from decimal import Decimal
import pytest
from src.features.remuneraciones.adicional import calcular,multiplo_cinco


def test_formula_y_redondeo_al_multiplo_mas_cercano():
    assert multiplo_cinco("12.5")==15
    assert multiplo_cinco("12.49")==10
    r=calcular(1396407)
    assert r["adicional"]==418920
    assert r["feriados"]==118695
    assert r["totalAdicional"]==537700
    assert r["totalACobrar"]==1934107
    assert calcular(1396407)["redondeo"]==85


def test_reproduce_fila_90_planilla():
    r=calcular("1333031.00")
    assert r["adicional"]==399910 and r["feriados"]==113310
    assert r["totalAdicional"]==513300


def test_no_acepta_total_negativo():
    with pytest.raises(ValueError):calcular(-1)
    assert calcular(0)["totalAdicional"]==0


def test_base_excluye_bonificacion_ya_registrada(monkeypatch):
    from src.features.remuneraciones import adicional as a
    def leer(sql,params):
        if "AS cuil" in sql:
            assert "-ISNULL(r.[Bonificacion adicional],0) AS neto" in sql
            return {"idContacto":374,"cuil":"20132391670","periodo":"Octubre 2026","neto":1000,"registrado":400}
        return None
    monkeypatch.setattr(a,"fetch_one",leer)
    r=a.obtener(123)
    assert r["netoRecibo"]==1000 and r["totalAdicional"]==400
    assert r["totalACobrar"]==1400



def test_adicional_historico_separado_no_se_duplica(monkeypatch):
    from src.features.remuneraciones import adicional as a
    def leer(sql,params):
        if "AS cuil" in sql:
            return {"idContacto":374,"cuil":"20132391670","periodo":"Agosto 2026","neto":1333031,"registrado":0}
        if "[Periodo liquidado]=?" in sql:
            return {"id":99,"importe":513300}
        return None
    monkeypatch.setattr(a,"fetch_one",leer)
    dato=a.obtener(1)
    assert dato["adicionalSeparado"]==99 and dato["puedeGuardar"] is False
    monkeypatch.setattr(a,"execute_write",lambda *a:pytest.fail("No debe escribir"))
    with pytest.raises(ValueError,match="ya está registrado"):
        a.guardar.__wrapped__(1,"prueba")



def test_guardar_actualiza_una_bonificacion_sin_otro_sueldo(monkeypatch):
    from src.features.remuneraciones import adicional as a
    from src.features.trabajos_eventuales import repository as t
    from src.features.auditoria_cuentas import bimonetaria
    dato={"idSalario":1,"periodo":"Octubre 2026","registrado":0,"puedeGuardar":True,**a.calcular(1396407)}
    monkeypatch.setattr(a,"obtener",lambda *x:dato)
    monkeypatch.setattr(a,"fetch_one",lambda sql,p: {"importe":0} if "SUM(Importe)" in sql else None)
    escritos=[]
    monkeypatch.setattr(a,"execute_write",lambda sql,p:escritos.append((sql,p)))
    monkeypatch.setattr(t,"auditar",lambda *a:None)
    monkeypatch.setattr(bimonetaria,"invalidar",lambda:None)
    a.guardar.__wrapped__(1,"prueba")
    sueldo=[x for x in escritos if "dbo.Remuneraciones SET" in x[0]]
    assert len(sueldo)==1 and sueldo[0][1]==(537700.0,1)
    assert not any("INSERT INTO dbo.Remuneraciones " in sql for sql,p in escritos)
