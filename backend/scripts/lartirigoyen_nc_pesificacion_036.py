"""036 — Lartirigoyen (61), 19/10/2026: NC de diferencia de pesificación (decisión de Sergio, mismo criterio que ASP tramo 2).

Lartirigoyen lleva la parte en pesos igual que nuestro motor (facturas en US$ al TC de origen, cobros por sus pesos, NDDC por
la diferencia) y su "Cuenta Corriente Pesificada" da $0,01 (extranet, 19/10/2026). Todos los documentos en pesos de los mails
(2019-2024: ND/NC de dif. de cambio e intereses, RR, RD, AP) están cargados con su importe; la diferencia que queda es la
pesificación acumulada de cada pago contra cada factura en dólares (unos $1.932 ya al 27/06/2022 —ficha: Lartirigoyen +$28,39,
nosotros −$1.904—, unos $3.900 entre jun-2022 y jul-2023, y $50 del RR 1283 que Lartirigoyen registró por $7.499,66 contra el
certificado de $7.449,66). Sin el libro histórico completo de Lartirigoyen (descartado pedirlo) no se ubica por factura.
Se borra el AjusteCuentaCorriente 25 ("redondeo final", $346,99, era un parche) y se registra una NC en pesos (ajuste de TC, no
mueve dólares) por el saldo en pesos que queda, con renglones por cultivo en proporción a las facturas en US$ 2017-2024.
Idempotente.

Uso (desde backend/): python -m scripts.lartirigoyen_nc_pesificacion_036
"""

from __future__ import annotations

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all
from src.features.auditoria_cuentas import bimonetaria
from src.features.vinculos.backup import backup_verificado

C, U, NRO = 61, "Sergio (barrida 036)", "NC PESIFICACION"

if __name__ == "__main__":
    _assert_target_is_wc()
    print("Respaldo verificado:", backup_verificado("lartirigoyen-nc-pesificacion-036"))
    execute_write_transaction([
        ("DELETE FROM dbo.ValuacionProveedor WHERE IdContacto = ? AND Origen = 'Compras' AND IdOrigen IN (SELECT IdDeuda FROM dbo.Compras WHERE IdContacto = ? AND [Nro Documento] = ?)", (C, C, NRO)),
        ("DELETE FROM dbo.Det_Compras WHERE IdCompra IN (SELECT IdDeuda FROM dbo.Compras WHERE IdContacto = ? AND [Nro Documento] = ?)", (C, NRO)),
        ("DELETE FROM dbo.Compras WHERE IdContacto = ? AND [Nro Documento] = ?", (C, NRO)),
        ("DELETE FROM dbo.ValuacionProveedor WHERE IdContacto = ? AND Origen = 'Ajuste Interno' AND IdOrigen = 25", (C,)),
        ("DELETE FROM dbo.RevisionPagosSinFactura WHERE IdContacto = ? AND Medio = 'ajuste-interno' AND IdMovimiento = 25", (C,)),
        ("DELETE FROM dbo.AjustesCuentaCorriente WHERE IdAjuste = 25 AND IdContacto = ?", (C,)),
    ])
    bimonetaria.invalidar()
    r = bimonetaria.cargar_cuenta(C, refrescar=True)
    dif = round(-r["saldoPesos"], 2)   # saldo negativo = el sistema muestra que debemos; Lartirigoyen dice $0
    print("Diferencia en pesos a cubrir con la NC:", dif, " US$", r["saldoDolares"])
    if dif <= 0.01:
        raise SystemExit("Nada que registrar.")
    ren = fetch_all("SELECT d.IdCentroCostos cc, d.IdDestino dest, d.IdRubro rub, d.IdCampaña ic, d.[Campaña] camp, SUM(d.Cantidad * d.[Precio Unitario]) neto "
                    "FROM dbo.Compras c JOIN dbo.Det_Compras d ON d.IdCompra = c.IdDeuda WHERE c.IdContacto = ? AND c.Moneda = 'Dolares' "
                    "AND c.[Tipo documento] = 'Factura' AND c.Fecha BETWEEN '2017-01-01' AND '2024-12-31' AND d.Cantidad * d.[Precio Unitario] > 0 "
                    "GROUP BY d.IdCentroCostos, d.IdDestino, d.IdRubro, d.IdCampaña, d.[Campaña]", (C,))
    grupos: dict = {}
    for x in ren:
        g = grupos.setdefault((x["cc"], x["dest"], x["ic"], x["camp"]), {"neto": 0.0, "rub": {}})
        g["neto"] += float(x["neto"]); g["rub"][x["rub"]] = g["rub"].get(x["rub"], 0.0) + float(x["neto"])
    base = sum(g["neto"] for g in grupos.values())
    imp = {k: round(dif * g["neto"] / base, 2) for k, g in grupos.items()}
    imp = {k: v for k, v in imp.items() if v != 0}
    k0 = max(imp, key=imp.get); imp[k0] = round(imp[k0] + dif - sum(imp.values()), 2)
    st = [("INSERT INTO dbo.Compras (Fecha, IdContacto, Tipo, [Tipo documento], [Nro Documento], Moneda, [Tipo de Cambio], [Ingresos Brutos], PercepcionIVA, "
           "[Conceptos no gravados], Guias, Comision, Financiacion, [Gastos Varios], [Ley de Sellos], [Res gral 4169/96], [Ajusta Tipo Cambio]) "
           "VALUES ('2024-07-01', ?, 'A', 'Nota de Crédito', ?, 'Pesos', 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1)", (C, NRO))]
    for (cc, dest, ic, camp), v in imp.items():
        rub = max(grupos[(cc, dest, ic, camp)]["rub"].items(), key=lambda t: t[1])[0]
        st.append(("INSERT INTO dbo.Det_Compras (IdCompra, Cantidad, [Producto/Servicio], IdFormulado, IdCentroCostos, IdDestino, IdRubro, IdCampaña, [Campaña], "
                   "[Precio Unitario], IVA, [Ajuste financiero]) SELECT IdDeuda, 1, 'Diferencia de pesificacion Lartirigoyen 2017-2024', 0, ?, ?, ?, ?, ?, ?, 0, 0 "
                   "FROM dbo.Compras WHERE IdContacto = ? AND [Nro Documento] = ?", (cc, dest, rub, ic, camp, -v, C, NRO)))
    st.append(("INSERT INTO dbo.ValuacionProveedor (Origen, IdOrigen, IdContacto, Dolares, Fuente, Nota, Usuario, Fecha) SELECT 'Compras', IdDeuda, ?, 0, "
               "'Diferencia de pesificación (no mueve dólares)', NULL, ?, SYSDATETIME() FROM dbo.Compras WHERE IdContacto = ? AND [Nro Documento] = ?", (C, U, C, NRO)))
    execute_write_transaction(st)
    bimonetaria.invalidar()
    r = bimonetaria.cargar_cuenta(C, refrescar=True)
    print("Renglones:", len(imp), " Saldo: pesos", r["saldoPesos"], " US$", r["saldoDolares"], r["gobierna"])
