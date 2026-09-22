# Data Model: Resultado y Costos de Cultivo (012)

Módulo 100% de solo lectura: no crea tablas nuevas. Las entidades de abajo son **vistas calculadas en el backend** (no persistidas), construidas en vivo en cada consulta a partir de las fuentes heredadas y de 011 listadas en `research.md`.

## Fuentes heredadas reutilizadas (solo lectura)

- **`Map_CultivoResultado`** (11 filas, 1:1 por Cultivo): `IdCultivo`, `IdDestino` (NULL para "Sin Cultivo", inactiva), `IdGrano` (NULL para Pastura), `Activo`.
- **`Campañas`** (32 filas): `IdCampaña`, `Campaña` (texto, formatos `"YYYY/YYYY+1"` / `"YYYY"` / `"No Aplica"`). Se traduce en ambos sentidos: texto→id para las vistas de costeo (`IdCampaña` numérico) e id→texto para las vistas de venta (`Campaña` texto) — ver `mapeo.py` en `plan.md`.
- **`vw_ResultadoCultivo_Campaña`**: total consolidado por Campaña (sin desglose por Cultivo) — usado como verificación cruzada de FR-014, no como fuente primaria (el consolidado se recalcula sumando los Cultivos).
- **`vw_ResultadosCultivo_CostosBase`**: línea de costo con `IdDestino`, `IdCampaña` (nullable), `IdCompra`, `IdDetalleCompra`, `Concepto`, `Item`, `Pesos`, `Dolares`, `Signo` (1 cargo / -1 crédito).
- **`vw_ResultadosCultivo_CostosAgrupados`**: mismo costo, agrupado por `Concepto`/`IdRubro`.
- **`vw_ResultadosCultivo_Seguros`**: `IdDestino`, `IdCampaña`, `SeguroPesos`, `SeguroDolares`.
- **`vw_ResultadosCultivo_Ventas`**: `IdCultivo`, `Campaña` (texto), `VentaPesos`, `VentaDolares`, `BonifPesos`, `BonifDolares`.
- **`vw_ResultadosCultivo_Deducciones`**: `IdCultivo`, `Campaña` (texto), `Detalle`, `Pesos`, `Dolares`.
- **`ResultadoCultivo_Cierre`** (43 filas): `IdCultivo`, `IdCampaña`, `SuperficieCosechada`, fechas de cosecha.
- **`PlanAgricola`** (233 filas, 011): `IdLote`, `IdCultivo`, `IdCampaña` → join con `Lotes.Superficie` da la superficie sembrada real.
- **`Ordenes_Trabajo_Insumos`**, **`Ordenes_Trabajo_Maquinaria`**, **`Ordenes_Trabajo_Contratista_Factura`** (011): costo de insumos/maquinaria/contratista de las órdenes nuevas, ya imputado a Cultivo/Campaña vía `Ordenes_Trabajo_Distrib`.

## Entidades calculadas

### `ResultadoCampania` (Historia 1 — pantalla de entrada)

| Campo | Origen |
|---|---|
| idCampania, campania | `Campañas` |
| superficieSembrada | `SUM` de `ResultadoCultivo` de todos sus Cultivos |
| costoTotalPesos/Dolares | `SUM` de `ResultadoCultivo.costoTotal*` de todos sus Cultivos; excluye el costo sin clasificar (ver `CostoSinClasificar`) |
| ventaNetaPesos/Dolares | `SUM` de `ResultadoCultivo.ventaNeta*` |
| margenBrutoPesos/Dolares | ventaNeta − costoTotal (por moneda, series independientes) |
| rentabilidadPesos/Dolares | margenBruto / costoTotal (por moneda) |
| costoPorHectareaSembradaPesos/Dolares | costoTotal / superficieSembrada si > 0, si no `null` — válido consolidar (división de sumas) |
| cultivos | lista de `ResultadoCultivoResumen` (una fila por Cultivo con datos en la Campaña) |
| costoSinClasificar | ver `CostoSinClasificar` |

`ResultadoCampania` **no incluye `rinde`**: sumar/promediar rinde de Cultivos distintos no es un número agronómicamente comparable (spec.md FR-003, corregido en `/speckit-analyze` hallazgo U1) — el rinde solo existe a nivel de `ResultadoCultivo`.

