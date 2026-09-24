# Data Model: Motor de auto-clasificación de Rubro/Centro de Costos/Cultivo/Campaña

Todas las tablas nuevas viven en `WC` (constitución I/II), nunca en `LaHerencia`. Ninguna tabla ni vista existente se modifica (FR-016) — este motor es aditivo.

## Tablas nuevas

### `ImputacionPropuestas`

Una fila por **fracción** de reparto propuesta para un renglón de factura (insumo o contratista). El "reparto vigente" de un renglón es el conjunto de filas `Estado = 'Aprobada'` de su última corrida; una corrida nueva reemplaza completo a la anterior al aprobarse (Clarifications: reemplazo completo, no incremental).

| Columna | Tipo | Notas |
|---|---|---|
| `IdPropuesta` | int identity PK | |
| `IdCorrida` | uniqueidentifier | Agrupa todas las fracciones generadas en un mismo cálculo — permite reemplazar la corrida completa de un renglón al aprobar una nueva, sin tocar filas de otros renglones. |
| `Origen` | varchar(10) | `'Insumo'` \| `'Contratista'`. |
| `IdDetalleCompra` | int FK → `Det_Compras.IdDetalleCompra` | Renglón de factura al que pertenece esta propuesta. |
| `IdOrdenTrabajo` | int NULL FK → `Ordenes_Trabajo.IdOrdenTrabajo` | NULL solo para la fracción "en stock sin consumir". |
| `IdLote`, `IdCultivo`, `IdCampania` | int NULL | NULL cuando el destino es Centro de Costos "Adm. General" (orden sin cultivo) o "en stock sin consumir". |
| `IdCentroCosto` | int NULL FK → `[Centro de costos].IdCentro` | Se completa con "Adm. General" para órdenes sin cultivo; NULL en los demás casos (el Centro de Costos real de Agricultura/Ganadería se resuelve por Cultivo, no se duplica acá). Nombre de columna deliberadamente distinto de `Det_Compras.IdCentroCostos` (con "s", tabla existente) — son dos conceptos distintos, no un typo. |
| `EsGanaderia` | bit | Reparto Agricultura (`0`) / Ganadería (`1`) de esta fracción, previo a Cultivo/Campaña (Clarifications: reparto multidestino). |
| `Importe` | money | Fracción del importe del renglón de factura imputada a este destino. |
| `Cantidad` | decimal(28,8) NULL | Cantidad física atribuida a la fracción, incluyendo stock; NULL si no registrada o contratista. |
| `Unidad` | nvarchar(50) NULL | Unidad original del renglón de remito que origina la fracción. Puede diferir de la unidad de compra. |
| `Estado` | varchar(20) | `'Pendiente'` \| `'Aprobada'` \| `'RequiereIntervencion'`. |
| `FechaCalculo` | datetime2 | Cuándo se generó esta corrida. |
| `FechaAprobacion` | datetime2 NULL | |

**Trazabilidad interna** (FR-013): no se persiste una tabla de lineage aparte — se remonta on-demand desde `IdDetalleCompra`/`IdOrdenTrabajo` hacia `tblRemitoCompra` → `Remitos_Detalles` (capa FIFO) y `Ordenes_Trabajo_Distrib` (renglón de distribución), reejecutando `stock_fifo.asignar_fifo()` para ese producto — la propuesta guarda el destino, no el camino completo, porque el camino ya es reconstruible desde datos existentes sin duplicarlo (evita una segunda fuente de verdad para el FIFO).

**Estado "en stock sin consumir"**: una fila con `IdOrdenTrabajo IS NULL`, `IdLote/IdCultivo/IdCampania IS NULL`, `EsGanaderia IS NULL`, `Estado = 'Aprobada'` automáticamente (no requiere aprobación explícita porque no imputa costo a ninguna campaña — ver FR-002).

### `OrdenesContratistaFacturas` (reemplaza `Ordenes_Trabajo_Contratista_Factura`)

Generaliza a N a N el vínculo 1 a 1 existente (ver research.md). Mismo par de columnas, sin restricción de unicidad por `IdOrdenTrabajo`.

| Columna | Tipo | Notas |
|---|---|---|
| `IdVinculo` | int identity PK | |
| `IdOrdenTrabajo` | int FK → `Ordenes_Trabajo.IdOrdenTrabajo` | |
| `IdCompra` | int FK → `Compras.IdDeuda` | |

**Migración**: copiar 1:1 las filas existentes de `Ordenes_Trabajo_Contratista_Factura`; `costeo.py::costo_contratista` y `resultado.py::_filas_maquinaria_y_contratista` pasan a leer de la tabla nueva (siguen iterando por filas, sin cambio de forma).

### `ImputacionReferencias` (aprendizaje simple, FR-008)

Última clasificación aprobada/corregida por contexto, usada como prioridad en el próximo cálculo (mismo espíritu que `get_rubro_sugerido`, spec 006).

| Columna | Tipo | Notas |
|---|---|---|
| `IdProducto` | int PK (o compuesta con `EsGanaderia`) | Producto del insumo. |
| `EsGanaderia` | bit | |
| `IdCultivo`, `IdCampania` | int NULL | Última corrección aprobada por el usuario para este producto. |
| `FechaActualizacion` | datetime2 | |

## Entidades ya existentes reutilizadas (sin modificar)

- `Det_Compras` (`IdCentroCostos`, `IdRubro`, `IdCampaña`) — clasificación manual, se lee como benchmark (Historia 5), nunca se sobreescribe (Assumptions).
- `tblRemitoCompra`, `Remitos_Detalles`, `Remitos` — cadena de entrada de stock.
- `Ordenes_Trabajo_Insumos`, `Ordenes_Trabajo_Distrib`, `Ordenes_Trabajo` — cadena de consumo y distribución.
- `vw_ResultadoCultivo_Campaña` — motor heredado de comparación (Historia 5, FR-015), solo lectura.

## Estados de una Propuesta (por `IdCorrida`)

```
(datos fuente cambian) → Pendiente ──aprobar──▶ Aprobada
                             │
                             └──no hay Orden vinculada,
                                o reparto no cierra──▶ RequiereIntervencion
```

- `Pendiente → Aprobada`: acción explícita del usuario (User Story 2).
- `Pendiente/Aprobada → Pendiente` (nueva corrida): cuando cambia un dato fuente (FR-011/FR-012) — la corrida vieja no se borra, queda con su `Estado` histórico pero deja de ser la vigente (solo la última `IdCorrida` de un renglón cuenta para reportes).
- `RequiereIntervencion`: terminal hasta que el usuario resuelve la causa (vincula la Orden faltante, corrige el reparto) — dispara una corrida nueva.
