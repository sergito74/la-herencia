Attribute VB_Name = "basOneShot_PerfFix"
Option Compare Database
Option Explicit

' ================================================================
' basOneShot_PerfFix  -  Correcciones de performance FrmOrdenTrabajo
' INSTRUCCIONES:
'   1. Importar este .bas en Access (Alt+F11 -> Archivo -> Importar)
'   2. En la ventana Inmediato escribir:  OneShot_PerfFix_Apply
'   3. Seguir las instrucciones en pantalla
'   4. Eliminar este modulo al terminar
' ================================================================

Private Const THIS_MODULE As String = "basOneShot_PerfFix"
Private Const TMP_FOLDER  As String = "_perffix"

' ================================================================
' PUNTO DE ENTRADA
' ================================================================
Public Sub OneShot_PerfFix_Apply()
    On Error GoTo EH

    Dim msg As String
    msg = "Se aplicaran las siguientes correcciones de performance:" & vbCrLf & vbCrLf & _
          "1. basUIHelpers: SafeRequerySub corregida (sin requery masivo)" & vbCrLf & _
          "2. basAsignaInsumos: DCount -> RecordsAffected, DSum -> subquery" & vbCrLf & _
          "3. Frm OrdenTrabajo: DoCmd.Echo False/True en btnAgregarInsumo y lstInsumosOrden" & vbCrLf & _
          "4. sfDistribDetalle: DoCmd.GoToRecord comentado en IrASiguienteDosis" & vbCrLf & vbCrLf & _
          "IMPORTANTE: las formas deben estar CERRADAS al ejecutar esto." & vbCrLf & _
          "Se creara backup en la carpeta _perffix antes de cada cambio." & vbCrLf & vbCrLf & _
          "Continuar?"
    If MsgBox(msg, vbYesNo + vbQuestion, "PerfFix") = vbNo Then Exit Sub

    Dim tmpDir As String: tmpDir = CurrentProject.path & "\" & TMP_FOLDER
    PF_EnsureFolder tmpDir

    Dim log As String: log = "== PerfFix aplicado " & Now() & " ==" & vbCrLf

    ' --- 1. Reemplazar basUIHelpers ---
    Dim r1 As String
    r1 = PF_ReplaceModule("basUIHelpers", PF_GetUIHelpersCode(), tmpDir)
    log = log & r1 & vbCrLf
    Debug.Print r1

    ' --- 2. Reemplazar basAsignaInsumos ---
    Dim r2 As String
    r2 = PF_ReplaceModule("basAsignaInsumos", PF_GetAsignaInsumosCode(), tmpDir)
    log = log & r2 & vbCrLf
    Debug.Print r2

    ' --- 3. Parchear Frm OrdenTrabajo (Echo en click handlers) ---
    Dim r3 As String
    r3 = PF_PatchFormEcho("Frm OrdenTrabajo", _
                          Array("btnAgregarInsumo_Click", "lstInsumosOrden_AfterUpdate"), _
                          tmpDir)
    log = log & r3 & vbCrLf
    Debug.Print r3

    ' --- 4. Parchear sfDistribDetalle (comentar GoToRecord) ---
    Dim r4 As String
    r4 = PF_PatchFormGoToRecord("sfDistribDetalle", "IrASiguienteDosis", tmpDir)
    log = log & r4 & vbCrLf
    Debug.Print r4

    ' Guardar log
    PF_WriteAllText tmpDir & "\PerfFix_log.txt", log

    MsgBox "PerfFix completado." & vbCrLf & vbCrLf & log & vbCrLf & _
           "Podes eliminar el modulo basOneShot_PerfFix cuando quieras.", _
           vbInformation, "PerfFix"
    Exit Sub
EH:
    DoCmd.Echo True
    MsgBox "ERROR en OneShot_PerfFix_Apply: " & Err.Number & " - " & Err.Description, vbCritical
End Sub

