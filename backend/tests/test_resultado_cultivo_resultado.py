"""Resultado por Cultivo/Campaña y consolidado de Campaña (resultado.py),
sin tocar la base real."""

from src.features.resultado_cultivo import resultado


def _stub_cultivo(idc, idcamp, **overrides):
    base = {
        "idCultivo": idc, "cultivo": f"Cultivo {idc}", "idCampania": idcamp, "campania": "2026/2027",
        "superficieSembrada": 10.0, "superficieCosechada": None, "superficiePicada": None, "rinde": None,
        "costoTotalPesos": 100.0, "costoTotalDolares": 10.0,
        "costoPorHectareaSembradaPesos": 10.0, "costoPorHectareaSembradaDolares": 1.0,
        "costoPorHectareaCosechadaPesos": None, "costoPorHectareaCosechadaDolares": None,
        "ventaNetaPesos": 150.0, "ventaNetaDolares": 15.0,
        "margenBrutoPesos": 50.0, "margenBrutoDolares": 5.0,
        "rentabilidadPesos": 0.5, "rentabilidadDolares": 0.5,
        "supCosechaEstimada": False, "advertenciaMargenNoRepresentativo": False,
    }
    base.update(overrides)
    return base


def test_resultado_campania_es_la_suma_de_sus_cultivos(monkeypatch):
    """FR-014/SC-004."""
    cultivos = [_stub_cultivo(1, 32), _stub_cultivo(2, 32, costoTotalPesos=200.0, ventaNetaPesos=300.0)]
    monkeypatch.setattr(resultado, "fetch_one", lambda sql, params: {"nombre": "2026/2027"})
    monkeypatch.setattr(resultado, "_cultivos_con_datos", lambda idcamp: [1, 2])
    monkeypatch.setattr(resultado, "resultado_cultivo", lambda idc, idcamp: cultivos[0] if idc == 1 else cultivos[1])
    sin_clasificar = {"montoPesos": 999.0, "montoDolares": 99.0, "motivo": "Sin clasificar"}
    monkeypatch.setattr(resultado, "costo_sin_clasificar", lambda idcamp: sin_clasificar)

    r = resultado.resultado_campania(32)
    assert r["costoTotalPesos"] == sum(c["costoTotalPesos"] for c in cultivos)
    assert r["ventaNetaPesos"] == sum(c["ventaNetaPesos"] for c in cultivos)
    assert r["margenBrutoPesos"] == r["ventaNetaPesos"] - r["costoTotalPesos"]
    assert "rinde" not in r
    assert r["costoSinClasificar"] == sin_clasificar
    assert r["costoTotalDolares"] == sum(c["costoTotalDolares"] for c in cultivos)


def test_resultado_campania_inexistente_falla(monkeypatch):
    monkeypatch.setattr(resultado, "fetch_one", lambda sql, params: None)
    try:
        resultado.resultado_campania(999)
        assert False, "debería haber lanzado ValueError"
    except ValueError:
        pass


def test_costo_por_hectarea_none_con_superficie_cero():
    assert resultado._costo_por_hectarea(100.0, 0.0) is None
    assert resultado._costo_por_hectarea(100.0, None) is None
    assert resultado._costo_por_hectarea(100.0, 10.0) == 10.0


def test_rinde_none_sin_superficie_cosechada(monkeypatch):
    monkeypatch.setattr(resultado, "fetch_one", lambda sql, params: {"nombre": "Soja"} if "Cultivos" in sql else ({"nombre": "2026/2027"} if "Campañas" in sql else None))
    monkeypatch.setattr(resultado, "detalle_costos", lambda idc, idcamp: [])
    monkeypatch.setattr(resultado, "superficie_sembrada", lambda idc, idcamp: 50.0)
    monkeypatch.setattr(resultado, "superficie_cosechada", lambda idc, idcamp: {"valor": None, "estimada": False})
    monkeypatch.setattr(resultado, "cantidad_cosechada", lambda idc, idcamp: 1000.0)
    monkeypatch.setattr(resultado, "venta_neta", lambda idc, idcamp: {"pesos": 0.0, "dolares": 0.0})

    r = resultado.resultado_cultivo(3, 32)
    assert r["rinde"] is None
    assert r["costoPorHectareaCosechadaPesos"] is None


