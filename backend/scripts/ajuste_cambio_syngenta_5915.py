"""Línea 5915 (Agronación, Syngenta): cierra los $332,87 de diferencia de cambio con una Nota de Débito
"SIN DOCUMENTO" en la cuenta de Syngenta (contacto 398), clasificada como la factura 0272-00067088
(15/10/5 litros de Dividend Extra en tres campañas). La línea se vincula a la ND, queda relacionada con
la factura y se retira el estado 'DiferenciaAceptada' (ya no hay diferencia).

Uso (desde backend/): python -m scripts.ajuste_cambio_syngenta_5915 [--apply]
"""

from __future__ import annotations

import sys
from datetime import datetime

from src.db.connection import execute_write_transaction, fetch_all
from src.features.vinculos.backup import backup_verificado

LINEA, FACTURA, CONTACTO = 5915, 2143512775, 398
IMPORTE = 332.87
IVA = 21.0
NETO = round(IMPORTE / (1 + IVA / 100), 2)  # 275,10 -> con IVA 332,87
FECHA = datetime(2020, 6, 18)


def main(apply: bool) -> None:
    # REEMPLAZADO el 2026-10-08: con los mails de SUNANCO se comprobó que Syngenta emitió la ND real 0272-00025845 ($675,39) que
    # incluye estos $332,87. La ND "SIN DOCUMENTO" se eliminó y el pago de tarjeta de $332,87 quedó vinculado a esa ND real.
    # No volver a correr este script: re-crearía la ND duplicada.
    print("Script reemplazado: la ND real 0272-00025845 de Syngenta ya recibe este pago. No se hace nada.")
    return
    if fetch_all("SELECT 1 AS x FROM dbo.Compras WHERE IdContacto = ? AND [Nro Documento] = 'SIN DOCUMENTO' AND Fecha = ? "
                 "AND [Ajusta Tipo Cambio] = 1", (CONTACTO, FECHA)):
        print("La nota de ajuste ya existe: no se hace nada.")
        return
    lineas_factura = fetch_all(
        "SELECT Cantidad, IdCentroCostos, IdDestino, IdRubro, IdCampaña, [Campaña] AS camp, [Producto/Servicio] AS prod "
        "FROM dbo.Det_Compras WHERE IdCompra = ?", (FACTURA,))
    total_cant = sum(float(l["Cantidad"]) for l in lineas_factura)
    partes = [round(NETO * float(l["Cantidad"]) / total_cant, 2) for l in lineas_factura]
    partes[-1] = round(NETO - sum(partes[:-1]), 2)
    print(f"ND de {IMPORTE:,.2f} (neto {NETO:,.2f} + IVA {IVA}%) repartida en {len(partes)} líneas: {partes}")
    if not apply:
        print("Solo verificación. Usar --apply.")
        return
    print(f"Respaldo verificado: {backup_verificado('ajuste-cambio-syngenta-5915')}")

    def cabecera(_r):
        return ("INSERT INTO dbo.Compras (Fecha, IdContacto, Tipo, [Tipo documento], [Nro Documento], Moneda, [Tipo de Cambio], "
                "[Ingresos Brutos], PercepcionIVA, [Conceptos no gravados], Guias, Comision, Financiacion, [Gastos Varios], "
                "[Ley de Sellos], [Res gral 4169/96], [Ajusta Tipo Cambio]) OUTPUT INSERTED.IdDeuda "
                "VALUES (?, ?, 'A', 'Nota de Débito', 'SIN DOCUMENTO', 'Pesos', 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1)", (FECHA, CONTACTO))

    def detalle(l, neto):
        def build(r):
            return ("INSERT INTO dbo.Det_Compras (IdCompra, Cantidad, [Producto/Servicio], IdCentroCostos, IdDestino, IdRubro, "
                    "IdCampaña, [Campaña], [Precio Unitario], IVA, [Ajuste financiero]) VALUES (?, 1, ?, ?, ?, ?, ?, ?, ?, ?, 0)",
                    (r[0], "Diferencia de cambio " + (l["prod"] or ""), l["IdCentroCostos"], l["IdDestino"], l["IdRubro"],
                     l["IdCampaña"], l["camp"], neto, IVA))
        return build

    sentencias = [cabecera] + [detalle(l, n) for l, n in zip(lineas_factura, partes)] + [
        lambda r: ("INSERT INTO dbo.Tarjetas_Resumenes_Lineas_Compras (IdLineaConsumo, IdCompra, ImporteImputado) VALUES (?, ?, ?)",
                   (LINEA, r[0], IMPORTE)),
        lambda r: ("INSERT INTO dbo.CompraDocumentosRelacionados (IdCompra, IdCompraRelacionada, CreatedAt) "
                   "VALUES (?, ?, SYSDATETIME())", (r[0], FACTURA)),
        ("DELETE FROM dbo.Tarjetas_Resumenes_Lineas_Estado WHERE IdLineaConsumo = ? AND Estado = 'DiferenciaAceptada'", (LINEA,)),
    ]
    resultados = execute_write_transaction(sentencias)
    print("Nota de Débito creada:", resultados[0])


if __name__ == "__main__":
    main("--apply" in sys.argv)
