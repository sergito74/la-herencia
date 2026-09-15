Imports System.Data

Public Class FrmExploradorSql
    Inherits Form

    Private ReadOnly cboObjeto As New ComboBox()
    Private ReadOnly btnConsultar As New Button()
    Private ReadOnly gridDatos As New DataGridView()
    Private ReadOnly lblEstado As New Label()

    Public Sub New()
        Text = "Explorador SQL Server"
        Width = 1100
        Height = 700
        StartPosition = FormStartPosition.CenterParent

        cboObjeto.Anchor = AnchorStyles.Top Or AnchorStyles.Left Or AnchorStyles.Right
        cboObjeto.DropDownStyle = ComboBoxStyle.DropDownList
        cboObjeto.Left = 12
        cboObjeto.Top = 12
        cboObjeto.Width = 820

        btnConsultar.Text = "Consultar"
        btnConsultar.Left = 844
        btnConsultar.Top = 11
        btnConsultar.Width = 100
        btnConsultar.Height = cboObjeto.Height
        AddHandler btnConsultar.Click, AddressOf ConsultarObjeto

        lblEstado.AutoSize = True
        lblEstado.Left = 12
        lblEstado.Top = 45

        gridDatos.Anchor = AnchorStyles.Top Or AnchorStyles.Bottom Or AnchorStyles.Left Or AnchorStyles.Right
        gridDatos.Left = 12
        gridDatos.Top = 70
        gridDatos.Width = ClientSize.Width - 24
        gridDatos.Height = ClientSize.Height - 82
        gridDatos.ReadOnly = True
        gridDatos.AllowUserToAddRows = False
        gridDatos.AutoSizeColumnsMode = DataGridViewAutoSizeColumnsMode.DisplayedCells

        Controls.AddRange(New Control() {cboObjeto, btnConsultar, lblEstado, gridDatos})
        AddHandler Load, AddressOf CargarObjetos
    End Sub

    Private Sub CargarObjetos(sender As Object, e As EventArgs)
        Try
            Dim objetos = SqlServerData.LoadTablesAndViews()
            cboObjeto.Items.Clear()
            For Each row As DataRow In objetos.Rows
                cboObjeto.Items.Add(row("TABLE_SCHEMA").ToString() & "." & row("TABLE_NAME").ToString())
            Next
            If cboObjeto.Items.Count > 0 Then
                cboObjeto.SelectedIndex = 0
                lblEstado.Text = cboObjeto.Items.Count.ToString() & " objetos disponibles."
            End If
        Catch ex As Exception
            MostrarError("No se pudo cargar el catálogo SQL Server.", ex)
        End Try
    End Sub

    Private Sub ConsultarObjeto(sender As Object, e As EventArgs)
        If cboObjeto.SelectedItem Is Nothing Then Return

        Try
            Dim tabla = SqlServerData.LoadTableOrView(cboObjeto.SelectedItem.ToString())
            gridDatos.DataSource = tabla
            lblEstado.Text = tabla.Rows.Count.ToString() & " registros."
        Catch ex As Exception
            MostrarError("No se pudo consultar el objeto seleccionado.", ex)
        End Try
    End Sub

    Private Sub MostrarError(mensaje As String, ex As Exception)
        lblEstado.Text = mensaje
        MessageBox.Show(mensaje & Environment.NewLine & ex.Message, Text, MessageBoxButtons.OK, MessageBoxIcon.Error)
    End Sub
End Class
