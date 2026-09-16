# Data Model: Impuestos, remuneraciones, arrendamientos y ventas de hacienda

## Impuesto

Origen: `dbo.Impuestos` (join opcional con `dbo.[Tipo Impuesto]` y `dbo.Contactos`)

| Campo (API) | Columna SQL | Notas |
|---|---|---|
| idImpuesto | `IdImpuesto` | PK |
| fecha | `Fecha` | |
| tipoImpuesto | `[Tipo Impuesto].[Nombre Impuesto]` | Join por `IdTipoImpuesto`, puede ser null |
| periodoLiquidado | `[Periodo liquidado]` | |
| numeroDocumento | `[Numero de documento]` | |
| importe | `Importe` | |
| organismo | `Contactos.[Razon Social]` | Join por `IdOrganismo`, null si no está cargado |

## Retención (impositiva genérica)

Origen: `dbo.Retenciones`

| Campo (API) | Columna SQL | Notas |
|---|---|---|
| idRetencion | `IdRetencionSQL` | PK |
| numeroCertificado | `[Numero Certificado]` | |
| fecha | `Fecha` | |
| contacto | `Contactos.[Razon Social]` | Join por `IdContacto` |
| importe | `Importe` | |

## Remuneración (liquidación)

Origen: `dbo.Remuneraciones`

| Campo (API) | Columna SQL | Notas |
|---|---|---|
| idSalario | `IdSalario` | PK |
| empleado | `Contactos.[Razon Social]` | Join por `IdContacto` |
| fechaPago | `[Fecha de pago]` | |
| periodoLiquidado | `[Periodo liquidado]` | |
| importe | Suma de conceptos monetarios de la fila (`Sueldo basico` + `Aguinaldo` + ... ) o el total ya calculado si existe una columna de total | Ver Nota de implementación abajo |

**Nota de implementación**: `Remuneraciones` no tiene una columna de "total" única — son ~15 columnas de concepto (`Sueldo basico`, `Aguinaldo`, `Vacaciones`, etc.). El campo `importe` del contrato MUST ser la suma de todos los conceptos monetarios de la fila, calculada en SQL (no en Python, para no duplicar la regla si cambia el listado de conceptos).

## Pago de remuneración (entidad independiente — corregido 2026-09-17)

Origen: `dbo.[Pagos Remuneraciones]`

**Corrección**: confirmado contra datos reales que `IdEmpleado` de esta tabla NO es una FK hacia `Contactos` (rango 1-6, resuelve a contactos tipo "Proveedor" — distinto del rango real de empleados 46-632 en `Remuneraciones.IdContacto`). No hay vínculo confiable hacia un empleado ni hacia una liquidación específica — ver `research.md`. Por lo tanto esta entidad **NO** se anida bajo `Remuneración`; se consulta de forma independiente, sin campo de contacto.

| Campo (API) | Columna SQL | Notas |
|---|---|---|
| idPago | `IdPago` | PK |
| fecha | `Fecha` | |
| cuenta | `Cuenta` | |
| caja | `Caja` | |
| importe | `[Importe imputado]` | |

## Arrendamiento (contrato de alquiler)

Origen: `dbo.Alquileres`

| Campo (API) | Columna SQL | Notas |
|---|---|---|
| idAlquiler | `IdAlquiler` | PK |
| fecha | `Fecha` | |
| inicioPeriodo | `[Inicio del periodo]` | |
| finPeriodo | `[Fin del periodo]` | |
| contacto | `Contactos.[Razon Social]` | Join por `IdContacto` |
| importeTotalContrato | `[Importe total del contrato]` | |
| cantidadCuotas | `[Cantidad de cuotas]` | |
| cobros | Lista de `Cobro de alquiler` (ver abajo) | Join directo por `IdAlquiler` |

## Cobro de alquiler

Origen: `dbo.[Detalle Cobro Alquiler]`

| Campo (API) | Columna SQL | Notas |
|---|---|---|
| idCobroAlquiler | `IdCobroAlquiler` | PK |
| numeroCuota | `[Numero Cuota]` | |
| importeCuota | `[Importe Cuota]` | |
| estado | `Estado` | |
| fechaVencimiento | `[Fecha vencimiento]` | |

## Venta de Hacienda

Origen: `dbo.[Venta Hacienda]`

| Campo (API) | Columna SQL | Notas |
|---|---|---|
| idVenta | `IdVenta` | PK |
| fecha | `Fecha` | |
| consignatario | `Contactos.[Razon Social]` | Join por `IdConsignatario` — es el intermediario, NO el comprador (clarificación 2026-09-16) |
| numeroDocumento | `[Nro documento]` | |
| lineas | Lista de `Línea de venta de hacienda` (ver abajo) | Join directo por `IdVenta` |

