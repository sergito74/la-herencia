# Data Model: Tesorería por banco, caja, valores y tarjetas

Todas las entidades se leen desde SQL Server tal como existen hoy. Cada medio conserva su propia forma (FR-002); no se fuerza un modelo único.

## Movimiento BNA

Origen: `dbo.Movimientos BNA`

| Campo (API) | Columna SQL | Notas |
|---|---|---|
| idMovimientoBNA | `IdMovimientoBNA` | PK |
| fechaHora | `Fecha / Hora Mov#` | |
| concepto | `Concepto` | |
| importe | `Importe` | |
| idContacto | `IdContacto` | Puede ser null |
| contacto | `Contacto` | |

## Movimiento Galicia

Origen: `dbo.Movimientos Galicia`

| Campo (API) | Columna SQL | Notas |
|---|---|---|
| idMovimiento | `IdMovimiento` | PK |
| fecha | `Fecha` | |
| descripcion | `Descripción` | |
| debitos | `Débitos` | |
| creditos | `Créditos` | |
| saldo | `Saldo` | Campo propio de Galicia, no forzado en BNA |
| idContacto | `IdContacto` | |
| contacto | `Contacto` | |

Nota: `centro de costos`, `rubro` y `destino` existen en esta tabla pero MUST NOT exponerse como imputación (FR-006) — quedan fuera del contrato de API de este módulo.

## Pago en efectivo

Origen: `dbo.[Pagos efectivo]` — confirmado contra `INFORMATION_SCHEMA` (2026-09-16).

| Campo (API) | Columna SQL | Notas |
|---|---|---|
| idPagoEfectivo | `IdPagoEfectivo` | PK |
| idContacto | `IdContacto` | |
| fecha | `Fecha` | |
| cuenta | `Cuenta` | |
| caja | `Caja` | |
| numeroDocumento | `Numero documento` | Tipo `float` en el origen (dato heredado, no numérico limpio) |
| importeImputado | `Importe imputado` | |
| idOperacion | `IdOperacion` | |

## Valor propio

Origen: `dbo.[Valores propios]` — confirmado contra `INFORMATION_SCHEMA` (2026-09-16).

| Campo (API) | Columna SQL | Notas |
|---|---|---|
| idValor | `IdValor` | PK |
| numeroCheque | `Numero cheque` | |
| fechaEmision | `Fecha emision` | |
| fechaVencimiento | `Fecha vencimiento` | |
| importe | `Importe` | |
| cobrado | `Cobrado` | |
| fechaCobro | `Fecha Cobro` | |
| numeroCuenta | `Numero Cuenta` | |

**Sin campo de contacto** (confirmado 2026-09-16). Por decisión del usuario, este medio **no participa de la referencia heurística hacia compras** (ver sección "Referencia de origen" más abajo): siempre devuelve `estado: "sin_coincidencia"`, sin intentar aproximar por fecha/importe solamente.

## Valor recibido

Origen: `dbo.[Valores Recibidos]` — confirmado contra `INFORMATION_SCHEMA` (2026-09-16).

| Campo (API) | Columna SQL | Notas |
|---|---|---|
| idValor | `IdValor` | PK |
| numeroValor | `Numero Valor` | |
| banco | `Banco` | |
| fechaEmision | `Fecha Emision` | |
| fechaVencimiento | `Fecha Vencimiento` | |
| fechaCobro | `Fecha Cobro` | |
| idEmisor | `IdEmisor` | Contacto emisor (no `IdContacto` genérico) |
| idReceptor | `IdReceptor` | Contacto receptor |
| importe | `Importe` | |
| destino | `Destino` | Texto libre, sin relación con la imputación de compras |

Para la referencia heurística hacia compras, usar `idEmisor` (el pagador) como equivalente a `IdContacto`.

## Tarjeta / Resumen / Línea de resumen

Origen: `dbo.Tarjetas`, `dbo.Tarjetas_Resumenes`, `dbo.Tarjetas_Resumenes_Lineas`.

`Tarjetas_Resumenes_Lineas` confirmado contra `INFORMATION_SCHEMA` (2026-09-16):

