# Data Model: 048

## dbo.OrdenesContratistaFacturas (existe, 0 filas → se amplía)

| Columna | Tipo | Nota |
|---------|------|------|
| IdVinculo | int identity PK | existe |
| IdOrdenTrabajo | int | existe → `Ordenes_Trabajo` |
| IdCompra | int | existe → `Compras.IdDeuda` (factura, NC o ND) |
| UsuarioConfirmacion | nvarchar(100) NOT NULL | NUEVA (FR-011) |
| FechaConfirmacion | datetime2 NOT NULL default SYSUTCDATETIME() | NUEVA |

Restricción nueva: UNIQUE (IdOrdenTrabajo, IdCompra). Solo hay filas confirmadas (no hay estado "propuesto": las propuestas se calculan, R3).

## dbo.OrdenesContratistaDescartes (NUEVA)

| Columna | Tipo | Nota |
|---------|------|------|
| IdDescarte | int identity PK | |
| IdCompra | int NOT NULL | factura descartada o marcada "sin orden" |
| Motivo | nvarchar(30) NOT NULL | `propuesta_incorrecta` \| `sin_orden` |
| OrdenesPropuestas | nvarchar(400) NULL | ids de las órdenes propuestas al descartar, ordenados (si cambian, la propuesta vuelve) |
| Observacion | nvarchar(400) NULL | |
| Usuario | nvarchar(100) NOT NULL | |
| Fecha | datetime2 NOT NULL default SYSUTCDATETIME() | |

UNIQUE (IdCompra). Borrarla = reabrir la factura.

## dbo.ImputacionPropuestas (017, sin cambios)

Para contratistas: `Origen='Contratista'`, `IdDetalleCompra` = IdCompra del documento, una fracción por orden × lote/cultivo/campaña (o centro de costo para órdenes sin cultivo). Al confirmar, `Estado='Aprobada'` y `UsuarioAprobacion`.

## Estados de una factura de labor (calculados)

```text
sin_revisar ──confirmar──▶ vinculada ──desvincular todo──▶ sin_revisar
     │                                           ▲
     └──descartar (propuesta_incorrecta | sin_orden)──▶ descartada ──reabrir──┘
```

`pendiente_sin_orden` (FR-008b) = `sin_revisar` y fecha ≥ puesta en marcha.

## Reglas

- Reparto: Σ fracciones = neto repartible del documento, al centavo (R4).
- Una orden puede tener varias facturas, y una factura varias órdenes.
- Anular una orden borra sus vínculos y recalcula las facturas afectadas.
- Corregir las hectáreas de una orden recalcula las facturas vinculadas a ella.
