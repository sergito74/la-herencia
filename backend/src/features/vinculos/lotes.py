"""Lotes de corrección (031, US2): persistir la propuesta, revisarla,
aplicarla con backup verificado y revertirla. Nada se borra: las
aplicaciones erróneas se anulan con `MotivoAnulacion = '031:<IdLote>: …'`
y las nuevas se crean con `Origen = 'correccion-031'`."""

from __future__ import annotations

import json
from collections import Counter

from src.db.connection import execute_write, execute_write_transaction, fetch_all
from src.features.vinculos import control, correccion, fuente
from src.features.vinculos.backup import backup_verificado

ORIGEN_CORRECCION = "correccion-031"


class LoteConflicto(Exception):
    """El lote no está en un estado que permita la operación (409)."""


def _prefijo(id_lote: int) -> str:
    return f"031:{id_lote}:"


def crear_lote(usuario: str) -> dict:
    raw = fuente.cargar()
    items = correccion.proponer(raw, control.hallazgos(raw))
    resumen = Counter(i["grupo"] for i in items)
    statements: list = [(
        "INSERT INTO dbo.CorreccionVinculosLote (Usuario, Resumen) OUTPUT INSERTED.IdLote VALUES (?, ?)",
        (usuario, json.dumps(resumen)),
    )]
    for i in items:
        statements.append(lambda res, i=i: (
            # Nada entra al lote hasta que Sergio apruebe el proveedor (Incluido = 0).
            "INSERT INTO dbo.CorreccionVinculosItem (IdLote, Grupo, Accion, IdAplicacion, OrigenMovimiento, "
            "IdMovimientoOrigen, TipoDocumento, IdDocumento, Importe, Motivo, Candidatos, Elegido, Incluido, IdContacto) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)",
            (res[0], i["grupo"], i["accion"], i["idAplicacion"], i["origenMovimiento"], i["idMovimientoOrigen"],
             i["tipoDocumento"], i["idDocumento"], i["importe"], i["motivo"][:400],
             json.dumps(i["candidatos"]) if i["candidatos"] else None, 1 if i["elegido"] else 0, i.get("idContacto"))))
    id_lote = execute_write_transaction(statements)[0]
    return {"idLote": id_lote, **resumen_lote(id_lote)}


def _lote(id_lote: int) -> dict:
    filas = fetch_all("SELECT IdLote AS idLote, Estado AS estado, FechaPropuesta AS fechaPropuesta, FechaAplicado AS fechaAplicado, "
                      "FechaRevertido AS fechaRevertido, Usuario AS usuario, BackupArchivo AS backupArchivo "
                      "FROM dbo.CorreccionVinculosLote WHERE IdLote = ?", (id_lote,))
    if not filas:
        raise KeyError(id_lote)
    return filas[0]


def resumen_lote(id_lote: int) -> dict:
    grupos = fetch_all(
        "SELECT Grupo AS grupo, Accion AS accion, COUNT(*) AS cantidad, SUM(CASE WHEN Incluido = 1 THEN 1 ELSE 0 END) AS incluidos, "
        "SUM(ISNULL(Importe, 0)) AS importe FROM dbo.CorreccionVinculosItem WHERE IdLote = ? GROUP BY Grupo, Accion "
        "ORDER BY Grupo, Accion", (id_lote,))
    ambiguos = fetch_all(
        "SELECT COUNT(*) AS n FROM dbo.CorreccionVinculosItem WHERE IdLote = ? AND Accion = 'reemplazo' "
        "AND Incluido = 1 AND Elegido = 0", (id_lote,))[0]["n"]
    return {"grupos": grupos, "ambiguosSinElegir": ambiguos}


def listar_lotes() -> list[dict]:
    return fetch_all("SELECT IdLote AS idLote, Estado AS estado, FechaPropuesta AS fechaPropuesta, FechaAplicado AS fechaAplicado, "
                     "FechaRevertido AS fechaRevertido, Usuario AS usuario FROM dbo.CorreccionVinculosLote ORDER BY IdLote DESC")


