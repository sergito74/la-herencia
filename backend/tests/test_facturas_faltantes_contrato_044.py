"""044 — Contrato de /api/facturas-faltantes con datos simulados (no conecta a WC)."""
from datetime import date, timedelta

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from src.features.facturas_faltantes import repository as repo
from src.features.facturas_faltantes import router as rt
from src.features.facturas_faltantes import service

HOY = date.today()


@pytest.fixture
def cliente(monkeypatch):
    estado = {"descartes": {}, "marcas": [], "perfiles": {}}
    # Movistar mensual (le falta un mes en el medio), Coop. bimestral, un proveedor suelto con pago sin factura.
    docs = []
    for i in range(14):
        if i != 6:
            docs.append({"idDeuda": i, "idContacto": 71, "fecha": HOY - timedelta(days=30 * (13 - i) + 5), "tipo": "Factura",
                         "numero": f"2467-{i}", "importe": 1000 + i})
    for i in range(8):
        docs.append({"idDeuda": 100 + i, "idContacto": 23, "fecha": HOY - timedelta(days=61 * (7 - i) + 10), "tipo": "Factura",
                     "numero": f"B-{i}", "importe": 500})
    monkeypatch.setattr(repo, "proveedores", lambda: {71: "Movistar", 23: "Coop. Eléctrica", 9: "Proveedor suelto"})
    monkeypatch.setattr(repo, "comprobantes", lambda: docs)
    monkeypatch.setattr(repo, "pagos", lambda: [{"idContacto": 9, "fecha": HOY - timedelta(days=200), "origen": "Galicia",
                                                  "idOrigen": 55, "importe": 777.0}])
    monkeypatch.setattr(repo, "pagos_aplicados", lambda: set())
    monkeypatch.setattr(repo, "fechas_de_deuda", lambda: [{"idContacto": x["idContacto"], "fecha": x["fecha"]} for x in docs])
    monkeypatch.setattr(repo, "saldos", lambda: [])
    monkeypatch.setattr(repo, "retenciones", lambda: [])
    monkeypatch.setattr(repo, "remitos_sin_factura", lambda: [])
    monkeypatch.setattr(repo, "perfiles", lambda: estado["perfiles"])
    monkeypatch.setattr(repo, "descartadas", lambda: set(estado["descartes"]))
    monkeypatch.setattr(repo, "descartar", lambda c, i, m, u: estado["descartes"].__setitem__(c, m))
    monkeypatch.setattr(repo, "marcas", lambda e=None: [m for m in estado["marcas"] if not e or m["estado"] == e])

    def crear(d, u):
        estado["marcas"].append({**d, "idMarca": len(estado["marcas"]) + 1, "estado": "abierta", "periodoDesde": None,
                                 "fechaAlta": HOY, "importeAprox": d.get("importeAprox")})
        return len(estado["marcas"])
    monkeypatch.setattr(repo, "crear_marca", crear)
    monkeypatch.setattr(repo, "cerrar_marca", lambda i, d: None)
    monkeypatch.setattr(rt, "_usuario", lambda request: "sergio")
    service.invalidar()
    app = FastAPI()

    @app.middleware("http")
    async def sesion(request: Request, call_next):
        request.state.usuario = {"idUsuario": 1, "rol": "Administrador"}
        return await call_next(request)
    app.include_router(rt.router)
    yield TestClient(app), estado
    service.invalidar()


def test_tablero_recurrentes_y_faltante_historico(cliente):
    c, _ = cliente
    r = c.get("/api/facturas-faltantes/tablero")
    assert r.status_code == 200
    items = {i["proveedor"]: i for i in r.json()["items"]}
    assert items["Movistar"]["ciclo"] == "mensual" and len(items["Movistar"]["faltantesHistoricos"]) == 1
    assert items["Coop. Eléctrica"]["ciclo"] == "bimestral" and items["Coop. Eléctrica"]["estado"] != "atrasada"
    assert "Proveedor suelto" not in items
    assert set(r.json()["resumen"]) == {"llego", "pendiente", "atrasada", "baja"}


def test_alarma_pago_sin_factura_y_descarte(cliente):
    c, estado = cliente
    r = c.get("/api/facturas-faltantes/alarmas", params={"pageSize": 200}).json()
    assert r["total"] == 1 and r["items"][0]["tipo"] == "pago-sin-factura" and r["items"][0]["proveedor"] == "Proveedor suelto"
    clave = r["items"][0]["clave"]
    assert c.post(f"/api/facturas-faltantes/alarmas/{clave}/descartar", json={"motivo": ""}).status_code == 422
    assert c.post(f"/api/facturas-faltantes/alarmas/{clave}/descartar", json={"motivo": "Es un anticipo"}).status_code == 204
    service.invalidar()
    assert c.get("/api/facturas-faltantes/alarmas").json()["total"] == 0
    assert c.post("/api/facturas-faltantes/alarmas/pago:x:1/descartar", json={"motivo": "x"}).status_code == 404


def test_descartar_faltante_historico(cliente):
    c, _ = cliente
    falt = next(i for i in c.get("/api/facturas-faltantes/tablero").json()["items"] if i["proveedor"] == "Movistar")["faltantesHistoricos"][0]
    assert c.post(f"/api/facturas-faltantes/alarmas/{falt['clave']}/descartar", json={"motivo": "No facturó ese mes"}).status_code == 204
    service.invalidar()
    movistar = next(i for i in c.get("/api/facturas-faltantes/tablero").json()["items"] if i["proveedor"] == "Movistar")
    assert movistar["faltantesHistoricos"] == []


def test_marca_falta_factura_y_conflicto(cliente):
    c, _ = cliente
    body = {"idContacto": 9, "origenPago": "galicia", "idPago": 55, "importeAprox": 777}
    assert c.post("/api/facturas-faltantes/marcas", json=body).status_code == 201
    assert c.post("/api/facturas-faltantes/marcas", json=body).status_code == 409
    assert c.post("/api/facturas-faltantes/marcas", json={**body, "origenPago": "cheque"}).status_code == 422
    assert c.get("/api/facturas-faltantes/pago-sin-factura", params={"origen": "galicia", "idPago": 55}).json() == {"sinAplicar": True, "puedeMarcar": False}
    service.invalidar()
    assert c.get("/api/facturas-faltantes/alarmas").json()["total"] == 0  # el pago marcado deja de ser alarma


def test_resumen_mensual_contrato(cliente):
    c, _ = cliente
    r = c.get("/api/facturas-faltantes/resumen-mensual").json()
    assert set(r) == {"mostrar", "mes", "atrasadas", "proveedores"}


def test_perfil_valida_ciclo(cliente, monkeypatch):
    c, _ = cliente
    monkeypatch.setattr(repo, "guardar_perfil", lambda i, campos, u: None)
    assert c.put("/api/facturas-faltantes/perfil/71", json={"cicloDias": 45}).status_code == 422
    assert c.put("/api/facturas-faltantes/perfil/71", json={"cicloDias": 60}).status_code == 204
