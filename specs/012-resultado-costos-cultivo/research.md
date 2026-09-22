# Research: Resultado y Costos de Cultivo

## 1. Fuente de superficie sembrada por Cultivo/Campaña

**Unknown**: la spec pide mostrar superficie sembrada por Cultivo/Campaña (FR-003), pero la única vista heredada agregada (`vw_ResultadoCultivo_Campaña`) trae `SuperficieTotal` solo a nivel de Campaña completa (sin desglose por Cultivo), y las tablas que sí parecían diseñadas para ese desglose (`ResultadoCultivo_Resumen`, y su vista `vw_ResultadoCultivo_Resumen`, que es un simple `SELECT * FROM ResultadoCultivo_Resumen` con dos columnas calculadas agregadas) están **ambas vacías (0 filas)** — confirmado con `OBJECT_DEFINITION`.

**Decision**: usar **`PlanAgricola`** (233 filas reales, tabla nueva construida en 011 — qué lote se destina a qué Cultivo/Campaña) como fuente de superficie sembrada: `SUM(Lotes.Superficie) FROM PlanAgricola JOIN Lotes GROUP BY IdCultivo, IdCampaña`. Verificado con datos reales (ej. Soja primera 2026/2027 → 89 ha, Girasol 2026/2027 → 78,1 ha, coincide con la superficie real de los lotes planificados).

**Rationale**: es la única fuente estructurada, no vacía, y ya construida específicamente para responder "qué Cultivo va en qué Lote en qué Campaña" — exactamente la pregunta que hace falta. Además es de carga activa (el módulo de Planificación Agrícola de 011 ya la mantiene), a diferencia de `ResultadoCultivo_Cierre` (43 filas, mayormente auto-estimadas).

**Alternatives considered**:
- `vw_TotSuperficiePorCultivoCampania` (agregada desde `Ordenes_Lotes`, heredada): rechazada porque mide superficie *afectada por una orden de labor*, no necesariamente toda la superficie sembrada (un lote sembrado sin ninguna orden de labor registrada no aparecería).
- Reconstruir desde `ResultadoCultivo_Resumen`: rechazada, tabla vacía sin ningún dato que migrar.

## 2. Fuente de superficie cosechada y superficie picada

**Decision**: superficie cosechada = `ResultadoCultivo_Cierre.SuperficieCosechada` (43 filas reales, JOIN por `IdCultivo`+`IdCampaña`). Si no hay fila para ese Cultivo/Campaña, se muestra "—" (no se asume 0, que implicaría "cosecha nula" en vez de "sin dato").

Superficie picada: **sin fuente estructurada encontrada** en ninguna tabla/vista real de `WC` (la columna `SupPicada` solo existe en las tablas vacías `ResultadoCultivo_Resumen`/`vw_ResultadoCultivo_Resumen`). Se muestra siempre como "—" en este corte — no se inventa un cálculo. Documentado como limitación conocida, no como bug.

**Rationale**: no hay ninguna fuente real de "superficie picada" hoy en `WC`; forzar un valor sería inventar un dato. Mantener el campo en la UI para pasturas/verdeos, con guion, deja la puerta abierta si en el futuro se carga.

**Hallazgo durante la implementación (2026-09-22)**: la cantidad cosechada (numerador del rinde) tampoco tenía fuente documentada en el research original. Encontrada la tabla heredada `Datos Cosecha` (225 filas reales, columnas `IdDestino`, `IdCampaña`, `[Cantidad a Liquidar]` — kg entregados/liquidados por remito de cosecha) — **decisión**: `cantidadCosechada = SUM([Cantidad a Liquidar]) FROM [Datos Cosecha] WHERE IdDestino = ? AND IdCampaña = ?`, vía `idCultivo_a_destino` (mismo `IdDestino` que el costeo). Si no hay filas, `cantidadCosechada = None` (rinde "—", no 0).

## 3. Traducción Cultivo → claves heredadas (`Map_CultivoResultado`)

