"""036 — Sancor Seguros (171), 18/10/2026: cuotas de las pólizas de Irma Miranda según el portal de Sancor.

Fuente: autogestión de Sancor (consulta del 18/10/2026, solo lectura, autorizada por Sergio), cuenta de Irma Delia Miranda
(gmail): estado de cuenta (`PostAccountBalance`) de las pólizas Accidentes Personales ref. 2409457, Vida Colectivo ref.
939969 y Salud ref. 514628. Desde abr-2025 Sancor emite una cuota mensual por las tres; todas figuran PAGAS hasta oct-2026
(la de nov-2026 vence el 02/11). Las pagan los socios desde cuentas particulares (MovimientosCuentaSocio "Seg. Accidentes
Irma"). Cuenta de Giamigli (fibertel): Vida Colectivo ref. 618733 paga hasta oct-2026.

Correcciones:
1. Conciliación tesorería 1460: el cheque propio 13826479 ($1.006, oct-2010) dice "Movistar" → pasa a Movistar (71), con
   un ajuste "saldo anterior al inicio del sistema" (la factura de Movistar de 2010 no está cargada).
2. Se borran tres cupones de pago que no son facturas (608099084 $52.075,92 de la emisión anterior de la póliza, reemplazada
   el 28/07/2026; el de $35.733 del 13/01/2026) y las NC 00035-6907 / 00030-3040, que anulan esa emisión anterior.
3. Cuotas abr-2025 a jun-2026: cada factura queda con la fecha y el importe de Sancor (Accidentes + Vida + Salud); se cargan
   las que faltaban (abr-2025, may-2025, abr-2026). Jul-2026 en adelante ya estaban cargadas por póliza.
4. Cuotas sep-2023 a mar-2025 (antes de lo que muestra el portal): Sancor avisó cada vencimiento por mail; se carga una cuota
   por cada pago de los socios, por el importe pagado (desde abr-2025 el pago coincide siempre con la cuota).
5. Se vinculan a la cuenta los pagos de los socios que no lo estaban y se cargan 6 comprobantes de Dropbox sin cargar (2023-24).
6. Lo que queda (diferencias chicas 2013-2024, antes del período del portal) se ajusta al 31/03/2025, dejando abierta solo la
   cuota oct-2026 de Vida Colectivo ($347,06), que Galicia pagó el 05/10 (extracto de octubre sin cargar).
7. Vida Colectivo feb y mar-2025: $274 según el PDF (estaban con la tarifa anterior). 8-9. Pagos de socios: dic-2025 fue
   $36.077 y la cuota de oct-2026 la pagó Lucy (Sergio, 18/10/2026).
Idempotente.

Uso (desde backend/): python -m scripts.sancor_036
"""

from __future__ import annotations

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc, fetch_all
from src.features.vinculos.backup import backup_verificado

