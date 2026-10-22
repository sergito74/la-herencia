"""039: repositorio de pastaje simulado en memoria. Prohíbe toda conexión a WC."""

from __future__ import annotations

from copy import deepcopy
from datetime import date
from decimal import Decimal

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from src.db import connection
from src.features.pastaje import inmag, repository as repo, router as router_mod, service
from src.features.pastaje.repository import Conflicto, NoExiste

SEP = {date(2026, 9, 25): Decimal("4068.212"), date(2026, 9, 29): Decimal("4241.828")}
CATS = {2: "Terneros", 3: "Vaquillonas", 4: "Novillos"}


def _iso(x):
    return x.isoformat() if isinstance(x, date) else x


class RepoSimulado:
    def __init__(self, monkeypatch, carpeta):
        self.carpeta = str(carpeta)
        self.indices = dict(SEP)
        self.t = {k: {} for k in ("contratos", "tarifas", "bitacora", "liq", "comp")}
        self.seq = 0
        self.cobros: dict[int, Decimal] = {}

        def prohibido(*a, **k):
            raise AssertionError("Prueba 039 intentó conectarse a WC")
        monkeypatch.setattr(connection.pyodbc, "connect", prohibido)
        for nombre in ("categorias", "contacto", "id_campania", "contratos", "contrato", "tarifas", "insertar_contrato",
                       "actualizar_contrato", "cambiar_estado", "bitacora", "insertar_movimiento", "movimiento",
                       "anular_movimiento", "liquidaciones", "liquidacion", "mensual_vigente", "guardar_borrador",
                       "confirmar_liquidacion", "guardar_pdf_liquidacion", "anular_liquidacion", "comprobantes",
                       "comprobante", "existe_numero", "insertar_comprobante", "anular_comprobante", "cobrado"):
            monkeypatch.setattr(repo, nombre, getattr(self, nombre))
        monkeypatch.setattr(inmag, "indices", lambda d, h: {k: v for k, v in self.indices.items() if d <= k <= h})
        monkeypatch.setattr(inmag, "listar", lambda d, h: [{"fecha": k.isoformat(), "indice": str(v)}
                                                           for k, v in sorted(self.indices.items()) if d <= k <= h])
        monkeypatch.setattr(router_mod, "fetch_one", lambda sql, p: {"nombre": "sergio"})

    def _id(self):
        self.seq += 1
        return self.seq

    def _version(self, tabla, id_, version, cond=lambda r: True):
        r = self.t[tabla].get(id_)
        if not r or r["version"] != version or not cond(r):
            raise Conflicto("El registro fue modificado por otra persona. Volvé a cargarlo.")
        r["version"] += 1
        return r

    # catálogos
    def categorias(self):
        return dict(CATS)

    def contacto(self, i):
        return {"id": i, "razonSocial": "GANADERA SAN JUSTO SOCIEDAD SIMPLE", "cuit": "30715943278"} if i == 900 else None

    def id_campania(self, nombre):
        return 32 if nombre == "2026/2027" else None

    # contratos
    def contratos(self, estado=None):
        return [deepcopy(c) for c in self.t["contratos"].values() if estado in (None, c["estado"])]

    def contrato(self, i):
        if i not in self.t["contratos"]:
            raise NoExiste(f"No existe el contrato {i}.")
        return deepcopy(self.t["contratos"][i])

    def tarifas(self, i):
        return [deepcopy(t) for t in self.t["tarifas"].values() if t["idContrato"] == i]

    def insertar_contrato(self, d, tarifas, usuario, empresa, est):
        i = self._id()
        self.t["contratos"][i] = {"id": i, "idContacto": d["idContacto"], "cliente": "GANADERA SAN JUSTO SOCIEDAD SIMPLE",
                                  "cuit": "30715943278", "fechaInicio": _iso(d["fechaInicio"]), "fechaFin": _iso(d.get("fechaFin")),
                                  "alicuotaIva": "21.00", "carpetaDocumentos": self.carpeta, "estado": "vigente", "version": 1,
                                  "establecimiento": "La Herencia", "creadoPor": usuario,
                                  **{k: d.get(k) for k in ("clausulaSanidad", "clausulaInfraestructura", "clausulaMortandad")}}
        for t in tarifas:
            self._tarifa(i, t)
        return i

    def _tarifa(self, i, t):
        k = (i, t["idTipoHacienda"], _iso(t["vigenteDesde"]))
        if any((x["idContrato"], x["idTipoHacienda"], x["vigenteDesde"]) == k for x in self.t["tarifas"].values()):
            raise Conflicto("Tarifa duplicada")
        j = self._id()
        self.t["tarifas"][j] = {"id": j, "idContrato": i, "idTipoHacienda": t["idTipoHacienda"], "tipoTarifa": t["tipoTarifa"],
                                "valor": str(t["valor"]), "vigenteDesde": _iso(t["vigenteDesde"])}

    def actualizar_contrato(self, i, d, nuevas, version, usuario):
        r = self._version("contratos", i, version, lambda r: r["estado"] == "vigente")
        r.update({k: _iso(d.get(k)) for k in ("fechaInicio", "fechaFin", "clausulaSanidad")})
        for t in nuevas:
            self._tarifa(i, t)

    def cambiar_estado(self, i, estado, motivo, fecha_fin, version, usuario):
        r = self._version("contratos", i, version, lambda r: r["estado"] == "vigente")
        r.update(estado=estado, motivoEstado=motivo, fechaFin=_iso(fecha_fin) or r["fechaFin"])

    # bitácora
    def bitacora(self, i):
        return sorted((deepcopy(m) for m in self.t["bitacora"].values() if m["idContrato"] == i), key=lambda m: (m["fecha"], m["id"]))

    def insertar_movimiento(self, i, m, sistema, usuario):
        j = self._id()
        self.t["bitacora"][j] = {"id": j, "idContrato": i, "fecha": _iso(m["fecha"]), "tipo": m["tipo"],
                                 "idTipoHacienda": m["idTipoHacienda"], "cabezas": int(m["cabezas"]), "cabezasSistema": sistema,
                                 "numeroDte": m.get("numeroDte"), "estado": "vigente", "version": 1}
        return j

    def movimiento(self, j):
        if j not in self.t["bitacora"]:
            raise NoExiste("no")
        return deepcopy(self.t["bitacora"][j])

    def anular_movimiento(self, j, motivo, version, usuario):
        self._version("bitacora", j, version, lambda r: r["estado"] == "vigente")["estado"] = "anulado"

    # liquidaciones
    def liquidaciones(self, i):
        return [deepcopy(l) for l in self.t["liq"].values() if l["idContrato"] == i]

    def liquidacion(self, j):
        if j not in self.t["liq"]:
            raise NoExiste(f"No existe la liquidación {j}.")
        return deepcopy(self.t["liq"][j])

    def mensual_vigente(self, i, periodo):
        return next((deepcopy(l) for l in self.t["liq"].values() if l["idContrato"] == i and l["periodo"] == periodo.isoformat()
                     and l["tipo"] == "mensual" and l["estado"] != "anulada"), None)

    def guardar_borrador(self, i, liq, usuario, tipo="mensual", original=None, existente=None, importes=None):
        neto, iva, total = importes or (liq.neto, liq.iva, liq.total)
        datos = {"precioPromedio": str(liq.precio) if liq.precio is not None else None, "kg": str(round(liq.kg, 4)),
                 "neto": str(neto), "iva": str(iva), "total": str(total), "moneda": liq.moneda,
                 "tramos": [{"idTipoHacienda": t.categoria, "categoria": CATS[t.categoria], "desde": t.desde.isoformat(),
                             "hasta": t.hasta.isoformat(), "cabezas": t.cabezas, "dias": t.dias, "tipoTarifa": t.tipo,
                             "valorMes": str(t.valor_mes), "kg": str(round(t.kg, 4)), "importe": str(round(t.importe, 4))}
                            for t in liq.tramos],
                 "indices": [{"fecha": f.isoformat(), "indice": str(v)} for f, v in liq.indices]}
        if existente:
            if existente["estado"] != "borrador":
                raise Conflicto("La liquidación ya está confirmada: los cambios se resuelven con un ajuste.")
            self._version("liq", existente["id"], existente["version"]).update(datos)
            return existente["id"]
        if tipo == "mensual" and self.mensual_vigente(i, liq.periodo):
            raise Conflicto("UX_PastajeLiq_Mensual")
        j = self._id()
        self.t["liq"][j] = {"id": j, "idContrato": i, "periodo": liq.periodo.isoformat(), "tipo": tipo,
                            "idLiquidacionOriginal": original, "estado": "borrador", "archivoPdf": None, "version": 1, **datos}
        return j

    def confirmar_liquidacion(self, j, version, usuario):
        self._version("liq", j, version, lambda r: r["estado"] == "borrador")["estado"] = "confirmada"

    def guardar_pdf_liquidacion(self, j, ruta):
        self.t["liq"][j]["archivoPdf"] = ruta

    def anular_liquidacion(self, j, version, usuario):
        if any(c["idLiquidacion"] == j and c["estado"] == "vigente" for c in self.t["comp"].values()):
            raise Conflicto("tiene comprobante")
        self._version("liq", j, version, lambda r: r["estado"] != "anulada")["estado"] = "anulada"

    # comprobantes
    def comprobantes(self, i):
        return [deepcopy(c) for c in self.t["comp"].values() if c["idContrato"] == i]

    def comprobante(self, j):
        if j not in self.t["comp"]:
            raise NoExiste("no")
        return deepcopy(self.t["comp"][j])

    def existe_numero(self, tipo, letra, pv, n):
        return any((c["tipo"], c["letra"], c["puntoVenta"], c["numero"]) == (tipo, letra, pv, n) for c in self.t["comp"].values())

    def insertar_comprobante(self, c, usuario):
        j = self._id()
        self.t["comp"][j] = {**{k: (str(v) if isinstance(v, Decimal) else _iso(v)) for k, v in c.items()},
                             "id": j, "estado": "vigente", "version": 1}
        return j

    def anular_comprobante(self, j, motivo, version, usuario):
        if self.cobros.get(j):
            raise Conflicto("cobros")
        self._version("comp", j, version, lambda r: r["estado"] == "vigente")["estado"] = "anulado"

    def cobrado(self, ids):
        return {i: self.cobros.get(i, Decimal(0)) for i in ids}


def cliente(rol="Administrador"):
    app = FastAPI()

    @app.middleware("http")
    async def sesion(request: Request, call_next):
        request.state.usuario = {"idUsuario": 1, "rol": rol}
        return await call_next(request)
    app.include_router(router_mod.router)
    return TestClient(app)


CONTRATO = {"idContacto": 900, "fechaInicio": "2026-09-25", "clausulaSanidad": "A cargo del dueño del ganado",
            "tarifas": [{"idTipoHacienda": 3, "tipoTarifa": "kg_novillo", "valor": "5"}]}
INGRESO = {"fecha": "2026-09-25", "tipo": "ingreso", "idTipoHacienda": 3, "cabezas": 70, "numeroDte": "DTE-123"}
