"""Agronación: cierre de Nación Seguros (líneas 5869/5870) y FEDEA (5879/5880).

Nación Seguros: la tarjeta registró la póliza como 27651 pero los documentos cargados son 27650
(factura 27650-2 por $167,30 y NC 27650-3 por -$144,07, mismos importes): se vinculan.
FEDEA: las ND 2291 y 2364 ya están imputadas; la tarjeta cobró $5,91 y $1,43 más (mismo
0,044% en las dos): redondeo, se aceptan con su explicación.

Uso: python -m scripts.cerrar_seguros_fedea_agronacion [--apply]
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import PureWindowsPath

import pyodbc

from src.db.connection import CONNECTION_STRING, execute_write_transaction, fetch_all

VINCULOS = [(5869, 2143511163, 167.30, "27650 2"), (5870, 2143511164, -144.07, "27650 3")]
DIFERENCIAS = [(5879, 5.91), (5880, 1.43)]
DETALLE_FEDEA = ("La tarjeta cobró %s más que la ND (mismo 0,044%% en las dos notas de enero de 2018): "
                 "redondeo de tipo de cambio o recargo mínimo; sin documento faltante.")


def _verificar() -> None:
    for linea, doc, imp, nro in VINCULOS:
        l = fetch_all("SELECT Importe i, IdContacto c FROM dbo.Tarjetas_Resumenes_Lineas WHERE IdLineaConsumo=?", (linea,))[0]
        d = fetch_all("SELECT [Nro Documento] n, IdContacto c FROM dbo.Compras WHERE IdDeuda=?", (doc,))[0]
        assert abs(l["i"] - imp) < 0.005 and l["c"] == 289 and d["n"] == nro and d["c"] == 289, (linea, l, d)
        assert not fetch_all("SELECT 1 FROM dbo.Tarjetas_Resumenes_Lineas_Compras WHERE IdLineaConsumo=? OR IdCompra=?", (linea, doc))
    for linea, dif in DIFERENCIAS:
        r = fetch_all("SELECT l.Importe - ISNULL((SELECT SUM(v.ImporteImputado) FROM dbo.Tarjetas_Resumenes_Lineas_Compras v "
                      "WHERE v.IdLineaConsumo=l.IdLineaConsumo),0) AS resto, l.IdContacto c FROM dbo.Tarjetas_Resumenes_Lineas l "
                      "WHERE l.IdLineaConsumo=?", (linea,))[0]
        assert r["c"] == 217 and abs(r["resto"] - dif) < 0.005, (linea, r)
        assert not fetch_all("SELECT 1 FROM dbo.Tarjetas_Resumenes_Lineas_Estado WHERE IdLineaConsumo=?", (linea,))
    print("Verificado: 2 vínculos de Nación Seguros y 2 diferencias de FEDEA.")


def _backup() -> None:
    with pyodbc.connect(CONNECTION_STRING, autocommit=True) as conn:
        cur = conn.cursor()
        if cur.execute("SELECT DB_NAME()").fetchone()[0] != "WC":
            raise RuntimeError("Solo WC")
        carpeta = cur.execute("SELECT SERVERPROPERTY('InstanceDefaultBackupPath')").fetchone()[0]
        ruta = str(PureWindowsPath(carpeta) / f"WC_pre_seguros_fedea_{datetime.now():%Y%m%d_%H%M%S}.bak")
        cur.execute("BACKUP DATABASE [WC] TO DISK = ? WITH COPY_ONLY, CHECKSUM", (ruta,))
        while cur.nextset():
            pass
        cur.execute("RESTORE VERIFYONLY FROM DISK = ? WITH CHECKSUM", (ruta,))
        while cur.nextset():
            pass
        print(f"BACKUP_VERIFICADO={ruta}")


def main(apply: bool) -> None:
    _verificar()
    if not apply:
        print("Solo verificación. Usar --apply.")
        return
    _backup()
    st = [("INSERT INTO dbo.Tarjetas_Resumenes_Lineas_Compras (IdLineaConsumo, IdCompra, ImporteImputado) VALUES (?, ?, ?)",
           (l, d, i)) for l, d, i, _ in VINCULOS]
    st += [("INSERT INTO dbo.Tarjetas_Resumenes_Lineas_Estado (IdLineaConsumo, Estado, Motivo, Detalle, ImporteDiferencia) "
            "VALUES (?, 'DiferenciaAceptada', 'Redondeo', ?, ?)", (l, DETALLE_FEDEA % f"${dif:.2f}".replace(".", ","), dif))
           for l, dif in DIFERENCIAS]
    execute_write_transaction(st)
    print("Nación Seguros y FEDEA cerrados.")


if __name__ == "__main__":
    main("--apply" in sys.argv)
