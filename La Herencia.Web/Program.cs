using System.Data;
using System.Data.Odbc;
using System.Text.Json;

var builder = WebApplication.CreateBuilder(args);
builder.Services.ConfigureHttpJsonOptions(options =>
{
    options.SerializerOptions.PropertyNamingPolicy = JsonNamingPolicy.CamelCase;
    options.SerializerOptions.DictionaryKeyPolicy = JsonNamingPolicy.CamelCase;
});
var app = builder.Build();

app.UseDefaultFiles();
app.UseStaticFiles();

app.MapGet("/api/dashboard", async () =>
{
    await using var connection = OpenConnection();
    var result = new DashboardSummary(
        await ScalarAsync(connection, "SELECT COUNT(*) FROM [dbo].[Compras]"),
        await ScalarAsync(connection, "SELECT COUNT(*) FROM [dbo].[Venta Hacienda]"),
        await ScalarAsync(connection, "SELECT COUNT(*) FROM [dbo].[Venta Granos]"),
        await ScalarAsync(connection, "SELECT COUNT(*) FROM [dbo].[Movimientos BNA]")
    );
    return Results.Ok(result);
});

app.MapGet("/api/catalogs", async () =>
{
    await using var connection = OpenConnection();
    var suppliers = await QueryAsync(connection, "SELECT [IdContacto] AS Id, [Razon Social] AS Name FROM [dbo].[Contactos] WHERE [Tipo Contacto] IN ('Proveedor', 'Multiple') ORDER BY [Razon Social]");
    var categories = await QueryAsync(connection, "SELECT [IdRubro] AS Id, [Rubro] AS Name FROM [dbo].[Rubros] ORDER BY [Rubro]");
    return Results.Ok(new { suppliers, categories });
});

app.MapGet("/api/purchases", async () =>
{
    await using var connection = OpenConnection();
    var purchases = await QueryAsync(connection, "SELECT TOP 100 C.[IdDeuda] AS Id, C.[Fecha] AS Date, CO.[Razon Social] AS Supplier, C.[Tipo documento] AS DocumentType, C.[Tipo] AS Letter, C.[Nro Documento] AS DocumentNumber, SUM(ISNULL(DC.[Cantidad], 0) * ISNULL(DC.[Precio Unitario], 0)) AS Subtotal, SUM(ISNULL(DC.[Cantidad], 0) * ISNULL(DC.[Precio Unitario], 0) * ISNULL(DC.[IVA], 0) / 100) AS Tax FROM [dbo].[Compras] C LEFT JOIN [dbo].[Contactos] CO ON CO.[IdContacto] = C.[IdContacto] LEFT JOIN [dbo].[Det_Compras] DC ON DC.[IdCompra] = C.[IdDeuda] GROUP BY C.[IdDeuda], C.[Fecha], CO.[Razon Social], C.[Tipo documento], C.[Tipo], C.[Nro Documento] ORDER BY C.[Fecha] DESC, C.[IdDeuda] DESC");
    return Results.Ok(purchases);
});

app.MapGet("/api/purchases/{id:int}", async (int id) =>
{
    await using var connection = OpenConnection();
    var header = await QueryAsync(connection, "SELECT C.[IdDeuda] AS Id, C.[Fecha] AS Date, CO.[Razon Social] AS Supplier, C.[Tipo documento] AS DocumentType, C.[Tipo] AS Letter, C.[Nro Documento] AS DocumentNumber, C.[Conceptos no gravados] AS NonTaxable, C.[Ingresos Brutos] AS GrossIncomeTax FROM [dbo].[Compras] C LEFT JOIN [dbo].[Contactos] CO ON CO.[IdContacto] = C.[IdContacto] WHERE C.[IdDeuda] = " + id);
    var details = await QueryAsync(connection, "SELECT [Cantidad] AS Quantity, [Producto/Servicio] AS Description, [IdRubro] AS CategoryId, [Precio Unitario] AS NetAmount, [IVA] AS TaxRate FROM [dbo].[Det_Compras] WHERE [IdCompra] = " + id);
    return Results.Ok(new { header = header.FirstOrDefault(), details });
});