| Campo (API) | Columna SQL | Notas |
|---|---|---|
| idLineaConsumo | `IdLineaConsumo` | PK |
| idResumen | `IdResumen` | FK → `Tarjetas_Resumenes` |
| fechaCompra | `FechaCompra` | |
| detalle | `Detalle` | |
| importe | `Importe` | |
| idContacto | `IdContacto` | |
| numeroDocumento | `NroDocumento` | |

`Tarjetas` y `Tarjetas_Resumenes` quedan pendientes de confirmar contra `INFORMATION_SCHEMA` en implementación (fuera del alcance de esta verificación puntual).

## Referencia de origen (heurística, no clave directa)

No es una tabla propia. Se calcula en `matching.py` buscando compras (`dbo.Compras`) del mismo `IdContacto`, con `Fecha` e importe compatibles con el movimiento de tesorería (clarificación 2026-09-15).

| Campo (API) | Descripción |
|---|---|
| estado | `"sin_coincidencia"` \| `"coincidencia_unica"` \| `"ambigua"` |
| candidatas | Lista de 0, 1 o N compras candidatas (`idCompra`, `numeroDocumento`, `proveedor`, `fecha`, `importe`) |

El API MUST devolver siempre el campo `estado` explícito; el frontend nunca debe inferir "sin coincidencia" a partir de una lista vacía sin ese campo (FR-005).

**Excepción confirmada (2026-09-16)**: para movimientos de `Valores propios` (que no tiene campo de contacto), el API MUST devolver siempre `estado: "sin_coincidencia"` sin ejecutar ninguna búsqueda por fecha/importe — no aplicar la heurística de forma parcial.

## Archivo de resumen (Excel) — validación y previsualización

No persiste en SQL Server en esta spec. Formato de origen confirmado contra archivos reales (2026-09-16):

**Galicia** (`.xlsx`, hoja `Movimientos`, encabezado en fila 1):

| Columna Excel | Campo previsualizado (API) |
|---|---|
| `Fecha` | fecha |
| `Descripción` | descripcion |
| `Débitos` | debitos |
| `Créditos` | creditos |
| `Número de Comprobante` | numeroComprobante |
| `Leyendas Adicionales 1-4` | leyendas (array, contraparte disperso, no estructurado) |
| `Saldo` | saldo |

**BNA** (`.xls`, formato binario antiguo, **5 filas de metadata antes del encabezado real** en la fila 6):

| Columna Excel | Campo previsualizado (API) |
|---|---|
| `Fecha` | fecha |
| `Comprobante` | comprobante |
| `Concepto` | concepto |
| `Importe` | importe (parseado desde texto `"$ 1.234,56"` a número; negativo si viene con `-`) |
| `Saldo` | saldo (mismo parseo) |

Modelo transitorio en memoria (respuesta del endpoint):

| Campo (API) | Descripción |
|---|---|
| medioDetectado | `"bna"` \| `"galicia"` \| `null` si no coincide con ningún formato conocido |
| valido | boolean |
| errores | lista de strings (si `valido = false`, explica qué columna/formato no coincide, ej. "no se encontró la fila de encabezado 'Fecha, Comprobante, Concepto, Importe, Saldo' en las primeras 10 filas") |
| movimientosPrevisualizados | lista de movimientos parseados según la tabla del medio detectado, sin `id` (no persistidos) |

**Nota**: ninguno de los dos formatos trae una columna de contacto estructurada (ver `research.md`); la previsualización de Excel no intenta resolver `estado`/`candidatas` de coincidencia con compras — eso solo aplica a movimientos ya existentes en SQL Server.

## Validaciones y reglas transversales

- Ninguna entidad de este módulo admite escritura real (FR-010); el endpoint de Excel solo válida y previsualiza (FR-008).
- Las columnas de imputación heredadas (`Movimientos Galicia`) MUST quedar excluidas del contrato de API (FR-006).
- Toda consulta de movimientos MUST ser parametrizada, paginada y filtrable por rango de fechas (FR-003, FR-013).
