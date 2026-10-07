"""Asignar contacto a movimientos del banco que no lo tienen — 035 (T053, FR-023).

Uno a uno, varios a la vez o todos los de un concepto (la regla). Corrige el contacto del propio movimiento
(`Movimientos BNA` / `Movimientos Galicia`) y solo si hoy no tiene contacto: nunca pisa uno ya asignado. Cada asignación
queda registrada en `AuditoriaCorrecciones` con el estado anterior de cada movimiento y se puede deshacer.
"""

from __future__ import annotations

import json
from datetime import date, datetime

from src.db.connection import execute_write_transaction, fetch_all, fetch_one
from src.features.auditoria_cuentas import conocidos, hallazgos as detectores

REGLA = "asignar-contacto"
MAX_MOVIMIENTOS = 500
TABLAS = {
    "bna": ("dbo.[Movimientos BNA]", "IdMovimientoBNA", "[Fecha / Hora Mov#]", "Importe", "Concepto"),
    "galicia": ("dbo.[Movimientos Galicia]", "IdMovimiento", "Fecha", "ISNULL([Créditos], 0) - ISNULL([Débitos], 0)", "[Descripción]"),
}


class AsignacionError(Exception):
    def __init__(self, codigo: int, mensaje: str):
        super().__init__(mensaje)
        self.codigo = codigo


def validar_pedido(items: list[dict], id_contacto: int, motivo: str) -> dict[str, list[int]]:
    """Agrupa por medio y valida: hay movimientos, no son demasiados, el medio existe y hay motivo."""
    if not items:
        raise AsignacionError(422, "No hay movimientos para asignar")
    if len(items) > MAX_MOVIMIENTOS:
        raise AsignacionError(422, f"Son demasiados movimientos juntos (máximo {MAX_MOVIMIENTOS})")
    if not (motivo or "").strip():
        raise AsignacionError(422, "Falta el motivo")
    if not id_contacto or id_contacto <= 0:
        raise AsignacionError(422, "Falta el contacto")
    por_medio: dict[str, set[int]] = {}
    for it in items:
        if it.get("medio") not in TABLAS:
            raise AsignacionError(422, f"Medio desconocido: {it.get('medio')}")
        por_medio.setdefault(it["medio"], set()).add(int(it["idMovimiento"]))
    return {m: sorted(ids) for m, ids in por_medio.items()}


def movimientos_sin_contacto(concepto_normalizado: str | None = None, limite: int = 300) -> list[dict]:
    """Movimientos del banco sin contacto, sin conciliación ni cruce (los mismos que el control)."""
    corte = datetime.now()
    todos = []
    for f in fetch_all(
            "SELECT IdMovimientoBNA AS i, [Fecha / Hora Mov#] AS f, Importe AS m, Concepto AS c FROM dbo.[Movimientos BNA] b WHERE ISNULL(IdContacto, 0) = 0 "
            "AND NOT EXISTS (SELECT 1 FROM dbo.ConciliacionesTesoreria t WHERE t.Medio = 'bna' AND t.IdMovimiento = b.IdMovimientoBNA) "
            "AND NOT EXISTS (SELECT 1 FROM dbo.TarjetasCruces x WHERE x.Deshecho = 0 AND x.MedioOrigen = 'bna' AND x.IdMovimientoOrigen = b.IdMovimientoBNA)", ()):
        todos.append({"medio": "bna", "idMovimiento": f["i"], "fecha": f["f"], "importe": float(f["m"] or 0), "concepto": f["c"]})
    for f in fetch_all(
            "SELECT IdMovimiento AS i, Fecha AS f, ISNULL([Créditos], 0) - ISNULL([Débitos], 0) AS m, [Descripción] AS c FROM dbo.[Movimientos Galicia] g "
            "WHERE ISNULL(IdContacto, 0) = 0 AND NOT EXISTS (SELECT 1 FROM dbo.ConciliacionesTesoreria t WHERE t.Medio = 'galicia' AND t.IdMovimiento = g.IdMovimiento) "
            "AND NOT EXISTS (SELECT 1 FROM dbo.TarjetasCruces x WHERE x.Deshecho = 0 AND x.MedioOrigen = 'galicia' AND x.IdMovimientoOrigen = g.IdMovimiento)", ()):
        todos.append({"medio": "galicia", "idMovimiento": f["i"], "fecha": f["f"], "importe": float(f["m"] or 0), "concepto": f["c"]})
    reglas = [k["clave"] for k in conocidos.listar() if k["tipo"] == "concepto-movimiento"]
    res = []
    for m in todos:
        if detectores.explicado_por(m["concepto"], reglas):
            continue
        if concepto_normalizado is not None and detectores.normalizar_concepto(m["concepto"]) != concepto_normalizado:
            continue
        m["fecha"] = m["fecha"].date() if isinstance(m["fecha"], datetime) else m["fecha"]
        res.append(m)
    res.sort(key=lambda m: (m["fecha"] or date.min, m["medio"], m["idMovimiento"]), reverse=True)
    return res[:limite]


