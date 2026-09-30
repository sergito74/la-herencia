"""Conciliación de Tesorería (023) — ver
specs/023-conciliacion-tesoreria/{research,data-model}.md.

`ConciliacionesTesoreria` es insert-only (nunca UPDATE/DELETE), mismo
patrón que `MovimientosCuentaSocio` (021) y `ReasignacionesContacto` (022):
cada fila es una "parte" de la conciliación de un movimiento. El estado
(sin conciliar / parcialmente conciliado / conciliado / ya reconocido) y el
saldo pendiente NUNCA se guardan — se recalculan siempre a partir de la
tabla de origen del medio + las filas ya insertadas, para no poder
desincronizarse.

`vw_MovimientosCuenta_Base` ya lee esta tabla (scripts/
crear_tabla_conciliaciones_tesoreria.py) con Origen = 'Conciliación
Tesorería', así que una vez insertada una conciliación el efecto en la
cuenta corriente del contacto es automático — este módulo nunca escribe
directamente en `vw_MovimientosCuenta_Base` ni en ninguna cuenta corriente.
"""

from __future__ import annotations

from typing import NamedTuple

from src.db.connection import (
    atomic_reconciliation,
    execute_write,
    execute_write_transaction,
    fetch_all,
    fetch_one,
)
from src.features.conciliacion_tesoreria import documentos, documentos_adapter

# Mismo criterio que tarjetas_resumenes/conciliacion_documentos.py: una
# diferencia de centavos por redondeo no debe impedir que un movimiento
# quede "conciliado por completo".
TOLERANCIA_REDONDEO = 0.10

MEDIOS_SOPORTADOS = (
    "bna",
    "galicia",
    "mercado-libre",
    "efectivo",
    "valores-propios",
    "valores-recibidos",
)


class _MedioInfo(NamedTuple):
    tabla: str
    id_col: str
    contacto_col: (
        str | None
    )  # None si la tabla no tiene columna de contacto (valores-propios/valores-recibidos)
    importe_expr: str  # expresión SQL del importe con signo, tal como está en la tabla de origen
    fecha_col: str


# bna/galicia/mercado-libre son bidireccionales (Debe o Haber según el
# signo real del movimiento bancario); efectivo/valores-propios/
# valores-recibidos son de una sola dirección (instrumentos de pago) —
# mismo criterio que sus ramas existentes o análogas en
# vw_MovimientosCuenta_Base (ver crear_tabla_conciliaciones_tesoreria.py).
_MEDIOS: dict[str, _MedioInfo] = {
    "bna": _MedioInfo(
        "dbo.[Movimientos BNA]", "IdMovimientoBNA", "IdContacto", "Importe", "[Fecha / Hora Mov#]"
    ),
    "galicia": _MedioInfo(
        "dbo.[Movimientos Galicia]",
        "IdMovimiento",
        "IdContacto",
        "(ISNULL([Créditos], 0) - ISNULL([Débitos], 0))",
        "Fecha",
    ),
    "mercado-libre": _MedioInfo(
        "dbo.[Movimientos Mercado Libre]", "IdMovimiento", "IdContacto", "Importe", "Fecha"
    ),
    "efectivo": _MedioInfo(
        "dbo.[Pagos efectivo]", "IdPagoEfectivo", "IdContacto", "[Importe imputado]", "Fecha"
    ),
    "valores-propios": _MedioInfo(
        "dbo.[Valores propios]", "IdValor", None, "Importe", "[Fecha emision]"
    ),
    "valores-recibidos": _MedioInfo(
        "dbo.[Valores Recibidos]", "IdValor", None, "Importe", "[Fecha Emision]"
    ),
}


def _f(value) -> float:
    return float(value) if value is not None else 0.0


def _info(medio: str) -> _MedioInfo:
    if medio not in _MEDIOS:
        raise ValueError(
            f"El medio '{medio}' no se concilia desde este módulo "
            "(Tarjetas se concilia desde su propia pantalla, 008/009)."
        )
    return _MEDIOS[medio]


