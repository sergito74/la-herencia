"""035 — Carga fila a fila la referencia del Access hasta el corte, para explicar las diferencias de saldo.

Lee SOLO LECTURA `LaHerencia.dbo.vw_MovimientosCuenta_Base` (hasta la fecha de corte de
`SaldosReferenciaAccess`) y la guarda en `WC.dbo.SaldosReferenciaAccessDetalle`. Nunca escribe en
`LaHerencia`. Es re-ejecutable: reemplaza lo cargado.

Uso (desde backend/):
    python -m scripts.cargar_referencia_detalle_035 --verificar
    python -m scripts.cargar_referencia_detalle_035
"""

from __future__ import annotations

import sys
from datetime import datetime

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_read_only, _assert_target_is_wc, fetch_one

SQL_LH = (
    "SELECT Origen, IdOrigen, IdContacto, Fecha, ISNULL(Deuda, 0) AS Deuda, ISNULL(Credito, 0) AS Credito "
    "FROM dbo.vw_MovimientosCuenta_Base WHERE Fecha <= ?"
)


def _filas_laherencia(corte: datetime) -> list[tuple]:
    _assert_read_only(SQL_LH)
    conn = pyodbc.connect("DSN=SQL_LaHerencia;Trusted_Connection=Yes;DATABASE=LaHerencia;", autocommit=True, readonly=True)
    try:
        cur = conn.cursor()
        cur.execute(SQL_LH, corte)
        return [(r.Origen, int(r.IdOrigen), int(r.IdContacto), r.Fecha, r.Deuda, r.Credito) for r in cur.fetchall()
                if r.IdContacto is not None]
    finally:
        conn.close()


def main(argv: list[str]) -> None:
    _assert_target_is_wc()
    corte = fetch_one("SELECT MAX(FechaCorte) AS c FROM dbo.SaldosReferenciaAccess", ())["c"]
    corte_dt = datetime.fromisoformat(str(corte)[:10] + "T23:59:59")
    filas = _filas_laherencia(corte_dt)
    print(f"Fecha de corte: {str(corte)[:10]}; filas de LaHerencia hasta el corte: {len(filas)}")
    if "--verificar" in argv:
        print("Solo verificación: no se escribió nada.")
        return
    from src.features.vinculos.backup import backup_verificado

    print(f"Respaldo verificado: {backup_verificado('referencia-detalle-035')}")
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=False)
    try:
        cur = conn.cursor()
        if cur.execute("SELECT DB_NAME()").fetchone()[0] != "WC":
            raise RuntimeError("Solo sobre WC")
        cur.execute("DELETE FROM dbo.SaldosReferenciaAccessDetalle")
        cur.fast_executemany = True
        cur.executemany(
            "INSERT INTO dbo.SaldosReferenciaAccessDetalle (Origen, IdOrigen, IdContacto, Fecha, Deuda, Credito) VALUES (?, ?, ?, ?, ?, ?)",
            filas,
        )
        conn.commit()
        n = cur.execute("SELECT COUNT(*) FROM dbo.SaldosReferenciaAccessDetalle").fetchone()[0]
        print(f"Cargadas {n} filas.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main(sys.argv[1:])
