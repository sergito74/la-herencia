"""Contract tests de /api/flujo-caja (018) — ver contracts/api-flujo-caja.md.

Los tests con fixtures monkeypatched verifican estructura/comportamiento del
router; los que llaman directo a `repository` sin mockear corren de solo
lectura contra `WC` real (mismo patrón que test_cuentas_corrientes_saldos.py)
para validar invariantes contra datos reales (SC-002, SC-004, SC-005).
"""

from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from src.auth.tokens import crear_token
from src.features.flujo_caja import repository
from src.main import app

client = TestClient(app)
client.cookies.set("la_herencia_session", crear_token(id_usuario=0, rol="Administrador"))


FIXTURE_PERIODOS = [
    {
        "periodo": "2026-07",
        "porCuenta": [{"banco": "BNA", "numeroCuenta": "6150111899", "ingresos": 1000.0, "egresos": -400.0, "neto": 600.0}],
        "totalIngresos": 1000.0,
        "totalEgresos": -400.0,
        "totalNeto": 600.0,
        "movimientosInternos": {"ingresos": 50000.0, "egresos": -50000.0, "total": 0.0},
        "sinClasificar": {"cantidad": 2, "importeAbsoluto": 300.0},
    }
]
FIXTURE_ULTIMA_CARGA = [
    {"banco": "BNA", "numeroCuenta": "6150111899", "fecha": "2026-07-30"},
    {"banco": "Galicia", "numeroCuenta": "0000798-8 383-4", "fecha": "2026-08-31"},
]


def test_resumen_estructura_y_movimientos_internos_separados(monkeypatch):
    monkeypatch.setattr(repository, "get_movimientos_normalizados", lambda *a, **k: [])
    monkeypatch.setattr(repository, "agregar_por_periodo", lambda *a, **k: FIXTURE_PERIODOS)
    monkeypatch.setattr(repository, "ultima_fecha_por_cuenta", lambda: FIXTURE_ULTIMA_CARGA)

    response = client.get("/api/flujo-caja/resumen?granularidad=mensual")
    assert response.status_code == 200
    body = response.json()
    periodo = body["periodos"][0]
    # El movimiento interno (FIMA) no está en totalNeto, pero sí en su bloque propio.
    assert periodo["totalNeto"] == 600.0
    assert periodo["movimientosInternos"]["total"] == 0.0
    assert periodo["movimientosInternos"]["ingresos"] == 50000.0
    assert periodo["sinClasificar"]["cantidad"] == 2
    assert len(body["ultimaCarga"]) == 2


def test_resumen_fecha_anterior_a_apertura_devuelve_400():
    response = client.get("/api/flujo-caja/resumen?fechaDesde=2005-01-01")
    assert response.status_code == 400


def test_detalle_solo_internos_filtra_por_esInterno(monkeypatch):
    movimientos = [
        {
            "fecha": "2026-07-15T00:00:00",
            "banco": "Galicia",
            "numeroCuentaBancaria": "0000798-8 383-4",
            "concepto": "Suscripcion FIMA",
            "importe": -50000.0,
            "idContacto": None,
            "contacto": None,
            "esInterno": True,
        },
        {
            "fecha": "2026-07-16T00:00:00",
            "banco": "BNA",
            "numeroCuentaBancaria": "6150111899",
            "concepto": "Pago proveedor",
            "importe": -1000.0,
            "idContacto": 42,
            "contacto": "Proveedor SA",
            "esInterno": False,
        },
    ]
    monkeypatch.setattr(repository, "get_movimientos_normalizados", lambda *a, **k: movimientos)

    response = client.get(
        "/api/flujo-caja/detalle?fechaDesde=2026-07-01&fechaHasta=2026-07-31&soloInternos=true"
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["movimientos"]) == 1
    assert body["movimientos"][0]["esInterno"] is True


def test_detalle_filtra_por_banco_y_numero_cuenta(monkeypatch):
    movimientos = [
        {
            "fecha": "2011-01-10T00:00:00",
            "banco": "BNA",
            "numeroCuentaBancaria": "12301640001709",
            "concepto": "x",
            "importe": -10.0,
            "idContacto": None,
            "contacto": None,
            "esInterno": False,
        },
        {
            "fecha": "2011-01-11T00:00:00",
            "banco": "Galicia",
            "numeroCuentaBancaria": "0000798-8 383-4",
            "concepto": "y",
            "importe": 20.0,
            "idContacto": None,
            "contacto": None,
            "esInterno": False,
        },
    ]
    monkeypatch.setattr(repository, "get_movimientos_normalizados", lambda *a, **k: movimientos)

    response = client.get(
        "/api/flujo-caja/detalle?fechaDesde=2011-01-01&fechaHasta=2011-01-31&banco=BNA&numeroCuenta=12301640001709",
    )
    body = response.json()
    assert len(body["movimientos"]) == 1
    assert body["movimientos"][0]["banco"] == "BNA"


def test_flujo_caja_no_expone_metodos_de_escritura():
    """FR-006: la pantalla es de solo lectura — refuerza contra una
    regresión que agregue accidentalmente un endpoint de escritura."""
    for metodo in ("post", "put", "patch", "delete"):
        response = getattr(client, metodo)("/api/flujo-caja/resumen")
        assert response.status_code in (404, 405)
        response = getattr(client, metodo)("/api/flujo-caja/detalle")
        assert response.status_code in (404, 405)


# --- Tests de solo lectura contra WC real (sin monkeypatch) ---


def test_ultima_fecha_por_cuenta_incluye_las_4_cuentas_conocidas():
    filas = repository.ultima_fecha_por_cuenta()
    claves = {(f["banco"], f["numeroCuenta"]) for f in filas}
    assert ("BNA", "12301640001709") in claves
    assert ("BNA", "12301640029280") in claves
    assert ("BNA", "6150111899") in claves
    assert ("Galicia", "0000798-8 383-4") in claves


def test_movimientos_bna_2011_pertenecen_solo_a_la_primera_cuenta():
    """US3: dentro de la vigencia de la cuenta 12301640001709 (2010-09→2012-06),
    ningun movimiento BNA deberia pertenecer a otra cuenta."""
    movimientos = repository.get_movimientos_normalizados(date(2011, 1, 1), date(2011, 12, 31))
    bna = [m for m in movimientos if m["banco"] == "BNA"]
    if bna:
        assert all(m["numeroCuentaBancaria"] == "12301640001709" for m in bna)


def test_agregacion_no_pierde_ni_duplica_contra_movimientos_crudos():
    """SC-002: el total agregado (antes de separar internos) debe coincidir
    con la suma cruda de movimientos del mismo rango."""
    desde, hasta = date(2026, 7, 1), date(2026, 7, 31)
    movimientos = repository.get_movimientos_normalizados(desde, hasta)
    periodos = repository.agregar_por_periodo(movimientos, "mensual")

    suma_cruda = round(sum(m["importe"] for m in movimientos), 2)
    suma_agregada = round(
        sum(p["totalIngresos"] + p["totalEgresos"] + p["movimientosInternos"]["total"] for p in periodos), 2
    )
    assert suma_cruda == suma_agregada
