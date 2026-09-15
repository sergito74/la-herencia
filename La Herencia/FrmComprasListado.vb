Imports System.Data

Public Class FrmComprasListado
    Inherits Form

    Private ReadOnly btnActualizar As New Button()
    Private ReadOnly gridCompras As New DataGridView()
    Private ReadOnly lblEstado As New Label()

    Public Sub New()
        Text = "Compras"
        Width = 1100
        Height = 700
        StartPosition = FormStartPosition.CenterParent

        btnActualizar.Text = "Actualizar"
        btnActualizar.Left = 12
        btnActualizar.Top = 12
        btnActualizar.Width = 100
        btnActualizar.Height = 28
        AddHandler btnActualizar.Click, AddressOf CargarCompras

        lblEstado.AutoSize = True
        lblEstado.Left = 125
        lblEstado.Top = 19

        gridCompras.Anchor = AnchorStyles.Top Or AnchorStyles.Bottom Or AnchorStyles.Left Or AnchorStyles.Right
        gridCompras.Left = 12
        gridCompras.Top = 52
        gridCompras.Width = ClientSize.Width - 24
        gridCompras.Height = ClientSize.Height - 64
        gridCompras.ReadOnly = True
        gridCompras.AllowUserToAddRows = False
        gridCompras.AutoSizeColumnsMode = DataGridViewAutoSizeColumnsMode.DisplayedCells
        gridCompras.SelectionMode = DataGridViewSelectionMode.FullRowSelect

        Controls.AddRange(New Control() {btnActualizar, lblEstado, gridCompras})
        AddHandler Load, AddressOf CargarCompras
    End Sub

    Private Sub CargarCompras(sender As Object, e As EventArgs)
        Try
            Dim compras As New DataTable()
            Using connection = SqlServerData.CreateConnection()
                Using command = connection.CreateCommand()
                    command.CommandText = "SELECT TOP 500 C.[IdDeuda], C.[Fecha], CO.[Razon Social] AS Proveedor, C.[Tipo], C.[Tipo documento], C.[Nro Documento], SUM(ISNULL(DC.[Cantidad], 0) * ISNULL(DC.[Precio Unitario], 0)) AS Subtotal, SUM(ISNULL(DC.[Cantidad], 0) * ISNULL(DC.[Precio Unitario], 0) * ISNULL(DC.[IVA], 0) / 100) AS IVA, ISNULL(C.[Conceptos no gravados], 0) AS [Conceptos no gravados], ISNULL(C.[Ingresos Brutos], 0) AS [Ingresos Brutos] FROM [dbo].[Compras] C LEFT JOIN [dbo].[Contactos] CO ON CO.[IdContacto] = C.[IdContacto] LEFT JOIN [dbo].[Det_Compras] DC ON DC.[IdCompra] = C.[IdDeuda] GROUP BY C.[IdDeuda], C.[Fecha], CO.[Razon Social], C.[Tipo], C.[Tipo documento], C.[Nro Documento], C.[Conceptos no gravados], C.[Ingresos Brutos] ORDER BY C.[Fecha] DESC, C.[IdDeuda] DESC"
                    Using adapter As New System.Data.Odbc.OdbcDataAdapter(command)
                        adapter.Fill(compras)
                    End Using
                End Using
            End Using

            gridCompras.DataSource = compras
            lblEstado.Text = compras.Rows.Count.ToString() & " compras."
        Catch ex As Exception
            lblEstado.Text = "Error de consulta."
            MessageBox.Show("No se pudo consultar compras." & Environment.NewLine & ex.Message, Text, MessageBoxButtons.OK, MessageBoxIcon.Error)
        End Try
    End Sub
End Class
