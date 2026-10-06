"""Carga los documentos de Cargill del pago con tarjeta Agronación del 27/04/2023
y corrige las imputaciones de los consumos 5943 y 5944.

Fuente: mails de Cargill (02 y 11/05/2023) y sus PDF en
Documents/La Herencia/Administracion y gestion/Cuentas a pagar/Comprobantes de Pago/Tarjeta AgroNacion.

Cargill canceló con $5.245.929,30 (los dos consumos de la tarjeta):
  fact. 5850-4490 (parte) 135.761,36 + ND 5848-2509 91.399,53
  fact. 5850-5550 (parte) 4.349.919,60 + ND 5848-2510 538.803,05
  fact. 7028-62758 (gastos de tarjeta) 130.045,76

Las ND y la factura no estaban cargadas y las facturas estaban imputadas de más.
Las líneas de las ND (y de la factura de gastos) se reparten con la misma
clasificación (centro, destino, rubro, campaña) que las facturas que ajustan.

Uso: python -m scripts.cargar_cargill_pago_tarjeta_20230427          (solo muestra)
     python -m scripts.cargar_cargill_pago_tarjeta_20230427 --apply  (backup + escribe en WC)
"""
from __future__ import annotations

import shutil
import sys
from datetime import date, datetime
from pathlib import Path, PureWindowsPath

import pyodbc

from src.db.connection import CONNECTION_STRING, execute_write_transaction, fetch_all
from src.features.compras.repository import calcular_totales, create_compra

ID_CONTACTO = 258  # Cargill
FACT_4490, FACT_5550 = 2143513740, 2143514016
LINEA_4490, LINEA_5550 = 5943, 5944
ORIGEN = Path(
    r"C:\Users\Sergio\Documents\La Herencia\Administracion y gestion\Cuentas a pagar"
    r"\Comprobantes de Pago\Tarjeta AgroNacion"
)
DESTINO = Path(r"C:\Users\Sergio\Dropbox\Giamigli de Bolivar SA\Compras\04 2023 - 03 2024")
RUBRO_GASTOS = 2047893491  # el mismo de la factura de intereses 7028-73987

# (nº, fecha, vencimiento, neto, iva%, percepción IVA, total, factura que ajusta, archivo origen, archivo destino)
DOCS = [
    dict(tipo="Nota de Débito", nro="5848-00002509", venc=date(2023, 5, 19), neto=82714.51, iva=10.5, perc=0.0,
         total=91399.53, base=FACT_4490, pdf="30712114602_NDEBITO_584800002509.pdf", dest="20230428_Cargill 001.pdf",
         ajusta=True, producto="DIF.TIPO CAMBIO FACTURA 5850-00004490"),
    dict(tipo="Nota de Débito", nro="5848-00002510", venc=date(2023, 5, 19), neto=487604.57, iva=10.5, perc=0.0,
         total=538803.05, base=FACT_5550, pdf="30712114602_NDEBITO_584800002510.pdf", dest="20230428_Cargill 002.pdf",
         ajusta=True, producto="DIF.TIPO CAMBIO FACTURA 5850-00005550"),
    dict(tipo="Factura", nro="7028-00062758", venc=date(2023, 5, 15), neto=104875.61, iva=21.0, perc=3146.27,
         total=130045.76, base=None, pdf="30712114602_FACTURA_702800062758.pdf", dest="20230428_Cargill 003.pdf",
         ajusta=False, producto="GASTOS ADM. TARJETA DE CREDITO"),
]
# Imputación de los consumos (en pesos): línea -> [(documento, importe)]
GASTOS_L1, GASTOS_L2 = 126969.58, 3076.17


def _lineas_factura(id_compra: int) -> list[dict]:
    return fetch_all(
        "SELECT d.Cantidad AS cant, d.[Precio Unitario] AS pu, d.IdCentroCostos AS cc, d.IdDestino AS dest, "
        "d.IdRubro AS rubro, d.Campaña AS camp, d.Unidad AS unidad, c.[Tipo de Cambio] AS tc "
        "FROM dbo.Det_Compras d JOIN dbo.Compras c ON c.IdDeuda = d.IdCompra WHERE d.IdCompra = ? "
        "ORDER BY d.IdDetalleCompra",
        (id_compra,),
    )


def _lineas_ajuste(doc: dict) -> list[dict]:
    """Líneas del documento con la clasificación de las facturas base."""
    if doc["base"] is not None:
        base = _lineas_factura(doc["base"])
        suma_qty = sum(b["cant"] for b in base)
        pesos = [b["cant"] / suma_qty * doc["neto"] for b in base]
        cantidades = [b["cant"] for b in base]
        precios = [p / q for p, q in zip(pesos, cantidades)]
    else:
        base = _lineas_factura(FACT_4490) + _lineas_factura(FACT_5550)
        peso = [b["cant"] * b["pu"] * b["tc"] for b in base]
        total_peso = sum(peso)
        netos = [round(doc["neto"] * p / total_peso, 2) for p in peso]
        netos[-1] = round(doc["neto"] - sum(netos[:-1]), 2)
        cantidades = [1.0] * len(base)
        precios = netos
    lineas = [
        dict(productoServicio=doc["producto"], cantidad=q, precioUnitario=p, iva=doc["iva"], unidad=b["unidad"],
             idCentroCosto=b["cc"], idDestino=b["dest"],
             idRubro=RUBRO_GASTOS if doc["base"] is None else b["rubro"], campaña=b["camp"])
        for b, q, p in zip(base, cantidades, precios)
    ]
    # El neto debe dar exacto al centavo: lo que sobre o falte lo absorbe la última línea.
    neto = sum(l["cantidad"] * l["precioUnitario"] for l in lineas)
    lineas[-1]["precioUnitario"] += (doc["neto"] - neto) / lineas[-1]["cantidad"]
    return lineas


