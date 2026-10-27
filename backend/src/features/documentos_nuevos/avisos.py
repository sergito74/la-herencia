"""Alta de avisos en `DocumentosNuevos` para lo que baja la bóveda (043, T010).

Cada documento de portal genera su fila: lo cargado solo queda para revisar,
lo que no se pudo cargar queda "para cargar a mano" y lo que ya estaba en el
sistema se registra sin aviso. Si la bajada ocurre dentro de la rutina, la
fila queda asociada a esa corrida.
"""

from __future__ import annotations

import logging
import threading

from src.features.documentos_nuevos import repository

log = logging.getLogger(__name__)

# Corrida de la rutina en curso en este hilo (la rutina corre las cuentas en su propio hilo, de a una).
_local = threading.local()

# Tipo de documento de portal → (tipo de DocumentosNuevos, módulo del aviso).
DESTINO_PORTAL = {
    "factura": ("factura", "compras"), "nota_credito": ("nota_credito", "compras"),
    "nota_debito": ("nota_debito", "compras"), "liquidacion": ("liquidacion", "ventas"),
    "certificado": ("retencion", "impuestos"),
}

ESTADO_PORTAL = {"cargado_auto": "cargado_solo", "pendiente": "para_cargar", "ya_cargado": "ya_estaba",
                 "no_aplica": "para_cargar"}


def fijar_corrida(id_corrida: int | None) -> None:
    _local.id_corrida = id_corrida


def corrida_actual() -> int | None:
    return getattr(_local, "id_corrida", None)


def desde_portal(id_portal: int, id_documento_portal: int, tipo_portal: str, d: dict) -> dict | None:
    """Registra el aviso de un documento recién guardado por la bóveda. Devuelve `{estado, nuevo}`.
    Nunca corta la corrida del portal: si falla, queda en el log."""
    tipo, modulo = DESTINO_PORTAL.get(tipo_portal, (tipo_portal, "sin_clasificar"))
    estado = ESTADO_PORTAL.get(d["estadoCarga"], "para_cargar")
    motivo = d.get("motivo")
    if estado == "para_cargar" and not motivo:
        motivo = "Revisar y cargar a mano"
    try:
        _, nuevo = repository.registrar_documento({
            "idRutinaCorrida": corrida_actual(), "origen": "portal", "idPortal": id_portal,
            "idDocumentoPortal": id_documento_portal, "sha256": d["sha256"], "ruta": d["ruta"], "tipo": tipo,
            "modulo": modulo, "idContacto": d.get("idContacto"), "fecha": d.get("fecha"),
            "numero": d.get("numeroDocumento"), "total": d.get("totalImpreso"), "estado": estado, "motivo": motivo,
            "idRegistro": d.get("idCompra"),
        })
    except Exception:
        log.exception("Documentos nuevos: no se pudo registrar el documento de portal %s", id_documento_portal)
        return None
    return {"estado": estado, "nuevo": nuevo}
