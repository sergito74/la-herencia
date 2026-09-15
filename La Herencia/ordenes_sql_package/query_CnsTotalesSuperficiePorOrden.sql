SELECT
    C.Cultivo,
    Sum(L.Superficie) AS [Superficie Afectada]
FROM
    (Ordenes_Detalles AS OD
     INNER JOIN Lotes AS L ON OD.IdLote = L.IdLote)
     INNER JOIN Cultivos AS C ON OD.IdCultivo = C.IdCultivo
WHERE
    OD.IdOrden = [TempVars]![IdOrden]
    AND Nz(OD.Aplica,0) <> 0
GROUP BY
    C.Cultivo
UNION ALL
SELECT
    'Total' AS Cultivo,
    Sum(L2.Superficie)
FROM
    Ordenes_Detalles AS OD2
    INNER JOIN Lotes AS L2 ON OD2.IdLote = L2.IdLote
WHERE
    OD2.IdOrden = [TempVars]![IdOrden]
    AND Nz(OD2.Aplica,0) <> 0;