"""041: impuestos particulares — un impuesto pagado por Giamigli cargado (total o parte) a la cuenta de un socio o del
Condominio LSC (spec 041, contrato `specs/041-impuestos-particulares/contracts/api.md`).

La boleta, su pago y la cuenta del organismo no cambian. Cada carga genera un Debe en la cuenta de socio
(Origen 'ImpuestoParticular', IdOrigen = IdCarga, magnitudes positivas, valuado a la fecha del impuesto); las
devoluciones son vínculos nominales a Haber del mismo socio (existentes o nuevos con Origen 'DevImpParticular').
Toda escritura ocurre dentro de `reconciliation_transaction` (bloqueo de aplicación: serializa cargas, devoluciones,
anulaciones y la edición/baja de boletas) con reintentos idempotentes por UUID + huella SHA256.

Las reglas viven en funciones que reciben un `store` (acceso a datos); `SqlStore` es el de producción y las pruebas
usan uno en memoria.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from src.features.cuentas_socios.contactos import SOCIO_CONTACTO

ORIGEN_CARGA = "ImpuestoParticular"  # 18 caracteres (Origen es varchar(20))
ORIGEN_DEVOLUCION = "DevImpParticular"  # 16 caracteres
SOCIO_CONDOMINIO = 3
VENTANA_MANUAL_DIAS = 3
CENT = Decimal("0.01")


class ErrorParticular(Exception):
    """Error de negocio con código del contrato. `status` 409/422/404."""

    def __init__(self, codigo: str, mensaje: str, status: int = 409, **contexto):
        super().__init__(mensaje)
        self.codigo, self.mensaje, self.status, self.contexto = codigo, mensaje, status, contexto

    def detalle(self) -> dict:
        return {"codigo": self.codigo, "mensaje": self.mensaje, **self.contexto}


# --- Reglas puras -------------------------------------------------------------------------------------------------

def dinero(valor, campo: str = "importe") -> Decimal:
    try:
        d = Decimal(str(valor).strip().replace(",", ".")) if not isinstance(valor, Decimal) else valor
    except (InvalidOperation, AttributeError) as exc:
        raise ErrorParticular("DATO_INVALIDO", f"{campo} no es un número válido.", 422) from exc
    return d


def importe_de_carga(total_boleta: Decimal, importe=None, porcentaje=None) -> Decimal:
    """Exactamente uno de importe/porcentaje; porcentaje sobre el total original, HALF_UP a 0,01, sin recorte."""
    if (importe is None) == (porcentaje is None):
        raise ErrorParticular("DATO_INVALIDO", "Indicá un importe o un porcentaje (uno solo).", 422)
    if importe is not None:
        monto = dinero(importe).quantize(CENT, rounding=ROUND_HALF_UP)
    else:
        p = dinero(porcentaje, "porcentaje")
        if p <= 0 or p > 100:
            raise ErrorParticular("DATO_INVALIDO", "El porcentaje debe ser mayor que 0 y hasta 100.", 422)
        monto = (total_boleta * p / 100).quantize(CENT, rounding=ROUND_HALF_UP)
    if monto <= 0:
        raise ErrorParticular("DATO_INVALIDO", "El importe resultante debe ser mayor que 0.", 422)
    return monto


def normalizar_partida(partida: str | None) -> str | None:
    """Trim, espacios colapsados y mayúsculas; conserva ceros y puntuación."""
    if partida is None:
        return None
    p = re.sub(r"\s+", " ", str(partida)).strip().upper()
    if not p:
        return None
    if len(p) > 60:
        raise ErrorParticular("DATO_INVALIDO", "La partida admite hasta 60 caracteres.", 422)
    return p


def texto(valor, campo: str, maximo: int = 255) -> str:
    t = (valor or "").strip() if isinstance(valor, str) or valor is None else str(valor)
    if not t:
        raise ErrorParticular("DATO_INVALIDO", f"{campo} es obligatorio.", 422)
    if len(t) > maximo:
        raise ErrorParticular("DATO_INVALIDO", f"{campo} admite hasta {maximo} caracteres.", 422)
    return t


def huella(cuerpo: dict, usuario: str) -> str:
    """SHA256 del cuerpo canónico (sin la clave) y el usuario; montos equivalentes ('8852.1' / 8852.10) canonizados."""
    def canon(v):
        if isinstance(v, (int, float, Decimal)) and not isinstance(v, bool):
            return str(Decimal(str(v)).normalize())
        if isinstance(v, str) and re.fullmatch(r"-?\d+([.,]\d+)?", v.strip()):
            return str(Decimal(v.strip().replace(",", ".")).normalize())
        if isinstance(v, (date, datetime)):
            return v.isoformat()[:10]
        return v
    base = {k: canon(v) for k, v in sorted(cuerpo.items()) if k != "claveIdempotencia" and v not in (None, False, "")}
    return hashlib.sha256(json.dumps({"c": base, "u": usuario}, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def estado_devolucion(importe: Decimal, devuelto: Decimal) -> str:
    if devuelto <= 0:
        return "pendiente"
    return "devuelto" if devuelto >= importe else "parcial"


def estado_agregado(estados: list[str]) -> str | None:
    if not estados:
        return None
    if all(e == "devuelto" for e in estados):
        return "devuelto"
    if all(e == "pendiente" for e in estados):
        return "pendiente"
    return "parcial"


def _dia(v) -> date:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    return date.fromisoformat(str(v)[:10])


# --- Consultas ------------------------------------------------------------------------------------------------------

def _carga_vista(store, c: dict) -> dict:
    vs = store.vinculos(c["IdCarga"])
    devuelto = sum((Decimal(str(v["Importe"])) for v in vs if v["Estado"] == "vigente"), Decimal(0))
    importe = Decimal(str(c["Importe"])).quantize(CENT)
    devuelto = devuelto.quantize(CENT)
    return {
        "idCarga": c["IdCarga"], "idImpuesto": c["IdImpuesto"], "idSocio": c["IdSocio"], "socio": store.nombre_socio(c["IdSocio"]),
        "importe": str(importe), "motivo": c["Motivo"], "partida": c["Partida"], "titularOscar": bool(c["TitularOscar"]),
        "estado": c["Estado"], "idMovimientoSocio": c["IdMovimientoSocio"],
        "devuelto": str(devuelto) if c["Estado"] == "vigente" else "0",
        "pendienteNominal": str(importe - devuelto) if c["Estado"] == "vigente" else "0",
        "estadoDevolucion": estado_devolucion(importe, devuelto) if c["Estado"] == "vigente" else None,
        "devoluciones": [{"idVinculo": v["IdVinculo"], "idMovimientoSocio": v["IdMovimientoSocio"], "importe": str(Decimal(str(v["Importe"]))),
                          "estado": v["Estado"]} for v in vs],
        "motivoAnulacion": c.get("MotivoAnulacion"),
    }


def consultar(store, id_impuesto: int, partida: str | None = None) -> dict:
    imp = store.impuesto(id_impuesto)
    if imp is None:
        raise ErrorParticular("NO_ENCONTRADO", "Boleta no encontrada.", 404)
    cargas = [_carga_vista(store, c) for c in store.cargas(id_impuesto)]
    vigentes = sum((Decimal(c["importe"]) for c in cargas if c["estado"] == "vigente"), Decimal(0)).quantize(CENT)
    total = Decimal(str(imp["Importe"])).quantize(CENT)
    avisos = []
    p = normalizar_partida(partida)
    partidas = {p} if p else {c["partida"] for c in cargas if c["partida"] and c["estado"] == "vigente"}
    for x in sorted(partidas):
        info = consultar_partida(store, x)
        if info["estado"] in ("vigente", "ambigua"):
            avisos.append({"tipo": "partida", **info})
    return {"idImpuesto": id_impuesto, "importe": str(total), "aCargoDeSocios": str(vigentes),
            "parteEmpresa": str(total - vigentes), "cargas": cargas, "avisos": avisos}


def consultar_partida(store, partida: str) -> dict:
    p = normalizar_partida(partida)
    reg = store.padron(p) if p else None
    if reg is None:
        return {"partida": p, "estado": "desconocida", "idSocio": None, "socio": None, "candidatos": [], "titularOscar": False}
    socios = sorted({c["IdSocio"] for c in store.cargas_de_partida(p) if c["Estado"] == "vigente"})
    return {"partida": p, "estado": reg["Estado"], "idSocio": reg["IdSocio"],
            "socio": store.nombre_socio(reg["IdSocio"]) if reg["IdSocio"] else None,
            "candidatos": [{"idSocio": s, "socio": store.nombre_socio(s)} for s in socios] if reg["Estado"] == "ambigua" else [],
            "titularOscar": bool(reg["TitularOscar"])}


def resumen_impuestos(store, ids: list[int]) -> dict[int, dict]:
    """Para la lista: aCargoDe, estadoDevolucion y pendienteNominal por impuesto (una consulta por lote)."""
    out: dict[int, dict] = {}
    for c in store.cargas_vigentes_de(ids):
        vista = _carga_vista(store, c)
        r = out.setdefault(c["IdImpuesto"], {"aCargoDe": [], "estados": [], "pendienteNominal": Decimal(0)})
        r["aCargoDe"].append({"idSocio": vista["idSocio"], "socio": vista["socio"], "importe": vista["importe"]})
        r["estados"].append(vista["estadoDevolucion"])
        r["pendienteNominal"] += Decimal(vista["pendienteNominal"])
    return {k: {"aCargoDe": v["aCargoDe"], "estadoDevolucion": estado_agregado(v["estados"]),
                "pendienteNominal": str(v["pendienteNominal"])} for k, v in out.items()}


# --- Padrón ---------------------------------------------------------------------------------------------------------

def recalcular_padron(store, partida: str | None, usuario: str) -> None:
    if not partida:
        return
    vig = [c for c in store.cargas_de_partida(partida) if c["Estado"] == "vigente"]
    socios = sorted({c["IdSocio"] for c in vig})
    oscar = any(c["TitularOscar"] for c in vig)
    if not socios:
        estado, id_socio, origen = "sin_cargas", None, None
    elif len(socios) == 1:
        estado, id_socio = "vigente", socios[0]
        origen = min(c["IdCarga"] for c in vig)
    else:
        estado, id_socio, origen = "ambigua", None, None
    store.padron_guardar(partida, id_socio, origen, estado, oscar, usuario)


# --- Escrituras -----------------------------------------------------------------------------------------------------

def _por_clave(store, tabla: str, clave: str, h: str):
    previo = store.por_clave(tabla, clave)
    if previo is None:
        return None
    if previo["HuellaSolicitud"] != h:
        raise ErrorParticular("CLAVE_IDEMPOTENCIA_REUTILIZADA", "Esa clave ya se usó para otra operación distinta.")
    return previo


def candidatos_manuales(store, id_socio: int, importe: Decimal, fecha) -> list[dict]:
    f = _dia(fecha)
    return [m for m in store.debes_manuales(id_socio, importe)
            if abs((_dia(m["Fecha"]) - f).days) <= VENTANA_MANUAL_DIAS]


def crear_carga(store, id_impuesto: int, cuerpo: dict, usuario: str, valuar) -> tuple[dict, bool]:
    """Devuelve (carga, creada). `valuar(importe, fecha) -> {importeUSD, importeKgCarne}`."""
    clave = cuerpo.get("claveIdempotencia")
    if not clave:
        raise ErrorParticular("DATO_INVALIDO", "Falta la clave de idempotencia.", 422)
    h = huella(cuerpo, usuario)
    previo = _por_clave(store, "carga", clave, h)
    if previo:
        return _carga_vista(store, previo), False
    imp = store.impuesto(id_impuesto, bloquear=True)
    if imp is None:
        raise ErrorParticular("NO_ENCONTRADO", "Boleta no encontrada.", 404)
    id_socio = int(cuerpo.get("idSocio") or 0)
    if not store.nombre_socio(id_socio):
        raise ErrorParticular("DATO_INVALIDO", "El socio no existe.", 422)
    total = Decimal(str(imp["Importe"])).quantize(CENT)
    monto = importe_de_carga(total, cuerpo.get("importe"), cuerpo.get("porcentaje"))
    motivo = texto(cuerpo.get("motivo"), "El motivo")
    partida = normalizar_partida(cuerpo.get("partida"))
    oscar = bool(cuerpo.get("titularOscar"))
    if oscar and (not partida or id_socio != SOCIO_CONDOMINIO):
        raise ErrorParticular("TITULAR_INVALIDO", "Una partida de Oscar Vicente va siempre al Condominio LSC e informa la partida.", 422)
    if partida:
        reg = store.padron(partida)
        if reg and reg["TitularOscar"] and reg["Estado"] != "sin_cargas" and id_socio != SOCIO_CONDOMINIO:
            raise ErrorParticular("TITULAR_INVALIDO", "Esa partida está declarada de Oscar Vicente: va al Condominio LSC.", 422)
    vigentes = sum((Decimal(str(c["Importe"])) for c in store.cargas(id_impuesto) if c["Estado"] == "vigente"), Decimal(0))
    if vigentes + monto > total:
        raise ErrorParticular("SUPERARIA_IMPORTE", "La suma cargada a socios superaría el importe de la boleta.",
                              remanente=str(total - vigentes))
    requiere = []
    if store.cuenta_cerrada(id_socio) and not cuerpo.get("confirmarCuentaCerrada"):
        requiere.append({"codigo": "CUENTA_CERRADA", "mensaje": "La cuenta del socio está cerrada. Confirmá para cargarle el impuesto."})
    manuales = candidatos_manuales(store, id_socio, monto, imp["Fecha"])
    reemplazo = cuerpo.get("reemplazarMovimientoManual")
    if reemplazo is not None:
        if int(reemplazo) not in {m["IdMovimiento"] for m in manuales}:
            raise ErrorParticular("DEBE_MANUAL_INVALIDO", "El asiento a reemplazar no es un Debe manual equivalente vigente.", 422)
    elif manuales and not cuerpo.get("ignorarManuales"):
        requiere.append({"codigo": "DEBE_MANUAL_EQUIVALENTE", "mensaje": "Ya hay un Debe manual equivalente: elegí cuál reemplazar.",
                         "candidatos": [{"idMovimiento": m["IdMovimiento"], "fecha": str(_dia(m["Fecha"])), "importe": str(Decimal(str(m["Importe"]))),
                                         "motivo": m.get("Motivo")} for m in manuales]})
    if requiere:
        raise ErrorParticular(requiere[0]["codigo"], requiere[0]["mensaje"], requiereConfirmacion=True, avisos=requiere)
    fecha = _dia(imp["Fecha"])
    v = valuar(monto, fecha)
    if reemplazo is not None:
        store.anular_movimiento(int(reemplazo), f"Reemplazado por la carga del impuesto {id_impuesto} (041)", usuario)
    detalle = f"{store.nombre_organismo(imp)} — impuesto {id_impuesto} a cargo del socio: {motivo}"[:255]
    id_mov = store.insertar_movimiento(id_socio, "AsignacionGasto", monto, Decimal(str(v["importeUSD"])),
                                       Decimal(str(v["importeKgCarne"])), fecha, None, None, None, detalle, usuario)
    id_carga = store.insertar_carga(id_impuesto, id_socio, monto, motivo, partida, oscar, id_mov, clave, h, usuario)
    store.enlazar_movimiento(id_mov, ORIGEN_CARGA, id_carga)
    store.auditar("Asignacion", id_mov, id_socio, usuario, f"041 carga {id_carga} del impuesto {id_impuesto}: {monto}")
    recalcular_padron(store, partida, usuario)
    return _carga_vista(store, store.carga(id_carga)), True


def vincular_devolucion(store, id_carga: int, cuerpo: dict, usuario: str, valuar) -> tuple[dict, bool]:
    clave = cuerpo.get("claveIdempotencia")
    if not clave:
        raise ErrorParticular("DATO_INVALIDO", "Falta la clave de idempotencia.", 422)
    existente, nuevo = cuerpo.get("idMovimientoSocio"), any(cuerpo.get(k) for k in ("fecha", "medio", "motivo"))
    if bool(existente) == bool(nuevo):
        raise ErrorParticular("DATO_INVALIDO", "Indicá un Haber existente o los datos de uno nuevo (solo una opción).", 422)
    h = huella(cuerpo, usuario)
    previo = _por_clave(store, "vinculo", clave, h)
    if previo:
        return {**_carga_vista(store, store.carga(previo["IdCarga"])), "idVinculo": previo["IdVinculo"]}, False
    carga = store.carga(id_carga, bloquear=True)
    if carga is None:
        raise ErrorParticular("NO_ENCONTRADO", "Carga no encontrada.", 404)
    if carga["Estado"] != "vigente":
        raise ErrorParticular("CARGA_ANULADA", "La carga está anulada.")
    monto = dinero(cuerpo.get("importe")).quantize(CENT, rounding=ROUND_HALF_UP)
    if monto <= 0:
        raise ErrorParticular("DATO_INVALIDO", "El importe debe ser mayor que 0.", 422)
    pendiente = Decimal(str(carga["Importe"])) - sum((Decimal(str(v["Importe"])) for v in store.vinculos(id_carga) if v["Estado"] == "vigente"),
                                                     Decimal(0))
    if monto > pendiente:
        raise ErrorParticular("SUPERARIA_PENDIENTE", "La devolución supera lo pendiente de la carga.", pendiente=str(pendiente))
    if existente:
        mov = store.movimiento(int(existente), bloquear=True)
        if not mov or mov["Tipo"] != "Devolucion" or mov["Anulada"] or mov["IdSocio"] != carga["IdSocio"]:
            raise ErrorParticular("HABER_NO_VALIDO", "El Haber no existe, está anulado o es de otro socio.")
        if any(v["Estado"] == "vigente" and v["IdCarga"] == id_carga for v in store.vinculos_de_movimiento(mov["IdMovimiento"])):
            raise ErrorParticular("VINCULO_DUPLICADO", "Ese Haber ya está vinculado a esta carga.")
        usado = sum((Decimal(str(v["Importe"])) for v in store.vinculos_de_movimiento(mov["IdMovimiento"]) if v["Estado"] == "vigente"),
                    Decimal(0))
        disponible = Decimal(str(mov["Importe"])) - usado
        if monto > disponible:
            raise ErrorParticular("CAPACIDAD_HABER_INSUFICIENTE", "El Haber no tiene disponible ese importe.", disponible=str(disponible))
        id_mov = mov["IdMovimiento"]
    else:
        fecha = _dia(cuerpo.get("fecha"))
        v = valuar(monto, fecha)
        motivo = texto(cuerpo.get("motivo"), "El motivo")
        medio = (cuerpo.get("medio") or "").strip()[:100] or None
        id_mov = store.insertar_movimiento(carga["IdSocio"], "Devolucion", monto, Decimal(str(v["importeUSD"])),
                                           Decimal(str(v["importeKgCarne"])), fecha, ORIGEN_DEVOLUCION, id_carga, medio, motivo, usuario)
    id_v = store.insertar_vinculo(id_carga, id_mov, monto, clave, h, usuario)
    store.auditar("Devolucion", id_mov, carga["IdSocio"], usuario, f"041 vínculo {id_v} a la carga {id_carga}: {monto}")
    return {**_carga_vista(store, store.carga(id_carga)), "idVinculo": id_v}, True


def anular_vinculo(store, id_carga: int, id_vinculo: int, motivo: str, usuario: str) -> dict:
    motivo = texto(motivo, "El motivo")
    v = store.vinculo(id_vinculo, bloquear=True)
    if v is None or v["IdCarga"] != id_carga:
        raise ErrorParticular("NO_ENCONTRADO", "Vínculo no encontrado.", 404)
    if v["Estado"] == "vigente":
        store.anular_vinculo(id_vinculo, motivo, usuario)
    return _carga_vista(store, store.carga(id_carga))


def anular_carga(store, id_carga: int, motivo: str, usuario: str) -> dict:
    motivo = texto(motivo, "El motivo")
    c = store.carga(id_carga, bloquear=True)
    if c is None:
        raise ErrorParticular("NO_ENCONTRADO", "Carga no encontrada.", 404)
    if c["Estado"] == "vigente":
        for v in store.vinculos(id_carga):
            if v["Estado"] == "vigente":
                store.anular_vinculo(v["IdVinculo"], f"Anulación de la carga {id_carga}: {motivo}", usuario)
        store.anular_movimiento(c["IdMovimientoSocio"], f"Anulación de la carga {id_carga} (041): {motivo}", usuario)
        store.anular_carga(id_carga, motivo, usuario)
        store.auditar("ReversionAsignacion", c["IdMovimientoSocio"], c["IdSocio"], usuario, f"041 anulación carga {id_carga}: {motivo}")
        recalcular_padron(store, c["Partida"], usuario)
    return _carga_vista(store, store.carga(id_carga))


def vinculo_de_movimiento(store, id_movimiento: int) -> dict | None:
    """Si el movimiento de socio es el Debe de una carga vigente o un Haber con vínculos vigentes, devuelve la referencia."""
    c = store.carga_por_movimiento(id_movimiento)
    if c:
        return {"idCarga": c["IdCarga"], "idImpuesto": c["IdImpuesto"], "rol": "debe"}
    vs = [v for v in store.vinculos_de_movimiento(id_movimiento) if v["Estado"] == "vigente"]
    if vs:
        return {"idCarga": vs[0]["IdCarga"], "idImpuesto": store.carga(vs[0]["IdCarga"])["IdImpuesto"], "rol": "haber"}
    return None


def cargas_vigentes_de_impuesto(store, id_impuesto: int) -> list[dict]:
    return [c for c in store.cargas(id_impuesto) if c["Estado"] == "vigente"]


# --- Store de producción ------------------------------------------------------------------------------------------

class SqlStore:
    """Acceso a WC dentro de la transacción vigente (cursor de `reconciliation_transaction`)."""

    def __init__(self, cursor=None):
        self.c = cursor
        self._socios: dict[int, str] | None = None

    def _q(self, sql, params=()):
        if self.c is None:
            from src.db.connection import fetch_all

            return fetch_all(sql, tuple(params))
        self.c.execute(sql, *params)
        if self.c.description is None:
            return []
        cols = [d[0] for d in self.c.description]
        return [dict(zip(cols, r)) for r in self.c.fetchall()]

    def _x(self, sql, params=()):
        self.c.execute(sql, *params)

    def _id(self, sql, params=()):
        self.c.execute(sql, *params)
        return int(self.c.fetchone()[0])

    def _uno(self, sql, params=()):
        r = self._q(sql, params)
        return r[0] if r else None

    def _lock(self, bloquear):
        return " WITH (UPDLOCK, HOLDLOCK)" if bloquear and self.c is not None else ""

    def nombre_socio(self, id_socio):
        if self._socios is None:
            self._socios = {r["IdSocio"]: r["Nombre"] for r in self._q("SELECT IdSocio, Nombre FROM dbo.Socios")}
        return self._socios.get(id_socio)

    def nombre_organismo(self, imp):
        r = self._uno("SELECT [Razon Social] r FROM dbo.Contactos WHERE IdContacto=?", (imp["IdOrganismo"],))
        return r["r"] if r else "Impuesto"

    def impuesto(self, id_impuesto, bloquear=False):
        return self._uno(f"SELECT IdImpuesto, Fecha, Importe, IdOrganismo, IdTipoImpuesto FROM dbo.Impuestos{self._lock(bloquear)} "
                         "WHERE IdImpuesto=?", (id_impuesto,))

    def cuenta_cerrada(self, id_socio):
        contacto = SOCIO_CONTACTO.get(id_socio)
        if contacto is None:
            return False
        r = self._uno("SELECT Estado FROM dbo.RevisionFichas WHERE IdContacto=?", (contacto,))
        return bool(r and r["Estado"] in ("cerrada", "cerrada-con-excepcion"))

    _CARGA = ("SELECT IdCarga, IdImpuesto, IdSocio, Importe, Motivo, Partida, TitularOscar, IdMovimientoSocio, Estado, "
              "ClaveIdempotencia, HuellaSolicitud, MotivoAnulacion FROM dbo.ImpuestosParticulares")

    def cargas(self, id_impuesto):
        return self._q(self._CARGA + " WHERE IdImpuesto=? ORDER BY IdCarga", (id_impuesto,))

    def cargas_vigentes_de(self, ids):
        if not ids:
            return []
        out = []
        for i in range(0, len(ids), 500):
            lote = ids[i:i + 500]
            out += self._q(self._CARGA + f" WHERE Estado='vigente' AND IdImpuesto IN ({','.join('?' * len(lote))})", lote)
        return out

    def carga(self, id_carga, bloquear=False):
        return self._uno(self._CARGA.replace("FROM dbo.ImpuestosParticulares", f"FROM dbo.ImpuestosParticulares{self._lock(bloquear)}")
                         + " WHERE IdCarga=?", (id_carga,))

    def carga_por_movimiento(self, id_mov):
        return self._uno(self._CARGA + " WHERE IdMovimientoSocio=? AND Estado='vigente'", (id_mov,))

    def cargas_de_partida(self, partida):
        return self._q(self._CARGA + " WHERE Partida=?", (partida,))

    def por_clave(self, tabla, clave):
        if tabla == "carga":
            return self._uno(self._CARGA + " WHERE ClaveIdempotencia=?", (clave,))
        return self._uno("SELECT IdVinculo, IdCarga, HuellaSolicitud FROM dbo.ImpuestosParticularesDevoluciones WHERE ClaveIdempotencia=?",
                         (clave,))

    def debes_manuales(self, id_socio, importe):
        return self._q("SELECT IdMovimiento, Fecha, Importe, Motivo FROM dbo.MovimientosCuentaSocio WHERE IdSocio=? AND Anulada=0 "
                       "AND Tipo='AsignacionGasto' AND (Origen IS NULL OR Origen='Manual') AND Importe=?", (id_socio, importe))

    def movimiento(self, id_mov, bloquear=False):
        return self._uno(f"SELECT IdMovimiento, IdSocio, Tipo, Importe, Anulada, Origen FROM dbo.MovimientosCuentaSocio{self._lock(bloquear)} "
                         "WHERE IdMovimiento=?", (id_mov,))

    def insertar_movimiento(self, id_socio, tipo, importe, usd, kg, fecha, origen, id_origen, medio, motivo, usuario):
        return self._id("INSERT INTO dbo.MovimientosCuentaSocio (IdSocio,Tipo,Importe,ImporteUSD,ImporteKgCarne,Fecha,Origen,IdOrigen,Medio,"
                        "Motivo,Usuario) OUTPUT INSERTED.IdMovimiento VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                        (id_socio, tipo, importe, usd, kg, fecha.isoformat(), origen, id_origen, medio, motivo, usuario))

    def enlazar_movimiento(self, id_mov, origen, id_origen):
        self._x("UPDATE dbo.MovimientosCuentaSocio SET Origen=?, IdOrigen=? WHERE IdMovimiento=?", (origen, id_origen, id_mov))

    def anular_movimiento(self, id_mov, motivo, usuario):
        self._x("UPDATE dbo.MovimientosCuentaSocio SET Anulada=1, MotivoAnulacion=?, UsuarioAnulacion=?, FechaAnulacion=SYSUTCDATETIME() "
                "WHERE IdMovimiento=? AND Anulada=0", (motivo[:255], usuario, id_mov))

    def insertar_carga(self, id_impuesto, id_socio, importe, motivo, partida, oscar, id_mov, clave, h, usuario):
        return self._id("INSERT INTO dbo.ImpuestosParticulares (IdImpuesto,IdSocio,Importe,Motivo,Partida,TitularOscar,IdMovimientoSocio,"
                        "ClaveIdempotencia,HuellaSolicitud,CreadoPor) OUTPUT INSERTED.IdCarga VALUES (?,?,?,?,?,?,?,?,?,?)",
                        (id_impuesto, id_socio, importe, motivo, partida, int(oscar), id_mov, clave, h, usuario))

    def anular_carga(self, id_carga, motivo, usuario):
        self._x("UPDATE dbo.ImpuestosParticulares SET Estado='anulada', MotivoAnulacion=?, AnuladoPor=?, AnuladoEn=SYSUTCDATETIME() "
                "WHERE IdCarga=? AND Estado='vigente'", (motivo, usuario, id_carga))

    _VINC = "SELECT IdVinculo, IdCarga, IdMovimientoSocio, Importe, Estado, HuellaSolicitud FROM dbo.ImpuestosParticularesDevoluciones"

    def vinculos(self, id_carga):
        return self._q(self._VINC + " WHERE IdCarga=? ORDER BY IdVinculo", (id_carga,))

    def vinculo(self, id_v, bloquear=False):
        return self._uno(self._VINC.replace("Devoluciones", f"Devoluciones{self._lock(bloquear)}") + " WHERE IdVinculo=?", (id_v,))

    def vinculos_de_movimiento(self, id_mov):
        return self._q(self._VINC + " WHERE IdMovimientoSocio=?", (id_mov,))

    def insertar_vinculo(self, id_carga, id_mov, importe, clave, h, usuario):
        return self._id("INSERT INTO dbo.ImpuestosParticularesDevoluciones (IdCarga,IdMovimientoSocio,Importe,ClaveIdempotencia,"
                        "HuellaSolicitud,Usuario) OUTPUT INSERTED.IdVinculo VALUES (?,?,?,?,?,?)", (id_carga, id_mov, importe, clave, h, usuario))

    def anular_vinculo(self, id_v, motivo, usuario):
        self._x("UPDATE dbo.ImpuestosParticularesDevoluciones SET Estado='anulada', MotivoAnulacion=?, AnuladoPor=?, "
                "AnuladoEn=SYSUTCDATETIME() WHERE IdVinculo=? AND Estado='vigente'", (motivo[:255], usuario, id_v))

    def padron(self, partida):
        return self._uno("SELECT Partida, IdSocio, IdCargaOrigen, Estado, TitularOscar FROM dbo.PartidasTitulares WHERE Partida=?",
                         (partida,))

    def padron_guardar(self, partida, id_socio, origen, estado, oscar, usuario):
        if self.padron(partida):
            self._x("UPDATE dbo.PartidasTitulares SET IdSocio=?, IdCargaOrigen=?, Estado=?, TitularOscar=?, Fecha=SYSUTCDATETIME(), "
                    "Usuario=? WHERE Partida=?", (id_socio, origen, estado, int(oscar), usuario, partida))
        else:
            self._x("INSERT INTO dbo.PartidasTitulares (Partida, IdSocio, IdCargaOrigen, Estado, TitularOscar, Usuario) VALUES (?,?,?,?,?,?)",
                    (partida, id_socio, origen, estado, int(oscar), usuario))

    def auditar(self, accion, id_mov, id_socio, usuario, detalle):
        self._x("INSERT INTO dbo.AuditoriaReflejoSocio (Accion, IdMovimiento, IdSocio, Usuario, Detalle) VALUES (?,?,?,?,?)",
                (accion, id_mov, id_socio, usuario, detalle[:500]))


# --- Entradas transaccionales (las usan el router, el script y las guardias de otras rutas) -------------------------

def _en_transaccion(fn):
    from src.db.connection import _reconciliation_connection, reconciliation_transaction

    with reconciliation_transaction():
        return fn(SqlStore(_reconciliation_connection.get().cursor()))


def _valuar(importe, fecha):
    from src.features.cuentas_socios.valuacion import a_fecha

    return a_fecha(importe, fecha)


def tx_crear_carga(id_impuesto, cuerpo, usuario):
    return _en_transaccion(lambda s: crear_carga(s, id_impuesto, cuerpo, usuario, _valuar))


def tx_vincular(id_carga, cuerpo, usuario):
    return _en_transaccion(lambda s: vincular_devolucion(s, id_carga, cuerpo, usuario, _valuar))


def tx_anular_vinculo(id_carga, id_vinculo, motivo, usuario):
    return _en_transaccion(lambda s: anular_vinculo(s, id_carga, id_vinculo, motivo, usuario))


def tx_anular_carga(id_carga, motivo, usuario):
    return _en_transaccion(lambda s: anular_carga(s, id_carga, motivo, usuario))


def leer(id_impuesto, partida=None):
    return consultar(SqlStore(), id_impuesto, partida)


def leer_partida(partida):
    return consultar_partida(SqlStore(), partida)


def leer_resumen(ids):
    return resumen_impuestos(SqlStore(), ids)


def guardia_movimiento(id_movimiento: int) -> None:
    """Rutas de socios/caja: un Debe de carga vigente o un Haber con vínculos vigentes no se edita ni anula por fuera."""
    ref = vinculo_de_movimiento(SqlStore(), id_movimiento)
    if ref:
        raise ErrorParticular("MOVIMIENTO_VINCULADO_A_IMPUESTO",
                              f"El movimiento está vinculado al impuesto {ref['idImpuesto']} (carga {ref['idCarga']}): "
                              "anulá o desvinculá primero desde la ficha del impuesto.", **ref)


def tiene_cargas_vigentes(id_impuesto: int) -> bool:
    return bool(cargas_vigentes_de_impuesto(SqlStore(), id_impuesto))


def saldo_socio(id_socio: int) -> dict:
    from src.features.cuentas_socios.repository import calcular_saldo

    return calcular_saldo(id_socio)


def fraccion_a_socios(ids: list[int]) -> dict[int, float]:
    """Flujo de caja: fracción del importe de cada boleta cargada a socios (0..1), una consulta por lote."""
    if not ids:
        return {}
    from src.db.connection import fetch_all

    out = {}
    try:
        for i in range(0, len(ids), 500):
            lote = ids[i:i + 500]
            for r in fetch_all("SELECT p.IdImpuesto i, SUM(p.Importe) s, MAX(i.Importe) t FROM dbo.ImpuestosParticulares p JOIN dbo.Impuestos i "
                               f"ON i.IdImpuesto=p.IdImpuesto WHERE p.Estado='vigente' AND p.IdImpuesto IN ({','.join('?' * len(lote))}) "
                               "GROUP BY p.IdImpuesto", tuple(lote)):
                if r["t"]:
                    out[r["i"]] = min(float(r["s"]) / float(r["t"]), 1.0)
    except Exception as exc:  # tablas aún no creadas: sin cargas
        if "Invalid object name" not in str(exc):
            raise
    return out
