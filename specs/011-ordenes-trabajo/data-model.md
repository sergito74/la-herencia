# Data Model: Órdenes de Trabajo (011)

Toda escritura va exclusivamente contra `WC`. Las tablas heredadas (`Ordenes`, `Ordenes_Detalles`, `Ordenes_Detalles_Distrib`, `Ordenes_Lotes`, `Lotes`, `Cultivos`, `Campañas`, `Tipo Labores`, `Contactos`) no se alteran en su estructura; se leen y se migran datos hacia las tablas nuevas descritas abajo, siguiendo el patrón de scripts idempotentes de 010-remitos.

## Entidades heredadas reutilizadas (solo lectura + migración inicial)

- **`Lotes`** (40 filas, se excluye `PRUE`): IdLote, "Numero Lote", Superficie.
- **`Cultivos`** (11 filas): IdCultivo, Nombre.
- **`Campañas`** (32 filas, incluye "No Aplica"): IdCampaña, Nombre.
- **`Contactos`**: maestro de contratistas vía `EsContratistaLabores = 1`; fuente de verdad única (la columna heredada `Ordenes.Contratista` no se migra).
- **`Unidades_Medida` / `Producto_Unidad`** (creadas por 010-remitos): se reutilizan sin cambios para normalizar las unidades de `Ordenes_Detalles_Distrib` (`LTS`/`LITROS`, `KGS`/`KILOS`, etc.).

## Entidades nuevas en `WC`

### `Ordenes_Trabajo` (cabecera)

| Columna | Tipo | Notas |
|---|---|---|
| IdOrdenTrabajo | int identity PK | |
| FechaPedido | date | obligatoria |
| FechaEjecucion | date NULL | se completa al marcar Ejecutada |
| IdTipoLabor | int FK → `Tipo Labores` | |
| IdContratistaContacto | int NULL FK → `Contactos` | NULL si se ejecuta con maquinaria propia exclusivamente |
| Estado | varchar | `Planificada` \| `Ejecutada` \| `Anulada` |
| MotivoAnulacion | varchar NULL | obligatorio si Estado = Anulada |
| IdRubro | int NULL FK → `Rubros` | solo para órdenes sin cultivo específico (Historia 5) |
| IdCentroCostos | int NULL FK → `Centros de Costos` | ídem |
| Observaciones | varchar NULL | |

### `Ordenes_Trabajo_Insumos` (reemplaza en el módulo nuevo a `Ordenes_Detalles`)

| Columna | Tipo | Notas |
|---|---|---|
| IdOrdenInsumo | int identity PK | |
| IdOrdenTrabajo | int FK | |
| IdProducto | int FK → catálogo unificado (`vw_CnsU_Producto_link`, igual que Remitos) | |
| CantidadTotal | decimal(18,4) | suma de las distribuciones al guardar; recalculada, no editable directamente |
| Unidad | varchar FK → `Unidades_Medida` | |

### `Ordenes_Trabajo_Distrib` (reemplaza a `Ordenes_Detalles_Distrib`)

| Columna | Tipo | Notas |
|---|---|---|
| IdDistrib | int identity PK | |
| IdOrdenInsumo | int FK | |
| IdLote | int FK → `Lotes` | |
| IdCultivo | int FK → `Cultivos` | |
| IdCampaña | int FK → `Campañas` | |
| DosisHa | decimal(18,4) | cargada por el usuario |
| Superficie | decimal(18,4) | superficie del lote considerada (puede ser parcial) |
| CantidadAsignada | decimal(18,4) | = DosisHa × Superficie, calculada |
| Aplicar | bit | si finalmente ese lote fue tratado (default true) |

**Regla de integridad (FR-004)**: `sum(CantidadAsignada donde Aplicar=1) + sum(Ordenes_Trabajo_Devoluciones.Cantidad del mismo IdOrdenInsumo) = CantidadTotal` del renglón de insumo. Se valida en el backend antes de confirmar la orden o la devolución (no es una constraint SQL, porque debe dar un mensaje de negocio, igual que las validaciones de Remitos).

### `Ordenes_Trabajo_Devoluciones`

| Columna | Tipo | Notas |
|---|---|---|
| IdDevolucion | int identity PK | |
| IdOrdenInsumo | int FK | |
| Fecha | date | |
| Cantidad | decimal(18,4) | no puede superar lo retirado y no devuelto de ese renglón |
| Observaciones | varchar NULL | |

