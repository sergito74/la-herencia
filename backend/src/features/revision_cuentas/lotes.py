"""Lotes de cola — 036 (research D10; FR-024, FR-025, FR-031).

Un lote es una corrección registrada de la auditoría 035 (`AuditoriaCorrecciones`, con una fila por cuenta en
`AuditoriaCorreccionesCuentas`): mismo respaldo verificado, mismas casillas sin tildar de antemano y misma reversión. Nunca borra
filas y nunca escribe en `LaHerencia`.

Reglas del primer corte:
  * `aprobar-cierre` (cola A): cierra al corte las cuentas ya sanas, con la referencia del Access como evidencia.
  * `fifo-tandas` (cola B): recalcula las imputaciones por FIFO (resuelve también los hallazgos de plazo).
  * `anular-doble-descuento` (cola C): anula las imputaciones del banco que duplican lo que cubrió la tarjeta.
"""

from __future__ import annotations

import json
from datetime import date, datetime

from src.db.connection import execute_write_transaction, fetch_all, fetch_one
from src.features.revision_cuentas import cache, colas, criterios, datos, fichas

TOLERANCIA_SALDO = 1.0     # el saldo de una cuenta no puede cambiar más que el redondeo entre la simulación y la aplicación
PREFIJO_REGLA = "lote-"

REGLAS = {
    "aprobar-cierre": {"cola": "A", "descripcion": "Cierra al corte las cuentas ya sanas, con la referencia del Access como evidencia"},
    "fifo-tandas": {"cola": "B", "descripcion": "Recalcula las imputaciones por FIFO y resuelve los hallazgos de plazo de 24 meses"},
    "anular-doble-descuento": {"cola": "C", "descripcion": "Anula las imputaciones del banco que duplican lo que ya cubrió la tarjeta"},
}


class LoteError(Exception):
    """Error de negocio con su código HTTP (404, 409, 422)."""

    def __init__(self, codigo: int, mensaje: str):
        super().__init__(mensaje)
        self.codigo, self.mensaje = codigo, mensaje


# --------------------------------------------------------------------------- funciones puras

def reglas_disponibles() -> list[dict]:
    return [{"regla": r, "cola": d["cola"], "descripcion": d["descripcion"]} for r, d in REGLAS.items()]


def validar_regla(cola: str, regla: str) -> None:
    if regla not in REGLAS:
        raise LoteError(422, "Regla desconocida")
    if REGLAS[regla]["cola"] != cola:
        raise LoteError(422, f"La regla {regla} corresponde a la cola {REGLAS[regla]['cola']}, no a la {cola}")


def faltantes_para_cierre_en_bloque(crit: list[dict]) -> list[dict]:
    """Criterios sin cumplir para cerrar en bloque, sin contar C7: la propia regla confirma el inventario con la fuente `access`."""
    return [c for c in criterios.faltantes_para_cerrar(crit) if c["codigo"] != "C7"]


def candidatas_aprobar_cierre(contextos: dict[int, dict], posteriores: dict[int, dict]) -> list[dict]:
    """Cuentas de la cola A con el motivo por el que no cierran, si no cumplen, y los movimientos posteriores a la referencia del Access."""
    salida = []
    for id_contacto, ctx in contextos.items():
        if colas.asignar_cola(ctx["colas_ctx"])[0] != "A":
            continue
        crit = criterios.evaluar(ctx["criterios_ctx"])
        faltan = faltantes_para_cierre_en_bloque(crit)
        post = posteriores.get(id_contacto, {"movimientos": 0, "importe": 0.0})
        extra = {"cumple": not faltan, "motivos": [f"{c['codigo']}: {c['medido']}" for c in faltan], "posteriores": post,
                 "evidencia": next((c["evidencia"] for c in crit if c["codigo"] == "C3"), None)}
        salida.append({"idContacto": id_contacto, "razonSocial": (ctx.get("cuenta") or {}).get("razonSocial"), "saldo": ctx["saldo"], "cumple": not faltan,
                       "extra": extra, "movimientos": ctx["movimientos"], "importe": ctx["volumen"]})
    return colas.orden_de_dificultad(salida)


