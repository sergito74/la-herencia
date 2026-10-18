"""036 — Nidera (303), 18/10/2026: cuenta según los estados y comprobantes de Nidera / SUNANCO / Fulltegra.

Fuentes: estados de cuenta de Nidera (13/04/2020, 31/08/2020, 23/06/2021, 06/07/2021 — mails de SUNANCO/Fulltegra y carpeta
"Resumenes de Cuenta/Nidera"), recibo 1202-8366 (2017), boleto Benedit Bursátil 27859 (27/08/2019), PDFs de Dropbox.
Nidera aplica cada pago en pesos a la deuda en dólares (recibo 2017: "convertidos en dólares ... al pago a cuenta de la deuda en
dólares"), así que la cuenta gobierna en dólares y cada pago se valúa con los US$ que Nidera acreditó (ValuacionProveedor).

Correcciones:
1. Galicia 877 (01/12/2022, $894.900,37, "Cuota De Prestamo" 808028227822): es la cuota del préstamo Galicia Rural del
   10/06/2022, no un pago a Nidera → Banco Galicia (518), como las demás cuotas.
2. Se borran dos ND "SIN COPIA" que no son de Nidera: $3.778,20 (08/08/2018, "Diferencia tipo de cambio": la FC 3931 se
   canceló justa con el cheque y la retención) y $167.162,46 (22/08/2019 ≈ US$13.668,23 x (55,02-42,79), estimación propia).
3. ND 7028-11189 ($180.411,29, dif. de cambio s/ FC 12491): Nidera la anuló con el documento "DI" 1820026177 → NC.
4. FC 0301-4242 / 4243: el total de Nidera incluye la percepción IIBB (US$6.073,07 / 3.314,28); estaban sin ella
   (US$5.786,22 / 3.157,62). La percepción se la devolvió Nidera con las NC 0303-1412 / 1422, que ya estaban.
5. ND 0303-7648: es la ND por dif. de cambio de $41.705,68 (estaba con $240.304,18 y renglones de bolsas de maíz).
6. FC 0301-32216: US$10.702,47 según el PDF (estaba 10.702,37).
7. Valuación en dólares de los pagos en pesos según lo que acreditó Nidera; las notas en pesos se marcan como ajuste de tipo de
   cambio (no mueven dólares): la cuenta gobierna en dólares, como la lleva Nidera.
Idempotente.

Uso (desde backend/): python -m scripts.nidera_036
"""

from __future__ import annotations

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc, fetch_all
from src.features.auditoria_cuentas import bimonetaria
from src.features.vinculos.backup import backup_verificado

C, U = 303, "Sergio (barrida 036)"
FUENTE = "Estados de cuenta de Nidera 2020-2021, recibo 1202-8366, boleto Benedit 27859 y PDFs (Sergio, 18/10/2026)"
VALUACION = {  # (Origen, IdOrigen) -> US$ que acreditó Nidera
    ("Banco Nacion", 16664): 13832.29,   # cheque 3619951 = FC 86913 + 87526 + 87684 al TC de cada una
    ("Retenciones", 2): 0.0, ("Pagos efectivo", 1096): 0.0,   # retención 2017 y su reversión (se netean)
    ("Retenciones", 159): 87.18, ("Banco Nacion", 16665): 11538.05,   # estado 13/04/2020
    ("Retenciones", 165): 144.50,
    ("Banco Nacion", 16666): 10693.54,   # CHPD 3620051 $979.459,97: Nidera recibió el neto $588.358,42 (US$10.693,54)
    ("Pagos efectivo", 2591): 0.0, ("Pagos efectivo", 2594): 0.0,   # costos Aval Rural y Benedit (compensaciones)
    ("Galicia", 50): 8875.42, ("Retenciones", 15): 66.43, ("Galicia", 56): 0.0,   # estado 06/07/2021
    ("Galicia", 581): 6216.50,   # Financiación Galicia Rural 10/06/2022 = FC 23328
    ("Retenciones", 89): 154.75, ("Tarjetas", 5537): 10547.72,   # FC 32216 (US$10.702,47) a TC de pago 216,94
}

