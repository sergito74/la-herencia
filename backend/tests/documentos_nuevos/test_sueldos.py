from contextlib import nullcontext
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest

from src.features.documentos_nuevos.lectores import sueldos

TEXTO = """C.U.I.T. EMPRESA:30-71211460-2
Mensual 10 2026 APELLIDO NOMBRE 00000001 $ 1.000,00
20-11111111-1 /
0010 SUELDO MENSUAL 31,00 1.000,00 1.000,00
0123 DIA GREMIO 1,00 100,00
0300 JUBILACION 11,00 1.100,00 -121,00
SUELDO NETO $ 979,00
"""


def test_lee_sueldo_con_gremio_y_deducciones():
    r = sueldos.leer_pagina(TEXTO)
    assert r["periodo"] == "Octubre 2026"
    assert r["fecha"] == datetime(2026, 10, 31)
    assert r["valores"]["Dia Gremio"] == Decimal("100")
    assert r["valores"]["Jubilacion"] == Decimal("121")
    assert r["neto"] == Decimal("979")


@pytest.mark.parametrize("texto", [TEXTO.replace("979,00", "979,01"), TEXTO.replace("0123", "9999"),
                                  TEXTO.replace("-121,00", "121,00"), TEXTO.replace("30-71211460-2", "30-00000000-0")])
def test_no_carga_con_diferencias(texto):
    with pytest.raises(ValueError):
        sueldos.leer_pagina(texto)


def test_carga_paquete_real_y_reintento_sin_duplicar(tmp_path, monkeypatch):
    ruta = Path(__file__).resolve().parents[3] / "backups/sueldos-octubre-20261029/RECIBOS OCT26.pdf"
    if not ruta.exists():
        pytest.skip("PDF local no disponible")
    pdf = ruta.read_bytes()
    monkeypatch.setattr(sueldos, "reconciliation_transaction", nullcontext)
    monkeypatch.setattr(sueldos.remuneraciones, "CARPETA_RECIBOS", str(tmp_path))
    filas = []
    def consultar(sql, params):
        if "dbo.Contactos" in sql:
            return [{"id": 374 if params[0] == "20132391670" else 375,
                     "nombre": "Marcelo Sierra" if params[0] == "20132391670" else "Sergio Giamberardini"}]
        return [f for f in filas if f["contacto"] == params[0]]
    monkeypatch.setattr(sueldos, "fetch_all", consultar)
    def insertar(sql, params):
        columnas = list(sueldos.leer(pdf)[len(filas)]["valores"])
        assert "INSERT INTO dbo.Remuneraciones" in sql
        assert "Dia Gremio" in columnas if not filas else True
        f = {"id": len(filas)+1, "contacto": params[0], "neto": Decimal("1396407") if not filas else Decimal("1800000")}
        filas.append(f)
        return f["id"]
    monkeypatch.setattr(sueldos, "execute_insert_returning_id", insertar)
    r = sueldos.cargar(pdf, str(ruta))
    assert r["estado"] == "cargado_solo" and r["total"] == Decimal("3196407")
    archivos = sorted(tmp_path.glob("2026/*.pdf"))
    assert len(archivos) == 2
    assert [sueldos.leer(a.read_bytes())[0]["cuil"] for a in archivos] == ["20132391670", "23238598109"]
    assert sueldos.cargar(pdf, str(ruta))["estado"] == "ya_estaba"
    assert len(filas) == 2
    filas[0]["neto"] += 1
    with pytest.raises(ValueError, match="distinta"):
        sueldos.cargar(pdf, str(ruta))


def test_lee_sueldo_casas_particulares_irma_miranda():
    texto_miranda = """RECIBO DE REMUNERACIONES RECIBO DE REMUNERACIONES
IGLINA ALBINA LUCILA IGLINA ALBINA LUCILA
HALE - PARCELA 280AD - (6550) BOLIVAR HALE - PARCELA 280AD - (6550) BOLIVAR
C.U.I.T.: 27-04862094-4 C.U.I.T.: 27-04862094-4
Período: Mensual 05/2026 Período: Mensual 05/2026
Legajo Apellido y Nombres C.U.I.L. Fecha Ing. Sector Sueldo/Jrnal
00001 MIRANDA IRMA DELIA 27-14401702-7 01/12/2011 $3.348,33
ULTIMO DEPOSITO LIQUIDACION
Fecha Período Banco Categoría Función
/ / CAT-5 EMP.DOM.CATEG.5
Cod CONCEPTO Unidades Hab.C/Desc. Hab.S/Desc. Deducciones Cod CONCEPTO
0017 HORAS TRABAJADAS 60,00 200.899,80 0017 HORAS TRABAJADAS 60,00 200.899,80
0154 ANTIG. EMPL.CAS.PART 4,00 8.035,99 0154 ANTIG. EMPL.CAS.PART 4,00 8.035,99
0401 SUMA NO REMUN. CASAS PART 11.500,00 0401 SUMA NO REMUN. CASAS PART 11.500,00
0800 DIFERENCIA REDONDEO 0,21 0800 DIFERENCIA REDONDEO 0,21
TOTALES 208.935,79 11.500,21 TOTALES 208.935,79 11.500,21
NETO 220.436,00 NETO 220.436,00
Lugar y Fecha de Pago: BOLIVAR, 31/05/2026
"""
    assert sueldos.reconoce(texto_miranda)
    r = sueldos.leer_pagina(texto_miranda)
    assert r["cuil"] == "27144017027"
    assert r["nombre"] == "MIRANDA IRMA DELIA"
    assert r["periodo"] == "Mayo 2026"
    assert r["fecha"] == datetime(2026, 5, 31)
    assert r["valores"]["Sueldo basico"] == Decimal("200899.80")
    assert r["valores"]["Antiguedad"] == Decimal("8035.99")
    assert r["valores"]["Ajuste No Remunerativo"] == Decimal("11500.00")
    assert r["valores"]["Redondeo"] == Decimal("0.21")
    assert r["neto"] == Decimal("220436.00")