' ================================================================
' REEMPLAZO DE MODULOS
' ================================================================
Private Function PF_ReplaceModule(modName As String, code As String, tmpDir As String) As String
    On Error GoTo EH
    Dim p As String: p = tmpDir & "\" & modName & "_backup.txt"

    ' Backup del modulo actual si existe
    On Error Resume Next
    Application.SaveAsText acModule, modName, p
    On Error GoTo EH

    ' Guardar nuevo codigo
    Dim newPath As String: newPath = tmpDir & "\" & modName & "_new.txt"
    PF_WriteAllText newPath, code

    ' Eliminar modulo viejo (si existe)
    On Error Resume Next
    DoCmd.DeleteObject acModule, modName
    Err.Clear
    On Error GoTo EH

    ' Importar nuevo
    Application.LoadFromText acModule, modName, newPath

    PF_ReplaceModule = "OK  - " & modName & " reemplazado"
    Exit Function
EH:
    PF_ReplaceModule = "ERR - " & modName & ": " & Err.Number & " - " & Err.Description
End Function

' ================================================================
' PARCHE ECHO EN FORM (inyecta DoCmd.Echo False/True en handlers)
' ================================================================
Private Function PF_PatchFormEcho(formName As String, subNames As Variant, tmpDir As String) As String
    On Error GoTo EH

    ' Verificar que el formulario este cerrado
    Dim isOpen As Boolean: isOpen = False
    On Error Resume Next
    isOpen = (Application.SysCmd(acSysCmdGetObjectState, acForm, formName) And acObjStateOpen) <> 0
    On Error GoTo EH

    If isOpen Then
        PF_PatchFormEcho = "SKIP - " & formName & " esta abierto; cerrarlo y re-ejecutar"
        Exit Function
    End If

    ' Exportar forma
    Dim bakPath As String: bakPath = tmpDir & "\" & Replace(formName, " ", "_") & "_backup.txt"
    Application.SaveAsText acForm, formName, bakPath

    ' Leer texto
    Dim txt As String: txt = PF_ReadAllText(bakPath)

    ' Aplicar parche a cada Sub
    Dim i As Long, patchCount As Long
    For i = 0 To UBound(subNames)
        Dim subName As String: subName = subNames(i)
        Dim patched As String
        patched = PF_InjectEchoInProc(txt, subName)
        If patched <> txt Then
            txt = patched
            patchCount = patchCount + 1
            Debug.Print "  Parcheado: " & subName & " en " & formName
        Else
            Debug.Print "  Sin cambios (no encontrado o ya parcheado): " & subName
        End If
    Next i

    If patchCount = 0 Then
        PF_PatchFormEcho = "SKIP - " & formName & ": ninguna Sub encontrada para parchar (puede que ya este aplicado)"
        Exit Function
    End If

    ' Guardar texto parcheado
    Dim newPath As String: newPath = tmpDir & "\" & Replace(formName, " ", "_") & "_patched.txt"
    PF_WriteAllText newPath, txt

    ' Reimportar forma
    DoCmd.Close acForm, formName, acSaveNo
    Application.LoadFromText acForm, formName, newPath

    PF_PatchFormEcho = "OK  - " & formName & ": " & patchCount & " Sub(s) parcheadas con Echo"
    Exit Function
EH:
    PF_PatchFormEcho = "ERR - " & formName & ": " & Err.Number & " - " & Err.Description
End Function

