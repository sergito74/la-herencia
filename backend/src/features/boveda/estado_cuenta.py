"""Foto del estado de cuenta de un portal comparada con el sistema (042, FR-019, research.md R6).

El saldo del sistema sale de la valuación bimonetaria de cuentas corrientes
(`auditoria_cuentas.bimonetaria.cargar_cuenta`, la misma de las fichas de
cierre): saldo acumulado en pesos y en dólares, en orden cronológico; el
saldo al corte es el de la última fila con fecha <= corte. Positivo = deuda
nuestra con el tercero, igual que la convención de `EstadoCuentaPortal`.

La comparación es al centavo, sin umbral (Sergio 27/10/2026). No crea
movimientos, asientos ni ajustes: solo registra la foto y la diferencia.
"""

from __future__ import annotations

import re

from datetime import date
from decimal import Decimal

from src.features.boveda import repository
from src.features.boveda.conectores import EstadoCuentaPortal


def saldo_sistema(id_contacto: int, corte: date, moneda: str) -> Decimal | None:
    from src.features.auditoria_cuentas.bimonetaria import cargar_cuenta

    c = cargar_cuenta(id_contacto)
    if moneda == "USD" and not c["tieneDolares"]:
        return None
    campo = "saldoDolares" if moneda == "USD" else "saldoPesos"
    saldo = Decimal("0")
    for f in c["filas"]:
        fecha = f["fecha"].date() if hasattr(f["fecha"], "date") else f["fecha"]
        if fecha > corte:
            break
        saldo = Decimal(str(f[campo]))
    return saldo.quantize(Decimal("0.01"))


def guardar(id_portal: int, id_corrida: int | None, id_contacto: int | None, estado: EstadoCuentaPortal) -> int:
    saldo_portal = Decimal(str(estado.saldo)).quantize(Decimal("0.01"))
    sistema = diferencia = None
    if estado.completa and id_contacto:
        sistema = saldo_sistema(id_contacto, estado.fecha_corte, estado.moneda)
        if sistema is not None:
            diferencia = saldo_portal - sistema
    id_foto = repository.insertar_foto(
        {"idPortal": id_portal, "idCorrida": id_corrida, "idContacto": id_contacto, "fechaCorte": estado.fecha_corte,
         "moneda": estado.moneda, "saldoPortal": saldo_portal, "saldoSistema": sistema, "diferencia": diferencia,
         "completa": estado.completa},
        [{"fecha": m.fecha, "comprobante": m.comprobante, "detalle": m.detalle, "debe": m.debe, "haber": m.haber,
          "saldo": m.saldo} for m in estado.movimientos],
    )
    if id_contacto:
        try:
            avisar_faltantes(id_portal, id_contacto, estado.movimientos)
        except Exception:
            import logging

            logging.getLogger(__name__).exception("Estado de cuenta: no se pudieron revisar las facturas faltantes")
    return id_foto


_FACTURA = re.compile(r"^\s*(?:FT|FC|FA|FACTURA)", re.I)
_NUMERO = re.compile(r"(\d{4,5})\s*-\s*(\d{8,9})")


def avisar_faltantes(id_portal: int, id_contacto: int, movimientos, dias: int = 120) -> int:
    """Facturas que el portal muestra en el estado de cuenta y no están cargadas en Compras (03/11/2026: ticket de
    Jáuregui y Morales del 27/10 que nadie avisó). Cada una queda en "Nuevos para revisar" una sola vez."""
    import hashlib
    from datetime import datetime, timedelta

    from src.features.documentos_nuevos import repository as nuevos

    desde = date.today() - timedelta(days=dias)
    avisos = 0
    for m in movimientos:
        n = _NUMERO.search(m.comprobante or m.detalle or "")
        if not n or not _FACTURA.search(m.detalle or "") or not m.fecha or m.fecha < desde:
            continue
        numero = f"{n.group(1)}-{n.group(2)}"
        if repository.compra_existente(id_contacto, numero, None):
            continue
        sha = hashlib.sha256(f"estado-cuenta:{id_portal}:{id_contacto}:{numero}".encode()).hexdigest()
        if nuevos.existente(sha):
            continue
        importe = m.haber or m.debe
        nuevos.registrar_documento({
            "idRutinaCorrida": None, "origen": "portal", "mailEntryId": None, "mailRemitente": "Estado de cuenta del portal",
            "mailAsunto": f"Factura {numero}", "mailRecibido": datetime.now(), "sha256": sha, "ruta": "",
            "tipo": "factura", "modulo": "compras", "idContacto": id_contacto, "fecha": m.fecha, "numero": numero,
            "total": importe, "estado": "para_cargar", "idRegistro": None,
            "motivo": "Figura en el estado de cuenta del portal y no está cargada: conseguir el comprobante y cargarlo",
        })
        avisos += 1
    return avisos
