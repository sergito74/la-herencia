"""Simulador acotado de persistencia. Prohíbe toda conexión a producción."""

from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime
from decimal import Decimal
from threading import RLock

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from src.db import connection
from src.features.cajas_efectivo import operaciones as db, router


class CajaSimulada:
    def __init__(self, monkeypatch):
        self.state = {"ops": {}, "records": [], "effects": [], "writes": [], "banks": []}
        self.fail_table = None
        self.doc_contact = 17
        self.paid = 0
        self.balance = Decimal("1000000")
        self.arqueos = []
        self.salary_date = datetime(2026, 10, 22)
        self.salary_total = Decimal("100")
        self.bank_contacts = []
        self.socio_withdrawals = []
        lock = RLock()

        def forbidden(*args, **kwargs):
            raise AssertionError("Prueba 038 intentó conectarse a WC")

        monkeypatch.setattr(connection.pyodbc, "connect", forbidden)
        # 041: sin cargas de impuestos en estas pruebas (la guardia no debe leer WC).
        from src.features.impuestos import particular as _particular
        monkeypatch.setattr(_particular, "guardia_movimiento", lambda id_movimiento: None)

        @contextmanager
        def transaction():
            with lock:
                before = deepcopy(self.state)
                try:
                    yield
                except Exception:
                    self.state.clear()
                    self.state.update(before)
                    raise

        monkeypatch.setattr(connection, "reconciliation_transaction", transaction)
        monkeypatch.setattr(db, "insert", self.insert)
        monkeypatch.setattr(db, "write", self.write)
        monkeypatch.setattr(db, "read", self.read)
        monkeypatch.setattr(db, "one", self.one)
        monkeypatch.setattr(db, "find_key", lambda key: self.state["ops"].get(str(key)))
        monkeypatch.setattr(
            db,
            "get_operation",
            lambda id: next(
                (x for x in self.state["ops"].values() if x["IdOperacion"] == id), None
            ),
        )
        monkeypatch.setattr(db, "create_operation", self.create)
        monkeypatch.setattr(db, "detail", self.detail)
        monkeypatch.setattr(
            db,
            "caja_context",
            lambda *args, **kwargs: {
                "saldoActual": self.balance,
                "saldoFecha": self.balance,
                "minimoPosterior": self.balance,
                "arqueos": self.arqueos,
            },
        )
        monkeypatch.setattr(router, "fetch_one", lambda *args, **kwargs: {"nombre": "prueba"})
        from src.features.aplicaciones_pago import repository as apps
        from src.features.compras import particular
        from src.features.cuentas_socios import valuacion, repository as socios
        from src.features.vinculos import fuente
        from src.features.traspasos_internos_tesoreria import repository as transfers
        from src.features.tesoreria import estado_resolucion

        monkeypatch.setattr(apps, "_importe_total_documento", lambda *a: 100)
        monkeypatch.setattr(
            fuente,
            "pagado_de_documentos",
            lambda docs: {
                key: self.paid
                + sum(
                    float(x["params"][4])
                    for x in self.rows("AplicacionesPago")
                    if len(x["params"]) >= 5
                    and (x["params"][2], x["params"][3]) == key
                    and not x["anulada"]
                )
                for key in docs
            },
        )
        monkeypatch.setattr(particular, "importe_personal_compra_particular", lambda id: 100)
        monkeypatch.setattr(particular, "importe_bruto_compra_particular", lambda id: 100)
        monkeypatch.setattr(
            valuacion,
            "a_fecha",
            lambda *a: {"importeUSD": Decimal("0.5000"), "importeKgCarne": Decimal("0.250")},
        )
        monkeypatch.setattr(
            transfers,
            "_movimiento_referencia",
            lambda medio, id: {
                "medio": medio,
                "idMovimiento": id,
                "importe": -100,
                "fecha": "2026-10-22",
            },
        )
        monkeypatch.setattr(estado_resolucion, "esta_resuelto", lambda *a: "sin_conciliar")
        monkeypatch.setattr(
            apps, "anular_aplicacion", lambda id, *a: self._annul("AplicacionesPago", id)
        )
        monkeypatch.setattr(
            socios, "anular_movimiento", lambda id, *a, **k: self._annul("MovimientosCuentaSocio", id)
        )
        monkeypatch.setattr(
            transfers,
            "vinculo_activo",
            lambda *a: next(
                (
                    x
                    for x in self.state["records"]
                    if x["table"] == "TraspasosInternosTesoreria" and not x.get("anulada")
                ),
                None,
            ),
        )
        monkeypatch.setattr(
            transfers,
            "deshacer",
            lambda *a: [
                self._annul("TraspasosInternosTesoreria", x["id"])
                for x in self.rows("TraspasosInternosTesoreria")
            ],
        )
        app = FastAPI()

        @app.middleware("http")
        async def auth(request: Request, call_next):
            request.state.usuario = {
                "idUsuario": 1,
                "rol": request.headers.get("X-Test-Role", "Administrador"),
            }
            return await call_next(request)

        app.include_router(router.router)
        self.client = TestClient(app)

    def rows(self, table):
        return [x for x in self.state["records"] if x["table"] == table]

    def insert(self, sql, params):
        import re

        match = re.search(r"INSERT INTO dbo\.((?:\[[^\]]+\])|\w+)", sql)
        assert match, sql
        table = match[1].strip("[]")
        if table == self.fail_table:
            raise RuntimeError("Fallo inyectado")
        id = len(self.state["records"]) + 1
        row = {"table": table, "params": tuple(params), "id": id, "anulada": False}
        row["particular"] = table == "Pagos efectivo" and "[Numero documento]" in sql
        self.state["records"].append(row)
        if table == "EfectosOperacionCaja":
            self.state["effects"].append(
                dict(
                    zip(
                        (
                            "IdOperacion",
                            "TipoEfecto",
                            "IdRegistro",
                            "EsCreadoPorOperacion",
                            "Snapshot",
                        ),
                        params,
                        strict=True,
                    )
                )
            )
        if table == "TraspasosInternosTesoreria":
            row.update(
                IdEvento=id,
                MedioA=params[0],
                IdMovimientoA=params[1],
                MedioB="efectivo",
                IdMovimientoB=params[2],
            )
        return id

    def create(self, key, fingerprint, op, context, user):
        id = len(self.state["ops"]) + 1
        self.state["ops"][str(key)] = {
            "IdOperacion": id,
            "HuellaSolicitud": fingerprint,
            "Estado": "Vigente",
            "Version": 0,
            "Solicitud": db.dumps(op.model_dump(mode="json")),
            "Contexto": db.dumps(context),
        }
        return id

    def detail(self, id):
        row = next(x for x in self.state["ops"].values() if x["IdOperacion"] == id)
        return {
            "idOperacion": id,
            "estado": row["Estado"],
            "version": row["Version"],
            "efectos": [x for x in self.state["effects"] if x["IdOperacion"] == id],
        }

    def _annul(self, table, id):
        for row in self.rows(table):
            if row["id"] == id:
                row["anulada"] = True

    def write(self, sql, params=()):
        self.state["writes"].append((sql, params))
        if sql.startswith("UPDATE dbo.OperacionesCajaEfectivo SET Version=Version+1"):
            for row in self.state["ops"].values():
                if row["IdOperacion"] == params[-1]:
                    row.update(Version=row["Version"]+1, Contexto=params[0])
        if sql.startswith("INSERT INTO dbo.BancoOperacionCaja"):
            self.state["banks"].append(params)
        if sql.startswith("UPDATE dbo.OperacionesCajaEfectivo SET Estado='Anulada'"):
            for row in self.state["ops"].values():
                if row["IdOperacion"] == params[-1]:
                    row.update(Estado="Anulada", Version=row["Version"] + 1)
        if sql.startswith("UPDATE dbo.MovimientosCajaEfectivo SET Anulada=1"):
            for row in self.rows("MovimientosCajaEfectivo"):
                if row["params"][9] == params[0]:
                    row["anulada"] = True
        if sql.startswith("UPDATE dbo.GastoCajaEfectivo SET Anulada=1"):
            self._annul("GastoCajaEfectivo", params[-1])
        return 1

    def read(self, sql, params=()):
        if "FROM dbo.vw_MovimientosCuenta_Base" in sql:
            return self.bank_contacts
        if "FROM dbo.MovimientosCuentaSocio" in sql and "Tipo IN ('AsignacionGasto','Devolucion')" in sql:
            return self.socio_withdrawals
        if "FROM dbo.ReasignacionesContacto" in sql or "FROM dbo.PagosSocioProveedor" in sql:
            return []
        if "vw_PagosEfectivoVigentes" in sql:
            return [
                {"IdPagoEfectivo": x["id"], "formal": 1}
                for x in self.rows("Pagos efectivo")
                if x.get("particular") and not x["anulada"]
            ]
        if "WITH (UPDLOCK,HOLDLOCK)" in sql:
            return []
        if "SELECT * FROM dbo.EfectosOperacionCaja" in sql:
            return list(
                reversed([x for x in self.state["effects"] if x["IdOperacion"] == params[0]])
            )
        if "OrigenMovimiento='efectivo'" in sql:
            return [
                {"IdAplicacion": x["id"]}
                for x in self.rows("AplicacionesPago")
                if x["params"][1] == params[0] and not x["anulada"]
            ]
        if (
            "dbo.AplicacionesPago" in sql
            or "dbo.ConciliacionesTesoreria" in sql
            or "dbo.vw_MovimientosCuenta_Base" in sql
            or "dbo.AjustesCuentaCorriente" in sql
        ):
            return []
        raise AssertionError(sql)

    def one(self, sql, params=()):
        if sql.startswith("SELECT IdContacto FROM"):
            return {"IdContacto": params[0]}
        if sql.startswith("SELECT IdSocio FROM"):
            return {"IdSocio": params[0]}
        if (
            "IdContacto contacto" in sql and "Remuneraciones" not in sql
        ) or "SELECT IdConsignatario contacto" in sql:
            return {"contacto": self.doc_contact, "moneda": "Pesos", "tc": 1}
        if "SELECT a.IdContacto contacto" in sql:
            return {"contacto": self.doc_contact, "estado": "Pendiente", "total": 100}
        if "FROM dbo.MovimientosCuentaSocio" in sql and "CompraParticular" in sql:
            return next(
                (
                    {"IdMovimiento": r["id"], "IdSocio": r["params"][0], "Anulada": False}
                    for r in self.rows("MovimientosCuentaSocio")
                    if r["params"][4] == "CompraParticular"
                    and r["params"][5] == params[0]
                    and not r["anulada"]
                ),
                None,
            )
        if "FROM dbo.vw_PagosEfectivoVigentes" in sql:
            return None
        if "FROM dbo.BancoOperacionCaja" in sql and "WHERE IdOperacion=?" in sql:
            return next(({"medio": b[1], "idMovimiento": b[2]} for b in self.state["banks"] if b[0] == params[0]), None)
        if "FROM dbo.BancoOperacionCaja" in sql:
            return next(
                (
                    {"IdOperacion": b[0]}
                    for b in self.state["banks"]
                    if b[1:] == tuple(params)
                    and any(
                        o["IdOperacion"] == b[0] and o["Estado"] == "Vigente"
                        for o in self.state["ops"].values()
                    )
                ),
                None,
            )
        if (
            sql.startswith("SELECT IdRubro")
            or sql.startswith("SELECT IdCentro")
            or sql.startswith("SELECT IdDestino")
            or sql.startswith("SELECT IdCampaña")
        ):
            return {"id": params[0]}
        if sql.startswith("SELECT Anulada FROM"):
            table = "AplicacionesPago" if "AplicacionesPago" in sql else "MovimientosCuentaSocio"
            return {"Anulada": next(x["anulada"] for x in self.rows(table) if x["id"] == params[0])}
        if "FROM dbo.TraspasosInternosTesoreria WHERE IdEvento" in sql:
            return next(x for x in self.rows("TraspasosInternosTesoreria") if x["id"] == params[0])
        if "FROM dbo.Remuneraciones r" in sql:
            return {
                "contacto": 375,
                "total": self.salary_total,
                "fecha": self.salary_date,
                "periodo": "09/2026",
            }
        raise AssertionError(sql)