def _movimiento_original(medio: str, id_movimiento: int) -> dict:
    info = _info(medio)
    columnas = f"{info.importe_expr} AS importe, {info.fecha_col} AS fecha"
    if info.contacto_col:
        columnas += f", {info.contacto_col} AS idContacto"
    fila = fetch_one(
        f"SELECT {columnas} FROM {info.tabla} WHERE {info.id_col} = ?", (id_movimiento,)
    )
    if fila is None:
        raise ValueError(f"No existe ningún movimiento '{medio}' con id {id_movimiento}.")
    return fila


def _contacto_reconocido_por_origen_automatico(
    medio: str, id_movimiento: int, movimiento: dict
) -> int | None:
    """IdContacto si el movimiento ya tiene uno reconocido por su origen
    automático habitual (no por este módulo), o None — FR-008. El override
    de 022 (a qué contacto queda atribuido) no cambia esta respuesta: un
    movimiento sigue "ya reconocido" tenga o no un override vigente, lo
    único que importa acá es si tiene un origen automático en absoluto."""
    info = _info(medio)
    if info.contacto_col:
        # `IdContacto=0` es el centinela heredado de "sin asignar" (no un
        # contacto real) en bna/galicia/mercado-libre/efectivo — bug real
        # encontrado 2026-09-29 corriendo la conciliación masiva: `0 is not
        # None` es `True` en Python, así que sin este chequeo CUALQUIER
        # movimiento con ese centinela (incluidos ~350 candidatos reales sin
        # LEY 25413) quedaba "ya_reconocido" con `idContactoReconocido=0` y
        # `contactoReconocido=None`, bloqueado para siempre sin ningún error
        # visible que lo explicara.
        return movimiento.get("idContacto") or None
    if medio == "valores-recibidos":
        # La tabla no tiene columna de contacto propia; se resuelve hoy vía
        # dos ramas existentes de la vista (endoso a tercero). Se consulta
        # la vista en vez de reimplementar ese join acá (fuente única de
        # verdad de "qué ya está reconocido").
        fila = fetch_one(
            "SELECT IdContacto FROM dbo.vw_MovimientosCuenta_Base "
            "WHERE Origen IN ('Pagos Valores Recibidos', 'Cobros Valores Recibidos') AND IdOrigen = ?",
            (id_movimiento,),
        )
        return fila["IdContacto"] if fila else None
    return None  # valores-propios: la tabla no tiene ninguna columna de contacto


def listar_conciliaciones(medio: str, id_movimiento: int) -> list[dict]:
    return fetch_all(
        """
        SELECT ct.IdConciliacion AS idConciliacion, ct.IdContacto AS idContacto,
               co.[Razon Social] AS contacto, ct.Importe AS importe, ct.Usuario AS usuario, ct.Fecha AS fecha,
               ct.TipoOrigenDocumento AS tipoOrigenDocumento, ct.IdOrigenDocumento AS idOrigenDocumento
        FROM dbo.ConciliacionesTesoreria ct
        JOIN dbo.Contactos co ON co.IdContacto = ct.IdContacto
        WHERE ct.Medio = ? AND ct.IdMovimiento = ?
        ORDER BY ct.IdConciliacion ASC
        """,
        (medio, id_movimiento),
    )


def calcular_estado(medio: str, id_movimiento: int) -> dict:
    movimiento = _movimiento_original(medio, id_movimiento)
    importe_total = abs(round(_f(movimiento["importe"]), 2))

    conciliaciones = listar_conciliaciones(medio, id_movimiento)
    suma_conciliada = round(sum(_f(c["importe"]) for c in conciliaciones), 2)
    saldo_pendiente = round(importe_total - suma_conciliada, 2)

    id_contacto_reconocido = _contacto_reconocido_por_origen_automatico(
        medio, id_movimiento, movimiento
    )
    contacto_reconocido = None
    if id_contacto_reconocido is not None:
        estado = "ya_reconocido"
        fila = fetch_one(
            "SELECT [Razon Social] AS n FROM dbo.Contactos WHERE IdContacto = ?",
            (id_contacto_reconocido,),
        )
        contacto_reconocido = fila["n"] if fila else None
    elif suma_conciliada <= 0:
        estado = "sin_conciliar"
    elif saldo_pendiente <= TOLERANCIA_REDONDEO:
        estado = "conciliado"
    else:
        estado = "parcialmente_conciliado"

    auditoria = _estado_vigente(medio, id_movimiento)
    if estado != "ya_reconocido" and auditoria:
        estado = "sin_documento" if auditoria["estado"] == "SinDocumento" else "conciliado"
        saldo_pendiente = 0.0
    return {
        "estado": estado,
        "importeTotal": importe_total,
        "saldoPendiente": max(saldo_pendiente, 0.0),
        "conciliaciones": conciliaciones,
        "idContactoReconocido": id_contacto_reconocido,
        "contactoReconocido": contacto_reconocido,
        "auditoria": auditoria,
    }


