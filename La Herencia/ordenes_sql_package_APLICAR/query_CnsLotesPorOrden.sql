SELECT
    OD.IdDetalleOrden,
    OD.IdOrden,
    OD.IdPlanAgricola,
    OD.IdCultivo,
    OD.IdLote,
    C.Cultivo,
    L.[Numero Lote] AS NumeroLote,
    L.Superficie,
    Nz(OD.Aplicar,0) AS Aplicar
FROM
    ((Ordenes_Detalles AS OD
      INNER JOIN Lotes AS L ON OD.IdLote = L.IdLote)
      INNER JOIN PlanAgricola AS PA ON OD.IdPlanAgricola = PA.IdPlanAgricola)
      INNER JOIN Cultivos AS C ON OD.IdCultivo = C.IdCultivo
WHERE
    OD.IdOrden = [TempVars]![IdOrden]
ORDER BY
    C.Cultivo, L.[Numero Lote];