**Nota de implementación (confirmado contra datos reales 2026-09-16)**: `Retenciones Ventas Hacienda` NO tiene columna `IdVenta`, y se verificó que su `IdContacto` no siempre coincide con ningún `IdComprador` de `Det_Ventas Hacienda` (ejemplo real: contacto 551 tiene una retención pero cero líneas de venta como comprador). **No existe una clave confiable para unir una retención a una venta específica** — por lo tanto, `Venta de Hacienda` NO incluye una lista anidada de `retenciones`; las retenciones se consultan como listado independiente (propio endpoint), filtrable por contacto, sin pretender asociarlas a una venta puntual (principio IV: no inventar trazabilidad donde no la hay).

## Línea de venta de hacienda

Origen: `dbo.[Det_Ventas Hacienda]`

| Campo (API) | Columna SQL | Notas |
|---|---|---|
| idDetalleVenta | `IdDetalleVenta` | PK |
| comprador | `Contactos.[Razon Social]` | Join por `IdComprador` |
| tipoHacienda | `[Tipo Hacienda].[Tipo de Hacienda]` | Join por `IdTipoProducto` |
| cantidad | `Cantidad` | |
| unidadMedida | `[Unidad de medida]` | |
| pesoTotal | `[Peso Total]` | |
| precioUnitarioA | `[Precio unitario (A)]` | Confirmado contra datos reales (2026-09-16): ambas columnas están pobladas en casi todas las filas (244/245 y 245/245) con escalas muy distintas entre sí (ej. 7.45 vs 1.59 en la misma línea) — no hay forma de inferir sin ambigüedad cuál es "el" importe de la línea ni cómo se relacionan entre sí (¿distinta unidad de medida? ¿moneda?). Se exponen ambos precios crudos tal cual están en el origen, sin calcular un total ni descartar ninguno (principio IV: no inventar un dato que la fuente no da con claridad) |
| precioUnitarioB | `[Precio unitario (B)]` | Ver nota de `precioUnitarioA` |

## Retención de venta de hacienda

Origen: `dbo.[Retenciones Ventas Hacienda]`

| Campo (API) | Columna SQL | Notas |
|---|---|---|
| idRetencion | `Id` | PK |
| fecha | `Fecha` | |
| contacto | `Contactos.[Razon Social]` | Join por `IdContacto` |
| documento | `Documento` | |
| numeroDocumento | `[Nro Documento]` | |
| importe | `Importe` | |

## Referencia de origen resuelta (ampliación de `specs/004-cuentas-corrientes`)

Nuevos casos de `origen` en `GET /api/cuentas-corrientes/contactos/{id}/movimientos`, siguiendo el mismo patrón que `compra`/`tesoreria`:

**Caso impuesto** (`Origen = "Impuestos"`):

| Campo (API) | Descripción |
|---|---|
| tipo | `"impuesto"` |
| idImpuesto | = `idOrigen` |
| tipoImpuesto | de `Impuestos` → `Tipo Impuesto` |
| importe | de `Impuestos.Importe` |

**Caso retención** (`Origen = "Retenciones"`):

| Campo (API) | Descripción |
|---|---|
| tipo | `"retencion"` |
| idRetencion | = `idOrigen` |
| numeroCertificado | de `Retenciones` |
| importe | de `Retenciones.Importe` |

**Caso remuneración** (`Origen = "Remuneraciones"`):

| Campo (API) | Descripción |
|---|---|
| tipo | `"remuneracion"` |
| idSalario | = `idOrigen` |
| periodoLiquidado | de `Remuneraciones` |
| empleado | de `Remuneraciones` → `Contactos` |

**Caso arrendamiento** (`Origen = "Alquileres"`):

| Campo (API) | Descripción |
|---|---|
| tipo | `"arrendamiento"` |
| idAlquiler | = `idOrigen` |
| contacto | de `Alquileres` → `Contactos` |
| importeTotalContrato | de `Alquileres` |

**Caso venta de hacienda** (`Origen = "Ret. Ventas Hacienda"`):

| Campo (API) | Descripción |
|---|---|
| tipo | `"venta_hacienda"` |
| idRetencion | = `idOrigen` (referencia a la retención, no a la venta — ver research.md) |
| numeroDocumento | de `Retenciones Ventas Hacienda` |
| importe | de `Retenciones Ventas Hacienda.Importe` |

**Caso fuera de alcance restante** (sin cambios respecto a 004):

| Campo (API) | Descripción |
|---|---|
| tipo | `"fuera_de_alcance"` |
| origenTipo | `"Ret. IVA Granos"` (único valor restante, dominio de Agricultura) |

## Validaciones y reglas transversales

- Ninguna entidad admite escritura (FR-008).
- Ningún dominio calcula ni expone imputación cruzada hacia compras (FR-007) — cada uno muestra únicamente sus propios campos.
- Cuando un contacto (organismo/empleado/arrendador/comprador/consignatario) no está cargado, el campo correspondiente MUST devolverse explícitamente `null`, nunca omitirse (principio IV).
