"""Conciliación automática de movimientos bancarios sin comprobante (19/11/2026, pedido de Sergio).

"Los movimientos que contienen en la descripción 'LEY 25413' deben conciliarse automáticamente y sumarse al rubro
Impuesto al débito/crédito." El rubro ya lo asigna el flujo de caja (`atribucion.es_ley_25413`); acá se los marca
conciliados sin documento, motivo Impuesto. Corre solo después de cada carga de extracto y una vez por día
(principio de sistema autónomo): nunca a mano.
"""
from __future__ import annotations

import logging
import threading
import time

from src.db.connection import execute_write_transaction, fetch_all

_log = logging.getLogger(__name__)
USUARIO = "sistema (Ley 25.413)"
DETALLE = "Impuesto al débito/crédito (Ley 25.413), conciliado automáticamente"

# Movimientos con la leyenda, sin conciliación, sin estado vigente y sin traspaso: los que hoy figuran "Sin conciliar".
_PENDIENTES = """
SELECT m.{id} AS id FROM dbo.[{tabla}] m
WHERE m.{texto} LIKE '%25413%'
  AND NOT EXISTS (SELECT 1 FROM dbo.ConciliacionesTesoreria c WHERE c.Medio = ? AND c.IdMovimiento = m.{id})
  AND NOT EXISTS (SELECT 1 FROM dbo.ConciliacionesTesoreriaEstado e WHERE e.Medio = ? AND e.IdMovimiento = m.{id})
  AND NOT EXISTS (SELECT 1 FROM dbo.TraspasosInternosTesoreria t WHERE (t.MedioA = ? AND t.IdMovimientoA = m.{id})
                                                                     OR (t.MedioB = ? AND t.IdMovimientoB = m.{id}))
"""
_MEDIOS = {"bna": ("Movimientos BNA", "IdMovimientoBNA", "Concepto"),
           "galicia": ("Movimientos Galicia", "IdMovimiento", "[Descripción]")}


def conciliar_ley_25413() -> int:
    from src.features.conciliacion_tesoreria.repository import _stmt_estado
    from src.features.tesoreria.estado_resolucion import esta_resuelto

    total = 0
    for medio, (tabla, col_id, texto) in _MEDIOS.items():
        ids = [r["id"] for r in fetch_all(_PENDIENTES.format(tabla=tabla, id=col_id, texto=texto), (medio,) * 4)]
        ids = [i for i in ids if esta_resuelto(medio, i) == "sin_conciliar"]  # misma regla que la pantalla
        for k in range(0, len(ids), 500):
            execute_write_transaction([_stmt_estado(medio, i, "SinDocumento", "Impuesto", DETALLE, None, USUARIO)
                                       for i in ids[k:k + 500]])
        total += len(ids)
    if total:
        _log.info("Ley 25.413: %s movimientos conciliados automáticamente", total)
    return total


# 19/11/2026 (auditoría de Tesorería, mejora 4): lo que se repite cada mes (comisión del paquete, IVA base, retención
# RG 2408…) se asigna solo al contacto de siempre. Regla: el mismo concepto exacto tuvo, en el último año, al menos 3
# movimientos asignados y TODOS al mismo contacto. Si hubo dos contactos distintos, no se toca (queda para Sergio).
_CONCEPTO = {"bna": ("Movimientos BNA", "IdMovimientoBNA", "Concepto", "[Fecha / Hora Mov#]"),
             "galicia": ("Movimientos Galicia", "IdMovimiento", "[Descripción]", "Fecha")}


# Nunca por esta regla: inversiones (son pases internos, no gastos), canales por los que pagan varios clientes y pagos de
# tarjeta (se vinculan al resumen en el módulo de Tarjetas, que es el que pone el contacto).
import re as _re
_EXCLUIDO = _re.compile(r"fima|plazo fijo|p\.fijo|cash proveedores|dep\.?efectivo|transf|bca\.e\.tr|cheq|echeq|visa|master|tarjeta|amex|cabal", _re.I)


