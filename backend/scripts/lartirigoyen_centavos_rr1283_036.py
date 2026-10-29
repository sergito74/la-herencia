"""036 — Lartirigoyen (61), 28/10/2026: últimos ajustes para que la cuenta sea copia exacta del sistema de Lartirigoyen.

1. Centavos: en 24 comprobantes el total de WC difiere del importe con que Lartirigoyen los cancela (redondeo de los renglones en
   US$, p. ej. US$28,7375 contra US$28,74 del PDF). Se corrige el precio del primer renglón para que el total sea el de Lartirigoyen.
2. RR 0007-00001283: Lartirigoyen registró nuestra retención por $7.499,66 (certificado 0000-2022-000032: $7.449,66) y aplicó los
   $7.499,66. Se registra la diferencia de $50 como crédito de Lartirigoyen, no fiscal; el certificado no se toca.
Idempotente (recalcula la diferencia contra el objetivo).

Uso (desde backend/): python -m scripts.lartirigoyen_centavos_rr1283_036
"""

from __future__ import annotations

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all
from src.features.auditoria_cuentas import bimonetaria
from src.features.vinculos.backup import backup_verificado

C = 61
# IdDeuda o número → importe en pesos con que Lartirigoyen cancela el comprobante (aplicaciones descargadas de la extranet)
OBJETIVO = {
    "0149-00003804": 46044.38, "0149-00003803": 30439.54, "0149-00002157": 12147.84, "0149-00007107": 6408.65,
    "0149-00007573": 208472.48, "0149-00008182": 397639.02, "0324-00055587": 32055.02, "0149-00008540": 99778.54,
    "0149-00008723": 21465.83, "0149-00008895": 46950.83, "0149-00008894": 22297.64, "0149-00008983": 2286.63,
    "0149-00008984": 11046.79, "0149-00004117": 323.98, "0149-00010918": 721744.85, "0149 - 00011506": 5768.98,
    "0149 - 00011517": 5801.46, "0149 - 00011518": 5801.46, "0149-00001775": 5801.46, "0149 - 00011992": 1435760.16,
    "0149 - 00005210": 12829457.58, "0118 - 00092846": 12829457.58, "0149 - 00012509": 2699268.00, "0149 - 00012612": 2801606.78,
    "0149-00001728": 84.34, "0149-00004176": 147372.79, "0149-00004739": 25855.13, "0172-00013096": 24938.11,
    "0149-00005499": 76781.78, "0149-00005514": 104292.93, "0172-00007543": 24938.11, "0149-00005834": 237251.80,
    "0149-00006391": 30114.59, "0149-00006399": 18652.49, "0324-00041069": 183342.93, "0149-00002902": 3548.20,
    "0149-00009398": 364219.80, "0149-00004118": 48688.06, "0149-00009731": 378345.27, "0149 - 00004645": 4683.23,
    "0149 - 00004646": 75211.72, "0149 - 00011970": 1400628.24, "0149 - 00005494": 127339.96,
    "0149 - 00001971": 2699268.00,
}


def saldo() -> float:
    return fetch_all("SELECT ROUND(SUM(Credito - Deuda), 2) s FROM dbo.vw_MovimientosCuenta_Saldo WHERE IdContacto = ?", (C,))[0]["s"]


