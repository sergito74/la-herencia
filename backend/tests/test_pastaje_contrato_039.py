"""039: contrato de la API de pastaje (contratos, bitácora, liquidación, comprobantes) con base simulada."""

from datetime import date
from decimal import Decimal as D
from pathlib import Path

import pytest

from src.features.pastaje import service
from tests.pastaje_039_helpers import CONTRATO, INGRESO, RepoSimulado, cliente

FACTURA = Path(__file__).parent / "fixtures" / "factura_arca_20261006.txt"


@pytest.fixture
def db(monkeypatch, tmp_path):
    return RepoSimulado(monkeypatch, tmp_path)


@pytest.fixture
def api(db):
    return cliente()


@pytest.fixture(autouse=True)
def hoy(monkeypatch):
    class Hoy(date):
        @classmethod
        def today(cls):
            return date(2026, 10, 22)
    monkeypatch.setattr(service, "date", Hoy)


def _contrato(api):
    c = api.post("/api/pastaje/contratos", json=CONTRATO).json()
    assert api.post(f"/api/pastaje/contratos/{c['id']}/bitacora", json=INGRESO).status_code == 200
    return c


def test_alta_y_condiciones(api):
    c = _contrato(api)
    assert c["estado"] == "vigente" and c["tarifas"][0]["valor"] == "5" and c["clausulaSanidad"]
    tarjetas = api.get("/api/pastaje/contratos").json()
    assert tarjetas[0]["cabezasActuales"] == [{"categoria": "Vaquillonas", "cabezas": 70}]
    assert tarjetas[0]["proximoPaso"] == "Liquidar septiembre 2026"


def test_contacto_inexistente_y_rol_lectura(api, db):
    assert api.post("/api/pastaje/contratos", json={**CONTRATO, "idContacto": 1}).status_code == 422
    assert cliente("Lectura").post("/api/pastaje/contratos", json=CONTRATO).status_code == 403
    assert cliente("Lectura").get("/api/pastaje/contratos").status_code == 200


def test_edicion_con_version_vieja_da_409(api):
    c = _contrato(api)
    body = {**{k: v for k, v in CONTRATO.items() if k != "tarifas"}, "version": c["version"]}
    assert api.put(f"/api/pastaje/contratos/{c['id']}", json=body).status_code == 200
    assert api.put(f"/api/pastaje/contratos/{c['id']}", json=body).status_code == 409


def test_recuento_alerta_diferencia_en_ambos_sentidos_sin_cambiar_cabezas(api):
    c = _contrato(api)
    mas = api.post(f"/api/pastaje/contratos/{c['id']}/bitacora", json={**INGRESO, "tipo": "recuento", "fecha": "2026-10-10", "cabezas": 72}).json()
    menos = api.post(f"/api/pastaje/contratos/{c['id']}/bitacora", json={**INGRESO, "tipo": "recuento", "fecha": "2026-10-11", "cabezas": 68}).json()
    assert (mas["diferencia"], menos["diferencia"]) == (2, -2)
    assert api.get(f"/api/pastaje/contratos/{c['id']}/bitacora").json()["cabezasActuales"][0]["cabezas"] == 70


def test_egreso_mayor_a_existencias_se_rechaza(api):
    c = _contrato(api)
    r = api.post(f"/api/pastaje/contratos/{c['id']}/bitacora", json={**INGRESO, "tipo": "egreso", "fecha": "2026-10-01", "cabezas": 71})
    assert r.status_code == 422


def test_liquidacion_septiembre_confirmada_y_pdf(api, db):
    c = _contrato(api)
    prev = api.get(f"/api/pastaje/contratos/{c['id']}/liquidaciones/preview", params={"periodo": "2026-09"}).json()
    assert (prev["neto"], prev["iva"], prev["total"], prev["precioPromedio"]) == ("290851.40", "61078.79", "351930.19", "4155.02")
    assert prev["textoFactura"] == ["Servicio de pastaje de 70 Vaquillonas del 25 al 30 de septiembre de 2026"]
    liq = api.post(f"/api/pastaje/contratos/{c['id']}/liquidaciones", json={"periodo": "2026-09"}).json()
    assert api.post(f"/api/pastaje/contratos/{c['id']}/liquidaciones", json={"periodo": "2026-10"}).status_code == 422  # mes en curso
    conf = api.post(f"/api/pastaje/liquidaciones/{liq['id']}/confirmar", json={"version": liq["version"]}).json()
    assert conf["estado"] == "confirmada" and Path(conf["archivoPdf"]).read_bytes()[:4] == b"%PDF"
    assert Path(conf["archivoPdf"]).name == "Liquidación de Pastaje - Septiembre 2026 - GANADERA SAN JUSTO SOCIEDAD SIMPLE.pdf"
    # Fijada: una nueva confirmación o un recálculo del borrador ya no aplican.
    assert api.post(f"/api/pastaje/contratos/{c['id']}/liquidaciones", json={"periodo": "2026-09"}).status_code == 409