def asignar_contacto_recurrente() -> int:
    from src.features.tesoreria.repository import ids_pendientes

    total = 0
    for medio, (tabla, col_id, texto, fecha) in _CONCEPTO.items():
        historia = fetch_all(f"""
            SELECT {texto} AS concepto, MIN(IdContacto) AS contacto, COUNT(DISTINCT IdContacto) AS distintos, COUNT(*) AS n
            FROM dbo.[{tabla}] WHERE ISNULL(IdContacto, 0) <> 0 AND {fecha} >= DATEADD(year, -1, GETDATE())
            GROUP BY {texto}""")
        regla = {h["concepto"]: h["contacto"] for h in historia
                 if h["distintos"] == 1 and h["n"] >= 3 and not _EXCLUIDO.search(h["concepto"] or "")}
        pendientes = set(ids_pendientes(medio, None, None))
        if not pendientes or not regla:
            continue
        filas = fetch_all(f"SELECT {col_id} AS id, {texto} AS concepto FROM dbo.[{tabla}] WHERE ISNULL(IdContacto, 0) = 0 "
                          f"AND {fecha} >= DATEADD(year, -1, GETDATE())")
        cambios = [(regla[f["concepto"]], f["id"]) for f in filas if f["id"] in pendientes and f["concepto"] in regla]
        for k in range(0, len(cambios), 500):
            execute_write_transaction([(f"UPDATE dbo.[{tabla}] SET IdContacto = ? WHERE {col_id} = ? AND ISNULL(IdContacto, 0) = 0", c)
                                       for c in cambios[k:k + 500]])
        total += len(cambios)
    if total:
        _log.info("Contacto recurrente asignado a %s movimientos", total)
    return total


# 19/11/2026 (modelo C de Inversiones, aprobado por Sergio): constituciones, cobros, suscripciones y rescates son pases
# entre el banco y la inversión; se concilian como "Inversión". El rendimiento lo calcula `tesoreria.inversiones`.
# Reemplaza los "sin documento / otro" que la conciliación masiva del 29/09 les había puesto a movimientos del Fima.
_INVERSIONES = {
    "bna": ("Movimientos BNA", "IdMovimientoBNA",
            "(Concepto LIKE '%P.FIJO%' OR Concepto = 'PLAZO FIJO' OR IdMovimientoBNA IN (12178, 12263))", "Plazo fijo Nación"),
    "galicia": ("Movimientos Galicia", "IdMovimiento", "([Descripción] LIKE '%Fima%' OR [Descripción] LIKE '%Plazo Fijo%')", None),
}


def conciliar_inversiones() -> int:
    from src.features.conciliacion_tesoreria.repository import _stmt_estado

    total = 0
    for medio, (tabla, col_id, cond, detalle_fijo) in _INVERSIONES.items():
        texto = "Concepto" if medio == "bna" else "[Descripción]"
        filas = fetch_all(f"""
            SELECT m.{col_id} AS id, m.{texto} AS concepto FROM dbo.[{tabla}] m
            WHERE {cond}
              AND NOT EXISTS (SELECT 1 FROM dbo.ConciliacionesTesoreria c WHERE c.Medio = ? AND c.IdMovimiento = m.{col_id})
              AND NOT EXISTS (SELECT 1 FROM dbo.ConciliacionesTesoreriaEstado e WHERE e.Medio = ? AND e.IdMovimiento = m.{col_id}
                    AND e.IdEstado = (SELECT MAX(e2.IdEstado) FROM dbo.ConciliacionesTesoreriaEstado e2 WHERE e2.Medio = e.Medio
                                      AND e2.IdMovimiento = e.IdMovimiento)
                    AND (e.Motivo = 'Inversion' OR e.Estado = 'EstadoQuitado'))""", (medio, medio))
        stmts = [_stmt_estado(medio, f["id"], "SinDocumento", "Inversion",
                              detalle_fijo or ("Fondo Fima" if "fima" in (f["concepto"] or "").lower() else "Plazo fijo Galicia"),
                              None, "sistema (inversiones)") for f in filas]
        for k in range(0, len(stmts), 500):
            execute_write_transaction(stmts[k:k + 500])
        total += len(stmts)
    if total:
        _log.info("Inversiones: %s movimientos conciliados como pase a la inversión", total)
    return total


