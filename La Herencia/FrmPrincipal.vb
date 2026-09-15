Public Class FrmPrincipal

    Private Sub CerrarToolStripMenuItem_Click(sender As Object, e As EventArgs) Handles CerrarToolStripMenuItem.Click

        Dim msj, titulo As String
        Dim estilo As MsgBoxStyle
        Dim resp As MsgBoxResult
        msj = "¿Está seguro que quiere salir?"
        estilo = MsgBoxStyle.YesNo
        titulo = "Confirmar Cierre"   ' Define title.
        resp = MsgBox(msj, estilo, titulo)
        If resp = MsgBoxResult.Yes Then
            Close()
        End If

    End Sub


    Private Sub AgregarRegistrosToolStripMenuItem_Click(sender As Object, e As EventArgs) Handles AgregarRegistrosToolStripMenuItem.Click

        Dim FrmCompGrales As New FrmComprasGrales()
        FrmCompGrales.MdiParent = Me
        FrmCompGrales.WindowState = FormWindowState.Maximized
        FrmCompGrales.Show()

    End Sub

    Private Sub VerRegistrosToolStripMenuItem_Click(sender As Object, e As EventArgs) Handles VerRegistrosToolStripMenuItem.Click
        Dim listado As New FrmComprasListado()
        listado.MdiParent = Me
        listado.WindowState = FormWindowState.Maximized
        listado.Show()
    End Sub
End Class