def _tiene_traspaso_interno_activo(medio: str, id_movimiento: int) -> bool:
    """Mismo `SELECT` inlineado de data-model.md de 024 ("Vínculo activo de
    un movimiento"), sin importar `traspasos_internos_tesoreria.repository`
    ni `tesoreria.estado_resolucion` — evita un ciclo de 3 módulos
    (`conciliacion_tesoreria` es la pieza que las otras dos consultan, nunca
    al revés; mismo criterio que I1/T007 de `/speckit-analyze`, 024)."""
    fila = fetch_one(
        "SELECT TOP 1 Accion FROM dbo.TraspasosInternosTesoreria "
        "WHERE (MedioA = ? AND IdMovimientoA = ?) OR (MedioB = ? AND IdMovimientoB = ?) "
        "ORDER BY IdEvento DESC",
        (medio, id_movimiento, medio, id_movimiento),
    )
    return fila is not None and fila.get("Accion") == "Vincular"


@atomic_reconciliation
def aplicar_conciliacion(
    medio: str, id_movimiento: int, id_contacto: int, importe: float, usuario: str
) -> dict:
    if importe is None or importe <= 0:
        raise ValueError("El importe a conciliar debe ser mayor a cero.")

    contacto_existe = fetch_one(
        "SELECT 1 AS x FROM dbo.Contactos WHERE IdContacto = ?", (id_contacto,)
    )
    if contacto_existe is None:
        raise ValueError(f"El contacto {id_contacto} no existe.")

    # Recalculado en el momento de escribir, no con el saldo que el cliente
    # vio al abrir la pantalla (FR-010: dos usuarios conciliando el mismo
    # movimiento a la vez). También valida que `medio` esté soportado, antes
    # de consultar `TraspasosInternosTesoreria` (que no tiene su propia
    # validación de medio — 024 usa el mismo dominio de 6 medios).
    estado = calcular_estado(medio, id_movimiento)

    if _tiene_traspaso_interno_activo(medio, id_movimiento):
        raise ValueError(
            f"El movimiento '{medio}' {id_movimiento} ya está vinculado como traspaso interno — "
            "deshacé ese vínculo antes de conciliarlo con un contacto."
        )

    if estado["estado"] == "ya_reconocido":
        raise ValueError(
            f"El movimiento '{medio}' {id_movimiento} ya tiene un contacto reconocido por su origen habitual — "
            "para corregirlo, usar la reasignación de contacto desde su cuenta corriente."
        )
    saldo_pendiente = estado["saldoPendiente"]
    if estado["estado"] in ("sin_documento", "conciliado"):
        raise ValueError("El movimiento ya está resuelto; no admite nuevas imputaciones.")
    if importe > saldo_pendiente + TOLERANCIA_REDONDEO:
        raise ValueError(
            f"El importe ({importe}) excede el saldo pendiente de conciliar de este movimiento "
            f"({saldo_pendiente})."
        )

    resultados = execute_write_transaction(
        [
            (
                "INSERT INTO dbo.ConciliacionesTesoreria (Medio, IdMovimiento, IdContacto, Importe, Usuario) "
                "OUTPUT INSERTED.IdConciliacion VALUES (?, ?, ?, ?, ?)",
                (medio, id_movimiento, id_contacto, importe, usuario),
            ),
        ]
    )
    id_conciliacion = resultados[0]
    fila = fetch_one(
        """
        SELECT ct.IdConciliacion AS idConciliacion, ct.IdContacto AS idContacto,
               co.[Razon Social] AS contacto, ct.Importe AS importe, ct.Usuario AS usuario, ct.Fecha AS fecha
        FROM dbo.ConciliacionesTesoreria ct
        JOIN dbo.Contactos co ON co.IdContacto = ct.IdContacto
        WHERE ct.IdConciliacion = ?
        """,
        (id_conciliacion,),
    )
    assert fila is not None
    return fila