C, U = 171, "Sergio (barrida 036)"
CC, RUBRO = 3, 2047893446   # imputación de las facturas de Accidentes Personales ya cargadas
# (fecha factura Sancor, vencimiento, accidentes, vida, salud, IdDeuda existente o None)
CUOTAS = [
    ("2025-04-16", "02/05/2025", 27005.00, 641.00, 1335.00, None),
    ("2025-05-14", "02/06/2025", 27005.00, 641.00, 1335.00, None),
    ("2025-06-13", "02/07/2025", 27005.00, 641.00, 1335.00, 2143516389),
    ("2025-07-21", "02/08/2025", 27005.00, 641.00, 1335.00, 2143516390),
    ("2025-08-20", "02/09/2025", 30580.00, 641.00, 1486.00, 2143516391),
    ("2025-09-16", "02/10/2025", 30580.00, 641.00, 1486.00, 2143516392),
    ("2025-10-16", "02/11/2025", 30580.00, 641.00, 1486.00, 2143515181),
    ("2025-11-21", "02/12/2025", 30580.00, 641.00, 1486.00, 2143515290),
    ("2025-12-18", "02/01/2026", 33793.00, 641.00, 1643.00, 2143515336),
    ("2026-01-27", "02/02/2026", 34588.00, 813.00, 1643.00, 2143515380),
    ("2026-02-14", "02/03/2026", 34588.00, 813.00, 1643.00, 2143516393),
    ("2026-03-14", "02/04/2026", 34588.00, 813.00, 1643.00, 2143516394),
    ("2026-04-17", "02/05/2026", 39580.00, 813.00, 1896.00, None),
    ("2026-05-15", "02/06/2026", 39580.00, 813.00, 1896.00, 2143517436),
    ("2026-06-12", "02/07/2026", 39580.00, 813.00, 1896.00, 2143517470),
]
# Cuotas previas al portal: (fecha estimada = vencimiento - 16 días, vencimiento, importe pagado, IdMovimientoSocio)
CUOTAS_PREVIAS = [
    ("2023-08-17", "02/09/2023", 4231.00, 2593), ("2023-09-16", "02/10/2023", 4232.00, 2598),
    ("2023-10-17", "02/11/2023", 6017.00, 2604), ("2024-01-17", "02/02/2024", 9226.00, 2621),
    ("2024-02-15", "02/03/2024", 9226.00, 2622), ("2024-03-17", "02/04/2024", 14322.00, 2628),
    ("2024-04-16", "02/05/2024", 14322.00, 2634), ("2024-05-17", "02/06/2024", 16794.00, 2636),
    ("2024-06-16", "02/07/2024", 16794.00, 2642), ("2024-07-17", "02/08/2024", 16794.00, 2650),
    ("2024-08-17", "02/09/2024", 21093.00, 2656), ("2024-09-16", "02/10/2024", 21093.00, 2664),
    ("2024-10-17", "02/11/2024", 21093.00, 2669), ("2024-11-16", "02/12/2024", 21093.00, 2674),
    ("2025-01-17", "02/02/2025", 24594.00, 2161), ("2025-02-14", "02/03/2025", 25388.00, 2682),
    ("2025-03-17", "02/04/2025", 25388.00, 2685),
]
# Comprobantes de Sancor que estaban en Dropbox ("04 2023 - 03 2024") y no se habían cargado: (fecha, número, importe, póliza)
DROPBOX = [("2023-04-07", "514339009", 1451.00, "Vida Colectivo ref. 542394"), ("2023-04-13", "514640013", 2917.00, "Accidentes Personales ref. 2409457 (Irma Miranda)"),
           ("2023-05-09", "517491167", 252.00, "Vida Colectivo ref. 542394"), ("2023-12-11", "539730035", 252.00, "Vida Colectivo ref. 542394"),
           ("2024-01-14", "542957474", 252.00, "Vida Colectivo ref. 542394"), ("2024-02-11", "545385766", 566.00, "Vida Colectivo ref. 542394")]
PENDIENTE_OCT_VC = 347.06   # cuota oct-2026 de Vida Colectivo: Galicia la pagó el 05/10 (extracto de octubre sin cargar)
BORRAR = (2143515354, 2143518493, 2143519509, 2143519514)
VINCULAR = [2593, 2598, 2621, 2622, 2628, 2634, 2636, 2642, 2650, 2656, 2664, 2669, 2674, 2161, 2682, 2685, 2696, 2700, 2704, 2706, 2730, 2766]
LINEAS = (("Accidentes Personales ref. 2409457 (Irma Miranda)", 2), ("Vida Colectivo ref. 939969 (Irma Miranda)", 3),
          ("Salud ref. 514628 (Irma Miranda)", 4))


def detalle(cur, id_compra, importes):
    cur.execute("DELETE FROM dbo.Det_Compras WHERE IdCompra = ?", id_compra)
    for (texto, _), imp in zip(LINEAS, importes):
        if imp:
            cur.execute("INSERT INTO dbo.Det_Compras (IdCompra, Cantidad, Unidad, [Producto/Servicio], IdFormulado, IdCentroCostos, "
                        "IdDestino, IdRubro, IdCampaña, [Campaña], [Precio Unitario], IVA, [Ajuste financiero]) "
                        "VALUES (?, 1, 'Unidades', ?, 0, ?, 1, ?, 20, 'No Aplica', ?, 0, 0)", id_compra, texto[:50], CC, RUBRO, imp)


def nueva(cur, fecha, nro):
    cur.execute("SELECT IdDeuda FROM dbo.Compras WHERE IdContacto = ? AND [Nro Documento] = ?", C, nro)
    r = cur.fetchone()
    if r:
        return r[0]
    cur.execute("INSERT INTO dbo.Compras (Fecha, IdContacto, Tipo, [Tipo documento], [Nro Documento], Moneda, [Tipo de Cambio], "
                "[Ingresos Brutos], PercepcionIVA, [Conceptos no gravados], Guias, Comision, Financiacion, [Gastos Varios], "
                "[Ley de Sellos], [Res gral 4169/96], [Ajusta Tipo Cambio]) OUTPUT INSERTED.IdDeuda "
                "VALUES (?, ?, 'B', 'Factura', ?, 'Pesos', 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)", fecha, C, nro)
    return cur.fetchone()[0]


