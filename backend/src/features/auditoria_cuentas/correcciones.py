"""Correcciones hechas desde la revisión de una cuenta — 035 (FR-021, research D7).

Anular imputaciones es una baja lógica (`AplicacionesPago.Anulada`): no borra nada, no cambia el saldo de ninguna
cuenta (el saldo sale de los movimientos de la vista) y se puede deshacer. Cada corrección queda registrada en
`AuditoriaCorrecciones` y `AuditoriaCorreccionesCuentas` con quién, cuándo y exactamente qué aplicaciones tocó.
"""

from __future__ import annotations

import json

from src.db.connection import execute_write_transaction, fetch_all, fetch_one

REGLA_MANUAL = "anular-manual"
MAX_APLICACIONES = 2000


class CorreccionError(Exception):
    def __init__(self, codigo: int, mensaje: str):
        super().__init__(mensaje)
        self.codigo = codigo


def validar_pedido(ids: list[int], motivo: str) -> list[int]:
    ids = sorted({int(i) for i in ids})
    if not ids:
        raise CorreccionError(422, "No hay imputaciones para anular")
    if len(ids) > MAX_APLICACIONES:
        raise CorreccionError(422, f"Son demasiadas imputaciones juntas (máximo {MAX_APLICACIONES})")
    if not (motivo or "").strip():
        raise CorreccionError(422, "Falta el motivo")
    return ids


def anular_aplicaciones(id_contacto: int, ids: list[int], motivo: str, usuario: str, saldo: float) -> dict:
    from src.features.vinculos.backup import backup_verificado

    ids = validar_pedido(ids, motivo)
    marcas = ",".join("?" * len(ids))
    vigentes = fetch_all(
        f"SELECT a.IdAplicacion AS id, a.ImporteAplicado AS imp FROM dbo.AplicacionesPago a "
        f"JOIN dbo.Compras c ON c.IdDeuda = a.IdDocumentoAplicado "
        f"WHERE a.Anulada = 0 AND c.IdContacto = ? AND a.IdAplicacion IN ({marcas})", (id_contacto, *ids))
    if len(vigentes) != len(ids):
        raise CorreccionError(409, "Alguna imputación no es de esta cuenta o ya estaba anulada: actualizá la pantalla")
    importe = round(sum(float(v["imp"]) for v in vigentes), 2)
    respaldo = backup_verificado("anular-aplicaciones-035")
    resumen = {"cuentas": 1, "aplicaciones": len(ids), "importe": importe}
    resultados = execute_write_transaction([
        ("INSERT INTO dbo.AuditoriaCorrecciones (Regla, Estado, Parametros, Usuario, UsuarioAplicacion, FechaAplicacion, Respaldo, Resumen) "
         "OUTPUT INSERTED.IdCorreccion VALUES (?, 'aplicada', ?, ?, ?, SYSDATETIME(), ?, ?)",
         (REGLA_MANUAL, json.dumps({"motivo": motivo}, ensure_ascii=False), usuario, usuario, str(respaldo), json.dumps(resumen))),
        lambda r: ("INSERT INTO dbo.AuditoriaCorreccionesCuentas (IdCorreccion, IdContacto, Tildada, SaldoAntes, SaldoDespues, IdsAplicacion, Detalle) "
                   "VALUES (?, ?, 1, ?, ?, ?, ?)",
                   (r[0], id_contacto, saldo, saldo, json.dumps(ids), f"Anula {len(ids)} imputaciones por {importe:,.2f}: {motivo.strip()}")),
        (f"UPDATE dbo.AplicacionesPago SET Anulada = 1, MotivoAnulacion = ?, UsuarioAnulacion = ?, FechaAnulacion = SYSUTCDATETIME() "
         f"WHERE Anulada = 0 AND IdAplicacion IN ({marcas})", (f"Auditoría 035: {motivo.strip()}"[:200], usuario, *ids)),
    ])
    return {"idCorreccion": resultados[0], "aplicaciones": len(ids), "importe": importe, "respaldo": str(respaldo)}


def revertir(id_correccion: int, usuario: str) -> dict:
    fila = fetch_one("SELECT Estado AS e, Regla AS r FROM dbo.AuditoriaCorrecciones WHERE IdCorreccion = ?", (id_correccion,))
    if fila is None:
        raise CorreccionError(404, "La corrección no existe")
    if fila["e"] != "aplicada":
        raise CorreccionError(409, "La corrección no está aplicada")
    ids: list[int] = []
    for c in fetch_all("SELECT IdsAplicacion AS ids FROM dbo.AuditoriaCorreccionesCuentas WHERE IdCorreccion = ?", (id_correccion,)):
        ids += json.loads(c["ids"] or "[]")
    ids = sorted(set(ids))
    marcas = ",".join("?" * len(ids)) if ids else "NULL"
    execute_write_transaction([
        (f"UPDATE dbo.AplicacionesPago SET Anulada = 0, MotivoAnulacion = NULL, UsuarioAnulacion = NULL, FechaAnulacion = NULL "
         f"WHERE Anulada = 1 AND IdAplicacion IN ({marcas})", tuple(ids)),
        ("UPDATE dbo.AuditoriaCorrecciones SET Estado = 'revertida', UsuarioReversion = ?, FechaReversion = SYSDATETIME() WHERE IdCorreccion = ?",
         (usuario, id_correccion)),
    ])
    return {"idCorreccion": id_correccion, "aplicaciones": len(ids)}


def listar_de_cuenta(id_contacto: int) -> list[dict]:
    try:
        return fetch_all(
            "SELECT k.IdCorreccion AS idCorreccion, k.Regla AS regla, k.Estado AS estado, k.UsuarioAplicacion AS usuario, "
            "k.FechaAplicacion AS fecha, c.Detalle AS detalle FROM dbo.AuditoriaCorrecciones k "
            "JOIN dbo.AuditoriaCorreccionesCuentas c ON c.IdCorreccion = k.IdCorreccion WHERE c.IdContacto = ? ORDER BY k.IdCorreccion DESC",
            (id_contacto,))
    except Exception:
        return []