def _cabecera(doc: dict) -> dict:
    ruta = r"..\..\..\Dropbox\Giamigli de Bolivar SA\Compras\04 2023 - 03 2024" + "\\" + doc["dest"]
    return dict(
        fecha=datetime(2023, 4, 28), idContacto=ID_CONTACTO, tipo="A", tipoDocumento=doc["tipo"],
        numeroDocumento=doc["nro"], moneda="Pesos", tipoDeCambio=1.0, percepcionIva=doc["perc"],
        ajustaTipoCambio=doc["ajusta"], documentoOriginal=f"{ruta}#{ruta}#",
    )


def _verificar() -> list[tuple[dict, dict, list[dict]]]:
    armados = []
    for doc in DOCS:
        cab, lineas = _cabecera(doc), _lineas_ajuste(doc)
        total = round(calcular_totales(lineas, cab)["importeTotal"], 2)
        print(f"{doc['tipo']} {doc['nro']}: {len(lineas)} líneas, total {total:,.2f} (esperado {doc['total']:,.2f})")
        assert abs(total - doc["total"]) < 0.005, f"{doc['nro']}: total {total} != {doc['total']}"
        assert not fetch_all("SELECT 1 FROM dbo.Compras WHERE IdContacto=? AND [Nro Documento]=?", (ID_CONTACTO, doc["nro"]))
        assert (ORIGEN / doc["pdf"]).exists() and not (DESTINO / doc["dest"]).exists()
        armados.append((doc, cab, lineas))
    assert abs(sum(d["total"] for d in DOCS) + 135761.36 + 4349919.60 - 5245929.30) < 0.005
    l1, l2 = (fetch_all("SELECT Importe FROM dbo.Tarjetas_Resumenes_Lineas WHERE IdLineaConsumo=?", (i,))[0]["Importe"]
              for i in (LINEA_4490, LINEA_5550))
    assert abs(l1 - (135761.36 + 91399.53 + GASTOS_L1)) < 0.005 and abs(l2 - (4349919.60 + 538803.05 + GASTOS_L2)) < 0.005
    return armados


def _backup() -> None:
    with pyodbc.connect(CONNECTION_STRING, autocommit=True) as conn:
        cur = conn.cursor()
        if cur.execute("SELECT DB_NAME()").fetchone()[0] != "WC":
            raise RuntimeError("Solo WC")
        carpeta = cur.execute("SELECT SERVERPROPERTY('InstanceDefaultBackupPath')").fetchone()[0]
        ruta = str(PureWindowsPath(carpeta) / f"WC_pre_cargill_20230427_{datetime.now():%Y%m%d_%H%M%S}.bak")
        cur.execute("BACKUP DATABASE [WC] TO DISK = ? WITH COPY_ONLY, CHECKSUM", (ruta,))
        while cur.nextset():
            pass
        cur.execute("RESTORE VERIFYONLY FROM DISK = ? WITH CHECKSUM", (ruta,))
        while cur.nextset():
            pass
        print(f"BACKUP_VERIFICADO={ruta}")


def main(apply: bool) -> None:
    armados = _verificar()
    if not apply:
        print("Solo verificación: no se escribió nada. Usar --apply.")
        return
    _backup()
    ids = {}
    for doc, cab, lineas in armados:
        ids[doc["nro"]] = create_compra(cab, lineas, [{"fechaVencimiento": datetime.combine(doc["venc"], datetime.min.time())}])
        shutil.copy2(ORIGEN / doc["pdf"], DESTINO / doc["dest"])
        print(f"Cargado {doc['nro']} -> IdDeuda {ids[doc['nro']]}")
    nd1, nd2, fg = (ids[d["nro"]] for d in DOCS)
    imputaciones = [
        (LINEA_4490, FACT_4490, 135761.36), (LINEA_4490, nd1, 91399.53), (LINEA_4490, fg, GASTOS_L1),
        (LINEA_5550, FACT_5550, 4349919.60), (LINEA_5550, nd2, 538803.05), (LINEA_5550, fg, GASTOS_L2),
    ]
    statements = [("DELETE FROM dbo.Tarjetas_Resumenes_Lineas_Compras WHERE IdLineaConsumo IN (?, ?)", (LINEA_4490, LINEA_5550))]
    statements += [
        ("INSERT INTO dbo.Tarjetas_Resumenes_Lineas_Compras (IdLineaConsumo, IdCompra, ImporteImputado) VALUES (?, ?, ?)", i)
        for i in imputaciones
    ]
    execute_write_transaction(statements)
    print("Imputaciones corregidas.")


if __name__ == "__main__":
    main("--apply" in sys.argv)
