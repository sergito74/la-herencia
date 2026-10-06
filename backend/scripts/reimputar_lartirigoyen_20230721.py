"""Lartirigoyen, pagos con tarjeta Agronación del 21 y 25/07/2023 (líneas 5861 y 5862).

Según las aplicaciones de cuenta corriente de Lartirigoyen (AP 0149-7885/7886/7887/7888/7896),
cada cupón se aplicó así:
  cupón 21/07 ($1.452.985,92): fact. 11970 neta de retención 1.381.957,48 + ND 5211 (intereses) 47.613,50
      + ND 5212 126,47 y 5213 9.360,90 (dif. de cambio) + fact. 11992 13.927,57 (sobrante).
  cupón 25/07 ($1.478.941,05): fact. 11992 1.415.812,54 + ND 5216 (intereses) 48.349,18
      + ND 5219 (dif. de cambio) 14.663,97 = 1.478.825,69; los $115,36 restantes no se aplicaron:
      quedan como saldo a favor en la cuenta de Lartirigoyen.

Uso: python -m scripts.reimputar_lartirigoyen_20230721 [--apply]
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import PureWindowsPath

import pyodbc

from src.db.connection import CONNECTION_STRING, execute_write_transaction, fetch_all

L1, L2 = 5861, 5862
F11970, F11992 = 2143514186, 2143514187
ND5211, ND5212, ND5213, ND5216, ND5219 = 2143514213, 2143514188, 2143514189, 2143514194, 2143514196
ESPERADO = {
    F11970: "0149 - 00011970", F11992: "0149 - 00011992", ND5211: "0149 - 00005211",
    ND5212: "0149- 00005212", ND5213: "0149- 00005213", ND5216: "0149 - 00005216", ND5219: "0149 - 00005219",
}
IMPUTACIONES = [
    (L1, F11970, 1381957.48), (L1, ND5211, 47613.50), (L1, ND5212, 126.47), (L1, ND5213, 9360.90), (L1, F11992, 13927.57),
    (L2, F11992, 1415812.54), (L2, ND5216, 48349.18), (L2, ND5219, 14663.97),
]
RELACIONES = [(F11970, ND5212), (F11970, ND5213), (F11992, ND5219)]  # ND de diferencia de cambio -> su factura
DETALLE = ("Saldo a favor que Lartirigoyen no aplicó: cupón RD 0007-00003763 ($1.478.941,05) vs aplicado "
           "$1.478.825,69 en AP 0149-00007896 (25/07/2023). Queda como crédito en su cuenta.")


def _verificar() -> None:
    for i, nro in ESPERADO.items():
        fila = fetch_all("SELECT [Nro Documento] n, IdContacto c FROM dbo.Compras WHERE IdDeuda=?", (i,))
        assert fila and fila[0]["n"] == nro and fila[0]["c"] == 61, f"Documento inesperado {i}: {fila}"
    for linea, esperado in ((L1, 1452985.92), (L2, 1478941.05)):
        imp = fetch_all("SELECT Importe FROM dbo.Tarjetas_Resumenes_Lineas WHERE IdLineaConsumo=?", (linea,))[0]["Importe"]
        assert abs(imp - esperado) < 0.005, f"Línea {linea}: {imp}"
        suma = sum(x[2] for x in IMPUTACIONES if x[0] == linea)
        print(f"Línea {linea}: importe {imp:,.2f}, imputado {suma:,.2f}, resto {imp - suma:,.2f}")
    ocupados = fetch_all(
        "SELECT IdCompra FROM dbo.Tarjetas_Resumenes_Lineas_Compras WHERE IdCompra IN (%s) AND IdLineaConsumo NOT IN (?, ?)"
        % ",".join("?" * len(ESPERADO)), (*ESPERADO, L1, L2))
    assert not ocupados, f"Hay documentos ya vinculados a otras líneas: {ocupados}"
    assert abs(sum(x[2] for x in IMPUTACIONES if x[0] == L2) + 115.36 - 1478941.05) < 0.005


def _backup() -> None:
    with pyodbc.connect(CONNECTION_STRING, autocommit=True) as conn:
        cur = conn.cursor()
        if cur.execute("SELECT DB_NAME()").fetchone()[0] != "WC":
            raise RuntimeError("Solo WC")
        carpeta = cur.execute("SELECT SERVERPROPERTY('InstanceDefaultBackupPath')").fetchone()[0]
        ruta = str(PureWindowsPath(carpeta) / f"WC_pre_lartirigoyen_{datetime.now():%Y%m%d_%H%M%S}.bak")
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
    st = [("DELETE FROM dbo.Tarjetas_Resumenes_Lineas_Compras WHERE IdLineaConsumo IN (?, ?)", (L1, L2)),
          ("DELETE FROM dbo.Tarjetas_Resumenes_Lineas_Estado WHERE IdLineaConsumo IN (?, ?)", (L1, L2))]
    st += [("INSERT INTO dbo.Tarjetas_Resumenes_Lineas_Compras (IdLineaConsumo, IdCompra, ImporteImputado) VALUES (?, ?, ?)", i)
           for i in IMPUTACIONES]
    st.append(("INSERT INTO dbo.Tarjetas_Resumenes_Lineas_Estado (IdLineaConsumo, Estado, Motivo, Detalle, ImporteDiferencia) "
               "VALUES (?, 'DiferenciaAceptada', 'Otro', ?, 115.36)", (L2, DETALLE)))
    for f, a in RELACIONES:
        st.append(("INSERT INTO dbo.CompraDocumentosRelacionados (IdCompra, IdCompraRelacionada, CreatedAt) "
                   "SELECT ?, ?, GETDATE() WHERE NOT EXISTS (SELECT 1 FROM dbo.CompraDocumentosRelacionados "
                   "WHERE (IdCompra = ? AND IdCompraRelacionada = ?) OR (IdCompra = ? AND IdCompraRelacionada = ?))",
                   (f, a, f, a, a, f)))
    execute_write_transaction(st)
    print("Reimputación aplicada.")


if __name__ == "__main__":
    main("--apply" in sys.argv)