def _estado_vigente(medio: str, id_movimiento: int) -> dict | None:
    row = fetch_one(
        "SELECT TOP 1 IdEstado AS idEstado, Estado AS estado, Motivo AS motivo, "
        "Detalle AS detalle, ImporteDiferencia AS importeDiferencia, Usuario AS usuario, Fecha AS fecha "
        "FROM dbo.ConciliacionesTesoreriaEstado WHERE Medio=? AND IdMovimiento=? ORDER BY IdEstado DESC",
        (medio, id_movimiento),
    )
    return row if row and row.get("estado") in ("SinDocumento", "DiferenciaAceptada") else None


def _pendiente(medio: str, id_movimiento: int) -> dict:
    estado = calcular_estado(medio, id_movimiento)
    if _tiene_traspaso_interno_activo(medio, id_movimiento):
        raise ValueError("El movimiento ya está vinculado como traspaso interno.")
    if estado["estado"] not in ("sin_conciliar", "parcialmente_conciliado"):
        raise ValueError("El movimiento ya está resuelto por otra vía.")
    if estado["saldoPendiente"] <= 0:
        raise ValueError("El movimiento no tiene saldo pendiente.")
    return estado


def buscar_documentos(texto: str) -> list[dict]:
    return documentos.buscar(texto)


def candidatos(medio: str, id_movimiento: int) -> dict:
    estado = _pendiente(medio, id_movimiento)
    movimiento = _movimiento_original(medio, id_movimiento)
    docs = documentos.buscar("", importe=estado["saldoPendiente"], fecha=movimiento["fecha"])
    return dict(
        documentos=docs, sugerencias=documentos_adapter.sugerencias(estado["saldoPendiente"], docs)
    )


def _calcular(medio: str, id_movimiento: int, refs: list[dict]) -> tuple[dict, list[dict]]:
    estado = _pendiente(medio, id_movimiento)
    docs = documentos.por_referencias(refs)
    for d in docs:
        if d["idContacto"] is None or d["importePesos"] is None:
            raise ValueError("El documento necesita contraparte y tipo de cambio válido.")
        if abs(d["saldoPendiente"]) < 0.005:
            raise ValueError("Un documento elegido ya no tiene saldo pendiente.")
        if d["saldoPendiente"] < 0 and d["origen"] != "Compras":
            raise ValueError("Solo Compras admite documentos negativos.")
    result = documentos_adapter.calcular(estado["saldoPendiente"], docs)
    for d, item in zip(docs, result["imputados"], strict=True):
        if item["importeImputado"] != 0:
            documentos.validar_imputacion(d["saldoPendiente"], item["importeImputado"])
    return result, docs


def calcular_conciliacion(medio: str, id_movimiento: int, refs: list[dict]) -> dict:
    return _calcular(medio, id_movimiento, refs)[0]


def _stmt_estado(
    medio: str,
    id_movimiento: int,
    estado: str,
    motivo: str,
    detalle: str | None,
    diferencia: float | None,
    usuario: str,
) -> tuple:
    motivos = {
        "SinDocumento": ("Impuesto", "Interes", "CompraNoCargada", "Otro"),
        "DiferenciaAceptada": ("AjusteTipoCambioSinNota", "Redondeo", "Impuesto", "Otro"),
        "EstadoQuitado": ("Revocacion",),
    }
    detalle = detalle.strip() if detalle else None
    if motivo not in motivos[estado] or (motivo == "Otro" and not detalle):
        raise ValueError("Motivo inválido; Otro requiere detalle.")
    if len(detalle or "") > 255 or not usuario or len(usuario) > 100:
        raise ValueError("Detalle o usuario excede la longitud permitida.")
    return (
        "INSERT INTO dbo.ConciliacionesTesoreriaEstado "
        "(Medio,IdMovimiento,Estado,Motivo,Detalle,ImporteDiferencia,Usuario) "
        "VALUES (?,?,?,?,?,?,?)",
        (medio, id_movimiento, estado, motivo, detalle, diferencia, usuario),
    )


