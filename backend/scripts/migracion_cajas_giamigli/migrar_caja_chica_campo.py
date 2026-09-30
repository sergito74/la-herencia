"""Migra la hoja "Caja chica campo" de `Cajas Giamigli.xlsx` a
`MovimientosCajaEfectivo` (Caja='CampoChica', 027-migracion-cajas-giamigli).
Sin overlap conocido con otra tabla del sistema — la única deduplicación
es contra sí misma (idempotencia de re-corrida, `dedup.ya_existe_movimiento_caja`).

Backup verificado de `WC` tomado antes de la primera corrida de esta
migración: WC_pre_027_cajas_giamigli_20260929_221602.bak (RESTORE
VERIFYONLY confirmado, 2026-09-29).

Uso (desde backend/):
    .venv\\Scripts\\python.exe -m scripts.migracion_cajas_giamigli.migrar_caja_chica_campo [ruta_excel]
"""

from __future__ import annotations

import sys

from src.db.connection import _assert_target_is_wc, execute_write
from scripts.migracion_cajas_giamigli import dedup
from scripts.migracion_cajas_giamigli.lector_excel import leer_hoja_caja

RUTA_EXCEL_DEFAULT = (
    r"C:\Users\Sergio\Documents\La Herencia\Administracion y gestion\Cuentas a pagar\Cajas Giamigli.xlsx"
)
NOMBRE_HOJA = "Caja chica campo"
CAJA = "CampoChica"


def migrar(ruta_excel: str) -> dict:
    filas, casos = leer_hoja_caja(ruta_excel, NOMBRE_HOJA, CAJA)

    migradas = 0
    deduplicadas = 0
    for fila in filas:
        if dedup.ya_existe_movimiento_caja(CAJA, fila.fecha, fila.importe, fila.concepto):
            deduplicadas += 1
            continue
        execute_write(
            "INSERT INTO dbo.MovimientosCajaEfectivo "
            "(Caja, Fecha, Concepto, Detalle, Importe, FormaPago, Usuario) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (CAJA, fila.fecha, fila.concepto, fila.detalle, fila.importe, fila.forma_pago, "migracion-cajas-giamigli"),
        )
        migradas += 1

    for caso in casos:
        execute_write(
            "INSERT INTO dbo.MigracionCajasGiamigliRevision (Hoja, NumeroFila, Motivo, DatosCrudos) "
            "VALUES (?, ?, ?, ?)",
            (caso.hoja, caso.numero_fila, caso.motivo, caso.datos_crudos_json()),
        )

    filas_leidas = len(filas) + len(casos)
    assert filas_leidas == migradas + len(casos), "SC-004: alguna fila se perdió sin contar"

    return {"leidas": filas_leidas, "migradas": migradas, "deduplicadas": deduplicadas, "aRevisar": len(casos)}


def main() -> None:
    _assert_target_is_wc()
    ruta_excel = sys.argv[1] if len(sys.argv) > 1 else RUTA_EXCEL_DEFAULT

    resumen = migrar(ruta_excel)

    from src.features.cajas_efectivo.repository import calcular_saldo

    saldo = calcular_saldo(CAJA)
    print(
        f"{NOMBRE_HOJA}: leídas={resumen['leidas']} migradas={resumen['migradas']} "
        f"deduplicadas={resumen['deduplicadas']} a_revisar={resumen['aRevisar']} | saldo=${saldo:,.2f}"
    )


if __name__ == "__main__":
    main()
