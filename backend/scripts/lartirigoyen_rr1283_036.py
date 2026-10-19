"""036 — Lartirigoyen (61), 19/10/2026: RR 0007-00001283 "Ing Rete" y ND 0149-00004694 (extranet, leídos con autorización).

El RR 1283 (22/12/2022, $7.499,66, régimen 78 Ganancias bienes) es el "Recibo de Retenciones" con que Lartirigoyen registró
NUESTRA retención de Ganancias del certificado 0000-2022-000032 ($7.449,66, 28/11/2022, ya cargada: Retenciones 71); lo
registró con $50 de más. Lo aplicó: AP 7311 (22/12/2022) $1.260,67 a la FC 10918 + $212,61 a la ND 4694; AP 7888 (2023)
$5.991,54 a la FC 11992; $34,84 a otro comprobante.
1. El AjusteCuentaCorriente 23 ($5.991,54) duplicaba en pesos la retención 71: se borra; sus US$ (22,2983, al TC 268,7 del
   AP 7888) pasan a la valuación de la retención 71 (misma retención aplicada en dos momentos).
2. Falta la ND 0149-00004694 (22/12/2022, diferencia de cambio sobre la FC 10918: $175,71 + IVA 21% = $212,61): ND en pesos,
   ajuste de TC, con los renglones por cultivo de la FC 10918 (regla de Sergio: dif. de cambio = costo real por cultivo).
Idempotente.

Uso (desde backend/): python -m scripts.lartirigoyen_rr1283_036
"""

from __future__ import annotations

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all
from src.features.auditoria_cuentas import bimonetaria
from src.features.vinculos.backup import backup_verificado

C, U, FC10918, NRO = 61, "Sergio (barrida 036)", 2143513761, "0149-00004694"
PDF = r"C:\Users\Sergio\Dropbox\Giamigli de Bolivar SA\Compras\04 2022 - 03 2023\20221222_Lartirigoyen ND 4694.pdf"
NETO = 175.71

if __name__ == "__main__":
    _assert_target_is_wc()
    print("Respaldo verificado:", backup_verificado("lartirigoyen-rr1283-036"))
    st = []
    aj = fetch_all("SELECT Dolares FROM dbo.ValuacionProveedor WHERE IdContacto = ? AND Origen = 'Ajuste Interno' AND IdOrigen = 23", (C,))
    if aj:
        st += [("UPDATE dbo.ValuacionProveedor SET Dolares = Dolares + ?, Nota = 'Incluye el resto del RR 1283 aplicado en el AP 7888 (antes ajuste 23)' "
                "WHERE IdContacto = ? AND Origen = 'Retenciones' AND IdOrigen = 71", (float(aj[0]["Dolares"]), C)),
               ("DELETE FROM dbo.ValuacionProveedor WHERE IdContacto = ? AND Origen = 'Ajuste Interno' AND IdOrigen = 23", (C,))]
    st += [("DELETE FROM dbo.RevisionPagosSinFactura WHERE IdContacto = ? AND Medio = 'ajuste-interno' AND IdMovimiento = 23", (C,)),
           ("DELETE FROM dbo.AjustesCuentaCorriente WHERE IdAjuste = 23 AND IdContacto = ?", (C,))]
    if not fetch_all("SELECT 1 AS x FROM dbo.Compras WHERE IdContacto = ? AND [Nro Documento] = ?", (C, NRO)):
        st.append(("INSERT INTO dbo.Compras (Fecha, IdContacto, Tipo, [Tipo documento], [Nro Documento], Moneda, [Tipo de Cambio], [Ingresos Brutos], "
                   "PercepcionIVA, [Conceptos no gravados], Guias, Comision, Financiacion, [Gastos Varios], [Ley de Sellos], [Res gral 4169/96], "
                   "[Ajusta Tipo Cambio], [Documento Original]) VALUES ('2022-12-22', ?, 'A', 'Nota de Débito', ?, 'Pesos', 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, ?)",
                   (C, NRO, PDF + "#" + PDF + "#")))
        ren = fetch_all("SELECT IdCentroCostos cc, IdDestino d, IdRubro r, IdCampaña ic, [Campaña] c, Cantidad * [Precio Unitario] AS neto "
                        "FROM dbo.Det_Compras WHERE IdCompra = ? AND Cantidad * [Precio Unitario] > 0", (FC10918,))
        base = sum(float(x["neto"]) for x in ren)
        imp = [round(NETO * float(x["neto"]) / base, 2) for x in ren]
        imp[imp.index(max(imp))] += round(NETO - sum(imp), 2)
        for x, v in zip(ren, imp):
            st.append(("INSERT INTO dbo.Det_Compras (IdCompra, Cantidad, [Producto/Servicio], IdFormulado, IdCentroCostos, IdDestino, IdRubro, IdCampaña, "
                       "[Campaña], [Precio Unitario], IVA, [Ajuste financiero]) SELECT IdDeuda, 1, 'Diferencia de cambio FC 0149-00010918', 0, ?, ?, ?, ?, ?, ?, 21, 0 "
                       "FROM dbo.Compras WHERE IdContacto = ? AND [Nro Documento] = ?", (x["cc"], x["d"], x["r"], x["ic"], x["c"], round(v, 2), C, NRO)))
        st.append(("INSERT INTO dbo.ValuacionProveedor (Origen, IdOrigen, IdContacto, Dolares, Fuente, Nota, Usuario, Fecha) SELECT 'Compras', IdDeuda, ?, 0, "
                   "'ND de diferencia de cambio en pesos (no mueve dólares)', NULL, ?, SYSDATETIME() FROM dbo.Compras WHERE IdContacto = ? AND [Nro Documento] = ?",
                   (C, U, C, NRO)))
        st.append(("INSERT INTO dbo.AplicacionesPago (OrigenMovimiento, IdMovimientoOrigen, TipoDocumento, IdDocumentoAplicado, ImporteAplicado, Fecha, Usuario, "
                   "Anulada, Origen, NotaConciliacion) SELECT 'retenciones', 71, 'CompraDeuda', IdDeuda, 212.61, SYSDATETIME(), ?, 0, 'manual', "
                   "'AP 0149-00007311: RR 1283 (retención 71) aplicado a la ND 4694' FROM dbo.Compras WHERE IdContacto = ? AND [Nro Documento] = ?", (U, C, NRO)))
    execute_write_transaction(st)
    bimonetaria.invalidar()
    r = bimonetaria.cargar_cuenta(C, refrescar=True)
    print("Saldo: pesos", r["saldoPesos"], " US$", r["saldoDolares"], r["gobierna"])
