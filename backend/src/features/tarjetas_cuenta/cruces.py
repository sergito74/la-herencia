"""Cruces de devoluciones con débitos y consumos de tarjeta — 034 (FR-003, FR-019, FR-022).

La sugerencia es solo lectura; el cruce se escribe únicamente cuando el usuario lo aprueba y
nunca se borra: se marca como deshecho con usuario y fecha.
"""

from __future__ import annotations

from datetime import date, datetime

from src.db.connection import execute_insert_returning_id, execute_write, fetch_all, fetch_one
from src.features.tarjetas import repository as tarjetas_repository

VENTANA_DIAS = 45
TOLERANCIA = 0.01

_MEDIOS = {
    "bna": ("dbo.[Movimientos BNA]", "IdMovimientoBNA", "[Fecha / Hora Mov#]", "Importe", "Concepto", "IdContacto"),
    "galicia": ("dbo.[Movimientos Galicia]", "IdMovimiento", "Fecha", "ISNULL([Créditos],0)-ISNULL([Débitos],0)",
                "[Descripción]", "IdContacto"),
    "mercado-libre": ("dbo.[Movimientos Mercado Libre]", "IdMovimiento", "Fecha", "Importe", "Descripcion", "IdContacto"),
}


def a_fecha(valor) -> date:
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, str):
        return datetime.fromisoformat(valor[:19]).date()
    return valor


class CruceError(Exception):
    """`codigo` es el estado HTTP que corresponde: 404, 409 o 422."""

    def __init__(self, codigo: int, mensaje: str):
        super().__init__(mensaje)
        self.codigo = codigo


# --------------------------------------------------------------------------- funciones puras

def puntaje(dias: int, diferencia: float) -> float:
    return round(max(0.0, 1.0 - dias / (VENTANA_DIAS * 3) - min(abs(diferencia), 1.0) * 0.1), 2)


def emparejar(origenes: list[dict], destinos: list[dict], excluidos: set | frozenset = frozenset(),
              un_sentido: bool = True) -> list[dict]:
    """Empareja cada origen con los destinos de igual importe (±$0,01) dentro de ±45 días.
    `un_sentido`: el destino (el débito) debe ser anterior o del mismo día que el origen (la devolución)."""
    sugerencias = []
    for o in origenes:
        if (o["medio"], o["idMovimiento"]) in excluidos:
            continue
        for d in destinos:
            if d.get("clave") in excluidos:
                continue
            dif = round(abs(o["importe"] - d["importe"]), 2)
            dias = (o["fecha"] - d["fecha"]).days
            if dif > TOLERANCIA or abs(dias) > VENTANA_DIAS or (un_sentido and dias < 0):
                continue
            sugerencias.append({"origen": o, "destino": d, "diasDiferencia": abs(dias), "diferenciaImporte": dif,
                                "puntaje": puntaje(abs(dias), dif)})
    sugerencias.sort(key=lambda s: (-s["puntaje"], s["diasDiferencia"]))
    return sugerencias


def validar_devolucion_debito(importe_dev: float, importe_deb: float, ya_cruzado_del_debito: float) -> None:
    if importe_dev <= 0:
        raise CruceError(422, "La devolución debe ser un ingreso")
    if importe_dev > importe_deb + TOLERANCIA:
        raise CruceError(422, "La devolución no puede superar el débito")
    if ya_cruzado_del_debito + importe_dev > importe_deb + TOLERANCIA:
        raise CruceError(422, "El débito ya tiene cruces que, sumados a este, lo superan")


def validar_consumo_devolucion(importe_dev: float, importe_linea: float, tiene_proveedor: bool, vinculado: float,
                               id_tarjeta_linea: int, id_tarjeta: int) -> None:
    if id_tarjeta_linea != id_tarjeta:
        raise CruceError(422, "La línea de consumo pertenece a otra tarjeta")
    if abs(importe_dev - importe_linea) > TOLERANCIA:
        raise CruceError(422, "El importe de la devolución debe igualar el del consumo")
    if tiene_proveedor or vinculado > TOLERANCIA:
        raise CruceError(422, "El consumo ya tiene proveedor o vínculo: cruzarlo lo contaría dos veces")