Al confirmarse, genera una nueva capa de entrada de stock (misma mecánica de capas FIFO que un remito, ver `stock_fifo.py` de 010-remitos) por `Cantidad` de `IdProducto`.

### `Ordenes_Trabajo_Maquinaria`

| Columna | Tipo | Notas |
|---|---|---|
| IdOrdenMaquinaria | int identity PK | |
| IdOrdenTrabajo | int FK | |
| Descripcion | varchar | identificación de la máquina (texto libre o referencia informal a `Labores Maquinaria propia` histórica) |
| CostoPorHectarea | decimal(18,2) | cargado a mano, en pesos |
| TipoCambioBNA | decimal(18,4) NULL | cargado a mano si se quiere expresar en dólares (no hay fuente automática) |

El costo total de este renglón se prorratea entre los lotes de la orden por superficie, igual que un insumo (Historia 3).

### `Ordenes_Trabajo_Contratista_Factura`

| Columna | Tipo | Notas |
|---|---|---|
| IdOrdenTrabajo | int FK | |
| IdCompra | int FK → `Compras` (factura del contratista) | mismo patrón que `Remitos_Facturas`, pero orden↔factura |

El tipo de cambio para dolarizar se toma de `Compras.tipoDeCambio` de esa factura (mismo mecanismo que ya usa `remitos/costeo.py` para facturas en dólares).

### `Formularios_Retiro`

| Columna | Tipo | Notas |
|---|---|---|
| IdFormularioRetiro | int identity PK | numeración secuencial propia (FR-008) |
| IdOrdenTrabajo | int FK unique | 1 a 1 con la orden |
| FechaEmision | datetime | |

### Alta de nuevos Tipos de Labor (Historia 7)

**Decisión** (resuelta en `/speckit-analyze`, hallazgo U1): se inserta directamente en la tabla heredada `Tipo Labores` (solo `INSERT` de filas nuevas, nunca `ALTER` de su estructura), con el mismo criterio ya usado en 010-remitos para dar de alta el rubro "Pérdidas y bajas de insumos" directamente en la tabla heredada `Rubros`. No se crea una tabla espejo: `Tipo Labores` es un catálogo simple (5 filas, sin dependencias VBA relevantes detectadas por el agente SQL) y agregar filas no altera su estructura ni el comportamiento de Access, cumpliendo el Principio I/VII de la constitución (no duplicar catálogos existentes).

## Estados y transiciones de `Ordenes_Trabajo.Estado`

```
Planificada → Ejecutada   (al marcar la labor como realizada en campo)
Planificada → Anulada     (con motivo; devuelve stock consumido)
Ejecutada   → Anulada     (con motivo; devuelve stock consumido, solo si no tiene devoluciones ni factura de contratista vinculada, según FR-007)
```

No hay transición inversa Ejecutada → Planificada ni reapertura de una orden Anulada.

## Migración de datos heredados

- 153 filas de `Ordenes` → `Ordenes_Trabajo`, con `Estado = 'Ejecutada'` si `FechaEjecucion` no es NULL, `'Planificada'` si lo es (4 casos: 185, 182, 127, 123).
- `IdContratistaContacto` se copia tal cual; la columna `Contratista` (entero 1-13) no se migra.
- 820 filas de `Ordenes_Detalles` → `Ordenes_Trabajo_Insumos`.
- 4.319 filas de `Ordenes_Detalles_Distrib` → `Ordenes_Trabajo_Distrib`, unificando unidades contra `Unidades_Medida`.
- 879 filas de `Ordenes_Lotes` se reconcilian contra `Ordenes_Trabajo_Distrib` (el flag `Aplicar` ya vive ahí a nivel de renglón).
- Los 13 renglones históricos donde `CantidadTotal` no cierra contra lo distribuido se migran con una bandera `RevisarMigracion = 1` (columna auxiliar temporal o lista aparte, igual que los duplicados de Remitos), sin bloquear la migración ni corregir el dato heredado.
- `Labores Maquinaria propia` no se migra a `Ordenes_Trabajo_Maquinaria` (son conceptos distintos: la planilla vieja no estaba vinculada a ninguna orden); queda como tabla heredada de solo referencia histórica.
- `DetCompra_OT` (vacía) no requiere migración.
