# Data Model: Método sistemático de revisión de cuentas (036)

Todo en `WC`. Las tablas nuevas se crean con `backend/scripts/crear_esquema_revision_036.py` (modo `--verificar` que no escribe; respaldo verificado antes de crear; idempotente). Nada se borra: las bajas son lógicas. Decisiones de origen en [research.md](research.md).

## Tablas nuevas

### `RevisionCortes`

El corte vigente de todo el método (D7). La fila más nueva manda; las anteriores quedan de historial.

| Columna | Tipo | Regla |
|---|---|---|
| IdCorte | int identity PK | |
| Corte | date NOT NULL | primer valor: 2026-09-30 |
| Motivo | varchar(200) NULL | |
| Usuario | varchar(60) NOT NULL | |
| Fecha | datetime2 NOT NULL | por defecto ahora |

### `RevisionFichas`

Una fila por cuenta con movimientos. Guarda solo lo que decide una persona; la etapa se calcula (D3).

| Columna | Tipo | Regla |
|---|---|---|
| IdContacto | int PK | contacto de la cuenta |
| Estado | varchar(24) NOT NULL | `pendiente`, `en-proceso`, `esperando-evidencia`, `esperando-sergio`, `cerrada`, `cerrada-con-excepcion` (CHECK). `reabierta` no se guarda: se calcula (D7) |
| InventarioFuentes | nvarchar(max) NULL | JSON: fuentes disponibles y cuáles faltan (E0) |
| Nota | varchar(500) NULL | |
| PreguntaBloqueante | varchar(300) NULL | lo que se necesita de Sergio; alimenta la lista de preguntas |
| Corte | date NULL | corte del cierre (D7) |
| SaldoAlCierre | money NULL | saldo a esa fecha, en la moneda que gobierna la cuenta |
| Moneda | varchar(10) NULL | |
| MotivoExcepcion | varchar(500) NULL | obligatorio si `cerrada-con-excepcion` |
| UsuarioCierre | varchar(60) NULL | |
| FechaCierre | datetime2 NULL | |
| UsuarioActualiza | varchar(60) NULL | |
| FechaActualiza | datetime2 NOT NULL | |

Reglas:
- Cerrar (`cerrada`) exige los 7 criterios cumplidos al corte vigente; cerrar con excepción exige `MotivoExcepcion` (FR-010, FR-011).
- El historial de cada cambio va a `AuditoriaRevisionesHistorial` (existente) con `Accion` nueva: `ficha-estado`, `ficha-inventario`, `ficha-cierre`, `ficha-reapertura`, `pago-sin-factura`, `saldo-externo`, `decision`. No se crea otra tabla de historial.
- Las filas se crean al primer acceso a la ficha o al abrir el tablero (`pendiente`); no hay carga masiva previa.

### `RevisionPagosSinFactura`

Marcas de Sergio sobre los pagos que el detector no pudo respaldar (FR-015). El detector no se guarda; se recalcula, y esta tabla conserva las decisiones.

| Columna | Tipo | Regla |
|---|---|---|
| IdMarca | int identity PK | |
| IdContacto | int NOT NULL | |
| Medio | varchar(20) NOT NULL | `bna`, `galicia`, `efectivo`, `tarjetas`, `retencion`, `valores` u otro origen de la vista |
| IdMovimiento | int NOT NULL | id de origen del movimiento |
| Estado | varchar(24) NOT NULL | `pendiente`, `factura-cargada`, `sin-documento`, `anticipo` (CHECK) |
| IdCompra | int NULL | factura cargada que lo respalda |
| FuenteRespaldo | varchar(20) NULL | CHECK en `portal`, `estado-de-cuenta`, `pdf`; obligatoria cuando `Estado = factura-cargada` y la compra no tiene archivo (FR-020) |
| Nota | varchar(500) NULL | obligatoria si `sin-documento` |
| Usuario | varchar(60) NOT NULL | |
| Fecha | datetime2 NOT NULL | |

Índice único por (IdContacto, Medio, IdMovimiento): una sola marca por movimiento, que se actualiza en el lugar (no hace falta filtro porque no hay baja lógica); cada cambio anterior queda en el historial, no se sobreescribe sin registro.

Traducción del `Origen` de `vw_MovimientosCuenta_Base` al `Medio` de esta tabla (la usan el detector y las marcas):

| Origen de la vista | Medio |
|---|---|
| `Banco Nacion` | `bna` |
| `Galicia` | `galicia` |
| `Pagos efectivo` | `efectivo` |
| `Tarjetas` | `tarjetas` |
| `Retenciones` | `retencion` |
| `Cobros Valores Recibidos`, `Pagos Valores Recibidos` | `valores` |
| `Venta Granos` | `venta-granos` |

Un origen que no figure en la tabla se guarda con su nombre normalizado (minúsculas y guiones) y se informa en el resultado, no se descarta.

### `RevisionSaldosExternos`

Saldo informado por el proveedor, el banco o la tarjeta (FR-017). Es un dato cargado por una persona; el sistema no lo busca.

| Columna | Tipo | Regla |
|---|---|---|
| IdSaldoExterno | int identity PK | |
| IdContacto | int NOT NULL | |
| FechaSaldo | date NOT NULL | fecha a la que corresponde el saldo |
| Saldo | money NOT NULL | signo: positivo a favor nuestro, igual que la cuenta |
| Moneda | varchar(10) NOT NULL | `Pesos` o `Dolares` |
| Fuente | varchar(20) NOT NULL | `portal`, `pdf`, `mail`, `banco`, `tarjeta`, `sin-estado` (CHECK) |
| Referencia | varchar(400) NULL | ruta del archivo guardado o descripción |
| Nota | varchar(500) NULL | para `sin-estado`: por qué no se pide (D12, FR-019) |
| Usuario | varchar(60) NOT NULL | |
| Fecha | datetime2 NOT NULL | |
| Anulado | bit NOT NULL | baja lógica |

