
Attribute VB_Name = "basInitOrdenes"
Option Compare Database
Option Explicit

Public Sub Ordenes_InitTempVars()
    On Error Resume Next
    [TempVars]![IdOrden] = Nz([TempVars]![IdOrden], 0)
    [TempVars]![IdFormulado] = Nz([TempVars]![IdFormulado], 0)
    [TempVars]![IdCampaña] = Nz([TempVars]![IdCampaña], 0)
    [TempVars]![IdCultivo] = Nz([TempVars]![IdCultivo], 0)
End Sub
