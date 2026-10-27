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
    return repository.insertar_foto(
        {"idPortal": id_portal, "idCorrida": id_corrida, "idContacto": id_contacto, "fechaCorte": estado.fecha_corte,
         "moneda": estado.moneda, "saldoPortal": saldo_portal, "saldoSistema": sistema, "diferencia": diferencia,
         "completa": estado.completa},
        [{"fecha": m.fecha, "comprobante": m.comprobante, "detalle": m.detalle, "debe": m.debe, "haber": m.haber,
          "saldo": m.saldo} for m in estado.movimientos],
    )
