"""Asociación de devoluciones de ARCA con certificados RETIVA (24/11/2026)."""
from datetime import date

from src.features.ventas_granos import retenciones_iva as R


def _c(i, imp, f=date(2024, 12, 27)):
    return {"id": i, "aDevolver": imp, "fecha": f}


def test_grupo_exacto_de_siete():
    certs = [_c(i, v) for i, v in enumerate([817743.32, 527.28, 92476.56, 203983.69, 202907.21, 127082.57, 294801.94])]
    grupo, exacto = R._grupo(certs + [_c(99, 5091.0)], 1739522.57, date(2025, 2, 27))
    assert exacto and sorted(c["id"] for c in grupo) == list(range(7))


def test_grupo_con_retencion_sin_certificado():
    certs = [_c(1, 25929.57, date(2020, 5, 26)), _c(2, 81313.19, date(2020, 5, 28)), _c(3, 2222.53, date(2020, 5, 28)),
             _c(4, 323.32, date(2020, 6, 5))]
    grupo, exacto = R._grupo(certs, 111112.96, date(2020, 7, 22))
    assert not exacto and len(grupo) == 4


def test_no_asocia_lejos():
    assert R._grupo([_c(1, 1000.0)], 50000.0, date(2025, 2, 1)) is None
