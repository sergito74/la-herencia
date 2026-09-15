Public Class FrmComprasGrales

    Dim cn As System.Data.Odbc.OdbcConnection
    Dim daCnt, daRbr As System.Data.Odbc.OdbcDataAdapter
    Dim dtCnt, dtRbr As New DataTable()
    Dim colRbr As New DataGridViewComboBoxColumn

    Private Sub FrmComprasGrales_Load(sender As Object, e As EventArgs) Handles MyBase.Load
        cn = SqlServerData.CreateConnection()
        daCnt = New System.Data.Odbc.OdbcDataAdapter("SELECT * FROM [dbo].[Contactos] WHERE [Tipo Contacto] = 'Proveedor' OR [Tipo Contacto] = 'Multiple' ORDER BY [Razon Social]", cn)
        daCnt.Fill(dtCnt)

        CmbProveedor.DataSource = dtCnt
        CmbProveedor.DisplayMember = "Razon Social"
        CmbProveedor.ValueMember = "IdContacto"

        daRbr = New System.Data.Odbc.OdbcDataAdapter("SELECT * FROM [dbo].[Rubros] ORDER BY [Rubro]", cn)
        daRbr.Fill(dtRbr)

        Rubro.DataSource = dtRbr
        Rubro.DisplayMember = "Rubro"
        Rubro.ValueMember = "IdRubro"

        cn.Dispose()
    End Sub

    Private Sub BtnGuardar_Click(sender As Object, e As EventArgs) Handles BtnGuardar.Click
        MessageBox.Show("El sistema está en modo consulta. No se permiten modificaciones de datos reales.", Text, MessageBoxButtons.OK, MessageBoxIcon.Information)
        Return

#Disable Warning BC42105
        If CmbProveedor.SelectedValue Is Nothing OrElse CmbProveedor.SelectedValue Is DBNull.Value Then
            MessageBox.Show("Seleccione un proveedor.", Text, MessageBoxButtons.OK, MessageBoxIcon.Warning)
            Return
        End If

        Dim lineas = DTGVDetCompras.Rows.Cast(Of DataGridViewRow)().Where(Function(row) Not row.IsNewRow AndAlso Not String.IsNullOrWhiteSpace(Convert.ToString(row.Cells("Descripcion").Value))).ToList()
        If lineas.Count = 0 Then
            MessageBox.Show("Ingrese al menos un detalle de compra.", Text, MessageBoxButtons.OK, MessageBoxIcon.Warning)
            Return
        End If

        Try
            Using connection = SqlServerData.CreateConnection()
                connection.Open()
                Using transaction = connection.BeginTransaction()
                    Dim idCompra As Integer
                    Using command = connection.CreateCommand()
                        command.Transaction = transaction
                        command.CommandText = "INSERT INTO [dbo].[Compras] ([Fecha], [IdContacto], [Tipo documento], [Tipo], [Nro Documento], [Conceptos no gravados], [Ingresos Brutos]) VALUES (?, ?, ?, ?, ?, ?, ?); SELECT CAST(SCOPE_IDENTITY() AS int)"
                        AddParameter(command, DTPFecha.Value.Date)
                        AddParameter(command, Convert.ToInt32(CmbProveedor.SelectedValue))
                        AddParameter(command, If(CmbTipoDoc.SelectedItem, DBNull.Value))
                        AddParameter(command, If(CmbLetraDoc.SelectedItem, DBNull.Value))
                        AddParameter(command, If(String.IsNullOrWhiteSpace(TxtNumDoc.Text), CType(DBNull.Value, Object), TxtNumDoc.Text.Trim()))
                        AddParameter(command, ParseMoney(TxtCNoGrav.Text))
                        AddParameter(command, ParseMoney(TxtPercIIBB.Text))
                        idCompra = Convert.ToInt32(command.ExecuteScalar())
                    End Using

                    For Each row In lineas
                        Using command = connection.CreateCommand()
                            command.Transaction = transaction
                            command.CommandText = "INSERT INTO [dbo].[Det_Compras] ([IdCompra], [Cantidad], [Producto/Servicio], [IdRubro], [Precio Unitario], [IVA]) VALUES (?, ?, ?, ?, ?, ?)"
                            AddParameter(command, ParseNumber(row.Cells("Cant").Value))
                            AddParameter(command, Convert.ToString(row.Cells("Descripcion").Value).Trim())
                            AddParameter(command, If(row.Cells("Rubro").Value Is Nothing, CType(DBNull.Value, Object), row.Cells("Rubro").Value))
                            AddParameter(command, ParseNumber(row.Cells("ImporteSinIVA").Value))
                            AddParameter(command, ParseNumber(row.Cells("porcIVA").Value))
                            command.Parameters.Insert(0, New System.Data.Odbc.OdbcParameter() With {.Value = idCompra})
                            command.ExecuteNonQuery()
                        End Using
                    Next

                    transaction.Commit()
                End Using
            End Using

            MessageBox.Show("Compra guardada correctamente.", Text, MessageBoxButtons.OK, MessageBoxIcon.Information)
        Catch ex As Exception
            MessageBox.Show("No se pudo guardar la compra." & Environment.NewLine & ex.Message, Text, MessageBoxButtons.OK, MessageBoxIcon.Error)
        End Try
#Enable Warning BC42105
    End Sub

    Private Shared Sub AddParameter(command As System.Data.Odbc.OdbcCommand, value As Object)
        command.Parameters.Add(New System.Data.Odbc.OdbcParameter() With {.Value = If(value Is Nothing, DBNull.Value, value)})
    End Sub

    Private Shared Function ParseMoney(value As String) As Object
        If String.IsNullOrWhiteSpace(value) Then Return DBNull.Value
        Return Decimal.Parse(value)
    End Function

    Private Shared Function ParseNumber(value As Object) As Object
        If value Is Nothing OrElse value Is DBNull.Value OrElse String.IsNullOrWhiteSpace(Convert.ToString(value)) Then Return DBNull.Value
        Return Decimal.Parse(Convert.ToString(value))
    End Function

    Private Sub DTGVDetCompras_CellContentClick(sender As Object, e As DataGridViewCellEventArgs) Handles DTGVDetCompras.CellContentClick

    End Sub
End Class