# Data Model: Recálculo FIFO de cuentas corrientes

## Tablas nuevas (WC)

### RecalculoFifoEjecucion

| Campo | Tipo | Notas |
| --- | --- | --- |
| IdEjecucion | int identity PK | |
| Tipo | varchar(20) | `simulacion`, `aplicacion` o `continua` |
| Estado | varchar(20) | `simulada`, `aplicada`, `revertida` o `descartada` |
| Alcance | nvarchar(max) | JSON con la lista de IdContacto o `todos` |
| FechaInicio, FechaFin | datetime2 | |
| Usuario | nvarchar(100) | Debe ser Sergio para aplicar o revertir |
| BackupArchivo | nvarchar(400) | Ruta del respaldo verificado. Obligatorio si se aplica |
| Resumen | nvarchar(max) | JSON con contactos, cierran, excepciones e importes |

Transiciones: `simulada` puede pasar a `aplicada` o a `descartada`. `aplicada` puede pasar a `revertida`.

### RecalculoFifoContacto

Hay una fila por contacto y ejecución, y es la base de la lista de excepciones.

| Campo | Tipo | Notas |
| --- | --- | --- |
| IdEjecucion, IdContacto | PK | |
| ContactoUnificado | int null | Contacto principal, si es un duplicado unificado |
| Moneda | char(3) | `ARS` o `USD` |
| FacturadoAntes, PagadoAntes, AplicadoAntes | decimal(18,2) | |
| AplicadoDespues, AnticipoAbierto | decimal(18,2) | |
| CerrabaAntes, CierraDespues | bit | Con la tolerancia de 0,5% |
| Tendencia | varchar(10) | `igual`, `mejora` o `empeora` |
| Controles | nvarchar(max) | JSON con la lista de controles fallidos y su motivo |
| Marcas | nvarchar(max) | JSON: anticipo largo, saldo estimado, cheque provisorio, TC implícito, endoso sin registro, manual-ajustado |
| Huella | char(64) | Hash de las aplicaciones resultantes, para la idempotencia |
| EstadoExcepcion | varchar(20) | `ninguna`, `pendiente` o `resuelta` |

### RecalculoFifoAplicacion

Contiene el resultado propuesto. Al aplicar se copia a `AplicacionesPago`.

| Campo | Tipo | Notas |
| --- | --- | --- |
| IdEjecucion, IdContacto | FK | |
| OrigenMovimiento, IdMovimientoOrigen | | Mismos códigos que `AplicacionesPago` |
| TipoDocumento, IdDocumentoAplicado, NroCuota | | |
| ImporteAplicado | decimal(18,2) | En la moneda del documento |
| ImporteArs, TipoCambio | decimal | TC BNA vendedor del día anterior, o implícito |
| Regla | varchar(20) | `cadena`, `eleccion`, `nota-origen`, `ajuste-tc`, `compensacion`, `fifo`, `anticipo` o `diferencia-cambio` |
| FechaCredito, FechaVencimiento | date | |

### RecalculoFifoSaldoInicial

| Campo | Tipo | Notas |
| --- | --- | --- |
| IdContacto | PK | |
| Importe, Moneda, Fecha | | |
| Estado | varchar(20) | `estimado`, `confirmado` o `rechazado` |
| Usuario, FechaConfirmacion | | |

### RecalculoFifoCola

Se usa para la aplicación continua.

| Campo | Tipo | Notas |
| --- | --- | --- |
| IdContacto | PK | |
| Motivo | varchar(40) | `movimiento`, `compra` o `venta` |
| FechaEncolado | datetime2 | |

### ContactoDuplicado

| Campo | Tipo | Notas |
| --- | --- | --- |
| IdContacto, IdContactoPrincipal | PK | |
| Criterio | varchar(20) | `cuit` o `nombre` |
| Estado | varchar(20) | `propuesto`, `confirmado` o `descartado` |

## Tablas existentes que se modifican

- **`Compras`**: se agrega la columna `Suspendida bit default 0` (FR-025).
- **`AplicacionesPago`**: no cambia su esquema. Se usan los valores nuevos `Origen='fifo-032'` y `NotaConciliacion='ejecucion:N regla:X'`.
- **`[Dolar BNA]`**: solo lectura, columna `Vend_Divisa` (research R2).

## Entradas del motor, en memoria

- **Débito**: `{clave, idContacto, tipo, fechaEmision, vencimiento, nroComprobante, moneda, importe, suspendido, origenNC}`.
- **Crédito**: `{clave, idContacto, medio, fechaErogacion, moneda, importe, eleccion: [docs], cadena: [docs], tipo: pago|retencion|nc|venta-compensable}`.

## Reglas de validación

- La suma de lo aplicado a un débito no puede superar su importe (FR-010).
- La suma de lo aplicado desde un crédito no puede superar su importe (FR-010).
- Lo aplicado tiene que ser igual al menor entre pagado y facturado, con una tolerancia de 0,5%.
- Un pago de más que no se puede imputar como anticipo a un débito posterior es una excepción (FR-037).
- Una cuenta sin continuidad tiene saldo 0 al 29/06/2012 (FR-034).