' ================================================================
' Inyecta DoCmd.Echo False al inicio y DoCmd.Echo True al final de una Sub
' ================================================================
Private Function PF_InjectEchoInProc(ByVal txt As String, ByVal procName As String) As String
    Const ECHO_OFF As String = "    DoCmd.Echo False"
    Const ECHO_ON  As String = "    DoCmd.Echo True"

    ' Buscar la declaracion de la Sub (acepta Private/Public/Friend + Sub nombre()
    Dim patterns(3) As String
    patterns(0) = "Private Sub " & procName & "("
    patterns(1) = "Public Sub "  & procName & "("
    patterns(2) = "Friend Sub "  & procName & "("
    patterns(3) = "Sub "         & procName & "("

    Dim pStart As Long, i As Long
    pStart = 0
    For i = 0 To 3
        pStart = InStr(1, txt, patterns(i), vbTextCompare)
        If pStart > 0 Then Exit For
    Next i
    If pStart = 0 Then
        PF_InjectEchoInProc = txt  ' Sub no encontrada
        Exit Function
    End If

    ' Verificar que no este ya parcheado
    Dim look As String: look = Mid$(txt, pStart, 300)
    If InStr(1, look, "DoCmd.Echo False", vbTextCompare) > 0 Then
        PF_InjectEchoInProc = txt  ' Ya parcheado
        Exit Function
    End If

    ' Encontrar el fin de linea de la declaracion
    Dim pDeclEnd As Long: pDeclEnd = InStr(pStart, txt, vbCrLf)
    If pDeclEnd = 0 Then pDeclEnd = InStr(pStart, txt, vbLf)
    If pDeclEnd = 0 Then
        PF_InjectEchoInProc = txt
        Exit Function
    End If
    pDeclEnd = pDeclEnd + Len(vbCrLf) - 1  ' apunta al ultimo char del CRLF

    ' Encontrar el End Sub correspondiente (primera ocurrencia despues del inicio)
    ' Buscamos "End Sub" al comienzo de linea dentro del cuerpo
    Dim pBody As Long: pBody = pDeclEnd + 1
    Dim pEndSub As Long

    Dim searchPos As Long: searchPos = pBody
    Do
        Dim candidate As Long
        candidate = InStr(searchPos, txt, "End Sub", vbTextCompare)
        If candidate = 0 Then
            PF_InjectEchoInProc = txt  ' no encontrado
            Exit Function
        End If
        ' Verificar que este al comienzo de linea (con posibles espacios)
        Dim lineStart As Long
        lineStart = candidate
        Do While lineStart > 1 And Mid$(txt, lineStart - 1, 1) <> vbLf And Mid$(txt, lineStart - 1, 1) <> Chr(13)
            lineStart = lineStart - 1
        Loop
        Dim linePrefix As String: linePrefix = Mid$(txt, lineStart, candidate - lineStart)
        If Trim$(linePrefix) = "" Then
            pEndSub = candidate
            Exit Do
        End If
        searchPos = candidate + 7
    Loop

    ' ---- Construir el texto modificado ----
    ' Parte 1: hasta el fin de la linea de declaracion
    Dim part1 As String: part1 = Left$(txt, pDeclEnd)

    ' Parte 2: cuerpo de la Sub hasta End Sub (exclusive)
    Dim body As String: body = Mid$(txt, pDeclEnd + 1, pEndSub - pDeclEnd - 1)

    ' Parte 3: "End Sub" en adelante
    Dim part3 As String: part3 = Mid$(txt, pEndSub)

    ' -- Inyectar Echo False como primera linea del cuerpo --
    Dim newBody As String
    newBody = vbCrLf & ECHO_OFF & vbCrLf & body

    ' -- Reemplazar cada "Exit Sub" por Echo True + Exit Sub --
    newBody = PF_ReplaceExitSub(newBody, ECHO_ON)

    ' -- Inyectar Echo True antes del End Sub --
    ' (part3 empieza con "End Sub")
    Dim part3mod As String: part3mod = ECHO_ON & vbCrLf & part3

    PF_InjectEchoInProc = part1 & newBody & part3mod
End Function

' Reemplaza "Exit Sub" por "EchoOn + Exit Sub" dentro de un bloque de texto
Private Function PF_ReplaceExitSub(ByVal s As String, ByVal echoLine As String) As String
    Dim result As String: result = s
    Dim pos As Long: pos = 1
    Do
        pos = InStr(pos, result, "Exit Sub", vbTextCompare)
        If pos = 0 Then Exit Do
        ' Verificar que no este ya precedido por Echo True (evitar duplicados)
        Dim lookback As String
        lookback = Mid$(result, IIf(pos > 50, pos - 50, 1), IIf(pos > 50, 50, pos - 1))
        If InStr(1, lookback, "DoCmd.Echo True", vbTextCompare) = 0 Then
            result = Left$(result, pos - 1) & echoLine & vbCrLf & "    " & Mid$(result, pos)
            pos = pos + Len(echoLine) + Len(vbCrLf) + 4 + Len("Exit Sub")
        Else
            pos = pos + Len("Exit Sub")
        End If
    Loop
    PF_ReplaceExitSub = result