def request(tipo="pago", **overrides):
    op = {
        "tipo": tipo,
        "caja": "giamigli-sa",
        "fecha": "2026-10-22",
        "importe": "100.00",
        "concepto": "Prueba",
        "cuenta": "A",
    }
    if tipo in ("pago", "cobro"):
        op.update(
            idContacto=17,
            aplicaciones=[
                {
                    "tipoDocumento": "CompraDeuda" if tipo == "pago" else "VentaHacienda",
                    "idDocumento": 10,
                    "importeAplicado": "100.00",
                }
            ],
        )
    if tipo in ("aporte", "retiro_a_cuenta", "retiro_ganancias"):
        op["idSocio"] = 1
    if tipo in ("extraccion_banco", "deposito_banco", "retorno_sueldo_opcion_a"):
        op["banco"] = {"medio": "bna", "idMovimiento": 7}
    if tipo == "traspaso_cajas":
        op["cajaDestino"] = "campo-chica"
    if tipo == "gasto_sin_comprobante":
        op["repartos"] = [{"idRubro": 1, "idCentroCostos": 1, "importePesos": "100.00"}]
    op.update(overrides)
    return op


def guardar(store, op, key=None):
    from uuid import uuid4

    if key is not None and str(key) in store.state["ops"]:
        return store.client.post(
            "/api/cajas-efectivo/operaciones",
            headers={"Idempotency-Key": str(key)},
            json={"operacion": op, "previewVersion": "0" * 64},
        )
    preview = store.client.post("/api/cajas-efectivo/operaciones/previsualizar", json=op)
    assert preview.status_code == 200, preview.text
    response = store.client.post(
        "/api/cajas-efectivo/operaciones",
        headers={"Idempotency-Key": str(key or uuid4())},
        json={
            "operacion": op,
            "previewVersion": preview.json()["previewVersion"],
            "advertenciasAceptadas": preview.json()["advertencias"],
        },
    )
    return response
