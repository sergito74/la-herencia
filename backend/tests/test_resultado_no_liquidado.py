"""20/11/2026: grano cosechado y no liquidado (silo fusible de la hacienda)."""
from src.features.resultado_cultivo import formularios_access as fa


def _bloque(monkeypatch, terminada):
    monkeypatch.setattr(fa, "liquidacion_terminada", lambda *a: {"terminada": terminada, "fecha": None, "motivo": None})
    return fa._bloque_no_liquidado(1, 24, 10, 104281, 76261, 1243017.89, 1062.13, 5580751.52, 3994.81, 19525249.10, 13805.0)


def test_estimado_mientras_no_termina_la_liquidacion(monkeypatch):
    b = _bloque(monkeypatch, False)
    assert b["noLiquidado"]["kg"] == 28020 and b["noLiquidado"]["estado"] == "estimado"
    assert b["margenRealizado"] == {"pesos": -4337733.63, "dolares": -2932.68}


def test_al_terminar_queda_como_consumo_de_la_hacienda(monkeypatch):
    assert _bloque(monkeypatch, True)["noLiquidado"]["estado"] == "consumoHacienda"


def test_sin_sobrante_no_hay_estado(monkeypatch):
    monkeypatch.setattr(fa, "liquidacion_terminada", lambda *a: {"terminada": False, "fecha": None, "motivo": None})
    assert fa._bloque_no_liquidado(1, 24, 10, 1000, 1000, 1, 1, 0, 0, 1, 1)["noLiquidado"]["estado"] is None


def test_precio_de_mercado_menos_gastos(monkeypatch):
    from datetime import date
    from src.features.resultado_cultivo import precio_mercado as pm
    monkeypatch.setattr(pm, "pizarra", lambda prod, f: {"fecha": date(2026, 5, 15), "pesos": 249500.0})
    monkeypatch.setattr(pm, "_bna_dia_habil_anterior", lambda f: 1382.0)
    monkeypatch.setattr(pm, "porcentaje_gastos_comercializacion", lambda c: {"porcentaje": 0.1728, "base": "Maiz"})
    p = pm.precio_neto_mercado("Maiz", date(2026, 5, 15))
    assert p["netoPesosTn"] == round(249500 * 0.8272, 2) and p["netoDolaresTn"] == round(249500 / 1382 * 0.8272, 2)
    assert pm.precio_neto_mercado("Avena", date(2026, 5, 15)) is None  # sin pizarra en Rosario: no se inventa precio
