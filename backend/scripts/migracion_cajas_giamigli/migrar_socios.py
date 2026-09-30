"""Migra las 4 hojas de socios de `Cajas Giamigli.xlsx` a
`MovimientosCuentaSocio` (027-migracion-cajas-giamigli). Idempotente:
usa `dedup.ya_existe_movimiento_socio` antes de insertar, seguro de
re-correr. Nunca escribe en `LaHerencia`.

Backup verificado de `WC` tomado antes de la primera corrida de esta
migración: WC_pre_027_cajas_giamigli_20260929_221602.bak (RESTORE
VERIFYONLY confirmado, 2026-09-29).

Uso (desde backend/):
    .venv\\Scripts\\python.exe -m scripts.migracion_cajas_giamigli.migrar_socios [ruta_excel]
"""

from __future__ import annotations

import sys
from collections import Counter

from src.db.connection import _assert_target_is_wc, execute_write, fetch_all
from scripts.migracion_cajas_giamigli.lector_excel import leer_hoja_socio

RUTA_EXCEL_DEFAULT = (
    r"C:\Users\Sergio\Documents\La Herencia\Administracion y gestion\Cuentas a pagar\Cajas Giamigli.xlsx"
)

# Nombre de hoja -> IdSocio (catálogo cerrado de 021, confirmado contra WC).
HOJA_A_ID_SOCIO = {
    "Cuenta Sergio": 1,
    "Cuenta Lucy": 2,
    "Cuenta Cond LSC": 3,
    "Cuenta Ceci": 4,
}


def _insertar_caso_a_revisar(caso) -> None:
    execute_write(
        "INSERT INTO dbo.MigracionCajasGiamigliRevision (Hoja, NumeroFila, Motivo, DatosCrudos) "
        "VALUES (?, ?, ?, ?)",
        (caso.hoja, caso.numero_fila, caso.motivo, caso.datos_crudos_json()),
    )


def _baseline_socio(id_socio: int) -> Counter:
    """Foto de lo que YA existe en `MovimientosCuentaSocio` para este socio
    ANTES de esta corrida (los 7 movimientos cargados a mano el
    2026-09-29/30, o lo que haya quedado de una corrida anterior de este
    mismo script). Se usa como un multiset: cada coincidencia consume una
    unidad, así dos filas del propio Excel con la misma fecha e importe
    (coincidencia real, no error) NUNCA se fusionan entre sí — solo se
    deduplica contra lo que existía de antes, nunca contra lo que esta
    misma corrida va insertando (bug real encontrado y corregido
    2026-09-30: la versión anterior comparaba contra una consulta en vivo,
    que encontraba la primera fila recién insertada como si fuera un
    duplicado de la segunda)."""
    filas = fetch_all(
        "SELECT Fecha, Importe FROM dbo.MovimientosCuentaSocio WHERE IdSocio = ? AND Anulada = 0",
        (id_socio,),
    )
    return Counter((_a_fecha_date(fila["Fecha"]), round(float(fila["Importe"]), 2)) for fila in filas)


def _a_fecha_date(valor):
    if isinstance(valor, str):
        from datetime import datetime as _dt

        return _dt.fromisoformat(valor).date()
    return valor.date()


def migrar_hoja(ruta_excel: str, nombre_hoja: str, id_socio: int) -> dict:
    filas, casos = leer_hoja_socio(ruta_excel, nombre_hoja)
    baseline = _baseline_socio(id_socio)

    migradas = 0
    deduplicadas = 0
    for fila in filas:
        clave = (fila.fecha, round(fila.importe_pesos, 2))
        if baseline[clave] > 0:
            baseline[clave] -= 1
            deduplicadas += 1
            continue
        motivo = f"{fila.proveedor or ''} — {fila.detalle or ''}".strip(" —")
        execute_write(
            "INSERT INTO dbo.MovimientosCuentaSocio "
            "(IdSocio, Tipo, Importe, ImporteUSD, ImporteKgCarne, Fecha, Medio, Motivo, Usuario) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                id_socio,
                fila.tipo,
                fila.importe_pesos,
                fila.importe_usd,
                fila.importe_kg_carne,
                fila.fecha,
                fila.forma_pago,
                motivo or None,
                "migracion-cajas-giamigli",
            ),
        )
        migradas += 1

    for caso in casos:
        _insertar_caso_a_revisar(caso)

    filas_leidas = len(filas) + len(casos)
    assert filas_leidas == migradas + deduplicadas + len(casos), "SC-004: alguna fila se perdió sin contar"

    return {
        "hoja": nombre_hoja,
        "leidas": filas_leidas,
        "migradas": migradas,
        "deduplicadas": deduplicadas,
        "aRevisar": len(casos),
    }


def _saldo_actual(id_socio: int) -> dict:
    from src.features.cuentas_socios.repository import calcular_saldo

    return calcular_saldo(id_socio)


def main() -> None:
    _assert_target_is_wc()
    ruta_excel = sys.argv[1] if len(sys.argv) > 1 else RUTA_EXCEL_DEFAULT

    for nombre_hoja, id_socio in HOJA_A_ID_SOCIO.items():
        resumen = migrar_hoja(ruta_excel, nombre_hoja, id_socio)
        saldo = _saldo_actual(id_socio)
        print(
            f"{resumen['hoja']}: leídas={resumen['leidas']} migradas={resumen['migradas']} "
            f"deduplicadas={resumen['deduplicadas']} a_revisar={resumen['aRevisar']} | "
            f"saldo pesos=${saldo['saldoPesos']:,.2f} USD={saldo['saldoUSD']:,.2f} "
            f"KgCarne={saldo['saldoKgCarne']:,.2f}"
        )


if __name__ == "__main__":
    main()
