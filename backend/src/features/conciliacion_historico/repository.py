"""Conciliación histórica de cuentas corrientes (020): aplica
retroactivamente movimientos de tesorería sin aplicar contra sus
documentos, reutilizando la sugerencia FIFO de 019 sin reimplementarla
(research.md §3/§4).

`clasificar_movimiento` decide entre tres resultados posibles:
- `automatica-exacta`: la combinación FIFO cierra dentro de
  `TOLERANCIA_REDONDEO_APLICACION` (misma tolerancia que usa 019 para el
  estado de un documento).
- `automatica-mejor-esfuerzo`: no cierra exacto, pero la diferencia es
  menor o igual al 2% del importe del movimiento (tolerancia calibrada
  con datos reales en conciliación de documentos USD, ver memoria
  `project_conciliacion_documentos_usd` y research.md §4).
- `excepcion`: sin contacto identificable, o sin documentos candidatos
  suficientes para cerrar dentro del 2%.
"""

from __future__ import annotations

from datetime import date

from src.db.connection import execute_insert_returning_id, execute_write, execute_write_transaction, fetch_all
from src.features.aplicaciones_pago import sugerencia
from src.features.aplicaciones_pago.documentos import TOLERANCIA_REDONDEO_APLICACION
from src.features.aplicaciones_pago.repository import aplicaciones_vigentes_de_movimiento
from src.features.tesoreria.repository import MEDIOS_CONFIG, get_movimientos

MEDIOS_CONCILIABLES = ("bna", "galicia", "efectivo", "valores-recibidos", "tarjetas")
TOLERANCIA_RELATIVA_MEJOR_ESFUERZO = 0.02
TOLERANCIA_RELATIVA_SALDO = 0.005
TOLERANCIA_ABSOLUTA_MINIMA_SALDO = 1.0
USUARIO_PROCESO = "sistema-conciliacion-020"

# Subcategorías de "excepcion" (research.md §6, analizado contra datos reales
# el 2026-09-25): distinguen qué excepciones son estructuralmente no
# accionables de las que sí ameritan revisión manual.
SIN_CONTACTO = "sin-contacto"
SIN_DOCUMENTO_COMERCIAL = "sin-documento-comercial"
CON_DOCUMENTO_SIN_PENDIENTE = "con-documento-sin-pendiente"


def _movimientos_del_medio(medio: str, fecha_desde: date, fecha_hasta: date) -> list[dict]:
    config = MEDIOS_CONFIG[medio]
    _rows, total = get_movimientos(medio, fecha_desde, fecha_hasta, 1, 1)
    if total == 0:
        return []
    rows, _total = get_movimientos(medio, fecha_desde, fecha_hasta, 1, total)
    return [{"idMovimientoOrigen": row[config.id_field]} for row in rows]


def movimientos_sin_aplicar(fecha_desde: date, fecha_hasta: date) -> list[dict]:
    """Movimientos de tesorería en el rango sin ninguna aplicación vigente
    (manual o automática) — insumo del proceso de conciliación histórica."""
    resultado = []
    for medio in MEDIOS_CONCILIABLES:
        for movimiento in _movimientos_del_medio(medio, fecha_desde, fecha_hasta):
            id_mov = movimiento["idMovimientoOrigen"]
            if aplicaciones_vigentes_de_movimiento(medio, id_mov):
                continue
            resultado.append({"origenMovimiento": medio, "idMovimientoOrigen": id_mov})
    return resultado


