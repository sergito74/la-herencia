"""ASP: completa los restos de las cuotas de tarjeta con los documentos libres de cada plan.

Cada plan se paga con un recibo de ASP (estado de cuenta en Resumenes de Cuenta/ASP) que
canceló un conjunto de facturas y notas; las cuotas se aplican en orden (FIFO) y la última
quedó sin documento porque el anterior ya estaba agotado. Se usan solo capacidades libres.
  - Recibo 831007 (oct-2013): fact. 1428, 1433, 1478 y ND 740 -> líneas 940 y 946.
  - Recibo 920744 (oct-2014): fact. 4050, 4045 y ND 1772 -> línea 1017 (fact. 4045).
  - Recibo 968040 (2015): fact. 6353/6354 y ND 2146/2148/2149 -> línea 1021 (ND 2146 y fact. 6354).

Uso: python -m scripts.completar_asp_restos_20261006 [--apply]
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import PureWindowsPath

import pyodbc

from src.db.connection import CONNECTION_STRING, execute_write_transaction, fetch_all

D = {"1433": 2143509854, "1478": 2143509856, "740": 2143509870, "4045": 2143510161, "2146": 2143510331, "6354": 2143510332}
IMPUTACIONES = [
    (940, D["1433"], 117.89),
    (946, D["1433"], 648.54), (946, D["1478"], 350.35), (946, D["740"], 489.54),
    (1017, D["4045"], 826.20),
    (1021, D["2146"], 189.88), (1021, D["6354"], 137.45),
]
RESTO_ESPERADO = {940: 117.89, 946: 1488.43, 1017: 826.34, 1021: 327.33}


def _verificar() -> None:
    for linea, esperado in RESTO_ESPERADO.items():
        r = fetch_all("SELECT l.Importe - ISNULL((SELECT SUM(v.ImporteImputado) FROM dbo.Tarjetas_Resumenes_Lineas_Compras v "
                      "WHERE v.IdLineaConsumo=l.IdLineaConsumo),0) AS resto, l.IdContacto c FROM dbo.Tarjetas_Resumenes_Lineas l "
                      "WHERE l.IdLineaConsumo=?", (linea,))[0]
        assert r["c"] == 17 and abs(r["resto"] - esperado) < 0.005, (linea, r)
        print(f"Línea {linea}: resto {r['resto']:.2f}, se imputa {sum(i for l, _, i in IMPUTACIONES if l == linea):.2f}")
    for doc in D.values():
        assert fetch_all("SELECT 1 FROM dbo.Compras WHERE IdDeuda=? AND IdContacto=17", (doc,))


def _backup() -> None:
    with pyodbc.connect(CONNECTION_STRING, autocommit=True) as conn:
        cur = conn.cursor()
        if cur.execute("SELECT DB_NAME()").fetchone()[0] != "WC":
            raise RuntimeError("Solo WC")
        carpeta = cur.execute("SELECT SERVERPROPERTY('InstanceDefaultBackupPath')").fetchone()[0]
        ruta = str(PureWindowsPath(carpeta) / f"WC_pre_asp_restos_{datetime.now():%Y%m%d_%H%M%S}.bak")
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
    execute_write_transaction([
        ("INSERT INTO dbo.Tarjetas_Resumenes_Lineas_Compras (IdLineaConsumo, IdCompra, ImporteImputado) VALUES (?, ?, ?)", i)
        for i in IMPUTACIONES
    ])
    print("Restos de ASP completados.")


if __name__ == "__main__":
    main("--apply" in sys.argv)