def elegir_a_tildar(cuentas: list[dict], ids: list[int] | None, todas: bool) -> set[int]:
    """Cuentas que quedan tildadas: con `todas`, las que cumplen la regla; con `ids`, exactamente esas (deben cumplir). Ninguna viene tildada de antemano."""
    cumplen = {c["idContacto"] for c in cuentas if c["cumple"]}
    if todas:
        return cumplen
    pedidas = set(ids or [])
    desconocidas = pedidas - {c["idContacto"] for c in cuentas}
    if desconocidas:
        raise LoteError(422, f"Cuentas que no están en el lote: {sorted(desconocidas)}")
    no_cumplen = pedidas - cumplen
    if no_cumplen:
        raise LoteError(422, f"Estas cuentas no cumplen la regla y no se pueden tildar: {sorted(no_cumplen)}")
    return pedidas


def validar_aplicacion(estado: str, tildadas: list[dict], saldos_ahora: dict[int, float]) -> None:
    """Un lote solo se aplica si está simulado, tiene cuentas tildadas y ningún saldo cambió desde la simulación (409)."""
    if estado != "simulada":
        raise LoteError(409, f"El lote está {estado}: solo se aplica un lote simulado")
    if not tildadas:
        raise LoteError(409, "No hay cuentas tildadas: tildá al menos una antes de aplicar")
    cambiaron = [c["idContacto"] for c in tildadas
                 if abs(float(saldos_ahora.get(c["idContacto"], 0.0)) - float(c["saldoAntes"] or 0.0)) > TOLERANCIA_SALDO]
    if cambiaron:
        raise LoteError(409, f"El saldo de estas cuentas cambió desde la simulación: {cambiaron}. Simulá el lote de nuevo")


def validar_reversion(estado: str) -> None:
    if estado != "aplicada":
        raise LoteError(409, "El lote no está aplicado: no hay nada para revertir")


def validar_descarte(estado: str) -> None:
    if estado != "simulada":
        raise LoteError(409, "Solo se descarta un lote simulado; uno aplicado se revierte")


def regla_de_correccion(nombre: str) -> tuple[str, str]:
    """`lote-A-aprobar-cierre` → (`A`, `aprobar-cierre`)."""
    _, cola, regla = nombre.split("-", 2)
    return cola, regla


# --------------------------------------------------------------------------- lectura y escritura de la base

def _leer(id_correccion: int) -> dict:
    f = fetch_one("SELECT IdCorreccion, Regla, Estado, Parametros, Respaldo, Resumen FROM dbo.AuditoriaCorrecciones WHERE IdCorreccion = ?", (id_correccion,))
    if f is None or not str(f["Regla"]).startswith(PREFIJO_REGLA):
        raise LoteError(404, "El lote no existe")
    cuentas = fetch_all("SELECT c.IdContacto, c.Tildada, c.SaldoAntes, c.SaldoDespues, c.IdsAplicacion, c.Detalle, k.[Razon Social] AS razon "
                        "FROM dbo.AuditoriaCorreccionesCuentas c LEFT JOIN dbo.Contactos k ON k.IdContacto = c.IdContacto WHERE c.IdCorreccion = ?", (id_correccion,))
    cola, regla = regla_de_correccion(f["Regla"])
    filas = []
    for c in cuentas:
        try:
            extra = json.loads(c["Detalle"] or "{}")
        except ValueError:
            extra = {}
        filas.append({"idContacto": int(c["IdContacto"]), "razonSocial": c["razon"], "tildada": bool(c["Tildada"]), "cumple": bool(extra.get("cumple", True)),
                      "saldoAntes": None if c["SaldoAntes"] is None else float(c["SaldoAntes"]),
                      "saldoDespues": None if c["SaldoDespues"] is None else float(c["SaldoDespues"]), "detalle": _texto(extra), "extra": extra,
                      "idsAplicacion": c["IdsAplicacion"]})
    return {"idCorreccion": int(f["IdCorreccion"]), "regla": regla, "cola": cola, "estado": f["Estado"], "respaldo": f["Respaldo"],
            "parametros": json.loads(f["Parametros"] or "{}"), "cuentas": filas}


def _texto(extra: dict) -> str:
    partes = []
    if not extra.get("cumple", True):
        partes.append("No cumple: " + "; ".join(extra.get("motivos", [])))
    post = extra.get("posteriores") or {}
    if post.get("movimientos"):
        partes.append(f"{post['movimientos']} movimientos posteriores a la referencia del Access por revisar")
    if extra.get("nota"):
        partes.append(extra["nota"])
    return ". ".join(partes)


