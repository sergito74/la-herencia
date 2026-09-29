# Data Model: Conciliación de Tesorería con documentos

## Extensión de `ConciliacionesTesoreria` (023)

Columnas nuevas, ambas nullable — no rompen las filas ya insertadas por 023:

| Columna | Tipo | Notas |
|---|---|---|
| `TipoOrigenDocumento` | varchar(20), NULL | `Compras` \| `Impuestos` \| `Remuneraciones` \| `Alquileres` \| `NULL` |
| `IdOrigenDocumento` | bigint, NULL | id del documento en su tabla de origen (`IdDeuda`/`IdImpuesto`/`IdSalario`/`IdCobroAlquiler`) |

**Validaciones (en el repository, no en `CHECK` — mismo criterio que 025 con `IdCompra`/`IdImpuesto`, para poder dar un mensaje de error legible)**: `TipoOrigenDocumento` e `IdOrigenDocumento` van juntos (ambos `NULL` o ambos con valor) — nunca uno sin el otro.

`IdContacto`, `Medio`, `IdMovimiento`, `Usuario`, `Fecha` no cambian de significado: una conciliación con documento sigue siendo "este movimiento le imputó $X a este contacto", solo que ahora también sabe a qué documento específico corresponde esa parte.

## Entidad nueva: `ConciliacionesTesoreriaEstado`

Insert-only — cada fila es un evento (`SinDocumento`, `DiferenciaAceptada` o `EstadoQuitado`). Los motivos se reutilizan de Tarjetas, pero su persistencia NO se copia: Tarjetas borra físicamente estados; Tesorería conserva el historial.

| Columna | Tipo | Notas |
|---|---|---|
| `IdEstado` | int identity, PK | |
| `Medio` | varchar(20) | uno de los 6 medios de 023 |
| `IdMovimiento` | bigint | id del movimiento en su tabla de origen |
| `Estado` | varchar(20) | `SinDocumento` \| `DiferenciaAceptada` \| `EstadoQuitado` |
| `Motivo` | varchar(30) | `SinDocumento`: `Impuesto`\|`Interes`\|`CompraNoCargada`\|`Otro`. `DiferenciaAceptada`: `AjusteTipoCambioSinNota`\|`Redondeo`\|`Impuesto`\|`Otro` (mismo catálogo que Tarjetas). `EstadoQuitado`: `Revocacion`, asignado por el servidor. |
| `Detalle` | nvarchar(255), NULL | obligatorio cuando `Motivo = 'Otro'` |
| `ImporteDiferencia` | money, NULL | solo para `DiferenciaAceptada` |
| `Usuario` | nvarchar(100) | |
| `Fecha` | datetime, default `getdate()` | |

**La fila de mayor `IdEstado` para un `(Medio, IdMovimiento)` es la vigente** (mismo criterio insert-only que el resto del sistema) — no hay `UPDATE`/`DELETE`.

Si la última fila es `EstadoQuitado`, no hay excepción vigente. Quitar estado es idempotente cuando ya no hay excepción: no agrega eventos vacíos. Se preservan todos los vínculos y se recalcula el estado normal. `SinDocumento` solo es admisible sin conciliaciones previas; para cerrar un residual ya imputado se usa diferencia aceptada. `DiferenciaAceptada` se considera antes del resultado parcial para que pueda cerrarlo; nunca oculta un origen automático o un traspaso interno. La auditoría vigente se devuelve en GET conciliación, incluyendo importe de diferencia, motivo, detalle, usuario y fecha.

`Detalle` se recorta y no puede ser vacío si el motivo es `Otro`; máximo 255 caracteres. `Usuario` proviene de la sesión autenticada y tiene máximo 100 caracteres; no lo acepta el body. `ImporteDiferencia` solo tiene valor en `DiferenciaAceptada`, conserva su signo y no se suma como si fuera una imputación a un contacto.

## Estado unificado de un movimiento de Tesorería (extiende 024)

`esta_resuelto(medio, id_movimiento)` pasa de 5 a 6 valores:

```
"ya_reconocido"           — origen automático habitual (023)
"conciliado"              — conciliación completa, con o sin documento (023, extendido)
"parcialmente_conciliado" — conciliación parcial (023, extendido)
"traspaso_interno"        — vínculo activo de 024
"sin_documento"           — marcado sin documento con motivo (026, NUEVO)
"sin_conciliar"           — ninguna de las anteriores
```

`conciliado`/`parcialmente_conciliado` no distinguen si las conciliaciones que los componen tienen documento o son manuales — es un detalle de cada fila, no del estado agregado del movimiento (mismo criterio que hoy: el estado nunca depende de CÓMO se conciliaron las partes, solo de CUÁNTO).

## Entidades de solo lectura (documentos conciliables — sin cambios de esquema)

| Origen | Tabla | Id | Contraparte | Importe |
|---|---|---|---|---|
| Compras | `dbo.Compras` (vía `vw_Compras_ImporteDocumento`) | `IdDeuda` | `IdContacto` | importe bruto (mismo cálculo que usa Tarjetas) |
| Impuestos | `dbo.Impuestos` | `IdImpuesto` | `IdOrganismo` | `Importe` |
| Remuneraciones | `dbo.Remuneraciones` | `IdSalario` | `IdContacto` | suma de conceptos (ya resuelta en `remuneraciones/repository.py`) |
| Alquileres | `dbo.[Detalle Cobro Alquiler]` | `IdCobroAlquiler` | `Alquileres.IdContacto` (join) | `[Importe Cuota]` |

Esta feature nunca escribe sobre estas 4 tablas (Principio III) — el vínculo vive exclusivamente en `ConciliacionesTesoreria`/`ConciliacionesTesoreriaEstado`.

## Imputaciones firmadas y saldo compartido

`Importe` conserva el signo del documento. La restricción pasa de `Importe > 0` a `Importe > 0 OR (Importe < 0 AND TipoOrigenDocumento = 'Compras' AND IdOrigenDocumento IS NOT NULL)`. Los negativos se validan contra una Compra de importe negativo; no son montos libres. Las sumas netas del movimiento y del lote deben ser positivas. No se cambia la vista contable: ya proyecta el importe firmado según el sentido del movimiento.

Saldo en pesos = importe original convertido a pesos - SUM(imputaciones Tesorería) - SUM(imputaciones Tarjetas para Compras/Impuestos). Se conserva el signo de las NC; los históricos sobreimputados se muestran sin disponibilidad, no con disponibilidad de signo contrario. Los pagos manuales sin documento no se adjudican a facturas por inferencia. ImporteOriginal mantiene su moneda y valor fiscal; saldoPendiente siempre se presenta en pesos. No se escribe en las tablas documentales.

**Esquema real**: los IDs de documentos heredados de Access pueden ser negativos. Validar rango bigint y existencia, nunca positividad ni valor absoluto del ID. Su signo no describe una nota de crédito.
