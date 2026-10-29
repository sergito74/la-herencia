"""036 — Lartirigoyen (61), 28/10/2026: la cuenta se copia tal cual del sistema de Lartirigoyen (pedido de Sergio, sin notas internas).

Fuente: extranet de Lartirigoyen, "Comprobantes en Lote" (autorización de Sergio del 28/10/2026): las 55 aplicaciones (AP/APC/APD/
APDS/APG) y todos los comprobantes 2016-2024 (facturas, ND/NC, recibos RID/RIT/RR, cancelaciones de granos TCC, órdenes de pago,
liquidaciones). Cruce comprobante por comprobante; lo que difiere:
1. Venta Granos 110 (LPG 3302-15433794, 14/05/2020): la deducción "Percepcion IVA" $1.281,53 es el IVA RG 4310 que Lartirigoyen
   pagó por CBU junto con el neto (OP 0012-186151, $23.659,27 = $22.377,74 + IC $1.281,53). No es deducción: se borra.
2. Faltaba la NC 0149-00001775 (28/03/2023, US$28,74): devolución del curasemillas del remito 16039; anula la FC 0149-11518 (APG 0147-24288).
3. Faltaban las NDDC 0149-00003931 (18/12/2020, $895,24, dif. de cambio de la FC 8848, AP 6158) y 0149-00004654 (02/12/2022,
   $1.231,60, dif. de cambio de la FC 10918, AP 7276).
4. RID 0007-00002827 (15/10/2021, $1.526, "S-EFt"): Lartirigoyen anuló con este recibo interno la ND 0172-19813 de diferencia de
   cambio después de que Sergio le reenviara (14/10/2021) la prueba de pago del 28/09 de la FC 9731. Nadie pagó en efectivo
   (Sergio, 28/10/2026): se registra como crédito de Lartirigoyen, no fiscal, sin caja.
5. La FC 0149-00008903 es la 0149-00008983 (número según el PDF y ARCA).
6. FC 0149-00007573: TC del PDF 59,925 (estaba 59,93).
7. Se borra la NC PESIFICACION (script lartirigoyen_nc_pesificacion_036, 19/10/2026): era el parche por no tener el libro.
Idempotente.

Uso (desde backend/): python -m scripts.lartirigoyen_recomposicion_portal_036
"""

from __future__ import annotations

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all
from src.features.auditoria_cuentas import bimonetaria
from src.features.vinculos.backup import backup_verificado

C = 61
CARPETA = r"C:\Users\Sergio\Dropbox\Giamigli de Bolivar SA\Compras"
INSERT_COMPRA = (
    "INSERT INTO dbo.Compras (Fecha, IdContacto, Tipo, [Tipo documento], [Nro Documento], Moneda, [Tipo de Cambio], [Ingresos Brutos], "
    "PercepcionIVA, [Conceptos no gravados], Guias, Comision, Financiacion, [Gastos Varios], [Ley de Sellos], [Res gral 4169/96], "
    "[Ajusta Tipo Cambio], [Documento Original]) OUTPUT INSERTED.IdDeuda VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, 0, 0, 0, 0, 0, 0, 0, ?, ?)"
)
INSERT_DET = (
    "INSERT INTO dbo.Det_Compras (IdCompra, Cantidad, [Producto/Servicio], IdFormulado, IdCentroCostos, IdDestino, IdRubro, "
    "IdCampaña, [Campaña], [Precio Unitario], IVA, [Ajuste financiero]) VALUES (?, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?, 0)"
)
FUENTE_PESOS = "Comprobante de la subcuenta en pesos de Lartirigoyen (recomposición desde la extranet, 28/10/2026)"

