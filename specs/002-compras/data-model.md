# Data Model: Compras como fuente de verdad de imputación

Todas las entidades se leen desde SQL Server (`LaHerencia`) tal como existen hoy; este documento no propone cambios de esquema, solo el modelo lógico que el backend expone al frontend.

## Compra

Origen: `dbo.Compras`

| Campo (API) | Columna SQL | Tipo | Notas |
|---|---|---|---|
| idCompra | `IdDeuda` | int (PK) | Identity |
| fecha | `Fecha` | date | |
| idContacto | `IdContacto` | int (FK → Contactos) | Proveedor |
| tipoDocumento | `Tipo documento` | string | |
| tipo | `Tipo` | string | |
| numeroDocumento | `Nro Documento` | string | |
| conceptosNoGravados | `Conceptos no gravados` | decimal | Mostrado diferenciado (FR-007) |
| ingresosBrutos | `Ingresos Brutos` | decimal | Mostrado diferenciado (FR-007) |

Relaciones: 1 Compra → N Línea de compra (`Det_Compras.IdCompra = Compras.IdDeuda`).

## Línea de compra

Origen: `dbo.Det_Compras`

| Campo (API) | Columna SQL | Tipo | Notas |
|---|---|---|---|
| idDetalleCompra | `IdDetalleCompra` | int (PK) | Identity |
| idCompra | `IdCompra` | int (FK → Compras.IdDeuda) | |
| productoServicio | `Producto/Servicio` | string | |
| cantidad | `Cantidad` | decimal | |
| precioUnitario | `Precio Unitario` | decimal | |
| iva | `IVA` | decimal | |
| idRubro | `IdRubro` | int (FK → `dbo.Rubros.IdRubro`) | Imputación — fuente de verdad (FR-004/FR-005) |
| idCentroCosto | `IdCentroCostos` | int (FK → `dbo.[Centro de costos].IdCentro`) | Imputación — puede estar ausente (FR-006) |
| idDestino | `IdDestino` | int (FK → `dbo.DestinoCompras.IdDestino`) | Imputación — puede estar ausente (FR-006) |
| idCampania | `IdCampaña` | int (FK → `dbo.Campañas`, tabla no relevada en detalle) | Imputación adicional confirmada el 2026-09-16 (clarificación de spec) |
| campania | `Campaña` | string | Texto de campaña, redundante con `idCampania` en el esquema actual |

Confirmado contra `INFORMATION_SCHEMA` (2026-09-16): `Det_Compras` también tiene `Unidad`, `IdFormulado` y `Ajuste financiero` (bit), no usados por esta spec.

Regla de negocio: si `idRubro`, `idCentroCosto`, `idDestino` o `idCampania` son `NULL`, el API MUST devolver el campo explícitamente como ausente (`null`), nunca omitirlo ni sustituirlo por un valor por defecto (FR-006).

**Nota (2026-09-16)**: existen tablas `rubros_compra` y `centros_costo` con esquema distinto (`uniqueidentifier`, `empresa_id`, `row_version`) que **no** corresponden a las FK de `Det_Compras` (que son `int`). No usar esas tablas para esta spec — quedan fuera de alcance, origen desconocido, a confirmar con el usuario si hace falta en el futuro.

## Rubro

Origen: `dbo.Rubros`

| Campo (API) | Columna SQL | Tipo | Notas |
|---|---|---|---|
| idRubro | `IdRubro` | int (PK) | |
| nombre | `Rubro` | string | Nombre de categoría de imputación |
| clasificacion | `Clasificacion` | string | No usado por esta spec, disponible para futuro |

## Centro de costo

Origen: `dbo.[Centro de costos]`

| Campo (API) | Columna SQL | Tipo | Notas |
|---|---|---|---|
| idCentroCosto | `IdCentro` | int (PK) | |
| nombre | `Centro de costos` | string | |

## Destino

Origen: `dbo.DestinoCompras`

| Campo (API) | Columna SQL | Tipo | Notas |
|---|---|---|---|
| idDestino | `IdDestino` | int (PK) | |
| nombre | `Destino` | string | |
| idCentroCosto | `IdCentroCostos` | int | Relación propia con centro de costo, no usada directamente por esta spec |

## Proveedor (subconjunto de Contacto)

Origen: `dbo.Contactos` filtrado por `Tipo Contacto`

| Campo (API) | Columna SQL | Tipo | Notas |
|---|---|---|---|
| idContacto | `IdContacto` | int (PK) | |
| razonSocial | `Razon Social` | string | |
| tipoContacto | `Tipo Contacto` | string | Ej. `Proveedor`, `Multiple` |

## Referencia de trazabilidad (Compra → Cuenta corriente / Tesorería)

No es una tabla propia; se resuelve consultando `vw_MovimientosCuenta_Base` (u origen equivalente) donde `IdOrigen = Compras.IdDeuda` (clarificación 2026-09-15, FR-008).

| Campo (API) | Origen | Notas |
|---|---|---|
| origenTipo | `Origen` de `vw_MovimientosCuenta_Base` | Ej. "Compra" |
| idOrigen | `IdOrigen` | Debe coincidir con `idCompra` |
| documento | `Documento` / `Nro Documento` | |
| fecha | `Fecha` | |
| importe | `Deuda` / `Credito` | |

Si no existen movimientos con `IdOrigen = idCompra`, el API MUST indicar explícitamente "sin movimientos asociados" (FR-009), no un array vacío ambiguo sin contexto.

## Validaciones y reglas transversales

- Ninguna entidad de este módulo admite escritura (FR-010): el contrato de API expone únicamente operaciones `GET`.
- Toda consulta MUST ser parametrizada y acotada por paginación (FR-013), conforme al principio V de la constitución.
- El campo de imputación (`idRubro`/`centroCosto`/`destino`) en Línea de compra es la única fuente de verdad para ese dato en todo el sistema (FR-005); ningún otro módulo debe redefinirlo.
