"""052 FR-016: dólar de gestión único (sin base de datos)."""

from src.features.cotizaciones import dolar_gestion as dg


def _tc(_fecha):
    return 1000.0


def test_pesos_al_tc_de_gestion():
    assert dg.usd(150_000, "2026-11-25", "Pesos", tc_pesos_fn=_tc) == 150.0


def test_dolares_a_su_propio_tc():
    assert dg.usd(150_000, "2026-11-25", "Dolares", tc_comprobante=1500, tc_pesos_fn=_tc) == 100.0


def test_ajusta_tc_es_cero():
    assert dg.usd(150_000, "2026-11-25", "Pesos", ajusta_tc=True, tc_pesos_fn=_tc) == 0.0


def test_sin_cotizacion_no_inventa():
    assert dg.usd(150_000, "2026-11-25", "Pesos", tc_pesos_fn=lambda f: None) is None


def test_sql_usa_dia_habil_anterior():
    sql = dg.sql_tc_pesos("c.Fecha")
    assert "_b.Fecha < CAST(c.Fecha AS date)" in sql and "Comp_Divisa > 0" in sql
