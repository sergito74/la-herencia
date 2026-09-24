# Data Model: Aplicación de pagos y cobros

## AplicacionesPago (tabla nueva)

| Columna | Tipo | Notas |
|---|---|---|
| IdAplicacion | int PK identity | |
| OrigenMovimiento | varchar(20) | Mismo catálogo que `tesoreria.MEDIOS`: `bna`\|`galicia`\|`efectivo`\|`valores-propios`\|`valores-recibidos`\|`tarjetas` |
| IdMovimientoOrigen | bigint | Id del movimiento en su tabla origen (`IdMovimientoBNA`, `IdMovimiento` de Galicia, etc.) |
| TipoDocumento | varchar(20) | `CompraDeuda`\|`VentaHacienda`\|`VentaGranos` |
| IdDocumentoAplicado | int | `Compras.IdDeuda`, o `IdVenta` de `Venta Hacienda`/`Venta Granos` según `TipoDocumento` |
| ImporteAplicado | money | > 0, siempre en valor absoluto (el signo lo da `TipoDocumento`: deuda=egreso, venta=ingreso) |
| Fecha | datetime2 | Fecha de la aplicación (no necesariamente la del movimiento) |
| Usuario | varchar(60) | Quién confirmó la aplicación |
| Anulada | bit | default 0 |
| MotivoAnulacion | nvarchar(255) NULL | Requerido si `Anulada=1` |
| UsuarioAnulacion | varchar(60) NULL | |
| FechaAnulacion | datetime2 NULL | |

Sin FK física a las tablas heredadas (`Compras`, `Movimientos BNA`, `Venta Hacienda`, `Venta Granos`) — mismo patrón ya usado en `CuentasBancarias`/`Movimientos BNA` (018), consistente con que esas tablas tampoco tienen FKs físicas entre sí en el esquema heredado.

Índices: `(OrigenMovimiento, IdMovimientoOrigen)` para "aplicaciones de este movimiento"; `(TipoDocumento, IdDocumentoAplicado)` para "aplicaciones de este documento".

**Regla de inmutabilidad (FR-005)**: nunca se hace `UPDATE` de `ImporteAplicado`/`IdDocumentoAplicado` sobre una fila existente. Corregir = poner `Anulada=1` (+ motivo/usuario/fecha) e insertar una fila nueva.

## Entidades derivadas (calculadas, no persistidas)

- **Estado de documento** (`{pendiente, aplicado, saldoPendiente, estado}`): para un `(TipoDocumento, IdDocumentoAplicado)`, `aplicado = SUM(ImporteAplicado) WHERE Anulada=0`; `saldoPendiente = importeTotal - aplicado`; `estado = 'Pendiente'` si `aplicado ≈ 0`, `'Parcial'` si `0 < saldoPendiente > TOLERANCIA_REDONDEO_APLICACION`, `'Total'` si `saldoPendiente <= TOLERANCIA_REDONDEO_APLICACION` ($1, research.md §4). `importeTotal` sale de `vw_Cns_Total_Compra.GranTotal` (Compras) o `calcular_totales`/`Importe Neto a percibir` (Ventas, research.md §1).
- **Estado de movimiento** (`{aplicado, saldoSinAplicar}`): análogo, `SUM(ImporteAplicado) WHERE OrigenMovimiento=X AND IdMovimientoOrigen=Y AND Anulada=0` comparado contra el importe real del movimiento (mismo campo `importe` que ya usa `flujo_caja.get_movimientos_normalizados`).
- **Documento pendiente de un contacto**: lista de compras/ventas de ese contacto con `saldoPendiente > TOLERANCIA_REDONDEO_APLICACION`, ordenadas por fecha — insumo de la sugerencia FIFO (research.md §3).

## Relación con 018 (`flujo_caja`)

`atribuir_egreso`/`atribuir_ingreso` (`flujo_caja/atribucion.py`) pasan a consultar primero `AplicacionesPago` para el movimiento; si hay aplicaciones vigentes, el Rubro/Centro de Costos sale de los documentos aplicados (Compras → `Det_Compras.IdRubro`/`IdCentroCostos`, ya usado hoy; Ventas → el nombre de categoría ya derivado en `_ventas_hacienda_en_rango`/`_ventas_granos_en_rango`). Si no hay aplicaciones, cae al matching exacto actual (fallback) o, si el movimiento es anterior a 2015-09-01, se marca "Histórico sin aplicar" (research.md §7, FR-010).
