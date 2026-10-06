"""ASP, plan de tarjeta Agronación del 17/07/2013 (recibo ASP 806954, $21.622,03).

Según el estado de cuenta de ASP en dólares, ese recibo canceló todo el saldo abierto
(US$4.131,86): resto de la factura 0392-71 (US$1.021,05), facturas 296 (US$1.559,98) y 297
(US$1.301,84) y la ND 549 de intereses (US$248,99). En la tarjeta quedó como 12 cuotas de
$1.693,25 (resúmenes 582 a 593, suman $20.319) más un pago único de $1.303 (resumen 593).
Las 12 cuotas se reparten entre 71/296/297 en proporción a los dólares cancelados; el pago
único corresponde a la ND 549. Reemplaza el reparto anterior de las líneas 804, 5846 y 750.

Uso: python -m scripts.reimputar_asp_plan_20130717 [--apply]
"""
from __future__ import annotations

import sys
from datetime import datetime
from decimal import ROUND_FLOOR, Decimal
from pathlib import PureWindowsPath

import pyodbc

from src.db.connection import CONNECTION_STRING, execute_write_transaction, fetch_all

CUOTAS = [804, 812, 816, 750, 5846, 853, 859, 865, 907, 914, 922, 930]  # cuotas 1..12 (res 582..593)
PAGO_UNICO = 931
IMPORTE_CUOTA = Decimal("1693.25")
DOCS = {  # IdCompra -> (nro, US$ cancelados por el plan de 12 cuotas)
    2143509715: ("0392-00000071", Decimal("1021.05")),
    2143509744: ("0392-00000296", Decimal("1559.98")),
    2143509745: ("0392-00000297", Decimal("1301.84")),
}
ND549 = 2143509794


def _repartir(total: Decimal, pesos: dict[int, Decimal]) -> dict[int, Decimal]:
    suma = sum(pesos.values())
    crudo = {k: total * v / suma for k, v in pesos.items()}
    base = {k: x.quantize(Decimal("0.01"), rounding=ROUND_FLOOR) for k, x in crudo.items()}
    faltan = int((total - sum(base.values())) * 100)
    for k in sorted(crudo, key=lambda k: crudo[k] - base[k], reverse=True)[:faltan]:
        base[k] += Decimal("0.01")
    assert sum(base.values()) == total
    return base


def _plan() -> list[tuple[int, int, Decimal]]:
    por_cuota = _repartir(IMPORTE_CUOTA, {k: v[1] for k, v in DOCS.items()})
    filas = [(linea, doc, imp) for linea in CUOTAS for doc, imp in por_cuota.items()]
    filas.append((PAGO_UNICO, ND549, Decimal("1303.00")))
    return filas


def _verificar() -> list[tuple[int, int, Decimal]]:
    for i, (nro, _) in {**DOCS, ND549: ("0392-00000549", 0)}.items():
        assert fetch_all("SELECT 1 FROM dbo.Compras WHERE IdDeuda=? AND [Nro Documento]=? AND IdContacto=17", (i, nro)), nro
    ph = ",".join("?" * (len(CUOTAS) + 1))
    for x in fetch_all(f"SELECT IdLineaConsumo i, Importe m FROM dbo.Tarjetas_Resumenes_Lineas WHERE IdLineaConsumo IN ({ph})", (*CUOTAS, PAGO_UNICO)):
        esperado = Decimal("1303.00") if x["i"] == PAGO_UNICO else IMPORTE_CUOTA
        assert abs(Decimal(str(x["m"])) - esperado) < Decimal("0.005"), x
    ids = ",".join("?" * len(DOCS) + "?")
    ajenos = fetch_all(f"SELECT IdLineaConsumo FROM dbo.Tarjetas_Resumenes_Lineas_Compras WHERE IdCompra IN ({ids}) "
                       f"AND IdLineaConsumo NOT IN ({ph})", (*DOCS, ND549, *CUOTAS, PAGO_UNICO))
    assert not ajenos, f"Los documentos tienen otros vínculos: {ajenos}"
    filas = _plan()
    for doc in (*DOCS, ND549):
        print(fetch_all("SELECT [Nro Documento] n FROM dbo.Compras WHERE IdDeuda=?", (doc,))[0]["n"],
              "total imputado", sum(i for _, d, i in filas if d == doc))
    return filas


def _backup() -> None:
    with pyodbc.connect(CONNECTION_STRING, autocommit=True) as conn:
        cur = conn.cursor()
        if cur.execute("SELECT DB_NAME()").fetchone()[0] != "WC":
            raise RuntimeError("Solo WC")
        carpeta = cur.execute("SELECT SERVERPROPERTY('InstanceDefaultBackupPath')").fetchone()[0]
        ruta = str(PureWindowsPath(carpeta) / f"WC_pre_asp_plan1_{datetime.now():%Y%m%d_%H%M%S}.bak")
        cur.execute("BACKUP DATABASE [WC] TO DISK = ? WITH COPY_ONLY, CHECKSUM", (ruta,))
        while cur.nextset():
            pass
        cur.execute("RESTORE VERIFYONLY FROM DISK = ? WITH CHECKSUM", (ruta,))
        while cur.nextset():
            pass
        print(f"BACKUP_VERIFICADO={ruta}")


def main(apply: bool) -> None:
    filas = _verificar()
    if not apply:
        print("Solo verificación. Usar --apply.")
        return
    _backup()
    ph = ",".join("?" * (len(CUOTAS) + 1))
    st = [(f"DELETE FROM dbo.Tarjetas_Resumenes_Lineas_Compras WHERE IdLineaConsumo IN ({ph})", (*CUOTAS, PAGO_UNICO))]
    st += [("INSERT INTO dbo.Tarjetas_Resumenes_Lineas_Compras (IdLineaConsumo, IdCompra, ImporteImputado) VALUES (?, ?, ?)",
            (l, d, float(i))) for l, d, i in filas]
    execute_write_transaction(st)
    print("Plan de ASP reimputado.")


if __name__ == "__main__":
    main("--apply" in sys.argv)