Invariante (FR-014, SC-004): `costoTotal`/`ventaNeta`/`margenBruto` de `ResultadoCampania` MUST igualar la suma de los mismos campos de sus `ResultadoCultivo`.

### `ResultadoCultivo` (Historia 2 — detalle por Cultivo dentro de la Campaña)

| Campo | Origen / Cálculo |
|---|---|
| idCultivo, cultivo, idCampania, campania | `Cultivos`, `Campañas` |
| superficieSembrada | `SUM(Lotes.Superficie)` vía `PlanAgricola` (research.md §1) |
| superficieCosechada | `ResultadoCultivo_Cierre.SuperficieCosechada`, o `null` si no hay fila |
| superficiePicada | siempre `null` en este corte (sin fuente real, research.md §2) |
| rinde | `cantidadCosechada / superficieCosechada` si `superficieCosechada > 0` y el Cultivo tiene `IdGrano` no nulo; si no, `null` (se muestra "—") |
| costoTotalPesos/Dolares | ver `DetalleCosto`, sumado, respetando `Signo` |
| costoPorHectareaSembradaPesos/Dolares | `costoTotal / superficieSembrada` si > 0, si no `null` |
| costoPorHectareaCosechadaPesos/Dolares | ídem con `superficieCosechada` |
| ventaNetaPesos/Dolares | `vw_ResultadosCultivo_Ventas` + `Bonif*` − `vw_ResultadosCultivo_Deducciones`, vía `IdGrano` |
| margenBrutoPesos/Dolares | ventaNeta − costoTotal |
| rentabilidadPesos/Dolares | margenBruto / costoTotal |
| supCosechaEstimada | `true` si la fila de `ResultadoCultivo_Cierre` de ese Cultivo/Campaña tiene `Observaciones` conteniendo "Revisar manualmente" (41 de 43 filas reales) — corregido en `/speckit-analyze` hallazgo I1: `Map_CultivoResultado` es 1:1, ningún Cultivo real tiene `IdDestino` NULL, así que esa no podía ser la condición real de FR-010 (FR-010) |
| advertenciaMargenNoRepresentativo | `true` si `ventaNeta > 0` y `costoTotal < 0.20 * ventaNeta` (FR-011) |
| detalleCostos | lista de `DetalleCosto` (Historia 3) |

### `DetalleCosto` (Historia 3 — drill-down de auditoría)

| Campo | Origen |
|---|---|
| concepto, rubro | `vw_ResultadosCultivo_CostosAgrupados` / `CostosBase.Concepto` |
| montoPesos/Dolares | `ABS(Pesos)`/`ABS(Dolares)` × `Signo` |
| origen | `"Compra"` \| `"OrdenTrabajo"` \| `"Seguro"` |
| idCompra, idDetalleCompra | de `vw_ResultadosCultivo_CostosBase`, solo si `origen = "Compra"` (mostrado como texto, sin link — Compras no migrado, research.md §8) |
| idOrdenTrabajo | de `Ordenes_Trabajo_*`, solo si `origen = "OrdenTrabajo"` (con link a `/produccion/ordenes/[idOrden]`) |

**Decisión T052 (2026-09-22)**: la línea `concepto = "Insumo"` (consumo FIFO de un renglón de Orden de Trabajo, motor reutilizado de 010) SIEMPRE trae `montoDolares = null`, nunca `0`. Se investigó reconstruir la serie histórica en dólares (camino a) y se descartó: `costo_unitario_renglon` (`backend/src/features/remitos/costeo.py`) promedia, por moneda, los vínculos factura/NC/ND de un mismo renglón de remito y sólo al final convierte el subtotal en dólares a pesos con el tipo de cambio histórico de cada vínculo — el resultado que expone `calcular_stock`/`Capa.costo_unitario` es un único monto en pesos ya mezclado, sin conservar qué fracción vino de una compra en dólares ni a qué tipo de cambio. Cuando una capa FIFO se nutre de compras en distintas monedas (caso real, no marginal) no existe una única "porción en dólares" que reconstruir sin inventar un criterio arbitrario de reparto. Se optó por el camino (b): `resultado_cultivo()` expone `costeoDolaresIncompleto = true` cuando alguna línea tiene `montoDolares = null` (`backend/src/features/resultado_cultivo/resultado.py`), y la UI (`ResultadoCultivoView.tsx`, `DetalleCostosPanel.tsx`) muestra una nota explícita ("Costos en dólares parciales…") y "Sin dato" en vez de "$0" en la línea de Insumo. Los totales/margen/rentabilidad en dólares sólo suman lo disponible y quedan señalizados como incompletos — nunca se presenta un cero engañoso.

