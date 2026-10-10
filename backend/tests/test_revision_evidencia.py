"""Pruebas de las funciones puras de `evidencia.py` — 036 (T035). No leen ni escriben la base."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from src.features.revision_cuentas import evidencia


def test_en_pesos_una_diferencia_de_hasta_un_peso_cierra():
    assert evidencia.clasificar_saldo_externo(0.0, 0.5, "Pesos") == (0.5, "cierra")
    assert evidencia.clasificar_saldo_externo(0.0, -1.0, "Pesos") == (-1.0, "cierra")


def test_la_diferencia_de_jauregui_contra_el_portal_es_menor_al_umbral():
    """Saldo de la cuenta −$3,31 contra +$0,01 a favor nuestro del proveedor: diferencia de $3,32, menor a $300."""
    diferencia, clasificacion = evidencia.clasificar_saldo_externo(0.01, -3.31, "Pesos")
    assert diferencia == -3.32 and clasificacion == "menor-al-umbral"


def test_clasificacion_en_pesos_por_tramos():
    assert evidencia.clasificar_saldo_externo(100.0, 100.5, "Pesos")[1] == "cierra"
    assert evidencia.clasificar_saldo_externo(100.0, 400.0, "Pesos")[1] == "menor-al-umbral"          # $300 exactos
    assert evidencia.clasificar_saldo_externo(100.0, 401.0, "Pesos")[1] == "con-diferencia"
    assert evidencia.clasificar_saldo_externo(100.0, -250.0, "Pesos")[1] == "con-diferencia"       # diferencia de $350
    assert evidencia.clasificar_saldo_externo(100.0, -200.0, "Pesos")[1] == "menor-al-umbral"      # diferencia de $300 exactos


def test_el_umbral_en_pesos_es_un_parametro():
    assert evidencia.clasificar_saldo_externo(0.0, 500.0, "Pesos", umbral_pesos=600.0)[1] == "menor-al-umbral"


def test_en_dolares_solo_hay_tolerancia_relativa_nunca_un_monto_fijo():
    # 0,2 % de 100.000 cierra; $250 en dólares chicos no se da por cerrado aunque sea menor a 300
    assert evidencia.clasificar_saldo_externo(100000.0, 100200.0, "Dolares")[1] == "cierra"
    assert evidencia.clasificar_saldo_externo(1000.0, 1250.0, "Dolares")[1] == "con-diferencia"
    assert evidencia.clasificar_saldo_externo(100000.0, 101000.0, "Dolares")[1] == "con-diferencia"


def test_la_diferencia_es_el_saldo_de_la_cuenta_menos_el_externo():
    assert evidencia.clasificar_saldo_externo(1000.0, 1500.0, "Pesos")[0] == 500.0
    assert evidencia.clasificar_saldo_externo(-50.0, -20.0, "Pesos")[0] == 30.0


def test_sin_estado_exige_una_nota_con_el_motivo():
    hoy = date.today()
    with pytest.raises(ValueError):
        evidencia.validar_saldo_externo(hoy, "sin-estado", None, "Pesos")
    with pytest.raises(ValueError):
        evidencia.validar_saldo_externo(hoy, "sin-estado", "   ", "Pesos")
    evidencia.validar_saldo_externo(hoy, "sin-estado", "Movimientos de 2015: no se pide estado de cuenta", "Pesos")


def test_la_fecha_del_saldo_no_puede_ser_futura():
    with pytest.raises(ValueError):
        evidencia.validar_saldo_externo(date.today() + timedelta(days=1), "portal", None, "Pesos")
    evidencia.validar_saldo_externo(date.today(), "portal", None, "Pesos")


def test_fuente_y_moneda_desconocidas_se_rechazan():
    with pytest.raises(ValueError):
        evidencia.validar_saldo_externo(date.today(), "telepatia", None, "Pesos")
    with pytest.raises(ValueError):
        evidencia.validar_saldo_externo(date.today(), "portal", None, "Euros")


def test_una_factura_tiene_archivo_si_su_documento_original_es_una_ruta_a_un_comprobante():
    assert evidencia.tiene_archivo(r"C:\Users\Sergio\Dropbox\Compras\20260812_JaureguiYMorales.pdf") is True
    assert evidencia.tiene_archivo(r"..\Compras\20251212_JaureguiYMorales.crdownload#..\Compras\20251212_JaureguiYMorales.crdownload#") is True
    assert evidencia.tiene_archivo("Sin archivo, respaldo: portal 09/10/2026") is False
    assert evidencia.tiene_archivo("Portal Jauregui y Morales (cliente 174), consultado 09/10/2026") is False
    assert evidencia.tiene_archivo(None) is False and evidencia.tiene_archivo("   ") is False


def test_validar_marca_no_necesita_la_base_cuando_no_hay_factura_asociada():
    assert evidencia.validar_marca(48, "factura-cargada", None, None, "portal") is True      # sin archivo, con respaldo
    with pytest.raises(ValueError):
        evidencia.validar_marca(48, "factura-cargada", None, None, None)
    with pytest.raises(ValueError):
        evidencia.validar_marca(48, "sin-documento", None, None, None)
    assert evidencia.validar_marca(48, "anticipo", None, None, None) is False
    with pytest.raises(ValueError):
        evidencia.validar_marca(48, "inventado", None, None, None)
    with pytest.raises(ValueError):
        evidencia.validar_marca(48, "factura-cargada", None, None, "telepatia")


# ---- Un pago de un cliente puede estar respaldado por una venta de hacienda o de granos

def test_una_venta_respalda_un_pago_si_existe_y_es_de_la_cuenta(monkeypatch):
    consultas = []
    monkeypatch.setattr(evidencia, "fetch_one", lambda sql, params=(): consultas.append((sql, params)) or {"x": 1})
    assert evidencia.validar_marca(551, "venta-cargada", None, None, None, "venta-hacienda", 67) is False
    assert "Venta Hacienda" in consultas[0][0] and consultas[0][1] == (67, 551)
    evidencia.validar_marca(551, "venta-cargada", None, None, None, "venta-granos", 12)
    assert "Venta Granos" in consultas[1][0]


def test_la_venta_de_otra_cuenta_o_inexistente_se_rechaza(monkeypatch):
    monkeypatch.setattr(evidencia, "fetch_one", lambda sql, params=(): None)
    with pytest.raises(ValueError, match="no existe o no es de esta cuenta"):
        evidencia.validar_marca(551, "venta-cargada", None, None, None, "venta-hacienda", 999)


def test_venta_cargada_exige_el_tipo_y_el_numero_de_la_venta():
    with pytest.raises(ValueError, match="cuál venta"):
        evidencia.validar_marca(551, "venta-cargada", None, None, None)
    with pytest.raises(ValueError, match="cuál venta"):
        evidencia.validar_marca(551, "venta-cargada", None, None, None, "venta-hacienda", None)
    with pytest.raises(ValueError, match="cuál venta"):
        evidencia.validar_marca(551, "venta-cargada", None, None, None, "otra-cosa", 5)


def test_la_venta_solo_se_indica_con_el_estado_venta_cargada():
    with pytest.raises(ValueError, match="solo se indica"):
        evidencia.validar_marca(551, "sin-documento", "nota", None, None, "venta-hacienda", 67)


def test_el_respaldo_se_muestra_como_venta_de_hacienda_con_su_numero(monkeypatch):
    monkeypatch.setattr(evidencia, "fetch_one", lambda sql, params=(): {"n": "00003-00000014"})
    assert evidencia.texto_de_venta("venta-hacienda", 67) == "venta de hacienda 00003-00000014"
    monkeypatch.setattr(evidencia, "fetch_one", lambda sql, params=(): {"n": None})
    assert evidencia.texto_de_venta("venta-granos", 12) == "venta de granos #12"
    assert evidencia.texto_de_venta(None, None) is None


def test_las_ventas_de_la_cuenta_traen_hacienda_y_granos_ordenadas_por_fecha(monkeypatch):
    def falso(sql, params=()):
        if "Venta Hacienda" in sql:
            return [{"i": 67, "f": "2024-05-28", "n": "00003-00000014"}]
        if "Venta Granos" in sql:
            return [{"i": 12, "f": "2025-01-10", "n": None}]
        return []  # sin contratos de arrendamiento
    monkeypatch.setattr(evidencia, "fetch_all", falso)
    ventas = evidencia.ventas_de_cuenta(551)
    assert [v["rotulo"] for v in ventas] == ["venta de granos #12", "venta de hacienda 00003-00000014"]
    assert [v["tipo"] for v in ventas] == ["venta-granos", "venta-hacienda"]


def test_un_contrato_de_arrendamiento_tambien_respalda_un_pago(monkeypatch):
    consultas = []
    monkeypatch.setattr(evidencia, "fetch_one", lambda sql, params=(): consultas.append((sql, params)) or {"x": 1})
    assert evidencia.validar_marca(562, "venta-cargada", None, None, None, "arrendamiento", 138210678) is False
    assert "Alquileres" in consultas[0][0] and "IdAlquiler" in consultas[0][0] and consultas[0][1] == (138210678, 562)


def test_el_contrato_de_arrendamiento_se_nombra_por_su_fecha(monkeypatch):
    monkeypatch.setattr(evidencia, "fetch_one", lambda sql, params=(): {"n": None, "f": "2024-11-19 00:00:00"})
    assert evidencia.texto_de_venta("arrendamiento", 138210678) == "contrato de arrendamiento del 19/11/2024"
    monkeypatch.setattr(evidencia, "fetch_all", lambda sql, params=(): [{"i": 138210678, "f": "2024-11-19", "n": None}] if "Alquileres" in sql else [])
    ventas = evidencia.ventas_de_cuenta(562)
    assert ventas == [{"tipo": "arrendamiento", "idVenta": 138210678, "fecha": "2024-11-19", "numero": "del 19/11/2024",
                       "rotulo": "contrato de arrendamiento del 19/11/2024"}]
