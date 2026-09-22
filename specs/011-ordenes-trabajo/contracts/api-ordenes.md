# API Contract: `/api/ordenes` (011-ordenes-trabajo)

Estilo y convenciones idénticas a `/api/remitos` (010-remitos): errores de negocio → 400 con lista de mensajes; confirmaciones pendientes (ej. stock insuficiente) → 409; escritura exclusiva contra `WC`.

## Cabecera de orden

### `GET /api/ordenes`
Listado paginado. Query params: `idContratista`, `idLote`, `idCultivo`, `idCampania`, `fechaDesde`, `fechaHasta`, `estado` (`planificada|ejecutada|anulada`), `page`, `pageSize`.

### `GET /api/ordenes/{idOrden}`
Detalle completo: cabecera, renglones de insumo con su distribución, maquinaria, factura de contratista vinculada, devoluciones, estado del Formulario de Retiro.

### `POST /api/ordenes`
Body: `OrdenIn` — fecha, idTipoLabor, idContratistaContacto | maquinaria[], renglones de insumo con sus distribuciones (lote, cultivo, campaña, dosisHa, superficie, aplicar).
- Valida que cada renglón de insumo cierre exactamente (FR-004) antes de guardar.
- Descuenta stock por FIFO (reutiliza `remitos.stock_fifo`).
- Si el consumo supera el stock disponible → 409 `RequiereConfirmacion` (igual que Remitos), reintentar con `confirmar: true`.
- Genera el Formulario de Retiro con su numeración propia.
- Devuelve la orden creada en estado `Planificada`.

### `PATCH /api/ordenes/{idOrden}`
Edición libre solo si `Estado = Planificada` y no tiene devoluciones ni factura de contratista vinculada (FR-007). Mismo shape que `POST`.

### `POST /api/ordenes/{idOrden}/ejecutar`
Body: `{ fechaEjecucion: date }`. Transición `Planificada → Ejecutada`.

### `POST /api/ordenes/{idOrden}/anular`
Body: `AnularIn { motivo: string }`. Devuelve las capas FIFO de stock consumidas por la orden (recalcula, no bloquea, igual que Remitos).

## Devoluciones

### `POST /api/ordenes/{idOrden}/insumos/{idOrdenInsumo}/devoluciones`
Body: `{ fecha: date, cantidad: number, observaciones?: string }`.
- Rechaza si `cantidad` supera lo retirado y no devuelto de ese renglón.
- Reingresa la cantidad al stock como nueva capa de entrada.
- Recalcula el cierre del renglón (FR-004).

## Maquinaria propia

### `POST /api/ordenes/{idOrden}/maquinaria`
Body: `{ descripcion: string, costoPorHectarea: number, tipoCambioBna?: number }`.
- Prorratea el costo entre los lotes de la orden por superficie.

## Contratista y factura

### `POST /api/ordenes/{idOrden}/factura`
Body: `{ idCompra: number }` — vincula la factura del contratista (misma mecánica que `Remitos_Facturas`).
- El tipo de cambio de dolarización se toma de `Compras.tipoDeCambio` de esa factura.

## Costo y resultado por Cultivo/Campaña (Historia 6)

### `GET /api/ordenes/resultado-cultivo`
Query params: `idCultivo?`, `idCampania?`, `idLote?`.
- Devuelve costo total (insumos FIFO + maquinaria + contratistas) por Cultivo/Campaña, en pesos y dólares, conectando con `vw_ResultadoCultivo_Campaña` y vistas relacionadas (sin modificarlas).
- Sin restricción de fecha de cierre (FR-015): incluye costos posteriores a la cosecha.

### `GET /api/ordenes/resultado-cultivo/exportar`
Export a Excel con los mismos filtros (FR-019).

## Catálogo de Tipos de Labor (Historia 7)

### `GET /api/ordenes/tipos-labor`
### `POST /api/ordenes/tipos-labor`
Body: `{ nombre: string }`. Alta de un nuevo tipo de labor.

## Formulario de Retiro

### `GET /api/ordenes/{idOrden}/formulario-retiro`
Devuelve el documento (datos + número secuencial) listo para exportar/imprimir (FR-008).

### `GET /api/ordenes/{idOrden}/formulario-retiro/exportar`
Export a Excel/PDF del listado de insumos a preparar.
