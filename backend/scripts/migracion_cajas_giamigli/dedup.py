"""Regla de deduplicación de la migración de Cajas Giamigli
(027-migracion-cajas-giamigli, spec Clarifications / research.md §3):
dos movimientos son "el mismo" cuando coinciden fecha + proveedor/contacto
+ importe, con tolerancia de redondeo de $0,01.

Para las cuentas de socios, el universo de "ya cargado a mano" es chico y
conocido (los 7 movimientos confirmados con el usuario el 2026-09-29/30)
y se resuelve comparando contra `MovimientosCuentaSocio` por
`(IdSocio, Fecha, Importe)` — no hace falta comparar proveedor ahí porque
`IdSocio` ya acota al mismo socio.

Para la caja de Giamigli SA, que se solapa con `Pagos efectivo`
(spec FR-008), hace falta resolver el proveedor de la planilla a un
`IdContacto` real antes de poder comparar.
"""

from __future__ import annotations

from datetime import date

from src.db.connection import fetch_one

TOLERANCIA_IMPORTE = 0.01


def ya_existe_movimiento_socio(id_socio: int, fecha: date, importe_pesos: float) -> bool:
    fila = fetch_one(
        "SELECT TOP 1 1 AS x FROM dbo.MovimientosCuentaSocio "
        "WHERE IdSocio = ? AND Fecha = ? AND Anulada = 0 AND ABS(Importe - ?) <= ?",
        (id_socio, fecha, importe_pesos, TOLERANCIA_IMPORTE),
    )
    return fila is not None


def resolver_contacto_por_nombre(nombre: str | None) -> int | None:
    if not nombre or not nombre.strip():
        return None
    fila = fetch_one(
        "SELECT TOP 1 IdContacto AS id FROM dbo.Contactos WHERE UPPER([Razon Social]) = UPPER(?)",
        (nombre.strip(),),
    )
    return fila["id"] if fila else None


def ya_existe_pago_efectivo(id_contacto: int, fecha: date, importe: float) -> bool:
    fila = fetch_one(
        "SELECT TOP 1 1 AS x FROM dbo.[Pagos efectivo] "
        "WHERE IdContacto = ? AND Fecha = ? AND ABS([Importe imputado] - ?) <= ?",
        (id_contacto, fecha, abs(importe), TOLERANCIA_IMPORTE),
    )
    return fila is not None


def ya_existe_movimiento_caja(caja: str, fecha: date, importe: float, concepto: str | None) -> bool:
    """Idempotencia de re-corrida para las cajas nuevas (sin overlap con
    otra tabla conocido) — evita duplicar si el script se corre dos veces."""
    fila = fetch_one(
        "SELECT TOP 1 1 AS x FROM dbo.MovimientosCajaEfectivo "
        "WHERE Caja = ? AND Fecha = ? AND ABS(Importe - ?) <= ? AND ISNULL(Concepto, '') = ISNULL(?, '')",
        (caja, fecha, importe, TOLERANCIA_IMPORTE, concepto),
    )
    return fila is not None