**Decision**: `Map_CultivoResultado` es 1:1 por Cultivo (11 filas, verificado). Cada fila expone dos claves independientes:
- `IdDestino` → JOIN con `vw_ResultadosCultivo_CostosBase`, `CostosAgrupados`, `Seguros` (por `IdDestino` + `IdCampaña`).
- `IdGrano` → JOIN con `vw_ResultadosCultivo_Ventas`, `Deducciones` (vía `[Venta Granos].IdProducto = Map_CultivoResultado.IdGrano`, agrupado por `IdCultivo` + `Campaña` texto).

7 de 17 `IdDestino` usados en las vistas de costeo no tienen fila en `Map_CultivoResultado` (huérfanos) — esos costos quedan sin Cultivo asignable; se excluyen del resultado por Cultivo y se muestran agregados como costo "sin clasificar" a nivel de Campaña (FR-012), igual que las filas con `IdCampaña NULL`.

Pastura tiene `IdGrano NULL` ("sin venta como grano") — el JOIN de Ventas/Deducciones no le aporta filas; se maneja como "sin venta" (no como error), rinde "—".

**Rationale**: confirmado por el agente `01-sql-server-engineer` contra `WC` real; evita el error del borrador inicial de la spec (que asumía relación 1:N).

## 4. Traducción Campaña (texto) → `IdCampaña` (numérico)

**Decision**: JOIN `Campañas.Campaña = <texto de la vista>` para obtener `IdCampaña`. Confirmado que todos los formatos reales (`"YYYY/YYYY+1"`, `"YYYY"` suelto, `"No Aplica"`) existen como filas válidas en `Campañas` (32 filas) — ninguna Campaña usada en `vw_ResultadosCultivo_Ventas`/`Deducciones` queda huérfana.

## 5. Cálculo de la "Campaña actual" (FR-001)

**Decision**: parsear el nombre de la Campaña con una expresión regular sobre dos formatos:
- `^(\d{4})/(\d{4})$` → cubre aproximadamente del 1° de julio del primer año al 30 de junio del segundo año (campaña agrícola típica, siembra de invierno/verano combinadas).
- `^(\d{4})$` → cubre el año calendario completo (1° de enero al 31 de diciembre).
- Cualquier otro valor (ej. `"No Aplica"`) no es parseable → se excluye de la comparación.

La Campaña "actual" es aquella cuyo rango contiene la fecha de hoy. Si ninguna coincide (fecha fuera de todo rango, o hay un hueco entre campañas), se cae a la Campaña más reciente con algún dato cargado (`MAX` de `IdCampaña` entre las que tienen fila en `vw_ResultadosCultivo_CostosBase`, `Ventas` o `Ordenes_Trabajo` vía `PlanAgricola`).

**Rationale**: `Campañas` no tiene columnas de fecha (verificado); es la única forma de derivar "actual" sin agregar una columna nueva a una tabla heredada (fuera de alcance — este módulo es de solo lectura).

**Alternatives considered**: agregar una columna `FechaInicio`/`FechaFin` a `Campañas` — rechazada, es una tabla heredada compartida por todo el sistema (Compras, Ventas, Órdenes de Trabajo) y el módulo es de solo lectura; cambiar su esquema está fuera de alcance de esta spec.

**Hallazgo durante la implementación (2026-09-22)**: una Campaña `"YYYY/YYYY+1"` y una `"YYYY"` suelta pueden contener la misma fecha de hoy simultáneamente — confirmado con datos reales: `"2026/2027"` (id 32) y `"2026"` (id 25) ambas activas y con datos (`PlanAgricola`, costos) al 2026-09-22. No estaba contemplado en la decisión original. Resuelto con un desempate explícito: se prioriza `"YYYY/YYYY+1"` (la campaña agrícola típica del sistema) por sobre `"YYYY"` cuando ambas coinciden.

## 6. Prevención de doble conteo (FR-004)

