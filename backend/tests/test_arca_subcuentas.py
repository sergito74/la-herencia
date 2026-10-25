"""Invariantes monetarias y contrato ARCA. No escribe WC."""
from datetime import date
from decimal import Decimal as D
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.features.cuentas_corrientes import arca, arca_router
from src.features.cuentas_corrientes import arca_documentos


def fila(i, fecha="2026-01-01", deuda="0", credito="0", detalle="", origen="Galicia"):
    return {"fecha": date.fromisoformat(fecha), "documento": "VEP", "numeroDocumento": str(i),
            "origen": origen, "idOrigen": i, "deuda": D(deuda), "credito": D(credito), "detalle": detalle}


def test_reparto_conserva_ambos_lados_y_precision_acumulada():
    filas = [fila(1, deuda="100.0001"), fila(2, credito="100.0002")]
    marca = {("Galicia", 2): {"version": 7, "reparto": json.dumps([
        {"subcuenta": "iva", "deuda": "0", "credito": "50.0001"},
        {"subcuenta": "ganancias", "deuda": "0", "credito": "50.0001"}])}}
    c = arca.construir(filas, marca)
    assert c["saldoTotal"] == D("0.0001")
    assert sum(r["credito"] for r in c["resumen"]) == D("100.0002")
    assert sum(r["deuda"] for r in c["resumen"]) == D("100.0001")
    assert len(c["items"]) == 2
    seleccion = arca.construir(filas, marca, subcuenta="iva")
    assert seleccion["saldoSeleccion"] == D("50.0001")
    assert seleccion["items"][0]["creditoOriginal"] == D("100.0002")


def test_apertura_filtro_corte_y_paginacion_no_reinician_saldo():
    filas = [fila(1, "2025-12-01", deuda="10", detalle="Ganancias"),
             fila(2, "2026-01-01", credito="20", detalle="Ganancias"),
             fila(3, "2026-02-01", credito="30", detalle="Ganancias"),
             fila(4, "2026-03-01", credito="999", detalle="Ganancias")]
    c = arca.construir(filas, {}, date(2026,1,1), date(2026,2,28), "ganancias", 2, 1)
    assert c["apertura"] == -10
    assert c["saldoSeleccion"] == 40
    assert c["saldoTotal"] == 40
    assert c["total"] == 2
    assert c["items"][0]["saldo"] == 40


@pytest.mark.parametrize("parte", [
    [{"subcuenta":"iva","deuda":"0","credito":"99"}],
    [{"subcuenta":"iva","deuda":"-1","credito":"100"}],
    [{"subcuenta":"iva","deuda":"0","credito":"100.00001"}],
    [{"subcuenta":"invalida","deuda":"0","credito":"100"}],
    [{"subcuenta":"iva","deuda":"0","credito":"50"}]*2,
    [{"subcuenta":"iva","deuda":"0","credito":"0"}],
])
def test_rechaza_repartos_invalidos(parte):
    with pytest.raises(ValueError):
        arca.validar_partes(parte, D(0), D(100))


def test_reversion_vuelve_a_concepto_y_guarda_version():
    c = arca.construir([fila(1, credito="100", detalle="F.931")],
                       {("Galicia",1): {"version":8,"reparto":"[]","motivo":"Revertido"}})
    assert c["items"][0]["partes"][0]["subcuenta"] == "cargas-sociales"
    assert c["items"][0]["version"] == 8
    assert not c["items"][0]["manual"]


def test_original_corregido_no_oculta_cuenta_ni_reparte_importe_viejo():
    c = arca.construir([fila(1, credito="150")], {("Galicia",1): {
        "version":9,"reparto":json.dumps([{"subcuenta":"iva","deuda":"0","credito":"100"}])}})
    assert c["saldoTotal"] == 150
    assert c["items"][0]["revisarReparto"]
    assert c["items"][0]["partes"][0]["subcuenta"] == "por-identificar"


@pytest.mark.parametrize("detalle,origen,esperado", [
    ("VEP 123", "Galicia", "por-identificar"),
    ("ANULACION DEBITOS", "Galicia", "por-identificar"),
    ("Autónomos 07 2024", "Impuestos", "autonomos-pendientes"),
    ("Autónomos Lucy", "Pago por socio", "autonomos-lucy"),
    ("SICORE Ganancias", "Impuestos", "sicore-ganancias"),
    ("IVA 03 2024", "Impuestos", "iva"),
    ("", "Ret. IVA Granos", "iva"),
])
def test_no_deduce_conceptos_por_importe(detalle, origen, esperado):
    assert arca.clasificar(fila(1, credito="100", detalle=detalle, origen=origen)) == esperado