if __name__ == "__main__":
    _assert_target_is_wc()
    antes = saldo()
    st = []
    for nro, objetivo in OBJETIVO.items():
        c = fetch_all("SELECT c.IdDeuda, c.Moneda, c.[Tipo de Cambio] tc, v.ImporteDocumento imp FROM dbo.Compras c "
                      "JOIN dbo.vw_Compras_ImporteDocumento v ON v.IdDeuda = c.IdDeuda WHERE c.IdContacto = ? AND c.[Nro Documento] = ?",
                      (C, nro))
        assert len(c) == 1, nro
        c = c[0]
        tc = float(c["tc"]) if c["Moneda"] == "Dolares" else 1.0
        actual = abs(float(c["imp"])) * tc
        dif = round(objetivo - actual, 2)
        if abs(dif) < 0.005:
            continue
        # La vista redondea a 4 decimales: el ajuste se calcula con la suma exacta de los renglones para no oscilar.
        exacto = fetch_all("SELECT SUM(CAST(Cantidad AS float) * CAST([Precio Unitario] AS float) * (1 + CAST(ISNULL(IVA, 0) AS float) / 100)) s "
                           "FROM dbo.Det_Compras WHERE IdCompra = ?", (c["IdDeuda"],))[0]["s"]
        extras = abs(float(c["imp"])) - abs(float(exacto))  # percepciones y otros campos de la cabecera
        det = fetch_all("SELECT TOP 1 IdDetalleCompra, Cantidad, [Precio Unitario] pu, IVA FROM dbo.Det_Compras WHERE IdCompra = ? "
                        "ORDER BY ABS(Cantidad * [Precio Unitario]) DESC", (c["IdDeuda"],))[0]
        signo = 1 if float(det["pu"]) >= 0 else -1  # las NC llevan precio negativo
        falta = objetivo / tc - extras - abs(float(exacto))
        delta_pu = signo * falta / (float(det["Cantidad"]) * (1 + float(det["IVA"] or 0) / 100))
        print(f"{nro:18} {c['Moneda'][:3]} actual {actual:,.2f} objetivo {objetivo:,.2f} dif {dif:+.2f}")
        st.append(("UPDATE dbo.Det_Compras SET [Precio Unitario] = [Precio Unitario] + ? WHERE IdDetalleCompra = ?",
                   (delta_pu, det["IdDetalleCompra"])))
    # ND 0149-5119 (intereses): US$0,95 a TC 229,20 = $217,74 según Lartirigoyen (WC tenía TC 229,29 y US$0,9496).
    if fetch_all("SELECT 1 AS x FROM dbo.Compras WHERE IdDeuda = 2143514128 AND [Tipo de Cambio] <> 229.2", ()):
        st += [("UPDATE dbo.Compras SET [Tipo de Cambio] = 229.2 WHERE IdDeuda = 2143514128", ()),
               ("UPDATE dbo.Det_Compras SET [Precio Unitario] = ? WHERE IdDetalleCompra = 2141374939", (0.95 / 1.21,))]
    if not fetch_all("SELECT 1 AS x FROM dbo.Compras WHERE IdContacto = ? AND [Nro Documento] = 'RR0007-1283'", (C,)):
        st += [("INSERT INTO dbo.Compras (Fecha, IdContacto, Tipo, [Tipo documento], [Nro Documento], Moneda, [Tipo de Cambio], "
                "[Ingresos Brutos], PercepcionIVA, [Conceptos no gravados], Guias, Comision, Financiacion, [Gastos Varios], [Ley de Sellos], "
                "[Res gral 4169/96], [Ajusta Tipo Cambio], [Documento Original]) OUTPUT INSERTED.IdDeuda VALUES ('2022-12-22', ?, 'X', "
                "'Nota de Crédito', 'RR0007-1283', 'Pesos', 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, NULL)", (C,)),
               lambda r: ("INSERT INTO dbo.Det_Compras (IdCompra, Cantidad, [Producto/Servicio], IdFormulado, IdCentroCostos, IdDestino, "
                          "IdRubro, IdCampaña, [Campaña], [Precio Unitario], IVA, [Ajuste financiero]) VALUES (?, 1, "
                          "'Dif. RR 1283 Lartirigoyen (7499,66 vs 7449,66)', 0, 1, 7, 564800828, 17, '2022/2023', -50, 0, 0)", (r[-1],)),
               lambda r: ("INSERT INTO dbo.ValuacionProveedor (Origen, IdOrigen, IdContacto, Dolares, Fuente, Usuario) VALUES "
                          "('Compras', ?, ?, 0, 'Comprobante de la subcuenta en pesos de Lartirigoyen (RR 1283)', 'Sergio (barrida 036)')",
                          (r[-2], C))]
    if not st:
        raise SystemExit("Nada que corregir.")
    print("Respaldo verificado:", backup_verificado("lartirigoyen-centavos-rr1283-036"))
    execute_write_transaction(st)
    bimonetaria.invalidar()
    r = bimonetaria.cargar_cuenta(C, refrescar=True)
    print("Saldo vista antes/después:", antes, saldo(), " bimonetaria: $", r["saldoPesos"], "US$", r["saldoDolares"])
