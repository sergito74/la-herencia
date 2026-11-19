from datetime import date

from src.features.tesoreria import inversiones as iv


def test_ejercicio_va_del_01_04_al_31_03():
    assert iv.ejercicio(date(2026, 3, 31)) == "2025/26"
    assert iv.ejercicio(date(2026, 4, 1)) == "2026/27"


def test_pares_conocidos_cierran():
    pfs = iv.plazos_fijos()
    galicia = next(p for p in pfs if p["cuenta"] == "Plazo fijo Galicia" and p["capital"] == 4500000)
    assert galicia["cobrado"] == 9257546.87 and galicia["vencimiento"] == "2024-08-14"
    assert {p["cobrado"] for p in pfs if p["constitucion"].startswith("2016")} == {219061.24, 224498.97}
    assert not [p for p in pfs if p["estado"] == "revisar"]