End Function

' ================================================================
' PARCHE GoToRecord EN sfDistribDetalle
' Comenta la linea "DoCmd.GoToRecord , , acNext" dentro de IrASiguienteDosis
' ================================================================
Private Function PF_PatchFormGoToRecord(formName As String, procName As String, tmpDir As String) As String
    On Error GoTo EH

    Dim isOpen As Boolean: isOpen = False
    On Error Resume Next
    isOpen = (Application.SysCmd(acSysCmdGetObjectState, acForm, formName) And acObjStateOpen) <> 0
    On Error GoTo EH

    If isOpen Then
        PF_PatchFormGoToRecord = "SKIP - " & formName & " esta abierto; cerrarlo y re-ejecutar"
        Exit Function
    End If

    Dim bakPath As String: bakPath = tmpDir & "\" & formName & "_backup.txt"
    Application.SaveAsText acForm, formName, bakPath

    Dim txt As String: txt = PF_ReadAllText(bakPath)

    ' Encontrar el proc IrASiguienteDosis y dentro de el buscar DoCmd.GoToRecord
    Dim pProc As Long: pProc = InStr(1, txt, "Sub " & procName & "(", vbTextCompare)
    If pProc = 0 Then
        PF_PatchFormGoToRecord = "SKIP - " & formName & ": " & procName & " no encontrada"
        Exit Function
    End If

    Dim pEndSub As Long: pEndSub = InStr(pProc, txt, "End Sub", vbTextCompare)
    If pEndSub = 0 Then
        PF_PatchFormGoToRecord = "SKIP - " & formName & ": End Sub no encontrado"
        Exit Function
    End If

    ' Buscar DoCmd.GoToRecord dentro del rango
    Dim pGTR As Long: pGTR = InStr(pProc, txt, "DoCmd.GoToRecord", vbTextCompare)
    If pGTR = 0 Or pGTR > pEndSub Then
        PF_PatchFormGoToRecord = "SKIP - " & formName & ": DoCmd.GoToRecord no encontrado en " & procName
        Exit Function
    End If

    ' Verificar que no este ya comentado
    Dim lineStart2 As Long: lineStart2 = pGTR
    Do While lineStart2 > 1 And Mid$(txt, lineStart2 - 1, 1) <> vbLf And Mid$(txt, lineStart2 - 1, 1) <> Chr(13)
        lineStart2 = lineStart2 - 1
    Loop
    Dim linePrefix2 As String: linePrefix2 = Mid$(txt, lineStart2, pGTR - lineStart2)
    If InStr(linePrefix2, "'") > 0 Then
        PF_PatchFormGoToRecord = "SKIP - " & formName & ": DoCmd.GoToRecord ya estaba comentado"
        Exit Function
    End If

    ' Comentar la linea: reemplazar la indentacion + DoCmd.GoToRecord por indentacion + ' DoCmd.GoToRecord
    Dim trimmedPrefix As String: trimmedPrefix = linePrefix2  ' espacios de indentacion
    txt = Left$(txt, lineStart2 - 1) & _
          trimmedPrefix & "' [PerfFix] " & Mid$(txt, pGTR)

    ' Guardar y reimportar
    Dim newPath As String: newPath = tmpDir & "\" & formName & "_patched.txt"
    PF_WriteAllText newPath, txt

    DoCmd.Close acForm, formName, acSaveNo
    Application.LoadFromText acForm, formName, newPath

    PF_PatchFormGoToRecord = "OK  - " & formName & ": DoCmd.GoToRecord comentado en " & procName
    Exit Function
EH:
    PF_PatchFormGoToRecord = "ERR - " & formName & ": " & Err.Number & " - " & Err.Description
End Function

