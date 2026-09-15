SELECT
    B.IdCultivo,
    C.Cultivo,
    Nz(
        (
            SELECT Sum(Nz(OD.[Total Aplicado],0))
            FROM Ordenes_Detalles AS OD
            WHERE OD.IdOrden = [TempVars]![IdOrden]
              AND OD.IdFormulado = [TempVars]![IdFormulado]
              AND OD.IdCultivo = B.IdCultivo
        ),0) AS CantAplicada,
    Nz(
        (
            SELECT TOP 1 OD2.Unidad
            FROM Ordenes_Detalles AS OD2
            WHERE OD2.IdOrden = [TempVars]![IdOrden]
              AND OD2.IdFormulado = [TempVars]![IdFormulado]
              AND OD2.IdCultivo = B.IdCultivo
            GROUP BY OD2.Unidad
        ),'') AS Unidad
FROM
    (SELECT DISTINCT IdCultivo
     FROM Ordenes_Detalles
     WHERE IdOrden = [TempVars]![IdOrden]
       AND IdCultivo Is Not Null) AS B
    INNER JOIN Cultivos AS C ON B.IdCultivo = C.IdCultivo
ORDER BY C.Cultivo;