def cliente():
    app = FastAPI()
    app.include_router(arca_router.router)
    return TestClient(app)


def test_contrato_decimal_y_fechas_invalidas(monkeypatch):
    monkeypatch.setattr(arca, "cargar", lambda: ([fila(1, credito="1.0001")], {}))
    c = cliente()
    r = c.get("/api/arca/cuenta")
    assert r.status_code == 200
    assert r.json()["saldoTotal"] == "1.0001"
    assert c.get("/api/arca/cuenta?fechaDesde=2026-02-01&fechaHasta=2026-01-01").status_code == 422
    assert c.get("/api/arca/cuenta?subcuenta=invalida").status_code == 422


@pytest.mark.parametrize("error,estado", [(arca.ConflictoVersion("cambió"),409),(LookupError("otro contacto"),404),(ValueError("suma"),422)])
def test_contrato_errores_sin_escrituras(monkeypatch,error,estado):
    def fallar(*args):
        raise error
    monkeypatch.setattr(arca_router, "_usuario_actual", lambda r: "prueba")
    monkeypatch.setattr(arca, "guardar", fallar)
    r = cliente().put("/api/arca/clasificacion",json={"origen":"Galicia","idOrigen":1,"version":0,"motivo":"Prueba","partes":[]})
    assert r.status_code == estado


def test_guardado_valida_pertenencia_y_version_antes_de_insertar(monkeypatch):
    consultas = []
    def leer(sql, params):
        consultas.append(params)
        return [{"deuda": D(0), "credito": D(100)}] if "vw_Movimientos" in sql else [{"version":8}]
    monkeypatch.setattr(arca, "read", leer)
    escrituras = []
    monkeypatch.setattr(arca, "execute_insert_returning_id", lambda sql, params: escrituras.append(params) or 9)
    with pytest.raises(arca.ConflictoVersion):
        arca.guardar.__wrapped__("Galicia",1,7,[],"Revertir", "prueba")
    assert not escrituras
    assert arca.guardar.__wrapped__("Galicia",1,8,[],"Revertir", "prueba") == {"version":9}
    assert escrituras[0][2] == "[]"
    assert consultas[0] == ("Galicia",1)


def test_pdf_solo_en_raiz_registrada_con_huella_intacta(tmp_path,monkeypatch):
    import hashlib
    raiz=tmp_path/"arca"
    raiz.mkdir()
    monkeypatch.setattr(arca_documentos,"RAIZ",raiz)
    contenido=b"%PDF-1.7\nfixture"
    p=raiz/"comprobante.pdf"
    p.write_bytes(contenido)
    h=hashlib.sha256(contenido).hexdigest()
    assert arca_documentos.verificar_archivo(p,h)==p
    with pytest.raises(ValueError):arca_documentos.verificar_archivo(p,"0"*64)
    fuera=tmp_path/"otro.pdf"
    fuera.write_bytes(contenido)
    with pytest.raises(FileNotFoundError):arca_documentos.verificar_archivo(fuera,h)
    p.write_bytes(b"archivo cambiado")
    with pytest.raises(ValueError):arca_documentos.verificar_archivo(p,h)


def test_endpoint_pdf_sirve_archivo_registrado_y_no_ruta_libre(tmp_path,monkeypatch):
    p=tmp_path/"acuse.pdf"
    p.write_bytes(b"%PDF-1.7\nfixture")
    monkeypatch.setattr(arca_documentos,"archivo",lambda ident: p)
    c=cliente()
    r=c.get("/api/arca/documentos/123/archivo")
    assert r.status_code==200 and r.content.startswith(b"%PDF-")
    assert r.headers["content-type"]=="application/pdf"
    assert "inline" in r.headers["content-disposition"]
    def ausente(ident):raise FileNotFoundError("No encontrado")
    monkeypatch.setattr(arca_documentos,"archivo",ausente)
    assert c.get("/api/arca/documentos/123/archivo").status_code==404
