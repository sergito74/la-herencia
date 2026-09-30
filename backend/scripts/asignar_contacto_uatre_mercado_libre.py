"""Backfill: asigna el contacto "UATRE" a los movimientos de Mercado Libre
ya cargados cuya descripción contiene "UATRE" y todavía no tienen
`IdContacto` (backlog post-025, punto 2 — ver memoria
`project_backlog_post_tarjetas_impuestos`).

La descripción real de estos pagos nunca es exactamente "UATRE" (viene
como "Pago de servicio(s) UATRE"), así que la resolución por coincidencia
exacta del loader (`cargar_resumenes_mercado_libre_pdf.py::_resolver_
contacto`) nunca los resolvía — confirmado 2026-09-30: 29 movimientos
reales, todos con `IdContacto IS NULL`, 100% de las filas con "UATRE" en
`Descripcion`. El loader ya se corrigió para resolver este caso a futuro;
este script solo backfillea lo ya cargado.

Por defecto corre en modo DRY-RUN. Requiere `--apply` para escribir, y aun
así NO EJECUTAR sin backup de `WC` verificado (Constitución, Principio II).

Uso (desde backend/):
  .venv\\Scripts\\python.exe -m scripts.asignar_contacto_uatre_mercado_libre           # dry-run
  .venv\\Scripts\\python.exe -m scripts.asignar_contacto_uatre_mercado_libre --apply    # escribe
"""

from __future__ import annotations

import argparse

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, fetch_one


def _id_contacto_uatre() -> int:
    fila = fetch_one("SELECT IdContacto FROM dbo.Contactos WHERE [Razon Social] = 'UATRE'")
    if fila is None:
        raise ValueError("No existe el contacto 'UATRE' en dbo.Contactos.")
    return fila["IdContacto"]


def _movimientos_pendientes() -> list[dict]:
    return fetch_all(
        "SELECT IdMovimiento, Fecha, Descripcion, Importe "
        "FROM dbo.[Movimientos Mercado Libre] "
        "WHERE IdContacto IS NULL AND Descripcion LIKE '%UATRE%' "
        "ORDER BY Fecha"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Escribe en WC (default: dry-run)")
    args = parser.parse_args()

    _assert_target_is_wc()

    id_uatre = _id_contacto_uatre()
    pendientes = _movimientos_pendientes()

    print(f"Contacto UATRE: IdContacto={id_uatre}")
    print(f"{len(pendientes)} movimientos de Mercado Libre a asignar:")
    for m in pendientes:
        print(f"  {m['Fecha']} · {m['Descripcion']:30s} · {m['Importe']:>12,.2f}")

    if args.apply:
        statements = [
            ("UPDATE dbo.[Movimientos Mercado Libre] SET IdContacto = ? WHERE IdMovimiento = ?", (id_uatre, m["IdMovimiento"]))
            for m in pendientes
        ]
        if statements:
            execute_write_transaction(statements)
        print(f"\nAplicados {len(pendientes)} movimientos.")
    else:
        print("\nDry-run: no se escribió nada. Correr con --apply para aplicar (requiere backup de WC verificado).")


if __name__ == "__main__":
    main()
