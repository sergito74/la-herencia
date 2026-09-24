# Research: Motor de auto-clasificación de Rubro/Centro de Costos/Cultivo/Campaña

## Esquema real confirmado (código actual, 2026-09-23)

### Cadena de trazabilidad de un insumo

`Compras`/`Det_Compras` (factura) → `tblRemitoCompra` (vínculo renglón factura↔renglón remito, fuente de verdad; `Remitos_Facturas` es solo el vínculo a nivel documento, sincronizado automáticamente) → `Remitos_Detalles`/`Remitos` (entrada de stock, capa FIFO `R{IdDetalleRemito}`) → `stock_fifo.asignar_fifo()` (consumo FIFO en memoria, sin persistir) → salida `OT{IdOrdenInsumo}` (`Ordenes_Trabajo_Insumos`) → `Ordenes_Trabajo_Distrib` (reparto por `IdLote`/`IdCultivo`/`IdCampania`, peso `DosisHa × Superficie`).

Columnas exactas relevantes:
- `Det_Compras`: `IdRubro`, `IdCentroCostos` (con "s" final), `IdDestino`, `IdCampaña` (id + texto). Defaults al cargar: `DEFAULT_CENTRO_COSTO = "Adm. General"`, `DEFAULT_DESTINO = "General"`, `DEFAULT_CAMPANIA = "No Aplica"` (`compras/repository.py`).
- `tblRemitoCompra`: `IdRemitoCompra` PK, `IdDeuda`, `IdDetalleRemito`, `IdDetalleCompra`, `CantidadRemitida`, `DescripFormuladoRemito`, `DescripProductoFactura`.
- `Ordenes_Trabajo_Insumos`: `IdOrdenInsumo` PK, `IdOrdenTrabajo`, `IdProducto`, `CantidadTotal` (neta de devoluciones), `Unidad`.
- `Ordenes_Trabajo_Distrib`: `IdDistrib` PK, `IdOrdenInsumo` FK, `IdLote`, `IdCultivo`, `IdCampania`, `DosisHa`, `Superficie`, `CantidadAsignada`, `Aplicar`.
- `Ordenes_Trabajo`: `IdOrdenTrabajo` PK, `Estado` (`Planificada`/`Ejecutada`/`Anulada`), `IdRubro` (NULL cuando la orden sí tiene cultivo — `resultado.py` filtra `ot.IdRubro IS NULL` para separar órdenes agrícolas de las de mantenimiento).

**Decisión — Punto de entrada al motor**: se reutiliza `stock_fifo.asignar_fifo()` (ya calcula, para cada salida `OT{id}`, de qué capa(s) `R{IdDetalleRemito}` salió y con qué costo — campo `items[].capa`) en vez de reimplementar el FIFO. El motor nuevo agrega un paso más: de cada capa `R{IdDetalleRemito}` remonta a `tblRemitoCompra` → `Det_Compras.IdDetalleCompra` para saber a qué renglón de factura corresponde, y de la distribución de la orden (`Ordenes_Trabajo_Distrib`) obtiene a qué Lote/Cultivo/Campaña se imputa.
**Rationale**: `asignar_fifo` ya expone exactamente la trazabilidad capa→consumo que pide FR-013; reimplementar el FIFO duplicaría lógica ya probada (010) y arriesgaría una fuente de verdad distinta a la que ya usa `resultado.py` (012) para el motor heredado con el que hay que comparar (Historia 5).
**Alternatives considered**: persistir el FIFO en una tabla (`Stock_Consumos_Capa`) fue evaluado y descartado en 010 mismo ("no hace falta la tabla prevista") — se mantiene ese criterio acá también.

### Vínculo factura de contratista↔Orden (corrección importante sobre la spec)

`Ordenes_Trabajo_Contratista_Factura(IdOrdenTrabajo, IdCompra)` **ya existe y ya persiste el vínculo** (spec 011) — pero es estrictamente **1 a 1**: `vincular_factura_contratista()` lanza error si la Orden ya tiene una factura cargada. La spec 017 (Clarifications, respuesta a la pregunta 11) confirmó con el usuario que una factura real puede cubrir varias Órdenes — el modelo actual no lo soporta.

**Decisión**: generalizar esta tabla a N a N (una fila por par Orden↔Factura, sin restricción de unicidad por Orden), en vez de crear una tabla paralela. `costeo.py::costo_contratista(id_compra, distribuciones)` y `resultado.py::_filas_maquinaria_y_contratista()` ya leen desde esta tabla — al generalizarla siguen funcionando sin cambios (ambas ya iteran por filas, no asumen una sola).
**Rationale**: evita mantener dos tablas con el mismo significado de negocio; el único cambio es remover la restricción de unicidad y permitir múltiples filas por Orden.
**Alternatives considered**: tabla nueva paralela (`Ordenes_Contratista_Facturas_N_N`) — rechazada por duplicar significado y complicar `resultado.py`, que ya lee de la tabla actual.

### Rubro/Centro de Costos "Adm. General"

Confirmado en código como el *default* que ya usa Compras (`DEFAULT_CENTRO_COSTO = "Adm. General"`, `compras/repository.py`) — no es un valor nuevo a inventar. `Ordenes_Trabajo.IdRubro IS NOT NULL` ya es, en el código de 012 (`resultado.py`), el marcador de "orden sin cultivo específico". El motor nuevo reutiliza ambos: cuando una Orden tiene `IdRubro` seteado (sin cultivo), su consumo se imputa a Centro de Costos "Adm. General" con ese Rubro, replicando el criterio ya usado por 012.

### Endpoint agregador remito→orden→distribución