def respuesta(lote: dict) -> dict:
    return {"idCorreccion": lote["idCorreccion"], "regla": lote["regla"], "cola": lote["cola"], "estado": lote["estado"], "respaldo": lote["respaldo"],
            "cuentas": [{k: c[k] for k in ("idContacto", "razonSocial", "tildada", "cumple", "saldoAntes", "saldoDespues", "detalle")} for c in lote["cuentas"]]}


def obtener(id_correccion: int) -> dict:
    return respuesta(_leer(id_correccion))


def _crear(cola: str, regla: str, parametros: dict, cuentas: list[dict], usuario: str) -> int:
    """Crea la corrección `simulada` y una fila por cuenta con `Tildada = 0` (no cambia nada más)."""
    resumen = {"cuentas": len(cuentas), "cumplen": sum(1 for c in cuentas if c["cumple"])}
    operaciones: list = [("INSERT INTO dbo.AuditoriaCorrecciones (Regla, Estado, Parametros, Usuario, Resumen) OUTPUT INSERTED.IdCorreccion VALUES (?, 'simulada', ?, ?, ?)",
                          (f"{PREFIJO_REGLA}{cola}-{regla}", json.dumps(parametros, ensure_ascii=False, default=str), usuario, json.dumps(resumen)))]
    for c in cuentas:
        operaciones.append(lambda r, c=c: ("INSERT INTO dbo.AuditoriaCorreccionesCuentas (IdCorreccion, IdContacto, Tildada, SaldoAntes, SaldoDespues, Detalle) VALUES (?, ?, 0, ?, ?, ?)",
                                           (r[0], c["idContacto"], c["saldo"], c["saldo"], json.dumps(c["extra"], ensure_ascii=False, default=str))))
    return execute_write_transaction(operaciones)[0]


def _marcar_tildadas(id_correccion: int, tildadas: set[int]) -> None:
    operaciones = [("UPDATE dbo.AuditoriaCorreccionesCuentas SET Tildada = 0 WHERE IdCorreccion = ?", (id_correccion,))]
    for i in sorted(tildadas):
        operaciones.append(("UPDATE dbo.AuditoriaCorreccionesCuentas SET Tildada = 1 WHERE IdCorreccion = ? AND IdContacto = ?", (id_correccion, i)))
    execute_write_transaction(operaciones)


def _poner_estado(id_correccion: int, estado: str, usuario: str | None = None, respaldo: str | None = None, aplicacion: bool = False, reversion: bool = False) -> None:
    sql, params = "UPDATE dbo.AuditoriaCorrecciones SET Estado = ?", [estado]
    if aplicacion:
        sql += ", UsuarioAplicacion = ?, FechaAplicacion = SYSDATETIME(), Respaldo = ?"
        params += [usuario, respaldo]
    if reversion:
        sql += ", UsuarioReversion = ?, FechaReversion = SYSDATETIME()"
        params += [usuario]
    execute_write_transaction([(sql + " WHERE IdCorreccion = ?", tuple(params + [id_correccion]))])


# --------------------------------------------------------------------------- simular, tildar, descartar

def _candidatas(cola: str, regla: str, corte: date, usuario: str) -> tuple[list[dict], dict]:
    contextos = fichas.cargar_contextos(corte)
    if regla == "aprobar-cierre":
        referencia = _fecha_de_referencia_del_access()
        posteriores = _movimientos_posteriores(referencia, corte)
        return candidatas_aprobar_cierre(contextos, posteriores), {"referenciaAccess": str(referencia)}
    if regla == "anular-doble-descuento":
        from src.features.revision_cuentas import dobles
        return dobles.candidatas(contextos)
    if regla == "fifo-tandas":
        from src.features.revision_cuentas import fifo_lote
        return fifo_lote.candidatas(contextos, usuario)
    raise LoteError(422, "Regla desconocida")


def _fecha_de_referencia_del_access() -> date:
    from src.features.auditoria_cuentas import datos as datos_035

    return datos_035.fecha_corte()


def _movimientos_posteriores(referencia: date, corte: date) -> dict[int, dict]:
    """Movimientos posteriores a la referencia del Access y hasta el corte (para que Sergio los revise en el lote)."""
    filas = fetch_all("SELECT IdContacto AS i, COUNT(*) AS n, SUM(ABS(Credito - Deuda)) AS s FROM dbo.vw_MovimientosCuenta_Base "
                      "WHERE IdContacto IS NOT NULL AND Fecha >= ? AND Fecha < ? GROUP BY IdContacto",
                      (datos._dia_siguiente(referencia), datos._dia_siguiente(corte)))
    return {int(f["i"]): {"movimientos": int(f["n"]), "importe": round(float(f["s"] or 0), 2)} for f in filas}