# --------------------------------------------------------------------------- lectura

def _movimiento(medio: str, id_mov: int) -> dict | None:
    if medio not in _MEDIOS:
        raise CruceError(422, f"Medio desconocido: {medio}")
    tabla, col_id, col_fecha, col_imp, col_desc, col_c = _MEDIOS[medio]
    f = fetch_one(f"SELECT {col_id} AS id, {col_fecha} AS fecha, {col_imp} AS importe, {col_desc} AS concepto, {col_c} AS contacto "
                  f"FROM {tabla} WHERE {col_id} = ?", (id_mov,))
    if not f:
        return None
    fecha = a_fecha(f["fecha"]) if isinstance(f["fecha"], datetime) else f["fecha"]
    return {"medio": medio, "idMovimiento": f["id"], "fecha": fecha, "importe": float(f["importe"] or 0),
            "concepto": f["concepto"], "contacto": f["contacto"]}


def _vigentes() -> list[dict]:
    return fetch_all("SELECT IdCruce, Tipo, IdTarjeta, MedioOrigen, IdMovimientoOrigen, MedioDestino, IdMovimientoDestino, "
                     "IdLineaConsumo, Importe FROM dbo.TarjetasCruces WHERE Deshecho = 0")


def _cruzados(vigentes: list[dict]) -> set:
    claves = {(c["MedioOrigen"], c["IdMovimientoOrigen"]) for c in vigentes}
    return claves