def test_sin_indice_bloquea(api, db):
    db.indices.clear()
    c = _contrato(api)
    prev = api.get(f"/api/pastaje/contratos/{c['id']}/liquidaciones/preview", params={"periodo": "2026-09"}).json()
    assert prev["bloqueo"]
    assert api.post(f"/api/pastaje/contratos/{c['id']}/liquidaciones", json={"periodo": "2026-09"}).status_code == 409


def _factura(api, c, liq, **extra):
    from src.features.pastaje.lector_factura import leer_texto

    datos = leer_texto(FACTURA.read_text(encoding="utf-8"))
    body = {k: (str(v) if isinstance(v, D) else v) for k, v in datos.items() if k not in ("codigo", "cuitEmisor", "cliente")}
    return api.post("/api/pastaje/comprobantes", json={**body, "idContrato": c["id"], "idLiquidacion": liq["id"], **extra})


def _liquidada(api):
    c = _contrato(api)
    liq = api.post(f"/api/pastaje/contratos/{c['id']}/liquidaciones", json={"periodo": "2026-09"}).json()
    liq = api.post(f"/api/pastaje/liquidaciones/{liq['id']}/confirmar", json={"version": liq["version"]}).json()
    return c, liq


def test_factura_real_se_vincula_sin_diferencias_y_no_se_duplica(api, db):
    c, liq = _liquidada(api)
    db.indices[date(2026, 10, 2)] = D("4100")
    r = _factura(api, c, liq)
    assert r.status_code == 200, r.text
    f = r.json()
    assert (f["numero"], f["puntoVenta"], f["total"], f["idCampania"]) == (8, 2, "351930.19", 32)
    assert _factura(api, c, liq).status_code == 409
    mes = api.get(f"/api/pastaje/contratos/{c['id']}").json()["meses"]
    sep = next(m for m in mes if m["periodo"] == "2026-09-01")
    assert sep["estado"] == "Facturado — pendiente de cobro" and sep["saldo"] == "351930.19"
    oct_ = next(m for m in mes if m["periodo"] == "2026-10-01")
    assert oct_["estado"] == "En curso" and oct_["devengado"]


def test_factura_con_importes_distintos_exige_aceptar(api):
    c, liq = _liquidada(api)
    r = _factura(api, c, liq, total="351930.20", neto="290851.41")
    assert r.status_code == 409


def test_cambio_retroactivo_genera_diferencia_y_ajuste_con_nc(api, db):
    c, liq = _liquidada(api)
    f = _factura(api, c, liq).json()
    # Una muerte el 29/09 cargada después de liquidar: 69 cabezas del 29 al 30.
    api.post(f"/api/pastaje/contratos/{c['id']}/bitacora", json={**INGRESO, "tipo": "muerte", "fecha": "2026-09-29", "cabezas": 1})
    sep = next(m for m in api.get(f"/api/pastaje/contratos/{c['id']}").json()["meses"] if m["periodo"] == "2026-09-01")
    assert D(sep["diferencia"]) < 0 and sep["alertas"]
    aj = api.post(f"/api/pastaje/liquidaciones/{liq['id']}/ajuste").json()
    aj = api.post(f"/api/pastaje/liquidaciones/{aj['id']}/confirmar", json={"version": aj["version"]}).json()
    assert aj["tipo"] == "ajuste" and D(aj["neto"]) == D(sep["diferencia"]) and aj["archivoPdf"]
    nc = {"idContrato": c["id"], "idLiquidacion": aj["id"], "idComprobanteAsociado": f["id"], "tipo": "nota_credito", "letra": "A",
          "puntoVenta": 2, "numero": 1, "fecha": "2026-10-23", "neto": str(-D(aj["neto"])), "iva": str(-D(aj["iva"])),
          "total": str(-D(aj["total"]))}
    assert api.post("/api/pastaje/comprobantes", json=nc).status_code == 200
    sep = next(m for m in api.get(f"/api/pastaje/contratos/{c['id']}").json()["meses"] if m["periodo"] == "2026-09-01")
    assert sep["diferencia"] is None and D(sep["facturado"]) == D(sep["liquidado"])