app.MapGet("/api/accounts", async (string? search, string? type) =>
{
    await using var connection = OpenConnection();
    var sql = "SELECT TOP 300 C.[IdContacto] AS Id, C.[Razon Social] AS Name, C.[Tipo Contacto] AS ContactType, COALESCE(SUM(V.[Deuda]), 0) AS Debt, COALESCE(SUM(V.[Credito]), 0) AS Credit, COALESCE(SUM(V.[Deuda] - V.[Credito]), 0) AS NetBalance FROM [dbo].[Contactos] C LEFT JOIN [dbo].[vw_MovimientosCuenta_Base] V ON V.[IdContacto] = C.[IdContacto] WHERE (? = '' OR C.[Razon Social] LIKE ?) AND (? = '' OR C.[Tipo Contacto] = ?) GROUP BY C.[IdContacto], C.[Razon Social], C.[Tipo Contacto] ORDER BY C.[Razon Social]";
    var normalizedSearch = search?.Trim() ?? string.Empty;
    var normalizedType = type?.Trim() ?? string.Empty;
    var accounts = await QueryAsync(connection, sql, normalizedSearch, "%" + normalizedSearch + "%", normalizedType, normalizedType);
    return Results.Ok(accounts);
});

app.MapGet("/api/accounts/{id:int}", async (int id) =>
{
    await using var connection = OpenConnection();
    var movements = await QueryAsync(connection, "SELECT [Fecha] AS Date, [Razon Social] AS Name, [Documento] AS Document, [Nro Documento] AS DocumentNumber, [Deuda] AS Debt, [Credito] AS Credit, [Origen] AS Origin, [IdOrigen] AS OriginId, [SaldoParcial] AS RunningBalance FROM [dbo].[vw_MovimientosCuenta_Saldo] WHERE [IdContacto] = ? ORDER BY [Fecha] DESC, [IdOrigen] DESC", id);
    return Results.Ok(movements);
});

app.MapGet("/api/treasury/accounts", async () =>
{
    await using var connection = OpenConnection();
    var accounts = await QueryAsync(connection, "SELECT [Cuenta] AS Account, [Caja] AS Cashbox, COUNT(*) AS MovementCount FROM [dbo].[Movimientos] GROUP BY [Cuenta], [Caja] ORDER BY [Cuenta], [Caja]");
    return Results.Ok(accounts);
});

app.MapGet("/api/treasury/movements", async (string? account, string? cashbox) =>
{
    await using var connection = OpenConnection();
    var movements = await QueryAsync(connection, "SELECT TOP 300 [Fecha] AS Date, [TipoMov] AS MovementType, [Tipo documento] AS DocumentType, [Nro Documento] AS DocumentNumber, [Cuenta] AS Account, [Caja] AS Cashbox, [Importe] AS Amount, [IdContacto] AS ContactId FROM [dbo].[Resumen Cuenta] WHERE (? = '' OR [Cuenta] = ?) AND (? = '' OR [Caja] = ?) ORDER BY [Fecha] DESC", account?.Trim() ?? string.Empty, account?.Trim() ?? string.Empty, cashbox?.Trim() ?? string.Empty, cashbox?.Trim() ?? string.Empty);
    return Results.Ok(movements);
});

app.MapGet("/api/operations", async () =>
{
    await using var connection = OpenConnection();
    var cattle = await QueryAsync(connection, "SELECT TOP 80 [IdVenta] AS Id, [Fecha] AS Date, [Nro documento] AS DocumentNumber, [IdConsignatario] AS ConsigneeId, [Flete] AS Freight, [Gastos Varios] AS OtherExpenses FROM [dbo].[Venta Hacienda] ORDER BY [Fecha] DESC, [IdVenta] DESC");
    var grains = await QueryAsync(connection, "SELECT TOP 80 [IdVenta] AS Id, [Fecha] AS Date, [Nro Documento] AS DocumentNumber, [Tipo de Grano] AS Grain, [Cantidad vendida] AS Quantity, [Precio unitario] AS UnitPrice, [Importe Neto a percibir] AS NetReceivable FROM [dbo].[Venta Granos] ORDER BY [Fecha] DESC, [IdVenta] DESC");
    return Results.Ok(new { cattle, grains });
});