### `CostoSinClasificar` (FR-012, a nivel de `ResultadoCampania`)

| Campo | Origen |
|---|---|
| montoPesos/Dolares | `SUM` de `vw_ResultadosCultivo_CostosBase` donde `IdCampaña IS NULL`, o `IdDestino` no está en `Map_CultivoResultado` |
| motivo | `"Sin campaña asignada"` \| `"Sin cultivo asociado (IdDestino huérfano)"` |

Este es el único lugar donde un `IdDestino` sin Cultivo asociado se hace visible — no genera ningún badge a nivel de Cultivo (ver `supCosechaEstimada` arriba, que es el badge real por Cultivo/Campaña).

## Reglas de validación / invariantes

- `costoTotal` de un `ResultadoCultivo` MUST excluir cualquier `Ordenes_Trabajo_Contratista_Factura.IdCompra` que ya exista en `vw_ResultadosCultivo_CostosBase` (FR-004, anti-doble-conteo).
- `rinde`, `costoPorHectareaSembrada`, `costoPorHectareaCosechada` MUST ser `null` (no `0` ni error) cuando el divisor es cero o no existe — nunca se divide por superficie sembrada para calcular rinde (research.md, spec Edge Cases).
- `pesos` y `dolares` de un mismo campo son series independientes (Assumptions de spec.md) — ninguna función de cálculo MUST derivar una a partir de la otra dividiendo por un tipo de cambio propio.


**Decisión del usuario (2026-09-22)**: los costos sin clasificar se muestran aparte, sin sumarlos al costo total de la campaña ni afectar su margen, rentabilidad o costo por hectárea. El total consolidado es la suma de los cultivos. El importe informativo incluye destinos sin cultivo de la campaña consultada y costos sin campaña asignada de todo el sistema; estos últimos no se atribuyen a la campaña seleccionada.


## Aclaración de costeo aplicada — 2026-09-22

El usuario aclaró que el contratista se costea por su factura y la maquinaria propia por el estimado por hectárea ingresado manualmente en su formulario. En 012, las facturas vinculadas se toman por sus renglones de `Det_Compras`, con el destino y la campaña registrados; no se reparten por superficie ni por cantidad de insumos. Una factura que ya aparece en CostosBase no vuelve a sumarse por la orden. Los identificadores de factura y renglón se conservan en el detalle. Vincular la misma factura a varias órdenes no multiplica sus renglones; se muestra como referencia la primera orden vigente vinculada.

Maquinaria propia nueva: se usa `CostoPorHectarea` manual y la superficie registrada del lote de la orden, una vez por lote (máxima superficie registrada para ese lote dentro del cultivo/campaña cuando se repite entre insumos). No hay tarifa calculada ni catálogo de tarifas. `TipoCambioBna`, cuando fue registrado, permite expresar ese estimado en dólares; si falta, el detalle no inventa conversión. La maquinaria heredada conserva los importes de su formulario incluidos en CostosBase y se identifica como `MaquinariaPropia`.

Verificación del SQL real: CostosBase ya firma `Pesos` y `Dolares` en notas de crédito. Se normaliza `ABS(importe) × Signo`, evitando volver a convertir el crédito en cargo. Esta corrección reemplaza cualquier indicación previa de multiplicar directamente el importe firmado por Signo.

El motor FIFO existente entrega los costos de insumos de órdenes en pesos. La serie en dólares de esos insumos no está reconstruida en este corte; no se debe interpretar su cero actual como una conversión validada. Esta limitación debe resolverse antes de considerar completos los indicadores en dólares cuando incluyen esas órdenes.
