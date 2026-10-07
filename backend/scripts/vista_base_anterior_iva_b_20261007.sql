
CREATE VIEW dbo.vw_MovimientosCuenta_Base
AS

SELECT
    base.Fecha,
    COALESCE(ov.IdContactoNuevo, base.IdContacto) AS IdContacto,
    COALESCE(ctov.[Razon Social], base.[Razon Social]) AS [Razon Social],
    base.Documento,
    base.[Nro Documento],
    base.Deuda,
    base.Credito,
    base.Origen,
    base.IdOrigen
FROM (
SELECT
    c.Fecha,
    c.IdContacto,
    ct.[Razon Social],
    c.[Tipo documento] AS Documento,
    c.[Nro Documento],
    CASE WHEN tc.GranTotal > 0 THEN tc.GranTotal ELSE 0 END AS Deuda,
    CASE WHEN tc.GranTotal < 0 THEN -tc.GranTotal ELSE 0 END AS Credito,
    CAST('Compras' AS varchar(50)) AS Origen,
    CAST(c.IdDeuda AS bigint) AS IdOrigen
FROM dbo.Compras AS c
INNER JOIN dbo.Contactos AS ct
    ON ct.IdContacto = c.IdContacto
INNER JOIN dbo.vw_Cns_Total_Compra AS tc
    ON tc.IdDeuda = c.IdDeuda

UNION ALL

SELECT
    a.Fecha,
    a.IdContacto,
    ct.[Razon Social],
    'Contrato Arrendamiento' AS Documento,
    'SIN NUMERO' AS [Nro Documento],
    CAST(0 AS money) AS Deuda,
    a.[Importe total del contrato] AS Credito,
    CAST('Alquileres' AS varchar(50)) AS Origen,
    CAST(a.IdAlquiler AS bigint) AS IdOrigen
FROM dbo.Alquileres AS a
INNER JOIN dbo.Contactos AS ct
    ON ct.IdContacto = a.IdContacto

UNION ALL

SELECT
    i.Fecha,
    i.IdOrganismo AS IdContacto,
    ct.[Razon Social],
    ti.[Nombre Impuesto] AS Documento,
    i.[Numero de documento] AS [Nro Documento],
    CASE WHEN i.Importe > 0 THEN i.Importe ELSE 0 END AS Deuda,
    CASE WHEN i.Importe < 0 THEN -i.Importe ELSE 0 END AS Credito,
    CAST('Impuestos' AS varchar(50)) AS Origen,
    CAST(i.IdImpuesto AS bigint) AS IdOrigen
FROM dbo.Impuestos AS i
INNER JOIN dbo.Contactos AS ct
    ON ct.IdContacto = i.IdOrganismo
INNER JOIN dbo.[Tipo Impuesto] AS ti
    ON ti.IdTipoImpuesto = i.IdTipoImpuesto

UNION ALL

SELECT
    r.[Fecha de pago] AS Fecha,
    r.IdContacto,
    ct.[Razon Social],
    'Recibo Sueldo' AS Documento,
    r.[Periodo liquidado] AS [Nro Documento],
    CASE
        WHEN (
            ISNULL(r.[Sueldo basico], 0) +
            ISNULL(r.[Antiguedad], 0) +
            ISNULL(r.[Adic futuros aumentos], 0) +
            ISNULL(r.[Dia Gremio], 0) +
            ISNULL(r.[Aguinaldo], 0) +
            ISNULL(r.[Vacaciones], 0) +
            ISNULL(r.[Ajuste], 0) +
            ISNULL(r.[Ajuste No Remunerativo], 0) +
            ISNULL(r.[Redondeo], 0) +
            ISNULL(r.[Bonificacion adicional], 0) -
            ISNULL(r.[Jubilacion], 0) -
            ISNULL(r.[Ley 19032], 0) -
            ISNULL(r.[Obra Social], 0) -
            ISNULL(r.[Obra Social Acuerdos], 0) -
            ISNULL(r.[Servicio de Sepelio], 0) -
            ISNULL(r.[Aporte Sindical], 0)
        ) > 0
        THEN (
            ISNULL(r.[Sueldo basico], 0) +
            ISNULL(r.[Antiguedad], 0) +
            ISNULL(r.[Adic futuros aumentos], 0) +
            ISNULL(r.[Dia Gremio], 0) +
            ISNULL(r.[Aguinaldo], 0) +
            ISNULL(r.[Vacaciones], 0) +
            ISNULL(r.[Ajuste], 0) +
            ISNULL(r.[Ajuste No Remunerativo], 0) +
            ISNULL(r.[Redondeo], 0) +
            ISNULL(r.[Bonificacion adicional], 0) -
            ISNULL(r.[Jubilacion], 0) -
            ISNULL(r.[Ley 19032], 0) -
            ISNULL(r.[Obra Social], 0) -
            ISNULL(r.[Obra Social Acuerdos], 0) -
            ISNULL(r.[Servicio de Sepelio], 0) -
            ISNULL(r.[Aporte Sindical], 0)
        )
        ELSE 0
    END AS Deuda,
    CASE
        WHEN (
            ISNULL(r.[Sueldo basico], 0) +
            ISNULL(r.[Antiguedad], 0) +
            ISNULL(r.[Adic futuros aumentos], 0) +
            ISNULL(r.[Dia Gremio], 0) +
            ISNULL(r.[Aguinaldo], 0) +
            ISNULL(r.[Vacaciones], 0) +
            ISNULL(r.[Ajuste], 0) +
            ISNULL(r.[Ajuste No Remunerativo], 0) +
            ISNULL(r.[Redondeo], 0) +
            ISNULL(r.[Bonificacion adicional], 0) -
            ISNULL(r.[Jubilacion], 0) -
            ISNULL(r.[Ley 19032], 0) -
            ISNULL(r.[Obra Social], 0) -
            ISNULL(r.[Obra Social Acuerdos], 0) -
            ISNULL(r.[Servicio de Sepelio], 0) -
            ISNULL(r.[Aporte Sindical], 0)
        ) < 0
        THEN -(
            ISNULL(r.[Sueldo basico], 0) +
            ISNULL(r.[Antiguedad], 0) +
            ISNULL(r.[Adic futuros aumentos], 0) +
            ISNULL(r.[Dia Gremio], 0) +
            ISNULL(r.[Aguinaldo], 0) +
            ISNULL(r.[Vacaciones], 0) +
            ISNULL(r.[Ajuste], 0) +
            ISNULL(r.[Ajuste No Remunerativo], 0) +
            ISNULL(r.[Redondeo], 0) +
            ISNULL(r.[Bonificacion adicional], 0) -
            ISNULL(r.[Jubilacion], 0) -
            ISNULL(r.[Ley 19032], 0) -
            ISNULL(r.[Obra Social], 0) -
            ISNULL(r.[Obra Social Acuerdos], 0) -
            ISNULL(r.[Servicio de Sepelio], 0) -
            ISNULL(r.[Aporte Sindical], 0)
        )
        ELSE 0
    END AS Credito,
    CAST('Remuneraciones' AS varchar(50)) AS Origen,
    CAST(r.IdSalario AS bigint) AS IdOrigen
FROM dbo.Remuneraciones AS r
INNER JOIN dbo.Contactos AS ct
    ON ct.IdContacto = r.IdContacto

UNION ALL

SELECT
    g.Fecha,
    CAST(g.IdContacto AS int) AS IdContacto,
    ct.[Razon Social],
    'Resumen Bancario' AS Documento,
    CONVERT(varchar(50), CONVERT(decimal(38,0), g.[Número de Comprobante])) AS [Nro Documento],
    ISNULL(g.[Créditos], 0) AS Deuda,
    ISNULL(g.[Débitos], 0) AS Credito,
    CAST('Galicia' AS varchar(50)) AS Origen,
    CAST(g.IdMovimiento AS bigint) AS IdOrigen
FROM dbo.[Movimientos Galicia] AS g
INNER JOIN dbo.Contactos AS ct
    ON ct.IdContacto = CAST(g.IdContacto AS int)

UNION ALL

SELECT
    b.[Fecha / Hora Mov#] AS Fecha,
    CAST(b.IdContacto AS int) AS IdContacto,
    ct.[Razon Social],
    'Resumen Bancario' AS Documento,
    CONVERT(varchar(50), CONVERT(decimal(38,0), b.[Nro# Comprobante])) AS [Nro Documento],
    CASE WHEN ISNULL(b.Importe, 0) > 0 THEN b.Importe ELSE 0 END AS Deuda,
    CASE WHEN ISNULL(b.Importe, 0) < 0 THEN -b.Importe ELSE 0 END AS Credito,
    CAST('Banco Nacion' AS varchar(50)) AS Origen,
    CAST(b.IdMovimientoBNA AS bigint) AS IdOrigen
FROM dbo.[Movimientos BNA] AS b
INNER JOIN dbo.Contactos AS ct
    ON ct.IdContacto = CAST(b.IdContacto AS int)

UNION ALL

SELECT
    pe.Fecha,
    pe.IdContacto,
    ct.[Razon Social],
    COALESCE(NULLIF(LTRIM(RTRIM(pe.Caja)), ''), NULLIF(LTRIM(RTRIM(pe.Cuenta)), ''), 'Pago efectivo') AS Documento,
    CASE
        WHEN pe.[Numero documento] IS NULL THEN NULL
        ELSE CONVERT(varchar(50), CONVERT(decimal(38,0), pe.[Numero documento]))
    END AS [Nro Documento],
    CAST(0 AS money) AS Deuda,
    CAST(pe.[Importe imputado] AS money) AS Credito,
    CAST('Pagos efectivo' AS varchar(50)) AS Origen,
    CAST(pe.IdPagoEfectivo AS bigint) AS IdOrigen
FROM dbo.[Pagos efectivo] AS pe
INNER JOIN dbo.Contactos AS ct
    ON ct.IdContacto = pe.IdContacto
WHERE pe.IdContacto IS NOT NULL
  AND ISNULL(pe.[Importe imputado], 0) <> 0

UNION ALL

SELECT
    vrp.Fecha,
    vrp.IdContacto,
    vrp.[Razon Social],
    vrp.Documento,
    CAST(vrp.[Nro Documento] AS varchar(50)) AS [Nro Documento],
    CAST(vrp.Deuda AS money) AS Deuda,
    CAST(vrp.Credito AS money) AS Credito,
    CAST('Pagos Valores Recibidos' AS varchar(50)) AS Origen,
    CAST(vr.IdValor AS bigint) AS IdOrigen
FROM dbo.vw_CnsPagosValoresRecibidos AS vrp
INNER JOIN dbo.[Valores Recibidos] AS vr
    ON vr.[Numero Valor] = vrp.[Nro Documento]
   AND vr.[Fecha Endoso] = vrp.Fecha
   AND vr.IdReceptor = vrp.IdContacto

UNION ALL

SELECT
    vrc.Fecha,
    vrc.IdContacto,
    vrc.[Razon Social],
    vrc.Documento,
    CAST(vrc.[Nro Documento] AS varchar(50)) AS [Nro Documento],
    CAST(vrc.Deuda AS money) AS Deuda,
    CAST(vrc.Credito AS money) AS Credito,
    CAST('Cobros Valores Recibidos' AS varchar(50)) AS Origen,
    CAST(vr.IdValor AS bigint) AS IdOrigen
FROM dbo.vw_CnsCobrosValoresRecibidos AS vrc
INNER JOIN dbo.[Valores Recibidos] AS vr
    ON vr.[Numero Valor] = vrc.[Nro Documento]
   AND vr.[Fecha Endoso] = vrc.Fecha
   AND vr.IdEmisor = vrc.IdContacto
   AND vr.Destino = 'Endoso a tercero'

UNION ALL

SELECT
    rig.Fecha,
    rig.IdContacto,
    rig.[Razon Social],
    rig.Documento,
    rig.[Nro Documento],
    CAST(rig.Deuda AS money) AS Deuda,
    CAST(rig.Credito AS money) AS Credito,
    CAST('Ret. IVA Granos' AS varchar(50)) AS Origen,
    rig.IdOrigen
FROM dbo.vw_CnsRetencionesIVAGranos AS rig

UNION ALL

SELECT
    r.Fecha,
    r.IdContacto,
    ct.[Razon Social],
    'Retención' AS Documento,
    r.[Numero Certificado] AS [Nro Documento],
    CAST(0 AS money) AS Deuda,
    CAST(r.Importe AS money) AS Credito,
    CAST('Retenciones' AS varchar(50)) AS Origen,
    CAST(r.IdRetencionSQL AS bigint) AS IdOrigen
FROM dbo.Retenciones AS r
INNER JOIN dbo.Contactos AS ct
    ON ct.IdContacto = r.IdContacto
WHERE r.IdContacto IS NOT NULL
  AND ISNULL(r.Importe, 0) <> 0

UNION ALL

SELECT
    rvh.Fecha,
    rvh.IdContacto,
    ct.[Razon Social],
    COALESCE(NULLIF(LTRIM(RTRIM(rvh.Documento)), ''), 'Retención Ventas Hacienda') AS Documento,
    rvh.[Nro Documento],
    CAST(rvh.Importe AS money) AS Deuda,
    CAST(0 AS money) AS Credito,
    CAST('Ret. Ventas Hacienda' AS varchar(50)) AS Origen,
    CAST(rvh.Id AS bigint) AS IdOrigen
FROM dbo.[Retenciones Ventas Hacienda] AS rvh
INNER JOIN dbo.Contactos AS ct
    ON ct.IdContacto = rvh.IdContacto
WHERE rvh.IdContacto IS NOT NULL
  AND ISNULL(rvh.Importe, 0) <> 0

UNION ALL

SELECT
    t.FechaCompra AS Fecha,
    c.IdContacto,
    ct.[Razon Social],
    'Tarjeta' AS Documento,
    CAST(rs.ResumenCodigo AS varchar(50)) AS [Nro Documento],
    CASE WHEN -ISNULL(v.ImporteImputado, 0) > 0 THEN -v.ImporteImputado ELSE 0 END AS Deuda,
    CASE WHEN -ISNULL(v.ImporteImputado, 0) < 0 THEN v.ImporteImputado ELSE 0 END AS Credito,
    CAST('Tarjetas' AS varchar(50)) AS Origen,
    CAST(v.IdVinculo AS bigint) AS IdOrigen
FROM dbo.Tarjetas_Resumenes_Lineas_Compras AS v
INNER JOIN dbo.Tarjetas_Resumenes_Lineas AS t
    ON t.IdLineaConsumo = v.IdLineaConsumo
LEFT JOIN dbo.Tarjetas_Resumenes AS rs
    ON rs.IdResumen = t.IdResumen
INNER JOIN dbo.Compras AS c
    ON c.IdDeuda = v.IdCompra
INNER JOIN dbo.vw_Cns_Total_Compra AS tc
    ON tc.IdDeuda = c.IdDeuda
INNER JOIN dbo.Contactos AS ct
    ON ct.IdContacto = c.IdContacto
WHERE ISNULL(v.ImporteImputado, 0) <> 0

UNION ALL

SELECT
    COALESCE(b.[Fecha / Hora Mov#], g.Fecha, ml.Fecha, pe.Fecha, vp.[Fecha emision], vr.[Fecha Emision]) AS Fecha,
    ct.IdContacto,
    co.[Razon Social],
    'Conciliación Tesorería' AS Documento,
    CAST(ct.IdMovimiento AS varchar(50)) AS [Nro Documento],
    CASE
        WHEN ct.Medio = 'bna' AND ISNULL(b.Importe, 0) > 0 THEN ct.Importe
        WHEN ct.Medio = 'galicia' AND ISNULL(g.[Créditos], 0) > ISNULL(g.[Débitos], 0) THEN ct.Importe
        WHEN ct.Medio = 'mercado-libre' AND ISNULL(ml.Importe, 0) > 0 THEN ct.Importe
        ELSE 0
    END AS Deuda,
    CASE
        WHEN ct.Medio = 'bna' AND ISNULL(b.Importe, 0) < 0 THEN ct.Importe
        WHEN ct.Medio = 'galicia' AND ISNULL(g.[Débitos], 0) > ISNULL(g.[Créditos], 0) THEN ct.Importe
        WHEN ct.Medio = 'mercado-libre' AND ISNULL(ml.Importe, 0) < 0 THEN ct.Importe
        WHEN ct.Medio IN ('efectivo', 'valores-propios', 'valores-recibidos') THEN ct.Importe
        ELSE 0
    END AS Credito,
    CAST('Conciliación Tesorería' AS varchar(50)) AS Origen,
    CAST(ct.IdConciliacion AS bigint) AS IdOrigen
FROM dbo.ConciliacionesTesoreria AS ct
INNER JOIN dbo.Contactos AS co ON co.IdContacto = ct.IdContacto
LEFT JOIN dbo.[Movimientos BNA] AS b ON ct.Medio = 'bna' AND b.IdMovimientoBNA = ct.IdMovimiento
LEFT JOIN dbo.[Movimientos Galicia] AS g ON ct.Medio = 'galicia' AND g.IdMovimiento = ct.IdMovimiento
LEFT JOIN dbo.[Movimientos Mercado Libre] AS ml ON ct.Medio = 'mercado-libre' AND ml.IdMovimiento = ct.IdMovimiento
LEFT JOIN dbo.[Pagos efectivo] AS pe ON ct.Medio = 'efectivo' AND pe.IdPagoEfectivo = ct.IdMovimiento
LEFT JOIN dbo.[Valores propios] AS vp ON ct.Medio = 'valores-propios' AND vp.IdValor = ct.IdMovimiento
LEFT JOIN dbo.[Valores Recibidos] AS vr ON ct.Medio = 'valores-recibidos' AND vr.IdValor = ct.IdMovimiento

UNION ALL

SELECT
    v.Fecha,
    v.IdConsignatario AS IdContacto,
    ct.[Razon Social],
    'Venta Granos' AS Documento,
    v.[Nro Documento] AS [Nro Documento],
    CAST(0 AS money) AS Deuda,
    CAST(
        (
            (CAST(ISNULL(v.[Cantidad vendida], 0) AS float)
                * ((CAST(ISNULL(v.[Precio unitario], 0) AS float) * CAST(ISNULL(v.Factor, 100) AS float) / 100.0
                    - CAST(ISNULL(v.Flete, 0) AS float)) / 1000.0))
            + ISNULL(aj.SumaAjustes, 0)
        ) * (1 + CAST(ISNULL(v.AlicuotaIVA, 0) AS float) / 100.0)
        - (CAST(ISNULL(v.[Ret IG], 0) AS float) + CAST(ISNULL(v.[Retencion IVA], 0) AS float)
            + CAST(ISNULL(v.Percepciones, 0) AS float) + CAST(ISNULL(v.[Otra Retenciones], 0) AS float))
        - ISNULL(ded.TotalDeducciones, 0)
    AS money) AS Credito,
    CAST('Venta Granos' AS varchar(50)) AS Origen,
    CAST(v.IdVenta AS bigint) AS IdOrigen
FROM dbo.[Venta Granos] AS v
INNER JOIN dbo.Contactos AS ct
    ON ct.IdContacto = v.IdConsignatario
OUTER APPLY (
    SELECT SUM(CAST(a.Importe AS float)) AS SumaAjustes
    FROM dbo.[Venta Granos_Ajustes] a
    WHERE a.IdVenta = v.IdVenta
) AS aj
OUTER APPLY (
    SELECT SUM(
        (CAST(d.[Base Calculo] AS float) * CAST(ISNULL(d.Porc, 0) AS float) / 100.0)
        + (CAST(d.[Base Calculo] AS float) * CAST(ISNULL(d.Porc, 0) AS float) / 100.0)
            * CAST(ISNULL(d.Alicuota, 0) AS float) / 100.0
    ) AS TotalDeducciones
    FROM dbo.[Venta Granos_Deducciones] d
    WHERE d.IdVenta = v.IdVenta
) AS ded
WHERE v.IdConsignatario IS NOT NULL


UNION ALL

SELECT
    v.Fecha,
    v.IdConsignatario AS IdContacto,
    ct.[Razon Social],
    'Venta Hacienda' AS Documento,
    v.[Nro documento] AS [Nro Documento],
    CAST(0 AS money) AS Deuda,
    CAST(
        (ISNULL(subtotal.Total, 0) - (ISNULL(subtotal.Total, 0) * ISNULL(v.[Porc Comision], 0) / 100.0)
            - ISNULL(v.[Gs Vs No Gravados], 0))
        * (1 + ISNULL(v.AlicuotaIVA, 0) / 100.0)
        - ISNULL(v.[Ley de Sellos], 0) - ISNULL(v.[Vis Municipal], 0) - ISNULL(v.Balanza, 0)
        - ISNULL(v.Flete, 0) - ISNULL(v.[Gastos Varios], 0) - ISNULL(v.[Retencion Ganancias], 0)
        - ISNULL(v.[Retencion IVA], 0) - ISNULL(v.[Ingresos Brutos], 0) + ISNULL(v.Complemento, 0)
    AS money) AS Credito,
    CAST('Venta Hacienda' AS varchar(50)) AS Origen,
    CAST(v.IdVenta AS bigint) AS IdOrigen
FROM dbo.[Venta Hacienda] AS v
INNER JOIN dbo.Contactos AS ct
    ON ct.IdContacto = v.IdConsignatario
CROSS APPLY (
    SELECT SUM(d.Cantidad * (ISNULL(d.[Precio unitario (A)], 0) + ISNULL(d.[Precio unitario (B)], 0))) AS Total
    FROM dbo.[Det_Ventas Hacienda] d
    WHERE d.IdVenta = v.IdVenta
) AS subtotal
WHERE v.IdConsignatario IS NOT NULL


UNION ALL

SELECT
    sc.FechaCobro AS Fecha,
    c.IdContacto,
    ct.[Razon Social],
    CAST('Cobro Seguro' AS varchar(50)) AS Documento,
    CAST(sc.NroSiniestro AS varchar(50)) AS [Nro Documento],
    CAST(0 AS money) AS Deuda,
    CAST(sc.ImportePesos AS money) AS Credito,
    CAST('Cobro Seguro' AS varchar(50)) AS Origen,
    CAST(sc.IdSeguroCobro AS bigint) AS IdOrigen
FROM dbo.Cultivos_Seguros_Cobros AS sc
INNER JOIN dbo.Compras AS c ON c.IdDeuda = sc.IdDeuda
INNER JOIN dbo.Contactos AS ct ON ct.IdContacto = c.IdContacto
WHERE ISNULL(sc.ImportePesos, 0) <> 0

UNION ALL

SELECT
    CAST(aj.Fecha AS datetime) AS Fecha,
    aj.IdContacto,
    ct.[Razon Social],
    CAST('Ajuste Interno' AS varchar(50)) AS Documento,
    CAST(aj.IdAjuste AS varchar(50)) AS [Nro Documento],
    CASE WHEN aj.Lado = 'Deuda' THEN aj.Importe ELSE CAST(0 AS money) END AS Deuda,
    CASE WHEN aj.Lado = 'Credito' THEN aj.Importe ELSE CAST(0 AS money) END AS Credito,
    CAST('Ajuste Interno' AS varchar(50)) AS Origen,
    CAST(aj.IdAjuste AS bigint) AS IdOrigen
FROM dbo.AjustesCuentaCorriente AS aj
INNER JOIN dbo.Contactos AS ct ON ct.IdContacto = aj.IdContacto


UNION ALL

SELECT -- resto-linea-v2
    l.FechaCompra AS Fecha,
    l.IdContacto,
    ct.[Razon Social],
    CAST('Tarjeta sin imputar' AS varchar(50)) AS Documento,
    CAST(rs.ResumenCodigo AS varchar(50)) AS [Nro Documento],
    CASE WHEN x.resto < 0 THEN -x.resto ELSE CAST(0 AS money) END AS Deuda,
    CASE WHEN x.resto > 0 THEN x.resto ELSE CAST(0 AS money) END AS Credito,
    CAST('Tarjeta sin imputar' AS varchar(50)) AS Origen,
    CAST(l.IdLineaConsumo AS bigint) AS IdOrigen
FROM dbo.Tarjetas_Resumenes_Lineas AS l
INNER JOIN dbo.Contactos AS ct ON ct.IdContacto = l.IdContacto
LEFT JOIN dbo.Tarjetas_Resumenes AS rs ON rs.IdResumen = l.IdResumen
CROSS APPLY (
    SELECT CAST(ISNULL(l.Importe, 0) - ISNULL((
        SELECT SUM(v.ImporteImputado)
        FROM dbo.Tarjetas_Resumenes_Lineas_Compras AS v
        WHERE v.IdLineaConsumo = l.IdLineaConsumo
    ), 0) AS money) AS resto
) AS x
WHERE ABS(x.resto) > 0.005


UNION ALL

SELECT
    CAST(ms.Fecha AS datetime) AS Fecha,
    psp.IdContacto,
    ct.[Razon Social],
    CAST('Pago por socio' AS varchar(50)) AS Documento,
    CAST(so.Nombre AS varchar(50)) AS [Nro Documento],
    CAST(0 AS money) AS Deuda,
    CAST(ms.Importe AS money) AS Credito,
    CAST('Pago por socio' AS varchar(50)) AS Origen,
    CAST(ms.IdMovimiento AS bigint) AS IdOrigen
FROM dbo.PagosSocioProveedor AS psp
INNER JOIN dbo.MovimientosCuentaSocio AS ms ON ms.IdMovimiento = psp.IdMovimientoSocio AND ms.Anulada = 0
INNER JOIN dbo.Socios AS so ON so.IdSocio = ms.IdSocio
INNER JOIN dbo.Contactos AS ct ON ct.IdContacto = psp.IdContacto
WHERE ISNULL(ms.Importe, 0) > 0


UNION ALL

SELECT
    t.FechaCompra AS Fecha,
    i.IdOrganismo AS IdContacto,
    ct.[Razon Social],
    CAST('Tarjeta' AS varchar(50)) AS Documento,
    CAST(rs.ResumenCodigo AS varchar(50)) AS [Nro Documento],
    CASE WHEN v.ImporteImputado < 0 THEN -v.ImporteImputado ELSE CAST(0 AS money) END AS Deuda,
    CASE WHEN v.ImporteImputado > 0 THEN v.ImporteImputado ELSE CAST(0 AS money) END AS Credito,
    CAST('Tarjeta impuesto' AS varchar(50)) AS Origen,
    CAST(v.IdVinculo AS bigint) AS IdOrigen
FROM dbo.Tarjetas_Resumenes_Lineas_Compras AS v
INNER JOIN dbo.Tarjetas_Resumenes_Lineas AS t ON t.IdLineaConsumo = v.IdLineaConsumo
LEFT JOIN dbo.Tarjetas_Resumenes AS rs ON rs.IdResumen = t.IdResumen
INNER JOIN dbo.Impuestos AS i ON i.IdImpuesto = v.IdImpuesto
INNER JOIN dbo.Contactos AS ct ON ct.IdContacto = i.IdOrganismo
WHERE v.IdImpuesto IS NOT NULL AND ISNULL(v.ImporteImputado, 0) <> 0


UNION ALL

SELECT
    l.FechaCompra AS Fecha,
    tc.IdContacto AS IdContacto,
    ct.[Razon Social],
    CAST('Consumo tarjeta' AS varchar(50)) AS Documento,
    CAST(rs.ResumenCodigo AS varchar(50)) AS [Nro Documento],
    CASE WHEN ISNULL(l.Importe, 0) > 0 THEN CAST(l.Importe AS money) ELSE CAST(0 AS money) END AS Deuda,
    CASE WHEN ISNULL(l.Importe, 0) < 0 THEN CAST(-l.Importe AS money) ELSE CAST(0 AS money) END AS Credito,
    CAST('Tarjeta consumo' AS varchar(50)) AS Origen,
    CAST(l.IdLineaConsumo AS bigint) AS IdOrigen
FROM dbo.Tarjetas_Resumenes_Lineas AS l
INNER JOIN dbo.Tarjetas_Resumenes AS rs ON rs.IdResumen = l.IdResumen
INNER JOIN dbo.TarjetasContacto AS tc ON tc.IdTarjeta = rs.IdTarjeta
INNER JOIN dbo.Contactos AS ct ON ct.IdContacto = tc.IdContacto
WHERE ISNULL(rs.EstadoResumen, '') <> 'Cerrado' AND ISNULL(l.Importe, 0) <> 0


UNION ALL

SELECT
    rs.FechaCierre AS Fecha,
    tc.IdContacto AS IdContacto,
    ct.[Razon Social],
    CAST(cg.Nombre AS varchar(50)) AS Documento,
    CAST(rs.ResumenCodigo AS varchar(50)) AS [Nro Documento],
    CASE WHEN cg.Importe > 0 THEN CAST(cg.Importe AS money) ELSE CAST(0 AS money) END AS Deuda,
    CASE WHEN cg.Importe < 0 THEN CAST(-cg.Importe AS money) ELSE CAST(0 AS money) END AS Credito,
    CAST('Tarjeta cargo' AS varchar(50)) AS Origen,
    CAST(rs.IdResumen * 100 + cg.N AS bigint) AS IdOrigen
FROM dbo.Tarjetas_Resumenes AS rs
INNER JOIN dbo.TarjetasContacto AS tc ON tc.IdTarjeta = rs.IdTarjeta
INNER JOIN dbo.Contactos AS ct ON ct.IdContacto = tc.IdContacto
CROSS APPLY (VALUES
        (1, N'Impuesto de sellos', rs.ImpuestoSellos),
        (2, N'Gastos administrativos', rs.GastosAdmin),
        (3, N'Mantenimiento de cuenta', rs.MantCuenta),
        (4, N'Renovación anual', rs.RenovAnual),
        (5, N'Promoción BNA', rs.PromocionBNA),
        (6, N'Crédito contingente', rs.CreditoContingente),
        (7, N'Interés financiero', rs.IntFinanc),
        (8, N'Interés compensatorio', rs.IntCompens),
        (9, N'IVA 10,5%', rs.IVA105),
        (10, N'Percepción IVA 10,5%', rs.PercepIVA105),
        (11, N'IVA 21%', rs.IVA21),
        (12, N'Percepción IVA 21%', rs.PercepIVA21),
        (13, N'Percepción IIBB', rs.PercepIIBB),
        (14, N'Ajuste resumen anterior', rs.AjusteResAnterior)
    ) AS cg (N, Nombre, Importe)
WHERE ISNULL(rs.EstadoResumen, '') <> 'Cerrado' AND ISNULL(cg.Importe, 0) <> 0


UNION ALL

SELECT
    m.Fecha AS Fecha,
    tc.IdContacto AS IdContacto,
    ct.[Razon Social],
    CAST('Devolución tarjeta' AS varchar(50)) AS Documento,
    CAST(x.IdCruce AS varchar(50)) AS [Nro Documento],
    CAST(x.Importe AS money) AS Deuda,
    CAST(0 AS money) AS Credito,
    CAST('Tarjeta devolución' AS varchar(50)) AS Origen,
    CAST(x.IdCruce AS bigint) AS IdOrigen
FROM dbo.TarjetasCruces AS x
INNER JOIN dbo.TarjetasContacto AS tc ON tc.IdTarjeta = x.IdTarjeta
INNER JOIN dbo.Contactos AS ct ON ct.IdContacto = tc.IdContacto
CROSS APPLY (
    SELECT TOP 1 f.Fecha FROM (
        SELECT b.[Fecha / Hora Mov#] AS Fecha FROM dbo.[Movimientos BNA] AS b
        WHERE x.MedioOrigen = 'bna' AND b.IdMovimientoBNA = x.IdMovimientoOrigen
        UNION ALL
        SELECT g.Fecha AS Fecha FROM dbo.[Movimientos Galicia] AS g
        WHERE x.MedioOrigen = 'galicia' AND g.IdMovimiento = x.IdMovimientoOrigen
    ) AS f
) AS m
WHERE x.Tipo = 'devolucion-debito' AND x.Deshecho = 0


UNION ALL

SELECT
    p.Fecha AS Fecha,
    tc.IdContacto AS IdContacto,
    ct.[Razon Social],
    CAST('Pago tarjeta sin movimiento' AS varchar(50)) AS Documento,
    CAST(rs.ResumenCodigo AS varchar(50)) AS [Nro Documento],
    CAST(0 AS money) AS Deuda,
    CAST(p.Importe AS money) AS Credito,
    CAST('Tarjeta pago' AS varchar(50)) AS Origen,
    CAST(p.IdPago AS bigint) AS IdOrigen
FROM dbo.Tarjetas_Resumenes_Pagos AS p
INNER JOIN dbo.Tarjetas_Resumenes AS rs ON rs.IdResumen = p.IdResumen
INNER JOIN dbo.TarjetasContacto AS tc ON tc.IdTarjeta = rs.IdTarjeta
INNER JOIN dbo.Contactos AS ct ON ct.IdContacto = tc.IdContacto
WHERE p.IdMovimientoOrigen IS NULL AND ISNULL(p.Importe, 0) <> 0 AND ISNULL(rs.EstadoResumen, '') <> 'Cerrado'


UNION ALL

SELECT
    CAST(m.Fecha AS datetime) AS Fecha,
    m.IdContacto AS IdContacto,
    ct.[Razon Social],
    CAST('Mercado Pago' AS varchar(50)) AS Documento,
    CAST(m.IdOperacion AS varchar(50)) AS [Nro Documento],
    CASE WHEN ISNULL(m.Importe, 0) > 0 THEN CAST(m.Importe AS money) ELSE CAST(0 AS money) END AS Deuda,
    CASE WHEN ISNULL(m.Importe, 0) < 0 THEN CAST(-m.Importe AS money) ELSE CAST(0 AS money) END AS Credito,
    CAST('Mercado Pago' AS varchar(50)) AS Origen,
    CAST(m.IdMovimiento AS bigint) AS IdOrigen
FROM dbo.[Movimientos Mercado Libre] AS m
INNER JOIN dbo.Contactos AS ct ON ct.IdContacto = m.IdContacto
WHERE m.IdContacto IS NOT NULL AND ISNULL(m.Importe, 0) <> 0
  AND NOT EXISTS (SELECT 1 FROM dbo.ConciliacionesTesoreria AS c
                  WHERE c.Medio = 'mercado-libre' AND c.IdMovimiento = m.IdMovimiento)
  AND NOT EXISTS (SELECT 1 FROM dbo.[Movimientos Mercado Libre] AS i
                  WHERE i.IdOperacion = m.IdOperacion AND i.IdMovimiento <> m.IdMovimiento
                    AND i.Descripcion LIKE N'Ingreso de dinero%' AND i.Fecha = m.Fecha
                    AND ABS(i.Importe + m.Importe) < 0.01)


) AS base
OUTER APPLY (
    SELECT TOP 1 r.IdContactoNuevo
    FROM dbo.ReasignacionesContacto r
    WHERE r.Origen = base.Origen AND r.IdOrigen = base.IdOrigen
    ORDER BY r.IdReasignacion DESC
) AS ov
LEFT JOIN dbo.Contactos AS ctov ON ctov.IdContacto = ov.IdContactoNuevo;
