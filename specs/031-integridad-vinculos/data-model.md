# Data Model: Integridad de vínculos (031)

## Entidades en memoria (sin tabla)

### Vinculo

Un vínculo normalizado entre dinero y un documento. Lo produce `features/vinculos/fuente.py`.

| Campo | Tipo | Notas |
|---|---|---|
| via | enum | `aplicacion` (`AplicacionesPago`), `tarjeta` (consumos de resumen), `valor-propio` (`ConciliacionesTesoreria` con `Medio='valores-propios'`), `tesoreria` (`ConciliacionesTesoreria` con cualquier otro medio), `backfill-impuesto` |
| nivel | enum | `documento` (cuenta aunque no esté debitado) o `movimiento` (solo lo debitado). Un mismo vínculo puede servir a los dos niveles. |
| origenMovimiento | str | `bna`, `galicia`, `efectivo`, `tarjetas`, `mercado-libre`, `valores-propios`… |
| idMovimiento | int | |
| tipoDocumento | str | `CompraDeuda`, `VentaGranos`, `VentaHacienda`, `Impuesto`, `Remuneracion` |
| idDocumento | int | |
| importeArs | float | Siempre en pesos. Los documentos en us$ se pesifican con el TC de la factura. |
| fechaPago | date | Fecha real: el débito bancario para tarjeta y cheque, la fecha del movimiento en los demás casos. |
| idRegistro | int | Id en la tabla de origen, para trazabilidad. |
| cadena | str? | Por ejemplo `resumen:667` o `valor:1152`, cuando el vínculo llega por herencia. |

**Reglas**

- Por documento, pagado = Σ vínculos vigentes de nivel documento. Se cuentan los consumos de tarjeta imputados y los cheques conciliados aunque el resumen o el cheque todavía no se hayan debitado.
- Por movimiento, solo cuenta lo debitado: el pago del resumen o el débito del cheque.
- Una aplicación directa desde un débito que pertenece a la cadena de ese documento se excluye de la suma y queda como hallazgo `doble-imputacion`.
- Débito de resumen → documentos: cada consumo imputado × (pago / total del resumen).
- Débito de cheque → documentos del cheque (`ConciliacionesTesoreria` con `Medio='valores-propios'`).

### HallazgoIntegridad

| Campo | Tipo | Notas |
|---|---|---|
| categoria | enum | `documento-excedido`, `movimiento-excedido`, `doble-imputacion`, `fecha-incoherente`, `moneda-mezclada` |
| tipoDocumento / idDocumento | | |
| origenMovimiento / idMovimiento | | Cuando aplica. |
| totalDocumento | float | En pesos. |
| imputadoPorVia | dict | `{via: importe}` |
| exceso | float | |
| diasAntes | int? | Solo para `fecha-incoherente`. |
| idAplicacion | int? | Aplicación señalada. |

## Tablas nuevas en WC

Llevan backup previo al crearlas (constitución II).

### CorreccionVinculosLote

| Columna | Tipo | Notas |
|---|---|---|
| IdLote | int identity PK | |
| Estado | varchar(20) | `propuesto` → `aplicado` → `revertido`. También `propuesto` → `descartado`. |
| FechaPropuesta | datetime2 | |
| FechaAplicado | datetime2 null | |
| FechaRevertido | datetime2 null | |
| Usuario | varchar(100) | |
| BackupArchivo | varchar(400) null | Ruta del .bak verificado. Es obligatoria para pasar a `aplicado`. |
| Resumen | nvarchar(max) | JSON con conteos por grupo. |

### CorreccionVinculosItem

| Columna | Tipo | Notas |
|---|---|---|
| IdItem | int identity PK | |
| IdLote | int FK | |
| Grupo | varchar(40) | Motivo + certeza, por ejemplo `fecha-incoherente/alta`. |
| Accion | varchar(20) | `anular`, `pesificar`, `reemplazo` |
| IdAplicacion | int null | Aplicación a anular o pesificar. |
| OrigenMovimiento, IdMovimientoOrigen, TipoDocumento, IdDocumento, Importe | | Para `reemplazo` y `pesificar`: la aplicación nueva a crear. |
| Motivo | nvarchar(400) | Texto legible. |
| Candidatos | nvarchar(max) null | JSON cuando el reemplazo es ambiguo. |
| Incluido | bit | Default 1. Sergio destilda para excluir. |
| Elegido | bit | Obligatorio en reemplazos ambiguos antes de aplicar. |
| IdAplicacionCreada | int null | Se completa al aplicar, para revertir. |

**Transiciones**

- Aplicar un lote:
  - Anula (`Anulada=1`, `MotivoAnulacion='031:<IdLote>: <motivo>'`) las aplicaciones de los ítems incluidos.
  - Crea las aplicaciones de `pesificar` y `reemplazo` con `Origen='correccion-031'`.
  - Todo en una transacción, después de un backup verificado.
- Revertir un lote:
  - Anula las aplicaciones creadas por el lote.
  - Des-anula las anuladas, solo si su `MotivoAnulacion` empieza con `031:<IdLote>:` de ese mismo lote.

## Tablas existentes que se leen

- `AplicacionesPago`
- `Tarjetas_Resumenes_Pagos`, `Tarjetas_Resumenes_Lineas`, `Tarjetas_Resumenes_Lineas_Compras`
- `ConciliacionesTesoreria`
- `BackfillImpuestosVinculos`
- `[Valores propios]`
- `[Movimientos BNA]`, `[Movimientos Galicia]`
- `Compras`, `vw_Cns_Total_Compra`
- `[Venta Hacienda]`, `[Venta Granos]`

Ninguna se modifica en su esquema. Las escrituras son solo en `AplicacionesPago` y en las dos tablas nuevas.
