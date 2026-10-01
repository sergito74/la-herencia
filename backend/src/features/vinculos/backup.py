"""Backup verificado de WC antes de escribir (constitución II). Mismo
procedimiento que los scripts de migración: `COPY_ONLY, CHECKSUM` en el
directorio de backup de la instancia y `RESTORE VERIFYONLY`. Si algo
falla, lanza: el llamador no debe escribir."""

from __future__ import annotations

from datetime import datetime
from pathlib import PureWindowsPath

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc


def backup_verificado(etiqueta: str) -> str:
    _assert_target_is_wc()
    with pyodbc.connect(CONNECTION_STRING, autocommit=True) as conn:
        cursor = conn.cursor()
        if cursor.execute("SELECT DB_NAME()").fetchone()[0] != "WC":
            raise RuntimeError("El backup de 031 solo se toma sobre WC")
        directorio = cursor.execute("SELECT SERVERPROPERTY('InstanceDefaultBackupPath')").fetchone()[0]
        if not directorio:
            raise RuntimeError("La instancia no tiene directorio de backup")
        ruta = str(PureWindowsPath(directorio) / f"WC_{etiqueta}_{datetime.now():%Y%m%d_%H%M%S_%f}.bak")
        cursor.execute("BACKUP DATABASE [WC] TO DISK = ? WITH COPY_ONLY, CHECKSUM", (ruta,))
        while cursor.nextset():
            pass
        cursor.execute("RESTORE VERIFYONLY FROM DISK = ? WITH CHECKSUM", (ruta,))
        while cursor.nextset():
            pass
    return ruta
