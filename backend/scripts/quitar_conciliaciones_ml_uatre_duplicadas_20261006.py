"""Mercado Libre / UATRE: quita 6 conciliaciones que duplicaban pagos ya acreditados por Galicia.

Cada 'Pago de servicio UATRE' de la billetera de Mercado Libre es el espejo de un DEBIN de Galicia
del mismo día e importe, que ya está asignado a UATRE (contacto 315) en el movimiento bancario.
Las conciliaciones 4, 5, 6, 7 y 9 acreditaban el mismo pago por segunda vez a UATRE (nov-2025 y
may-ago 2026); la 10 es el 'Ingreso de dinero' de la billetera de agosto-2026 conciliado a Banco
Galicia (contacto 518), pata espejo de la 4. Criterio de Sergio: "el banco manda".

Las filas borradas se guardan en un JSON en la carpeta Auditoria cuentas corrientes.
Uso: python -m scripts.quitar_conciliaciones_ml_uatre_duplicadas_20261006 [--apply]
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path, PureWindowsPath

import pyodbc

from src.db.connection import CONNECTION_STRING, execute_write_transaction, fetch_all

IDS = [4, 5, 6, 7, 9, 10]
CARPETA = Path(r"C:\Users\Sergio\Documents\La Herencia\Administracion y gestion\Auditoria cuentas corrientes")


def _filas() -> list[dict]:
    ph = ",".join("?" * len(IDS))
    filas = fetch_all(
        f"""SELECT ct.IdConciliacion, ct.Medio, ct.IdMovimiento, ct.IdContacto, ct.Importe, ct.Usuario,
                   CONVERT(varchar(23), ct.Fecha, 121) AS Fecha, ct.TipoOrigenDocumento, ct.IdOrigenDocumento,
                   m.Descripcion, m.Importe AS ImporteML, CONVERT(varchar(10), m.Fecha, 23) AS FechaML
            FROM dbo.ConciliacionesTesoreria ct
            JOIN dbo.[Movimientos Mercado Libre] m ON m.IdMovimiento = ct.IdMovimiento
            WHERE ct.IdConciliacion IN ({ph}) AND ct.Medio = 'mercado-libre'""", tuple(IDS))
    assert len(filas) == len(IDS), f"Se esperaban {len(IDS)} filas, hay {len(filas)}"
    for f in filas:
        # cada una tiene un movimiento de Galicia del mismo día e importe, asignado a UATRE
        g = fetch_all("SELECT 1 FROM dbo.[Movimientos Galicia] WHERE IdContacto = 315 AND CONVERT(varchar(10), Fecha, 23) = ? "
                      "AND ABS([Débitos] - ?) < 0.01", (f["FechaML"], abs(f["ImporteML"])))
        assert g, f"Sin débito de Galicia para {f}"
        assert f["IdContacto"] in (315, 518), f
    return filas


def _backup() -> None:
    with pyodbc.connect(CONNECTION_STRING, autocommit=True) as conn:
        cur = conn.cursor()
        if cur.execute("SELECT DB_NAME()").fetchone()[0] != "WC":
            raise RuntimeError("Solo WC")
        carpeta = cur.execute("SELECT SERVERPROPERTY('InstanceDefaultBackupPath')").fetchone()[0]
        ruta = str(PureWindowsPath(carpeta) / f"WC_pre_ml_uatre_{datetime.now():%Y%m%d_%H%M%S}.bak")
        cur.execute("BACKUP DATABASE [WC] TO DISK = ? WITH COPY_ONLY, CHECKSUM", (ruta,))
        while cur.nextset():
            pass
        cur.execute("RESTORE VERIFYONLY FROM DISK = ? WITH CHECKSUM", (ruta,))
        while cur.nextset():
            pass
        print(f"BACKUP_VERIFICADO={ruta}")


def main(apply: bool) -> None:
    filas = _filas()
    print(f"Verificadas {len(filas)} conciliaciones; importe {sum(f['Importe'] for f in filas):,.2f}")
    if not apply:
        print("Solo verificación. Usar --apply.")
        return
    _backup()
    CARPETA.mkdir(parents=True, exist_ok=True)
    destino = CARPETA / f"conciliaciones_ml_uatre_quitadas_{datetime.now():%Y%m%d_%H%M%S}.json"
    destino.write_text(json.dumps(filas, default=str, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Respaldo de filas: {destino}")
    ph = ",".join("?" * len(IDS))
    execute_write_transaction([(f"DELETE FROM dbo.ConciliacionesTesoreria WHERE IdConciliacion IN ({ph}) AND Medio='mercado-libre'", tuple(IDS))])
    print("Conciliaciones quitadas.")


if __name__ == "__main__":
    main("--apply" in sys.argv)
