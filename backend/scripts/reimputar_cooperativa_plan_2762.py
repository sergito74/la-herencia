"""Cooperativa Agropecuaria, operación 2762 (12 cuotas, ago-2013 a jul-2014, $26.791,90).

Cuenta corriente en papel (Resumenes de Cuenta/Cooperativa Agropecuaria/Resumenes de cuenta
completo.pdf, resumen al 22/10/13): el recibo 74501 del 31/07/2013 "s/ent AgroNacion" por
$26.791,90 cancelo todo el saldo abierto hasta el 24/07/2013 ($24.152,32) y, con el excedente
($2.639,58), las facturas del 31/07/2013 en orden; de la ND 7015 solo $1.576,94 (los otros
$1.801,26 los pago la transferencia del 01/08/2013).
Cambios: la ND 7015 baja de $3.378,20 a $1.576,94 imputados; las cuotas sin documento se
reparten en orden entre fact. 1605 (resto $178,41), 60975 ($172,39) y 2436 ($18.946,66).

Uso: python -m scripts.reimputar_cooperativa_plan_2762 [--apply]
"""
from __future__ import annotations

import sys
from datetime import datetime
from decimal import Decimal
from pathlib import PureWindowsPath

import pyodbc

from src.db.connection import CONNECTION_STRING, execute_write_transaction, fetch_all

CUOTAS = [805, 813, 817, 751, 5847, 854, 860, 866, 908, 915, 923, 932]  # cuotas 1..12
ND7015 = 2143509842
ND7015_NUEVO = {817: Decimal("1576.94"), 854: None}  # None = se elimina el vínculo
COLA = [(2143509749, "0015-00001605", Decimal("178.41")),
        (2143509714, "0019-00060975", Decimal("172.39")),
        (2143509785, "0015-00002436", Decimal("18946.66"))]


def _restos() -> dict[int, Decimal]:
    restos = {}
    for l in CUOTAS:
        r = fetch_all("SELECT l.Importe i, l.IdContacto c, ISNULL((SELECT SUM(v.ImporteImputado) FROM dbo.Tarjetas_Resumenes_Lineas_Compras v "
                      "WHERE v.IdLineaConsumo=l.IdLineaConsumo),0) s FROM dbo.Tarjetas_Resumenes_Lineas l WHERE l.IdLineaConsumo=?", (l,))[0]
        assert r["c"] == 22
        restos[l] = Decimal(str(r["i"])) - Decimal(str(r["s"]))
    # efecto de reducir la ND 7015
    for l, nuevo in ND7015_NUEVO.items():
        actual = Decimal(str(fetch_all("SELECT ImporteImputado i FROM dbo.Tarjetas_Resumenes_Lineas_Compras WHERE IdLineaConsumo=? AND IdCompra=?",
                                       (l, ND7015))[0]["i"]))
        restos[l] += actual - (nuevo or Decimal(0))
    return {l: r.quantize(Decimal("0.01")) for l, r in restos.items()}


def _asignaciones() -> list[tuple[int, int, Decimal]]:
    restos, cola, filas = _restos(), [list(c) for c in COLA], []
    for l in CUOTAS:
        falta = restos[l]
        while falta > 0 and cola:
            doc = cola[0]
            pedazo = min(falta, doc[2])
            filas.append((l, doc[0], pedazo))
            falta -= pedazo
            doc[2] -= pedazo
            if doc[2] <= 0:
                cola.pop(0)
        restos[l] = falta
    print("Resto final por línea:", {l: str(r) for l, r in restos.items() if r})
    return filas


def _verificar() -> list[tuple[int, int, Decimal]]:
    for doc, nro, _ in COLA:
        assert fetch_all("SELECT 1 FROM dbo.Compras WHERE IdDeuda=? AND [Nro Documento]=? AND IdContacto=22", (doc, nro)), nro
        assert not fetch_all("SELECT 1 FROM dbo.Tarjetas_Resumenes_Lineas_Compras WHERE IdCompra=?", (doc,)), f"{nro} ya vinculado"
    assert abs(sum(Decimal(str(x["Importe"])) for x in fetch_all(
        f"SELECT Importe FROM dbo.Tarjetas_Resumenes_Lineas WHERE IdLineaConsumo IN ({','.join('?' * len(CUOTAS))})", tuple(CUOTAS))) - Decimal("26791.90")) < Decimal("0.005")
    filas = _asignaciones()
    por_doc = {}
    for _, d, i in filas:
        por_doc[d] = por_doc.get(d, Decimal(0)) + i
    for doc, nro, total in COLA:
        print(f"{nro}: se imputan {por_doc.get(doc, Decimal(0))} de {total}")
    return filas


def _backup() -> None:
    with pyodbc.connect(CONNECTION_STRING, autocommit=True) as conn:
        cur = conn.cursor()
        if cur.execute("SELECT DB_NAME()").fetchone()[0] != "WC":
            raise RuntimeError("Solo WC")
        carpeta = cur.execute("SELECT SERVERPROPERTY('InstanceDefaultBackupPath')").fetchone()[0]
        ruta = str(PureWindowsPath(carpeta) / f"WC_pre_coop_2762_{datetime.now():%Y%m%d_%H%M%S}.bak")
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
    st = []
    for l, nuevo in ND7015_NUEVO.items():
        if nuevo is None:
            st.append(("DELETE FROM dbo.Tarjetas_Resumenes_Lineas_Compras WHERE IdLineaConsumo=? AND IdCompra=?", (l, ND7015)))
        else:
            st.append(("UPDATE dbo.Tarjetas_Resumenes_Lineas_Compras SET ImporteImputado=? WHERE IdLineaConsumo=? AND IdCompra=?",
                       (float(nuevo), l, ND7015)))
    st += [("INSERT INTO dbo.Tarjetas_Resumenes_Lineas_Compras (IdLineaConsumo, IdCompra, ImporteImputado) VALUES (?, ?, ?)",
            (l, d, float(i))) for l, d, i in filas]
    execute_write_transaction(st)
    print("Operación 2762 reimputada.")


if __name__ == "__main__":
    main("--apply" in sys.argv)