def test_no_se_anula_comprobante_cobrado(api, db):
    c, liq = _liquidada(api)
    f = _factura(api, c, liq).json()
    db.cobros[f["id"]] = D("351930.19")
    assert api.post(f"/api/pastaje/comprobantes/{f['id']}/anular", json={"motivo": "x", "version": f["version"]}).status_code == 409
    sep = next(m for m in api.get(f"/api/pastaje/contratos/{c['id']}").json()["meses"] if m["periodo"] == "2026-09-01")
    assert sep["estado"] == "Cobrado"


def test_finalizar_exige_egreso_total(api):
    c = _contrato(api)
    v = api.get(f"/api/pastaje/contratos/{c['id']}").json()["version"]
    assert api.post(f"/api/pastaje/contratos/{c['id']}/finalizar", json={"fechaFin": "2026-10-20", "version": v}).status_code == 409
    api.post(f"/api/pastaje/contratos/{c['id']}/bitacora", json={**INGRESO, "tipo": "egreso", "fecha": "2026-10-20", "cabezas": 70})
    assert api.post(f"/api/pastaje/contratos/{c['id']}/finalizar", json={"fechaFin": "2026-10-20", "version": v}).json()["estado"] == "finalizado"


def test_generar_mes_es_idempotente(api, db):
    c = _contrato(api)
    r1 = api.post("/api/pastaje/liquidaciones/generar-mes", json={"periodo": "2026-09"}).json()
    r2 = api.post("/api/pastaje/liquidaciones/generar-mes", json={"periodo": "2026-09"}).json()
    assert r1[0]["estado"] == r2[0]["estado"] == "borrador" and r1[0]["id"] == r2[0]["id"]


def test_nd_no_puede_respaldar_un_ajuste_a_favor_del_cliente(api, db):
    c, liq = _liquidada(api)
    f = _factura(api, c, liq).json()
    api.post(f"/api/pastaje/contratos/{c['id']}/bitacora", json={**INGRESO, "tipo": "muerte", "fecha": "2026-09-29", "cabezas": 1})
    aj = api.post(f"/api/pastaje/liquidaciones/{liq['id']}/ajuste").json()
    aj = api.post(f"/api/pastaje/liquidaciones/{aj['id']}/confirmar", json={"version": aj["version"]}).json()
    # IVA del ajuste = IVA recalculado − IVA original (sin redondeo del ajuste por separado).
    from src.features.pastaje.calculo import Movimiento as M, Tarifa as T, liquidar
    from tests.pastaje_039_helpers import SEP
    nuevo = liquidar(date(2026, 9, 1), [M(date(2026, 9, 25), "ingreso", 3, 70), M(date(2026, 9, 29), "muerte", 3, 1)],
                     [T(3, "kg_novillo", D(5), date(2026, 9, 25))], SEP)
    assert (D(aj["neto"]), D(aj["iva"])) == (nuevo.neto - D("290851.40"), nuevo.iva - D("61078.79"))
    nd = {"idContrato": c["id"], "idLiquidacion": aj["id"], "idComprobanteAsociado": f["id"], "tipo": "nota_debito", "letra": "A",
          "puntoVenta": 2, "numero": 2, "fecha": "2026-10-23", "neto": str(-D(aj["neto"])), "iva": str(-D(aj["iva"])),
          "total": str(-D(aj["total"]))}
    assert api.post("/api/pastaje/comprobantes", json=nd).status_code == 422


def test_nc_sin_liquidacion_hereda_la_campania_de_la_factura(api, db):
    c, liq = _liquidada(api)
    f = _factura(api, c, liq).json()
    nc = {"idContrato": c["id"], "idComprobanteAsociado": f["id"], "tipo": "nota_credito", "letra": "A", "puntoVenta": 2,
          "numero": 3, "fecha": "2027-07-05", "neto": "100", "iva": "21", "total": "121"}
    assert api.post("/api/pastaje/comprobantes", json=nc).json()["idCampania"] == f["idCampania"] == 32