def asignar(items: list[dict], id_contacto: int, motivo: str, usuario: str) -> dict:
    from src.features.vinculos.backup import backup_verificado

    por_medio = validar_pedido(items, id_contacto, motivo)
    contacto = fetch_one("SELECT [Razon Social] AS rs FROM dbo.Contactos WHERE IdContacto = ?", (id_contacto,))
    if contacto is None:
        raise AsignacionError(404, "El contacto no existe")
    antes: list[dict] = []
    for medio, ids in por_medio.items():
        tabla, col_id, _, _, _ = TABLAS[medio]
        marcas = ",".join("?" * len(ids))
        filas = fetch_all(f"SELECT {col_id} AS id, IdContacto AS c, Contacto AS n FROM {tabla} WHERE {col_id} IN ({marcas})", tuple(ids))
        if len(filas) != len(ids):
            raise AsignacionError(404, "Algún movimiento no existe")
        asignados = [f["id"] for f in filas if f["c"] not in (None, 0)]
        if asignados:
            raise AsignacionError(409, f"Hay movimientos que ya tienen contacto: actualizá la pantalla ({asignados[:5]})")
        antes += [{"medio": medio, "id": f["id"], "contactoAntes": f["c"], "nombreAntes": f["n"]} for f in filas]
    respaldo = backup_verificado("asignar-contacto-035")
    resumen = {"cuentas": 1, "movimientos": len(antes), "contacto": contacto["rs"]}
    sentencias = [
        ("INSERT INTO dbo.AuditoriaCorrecciones (Regla, Estado, Parametros, Usuario, UsuarioAplicacion, FechaAplicacion, Respaldo, Resumen) "
         "OUTPUT INSERTED.IdCorreccion VALUES (?, 'aplicada', ?, ?, ?, SYSDATETIME(), ?, ?)",
         (REGLA, json.dumps({"motivo": motivo, "idContacto": id_contacto}, ensure_ascii=False), usuario, usuario, str(respaldo), json.dumps(resumen, ensure_ascii=False))),
        lambda r: ("INSERT INTO dbo.AuditoriaCorreccionesCuentas (IdCorreccion, IdContacto, Tildada, SaldoAntes, SaldoDespues, IdsAplicacion, Detalle) "
                   "VALUES (?, ?, 1, NULL, NULL, ?, ?)",
                   (r[0], id_contacto, json.dumps(antes), f"Asigna {len(antes)} movimientos del banco a {contacto['rs']}: {motivo.strip()}"[:500])),
    ]
    for medio, ids in por_medio.items():
        tabla, col_id, _, _, _ = TABLAS[medio]
        marcas = ",".join("?" * len(ids))
        sentencias.append((f"UPDATE {tabla} SET IdContacto = ?, Contacto = ? WHERE {col_id} IN ({marcas}) AND ISNULL(IdContacto, 0) = 0",
                           (id_contacto, contacto["rs"], *ids)))
    resultados = execute_write_transaction(sentencias)
    return {"idCorreccion": resultados[0], "movimientos": len(antes), "contacto": contacto["rs"], "respaldo": str(respaldo)}


def revertir(id_correccion: int, usuario: str) -> dict:
    """Devuelve cada movimiento al contacto que tenía (ninguno) si todavía conserva el asignado."""
    fila = fetch_one("SELECT Estado AS e, Regla AS r FROM dbo.AuditoriaCorrecciones WHERE IdCorreccion = ?", (id_correccion,))
    if fila is None or fila["r"] != REGLA:
        raise AsignacionError(404, "La asignación no existe")
    if fila["e"] != "aplicada":
        raise AsignacionError(409, "La asignación no está aplicada")
    c = fetch_one("SELECT IdContacto AS c, IdsAplicacion AS ids FROM dbo.AuditoriaCorreccionesCuentas WHERE IdCorreccion = ?", (id_correccion,))
    antes = json.loads(c["ids"] or "[]")
    sentencias = []
    for a in antes:
        tabla, col_id, _, _, _ = TABLAS[a["medio"]]
        sentencias.append((f"UPDATE {tabla} SET IdContacto = ?, Contacto = ? WHERE {col_id} = ? AND IdContacto = ?",
                           (a["contactoAntes"], a["nombreAntes"], a["id"], c["c"])))
    sentencias.append(("UPDATE dbo.AuditoriaCorrecciones SET Estado = 'revertida', UsuarioReversion = ?, FechaReversion = SYSDATETIME() WHERE IdCorreccion = ?",
                       (usuario, id_correccion)))
    execute_write_transaction(sentencias)
    return {"idCorreccion": id_correccion, "movimientos": len(antes)}
