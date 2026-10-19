"""036 — Ajustes de cuenta corriente que son costo/descuento real → ND/NC en pesos imputadas por cultivo (regla de Sergio, 19/10/2026).

Una diferencia que es costo real se registra como ND/NC con renglones por centro de costos/destino/campaña (tomados de la
factura que ajusta, en proporción a sus renglones), no como AjusteCuentaCorriente (que no imputa a cultivos). Cada documento
reemplaza a su ajuste y se imputa: la NC a la factura que descuenta; la ND al pago que la cubrió. No cambia ningún saldo.
Si la factura de origen es en dólares, el documento se marca como ajuste de TC (no mueve dólares). Idempotente.

Uso (desde backend/): python -m scripts.ajustes_a_documentos_036
"""

from __future__ import annotations

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all
from src.features.vinculos.backup import backup_verificado

U = "Sergio (barrida 036)"
# IdAjuste: (IdContacto, tipo, facturas de origen para la imputación, (medio, IdMovimiento) que cubre la ND | None, texto)
CASOS = {
    28: (171, "Nota de Débito", "SELECT IdDeuda FROM dbo.Compras WHERE IdContacto = 171 AND Fecha BETWEEN '2013-01-01' AND '2025-03-31'", None,
         "Diferencias de primas Sancor 2013-2024"),
    5: (605, "Nota de Crédito", "SELECT 2143515191", None, "Descuento FC 00002-00000359 (pago MercadoLibre)"),
    4: (606, "Nota de Crédito", "SELECT 2143515192", None, "Descuento FC 00004-00000305 (pago MercadoLibre)"),
    6: (626, "Nota de Crédito", "SELECT 2143515257", None, "Descuento MercadoLibre 2,108% FC 0002-01277521"),
    20: (440, "Nota de Crédito", "SELECT 2143514091", None, "eCheq 66 por $30 menos (FC 00007-32206)"),
    21: (449, "Nota de Débito", "SELECT IdDeuda FROM dbo.Compras WHERE IdDeuda IN (2143513696, 2143513697)", ("galicia", 612),
         "Dif. cambio eCheqs 6 y 8 sobre FC 0003-61/73 en US$"),
}

