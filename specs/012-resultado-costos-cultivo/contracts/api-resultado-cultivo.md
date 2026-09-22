# API Contract: `/api/resultado-cultivo` (012-resultado-costos-cultivo)

Módulo 100% de solo lectura: todos los endpoints son `GET`. Errores de negocio (ej. Campaña/Cultivo inexistente) → 404. Sin `POST`/`PATCH`/`DELETE` en este módulo (FR-013).

## Catálogo

### `GET /api/resultado-cultivo/campanias`
Listado de Campañas (`idCampania`, `campania`), igual catálogo que `/api/ordenes/catalogos`. `campaniaActualId` incluido en la respuesta: el resultado de aplicar la regla de FR-001 (research.md §5).

## Resultado

### `GET /api/resultado-cultivo/campania/{idCampania}`
`ResultadoCampania` completo (Historia 1): tarjetas KPI consolidadas + `cultivos: ResultadoCultivoResumen[]` (una fila por Cultivo, sin el detalle de costos). Incluye `costoSinClasificar` si aplica (FR-012).

### `GET /api/resultado-cultivo/campania/{idCampania}/cultivo/{idCultivo}`
`ResultadoCultivo` completo de un Cultivo puntual (Historia 2): superficie, rinde, costo, costo/ha, venta, margen, rentabilidad, `costeoIncompleto`, `advertenciaMargenNoRepresentativo`. No incluye `detalleCostos` (endpoint separado, para no traer el desglose completo cuando solo hace falta el resumen).

### `GET /api/resultado-cultivo/campania/{idCampania}/cultivo/{idCultivo}/costos`
`DetalleCosto[]` (Historia 3): una fila por línea de costo, agrupable en el cliente por `concepto`/`rubro`. Cada línea trae `origen` (`Compra` | `OrdenTrabajo` | `Seguro`) y su identificador de origen (`idCompra`/`idDetalleCompra` como texto, o `idOrdenTrabajo` con link).

### `GET /api/resultado-cultivo/campania/{idCampania}/exportar`
Excel de 2 hojas ("Resultado", "Detalle de costos") de todos los Cultivos con datos en esa Campaña (Historia 4). `Content-Disposition: attachment; filename="resultado-cultivo-{campania}.xlsx"`.

### `GET /api/resultado-cultivo/campania/{idCampania}/cultivo/{idCultivo}/exportar`
Mismo archivo, acotado a un solo Cultivo (exportar desde la vista de detalle, Historia 2).
