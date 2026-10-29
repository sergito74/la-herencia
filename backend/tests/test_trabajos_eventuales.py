from decimal import Decimal
from pathlib import Path
import pytest
from pydantic import ValidationError
from src.features.trabajos_eventuales import repository as r
from src.features.trabajos_eventuales.schemas import TrabajoInput
from scripts.trabajos_eventuales_045 import leer_planilla,FUENTE


def test_medio_dia_y_redondeo():
    assert r.total_trabajo("0.5",10000,1000)==Decimal("6000.00")
    assert r.total_trabajo(1,"67824.25",21000,"0.75")==Decimal("88825.00")


@pytest.mark.parametrize("importe,usado,contacto,restante", [(0,0,1,100),(-1,0,1,100),(101,0,1,100),(60,50,1,100),(10,0,2,100)])
def test_limites_en_ambos_extremos(importe,usado,contacto,restante):
    with pytest.raises(ValueError):
        r.validar_vinculo({"idContacto":1,"sinVincular":restante},{"idContacto":contacto,"neto":100},importe,usado)


def test_vinculo_parcial_valido():
    r.validar_vinculo({"idContacto":1,"sinVincular":100},{"idContacto":1,"neto":100},60,20)


def test_edicion_protege_vinculos():
    datos=TrabajoInput(idContacto=1,fecha="2026-10-29",descripcion="Labor",dias=1,jornal=100)
    with pytest.raises(ValueError):r.validar_edicion({"vinculado":80,"idContacto":1},datos,70)
    otro=datos.model_copy(update={"idContacto":2})
    with pytest.raises(ValueError):r.validar_edicion({"vinculado":80,"idContacto":1},otro,100)


@pytest.mark.parametrize("cambio", [{"descripcion":"  "},{"dias":0},{"jornal":-1},{"viaticos":-1},{"dias":"0.00001"},{"jornal":"1.001"}])
def test_valida_entrada(cambio):
    with pytest.raises(ValidationError):
        TrabajoInput(**({"idContacto":1,"fecha":"2026-10-29","descripcion":"Labor","dias":1,"jornal":100}|cambio))


def test_fuente_real_sin_modificar():
    if not FUENTE.exists():pytest.skip("Planilla local no disponible")
    registros,hojas=leer_planilla(FUENTE)
    assert len(registros)==78
    assert sum(r["total"] for r in registros)==Decimal("2500558")
    assert len({r["cuit"] for r in registros})==8
    assert all(r["estado"]=="Pagado" for r in registros)
    assert sum(r["redondeo"]!=0 for r in registros)==5
    assert sum(r["total"]==0 for r in registros)==1
    assert len({r["origen"] for r in registros})==75
    assert "Detalles" in hojas and "Hoja1" in hojas
