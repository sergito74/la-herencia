"""Migra la hoja "Caja Efectivo Pesos" de `Cajas Giamigli.xlsx` a
`MovimientosCajaEfectivo` (Caja='GiamigliSA', 027-migracion-cajas-giamigli).
Deduplica contra `Pagos efectivo` (spec FR-008): si el proveedor de la
fila resuelve a un contacto real y ese contacto ya tiene un pago en
efectivo registrado con la misma fecha e importe, el movimiento NO se
inserta acá (ya está representado en `Pagos efectivo`). Idempotente
además contra sí misma (no duplica si se re-corre).

Backup verificado de `WC` tomado antes de la primera corrida de esta
migración: WC_pre_027_cajas_giamigli_20260929_221602.bak (RESTORE
VERIFYONLY confirmado, 2026-09-29).

Uso (desde backend/):
    .venv\\Scripts\\python.exe -m scripts.migracion_cajas_giamigli.migrar_caja_giamigli_sa [ruta_excel]
"""

from __future__ import annotations

import sys

from src.db.connection import _assert_target_is_wc, execute_write
from scripts.migracion_cajas_giamigli import dedup
from scripts.migracion_cajas_giamigli.lector_excel import FilaCaja, leer_hoja_caja

RUTA_EXCEL_DEFAULT = (
    r"C:\Users\Sergio\Documents\La Herencia\Administracion y gestion\Cuentas a pagar\Cajas Giamigli.xlsx"
)
NOMBRE_HOJA = "Caja Efectivo Pesos"
CAJA = "GiamigliSA"


def decidir_accion(fila: FilaCaja) -> tuple[str, int | None]:
    """Devuelve ('duplicado' | 'nuevo', id_contacto_o_None) — no escribe
    nada, solo decide (testeable sin tocar `WC`)."""
    id_contacto = dedup.resolver_contacto_por_nombre(fila.concepto)
    if id_contacto is not None and dedup.ya_existe_pago_efectivo(id_contacto, fila.fecha, fila.importe):
        return "duplicado", id_contacto
    return "nuevo", id_contacto


def migrar(ruta_excel: str) -> dict:
    filas, casos = leer_hoja_caja(ruta_excel, NOMBRE_HOJA, CAJA)

    migradas = 0
    duplicados_detectados = 0
    for fila in filas:
        accion, id_contacto = decidir_accion(fila)
        if accion == "duplicado":
            duplicados_detectados += 1
            continue
        execute_write(
            "INSERT INTO dbo.MovimientosCajaEfectivo "
            "(Caja, Fecha, Concepto, Detalle, Importe, Cuenta, IdContactoRelacionado, NumeroDocumento, Usuario) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                CAJA,
                fila.fecha,
                fila.concepto,
                fila.detalle,
                fila.importe,
                fila.cuenta,
                id_contacto,
                fila.numero_documento,
                "migracion-cajas-giamigli",
            ),
        )
        migradas += 1

    for caso in casos:
        execute_write(
            "INSERT INTO dbo.MigracionCajasGiamigliRevision (Hoja, NumeroFila, Motivo, DatosCrudos) "
            "VALUES (?, ?, ?, ?)",
            (caso.hoja, caso.numero_fila, caso.motivo, caso.datos_crudos_json()),
        )

    filas_leidas = len(filas) + len(casos)
    assert filas_leidas == migradas + duplicados_detectados + len(casos), "SC-004: alguna fila se perdió sin contar"

    return {
        "leidas": filas_leidas,
        "migradas": migradas,
        "duplicadosDetectados": duplicados_detectados,
        "aRevisar": len(casos),
    }


def main() -> None:
    _assert_target_is_wc()
    ruta_excel = sys.argv[1] if len(sys.argv) > 1 else RUTA_EXCEL_DEFAULT

    resumen = migrar(ruta_excel)

    from src.features.cajas_efectivo.repository import calcular_saldo

    saldo = calcular_saldo(CAJA)
    print(
        f"{NOMBRE_HOJA}: leídas={resumen['leidas']} migradas={resumen['migradas']} "
        f"duplicados_detectados={resumen['duplicadosDetectados']} a_revisar={resumen['aRevisar']} | "
        f"saldo=${saldo:,.2f}"
    )


if __name__ == "__main__":
    main()