def clasificar_movimiento(origen_movimiento: str, id_movimiento_origen: int) -> dict:
    """Clasifica un movimiento sin aplicar reutilizando `sugerencia.sugerir`
    (019) — no reimplementa el matching FIFO, solo interpreta su resultado."""
    id_contacto, importe = sugerencia._contacto_e_importe(origen_movimiento, id_movimiento_origen)
    if id_contacto is None or importe is None:
        return {"clasificacion": "excepcion", "motivo": "sin contacto identificable", "idContacto": None}

    resultado = sugerencia.sugerir(origen_movimiento, id_movimiento_origen)
    if not resultado["sugerencias"]:
        return {"clasificacion": "excepcion", "motivo": "sin documentos candidatos", "idContacto": id_contacto}

    importe_abs = resultado["importeMovimiento"]
    saldo_sin_asignar = resultado["saldoSinAsignar"]

    if saldo_sin_asignar <= TOLERANCIA_REDONDEO_APLICACION:
        return {
            "clasificacion": "automatica-exacta",
            "sugerencias": resultado["sugerencias"],
            "notaConciliacion": None,
            "idContacto": id_contacto,
        }

    if importe_abs > 0 and saldo_sin_asignar <= importe_abs * TOLERANCIA_RELATIVA_MEJOR_ESFUERZO:
        detalle = ", ".join(f"{s['tipoDocumento']} #{s['idDocumento']}" for s in resultado["sugerencias"])
        porcentaje = round((saldo_sin_asignar / importe_abs) * 100, 2)
        nota = (
            f"Diferencia de ${saldo_sin_asignar:.2f} ({porcentaje}%) contra combinación FIFO "
            f"de {len(resultado['sugerencias'])} documento(s): {detalle}"
        )
        return {
            "clasificacion": "automatica-mejor-esfuerzo",
            "sugerencias": resultado["sugerencias"],
            "notaConciliacion": nota,
            "idContacto": id_contacto,
        }

    return {"clasificacion": "excepcion", "motivo": "sin documentos candidatos", "idContacto": id_contacto}


def _contacto_tuvo_documento_comercial_alguna_vez(id_contacto: int) -> bool:
    """True si el contacto tiene al menos una Compra o Venta cargada en el
    sistema, sin importar si está pendiente o no — distingue un contacto
    estructuralmente fuera de alcance (nunca fue proveedor/cliente) de uno
    donde el pago simplemente ya no tiene saldo pendiente que cubrir."""
    fila = fetch_all(
        "SELECT "
        "(SELECT COUNT(*) FROM dbo.Compras WHERE IdContacto = ?) + "
        "(SELECT COUNT(*) FROM dbo.[Venta Hacienda] WHERE IdConsignatario = ?) + "
        "(SELECT COUNT(*) FROM dbo.[Venta Granos] WHERE IdConsignatario = ?) AS total",
        (id_contacto, id_contacto, id_contacto),
    )
    return bool(fila and fila[0]["total"] > 0)


def subcategorizar_excepcion(id_contacto: int | None) -> str:
    """Ver research.md §6: análisis contra datos reales (8.976 excepciones,
    2026-09-25) mostró que agrupar todo bajo "sin documentos candidatos" es
    correcto pero inútil para decidir qué revisar — separa en 3 grupos con
    accionabilidad muy distinta."""
    if id_contacto is None:
        return SIN_CONTACTO
    if not _contacto_tuvo_documento_comercial_alguna_vez(id_contacto):
        return SIN_DOCUMENTO_COMERCIAL
    return CON_DOCUMENTO_SIN_PENDIENTE


TAMANO_LOTE_LOG = 500


