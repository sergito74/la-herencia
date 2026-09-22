# API Contract: `/api/resultado-cultivo` (012-resultado-costos-cultivo)

Módulo 100% de solo lectura: todos los endpoints son `GET`. Errores de negocio (ej. Campaña/Cultivo inexistente) → 404. Sin `POST`/`PATCH`/`DELETE` en este módulo (FR-013).

## Catálogo

### `GET /api/resultado-cultivo/campanias`
Listado de Campañas (`idCampania`, `campania`), igual catálogo que `/api/ordenes/catalogos`. `campaniaActualId` incluido en la respuesta: el resultado de aplicar la regla de FR-001 (research.md §5).

## Resultado

### `GET /api/resultado-cultivo/campania/{idCampania}`
`ResultadoCampania` completo (Historia 1): tarjetas KPI consolidadas + `cultivos: ResultadoCultivoResumen[]` (una fila por Cultivo, sin el detalle de costos). Incluye `costoSinClasificar` si aplica (FR-012).

### `GET /api/resultado-cultivo/campania/{idCampania}/cultivo/{idCultivo}`
`ResultadoCultivo` completo de un Cultivo puntual (Historia 2): superficie, rinde, costo, costo/ha, venta, margen, rentabilidad, `supCosechaEstimada`, `advertenciaMargenNoRepresentativo`. No incluye `detalleCostos` (endpoint separado, para no traer el desglose completo cuando solo hace falta el resumen).

### `GET /api/resultado-cultivo/campania/{idCampania}/cultivo/{idCultivo}/costos`
`DetalleCosto[]` (Historia 3): una fila por línea de costo, agrupable en el cliente por `concepto`/`rubro`. Cada línea trae `origen` (`Compra` | `OrdenTrabajo` | `Seguro`) y su identificador de origen (`idCompra`/`idDetalleCompra` como texto, o `idOrdenTrabajo` con link).

### `GET /api/resultado-cultivo/campania/{idCampania}/exportar`
Excel de 2 hojas ("Resultado", "Detalle de costos") de todos los Cultivos con datos en esa Campaña (Historia 4). `Content-Disposition: attachment; filename="resultado-cultivo-{campania}.xlsx"`.

### `GET /api/resultado-cultivo/campania/{idCampania}/cultivo/{idCultivo}/exportar`
Mismo archivo, acotado a un solo Cultivo (exportar desde la vista de detalle, Historia 2).


**Decisión del usuario (2026-09-22)**: los costos sin clasificar se muestran aparte, sin sumarlos al costo total de la campaña ni afectar su margen, rentabilidad o costo por hectárea. El total consolidado es la suma de los cultivos. El importe informativo incluye destinos sin cultivo de la campaña consultada y costos sin campaña asignada de todo el sistema; estos últimos no se atribuyen a la campaña seleccionada.


## Aclaración de costeo aplicada — 2026-09-22

El usuario aclaró que el contratista se costea por su factura y la maquinaria propia por el estimado por hectárea ingresado manualmente en su formulario. En 012, las facturas vinculadas se toman por sus renglones de `Det_Compras`, con el destino y la campaña registrados; no se reparten por superficie ni por cantidad de insumos. Una factura que ya aparece en CostosBase no vuelve a sumarse por la orden. Los identificadores de factura y renglón se conservan en el detalle. Vincular la misma factura a varias órdenes no multiplica sus renglones; se muestra como referencia la primera orden vigente vinculada.

Maquinaria propia nueva: se usa `CostoPorHectarea` manual y la superficie registrada del lote de la orden, una vez por lote (máxima superficie registrada para ese lote dentro del cultivo/campaña cuando se repite entre insumos). No hay tarifa calculada ni catálogo de tarifas. `TipoCambioBna`, cuando fue registrado, permite expresar ese estimado en dólares; si falta, el detalle no inventa conversión. La maquinaria heredada conserva los importes de su formulario incluidos en CostosBase y se identifica como `MaquinariaPropia`.

Verificación del SQL real: CostosBase ya firma `Pesos` y `Dolares` en notas de crédito. Se normaliza `ABS(importe) × Signo`, evitando volver a convertir el crédito en cargo. Esta corrección reemplaza cualquier indicación previa de multiplicar directamente el importe firmado por Signo.

El motor FIFO existente entrega los costos de insumos de órdenes en pesos. La serie en dólares de esos insumos no está reconstruida en este corte; no se debe interpretar su cero actual como una conversión validada. Esta limitación debe resolverse antes de considerar completos los indicadores en dólares cuando incluyen esas órdenes.
