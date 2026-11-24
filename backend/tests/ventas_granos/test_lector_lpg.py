"""Lector de LPG (24/11/2026) con el texto real de dos liquidaciones de Cargill y su certificado de IVA."""
from pathlib import Path

from src.features.ventas_granos import lector_lpg as L
from src.features.ventas_granos.repository import calcular_totales

F = Path(__file__).parent / "fixtures"


def _t(n):
    return (F / n).read_text(encoding="utf-8")


def test_lee_lpg_maiz():
    d = L.leer_lpg(_t("lpg_cargill_maiz.txt"))
    assert d["coe"] == "330132967323" and d["cuitComprador"] == "30506792165"
    assert (d["precioTn"], d["fleteTn"], d["factor"], d["kilos"], d["alicuotaIVA"]) == (267476.0, 65682.835, 100.0, 25704.0, 10.5)
    assert [(x["detalle"], x["baseCalculo"], x["alicuota"]) for x in d["deducciones"]] == [
        ("Honorarios Laboratorio", 26413.62, 21.0), ("Per Iva Rg3337 Gral", 792.53, 0.0)]
    assert d["netoImpreso"] == 5698761.96


def test_etiqueta_partida_redondeo():
    d = L.leer_lpg(_t("lpg_cargill_redondeo.txt"))
    assert [x["detalle"] for x in d["deducciones"]] == ["Diferencia Por Redondeo", "Honorarios Laboratorio"]


def test_cierra_al_centavo_con_redondeo():
    d = L.leer_lpg(_t("lpg_cargill_maiz.txt"))
    cab = {"precioUnitario": d["precioTn"], "factor": d["factor"], "flete": d["fleteTn"], "cantidadVendida": d["kilos"],
           "alicuotaIVA": d["alicuotaIVA"]}
    ded = [{k: v for k, v in x.items() if not k.startswith("_")} for x in d["deducciones"]]
    sub = calcular_totales(cab, [], ded)["subTotal"]
    aj = [{"concepto": "Redondeo LPG", "importe": round(d["subtotal"] - sub, 4)}]
    assert abs(calcular_totales(cab, aj, ded)["importeNetoAPercibir"] - d["netoImpreso"]) <= L.TOLERANCIA


def test_certificado_iva():
    c = L.leer_certificado(_t("cert_iva_cargill.txt"))
    assert c == {"nro": "09601-2026-212205", "coe": "330132967323", "importe": 259344.58, "cuitAgente": "30506792165"}


def test_campania_estimada():
    from datetime import date
    assert L.campania("Maiz", date(2026, 11, 21)) == "2025/2026"
    assert L.campania("Trigo", date(2026, 12, 10)) == "2026/2027"
    assert L.campania("Trigo", date(2027, 1, 10)) == "2026/2027"
    assert L.campania("Maiz", date(2026, 11, 21), "2024/2025") == "2024/2025"