@atomic_reconciliation
def vincular_lote(
    medio: str, id_movimiento: int, refs: list[dict], aceptar_diferencia: dict | None, usuario: str
) -> list[dict]:
    result, docs = _calcular(medio, id_movimiento, refs)
    statements = []
    for d, item in zip(docs, result["imputados"], strict=True):
        if item["importeImputado"] == 0:
            continue
        statements.append(
            (
                "INSERT INTO dbo.ConciliacionesTesoreria "
                "(Medio,IdMovimiento,IdContacto,Importe,Usuario,TipoOrigenDocumento,IdOrigenDocumento) "
                "OUTPUT INSERTED.IdConciliacion VALUES (?,?,?,?,?,?,?)",
                (
                    medio,
                    id_movimiento,
                    d["idContacto"],
                    item["importeImputado"],
                    usuario,
                    d["origen"],
                    d["idOrigen"],
                ),
            )
        )
    count = len(statements)
    if aceptar_diferencia:
        statements.append(
            _stmt_estado(
                medio,
                id_movimiento,
                "DiferenciaAceptada",
                aceptar_diferencia["motivo"],
                aceptar_diferencia.get("detalle"),
                result["diferencia"],
                usuario,
            )
        )
    ids = execute_write_transaction(statements)[:count]
    return [c for c in listar_conciliaciones(medio, id_movimiento) if c["idConciliacion"] in ids]


@atomic_reconciliation
def marcar_sin_documento(
    medio: str, id_movimiento: int, motivo: str, detalle: str | None, usuario: str
) -> None:
    estado = _pendiente(medio, id_movimiento)
    if estado["conciliaciones"]:
        raise ValueError(
            "El movimiento tiene imputaciones; usá diferencia aceptada para el residual."
        )
    execute_write_transaction(
        [_stmt_estado(medio, id_movimiento, "SinDocumento", motivo, detalle, None, usuario)]
    )


@atomic_reconciliation
def quitar_vinculo(medio: str, id_movimiento: int, id_conciliacion: int) -> None:
    """Corrige una conciliación mal cargada (mismo criterio que
    `tarjetas_resumenes.repository.quitar_vinculo_compra`: un `DELETE`
    real, no un evento — el saldo/estado del movimiento se recalcula
    siempre a partir de las filas que queden, así que borrar una fila
    equivocada es seguro y no requiere un mecanismo de reversión aparte).
    Disponible para cualquier línea de cualquier medio (bna, galicia,
    mercado-libre, efectivo, valores-propios, valores-recibidos), tanto
    para conciliaciones manuales como con documento."""
    _movimiento_original(medio, id_movimiento)
    fila = fetch_one(
        "SELECT IdConciliacion FROM dbo.ConciliacionesTesoreria "
        "WHERE IdConciliacion = ? AND Medio = ? AND IdMovimiento = ?",
        (id_conciliacion, medio, id_movimiento),
    )
    if fila is None:
        raise ValueError(f"No existe la conciliación {id_conciliacion} para este movimiento.")
    execute_write("DELETE FROM dbo.ConciliacionesTesoreria WHERE IdConciliacion = ?", (id_conciliacion,))


@atomic_reconciliation
def quitar_estado(medio: str, id_movimiento: int, usuario: str) -> None:
    _movimiento_original(medio, id_movimiento)
    if _estado_vigente(medio, id_movimiento):
        execute_write_transaction(
            [_stmt_estado(medio, id_movimiento, "EstadoQuitado", "Revocacion", None, None, usuario)]
        )
