from datetime import date, datetime
from decimal import Decimal

from src.features.tesoreria import confirmacion_carga


def test_normalizar_concepto_colapsa_espacios_y_mayusculas():
    assert confirmacion_carga._normalizar_concepto("  Gravamen   Ley  25413 ") == "GRAVAMEN LEY 25413"
    assert confirmacion_carga._normalizar_concepto(None) == ""


def test_detectar_duplicados_bna_marca_coincidencia_exacta(monkeypatch):
    existente = {
        "fecha": date(2026, 1, 19),
        "importe": 5107397.26,
        "concepto": "PLAZO FIJO",
        "comprobante": "81415",
    }
    monkeypatch.setattr(confirmacion_carga, "fetch_all", lambda *a, **k: [existente])

    nuevo = {"fecha": date(2026, 1, 20), "importe": 100.0, "concepto": "OTRO", "comprobante": None}
    igual = {"fecha": date(2026, 1, 19), "importe": 5107397.26, "concepto": "  plazo   fijo ", "comprobante": "81415"}
    resultado = confirmacion_carga.detectar_duplicados("bna", [nuevo, igual])
    assert resultado == [False, True]


def test_detectar_duplicados_no_marca_falso_positivo_por_importe_o_fecha(monkeypatch):
    existente = {
        "fecha": date(2026, 1, 19),
        "importe": 100.0,
        "concepto": "IMPUESTO",
        "comprobante": None,
    }
    monkeypatch.setattr(confirmacion_carga, "fetch_all", lambda *a, **k: [existente])

    mismo_importe_otro_concepto = {"fecha": date(2026, 1, 19), "importe": 100.0, "concepto": "OTRO", "comprobante": None}
    mismo_concepto_otra_fecha = {"fecha": date(2026, 1, 20), "importe": 100.0, "concepto": "IMPUESTO", "comprobante": None}
    resultado = confirmacion_carga.detectar_duplicados(
        "bna", [mismo_importe_otro_concepto, mismo_concepto_otra_fecha]
    )
    assert resultado == [False, False]


def test_detectar_duplicados_galicia_usa_debitos_creditos_y_comprobante(monkeypatch):
    existente = {
        "fecha": date(2026, 8, 20),
        "debitos": 46044.04,
        "creditos": None,
        "descripcion": "Trf Inmed Proveed",
        "numeroComprobante": "57808209",
    }
    monkeypatch.setattr(confirmacion_carga, "fetch_all", lambda *a, **k: [existente])

    igual = {"fecha": date(2026, 8, 20), "debitos": 46044.04, "creditos": None, "descripcion": "TRF INMED PROVEED", "numeroComprobante": "57808209"}
    distinto_comprobante = {"fecha": date(2026, 8, 20), "debitos": 46044.04, "creditos": None, "descripcion": "Trf Inmed Proveed", "numeroComprobante": "OTRO"}
    resultado = confirmacion_carga.detectar_duplicados("galicia", [igual, distinto_comprobante])
    assert resultado == [True, False]


def test_detectar_duplicados_sin_movimientos_no_consulta_la_base(monkeypatch):
    llamado = []
    monkeypatch.setattr(confirmacion_carga, "fetch_all", lambda *a, **k: llamado.append(1) or [])
    resultado = confirmacion_carga.detectar_duplicados("bna", [{"fecha": None, "importe": None}])
    assert resultado == [False]
    assert llamado == []


def test_detectar_duplicados_compara_decimal_de_sql_server_contra_float_del_excel(monkeypatch):
    """Regresión: `fetch_all` devuelve `money`/`datetime` de SQL Server como
    `Decimal`/`datetime`, mientras el preview de Excel trae `float`/`date` —
    comparar esos tipos directamente en Python nunca lanza error, solo
    siempre da `False`, así que ningún duplicado real se detectaba nunca
    (encontrado corriendo T025 contra `WC` real, 2026-09-22)."""
    existente_sql_server = {
        "fecha": datetime(2026, 9, 1, 0, 0),
        "debitos": Decimal("1234.56"),
        "creditos": None,
        "descripcion": "PRUEBA T025 CARGA EXCEL 013",
        "numeroComprobante": "999001",
    }
    monkeypatch.setattr(confirmacion_carga, "fetch_all", lambda *a, **k: [existente_sql_server])

    fila_excel = {
        "fecha": date(2026, 9, 1),
        "debitos": 1234.56,
        "creditos": None,
        "descripcion": "PRUEBA T025 CARGA EXCEL 013",
        "numeroComprobante": "999001",
    }
    assert confirmacion_carga.detectar_duplicados("galicia", [fila_excel]) == [True]


def test_detectar_duplicados_compara_comprobante_numerico_de_sql_server_contra_texto_del_excel(monkeypatch):
    """Regresión: `Nro# Comprobante`/`Número de Comprobante` son columnas
    `float` en SQL Server, así que un comprobante real vuelve como
    `999001.0`, mientras el preview de Excel lo trae como texto `"999001"` —
    `str(999001.0) != "999001"` (encontrado corriendo T025 contra `WC` real,
    2026-09-22, junto al bug de Decimal/datetime)."""
    existente_sql_server = {
        "fecha": datetime(2026, 9, 1, 0, 0),
        "debitos": Decimal("1234.5600"),
        "creditos": None,
        "descripcion": "PRUEBA CON COMPROBANTE",
        "numeroComprobante": 999001.0,
    }
    monkeypatch.setattr(confirmacion_carga, "fetch_all", lambda *a, **k: [existente_sql_server])

    fila_excel = {
        "fecha": date(2026, 9, 1),
        "debitos": 1234.56,
        "creditos": None,
        "descripcion": "PRUEBA CON COMPROBANTE",
        "numeroComprobante": "999001",
    }
    assert confirmacion_carga.detectar_duplicados("galicia", [fila_excel]) == [True]


def test_es_completa_exige_fecha_y_el_campo_de_importe_del_banco():
    assert confirmacion_carga._es_completa("bna", {"fecha": date(2026, 1, 1), "importe": 10.0}) is True
    assert confirmacion_carga._es_completa("bna", {"fecha": None, "importe": 10.0}) is False
    assert confirmacion_carga._es_completa("bna", {"fecha": date(2026, 1, 1), "importe": None}) is False
    assert confirmacion_carga._es_completa("galicia", {"fecha": date(2026, 1, 1), "debitos": None, "creditos": 5.0}) is True
    assert confirmacion_carga._es_completa("galicia", {"fecha": date(2026, 1, 1), "debitos": None, "creditos": None}) is False
