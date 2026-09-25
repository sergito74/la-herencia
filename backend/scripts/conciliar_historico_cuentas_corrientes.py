"""Conciliación histórica de cuentas corrientes de proveedores y ventas
(020-conciliacion-historica-cuentas-corrientes).

Aplica retroactivamente los movimientos de tesorería sin aplicar contra
sus documentos (compras/ventas), reutilizando la sugerencia FIFO de 019
(ver `src/features/conciliacion_historico/repository.py`). Clasifica cada
movimiento en exacto / mejor esfuerzo (tolerancia 2%, research.md §4) /
excepción, y solo escribe si se pasa `--apply`.

Por defecto corre en modo DRY-RUN (solo lectura): imprime el resumen y no
escribe nada. Requiere `--apply` para escribir, y aun así NO EJECUTAR sin
backup de `WC` verificado y autorización explícita del usuario
(Constitución, Principio II).

Idempotente: `movimientos_sin_aplicar` excluye los movimientos que ya
tienen una aplicación vigente (manual o de una corrida anterior de este
mismo script), así que correrlo dos veces no duplica nada.

Uso (desde backend/):
  .venv\\Scripts\\python.exe -m scripts.conciliar_historico_cuentas_corrientes                  # dry-run, todo el rango
  .venv\\Scripts\\python.exe -m scripts.conciliar_historico_cuentas_corrientes --apply           # escribe
  .venv\\Scripts\\python.exe -m scripts.conciliar_historico_cuentas_corrientes --contacto 123    # limita a un contacto (debug)
"""

import argparse
import csv
from datetime import date, datetime

from src.db.connection import _assert_target_is_wc
from src.features.conciliacion_historico.repository import (
    aplicar_clasificacion,
    clasificar_movimiento,
    movimientos_sin_aplicar,
    registrar_en_log,
    subcategorizar_excepcion,
)

FECHA_DESDE = date(2015, 1, 1)
FECHA_HASTA = date(2026, 12, 31)


def _procesar(fecha_desde: date, fecha_hasta: date, id_contacto: int | None, aplicar: bool) -> list[dict]:
    """Clasifica cada movimiento y, si `aplicar`, lo escribe inmediatamente
    después de clasificarlo — en la misma pasada, nunca en una segunda
    reclasificación. Aplicar un movimiento consume saldo pendiente de sus
    documentos, lo que puede cambiar la clasificación de un movimiento
    posterior del mismo contacto/documento; reclasificar más tarde con un
    estado ya desactualizado del pendiente producía resultados inconsistentes
    con el resumen ya impreso (bug encontrado corriendo --apply real,
    2026-09-25: un movimiento que había salido "exacto" en la primera pasada
    volvía a clasificarse como excepción en la segunda, porque otro
    movimiento anterior en el mismo run ya había consumido el documento)."""
    filas = []
    for movimiento in movimientos_sin_aplicar(fecha_desde, fecha_hasta):
        origen_movimiento = movimiento["origenMovimiento"]
        id_movimiento_origen = movimiento["idMovimientoOrigen"]

        clasificacion = clasificar_movimiento(origen_movimiento, id_movimiento_origen)
        id_contacto_movimiento = clasificacion["idContacto"]

        if id_contacto is not None and id_contacto_movimiento != id_contacto:
            continue

        if aplicar and clasificacion["clasificacion"] in ("automatica-exacta", "automatica-mejor-esfuerzo"):
            aplicar_clasificacion(origen_movimiento, id_movimiento_origen, clasificacion)

        subcategoria = (
            subcategorizar_excepcion(id_contacto_movimiento) if clasificacion["clasificacion"] == "excepcion" else None
        )
        filas.append(
            {
                "origenMovimiento": origen_movimiento,
                "idMovimientoOrigen": id_movimiento_origen,
                "idContacto": id_contacto_movimiento,
                "clasificacion": clasificacion["clasificacion"],
                "subcategoria": subcategoria,
                "detalle": clasificacion.get("notaConciliacion") or clasificacion.get("motivo") or "",
            }
        )
    return filas


def _imprimir_resumen(filas: list[dict]) -> None:
    conteos = {"automatica-exacta": 0, "automatica-mejor-esfuerzo": 0, "excepcion": 0}
    for fila in filas:
        conteos[fila["clasificacion"]] = conteos.get(fila["clasificacion"], 0) + 1

    print(f"Movimientos procesados: {len(filas)}")
    print(f"  Exactos:        {conteos['automatica-exacta']}")
    print(f"  Mejor esfuerzo: {conteos['automatica-mejor-esfuerzo']}")
    print(f"  Excepciones:    {conteos['excepcion']}")


def _escribir_csv(filas: list[dict]) -> str:
    nombre = f"conciliacion_historico_{datetime.now():%Y%m%d_%H%M%S}.csv"
    campos = ["origenMovimiento", "idMovimientoOrigen", "idContacto", "clasificacion", "subcategoria", "detalle"]
    with open(nombre, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        writer.writerows(filas)
    return nombre


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Escribe las aplicaciones en WC (default: dry-run)")
    parser.add_argument("--contacto", type=int, default=None, help="Limita el proceso a un IdContacto (debug/validación puntual)")
    args = parser.parse_args()

    _assert_target_is_wc()

    filas = _procesar(FECHA_DESDE, FECHA_HASTA, args.contacto, args.apply)
    _imprimir_resumen(filas)

    if args.apply:
        aplicadas = sum(1 for f in filas if f["clasificacion"] in ("automatica-exacta", "automatica-mejor-esfuerzo"))
        print(f"Aplicadas {aplicadas} clasificaciones a dbo.AplicacionesPago.")
    else:
        print("Dry-run: no se escribió nada. Volver a correr con --apply para aplicar (requiere backup de WC verificado).")

    registrar_en_log(filas)
    print(f"Log actualizado en dbo.ConciliacionHistoricoLog ({len(filas)} filas).")

    csv_path = _escribir_csv(filas)
    print(f"Auditoría completa en: {csv_path}")


if __name__ == "__main__":
    main()