No existe hoy un endpoint único que junte esta cadena — hay que construirlo. El FIFO se resuelve en memoria (Python) sobre todas las capas/salidas de un producto (`calcular_stock`), no en SQL. Para un motor que tiene que recorrer potencialmente miles de renglones de factura, correr `calcular_stock` por producto en cada consulta puede ser costoso.

**Decisión — Persistencia**: el motor calcula al vuelo (reusa `calcular_stock`) para volúmenes bajos/medios (validado con los datos reales: 215 remitos, 467 renglones, 153 órdenes — spec 010/011), pero expone su resultado a través de una tabla de **snapshot recalculable** (`ImputacionPropuestas`, ver data-model.md) en vez de una vista en vivo: la propuesta se recalcula y se vuelve a escribir en esa tabla cada vez que cambia un dato fuente relevante (remito recargado, distribución corregida, capa FIFO revinculada), en vez de recalcularse en cada GET. Esto resuelve "recalcula silenciosamente" (Clarifications) sin pagar el costo de recorrer la cadena completa en cada consulta de la lista de propuestas.
**Rationale**: la spec deja la decisión de performance "a criterio técnico, optimizando por eficiencia de recursos" — con los volúmenes reales confirmados (cientos de renglones, no millones), un recálculo por evento (no por request) es suficientemente eficiente y evita tanto la complejidad de una vista materializada SQL como la latencia de recalcular todo el FIFO en cada carga de pantalla.
**Alternatives considered**: (a) vista SQL materializada — más compleja de mantener sincronizada con la lógica Python del FIFO, que ya vive fuera de SQL; (b) cálculo 100% al vuelo sin tabla — descartado porque la propuesta necesita un estado persistente (pendiente/aprobada/requiere intervención) que por definición no puede ser un cálculo puro.

### Umbral de "diferencia grande" (FR-010)

**Decisión**: 5% del total de la factura de contratista, con un piso absoluto de $10.000 (para que facturas chicas con error de redondeo de céntimos no disparen falsa alarma, y facturas grandes no toleren un desvío proporcionalmente enorme). Documentado como constante configurable (`UMBRAL_INCONSISTENCIA_PORCENTAJE`, `UMBRAL_INCONSISTENCIA_MONTO_MINIMO`), no hardcodeada sin nombre.
**Rationale**: no hay dato real para calibrar (a diferencia de la tolerancia de conciliación de tarjetas, spec 009, que sí tuvo datos históricos) — se documenta como punto de partida ajustable, consistente con cómo se calibraron otros umbrales del sistema (spec 009: "tolerancia $0.10 con diferencia siempre expuesta").
**Alternatives considered**: umbral fijo en pesos sin porcentaje — rechazado porque no escala entre una factura de $50.000 y una de $5.000.000.

### Reparto Agricultura/Ganadería de un insumo (FR-001, Clarifications)

**Decisión**: el consumo "ganadero" de un insumo (el que no pasa por una Orden de Trabajo, que es un concepto agrícola por lote/cultivo/campaña — spec 011) se rastrea vía las bajas de stock ya existentes: `dbo.Stock_Bajas_Detalle`/`dbo.Stock_Bajas` (spec 010, Historia 4 — "dar de baja del stock productos que salen sin haber sido usados en una orden de trabajo"), que ya traen `IdRubro`/`IdCentro` por baja y ya son una salida FIFO reconocida por `stock_datos.calcular_stock()` (id `B{IdBajaDetalle}`). El motor interpreta una baja cuyo `IdCentro` resuelve a un Centro de Costos de Ganadería como consumo ganadero; el resto de las bajas (ej. "Pérdidas y bajas de insumos", "Mantenimiento") no son ni agrícolas ni ganaderas y se imputan directo a su Centro de Costos, igual que las Órdenes sin cultivo.
**Rationale**: es el único mecanismo real hoy en el sistema para registrar una salida de stock que no es consumo agrícola por Orden de Trabajo — no existe ningún concepto de "Orden de Trabajo ganadera" en el modelo actual (011 es explícitamente agrícola: Lote/Cultivo/Campaña). Introducir un concepto nuevo de "consumo ganadero" sin reutilizar las bajas ya existentes duplicaría un flujo que spec 010 ya resolvió para este mismo propósito genérico (salida de stock sin Orden).
**Alternatives considered**: modelar un tipo de "Orden de Trabajo ganadera" nueva — rechazado por alcance (esta spec no toca el modelo de Órdenes de Trabajo salvo el vínculo de contratista, FR-003) y porque no hay evidencia de que el usuario lo haya pedido; las bajas de stock ya cubren el caso real declarado en Clarifications ("producto usado tanto en agricultura como en ganadería").
**Riesgo documentado**: esta decisión no fue confirmada explícitamente con el usuario durante la sesión de clarificación (que se centró en el reparto Agricultura/Ganadería como resultado, no en su mecanismo de origen) — si en la práctica existe otro flujo real para registrar consumo ganadero que no sea una baja de stock, esta decisión debe revisarse antes de implementar T012/T014 (motor.py) en tasks.md.

### "Aprendizaje simple" (FR-008)

**Decisión**: se reutiliza el mismo patrón que `compras/repository.py::get_rubro_sugerido()` (spec 006, FR-012a) — al aprobar o corregir una propuesta, el sistema guarda esa clasificación final como un caso de referencia (producto + destino aprobado), y para casos futuros similares (mismo producto, patrón de consumo parecido) prioriza esa referencia en la propuesta que genera. Sin modelo entrenado ni ML — es una tabla de "última corrección por producto/contexto" consultada como prioridad antes del cálculo puro por consumo.
**Rationale**: mismo criterio arquitectónico ya usado y validado en el sistema (texto histórico exacto → sugerencia), consistente con constitución VII (simplicidad).