if __name__ == "__main__":
    _assert_target_is_wc()
    print("Antes:", fetch_all("SELECT SUM(Credito - Deuda) s FROM dbo.vw_MovimientosCuenta_Saldo WHERE IdContacto = ?", (C,)))
    print("Respaldo verificado:", backup_verificado("sancor-036"))
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=False)
    cur = conn.cursor()
    try:
        cur.execute("UPDATE dbo.ConciliacionesTesoreria SET IdContacto = 71 WHERE IdConciliacion = 1460 AND IdContacto = ?", C)
        if cur.rowcount:
            cur.execute("INSERT INTO dbo.AjustesCuentaCorriente (IdContacto, Fecha, Lado, Importe, Motivo, Usuario) VALUES "
                        "(71, '2010-10-31', 'Deuda', 1006.00, ?, ?)",
                        "Saldo anterior al inicio del sistema: el cheque 13826479 del 31/10/2010 ($1.006, 'Movistar') cancela una "
                        "factura de 2010 que no está cargada (estaba conciliado por error a Sancor; decisión de Sergio).", U)
        for i in BORRAR:
            cur.execute("DELETE FROM dbo.Det_Compras WHERE IdCompra = ?", i)
            cur.execute("DELETE FROM dbo.Compras WHERE IdDeuda = ? AND IdContacto = ?", i, C)
        for fecha, venc, ap, vida, salud, id_existente in CUOTAS:
            idc = id_existente or nueva(cur, fecha, f"CUOTA {venc[:6]}{venc[-2:]}")
            cur.execute("UPDATE dbo.Compras SET Fecha = ?, Tipo = 'B', [Ingresos Brutos] = 0, PercepcionIVA = 0, "
                        "[Conceptos no gravados] = 0, Guias = 0, Comision = 0, Financiacion = 0, [Gastos Varios] = 0, "
                        "[Ley de Sellos] = 0, [Res gral 4169/96] = 0 WHERE IdDeuda = ?", fecha, idc)
            detalle(cur, idc, (ap, vida, salud))
        for fecha, venc, importe, _ in CUOTAS_PREVIAS:
            idc = nueva(cur, fecha, f"CUOTA {venc[:6]}{venc[-2:]}")
            cur.execute("DELETE FROM dbo.Det_Compras WHERE IdCompra = ?", idc)
            cur.execute("INSERT INTO dbo.Det_Compras (IdCompra, Cantidad, Unidad, [Producto/Servicio], IdFormulado, IdCentroCostos, "
                        "IdDestino, IdRubro, IdCampaña, [Campaña], [Precio Unitario], IVA, [Ajuste financiero]) "
                        "VALUES (?, 1, 'Unidades', 'Cuota seguros Irma Miranda (importe del pago)', 0, ?, 1, ?, 20, 'No Aplica', ?, 0, 0)",
                        idc, CC, RUBRO, importe)
        for fecha, nro, importe, poliza in DROPBOX:
            idc = nueva(cur, fecha, nro)
            cur.execute("UPDATE dbo.Compras SET [Documento Original] = ? WHERE IdDeuda = ?",
                        f"04 2023 - 03 2024\{fecha.replace('-', '')}_SancorSeguros.pdf#04 2023 - 03 2024\{fecha.replace('-', '')}_SancorSeguros.pdf#", idc)
            cur.execute("DELETE FROM dbo.Det_Compras WHERE IdCompra = ?", idc)
            cur.execute("INSERT INTO dbo.Det_Compras (IdCompra, Cantidad, Unidad, [Producto/Servicio], IdFormulado, IdCentroCostos, "
                        "IdDestino, IdRubro, IdCampaña, [Campaña], [Precio Unitario], IVA, [Ajuste financiero]) "
                        "VALUES (?, 1, 'Unidades', ?, 0, ?, 1, ?, 20, 'No Aplica', ?, 0, 0)", idc, poliza[:50], CC, RUBRO, importe)
        # 7. Cuotas de Vida Colectivo feb y mar-2025: el PDF dice $274 (cargadas con la tarifa anterior, $144 / $143,22)
        for idc in (2143515222, 2143515223):
            cur.execute("UPDATE dbo.Det_Compras SET [Precio Unitario] = 247.34 WHERE IdCompra = ? AND [Producto/Servicio] = 'Seguro de vida'", idc)
            cur.execute("UPDATE dbo.Det_Compras SET [Precio Unitario] = 25.18 WHERE IdCompra = ? AND [Producto/Servicio] = 'Aumento de capital'", idc)
            cur.execute("UPDATE dbo.Compras SET [Conceptos no gravados] = 1.48 WHERE IdDeuda = ?", idc)
        # 8. Sergio: la cuota de dic-2025 se pagó por $36.077 (el movimiento de socio 2227 estaba cargado por $32.707)
        cur.execute("UPDATE dbo.MovimientosCuentaSocio SET Importe = 36077, ImporteUSD = ROUND(ImporteUSD * 36077 / 32707, 4), "
                    "ImporteKgCarne = ROUND(ImporteKgCarne * 36077 / 32707, 3) WHERE IdMovimiento = 2227 AND Importe = 32707")
        # 9. Sergio: la cuota de oct-2026 ($50.259,78, cobrada por Sancor el 05/10/2026) la pagó Lucy
        cur.execute("SELECT IdMovimiento FROM dbo.MovimientosCuentaSocio WHERE IdSocio = 2 AND Importe = 50259.78 AND Fecha = '2026-10-05'")
        r = cur.fetchone()
        if not r:
            cur.execute("INSERT INTO dbo.MovimientosCuentaSocio (IdSocio, Tipo, Importe, Fecha, Medio, Motivo, Usuario, Anulada, ImporteUSD, "
                        "ImporteKgCarne) OUTPUT INSERTED.IdMovimiento VALUES (2, 'Devolucion', 50259.78, '2026-10-05', 'Banco Galicia', "
                        "?, ?, 0, 0, 0)", "Sancor Seguros – Seg. Accidentes Irma (cuota oct-2026, cobrada por Sancor el 05/10/2026)", U)
            r = cur.fetchone()
        VINCULAR.append(int(r[0]))
        for m in VINCULAR:
            cur.execute("IF NOT EXISTS (SELECT 1 FROM dbo.PagosSocioProveedor WHERE IdMovimientoSocio = ?) "
                        "INSERT INTO dbo.PagosSocioProveedor (IdMovimientoSocio, IdContacto, Criterio, FechaAlta) "
                        "VALUES (?, ?, 'manual-036', SYSDATETIME())", m, m, C)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    # 6. Diferencias anteriores a abr-2025 (lo que el portal no muestra; Sancor informa todo pago): ajuste al 31/03/2025
    aj = fetch_all("SELECT ISNULL(SUM(CASE Lado WHEN 'Credito' THEN Importe ELSE -Importe END), 0) s FROM dbo.AjustesCuentaCorriente "
                   "WHERE IdContacto = ? AND Fecha = '2025-03-31'", (C,))[0]["s"]
    total = fetch_all("SELECT SUM(Credito - Deuda) s FROM dbo.vw_MovimientosCuenta_Saldo WHERE IdContacto = ?", (C,))[0]["s"] or 0
    resto = round(total - float(aj) + PENDIENTE_OCT_VC, 2)
    ya = fetch_all("SELECT IdAjuste FROM dbo.AjustesCuentaCorriente WHERE IdContacto = ? AND Fecha = '2025-03-31'", (C,))
    if abs(resto) >= 0.01:
        from src.db.connection import execute_write_transaction
        lado = "Deuda" if resto > 0 else "Credito"
        motivo = ("Diferencias 2013-2024 anteriores al período que muestra el portal de Sancor (abr-2025 en adelante, todo pago): "
                  "pagos chicos de Vida Colectivo y Accidentes sin su comprobante y redondeos. Cierre en 0 (decisión de Sergio).")
        if ya:
            execute_write_transaction([("UPDATE dbo.AjustesCuentaCorriente SET Lado = ?, Importe = ?, Motivo = ? WHERE IdAjuste = ?",
                                        (lado, round(abs(resto), 2), motivo, ya[0]["IdAjuste"]))])
        else:
            execute_write_transaction([("INSERT INTO dbo.AjustesCuentaCorriente (IdContacto, Fecha, Lado, Importe, Motivo, Usuario) "
                                        "VALUES (?, '2025-03-31', ?, ?, ?, ?)", (C, lado, round(abs(resto), 2), motivo, U))])
        print("Ajuste histórico:", lado, round(abs(resto), 2))
    print("Después:", fetch_all("SELECT SUM(Credito - Deuda) s FROM dbo.vw_MovimientosCuenta_Saldo WHERE IdContacto = ?", (C,)))
