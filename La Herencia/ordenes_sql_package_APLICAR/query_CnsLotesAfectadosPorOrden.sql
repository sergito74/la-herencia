INSERT INTO Ordenes_Detalles (IdOrden, IdPlanAgricola, IdCultivo, IdLote)
SELECT [TempVars]![IdOrden], PA.IdPlanAgricola, PA.IdCultivo, PA.IdLote
FROM PlanAgricola AS PA
WHERE
    ( [TempVars]![IdCampaña] Is Null OR [TempVars]![IdCampaña]=0 OR PA.IdCampaña = [TempVars]![IdCampaña] )
    AND ( [TempVars]![IdCultivo] Is Null OR [TempVars]![IdCultivo]=0 OR PA.IdCultivo = [TempVars]![IdCultivo] )
    AND NOT EXISTS (
        SELECT * FROM Ordenes_Detalles AS OD
        WHERE OD.IdOrden = [TempVars]![IdOrden]
          AND OD.IdPlanAgricola = PA.IdPlanAgricola
    );