if __name__ == "__main__":
    _assert_target_is_wc()
    print("Respaldo verificado:", backup_verificado("nidera-036"))
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=False)
    cur = conn.cursor()
    try:
        cur.execute("UPDATE dbo.[Movimientos Galicia] SET IdContacto = 518 WHERE IdMovimiento = 877 AND IdContacto = ?", C)
        if cur.rowcount:
            cur.execute("INSERT INTO dbo.ReasignacionesContacto (Origen, IdOrigen, IdContactoAnterior, IdContactoNuevo, Motivo, Usuario, Fecha) "
                        "VALUES ('Galicia', 877, ?, 518, ?, ?, SYSDATETIME())", C,
                        "Cuota del préstamo Galicia Rural 808028227822 (financiación de la FC Nidera 23328 del 10/06/2022)", U)
        for i in (2143514682, 2143514683):
            cur.execute("UPDATE dbo.AplicacionesPago SET Anulada = 1, MotivoAnulacion = 'ND propia borrada (barrida 036)', "
                        "UsuarioAnulacion = ?, FechaAnulacion = SYSDATETIME() WHERE IdDocumentoAplicado = ? AND Anulada = 0", U, i)
            cur.execute("DELETE FROM dbo.Remitos_Facturas WHERE IdDeuda = ?", i)
            cur.execute("DELETE FROM dbo.Det_Compras WHERE IdCompra = ?", i)
            cur.execute("DELETE FROM dbo.Compras WHERE IdDeuda = ? AND IdContacto = ? AND [Nro Documento] = 'SIN COPIA'", i, C)
        cur.execute("SELECT 1 FROM dbo.Compras WHERE IdContacto = ? AND [Nro Documento] = 'DI-1820026177'", C)
        if not cur.fetchone():
            cur.execute("INSERT INTO dbo.Compras (Fecha, IdContacto, Tipo, [Tipo documento], [Nro Documento], Moneda, [Tipo de Cambio], "
                        "[Ingresos Brutos], PercepcionIVA, [Conceptos no gravados], Guias, Comision, Financiacion, [Gastos Varios], "
                        "[Ley de Sellos], [Res gral 4169/96], [Ajusta Tipo Cambio]) OUTPUT INSERTED.IdDeuda "
                        "VALUES ('2019-11-20', ?, 'A', 'Nota de Crédito', 'DI-1820026177', 'Pesos', 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1)", C)
            nc = cur.fetchone()[0]
            cur.execute("INSERT INTO dbo.Det_Compras (IdCompra, Cantidad, [Producto/Servicio], IdFormulado, IdCentroCostos, IdDestino, IdRubro, "
                        "IdCampaña, [Campaña], [Precio Unitario], IVA, [Ajuste financiero]) SELECT ?, 1, 'Anulación ND 7028-11189 (dif. cambio)', 0, "
                        "IdCentroCostos, IdDestino, IdRubro, IdCampaña, [Campaña], 149100.24, 21, 0 FROM dbo.Det_Compras WHERE IdCompra = 2143512784 "
                        "AND IdDetalleCompra = (SELECT MIN(IdDetalleCompra) FROM dbo.Det_Compras WHERE IdCompra = 2143512784)", nc)
        cur.execute("UPDATE dbo.Det_Compras SET [Precio Unitario] = -149100.24 WHERE IdCompra IN (SELECT IdDeuda FROM dbo.Compras "
                    "WHERE IdContacto = ? AND [Nro Documento] = 'DI-1820026177') AND [Precio Unitario] > 0", C)   # NC: importe negativo
        # Notas en pesos que solo corrigen la cuenta en pesos de facturas en dólares (no mueven dólares): ND 92707/92708,
        # NC 61472 (2017), ND 11189 y su anulación, ND 7648 y ND 15276 (dif. de cambio)
        cur.execute("UPDATE dbo.Compras SET [Ajusta Tipo Cambio] = 1 WHERE IdContacto = ? AND Moneda = 'Pesos'", C)
        cur.execute("UPDATE dbo.Compras SET [Ingresos Brutos] = 286.85 WHERE IdDeuda = 2143512872")   # 4242
        cur.execute("UPDATE dbo.Compras SET [Ingresos Brutos] = 156.66 WHERE IdDeuda = 2143512871")   # 4243
        cur.execute("SELECT COUNT(*) FROM dbo.Det_Compras WHERE IdCompra = 2143513234")
        if cur.fetchone()[0] != 1 or True:
            cur.execute("SELECT TOP 1 IdCentroCostos, IdDestino, IdRubro, IdCampaña, [Campaña] FROM dbo.Det_Compras WHERE IdCompra = 2143513234")
            m = cur.fetchone()
            cur.execute("DELETE FROM dbo.Det_Compras WHERE IdCompra = 2143513234")
            cur.execute("INSERT INTO dbo.Det_Compras (IdCompra, Cantidad, [Producto/Servicio], IdFormulado, IdCentroCostos, IdDestino, IdRubro, "
                        "IdCampaña, [Campaña], [Precio Unitario], IVA, [Ajuste financiero]) VALUES (2143513234, 1, 'ND/NC Dif. cambio', 0, ?, ?, ?, ?, ?, "
                        "34467.50, 21, 0)", *m)
            cur.execute("UPDATE dbo.Compras SET [Ajusta Tipo Cambio] = 1 WHERE IdDeuda IN (2143513234, 2143513707)")
        cur.execute("UPDATE dbo.Det_Compras SET [Precio Unitario] = 173.4318 WHERE IdCompra = 2143514077 AND Cantidad = 51")
        cur.execute("DELETE FROM dbo.ValuacionProveedor WHERE IdContacto = ?", C)
        for (o, i), d in VALUACION.items():
            cur.execute("INSERT INTO dbo.ValuacionProveedor (Origen, IdOrigen, IdContacto, Dolares, Fuente, Nota, Usuario, Fecha) "
                        "VALUES (?, ?, ?, ?, ?, NULL, ?, SYSDATETIME())", o, i, C, d, FUENTE, U)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    bimonetaria.invalidar()
    r = bimonetaria.cargar_cuenta(C, refrescar=True)
    print("Saldo: pesos", r["saldoPesos"], " US$", r["saldoDolares"], r["gobierna"])
    for f in r["filas"][-8:]:
        print(" ", f["fecha"], f["numeroDocumento"], f["moneda"][:3], round(f["deudaOriginal"], 2), round(f["creditoOriginal"], 2), f["saldoPesos"], f["saldoDolares"])