def registrar_en_log(filas: list[dict]) -> None:
    """Persiste el resultado de una corrida del script (dry-run o --apply)
    en `ConciliacionHistoricoLog`, en lotes dentro de una única conexión por
    lote (`execute_write_transaction`) — insertar fila por fila con
    `execute_write` abriría una conexión nueva por cada una de las ~12.700
    filas, más lento que el propio reprocesamiento que este log busca evitar.

    **Nunca vacía la tabla entera primero** (bug real encontrado 2026-09-25):
    una corrida normal solo reprocesa `movimientos_sin_aplicar` — los
    movimientos ya aplicados en una corrida anterior no vuelven a aparecer.
    Vaciar todo el log antes de reescribir solo lo procesado en esta corrida
    borraba el registro de lo ya aplicado. En cambio, borra únicamente las
    claves (`OrigenMovimiento`, `IdMovimientoOrigen`) que va a reinsertar
    —necesario porque una excepción sí puede reprocesarse en corridas
    sucesivas y violaría la PK— dejando intacto todo lo demás."""
    for inicio in range(0, len(filas), TAMANO_LOTE_LOG):
        lote = filas[inicio : inicio + TAMANO_LOTE_LOG]
        valores_join = ", ".join("(?, ?)" for _ in lote)
        params_delete: list = []
        for fila in lote:
            params_delete.extend((fila["origenMovimiento"], fila["idMovimientoOrigen"]))
        execute_write(
            f"DELETE l FROM dbo.ConciliacionHistoricoLog l "
            f"JOIN (VALUES {valores_join}) AS v(OrigenMovimiento, IdMovimientoOrigen) "
            f"ON l.OrigenMovimiento = v.OrigenMovimiento AND l.IdMovimientoOrigen = v.IdMovimientoOrigen",
            tuple(params_delete),
        )
        statements = [
            (
                "INSERT INTO dbo.ConciliacionHistoricoLog "
                "(OrigenMovimiento, IdMovimientoOrigen, IdContacto, Clasificacion, Subcategoria, Detalle) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    fila["origenMovimiento"],
                    fila["idMovimientoOrigen"],
                    fila.get("idContacto"),
                    fila["clasificacion"],
                    fila.get("subcategoria"),
                    fila.get("detalle") or None,
                ),
            )
            for fila in lote
        ]
        execute_write_transaction(statements)


def resumen_por_contacto(solo_con_dudas: bool = False) -> list[dict]:
    """Conteo por contacto desde `ConciliacionHistoricoLog` (US2) — lectura
    instantánea, no reprocesa el histórico."""
    filas = fetch_all(
        "SELECT l.IdContacto AS idContacto, c.[Razon Social] AS razonSocial, "
        "SUM(CASE WHEN l.Clasificacion = 'automatica-exacta' THEN 1 ELSE 0 END) AS aplicadosExactos, "
        "SUM(CASE WHEN l.Clasificacion = 'automatica-mejor-esfuerzo' THEN 1 ELSE 0 END) AS aplicadosMejorEsfuerzo, "
        "SUM(CASE WHEN l.Subcategoria = 'con-documento-sin-pendiente' THEN 1 ELSE 0 END) AS revisionManual, "
        "SUM(CASE WHEN l.Subcategoria IN ('sin-contacto', 'sin-documento-comercial') THEN 1 ELSE 0 END) AS fueraDeAlcance "
        "FROM dbo.ConciliacionHistoricoLog l "
        "LEFT JOIN dbo.Contactos c ON c.IdContacto = l.IdContacto "
        "WHERE l.IdContacto IS NOT NULL "
        "GROUP BY l.IdContacto, c.[Razon Social]"
    )
    if solo_con_dudas:
        filas = [f for f in filas if f["aplicadosMejorEsfuerzo"] > 0 or f["revisionManual"] > 0]
    return filas


def detalle_contacto(id_contacto: int) -> dict:
    """Detalle de un contacto (US2): sus aplicaciones automáticas vigentes
    (con `Origen`/`NotaConciliacion`) y sus excepciones con motivo/subcategoría."""
    aplicaciones = fetch_all(
        "SELECT a.IdAplicacion AS idAplicacion, a.Origen AS origen, a.OrigenMovimiento AS origenMovimiento, "
        "a.IdMovimientoOrigen AS idMovimientoOrigen, a.TipoDocumento AS tipoDocumento, "
        "a.IdDocumentoAplicado AS idDocumentoAplicado, a.ImporteAplicado AS importeAplicado, "
        "a.NotaConciliacion AS notaConciliacion "
        "FROM dbo.AplicacionesPago a "
        "JOIN dbo.ConciliacionHistoricoLog l "
        "ON l.OrigenMovimiento = a.OrigenMovimiento AND l.IdMovimientoOrigen = a.IdMovimientoOrigen "
        "WHERE a.Origen IN ('automatica-exacta', 'automatica-mejor-esfuerzo') AND a.Anulada = 0 AND l.IdContacto = ?",
        (id_contacto,),
    )
    excepciones = fetch_all(
        "SELECT OrigenMovimiento AS origenMovimiento, IdMovimientoOrigen AS idMovimientoOrigen, "
        "Subcategoria AS subcategoria, Detalle AS motivo "
        "FROM dbo.ConciliacionHistoricoLog WHERE IdContacto = ? AND Clasificacion = 'excepcion'",
        (id_contacto,),
    )
    return {"idContacto": id_contacto, "aplicaciones": aplicaciones, "excepciones": excepciones}


