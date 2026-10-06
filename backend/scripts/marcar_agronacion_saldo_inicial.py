"""Agronación: los resúmenes 571 a 578 (nov-2011 a jun-2012) son el saldo inicial de la
administración anterior (Oscar y Albina), sin registros completos. Se marcan 'Cerrado'
(no se concilian ni generan créditos) con una nota; no se modifica ningún importe.
El resumen 579 (jul-2012) es el cierre de la tarjeta vieja y el 580 (jun-2013) el primero
de la tarjeta nueva a nombre de Giamigli de Bolivar.

Uso: python -m scripts.marcar_agronacion_saldo_inicial [--apply]
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import PureWindowsPath

import pyodbc

from src.db.connection import CONNECTION_STRING, execute_write_transaction, fetch_all

IDS = list(range(571, 579))
NOTA = "Saldo inicial: administración anterior (Oscar y Albina); sin registros completos del período."


def _backup() -> None:
    with pyodbc.connect(CONNECTION_STRING, autocommit=True) as conn:
        cur = conn.cursor()
        if cur.execute("SELECT DB_NAME()").fetchone()[0] != "WC":
            raise RuntimeError("Solo WC")
        carpeta = cur.execute("SELECT SERVERPROPERTY('InstanceDefaultBackupPath')").fetchone()[0]
        ruta = str(PureWindowsPath(carpeta) / f"WC_pre_agronacion_saldo_inicial_{datetime.now():%Y%m%d_%H%M%S}.bak")
        cur.execute("BACKUP DATABASE [WC] TO DISK = ? WITH COPY_ONLY, CHECKSUM", (ruta,))
        while cur.nextset():
            pass
        cur.execute("RESTORE VERIFYONLY FROM DISK = ? WITH CHECKSUM", (ruta,))
        while cur.nextset():
            pass
        print(f"BACKUP_VERIFICADO={ruta}")


def main(apply: bool) -> None:
    ph = ",".join("?" * len(IDS))
    filas = fetch_all(
        f"SELECT IdResumen, IdTarjeta, EstadoResumen FROM dbo.Tarjetas_Resumenes WHERE IdResumen IN ({ph})", tuple(IDS)
    )
    assert len(filas) == len(IDS) and all(f["IdTarjeta"] == 1 for f in filas), "Los resúmenes no son los esperados"
    print(f"{len(filas)} resúmenes de Agronación; estados actuales: {sorted({f['EstadoResumen'] for f in filas})}")
    if not apply:
        print("Solo verificación. Usar --apply.")
        return
    _backup()
    statements = [
        (f"UPDATE dbo.Tarjetas_Resumenes SET EstadoResumen='Cerrado', FechaEstado=GETDATE(), "
         f"ObservacionesEstado=? WHERE IdResumen IN ({ph})", (NOTA, *IDS)),
        ("UPDATE dbo.Tarjetas_Resumenes SET Observaciones=? WHERE IdResumen=571 AND Observaciones IS NULL", (NOTA,)),
    ]
    execute_write_transaction(statements)
    print("Marcados como saldo inicial.")


if __name__ == "__main__":
    main("--apply" in sys.argv)