' ================================================================
' CODIGO DE LOS MODULOS (strings embebidos)
' ================================================================
Private Function PF_GetUIHelpersCode() As String
    Dim s As String
    s = "Option Compare Database" & vbCrLf
    s = s & "Option Explicit" & vbCrLf & vbCrLf
    s = s & "' SafeRequeryCtrl: refresca el CONTROL subform (metodo correcto)." & vbCrLf
    s = s & "' .Requery sobre el control respeta Link Master/Child y evita eventos extra." & vbCrLf
    s = s & "Public Sub SafeRequeryCtrl(frmPadre As Form, ctrlName As String)" & vbCrLf
    s = s & "    On Error Resume Next" & vbCrLf
    s = s & "    frmPadre.Controls(ctrlName).Requery" & vbCrLf
    s = s & "    If Err.Number <> 0 Then" & vbCrLf
    s = s & "        Err.Clear" & vbCrLf
    s = s & "        Debug.Print ""SafeRequeryCtrl: control '"" & ctrlName & ""' no encontrado en "" & frmPadre.Name" & vbCrLf
    s = s & "    End If" & vbCrLf
    s = s & "    On Error GoTo 0" & vbCrLf
    s = s & "End Sub" & vbCrLf & vbCrLf
    s = s & "' SafeRequerySub: compatibilidad hacia atras." & vbCrLf
    s = s & "' Solo refresca el control pedido; NO hace fallback masivo." & vbCrLf
    s = s & "Public Sub SafeRequerySub(frmPadre As Form, subName As String)" & vbCrLf
    s = s & "    Call SafeRequeryCtrl(frmPadre, subName)" & vbCrLf
    s = s & "End Sub" & vbCrLf & vbCrLf
    s = s & "Public Sub EchoOff()" & vbCrLf
    s = s & "    DoCmd.Echo False" & vbCrLf
    s = s & "End Sub" & vbCrLf & vbCrLf
    s = s & "Public Sub EchoOn()" & vbCrLf
    s = s & "    DoCmd.Echo True" & vbCrLf
    s = s & "    Application.Screen.Repaint" & vbCrLf
    s = s & "End Sub" & vbCrLf & vbCrLf
    s = s & "' SetInsumoSeleccionado / PickFolder: mantenidos para compatibilidad" & vbCrLf
    s = s & "Public Sub SetInsumoSeleccionado(ByVal sv As String)" & vbCrLf
    s = s & "    On Error Resume Next" & vbCrLf
    s = s & "    TempVars.Remove ""TxtInsumoSeleccionado""" & vbCrLf
    s = s & "    On Error GoTo 0" & vbCrLf
    s = s & "    TempVars.Add ""TxtInsumoSeleccionado"", sv" & vbCrLf
    s = s & "End Sub" & vbCrLf & vbCrLf
    s = s & "Public Function PickFolder(titleText As String) As String" & vbCrLf
    s = s & "    Dim fd As Object" & vbCrLf
    s = s & "    Set fd = Application.FileDialog(4)" & vbCrLf
    s = s & "    With fd" & vbCrLf
    s = s & "        .Title = titleText" & vbCrLf
    s = s & "        If .Show = -1 Then PickFolder = .SelectedItems(1)" & vbCrLf
    s = s & "    End With" & vbCrLf
    s = s & "End Function" & vbCrLf
    PF_GetUIHelpersCode = s
End Function

