"""Verificación de saldos contra el sistema real (020, US3 — research.md §2,
actualizado 2026-09-25).

El "sistema Access" no es un archivo `.accdb` con datos propios: los
`.accdb` de `La Herencia/*.accdb` son un front-end cuyas tablas están
enlazadas por ODBC (confirmado: `SYNONYM` en `cur.tables()`, mismo DSN
`SQL_LaHerencia`) a la base SQL Server **`LaHerencia`** — la base oficial
protegida, que Access sigue escribiendo en producción (confirmado
2026-09-25: `LaHerencia` tiene 6.436 `Compras` contra 6.435 de `WC`, y no
tiene rastro de `AplicacionesPago` — está viva, y aislada de nuestro
trabajo). Esa es la fuente de verdad real: el saldo que muestra Access
hoy es ni más ni menos que `vw_MovimientosCuenta_Saldo` calculado sobre
`LaHerencia`, la misma vista y fórmula que ya usa `cuentas_corrientes`
(004) sobre `WC`.

Este script:
1. Lee (solo lectura, nunca escribe en `LaHerencia`) el saldo actual por
   contacto directamente de `LaHerencia`.
2. Lee el saldo actual por contacto de `WC` reutilizando
   `cuentas_corrientes.repository.get_saldos_todos` sin modificarlo.
3. Guarda el saldo de `LaHerencia` en `dbo.SaldosReferenciaAccess` (en
   `WC`) para que `GET /api/conciliacion-historico/saldos` lo compare
   contra el saldo actual sin tener que releer `LaHerencia` en cada
   consulta.
4. Imprime el resumen: cuántos contactos coinciden (dentro de la
   tolerancia) y cuántos difieren, con el detalle de los que difieren.

Uso (desde backend/):
  .venv\\Scripts\\python.exe -m scripts.comparar_saldo_laherencia            # dry-run
  .venv\\Scripts\\python.exe -m scripts.comparar_saldo_laherencia --apply    # guarda en SaldosReferenciaAccess
"""

from __future__ import annotations

import argparse
from datetime import date

import pyodbc

from src.db.connection import _assert_read_only, _coerce_row, execute_write
from src.features.cuentas_corrientes.repository import get_saldos_todos

TOLERANCIA_RELATIVA_SALDO = 0.005  # 0.5%, decidido con el usuario 2026-09-25
TOLERANCIA_ABSOLUTA_MINIMA = 1.0  # evita que saldos cercanos a $0 exijan una precisión irreal


def _fetch_laherencia(sql: str) -> list[dict]:
    """Conexión de solo lectura a `LaHerencia`, aislada de `src/db/connection`
    (que solo admite `WC`). Reutiliza el mismo guard `_assert_read_only`
    para que sea imposible, incluso por error, ejecutar algo que no sea
    `SELECT` contra la base protegida."""
    _assert_read_only(sql)
    conn = pyodbc.connect("DSN=SQL_LaHerencia;Trusted_Connection=Yes;DATABASE=LaHerencia;", autocommit=True, readonly=True)
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        columns = [c[0] for c in cursor.description]
        return [_coerce_row(dict(zip(columns, row, strict=True))) for row in cursor.fetchall()]
    finally:
        conn.close()


def _saldos_laherencia() -> dict[int, float]:
    filas = _fetch_laherencia(
        """
        SELECT IdContacto, SaldoParcial
        FROM (
            SELECT IdContacto, SaldoParcial,
                   ROW_NUMBER() OVER (
                       PARTITION BY IdContacto
                       ORDER BY Fecha DESC, Origen DESC, IdOrigen DESC
                   ) AS rn
            FROM dbo.vw_MovimientosCuenta_Saldo
        ) ultimos
        WHERE rn = 1
        """
    )
    return {f["IdContacto"]: float(f["SaldoParcial"]) for f in filas}


def _es_conciliado(saldo_wc: float, saldo_laherencia: float) -> bool:
    diferencia = abs(saldo_wc - saldo_laherencia)
    tolerancia = max(TOLERANCIA_ABSOLUTA_MINIMA, abs(saldo_laherencia) * TOLERANCIA_RELATIVA_SALDO)
    return diferencia <= tolerancia


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Guarda el resultado en dbo.SaldosReferenciaAccess (WC)")
    args = parser.parse_args()

    print("Leyendo saldos de LaHerencia (solo lectura)...")
    saldos_laherencia = _saldos_laherencia()
    print(f"  {len(saldos_laherencia)} contactos con saldo en LaHerencia.")

    print("Leyendo saldos de WC...")
    saldos_wc = {f["idContacto"]: float(f["saldoParcial"] or 0) for f in get_saldos_todos()}
    print(f"  {len(saldos_wc)} contactos con saldo en WC.")

    conciliados = 0
    con_diferencia = []
    hoy = date.today()

    for id_contacto, saldo_lh in saldos_laherencia.items():
        saldo_wc = saldos_wc.get(id_contacto, 0.0)
        if _es_conciliado(saldo_wc, saldo_lh):
            conciliados += 1
        else:
            con_diferencia.append((id_contacto, saldo_wc, saldo_lh, round(saldo_wc - saldo_lh, 2)))

        if args.apply:
            execute_write("DELETE FROM dbo.SaldosReferenciaAccess WHERE IdContacto = ?", (id_contacto,))
            execute_write(
                "INSERT INTO dbo.SaldosReferenciaAccess (IdContacto, SaldoAccess, FechaCorte) VALUES (?, ?, ?)",
                (id_contacto, saldo_lh, hoy),
            )

    print(f"\nConciliados (dentro de tolerancia {TOLERANCIA_RELATIVA_SALDO:.1%}): {conciliados}")
    print(f"Con diferencia: {len(con_diferencia)}")
    for id_contacto, saldo_wc, saldo_lh, diferencia in sorted(con_diferencia, key=lambda x: -abs(x[3]))[:20]:
        print(f"  Contacto #{id_contacto}: WC={saldo_wc:.2f} LaHerencia={saldo_lh:.2f} diferencia={diferencia:.2f}")

    if args.apply:
        print(f"\nGuardado en dbo.SaldosReferenciaAccess ({len(saldos_laherencia)} contactos).")
    else:
        print("\nDry-run: no se escribió nada. Correr con --apply para guardar en dbo.SaldosReferenciaAccess.")


if __name__ == "__main__":
    main()