def test_sup_cosecha_estimada_activa_el_flag(monkeypatch):
    monkeypatch.setattr(resultado, "fetch_one", lambda sql, params: {"nombre": "x"})
    monkeypatch.setattr(resultado, "detalle_costos", lambda idc, idcamp: [])
    monkeypatch.setattr(resultado, "superficie_sembrada", lambda idc, idcamp: 50.0)
    monkeypatch.setattr(resultado, "superficie_cosechada", lambda idc, idcamp: {"valor": 40.0, "estimada": True})
    monkeypatch.setattr(resultado, "cantidad_cosechada", lambda idc, idcamp: None)
    monkeypatch.setattr(resultado, "venta_neta", lambda idc, idcamp: {"pesos": 0.0, "dolares": 0.0})

    r = resultado.resultado_cultivo(3, 32)
    assert r["supCosechaEstimada"] is True


def test_advertencia_margen_no_representativo(monkeypatch):
    """FR-011: venta > 0 y costo < 20% de la venta."""
    monkeypatch.setattr(resultado, "fetch_one", lambda sql, params: {"nombre": "x"})
    monkeypatch.setattr(resultado, "detalle_costos", lambda idc, idcamp: [{"montoPesos": 5.0, "montoDolares": 0.0}])
    monkeypatch.setattr(resultado, "superficie_sembrada", lambda idc, idcamp: 10.0)
    monkeypatch.setattr(resultado, "superficie_cosechada", lambda idc, idcamp: {"valor": None, "estimada": False})
    monkeypatch.setattr(resultado, "cantidad_cosechada", lambda idc, idcamp: None)
    monkeypatch.setattr(resultado, "venta_neta", lambda idc, idcamp: {"pesos": 100.0, "dolares": 0.0})

    r = resultado.resultado_cultivo(3, 32)
    assert r["advertenciaMargenNoRepresentativo"] is True


def test_sin_advertencia_si_costo_supera_el_20_por_ciento(monkeypatch):
    monkeypatch.setattr(resultado, "fetch_one", lambda sql, params: {"nombre": "x"})
    monkeypatch.setattr(resultado, "detalle_costos", lambda idc, idcamp: [{"montoPesos": 30.0, "montoDolares": 0.0}])
    monkeypatch.setattr(resultado, "superficie_sembrada", lambda idc, idcamp: 10.0)
    monkeypatch.setattr(resultado, "superficie_cosechada", lambda idc, idcamp: {"valor": None, "estimada": False})
    monkeypatch.setattr(resultado, "cantidad_cosechada", lambda idc, idcamp: None)
    monkeypatch.setattr(resultado, "venta_neta", lambda idc, idcamp: {"pesos": 100.0, "dolares": 0.0})

    r = resultado.resultado_cultivo(3, 32)
    assert r["advertenciaMargenNoRepresentativo"] is False


def test_detalle_costos_suma_igual_al_costo_total(monkeypatch):
    """Regresión hallazgo /speckit-analyze: SUM(detalle_costos) == costoTotal."""
    lineas = [{"montoPesos": 10.0, "montoDolares": 1.0}, {"montoPesos": 20.0, "montoDolares": 2.0}]
    monkeypatch.setattr(resultado, "fetch_one", lambda sql, params: {"nombre": "x"})
    monkeypatch.setattr(resultado, "detalle_costos", lambda idc, idcamp: lineas)
    monkeypatch.setattr(resultado, "superficie_sembrada", lambda idc, idcamp: 10.0)
    monkeypatch.setattr(resultado, "superficie_cosechada", lambda idc, idcamp: {"valor": None, "estimada": False})
    monkeypatch.setattr(resultado, "cantidad_cosechada", lambda idc, idcamp: None)
    monkeypatch.setattr(resultado, "venta_neta", lambda idc, idcamp: {"pesos": 0.0, "dolares": 0.0})

    r = resultado.resultado_cultivo(3, 32)
    assert r["costoTotalPesos"] == sum(l["montoPesos"] for l in lineas)
    assert r["costoTotalDolares"] == sum(l["montoDolares"] for l in lineas)


def test_costo_dolares_faltante_se_declara_incompleto(monkeypatch):
    monkeypatch.setattr(resultado, "fetch_one", lambda *_: {"nombre": "Soja"})
    monkeypatch.setattr(resultado, "detalle_costos", lambda *_: [{"montoPesos": 100, "montoDolares": None}])
    monkeypatch.setattr(resultado, "superficie_sembrada", lambda *_: 10)
    monkeypatch.setattr(resultado, "superficie_cosechada", lambda *_: {"valor": None, "estimada": False})
    monkeypatch.setattr(resultado, "cantidad_cosechada", lambda *_: None)
    monkeypatch.setattr(resultado, "venta_neta", lambda *_: {"pesos": 0, "dolares": 0})
    assert resultado.resultado_cultivo(1, 32)["costeoDolaresIncompleto"] is True