### `RevisionTableroFotos`

Foto semanal del tablero (D13).

| Columna | Tipo | Regla |
|---|---|---|
| IdFoto | int identity PK | |
| Semana | date NOT NULL | lunes de la semana, único |
| Corte | date NOT NULL | corte vigente al momento |
| Datos | nvarchar(max) NOT NULL | JSON: por cola, etapa y estado, cantidad de cuentas e importe en juego, más totales |
| Usuario | varchar(60) NULL | `sistema` si se creó al abrir el tablero |
| Fecha | datetime2 NOT NULL | |

## Tablas existentes que se reutilizan (sin cambios de esquema)

| Tabla | Uso en la 036 |
|---|---|
| `vw_MovimientosCuenta_Base` | movimientos de la cuenta; saldo = crédito − deuda; cantidad de movimientos y saldo al corte |
| `Compras`, `vw_Compras_ImporteDocumento` | facturas y notas del proveedor, y su importe |
| `Tarjetas_Resumenes_Lineas_Compras` | vínculo de la tarjeta con la factura (crédito del proveedor) |
| `AplicacionesPago` | imputaciones de pagos a facturas (las ordena el FIFO) |
| `AuditoriaRevisiones`, `AuditoriaRevisionesHistorial` | saldo esperado (cero / puede tener saldo) y notas de la 035; el historial de la ficha |
| `AuditoriaCorrecciones`, `AuditoriaCorreccionesCuentas` | lotes de cola (D10): regla, estado, respaldo, cuentas tildadas, saldo antes y después |
| `RecalculoFifoEjecucion`, `RecalculoFifoContacto`, `RecalculoFifoAplicacion` | simulación, aplicación y reversión del FIFO |
| `SaldosReferenciaAccess`, `SaldosReferenciaAccessDetalle` | referencia del Access y saldo inicial de cuentas viejas |
| `CuentasARevisar` | excepciones de la 035 (alimentan la cola I) |
| `ReasignacionesContacto`, `AjustesCuentaCorriente` | reasignaciones de contacto y notas de ajuste |
| `Retenciones` | retenciones como crédito (se suman al pago en el detector, D1) |

## Resultados calculados (no se guardan)

### Pago sin factura (detector)

| Campo | Significado |
|---|---|
| medio, idMovimiento, fecha, importe | el pago o crédito sin respaldo |
| retencionAsociada | importe de la retención que lo acompaña, si hay |
| importeEsperadoFactura | pago más retención asociada |
| fechaEsperadaDesde, fechaEsperadaHasta | rango según la mediana de la cuenta (D2) |
| confianza | `alta` (emparejamiento exacto de pasadas 1 y 2) o `media` (corrida FIFO de la pasada 3) |
| marca | estado de `RevisionPagosSinFactura`, si hay |
| anteriorA2021 | verdadero si es de antes de 2021 (D8) |

### Criterios de cierre (los 7, FR-008)

Cada uno devuelve `cumple` (sí, no, no aplica), el número medido, el texto en español simple y a qué etapa pertenece:

| # | Criterio | Etapa | Se mide con |
|---|---|---|---|
| C1 | Documentos completos | E1 | pagos sin factura sin decisión = 0; facturas sin pago explicadas |
| C2 | Movimientos y contactos correctos | E2 | hallazgos `contacto-duplicado` y `movimiento-sin-contacto` = 0 |
| C3 | Saldo explicado por evidencia | E4 | diferencia contra saldo externo menor al umbral (pesos $300; dólares tolerancia relativa) o `sin-estado` con motivo |
| C4 | Tarjeta sin doble conteo | E3 | hallazgos `doble-descuento-tarjeta` = 0 |
| C5 | Imputaciones sanas | E5 | `aplicacion-fuera-de-plazo` y `sobrepago` = 0 o decididos; FIFO aplicado con saldo idéntico |
| C6 | Pendientes tipificados | E4 | `nota-sin-imputar` e `impuesto-sin-boleta` = 0 o con decisión; retenciones con certificado |
| C7 | Trazabilidad | E6 | ficha con evidencia, decisión y fecha; sin cambios de saldo al corte desde el cierre |

### Etapa de una cuenta

Se obtiene de los criterios: E0 si no hay inventario de fuentes confirmado; luego la primera etapa (E1 a E5) con un criterio sin cumplir; E6 si todo cumple y falta la aprobación de Sergio.

### Cola de una cuenta

La define la precedencia de [research.md D5](research.md). Los otros problemas de la cuenta se devuelven en `otrosProblemas`.

## Transiciones de estado de la ficha

```text
pendiente ──► en-proceso ──► esperando-evidencia ──► en-proceso
                        └──► esperando-sergio ──► en-proceso
en-proceso ──► cerrada                (7 criterios cumplidos al corte; la aprueba Sergio)
en-proceso ──► cerrada-con-excepcion  (motivo obligatorio; la aprueba Sergio)
cerrada | cerrada-con-excepcion ──► reabierta   (calculada: el saldo al corte cambió)
reabierta ──► en-proceso
```

Solo el rol con permiso de escritura puede cambiar el estado; el de solo lectura ve la ficha.
