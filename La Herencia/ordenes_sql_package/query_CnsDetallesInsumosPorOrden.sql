SELECT
    OD.IdDetalleOrden,
    OD.IdOrden,
    OD.IdPlanAgricola,
    OD.IdFormulado,
    OD.IdCultivo,
    OD.IdLote,
    L.[Numero Lote],
    CDbl(Nz(L.Superficie,0)) AS Superficie,
    CDbl(Nz(OD.[Dosis Teorica],0)) AS [Dosis Teorica],
    CDbl(Nz(L.Superficie,0)) * CDbl(Nz(OD.[Dosis Teorica],0)) AS [Cantidad Requerida],
    CDbl(Nz(OD.[Total Aplicado],0)) AS [Total Aplicado],
    OD.Unidad,
    OD.Observaciones
FROM
    Ordenes_Detalles AS OD
    INNER JOIN Lotes AS L ON OD.IdLote = L.IdLote
WHERE
    OD.IdOrden = [TempVars]![IdOrden]
    AND OD.IdFormulado Is Not Null
ORDER BY
    OD.IdDetalleOrden;