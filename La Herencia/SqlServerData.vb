Imports System.Data.Odbc
Imports System.Configuration

Public NotInheritable Class SqlServerData
    Private Sub New()
    End Sub

    Public Shared Function CreateConnection() As OdbcConnection
        Dim settings = ConfigurationManager.ConnectionStrings("LaHerenciaSqlServer")
        If settings Is Nothing OrElse String.IsNullOrWhiteSpace(settings.ConnectionString) Then
            Throw New ConfigurationErrorsException("No está configurada la conexión LaHerenciaSqlServer.")
        End If

        Return New OdbcConnection(settings.ConnectionString)
    End Function

    Public Shared Function LoadTableOrView(objectName As String) As DataTable
        If String.IsNullOrWhiteSpace(objectName) Then
            Throw New ArgumentException("Debe indicar una tabla o vista.", NameOf(objectName))
        End If

        Dim table As New DataTable()
        Using connection = CreateConnection()
            Using command = connection.CreateCommand()
                command.CommandText = "SELECT * FROM " & QuoteIdentifier(objectName)
                Using adapter As New OdbcDataAdapter(command)
                    adapter.Fill(table)
                End Using
            End Using
        End Using
        Return table
    End Function

    Public Shared Function LoadTablesAndViews() As DataTable
        Dim objects As New DataTable()
        Using connection = CreateConnection()
            connection.Open()
            Using command = connection.CreateCommand()
                command.CommandText = "SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE IN ('BASE TABLE', 'VIEW') ORDER BY TABLE_SCHEMA, TABLE_NAME"
                Using adapter As New OdbcDataAdapter(command)
                    adapter.Fill(objects)
                End Using
            End Using
        End Using
        Return objects
    End Function

    Private Shared Function QuoteIdentifier(objectName As String) As String
        Dim parts = objectName.Split("."c)
        If parts.Length > 2 OrElse parts.Any(Function(part) String.IsNullOrWhiteSpace(part) OrElse part.Contains("]")) Then
            Throw New ArgumentException("Nombre de objeto SQL no válido.", NameOf(objectName))
        End If

        Return String.Join(".", parts.Select(Function(part) "[" & part & "]"))
    End Function
End Class