if __name__ == "__main__":
    _assert_target_is_wc()
    print("Respaldo verificado:", backup_verificado("ajustes-a-documentos-036"))
    for id_ajuste, (c, tipo, origen, cubre, texto) in CASOS.items():
        nro = f"AJ {id_ajuste}"
        ya = fetch_all("SELECT IdDeuda FROM dbo.Compras WHERE IdContacto = ? AND [Nro Documento] = ?", (c, nro))
        aj = fetch_all("SELECT Fecha, Importe FROM dbo.AjustesCuentaCorriente WHERE IdAjuste = ?", (id_ajuste,))
        if ya and not aj:
            continue   # ya convertido
        fecha, importe = aj[0]["Fecha"], float(aj[0]["Importe"])
        signo = -1 if tipo == "Nota de Crédito" else 1
        ids = [r[k] for r in fetch_all(origen, ()) for k in r]
        marcas = ",".join("?" * len(ids))
        renglones = fetch_all(f"SELECT d.IdCompra, d.Cantidad * d.[Precio Unitario] AS neto, d.IdCentroCostos cc, d.IdDestino dest, d.IdRubro rub, "
                              f"d.IdCampaña ic, d.[Campaña] camp FROM dbo.Det_Compras d WHERE d.IdCompra IN ({marcas}) AND d.Cantidad * d.[Precio Unitario] > 0", tuple(ids))
        dolares = bool(fetch_all(f"SELECT 1 AS x FROM dbo.Compras WHERE IdDeuda IN ({marcas}) AND Moneda = 'Dolares'", tuple(ids)))
        grupos: dict = {}
        for r in renglones:
            g = grupos.setdefault((r["cc"], r["dest"], r["ic"], r["camp"]), {"neto": 0.0, "rub": {}})
            g["neto"] += float(r["neto"]); g["rub"][r["rub"]] = g["rub"].get(r["rub"], 0.0) + float(r["neto"])
        base = sum(g["neto"] for g in grupos.values())
        imp = {k: round(importe * g["neto"] / base, 2) for k, g in grupos.items()}
        k0 = max(imp, key=imp.get); imp[k0] = round(imp[k0] + importe - sum(imp.values()), 2)
        st = [("INSERT INTO dbo.Compras (Fecha, IdContacto, Tipo, [Tipo documento], [Nro Documento], Moneda, [Tipo de Cambio], [Ingresos Brutos], "
               "PercepcionIVA, [Conceptos no gravados], Guias, Comision, Financiacion, [Gastos Varios], [Ley de Sellos], [Res gral 4169/96], "
               "[Ajusta Tipo Cambio]) VALUES (?, ?, 'A', ?, ?, 'Pesos', 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, ?)", (fecha, c, tipo, nro, 1 if dolares else 0))]
        for (cc, dest, ic, camp), v in imp.items():
            rub = max(grupos[(cc, dest, ic, camp)]["rub"].items(), key=lambda t: t[1])[0]
            st.append(("INSERT INTO dbo.Det_Compras (IdCompra, Cantidad, [Producto/Servicio], IdFormulado, IdCentroCostos, IdDestino, IdRubro, IdCampaña, "
                       "[Campaña], [Precio Unitario], IVA, [Ajuste financiero]) SELECT IdDeuda, 1, ?, 0, ?, ?, ?, ?, ?, ?, 0, 0 FROM dbo.Compras "
                       "WHERE IdContacto = ? AND [Nro Documento] = ?", (texto[:50], cc, dest, rub, ic, camp, signo * v, c, nro)))
        if tipo == "Nota de Crédito":   # la NC cancela la factura que descuenta
            st.append(("INSERT INTO dbo.AplicacionesPago (OrigenMovimiento, IdMovimientoOrigen, TipoDocumento, IdDocumentoAplicado, ImporteAplicado, Fecha, "
                       "Usuario, Anulada, Origen, NotaConciliacion) SELECT 'comp-compra', IdDeuda, 'CompraDeuda', ?, ?, SYSDATETIME(), ?, 0, 'manual', ? "
                       "FROM dbo.Compras WHERE IdContacto = ? AND [Nro Documento] = ?", (ids[0], importe, U, f"Barrida 036: {texto}", c, nro)))
        elif cubre:   # la ND la cubrió el pago que pagó de más
            st.append(("INSERT INTO dbo.AplicacionesPago (OrigenMovimiento, IdMovimientoOrigen, TipoDocumento, IdDocumentoAplicado, ImporteAplicado, Fecha, "
                       "Usuario, Anulada, Origen, NotaConciliacion) SELECT ?, ?, 'CompraDeuda', IdDeuda, ?, SYSDATETIME(), ?, 0, 'manual', ? "
                       "FROM dbo.Compras WHERE IdContacto = ? AND [Nro Documento] = ?", (cubre[0], cubre[1], importe, U, f"Barrida 036: {texto}", c, nro)))
        st.append(("DELETE FROM dbo.RevisionPagosSinFactura WHERE IdContacto = ? AND Medio = 'ajuste-interno' AND IdMovimiento = ?", (c, id_ajuste)))
        st.append(("DELETE FROM dbo.ValuacionProveedor WHERE IdContacto = ? AND Origen = 'Ajuste Interno' AND IdOrigen = ?", (c, id_ajuste)))
        st.append(("DELETE FROM dbo.AjustesCuentaCorriente WHERE IdAjuste = ?", (id_ajuste,)))
        execute_write_transaction(st)
        print(id_ajuste, c, nro, tipo, importe, {f"{k[0]}/{k[1]}/{k[3]}": v for k, v in imp.items()})
