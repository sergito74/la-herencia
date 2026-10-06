"""Quita 30 conciliaciones de cheques propios que acreditaban el mismo pago a un segundo contacto.

Los 30 cheques (Valores propios cobrados) ya figuran como movimiento del Banco Nación asignado al
contacto correcto (el comentario del cheque nombra al beneficiario); las conciliaciones masivas del
29/09/2026 ('conciliacion-masiva' / 'conciliacion-masiva-fifo') los ataron a otro contacto y
documento. Criterio de Sergio (2026-10-06): "el banco manda". Auditoría: Documents/La Herencia/
Administracion y gestion/Auditoria cuentas corrientes/Auditoria_30_cheques_propios.xlsx

Cada fila borrada se guarda antes en un JSON junto al Excel para poder reponerla.

Uso: python -m scripts.quitar_conciliaciones_cheques_duplicadas_20261006 [--apply]
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path, PureWindowsPath

import pyodbc

from src.db.connection import CONNECTION_STRING, execute_write_transaction, fetch_all

IDS = [1279, 1290, 1297, 1312, 1314, 1335, 1337, 1338, 1342, 1343, 1345, 1351, 1358, 1366, 1367, 1370, 1381, 1394,
       1396, 1421, 1425, 1446, 1461, 1462, 1466, 1469, 1471, 1480, 1507, 1539]
CARPETA = Path(r"C:\Users\Sergio\Documents\La Herencia\Administracion y gestion\Auditoria cuentas corrientes")


def _filas() -> list[dict]:
    ph = ",".join("?" * len(IDS))
    filas = fetch_all(
        f"""SELECT ct.IdConciliacion, ct.Medio, ct.IdMovimiento, ct.IdContacto, ct.Importe, ct.Usuario,
                   CONVERT(varchar(23), ct.Fecha, 121) AS Fecha, ct.TipoOrigenDocumento, ct.IdOrigenDocumento,
                   b.IdMovimientoBNA, b.IdContacto AS ContactoBanco
            FROM dbo.ConciliacionesTesoreria ct
            JOIN dbo.[Valores propios] v ON v.IdValor = ct.IdMovimiento
            JOIN dbo.[Movimientos BNA] b ON TRY_CAST(b.[Nro# Comprobante] AS decimal(38,0)) = TRY_CAST(v.[Numero cheque] AS decimal(38,0))
                                         AND ABS(ABS(b.Importe) - v.Importe) < 0.01
            WHERE ct.IdConciliacion IN ({ph})""", tuple(IDS))
    assert len(filas) == len(IDS), f"Se esperaban {len(IDS)} filas, hay {len(filas)}"
    for f in filas:
        assert f["Medio"] == "valores-propios" and f["Usuario"].startswith("conciliacion-masiva"), f
        assert (f["ContactoBanco"] or 0) > 0 and f["ContactoBanco"] != f["IdContacto"], f
    return filas


def _backup() -> None:
    with pyodbc.connect(CONNECTION_STRING, autocommit=True) as conn:
        cur = conn.cursor()
        if cur.execute("SELECT DB_NAME()").fetchone()[0] != "WC":
            raise RuntimeError("Solo WC")
        carpeta = cur.execute("SELECT SERVERPROPERTY('InstanceDefaultBackupPath')").fetchone()[0]
        ruta = str(PureWindowsPath(carpeta) / f"WC_pre_cheques_duplicados_{datetime.now():%Y%m%d_%H%M%S}.bak")
        cur.execute("BACKUP DATABASE [WC] TO DISK = ? WITH COPY_ONLY, CHECKSUM", (ruta,))
        while cur.nextset():
            pass
        cur.execute("RESTORE VERIFYONLY FROM DISK = ? WITH CHECKSUM", (ruta,))
        while cur.nextset():
            pass
        print(f"BACKUP_VERIFICADO={ruta}")


def main(apply: bool) -> None:
    filas = _filas()
    print(f"Verificadas {len(filas)} conciliaciones; importe total {sum(f['Importe'] for f in filas):,.2f}")
    if not apply:
        print("Solo verificación. Usar --apply.")
        return
    _backup()
    CARPETA.mkdir(parents=True, exist_ok=True)
    destino = CARPETA / f"conciliaciones_quitadas_{datetime.now():%Y%m%d_%H%M%S}.json"
    destino.write_text(json.dumps(filas, default=str, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Respaldo de filas: {destino}")
    ph = ",".join("?" * len(IDS))
    execute_write_transaction([(f"DELETE FROM dbo.ConciliacionesTesoreria WHERE IdConciliacion IN ({ph}) AND Medio='valores-propios'", tuple(IDS))])
    print("Conciliaciones quitadas.")


if __name__ == "__main__":
    main("--apply" in sys.argv)