# (fecha, tipo, tipo doc, nro, moneda, tc, ajusta TC, pdf, renglones: (cant, texto, cc, destino, rubro, campaña id, campaña, precio, iva))
NUEVOS = [
    ("2020-12-18", "A", "Nota de Débito", "0149-00003931", "Pesos", 1, 1, r"04 2020 - 03 2021\20201218_Lartirigoyen NDDC 3931.pdf",
     [(1, "Diferencia de cambio FC 0149-00008848", 1, 14, 2047893470, 13, "2020/2021", 739.87, 21)]),
    ("2022-12-02", "A", "Nota de Débito", "0149-00004654", "Pesos", 1, 1, r"04 2022 - 03 2023\20221202_Lartirigoyen NDDC 4654.pdf",
     [(1, "Diferencia de cambio FC 0149-00010918", 1, 7, 564800828, 17, "2022/2023", 1017.85, 21)]),
    ("2023-03-28", "A", "Nota de Crédito", "0149-00001775", "Dolares", 201.86, 0, r"04 2022 - 03 2023\20230328_Lartirigoyen.pdf",
     [(3, "Lts. Curas.Nova (devolucion)", 2, 12, 2047893470, 18, "2023", -4.75, 21),
      (2, "Lts. Curas.Nova (devolucion)", 3, 16, 2047893470, 20, "No Aplica", -4.75, 21)]),
    ("2021-10-15", "X", "Nota de Crédito", "RID0007-2827", "Pesos", 1, 1, r"04 2021 - 03 2022\20211015_Lartirigoyen RID 2827.pdf",
     [(1, "Anulacion ND 0172-19813 por Lartirigoyen", 1, 7, 564800828, 15, "2021/2022", -1526.00, 0)]),
]


def saldo() -> float:
    return fetch_all("SELECT ROUND(SUM(Credito - Deuda), 2) s FROM dbo.vw_MovimientosCuenta_Saldo WHERE IdContacto = ?", (C,))[0]["s"]


if __name__ == "__main__":
    _assert_target_is_wc()
    antes = saldo()
    st = []
    pesif = fetch_all("SELECT IdDeuda FROM dbo.Compras WHERE IdContacto = ? AND [Nro Documento] = 'NC PESIFICACION'", (C,))
    if pesif:
        i = pesif[0]["IdDeuda"]
        st += [("DELETE FROM dbo.AplicacionesPago WHERE TipoDocumento = 'CompraDeuda' AND IdDocumentoAplicado = ?", (i,)),
               ("DELETE FROM dbo.ValuacionProveedor WHERE IdContacto = ? AND Origen = 'Compras' AND IdOrigen = ?", (C, i)),
               ("DELETE FROM dbo.Det_Compras WHERE IdCompra = ?", (i,)),
               ("DELETE FROM dbo.Compras WHERE IdDeuda = ?", (i,))]
    st += [("DELETE FROM dbo.[Venta Granos_Deducciones] WHERE IdDeduccion = 221 AND IdVenta = 110 AND Detalle = 'Percepcion IVA'", ()),
           ("UPDATE dbo.Compras SET [Nro Documento] = '0149-00008983' WHERE IdDeuda = 2143513043 AND [Nro Documento] = '0149-00008903'", ()),
           ("UPDATE dbo.Compras SET [Tipo de Cambio] = 59.925 WHERE IdDeuda = 2143512469 AND [Tipo de Cambio] = 59.93", ())]
    for fecha, tipo, td, nro, mon, tc, aj, pdf, renglones in NUEVOS:
        if fetch_all("SELECT 1 AS x FROM dbo.Compras WHERE IdContacto = ? AND [Nro Documento] = ?", (C, nro)):
            continue
        pos = len(st)  # results[pos] = IdDeuda del comprobante recién insertado
        st.append((INSERT_COMPRA, (fecha, C, tipo, td, nro, mon, tc, aj, CARPETA + "\\" + pdf)))
        for cant, texto, cc, de, ru, ca, cn, pu, iva in renglones:
            st.append(lambda r, p=pos, v=(cant, texto, cc, de, ru, ca, cn, pu, iva): (INSERT_DET, (r[p], *v)))
        if mon == "Pesos":
            st.append(lambda r, p=pos: ("INSERT INTO dbo.ValuacionProveedor (Origen, IdOrigen, IdContacto, Dolares, Fuente, Usuario) "
                                        "VALUES ('Compras', ?, ?, 0, ?, 'Sergio (barrida 036)')", (r[p], C, FUENTE_PESOS)))
    print("Respaldo verificado:", backup_verificado("lartirigoyen-recomposicion-portal-036"))
    execute_write_transaction(st)
    bimonetaria.invalidar()
    r = bimonetaria.cargar_cuenta(C, refrescar=True)
    print("Saldo vista antes/después:", antes, saldo(), " bimonetaria: $", r["saldoPesos"], "US$", r["saldoDolares"])