def obtener(id_lote: int, grupo: str | None = None, pagina: int = 1, tamanio: int = 100) -> dict:
    lote = _lote(id_lote)
    filtro, params = ("AND Grupo = ?", (id_lote, grupo)) if grupo else ("", (id_lote,))
    items = fetch_all(
        "SELECT IdItem AS idItem, Grupo AS grupo, Accion AS accion, IdAplicacion AS idAplicacion, "
        "OrigenMovimiento AS origenMovimiento, IdMovimientoOrigen AS idMovimientoOrigen, TipoDocumento AS tipoDocumento, "
        "IdDocumento AS idDocumento, Importe AS importe, Motivo AS motivo, Candidatos AS candidatos, "
        "Incluido AS incluido, Elegido AS elegido, IdAplicacionCreada AS idAplicacionCreada "
        f"FROM dbo.CorreccionVinculosItem WHERE IdLote = ? {filtro} ORDER BY Grupo, IdItem "
        f"OFFSET {max(pagina - 1, 0) * tamanio} ROWS FETCH NEXT {int(tamanio)} ROWS ONLY", params)
    for i in items:
        i["candidatos"] = json.loads(i["candidatos"]) if i["candidatos"] else None
        i["incluido"], i["elegido"] = bool(i["incluido"]), bool(i["elegido"])
    return {**lote, **resumen_lote(id_lote), "items": items}


def _exigir_estado(id_lote: int, estado: str) -> dict:
    lote = _lote(id_lote)
    if lote["estado"] != estado:
        raise LoteConflicto(f"El lote {id_lote} está '{lote['estado']}', se esperaba '{estado}'")
    return lote


def actualizar_items(id_lote: int, incluir: list[int], excluir: list[int], elegir: list[dict], incluir_grupo: str | None = None,
                     excluir_grupo: str | None = None) -> dict:
    _exigir_estado(id_lote, "propuesto")
    statements: list = []
    for grupo, valor in ((incluir_grupo, 1), (excluir_grupo, 0)):
        if grupo:
            statements.append(("UPDATE dbo.CorreccionVinculosItem SET Incluido = ? WHERE IdLote = ? AND Grupo = ?", (valor, id_lote, grupo)))
    for id_item in incluir:
        statements.append(("UPDATE dbo.CorreccionVinculosItem SET Incluido = 1 WHERE IdLote = ? AND IdItem = ?", (id_lote, id_item)))
    for id_item in excluir:
        statements.append(("UPDATE dbo.CorreccionVinculosItem SET Incluido = 0 WHERE IdLote = ? AND IdItem = ?", (id_lote, id_item)))
    for e in elegir:
        fila = fetch_all("SELECT Candidatos AS c FROM dbo.CorreccionVinculosItem WHERE IdLote = ? AND IdItem = ? AND Accion = 'reemplazo'",
                         (id_lote, e["idItem"]))
        candidatos = json.loads(fila[0]["c"]) if fila and fila[0]["c"] else []
        if not 0 <= e["candidato"] < len(candidatos):
            raise ValueError(f"Candidato inválido para el ítem {e['idItem']}")
        c = candidatos[e["candidato"]]
        usado = fetch_all(
            "SELECT COUNT(*) AS n FROM dbo.CorreccionVinculosItem WHERE IdLote = ? AND IdItem <> ? AND Accion = 'reemplazo' "
            "AND Elegido = 1 AND Incluido = 1 AND OrigenMovimiento = ? AND IdMovimientoOrigen = ? AND TipoDocumento = ? AND IdDocumento = ?",
            (id_lote, e["idItem"], c["origenMovimiento"], c["idMovimientoOrigen"], c["tipoDocumento"], c["idDocumento"]))[0]["n"]
        if usado:
            raise LoteConflicto("Ese candidato ya está elegido para otro reemplazo del lote")
        statements.append((
            # Si el proveedor ya está aprobado, el reemplazo elegido entra al lote.
            "UPDATE i SET OrigenMovimiento = ?, IdMovimientoOrigen = ?, TipoDocumento = ?, IdDocumento = ?, Elegido = 1, "
            "Incluido = CASE WHEN EXISTS (SELECT 1 FROM dbo.CorreccionVinculosRevision r WHERE r.IdLote = i.IdLote "
            "AND r.IdContacto = ISNULL(i.IdContacto, 0) AND r.Estado = 'aprobado') THEN 1 ELSE i.Incluido END "
            "FROM dbo.CorreccionVinculosItem i WHERE i.IdLote = ? AND i.IdItem = ?",
            (c["origenMovimiento"], c["idMovimientoOrigen"], c["tipoDocumento"], c["idDocumento"], id_lote, e["idItem"])))
    if statements:
        execute_write_transaction(statements)
    return resumen_lote(id_lote)


