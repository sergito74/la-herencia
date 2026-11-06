# Data Model: 048 (revisado 06/11)

## dbo.OrdenesContratistaFacturas (existe, 0 filas)

| Columna | Tipo | Nota |
|---------|------|------|
| IdVinculo | int identity PK | existe |
| IdOrdenTrabajo | int | existe |
| IdCompra | int | existe; solo facturas de labor (las NC/ND no) |
| UsuarioConfirmacion | nvarchar(100) NOT NULL | NUEVA |
| FechaConfirmacion | datetime2 NOT NULL default SYSUTCDATETIME() | NUEVA |

UNIQUE (IdOrdenTrabajo, IdCompra).

## dbo.CompraDocumentosRelacionados (existe, sin cambios)

NC/ND ↔ factura.

## dbo.ImputacionPropuestas (017, sin cambios)

`Origen='Contratista'`, `IdDetalleCompra` = IdCompra (factura o NC/ND), una fracción por orden × lote/cultivo/campaña (o centro de costo); `Estado='Aprobada'` al guardar.

## Reglas

- Σ fracciones = neto repartible, al centavo.
- Anular una orden borra sus vínculos y recalcula las facturas afectadas (y sus NC/ND); corregir sus hectáreas, también.
- No hay tabla de propuestas ni de descartes.
