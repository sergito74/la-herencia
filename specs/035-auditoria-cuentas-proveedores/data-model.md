# Data Model: Auditoría de cuentas corrientes de proveedores

Todo en la base `WC`. Se agregan tres tablas; no se modifica ninguna tabla ni vista existente. El saldo sigue siendo `Σ(Crédito − Deuda)` de `vw_MovimientosCuenta_Base`.

## Tablas nuevas

### `dbo.AuditoriaParametros`

| Columna | Tipo | Notas |
|---|---|---|
| `Clave` | varchar(60), PK | `plazoMaximoMeses`, `umbralPesos`, `anticipoDias` |
| `Valor` | varchar(60), NOT NULL | Texto del valor (número) |
| `Usuario` | varchar(60) | Quién lo cambió |
| `Fecha` | datetime2 | Cuándo |

Carga inicial: `plazoMaximoMeses = 24`, `umbralPesos = 300`, `anticipoDias = 60`.

### `dbo.AuditoriaCorrecciones`

Una fila por aplicación de una regla de corrección. Nunca se borra; se marca revertida.

| Columna | Tipo | Notas |
|---|---|---|
| `IdCorreccion` | int identity, PK | |
| `Regla` | varchar(60), NOT NULL | `anular-doble-descuento-tarjeta`, `anular-fuera-de-plazo` |
| `Estado` | varchar(20), CHECK | `simulada`, `aplicada`, `revertida`, `descartada` |
| `Parametros` | nvarchar(max) | Plazo y umbral con que se calculó (JSON) |
| `Usuario`, `Fecha` | varchar(60), datetime2 | Quién la creó y cuándo |
| `UsuarioAplicacion`, `FechaAplicacion` | varchar(60), datetime2, NULL | Quién aprobó y cuándo |
| `Respaldo` | varchar(260), NULL | Archivo de respaldo verificado previo a aplicar |
| `UsuarioReversion`, `FechaReversion` | varchar(60), datetime2, NULL | |
| `Resumen` | nvarchar(max) | Cuentas, importes y conteos (JSON) |

### `dbo.AuditoriaCorreccionesCuentas`

Una fila por cuenta incluida en una corrección: es lo que Sergio tilda.

| Columna | Tipo | Notas |
|---|---|---|
| `IdCorreccion` | int, FK | |
| `IdContacto` | int | |
| `Tildada` | bit | `1` si Sergio la eligió |
| `SaldoAntes`, `SaldoDespues` | money | Deben ser iguales cuando la regla solo ordena imputaciones |
| `IdsAplicacion` | nvarchar(max) | Aplicaciones tocadas (JSON), para revertir exacto |
| `Detalle` | nvarchar(max) | Qué cambia, en texto simple |

PK `(IdCorreccion, IdContacto)`.

### `dbo.SaldosReferenciaAccessDetalle`

Referencia del Access fila a fila hasta la fecha de corte (copia de `LaHerencia.vw_MovimientosCuenta_Base`, solo lectura de origen): `Origen` varchar(60), `IdOrigen` bigint, `IdContacto` int, `Fecha` datetime2, `Deuda` y `Credito` decimal(19,4), `FechaCarga`. Se recarga con `scripts/cargar_referencia_detalle_035.py`; permite descomponer cada diferencia sin releer `LaHerencia` en cada corrida.

### `dbo.AuditoriaConocidos`

Reglas de lo ya conocido (FR-019). `IdConocido` int identity PK; `Tipo` varchar(30) CHECK en `concepto-movimiento` o `cuenta`; `Clave` varchar(200) (texto del concepto, o el número de contacto); `ImporteRef` money NULL (diferencia documentada de una cuenta); `Motivo` varchar(300) NOT NULL; `Usuario`, `Fecha`; `Activo` bit (baja lógica con `UsuarioBaja` y `FechaBaja`). Carga inicial: 11 conceptos normales (impuesto al débito y crédito, comisiones, fondos comunes, plazos fijos, transferencias entre cuentas propias, depósitos de efectivo).

## Tablas existentes que se leen o se usan

- `SaldosReferenciaAccess` (`IdContacto`, `SaldoAccess`, `FechaCorte`, `FechaCarga`): referencia y fecha de corte.
- `AplicacionesPago`: aplicaciones (`OrigenMovimiento`, `IdMovimientoOrigen`, `TipoDocumento`, `IdDocumentoAplicado`, `ImporteAplicado`, `Origen`, `Anulada`, `MotivoAnulacion`, `UsuarioAnulacion`, `FechaAnulacion`). La baja lógica ya existe; la corrección la usa y no borra filas.
- `Tarjetas_Resumenes_Lineas_Compras`: vínculos de tarjeta con facturas (detección de doble descuento).
- `ReasignacionesContacto`, `AjustesCuentaCorriente`: explican parte de la diferencia (D4 de research).
- `RecalculoFifoEjecucion`, `RecalculoFifoAplicacion`, `RecalculoFifoContacto`, `CuentasARevisar`: FIFO completo e historial.

## Entidades derivadas (no se almacenan)

- **Cuenta auditada**: `{idContacto, razonSocial, moneda, saldoSistema, saldoAccess, diferencia, causa, explicada, sinExplicar}`.
- **Causa** (una principal por cuenta): `coincide`, `coincide-causa-conocida`, `diferencia-menor-umbral`, `aplicacion-fuera-de-plazo`, `fuera-de-plazo-decidido` (manual o FIFO; no cuenta como excepción), `doble-descuento-tarjeta`, `nota-sin-imputar`, `impuesto-sin-boleta`, `movimiento-sin-contacto`, `sobrepago`, `contacto-duplicado`, `falta-documento`, `sin-referencia`, `otros`. Una cuenta puede tener más de un hallazgo, pero cuenta una sola vez en el total de cuentas con diferencia.
- **Hallazgo de plazo**: `{idMovimiento, medio, fechaPago, idContacto, importeAplicado, cantidadFacturas, facturaMasVieja, diasMaximos, origenAplicacion}`, agrupado por movimiento de pago.
- **Grupo de excepciones**: `{causa, cuentas, importe, hallazgos}`.

## Reglas de validación

- Una corrección solo puede aplicarse si fue simulada, tiene al menos una cuenta tildada y no está aplicada ya.
- Antes de aplicar se verifica que el saldo de cada cuenta tildada no cambió desde la simulación; si cambió, se pide volver a simular.
- Aplicar crea el respaldo verificado y escribe todo en una sola transacción; si algo falla no se escribe nada.
- Revertir devuelve `Anulada = 0` en exactamente las aplicaciones registradas en `IdsAplicacion`; nada más.
- El saldo de ninguna cuenta puede cambiar por una regla que solo ordena imputaciones (`SaldoAntes = SaldoDespues` con tolerancia $0,01).

## Transiciones de estado de una corrección

`simulada` → `aplicada` → `revertida`; `simulada` → `descartada`. Aplicar de nuevo después de revertir crea una corrección nueva.