def aplicar(id_lote: int, usuario: str, backup=backup_verificado) -> dict:
    _exigir_estado(id_lote, "propuesto")
    if resumen_lote(id_lote)["ambiguosSinElegir"]:
        raise LoteConflicto("Hay reemplazos ambiguos incluidos sin elegir")
    items = fetch_all(
        "SELECT IdItem AS idItem, Accion AS accion, IdAplicacion AS idAplicacion, OrigenMovimiento AS origenMovimiento, "
        "IdMovimientoOrigen AS idMovimientoOrigen, TipoDocumento AS tipoDocumento, IdDocumento AS idDocumento, "
        "Importe AS importe, Motivo AS motivo FROM dbo.CorreccionVinculosItem WHERE IdLote = ? AND Incluido = 1 ORDER BY IdItem",
        (id_lote,))
    ruta = backup(f"pre_031_lote{id_lote}")  # si falla, lanza y no se escribe nada (FR-008)

    statements: list = []
    for i in items:
        if i["accion"] in ("anular", "pesificar"):
            statements.append((
                "UPDATE dbo.AplicacionesPago SET Anulada = 1, MotivoAnulacion = ?, UsuarioAnulacion = ?, "
                "FechaAnulacion = SYSUTCDATETIME() WHERE IdAplicacion = ? AND Anulada = 0",
                (f"{_prefijo(id_lote)} {i['motivo']}"[:255], usuario[:60], i["idAplicacion"])))
    for i in items:
        if i["accion"] in ("pesificar", "reemplazo"):
            indice = len(statements)
            statements.append((
                "INSERT INTO dbo.AplicacionesPago (OrigenMovimiento, IdMovimientoOrigen, TipoDocumento, IdDocumentoAplicado, "
                "ImporteAplicado, Usuario, Origen, NotaConciliacion) OUTPUT INSERTED.IdAplicacion VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (i["origenMovimiento"], i["idMovimientoOrigen"], i["tipoDocumento"], i["idDocumento"], float(i["importe"]),
                 usuario[:60], ORIGEN_CORRECCION, f"Lote 031:{id_lote} — {i['motivo']}"[:255])))
            statements.append(lambda res, indice=indice, id_item=i["idItem"]: (
                "UPDATE dbo.CorreccionVinculosItem SET IdAplicacionCreada = ? WHERE IdItem = ?", (res[indice], id_item)))
    statements.append(("UPDATE dbo.CorreccionVinculosLote SET Estado = 'aplicado', FechaAplicado = SYSUTCDATETIME(), "
                       "BackupArchivo = ? WHERE IdLote = ? AND Estado = 'propuesto'", (ruta, id_lote)))
    n_anular = sum(1 for i in items if i["accion"] in ("anular", "pesificar"))
    resultados = execute_write_transaction(statements)
    anuladas = sum(resultados[:n_anular])
    creadas = sum(1 for i in items if i["accion"] in ("pesificar", "reemplazo"))
    return {"anuladas": anuladas, "creadas": creadas, "backup": ruta}


def revertir(id_lote: int, usuario: str) -> dict:
    _exigir_estado(id_lote, "aplicado")
    items = fetch_all("SELECT Accion AS accion, IdAplicacion AS idAplicacion, IdAplicacionCreada AS idAplicacionCreada "
                      "FROM dbo.CorreccionVinculosItem WHERE IdLote = ? AND Incluido = 1", (id_lote,))
    statements: list = []
    for i in items:
        if i["accion"] in ("anular", "pesificar") and i["idAplicacion"]:
            statements.append((
                "UPDATE dbo.AplicacionesPago SET Anulada = 0, MotivoAnulacion = NULL, UsuarioAnulacion = NULL, FechaAnulacion = NULL "
                "WHERE IdAplicacion = ? AND Anulada = 1 AND MotivoAnulacion LIKE ?", (i["idAplicacion"], _prefijo(id_lote) + "%")))
    reactivadas_n = len(statements)
    for i in items:
        if i["idAplicacionCreada"]:
            statements.append((
                "UPDATE dbo.AplicacionesPago SET Anulada = 1, MotivoAnulacion = ?, UsuarioAnulacion = ?, "
                "FechaAnulacion = SYSUTCDATETIME() WHERE IdAplicacion = ? AND Anulada = 0",
                (f"{_prefijo(id_lote)} reversión del lote", usuario[:60], i["idAplicacionCreada"])))
    statements.append(("UPDATE dbo.CorreccionVinculosLote SET Estado = 'revertido', FechaRevertido = SYSUTCDATETIME() "
                       "WHERE IdLote = ? AND Estado = 'aplicado'", (id_lote,)))
    resultados = execute_write_transaction(statements)
    return {"reactivadas": sum(resultados[:reactivadas_n]), "anuladas": sum(resultados[reactivadas_n:-1])}


def descartar(id_lote: int) -> None:
    _exigir_estado(id_lote, "propuesto")
    execute_write("UPDATE dbo.CorreccionVinculosLote SET Estado = 'descartado' WHERE IdLote = ?", (id_lote,))
