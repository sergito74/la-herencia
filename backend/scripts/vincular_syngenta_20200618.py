"""Línea 5915 (tarjeta Agronación, 18/06/2020, $54.764,30): consumo en Syngenta.

La factura 0272-00067088 (11/06/2020, US$785,90 a TC 69,26 = $54.431,43) ya estaba cargada,
pero la línea apuntaba a un contacto inexistente (410) y por eso nunca la encontraba.
El contacto correcto es Syngenta Semillas (398, CUIT 30-64632845-0 como en la factura).
Se imputa el valor de la factura y la diferencia ($332,87) se registra como diferencia
de tipo de cambio: la tarjeta cobró a ~69,68 (cupón 910712 del 18/06/2020) y la factura es a 69,26.

Uso: python -m scripts.vincular_syngenta_20200618 [--apply]
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import PureWindowsPath

import pyodbc

from src.db.connection import CONNECTION_STRING, execute_write_transaction, fetch_all

LINEA, COMPRA, CONTACTO = 5915, 2143512775, 398
IMPORTE_DOC, DIFERENCIA = 54431.43, 332.87
DETALLE = ("Cupón 910712 del 18/06/2020 por $54.764,30 (TC implícito 69,68) vs factura 0272-00067088 en USD 785,90 "
           "a TC 69,26 ($54.431,43): diferencia de cambio sin nota.")


def _backup() -> None:
    with pyodbc.connect(CONNECTION_STRING, autocommit=True) as conn:
        cur = conn.cursor()
        if cur.execute("SELECT DB_NAME()").fetchone()[0] != "WC":
            raise RuntimeError("Solo WC")
        carpeta = cur.execute("SELECT SERVERPROPERTY('InstanceDefaultBackupPath')").fetchone()[0]
        ruta = str(PureWindowsPath(carpeta) / f"WC_pre_syngenta_{datetime.now():%Y%m%d_%H%M%S}.bak")
        cur.execute("BACKUP DATABASE [WC] TO DISK = ? WITH COPY_ONLY, CHECKSUM", (ruta,))
        while cur.nextset():
            pass
        cur.execute("RESTORE VERIFYONLY FROM DISK = ? WITH CHECKSUM", (ruta,))
        while cur.nextset():
            pass
        print(f"BACKUP_VERIFICADO={ruta}")


def main(apply: bool) -> None:
    linea = fetch_all("SELECT IdContacto c, Importe i, NroDocumento n FROM dbo.Tarjetas_Resumenes_Lineas WHERE IdLineaConsumo=?", (LINEA,))[0]
    assert linea["c"] == 410 and abs(linea["i"] - 54764.30) < 0.005 and linea["n"] == "0272-00067088", linea
    assert not fetch_all("SELECT 1 FROM dbo.Contactos WHERE IdContacto=410")
    doc = fetch_all("SELECT IdContacto c, [Nro Documento] n FROM dbo.Compras WHERE IdDeuda=?", (COMPRA,))[0]
    assert doc["c"] == CONTACTO and doc["n"] == "0272-00067088", doc
    assert not fetch_all("SELECT 1 FROM dbo.Tarjetas_Resumenes_Lineas_Compras WHERE IdLineaConsumo=? OR IdCompra=?", (LINEA, COMPRA))
    print(f"Imputar {IMPORTE_DOC:,.2f} y aceptar diferencia {DIFERENCIA:,.2f} (total {IMPORTE_DOC + DIFERENCIA:,.2f})")
    if not apply:
        print("Solo verificación. Usar --apply.")
        return
    _backup()
    execute_write_transaction([
        ("UPDATE dbo.Tarjetas_Resumenes_Lineas SET IdContacto=?, Detalle='Syngenta' WHERE IdLineaConsumo=? AND IdContacto=410", (CONTACTO, LINEA)),
        ("INSERT INTO dbo.Tarjetas_Resumenes_Lineas_Compras (IdLineaConsumo, IdCompra, ImporteImputado) VALUES (?, ?, ?)", (LINEA, COMPRA, IMPORTE_DOC)),
        ("INSERT INTO dbo.Tarjetas_Resumenes_Lineas_Estado (IdLineaConsumo, Estado, Motivo, Detalle, ImporteDiferencia) "
         "VALUES (?, 'DiferenciaAceptada', 'AjusteTipoCambioSinNota', ?, ?)", (LINEA, DETALLE, DIFERENCIA)),
    ])
    print("Línea 5915 vinculada.")


if __name__ == "__main__":
    main("--apply" in sys.argv)