**Decision**: al sumar el costo de contratista de una Orden de Trabajo (`Ordenes_Trabajo_Contratista_Factura.IdCompra`), excluir explícitamente cualquier `IdCompra` que ya aparezca en `vw_ResultadosCultivo_CostosBase` (`WHERE IdCompra NOT IN (SELECT IdCompra FROM vw_ResultadosCultivo_CostosBase)` o equivalente por `LEFT JOIN ... IS NULL`). Cubrir con un test unitario que simule el caso (hoy no reproducible con datos reales: `Ordenes_Trabajo_Contratista_Factura` está vacía), para que quede blindado antes de que se cargue el primer dato real.

**Rationale**: hallazgo del agente `01-sql-server-engineer` — riesgo estructural real vía la FK compartida a `Compras`, aunque hoy no se manifiesta.

## 7. Patrón de exportación multi-hoja

**Decision**: reutilizar el patrón ya usado en `backend/src/features/ordenes/exportacion.py` (helper `_hoja()` reutilizable, un `Workbook` con `ws = wb.active` para la primera hoja y `wb.create_sheet()` para las siguientes). Dos hojas: "Resultado" (una fila por Cultivo/Campaña de lo exportado) y "Detalle de costos" (una fila por línea de costo, con su origen).

**Rationale**: consistencia con el patrón ya validado en 010/011; sin necesidad de investigación adicional.

## 8. Trazabilidad a la línea de origen (FR-007)

**Decision**: cada línea de `vw_ResultadosCultivo_CostosBase` ya expone `IdCompra`/`IdDetalleCompra` — se muestran como texto (el módulo de Compras aún no está migrado a la web, así que no hay a dónde linkear todavía). Las líneas originadas en `Ordenes_Trabajo_*` sí tienen link "Ver orden" hacia `/produccion/ordenes/[idOrden]` (módulo 011, ya en producción).

**Rationale**: confirmado por el agente `07-financial-direction-specialist` (necesidad real) y `09-agroux-lead-product-architect` (mecanismo de navegación); limitado por lo que efectivamente está migrado hoy.


**Decisión del usuario (2026-09-22)**: los costos sin clasificar se muestran aparte, sin sumarlos al costo total de la campaña ni afectar su margen, rentabilidad o costo por hectárea. El total consolidado es la suma de los cultivos. El importe informativo incluye destinos sin cultivo de la campaña consultada y costos sin campaña asignada de todo el sistema; estos últimos no se atribuyen a la campaña seleccionada.


## Aclaración de costeo aplicada — 2026-09-22

El usuario aclaró que el contratista se costea por su factura y la maquinaria propia por el estimado por hectárea ingresado manualmente en su formulario. En 012, las facturas vinculadas se toman por sus renglones de `Det_Compras`, con el destino y la campaña registrados; no se reparten por superficie ni por cantidad de insumos. Una factura que ya aparece en CostosBase no vuelve a sumarse por la orden. Los identificadores de factura y renglón se conservan en el detalle. Vincular la misma factura a varias órdenes no multiplica sus renglones; se muestra como referencia la primera orden vigente vinculada.

Maquinaria propia nueva: se usa `CostoPorHectarea` manual y la superficie registrada del lote de la orden, una vez por lote (máxima superficie registrada para ese lote dentro del cultivo/campaña cuando se repite entre insumos). No hay tarifa calculada ni catálogo de tarifas. `TipoCambioBna`, cuando fue registrado, permite expresar ese estimado en dólares; si falta, el detalle no inventa conversión. La maquinaria heredada conserva los importes de su formulario incluidos en CostosBase y se identifica como `MaquinariaPropia`.

Verificación del SQL real: CostosBase ya firma `Pesos` y `Dolares` en notas de crédito. Se normaliza `ABS(importe) × Signo`, evitando volver a convertir el crédito en cargo. Esta corrección reemplaza cualquier indicación previa de multiplicar directamente el importe firmado por Signo.

El motor FIFO existente entrega los costos de insumos de órdenes en pesos. La serie en dólares de esos insumos no está reconstruida en este corte; no se debe interpretar su cero actual como una conversión validada. Esta limitación debe resolverse antes de considerar completos los indicadores en dólares cuando incluyen esas órdenes.