def simular(cola: str, regla: str, usuario: str) -> dict:
    """Crea el lote en estado `simulada` con una fila por cuenta (ninguna tildada). No cambia nada de las cuentas."""
    validar_regla(cola, regla)
    vigente = fichas.corte_vigente()
    if vigente is None:
        raise LoteError(404, "Todavía no hay un corte definido")
    cuentas, parametros = _candidatas(cola, regla, vigente["corte"], usuario)
    id_correccion = _crear(cola, regla, {"cola": cola, "regla": regla, "corte": str(vigente["corte"]), **parametros}, cuentas, usuario)
    return obtener(id_correccion)


def tildar(id_correccion: int, ids: list[int] | None, todas: bool) -> dict:
    lote = _leer(id_correccion)
    if lote["estado"] != "simulada":
        raise LoteError(409, "El lote no está simulado: no se pueden cambiar las cuentas tildadas")
    elegidas = elegir_a_tildar(lote["cuentas"], ids, todas)
    _marcar_tildadas(id_correccion, elegidas)
    return obtener(id_correccion)


def descartar(id_correccion: int) -> None:
    lote = _leer(id_correccion)
    validar_descarte(lote["estado"])
    if lote["regla"] == "fifo-tandas":
        from src.features.revision_cuentas import fifo_lote
        fifo_lote.descartar(lote)   # también descarta la simulación del FIFO que dejó el lote
    _poner_estado(id_correccion, "descartada")


# --------------------------------------------------------------------------- aplicar y revertir

def aplicar(id_correccion: int, usuario: str) -> dict:
    """Aplica el lote: respaldo verificado, saldos sin cambios desde la simulación, una sola transacción y reversión disponible."""
    lote = _leer(id_correccion)
    tildadas = [c for c in lote["cuentas"] if c["tildada"]]
    vigente = fichas.corte_vigente()
    corte = vigente["corte"] if vigente else date.today()
    ahora = datos.saldos_al_corte(corte) if tildadas else {}
    validar_aplicacion(lote["estado"], tildadas, ahora)
    from src.features.vinculos.backup import backup_verificado

    respaldo = backup_verificado(f"lote-036-{id_correccion}")
    if lote["regla"] == "aprobar-cierre":
        _aplicar_cierre(lote, tildadas, corte, usuario)
    elif lote["regla"] == "anular-doble-descuento":
        from src.features.revision_cuentas import dobles
        dobles.aplicar(lote, tildadas, usuario)
    elif lote["regla"] == "fifo-tandas":
        from src.features.revision_cuentas import fifo_lote
        fifo_lote.aplicar(lote, tildadas, usuario)
    _poner_estado(id_correccion, "aplicada", usuario, str(respaldo), aplicacion=True)
    cache.invalidar()
    return obtener(id_correccion)


def _aplicar_cierre(lote: dict, tildadas: list[dict], corte: date, usuario: str) -> None:
    """Cierra al corte las cuentas tildadas, con la fuente `access` en el inventario. Guarda la ficha previa de cada una para revertir."""
    ids = [c["idContacto"] for c in tildadas]
    contextos = fichas.cargar_contextos(corte, ids)
    fichas.cerrar_en_bloque(lote["idCorreccion"], contextos, tildadas, corte, usuario)


def revertir(id_correccion: int, usuario: str) -> dict:
    lote = _leer(id_correccion)
    validar_reversion(lote["estado"])
    if lote["regla"] == "aprobar-cierre":
        fichas.revertir_cierre_en_bloque(lote["idCorreccion"], [c for c in lote["cuentas"] if c["tildada"]], usuario)
        _poner_estado(id_correccion, "revertida", usuario, reversion=True)
    elif lote["regla"] == "anular-doble-descuento":
        from src.features.revision_cuentas import dobles
        dobles.revertir(lote, usuario)
        _poner_estado(id_correccion, "revertida", usuario, reversion=True)
    elif lote["regla"] == "fifo-tandas":
        from src.features.revision_cuentas import fifo_lote
        fifo_lote.revertir(lote, usuario)
        _poner_estado(id_correccion, "revertida", usuario, reversion=True)
    cache.invalidar()
    return obtener(id_correccion)