def sugerencias(tipo: str, id_tarjeta: int | None = None) -> list[dict]:
    if tipo not in ("devolucion-debito", "consumo-devolucion"):
        raise CruceError(422, "Tipo de cruce desconocido")
    vigentes = _vigentes()
    excluidos = _cruzados(vigentes)
    tarjetas = [t for t in tarjetas_repository.get_tarjetas(False) if id_tarjeta in (None, t["idTarjeta"])]
    contactos = {tarjetas_repository.get_id_contacto_tarjeta(t["idTarjeta"]): t["idTarjeta"] for t in tarjetas}
    contactos.pop(None, None)
    resultado = []
    if tipo == "devolucion-debito":
        origenes = []
        for medio in ("bna", "galicia"):
            tabla, col_id, col_fecha, col_imp, col_desc, col_c = _MEDIOS[medio]
            for f in fetch_all(f"SELECT {col_id} AS id, {col_fecha} AS fecha, {col_imp} AS importe, {col_desc} AS concepto "
                               f"FROM {tabla} WHERE ({col_imp}) > 0 AND ISNULL({col_c}, 0) = 0"):
                origenes.append({"medio": medio, "idMovimiento": f["id"], "fecha": a_fecha(f["fecha"]), "importe": float(f["importe"]),
                                 "concepto": f["concepto"]})
        destinos = []
        if contactos:
            marcas = ",".join("?" * len(contactos))
            for medio in ("bna", "galicia"):
                tabla, col_id, col_fecha, col_imp, col_desc, col_c = _MEDIOS[medio]
                for f in fetch_all(f"SELECT {col_id} AS id, {col_fecha} AS fecha, -({col_imp}) AS importe, {col_desc} AS concepto, "
                                   f"{col_c} AS c FROM {tabla} WHERE ({col_imp}) < 0 AND {col_c} IN ({marcas})", tuple(contactos)):
                    destinos.append({"medio": medio, "idMovimiento": f["id"], "fecha": a_fecha(f["fecha"]), "importe": float(f["importe"]),
                                     "concepto": f["concepto"], "idTarjeta": contactos[f["c"]]})
        for s in emparejar(origenes, destinos, excluidos):
            resultado.append({"tipo": tipo, "idTarjeta": s["destino"]["idTarjeta"], **{k: s[k] for k in
                              ("origen", "destino", "diasDiferencia", "diferenciaImporte", "puntaje")}})
    else:
        origenes = [{"medio": "mercado-libre", "idMovimiento": f["id"], "fecha": a_fecha(f["fecha"]), "importe": float(f["importe"]),
                     "concepto": f["concepto"]}
                    for f in fetch_all("SELECT IdMovimiento AS id, Fecha AS fecha, Importe AS importe, Descripcion AS concepto "
                                       "FROM dbo.[Movimientos Mercado Libre] WHERE Importe > 0 AND Descripcion LIKE 'Devoluci%'")]
        destinos = []
        for t in tarjetas:
            for f in fetch_all(
                "SELECT l.IdLineaConsumo AS id, l.FechaCompra AS fecha, l.Importe AS importe, l.Detalle AS concepto "
                "FROM dbo.Tarjetas_Resumenes_Lineas l JOIN dbo.Tarjetas_Resumenes r ON r.IdResumen = l.IdResumen "
                "WHERE r.IdTarjeta = ? AND l.IdContacto IS NULL AND l.Importe > 0 AND ISNULL(r.EstadoResumen,'') <> 'Cerrado' "
                "AND NOT EXISTS (SELECT 1 FROM dbo.Tarjetas_Resumenes_Lineas_Compras v WHERE v.IdLineaConsumo = l.IdLineaConsumo) "
                "AND NOT EXISTS (SELECT 1 FROM dbo.TarjetasCruces x WHERE x.Deshecho = 0 AND x.IdLineaConsumo = l.IdLineaConsumo)",
                    (t["idTarjeta"],)):
                destinos.append({"medio": "linea", "idMovimiento": f["id"], "idLineaConsumo": f["id"], "fecha": a_fecha(f["fecha"]),
                                 "importe": float(f["importe"]), "concepto": f["concepto"], "idTarjeta": t["idTarjeta"]})
        for s in emparejar(origenes, destinos, excluidos, un_sentido=False):
            resultado.append({"tipo": tipo, "idTarjeta": s["destino"]["idTarjeta"], **{k: s[k] for k in
                              ("origen", "destino", "diasDiferencia", "diferenciaImporte", "puntaje")}})
    return resultado


# --------------------------------------------------------------------------- escritura