# 19/11/2026 (Sergio, punto 4): una extracción de efectivo del banco que fondea una caja es un pase entre cuentas
# propias. Si en una caja hay un ingreso del mismo día y el mismo importe que dice "retiro"/"extracción", el movimiento
# del banco queda conciliado como "Pase a caja" (sin asientos manuales). Cada ingreso de caja se usa una sola vez.
_EXTRACCIONES = {"bna": ("Movimientos BNA", "IdMovimientoBNA", "[Fecha / Hora Mov#]", "-Importe", "(Concepto LIKE 'EXTR%' OR Concepto LIKE 'COBRADO POR CAJA%')"),
                 "galicia": ("Movimientos Galicia", "IdMovimiento", "Fecha", "ISNULL([Débitos],0)",
                             "([Descripción] LIKE 'Extraccion%' OR [Descripción] LIKE 'Extracción%')")}


def conciliar_extracciones_a_caja() -> int:
    from src.features.conciliacion_tesoreria.repository import _stmt_estado
    from src.features.tesoreria.repository import ids_pendientes

    usados = {r["d"] for r in fetch_all("SELECT Detalle AS d FROM dbo.ConciliacionesTesoreriaEstado WHERE Motivo = 'PaseCaja'")}
    total = 0
    for medio, (tabla, col, fecha, importe, cond) in _EXTRACCIONES.items():
        pendientes = set(ids_pendientes(medio, None, None))
        filas = fetch_all(f"SELECT {col} AS id, CAST({fecha} AS date) AS f, {importe} AS imp FROM dbo.[{tabla}] WHERE {cond}")
        stmts = []
        for m in filas:
            if m["id"] not in pendientes or not m["imp"]:
                continue
            caja = fetch_all("SELECT IdMovimiento AS id, Caja AS caja FROM dbo.MovimientosCajaEfectivo WHERE CAST(Fecha AS date) = ? "
                             "AND Importe = ? AND (Concepto LIKE '%Retiro%' OR Concepto LIKE '%Extrac%') ORDER BY IdMovimiento",
                             (m["f"], float(m["imp"])))
            libre = next((c for c in caja if f"Pase a caja {c['caja']} (movimiento de caja {c['id']})" not in usados), None)
            if libre:
                det = f"Pase a caja {libre['caja']} (movimiento de caja {libre['id']})"
                usados.add(det)
                stmts.append(_stmt_estado(medio, m["id"], "SinDocumento", "PaseCaja", det, None, "sistema (pase a caja)"))
        if stmts:
            execute_write_transaction(stmts)
        total += len(stmts)
    return total


def correr_reglas() -> None:
    try:
        from src.features.tesoreria import lector_fima

        lector_fima.actualizar()  # extracto mensual del Fondo Fima, desde Dropbox
    except Exception:
        _log.exception("Lectura del extracto del Fondo Fima")
    try:
        # 19/11/2026: los certificados de retención de Ganancias (SICORE) entran solos a la cuenta del proveedor; sin
        # esto la parte retenida de cada orden de pago seguía figurando impaga en Facturas a pagar.
        from scripts.cargar_retenciones_certificados import main as cargar_retenciones

        cargar_retenciones(aplicar=True)
    except Exception:
        _log.exception("Carga de certificados de retención")
    conciliar_ley_25413()
    conciliar_inversiones()
    conciliar_extracciones_a_caja()
    asignar_contacto_recurrente()


def conciliar_en_segundo_plano() -> None:
    def correr():
        try:
            correr_reglas()
        except Exception:  # nunca frena la carga del extracto
            _log.exception("Conciliación automática Ley 25.413")
    threading.Thread(target=correr, daemon=True).start()


def arrancar() -> None:
    """Una pasada al abrir el sistema y después una por día."""
    def bucle():
        while True:
            try:
                correr_reglas()
            except Exception:
                _log.exception("Conciliación automática Ley 25.413")
            time.sleep(24 * 3600)
    threading.Thread(target=bucle, daemon=True).start()