Private Function PF_GetAsignaInsumosCode() As String
    Dim s As String
    Dim n As String: n = Chr(241)  ' n con tilde para IdCampana
    Dim o As String: o = Chr(243)  ' o con tilde para encontro
    s = "Option Compare Database" & vbCrLf
    s = s & "Option Explicit" & vbCrLf & vbCrLf
    s = s & "' SIA_PrepararTMP_DesdeDetalle" & vbCrLf
    s = s & "' FIX: RecordsAffected en vez de DCount" & vbCrLf
    s = s & "Public Sub SIA_PrepararTMP_DesdeDetalle(ByVal vIdDetalleOrden As Long)" & vbCrLf
    s = s & "    Dim db As DAO.Database: Set db = CurrentDb" & vbCrLf
    s = s & "    Dim rs As DAO.Recordset" & vbCrLf
    s = s & "    Dim vIdOrden As Long, vIdForm As Long, vDosis As Double" & vbCrLf
    s = s & "    Dim vUni As String, vIdCamp As Variant" & vbCrLf & vbCrLf
    s = s & "    Set rs = db.OpenRecordset( _" & vbCrLf
    s = s & "        ""SELECT OD.IdOrden, OD.IdFormulado, OD.[Dosis Teorica] AS DosisT, OD.Unidad, "" & _" & vbCrLf
    s = s & "        ""       First(OL.[IdCampa" & n & "a]) AS IdCamp "" & _" & vbCrLf
    s = s & "        ""FROM (Ordenes_Detalles AS OD "" & _" & vbCrLf
    s = s & "        ""      LEFT JOIN Ordenes_Lotes AS OL ON OD.IdOrden = OL.IdOrden) "" & _" & vbCrLf
    s = s & "        ""WHERE OD.IdDetalleOrden="" & vIdDetalleOrden & "" "" & _" & vbCrLf
    s = s & "        ""GROUP BY OD.IdOrden, OD.IdFormulado, OD.[Dosis Teorica], OD.Unidad;"")" & vbCrLf & vbCrLf
    s = s & "    If rs.EOF Then" & vbCrLf
    s = s & "        rs.Close: Set db = Nothing" & vbCrLf
    s = s & "        MsgBox ""No se encontr" & o & " el detalle de la orden."", vbCritical" & vbCrLf
    s = s & "        Exit Sub" & vbCrLf
    s = s & "    End If" & vbCrLf
    s = s & "    vIdOrden = Nz(rs!IdOrden, 0)" & vbCrLf
    s = s & "    vIdForm  = Nz(rs!IdFormulado, 0)" & vbCrLf
    s = s & "    vDosis   = Nz(rs!DosisT, 0)" & vbCrLf
    s = s & "    vUni     = Nz(rs!Unidad, """")" & vbCrLf
    s = s & "    vIdCamp  = rs!IdCamp" & vbCrLf
    s = s & "    rs.Close" & vbCrLf & vbCrLf
    s = s & "    db.Execute ""DELETE FROM TMP_AsigInsumo_Cultivo "" & _" & vbCrLf
    s = s & "               ""WHERE IdOrden="" & vIdOrden & "" AND IdFormulado="" & vIdForm & "";"", _" & vbCrLf
    s = s & "               dbFailOnError" & vbCrLf & vbCrLf
    s = s & "    Dim sDosis As String: sDosis = Replace(CStr(vDosis), "","", ""."")" & vbCrLf
    s = s & "    db.Execute _" & vbCrLf
    s = s & "        ""INSERT INTO TMP_AsigInsumo_Cultivo "" & _" & vbCrLf
    s = s & "        "" (IdOrden, IdFormulado, [IdCampa" & n & "a], IdCultivo, SupAfectada, "" & _" & vbCrLf
    s = s & "        ""  DosisHa, CantidadAsignada, Unidad, RedondeoEnvase, PasoMinimo) "" & _" & vbCrLf
    s = s & "        ""SELECT "" & vIdOrden & "", "" & vIdForm & "", OL.[IdCampa" & n & "a], OL.IdCultivo, "" & _" & vbCrLf
    s = s & "        ""       Sum(Nz(OL.Superficie,0)) AS SupAfectada, "" & _" & vbCrLf
    s = s & "        ""       "" & sDosis & "" AS DosisHa, "" & _" & vbCrLf
    s = s & "        ""       Sum(Nz(OL.Superficie,0)) * "" & sDosis & "" AS CantidadAsignada, "" & _" & vbCrLf
    s = s & "        ""       '"" & Replace(vUni, ""'"", ""''"") & ""' AS Unidad, "" & _" & vbCrLf
    s = s & "        ""       0 AS RedondeoEnvase, 0 AS PasoMinimo "" & _" & vbCrLf
    s = s & "        ""FROM Ordenes_Lotes AS OL "" & _" & vbCrLf
    s = s & "        ""WHERE OL.IdOrden="" & vIdOrden & "" AND OL.Aplicar=TRUE "" & _" & vbCrLf
    s = s & "        ""GROUP BY OL.[IdCampa" & n & "a], OL.IdCultivo;"", _" & vbCrLf
    s = s & "        dbFailOnError" & vbCrLf & vbCrLf
    s = s & "    ' FIX: RecordsAffected en vez de DCount" & vbCrLf
    s = s & "    If db.RecordsAffected = 0 Then" & vbCrLf
    s = s & "        Set db = Nothing" & vbCrLf
    s = s & "        MsgBox ""No hay cultivos/lotes marcados para aplicar en esta orden."", vbInformation" & vbCrLf
    s = s & "        Exit Sub" & vbCrLf
    s = s & "    End If" & vbCrLf & vbCrLf
    s = s & "    TVSet ""IdOrden"", vIdOrden" & vbCrLf
    s = s & "    If Not IsNull(vIdCamp) Then TVSet ""IdCampania"", vIdCamp" & vbCrLf
    s = s & "    TVSet ""IdFormulado"", vIdForm" & vbCrLf
    s = s & "    TVSet ""IdDetalleOrden"", vIdDetalleOrden" & vbCrLf
    s = s & "    Set db = Nothing" & vbCrLf
    s = s & "End Sub" & vbCrLf & vbCrLf
    s = s & "Public Sub SIA_RecalcularTMP_Cantidad( _" & vbCrLf
    s = s & "        Optional ByVal vIdOrden As Long = 0, _" & vbCrLf
    s = s & "        Optional ByVal vIdForm As Long = 0)" & vbCrLf
    s = s & "    Dim f As String: f = """"" & vbCrLf
    s = s & "    If vIdOrden <> 0 Then f = f & IIf(f <> """", "" AND "", """") & ""IdOrden="" & vIdOrden" & vbCrLf
    s = s & "    If vIdForm  <> 0 Then f = f & IIf(f <> """", "" AND "", """") & ""IdFormulado="" & vIdForm" & vbCrLf
    s = s & "    If f <> """" Then f = "" WHERE "" & f" & vbCrLf
    s = s & "    CurrentDb.Execute _" & vbCrLf
    s = s & "        ""UPDATE TMP_AsigInsumo_Cultivo "" & _" & vbCrLf
    s = s & "        ""SET CantidadAsignada = Nz(DosisHa,0) * Nz(SupAfectada,0)"" & f & "";"", _" & vbCrLf
    s = s & "        dbFailOnError" & vbCrLf
    s = s & "End Sub" & vbCrLf & vbCrLf
    s = s & "' SIA_ConfirmarDistribucion" & vbCrLf
    s = s & "' FIX: DSum eliminado, UPDATE con subquery (3 viajes en vez de 4)" & vbCrLf
    s = s & "Public Sub SIA_ConfirmarDistribucion(ByVal vIdDetalleOrden As Long)" & vbCrLf
    s = s & "    Dim db As DAO.Database: Set db = CurrentDb" & vbCrLf
    s = s & "    Dim rs As DAO.Recordset" & vbCrLf
    s = s & "    Dim vIdOrden As Long, vIdForm As Long" & vbCrLf & vbCrLf
    s = s & "    Set rs = db.OpenRecordset( _" & vbCrLf
    s = s & "        ""SELECT IdOrden, IdFormulado FROM Ordenes_Detalles "" & _" & vbCrLf
    s = s & "        ""WHERE IdDetalleOrden="" & vIdDetalleOrden & "";"")" & vbCrLf
    s = s & "    If rs.EOF Then" & vbCrLf
    s = s & "        rs.Close: Set db = Nothing" & vbCrLf
    s = s & "        MsgBox ""No se encontr" & o & " el detalle."", vbCritical" & vbCrLf
    s = s & "        Exit Sub" & vbCrLf
    s = s & "    End If" & vbCrLf
    s = s & "    vIdOrden = rs!IdOrden: vIdForm = rs!IdFormulado" & vbCrLf
    s = s & "    rs.Close" & vbCrLf & vbCrLf
    s = s & "    Call SIA_RecalcularTMP_Cantidad(vIdOrden, vIdForm)" & vbCrLf & vbCrLf
    s = s & "    db.Execute _" & vbCrLf
    s = s & "        ""DELETE FROM Ordenes_Detalles_Distrib "" & _" & vbCrLf
    s = s & "        ""WHERE IdDetalleOrden="" & vIdDetalleOrden & "";"", dbFailOnError" & vbCrLf & vbCrLf
    s = s & "    db.Execute _" & vbCrLf
    s = s & "        ""INSERT INTO Ordenes_Detalles_Distrib "" & _" & vbCrLf
    s = s & "        "" (IdDetalleOrden, IdOrden, [IdCampa" & n & "a], IdCultivo, IdLote, "" & _" & vbCrLf
    s = s & "        ""  CantidadAsignada, Unidad, Observaciones) "" & _" & vbCrLf
    s = s & "        ""SELECT "" & vIdDetalleOrden & "", OL.IdOrden, OL.[IdCampa" & n & "a], "" & _" & vbCrLf
    s = s & "        ""       OL.IdCultivo, OL.IdLote, "" & _" & vbCrLf
    s = s & "        ""       IIf(Nz(T.SupAfectada,0)>0, "" & _" & vbCrLf
    s = s & "        ""           Nz(OL.Superficie,0)/T.SupAfectada * T.CantidadAsignada, 0), "" & _" & vbCrLf
    s = s & "        ""       T.Unidad, Null "" & _" & vbCrLf
    s = s & "        ""FROM Ordenes_Lotes AS OL "" & _" & vbCrLf
    s = s & "        ""INNER JOIN TMP_AsigInsumo_Cultivo AS T "" & _" & vbCrLf
    s = s & "        ""   ON OL.IdOrden = T.IdOrden "" & _" & vbCrLf
    s = s & "        ""  AND OL.[IdCampa" & n & "a] = T.[IdCampa" & n & "a] "" & _" & vbCrLf
    s = s & "        ""  AND OL.IdCultivo = T.IdCultivo "" & _" & vbCrLf
    s = s & "        ""WHERE OL.IdOrden="" & vIdOrden & "" AND OL.Aplicar=TRUE;"", dbFailOnError" & vbCrLf & vbCrLf
    s = s & "    ' FIX: UPDATE con subquery (elimina DSum separado)" & vbCrLf
    s = s & "    db.Execute _" & vbCrLf
    s = s & "        ""UPDATE Ordenes_Detalles "" & _" & vbCrLf
    s = s & "        ""SET [Total Aplicado] = "" & _" & vbCrLf
    s = s & "        ""    (SELECT Nz(Sum(D.CantidadAsignada),0) "" & _" & vbCrLf
    s = s & "        ""     FROM Ordenes_Detalles_Distrib AS D "" & _" & vbCrLf
    s = s & "        ""     WHERE D.IdDetalleOrden="" & vIdDetalleOrden & "") "" & _" & vbCrLf
    s = s & "        ""WHERE IdDetalleOrden="" & vIdDetalleOrden & "";"", dbFailOnError" & vbCrLf & vbCrLf
    s = s & "    Set db = Nothing" & vbCrLf
    s = s & "End Sub" & vbCrLf
    PF_GetAsignaInsumosCode = s
End Function

' ================================================================
' UTILIDADES
' ================================================================
Private Sub PF_EnsureFolder(ByVal p As String)
    On Error Resume Next
    If Dir(p, vbDirectory) = "" Then MkDir p
    On Error GoTo 0
End Sub

Private Function PF_ReadAllText(ByVal p As String) As String
    Dim f As Integer: f = FreeFile
    Dim s As String
    Open p For Binary Access Read As #f
    s = Space$(LOF(f))
    Get #f, , s
    Close #f
    PF_ReadAllText = s
End Function

Private Sub PF_WriteAllText(ByVal p As String, ByVal s As String)
    Dim f As Integer: f = FreeFile
    Open p For Output As #f
    Print #f, s
    Close #f
End Sub