app.MapGet("/api/treasury", async () =>
{
    await using var connection = OpenConnection();
    var bna = await QueryAsync(connection, "SELECT TOP 100 [Fecha / Hora Mov#] AS Date, [Concepto] AS Description, [Importe] AS Amount, [Contacto] AS Contact FROM [dbo].[Movimientos BNA] ORDER BY [Fecha / Hora Mov#] DESC, [IdMovimientoBNA] DESC");
    var galicia = await QueryAsync(connection, "SELECT TOP 100 [Fecha] AS Date, [Descripción] AS Description, [Débitos] AS Debits, [Créditos] AS Credits, [Saldo] AS Balance, [Contacto] AS Contact FROM [dbo].[Movimientos Galicia] ORDER BY [Fecha] DESC, [IdMovimiento] DESC");
    return Results.Ok(new { bna, galicia });
});

app.MapGet("/api/sql-objects", async () =>
{
    await using var connection = OpenConnection();
    var objects = await QueryAsync(connection, "SELECT [TABLE_NAME] AS Name, [TABLE_TYPE] AS Type FROM [INFORMATION_SCHEMA].[TABLES] WHERE [TABLE_SCHEMA] = 'dbo' AND [TABLE_TYPE] IN ('BASE TABLE', 'VIEW') ORDER BY [TABLE_TYPE], [TABLE_NAME]");
    return Results.Ok(objects);
});

app.MapGet("/api/sql-preview", async (string? name, int? limit) =>
{
    if (string.IsNullOrWhiteSpace(name) || name.Contains(']'))
    {
        return Results.BadRequest(new { message = "Seleccione una tabla o vista válida." });
    }

    await using var connection = OpenConnection();
    await using var validation = connection.CreateCommand();
    validation.CommandText = "SELECT COUNT(*) FROM [INFORMATION_SCHEMA].[TABLES] WHERE [TABLE_SCHEMA] = 'dbo' AND [TABLE_NAME] = ? AND [TABLE_TYPE] IN ('BASE TABLE', 'VIEW')";
    validation.Parameters.Add(new OdbcParameter { Value = name });
    if (Convert.ToInt32(await validation.ExecuteScalarAsync()) != 1)
    {
        return Results.BadRequest(new { message = "La tabla o vista seleccionada no existe." });
    }

    var safeLimit = Math.Clamp(limit ?? 50, 1, 200);
    var rows = await QueryAsync(connection, $"SELECT TOP {safeLimit} * FROM [dbo].[{name}]");
    return Results.Ok(rows);
});

app.MapPost("/api/purchases", () =>
{
    return Results.StatusCode(StatusCodes.Status403Forbidden);
});

app.Run();

static OdbcConnection OpenConnection()
{
    var connectionString = Environment.GetEnvironmentVariable("LA_HERENCIA_SQL")
        ?? "DSN=SQL_LaHerencia;Trusted_Connection=Yes;DATABASE=LaHerencia";
    var connection = new OdbcConnection(connectionString);
    connection.Open();
    return connection;
}

static async Task<object?> ScalarAsync(OdbcConnection connection, string sql)
{
    await using var command = connection.CreateCommand();
    command.CommandText = sql;
    return await command.ExecuteScalarAsync();
}

static async Task<List<Dictionary<string, object?>>> QueryAsync(OdbcConnection connection, string sql, params object[] values)
{
    await using var command = connection.CreateCommand();
    command.CommandText = sql;
    foreach (var value in values)
    {
        command.Parameters.Add(new OdbcParameter { Value = value ?? DBNull.Value });
    }
    await using var reader = await command.ExecuteReaderAsync();
    var rows = new List<Dictionary<string, object?>>();
    while (await reader.ReadAsync())
    {
        var row = new Dictionary<string, object?>();
        for (var index = 0; index < reader.FieldCount; index++)
        {
            row[reader.GetName(index)] = reader.IsDBNull(index) ? null : reader.GetValue(index);
        }
        rows.Add(row);
    }
    return rows;
}

record DashboardSummary(object? Purchases, object? CattleSales, object? GrainSales, object? BankMovements);