def aprobar(alta: dict, usuario: str) -> dict:
    tipo, id_tarjeta = alta["tipo"], alta["idTarjeta"]
    if tipo not in ("devolucion-debito", "consumo-devolucion"):
        raise CruceError(422, "Tipo de cruce desconocido")
    if tarjetas_repository.get_tarjeta(id_tarjeta) is None:
        raise CruceError(404, "La tarjeta no existe")
    origen = _movimiento(alta["origen"]["medio"], alta["origen"]["idMovimiento"])
    if origen is None:
        raise CruceError(404, "El movimiento de la devolución no existe")
    vigentes = _vigentes()
    if (origen["medio"], origen["idMovimiento"]) in _cruzados(vigentes):
        raise CruceError(409, "El movimiento ya está en un cruce vigente")
    medio_dest = id_dest = linea = None
    if tipo == "devolucion-debito":
        destino = alta.get("destino")
        if not destino:
            raise CruceError(422, "Falta el débito de la tarjeta")
        deb = _movimiento(destino["medio"], destino["idMovimiento"])
        if deb is None:
            raise CruceError(404, "El débito no existe")
        if deb["contacto"] != tarjetas_repository.get_id_contacto_tarjeta(id_tarjeta) or deb["importe"] >= 0:
            raise CruceError(422, "El débito no es un pago de la tarjeta indicada")
        ya = sum(float(c["Importe"]) for c in vigentes if c["Tipo"] == "devolucion-debito"
                 and (c["MedioDestino"], c["IdMovimientoDestino"]) == (deb["medio"], deb["idMovimiento"]))
        validar_devolucion_debito(origen["importe"], -deb["importe"], ya)
        medio_dest, id_dest = deb["medio"], deb["idMovimiento"]
    else:
        linea = alta.get("idLineaConsumo")
        fila = fetch_one(
            "SELECT l.Importe AS importe, l.IdContacto AS contacto, r.IdTarjeta AS tarjeta, "
            "ISNULL((SELECT SUM(v.ImporteImputado) FROM dbo.Tarjetas_Resumenes_Lineas_Compras v WHERE v.IdLineaConsumo = l.IdLineaConsumo), 0) AS vinc "
            "FROM dbo.Tarjetas_Resumenes_Lineas l JOIN dbo.Tarjetas_Resumenes r ON r.IdResumen = l.IdResumen WHERE l.IdLineaConsumo = ?",
            (linea,)) if linea else None
        if fila is None:
            raise CruceError(404, "La línea de consumo no existe")
        validar_consumo_devolucion(origen["importe"], float(fila["importe"]), fila["contacto"] is not None, float(fila["vinc"]),
                                   fila["tarjeta"], id_tarjeta)
        if any(c["IdLineaConsumo"] == linea for c in vigentes):
            raise CruceError(409, "La línea ya está en un cruce vigente")
    nuevo_id = execute_insert_returning_id(
        "INSERT INTO dbo.TarjetasCruces (Tipo, IdTarjeta, MedioOrigen, IdMovimientoOrigen, MedioDestino, IdMovimientoDestino, "
        "IdLineaConsumo, Importe, Sugerido, Usuario, Fecha, Deshecho) OUTPUT INSERTED.IdCruce "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, SYSDATETIME(), 0)",
        (tipo, id_tarjeta, origen["medio"], origen["idMovimiento"], medio_dest, id_dest, linea, origen["importe"],
         1 if alta.get("sugerido") else 0, usuario))
    return {"idCruce": nuevo_id, "tipo": tipo, "importe": origen["importe"], "usuario": usuario, "fecha": datetime.now()}


def deshacer(id_cruce: int, usuario: str) -> None:
    fila = fetch_one("SELECT Deshecho AS d FROM dbo.TarjetasCruces WHERE IdCruce = ?", (id_cruce,))
    if fila is None:
        raise CruceError(404, "El cruce no existe")
    if fila["d"]:
        raise CruceError(409, "El cruce ya estaba deshecho")
    execute_write("UPDATE dbo.TarjetasCruces SET Deshecho = 1, UsuarioDeshecho = ?, FechaDeshecho = SYSDATETIME() WHERE IdCruce = ?",
            (usuario, id_cruce))


def listar(id_tarjeta: int | None = None, incluir_deshechos: bool = False) -> list[dict]:
    condiciones, params = [], []
    if id_tarjeta is not None:
        condiciones.append("IdTarjeta = ?")
        params.append(id_tarjeta)
    if not incluir_deshechos:
        condiciones.append("Deshecho = 0")
    where = " WHERE " + " AND ".join(condiciones) if condiciones else ""
    return fetch_all(
        "SELECT IdCruce AS idCruce, Tipo AS tipo, IdTarjeta AS idTarjeta, MedioOrigen AS medioOrigen, IdMovimientoOrigen AS idMovimientoOrigen, "
        "MedioDestino AS medioDestino, IdMovimientoDestino AS idMovimientoDestino, IdLineaConsumo AS idLineaConsumo, Importe AS importe, "
        "Sugerido AS sugerido, Usuario AS usuario, Fecha AS fecha, Deshecho AS deshecho, UsuarioDeshecho AS usuarioDeshecho, "
        f"FechaDeshecho AS fechaDeshecho FROM dbo.TarjetasCruces{where} ORDER BY IdCruce DESC", tuple(params))