def aplicar_clasificacion(origen_movimiento: str, id_movimiento_origen: int, clasificacion: dict) -> list[int]:
    """Inserta una fila en `AplicacionesPago` por cada documento de la
    combinación FIFO ya calculada por `clasificar_movimiento`."""
    ids_generados = []
    for sug in clasificacion["sugerencias"]:
        id_aplicacion = execute_insert_returning_id(
            "INSERT INTO dbo.AplicacionesPago "
            "(OrigenMovimiento, IdMovimientoOrigen, TipoDocumento, IdDocumentoAplicado, ImporteAplicado, "
            "Usuario, Origen, NotaConciliacion) "
            "OUTPUT INSERTED.IdAplicacion "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                origen_movimiento,
                id_movimiento_origen,
                sug["tipoDocumento"],
                sug["idDocumento"],
                sug["importeSugerido"],
                USUARIO_PROCESO,
                clasificacion["clasificacion"],
                clasificacion.get("notaConciliacion"),
            ),
        )
        ids_generados.append(id_aplicacion)
    return ids_generados


def comparar_saldos(estado: str | None = None) -> list[dict]:
    """Compara, por contacto con referencia cargada, el saldo actual de `WC`
    contra el saldo real leído de `LaHerencia` (US3 — research.md §2,
    actualizado 2026-09-25: el "sistema Access" es, en los hechos, un
    front-end sobre `LaHerencia`; `SaldosReferenciaAccess` se puebla desde
    ahí vía `scripts/comparar_saldo_laherencia.py`, no desde un archivo
    manual). El saldo actual de `WC` se reutiliza tal cual de `cuentas_corrientes`
    (004) — esta función no reimplementa ni ajusta ese cálculo."""
    from src.features.cuentas_corrientes.repository import get_saldos_todos

    referencias = fetch_all(
        "SELECT r.IdContacto AS idContacto, r.SaldoAccess AS saldoReferencia, r.FechaCorte AS fechaCorte "
        "FROM dbo.SaldosReferenciaAccess r"
    )
    saldos_wc = {f["idContacto"]: float(f["saldoParcial"] or 0) for f in get_saldos_todos()}
    razones_sociales = {
        f["idContacto"]: f["razonSocial"] for f in fetch_all("SELECT IdContacto AS idContacto, [Razon Social] AS razonSocial FROM dbo.Contactos")
    }

    resultado = []
    for ref in referencias:
        id_contacto = ref["idContacto"]
        saldo_referencia = float(ref["saldoReferencia"])
        saldo_actual = saldos_wc.get(id_contacto, 0.0)
        diferencia = round(saldo_actual - saldo_referencia, 2)
        tolerancia = max(TOLERANCIA_ABSOLUTA_MINIMA_SALDO, abs(saldo_referencia) * TOLERANCIA_RELATIVA_SALDO)
        item_estado = "conciliado" if abs(diferencia) <= tolerancia else "con-diferencia"
        if estado and item_estado != estado:
            continue
        resultado.append(
            {
                "idContacto": id_contacto,
                "razonSocial": razones_sociales.get(id_contacto),
                "saldoActual": saldo_actual,
                "saldoReferencia": saldo_referencia,
                "fechaCorteReferencia": ref["fechaCorte"],
                "diferencia": diferencia,
                "estado": item_estado,
            }
        )
    return resultado
