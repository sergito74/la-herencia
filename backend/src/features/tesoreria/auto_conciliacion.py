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


def conciliar_en_segundo_plano() -> None:
    def correr():
        try:
            conciliar_ley_25413()
        except Exception:  # nunca frena la carga del extracto
            _log.exception("Conciliación automática Ley 25.413")
    threading.Thread(target=correr, daemon=True).start()


def arrancar() -> None:
    """Una pasada al abrir el sistema y después una por día."""
    def bucle():
        while True:
            try:
                conciliar_ley_25413()
            except Exception:
                _log.exception("Conciliación automática Ley 25.413")
            time.sleep(24 * 3600)
    threading.Thread(target=bucle, daemon=True).start()
