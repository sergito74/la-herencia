# Data Model: Tarjetas de Crédito (008)

Todas las tablas de negocio ya existen en `WC` (confirmadas por `INFORMATION_SCHEMA`/`sys.foreign_keys` reales, ver `research.md`). Este spec agrega únicamente tablas de infraestructura: `TarjetaResumenEditLocks`, `TarjetaCuotasEditLocks` (mismo patrón que `CompraEditLocks`/`VentaHaciendaEditLocks` de 006/007). No se modifica ninguna tabla existente (decisión: la compra en cuotas no se vincula a `Tarjetas`, ver Assumptions de `spec.md`).

## Tarjeta (tabla `dbo.Tarjetas`)

| Campo (API) | Columna real | Tipo | Notas |
|---|---|---|---|
| idTarjeta | IdTarjeta (PK) | int | |
| nombre | TarjetaNombre | varchar(50), NOT NULL | |
| banco | Banco | varchar(50), nullable | |
| activa | Activa | bit, NOT NULL | Determina si aparece en los combos de selección de resúmenes nuevos (FR-001, Acceptance Scenario 2 de Historia 4). Las tarjetas inactivas siguen siendo consultables en su historial. |

Catálogo de solo lectura en este alcance (5 filas reales). Sin FK ni columna hacia `Contactos` — no hay forma estructural de resolver "a qué contacto pertenece esta tarjeta"; no se necesita para ninguna historia de este alcance (ver research.md §3 sobre el vínculo frágil por nombre, documentado pero no usado en el código).

## Resumen de Tarjeta (tabla `dbo.Tarjetas_Resumenes`)

| Campo (API) | Columna real | Tipo | Obligatorio en alta | Notas |
|---|---|---|---|---|
| idResumen | IdResumen (PK, identity) | int | — (generado) | |
| idTarjeta | IdTarjeta | int, FK declarada → Tarjetas | Sí | |
| codigo | ResumenCodigo | varchar(80), NOT NULL | Sí | Usado para detectar reimportación (FR-012). |
| fechaCierre | FechaCierre | datetime, nullable | Sí | |
| fechaVencimiento | FechaVencimiento | datetime, nullable | Sí | |
| impuestoSellos | ImpuestoSellos | decimal(18,2), nullable | No (default 0) | |
| gastosAdmin | GastosAdmin | decimal(18,2), nullable | No (default 0) | |
| mantCuenta | MantCuenta | decimal(18,2), nullable | No (default 0) | |
| renovAnual | RenovAnual | decimal(18,2), nullable | No (default 0) | Observado negativo en datos reales — sumar con signo, sin `ABS()`. |
| promocionBNA | PromocionBNA | decimal(18,2), nullable | No (default 0) | Ídem. |
| creditoContingente | CreditoContingente | decimal(18,2), nullable | No (default 0) | Ídem. |
| intFinanc | IntFinanc | decimal(18,2), nullable | No (default 0) | |
| intCompens | IntCompens | decimal(18,2), nullable | No (default 0) | Observado negativo en datos reales. |
| iva105 | IVA105 | decimal(18,2), nullable | No (default 0) | Observado negativo en datos reales. |
| percepIVA105 | PercepIVA105 | decimal(18,2), nullable | No (default 0) | |
| iva21 | IVA21 | decimal(18,2), nullable | No (default 0) | Observado negativo en datos reales. |
| percepIVA21 | PercepIVA21 | decimal(18,2), nullable | No (default 0) | |
| percepIIBB | PercepIIBB | decimal(18,2), nullable | No (default 0) | |
| ajusteResAnterior | AjusteResAnterior | decimal(18,2), nullable | No (default 0) | Observado negativo en 2/293 resúmenes reales (ajuste a favor del cliente) — resta del total tal cual está guardado. |

Columnas reales no expuestas en v1 (workflow/importación automática que este alcance no migra, ver research.md §2): `FechaAlta`, `EstadoResumen`, `FechaEstado`, `UsuarioEstado`, `UsuarioCierre`, `ObservacionesEstado`, `FechaCierreProceso`, `UsuarioCierreProceso`, `ArchivoOrigen`, `TablaOrigen`. `SoloCabecera` (bit) tampoco se expone como input — está en NULL en el 100% de los datos reales y no es un indicador confiable; el criterio de "resumen sin líneas" es la ausencia de filas en `Tarjetas_Resumenes_Lineas` (FR-009).

**Campo calculado**: `totalCalculado` = `Σ(lineas.Importe)` + los 14 campos de cargos/impuestos de arriba, cada uno con su propio signo (fórmula completa en `research.md` §5). No hay columna de "total declarado por el banco" en el esquema real — el contraste es visual, no automático (FR-011).

## Línea de Consumo (tabla `dbo.Tarjetas_Resumenes_Lineas`)

| Campo (API) | Columna real | Tipo | Obligatorio en alta | Notas |
|---|---|---|---|---|
| idLineaConsumo | IdLineaConsumo (PK, identity) | int | — (generado) | |
| idResumen | IdResumen | int, FK declarada → Tarjetas_Resumenes | Sí | |
| fechaCompra | FechaCompra | datetime, nullable | Sí | |
| detalle | Detalle | nvarchar(255), nullable | Sí | |
| importe | Importe | money, nullable | Sí | 1.8% de las líneas reales son negativas (devoluciones del comercio) — sumar con signo real. |
| fechaVencimientoCompra | FechaVencimientoCompra | datetime, nullable | No | |
| idContacto | IdContacto | int, nullable | No | FK implícita a `Contactos` (no declarada). La mayoría de las líneas reales no lo tiene cargado (edge case). |
| nroDocumento | NroDocumento | nvarchar(50), nullable | No | |

Columnas reales no expuestas en v1 (no confirmado si ya están incluidas en `Importe`, ver research.md §2 — riesgo de doble conteo si se exponen sin confirmar): `CreditoContingente`, `InteresPagoDiferido`, `OrigenTabla`, `Observaciones`.

## Compra en Cuotas (tabla `dbo.[Tarjetas de Credito]`)

| Campo (API) | Columna real | Tipo | Obligatorio en alta | Notas |
|---|---|---|---|---|
| idPagoTarjeta | IdPagoTarjeta (PK, identity) | int | — (generado) | |
| fecha | Fecha | datetime, nullable | Sí | |
| idContacto | IdContacto | int, nullable | Sí | FK implícita a `Contactos` (no declarada). |
| nroComprobante | [Nro Comprobante] | int, nullable | Sí | |
| cantidadCuotas | Cuotas | int, nullable | Sí | Determina cuántas filas se generan en `Cuotas Tarjetas de Credito` al guardar (FR-005). |

**Sin columna `IdTarjeta` ni FK a `Tarjetas`** — confirmado contra las 18 filas reales completas y contra `INFORMATION_SCHEMA`. Decisión de producto: no se agrega la columna; la compra en cuotas no pide ni filtra por tarjeta (FR-004/FR-006).

`importeTotal` no es una columna propia de esta tabla — se deriva de `Σ(cuotas.Importe)` de sus cuotas generadas; no se persiste por separado.

## Cuota (tabla `dbo.[Cuotas Tarjetas de Credito]`)

| Campo (API) | Columna real | Tipo | Obligatorio | Notas |
|---|---|---|---|---|
| idCuota | IdAuto (PK real) | smallint | — (generado) | **No es identity** (confirmado con `COLUMNPROPERTY(...,'IsIdentity')` durante la implementación) — se genera a mano con `MAX(IdAuto)+1`, igual que hacía Access. `IdCuotaTarjeta` (nvarchar(15)) es un label de texto sin uso como clave, pero tiene un índice único real no filtrado — no puede quedar en NULL en una fila nueva; se genera como `'CUOT' + IdAuto` (patrón real confirmado contra los 183 valores existentes). |
| idPagoTarjeta | IdPagoTarjeta | int | Sí (FK real, aunque solo declarada como constraint residual de backup — ver research.md §2) | |
| numeroCuota | [Cuota nro] | int | Sí | |
| fechaVencimiento | [Fecha Vencimiento] | datetime | Sí | |
| importe | Importe | money | Sí | Ver fórmula de generación en research.md §5. |
| cobrado | Cobrado | **nvarchar(1) — 'S'/'N', no bit** | No (default 'N') | Mapear explícitamente a booleano en el schema Pydantic; no asumir tipo `bit`. |

`IdOperacion` (int, nullable) existe en el esquema real pero no se expone — solo 12 valores distintos entre 183 filas, no es una FK 1:1 útil (research.md §2), no se usa para navegación ni trazabilidad.

**Campos calculados** (fórmula real, confirmada contra el patrón de financiación sin interés que este generador implementa — ver research.md §5 para la discrepancia con el 44% del histórico real que sí tiene interés):
```
cuotaBase = ROUND(importeTotal / cantidadCuotas, 2)
cuota[i]  = cuotaBase                          para i = 1..(N-1)
cuota[N]  = importeTotal - cuotaBase × (N-1)
fechaVencimiento[i] = fechaCompra + i meses
```

## Movimiento de Cuenta Corriente de Tarjeta (fuente nueva, no una tabla — vista o query propia)

No existe hoy en `WC` ninguna fuente que emita movimientos de tarjeta (research.md §3 — `vw_MovimientosCuenta_Base` no tiene rama para "Tarjetas"). Este spec agrega una consulta/vista propia (`vw_TarjetaCuenta_Movimientos` o directamente en `repository.py`, a decidir en implementación) que arma **un movimiento por resumen** de `Tarjetas_Resumenes`, particionada por `IdTarjeta` (no por `IdContacto` — una tarjeta no es un contacto):

| Campo | Origen | Notas |
|---|---|---|
| idTarjeta | Tarjetas_Resumenes.IdTarjeta | Partición del saldo acumulado. |
| fecha | Tarjetas_Resumenes.FechaCierre | Orden cronológico. |
| origen | constante `"Tarjetas"` | Único origen — las cuotas de compras en cuotas no generan movimiento propio (decisión de producto, ver spec Assumptions y research.md §3, evita doble conteo). |
| idOrigen | Tarjetas_Resumenes.IdResumen | Usado por FR-003 para armar el link directo a `/finanzas/tarjetas/resumenes/{idResumen}`. |
| deuda | `totalCalculado` si > 0, si no 0 | Mismo criterio de signo que la rama `Compras` de `vw_MovimientosCuenta_Base` (research.md §5). |
| credito | `-totalCalculado` si < 0, si no 0 | |
| saldoAcumulado | `SUM(deuda - credito) OVER (PARTITION BY idTarjeta ORDER BY fecha, idResumen ROWS UNBOUNDED PRECEDING)` | Mismo patrón que `vw_MovimientosCuenta_Saldo` (004). |

Las compras en cuotas y sus cuotas **no** aparecen en esta cuenta corriente — se listan y editan solo dentro del propio dominio "Compras en cuotas" (Historia 3), con su propio estado `cobrado`/`no cobrado` por cuota (FR-007), sin proyectarse como movimiento de deuda hacia la tarjeta.

## Tablas de infraestructura nuevas en `WC`

- `dbo.TarjetaResumenEditLocks` (`IdResumen` int, `LockToken` uniqueidentifier, `LockedAt` datetime, `ExpiresAt` datetime) — mismo patrón que `VentaHaciendaEditLocks`/`CompraEditLocks`, para FR-013 sobre resúmenes.
- `dbo.TarjetaCuotasEditLocks` (`IdPagoTarjeta` int, `LockToken` uniqueidentifier, `LockedAt` datetime, `ExpiresAt` datetime) — **sin uso** desde Session 2026-09-19: Historia 3 pasó a ser solo lectura (evidencia real: las 18 compras nunca se cargaron después de dic-2015). Se deja la tabla creada por si en el futuro se retoma algún mecanismo de edición sobre este dominio, pero el código actual no la usa.

## Cambios de Session 2026-09-19 (feedback real del usuario, con Excel de resúmenes bancarios)

### `Tarjetas.Activa` (corrección de dato, no de esquema)

Mastercard BNA (`IdTarjeta=3`) fue dada de baja y reemplazada por Corporativa Nacion — corregido `Activa=0` a mano contra `WC` (dato de negocio).

### `Tarjetas_Resumenes.ArchivoOrigen` reutilizada como `urlResumenOriginal` (FR-008)

La columna `ArchivoOrigen` (varchar(255)) ya existía en el esquema real, vestigio de un mecanismo de importación automática nunca usado (0 filas pobladas, ver research.md §2) — se reutiliza tal cual para guardar el link/ruta al PDF del resumen original, mismo patrón que `documentoOriginal` en Compras/Ventas. No requirió `ALTER TABLE`.

### `dbo.Tarjetas_Resumenes_Lineas_Compras` (nueva, FR-009a)

Vincula una línea de consumo con una o varias Compras reales (facturas/NC/ND) que la documentan — confirmado con casos reales (ej. la línea "NEUMATICOS CORRAL 12/12" de `IdLineaConsumo=1023` vincula contra `Compras.IdDeuda=2143513659`, factura real `0265-00004930` de Neumáticos Corral).

| Campo (API) | Columna real | Tipo | Notas |
|---|---|---|---|
| idVinculo | IdVinculo (PK, identity) | int | — (generado) |
| idLineaConsumo | IdLineaConsumo | int, NOT NULL | FK lógica a `Tarjetas_Resumenes_Lineas` (no declarada), sin cascada real — el `repository.py` borra estos vínculos explícitamente antes de recrear las líneas en cada `PUT`/`DELETE` de resumen. |
| idCompra | IdCompra | int, NOT NULL | FK lógica a `Compras.IdDeuda` (no declarada, validada en aplicación). |
| importeImputado | ImporteImputado | money, NOT NULL | Porción del importe de la compra real que corresponde a esta línea de consumo — permite que una compra en cuotas real (financiada en varios resúmenes mensuales) tenga varios vínculos parciales, uno por línea/mes. |

**Riesgo conocido, no resuelto**: como el `PUT` de un resumen reemplaza todas sus líneas (mismo criterio "PUT reemplaza todo" que el resto de la app), cada edición borra y recrea `IdLineaConsumo`, y por lo tanto también borra los vínculos a Compras de ese resumen. Se mitiga en la práctica porque `auto_vincular_compras` (ver abajo) se vuelve a correr después de cada `PUT` — si la línea sigue trayendo el mismo `IdContacto`/`NroDocumento` (lo normal, porque esos datos no cambian al editar otra cosa del resumen), el vínculo se recrea solo en el mismo request. Solo se perdería de verdad un vínculo cargado a mano (el 14% que no matchea automático) si además se edita esa línea puntual.

### Session 2026-09-19 (segunda vuelta, feedback "el vínculo es engorroso y no funciona bien")

**Auto-vínculo, sin acción del usuario en la mayoría de los casos.** El vínculo manual (buscar proveedor, elegir de una lista, tipear el importe) resultó tener dos problemas reales: (1) es tedioso incluso cuando funciona, y (2) rara vez hacía falta, porque el dato para resolverlo solo ya estaba ahí. Verificado contra los 1694 registros reales de `Tarjetas_Resumenes_Lineas`: **1634 (96%) ya traen `IdContacto` y `NroDocumento` cargados** (no la minoría que decía la primera versión de este documento — esa afirmación era incorrecta, nunca se había medido). De esas, **1402 (86%) matchean exacto contra `Compras` por (`IdContacto`, `[Nro Documento]`)**.

`tarjetas_resumenes/repository.py` agrega `auto_vincular_compras(id_resumen)`: para cada línea sin vínculo todavía, busca Compras candidatas por (`IdContacto`, `NroDocumento`) exacto; si hay **una sola**, la vincula sola (`importeImputado` = importe de la línea); si hay cero o más de una, no hace nada (queda para el buscador manual, ya simplificado: precarga la búsqueda con el número de documento de la línea y el importe con el de la línea, en vez de arrancar todo en blanco). Se llama automáticamente en el `GET` del resumen (resuelve también el histórico ya migrado, sin que nadie tenga que reabrir/editar cada uno) y después de cada `POST`/`PUT`.

Mismo criterio para pagos: `tarjetas/repository.py` agrega `auto_vincular_pago(id_resumen)`, que busca en los movimientos bancarios reales (`get_pagos_candidatos`) un movimiento con importe exacto al `totalCalculado` dentro de ±20 días de la fecha de vencimiento, o (patrón real confirmado en Visa Galicia: el banco separa "Total Consumos" del resto de los cargos en dos débitos el mismo día) un par de movimientos del mismo día que sumen exacto. Si encuentra, vincula sola; si no, no hace nada (no reintenta si el resumen ya tiene algún pago cargado, para no duplicar). Corrida contra los 293 resúmenes reales: **185 (63%) se resolvieron solos** (single-match o par-mismo-día), sin que el usuario busque ni confirme nada.

Corrido una sola vez contra `WC` el 2026-09-19 sobre el histórico completo: 1397 vínculos de compras y 185 pagos creados de una, sin intervención manual — la cuenta corriente de cada tarjeta ya muestra los pagos reales sin que nadie haya tenido que abrir cada resumen.

### `dbo.Tarjetas_Resumenes_Pagos` (nueva, FR-002/FR-002a)

Registra el pago de un resumen — confirmado que `Movimientos BNA`/`Movimientos Galicia` ya traen `IdContacto` cargado apuntando al contacto de la tarjeta (ej. `IdContacto=532` "Visa Galicia" en `Movimientos Galicia`, concepto real "PAGO VISA EMPRESA") — no hace falta adivinar por fecha/importe, se filtra directo por ese `IdContacto` (mismo vínculo por nombre documentado en research.md §3).

| Campo (API) | Columna real | Tipo | Notas |
|---|---|---|---|
| idPago | IdPago (PK, identity) | int | — (generado) |
| idResumen | IdResumen | int, NOT NULL | FK lógica a `Tarjetas_Resumenes` (no declarada). |
| fecha | Fecha | datetime, NOT NULL | |
| importe | Importe | money, NOT NULL | |
| origen | Origen | nvarchar(20), nullable | `'BNA'`/`'Galicia'` si viene de un movimiento bancario confirmado, `NULL` si se cargó a mano. |
| idMovimientoOrigen | IdMovimientoOrigen | int, nullable | `IdMovimientoBNA`/`IdMovimiento` del movimiento bancario vinculado — usado para no volver a ofrecerlo como candidato. |

**Campo calculado, cuenta corriente de tarjeta** (actualiza la sección "Movimiento de Cuenta Corriente de Tarjeta" de arriba): además del movimiento de deuda por resumen, se agrega un movimiento de crédito por cada fila de `Tarjetas_Resumenes_Pagos` de ese resumen, con la misma fecha del pago. Se intercalan por fecha antes de calcular `saldoAcumulado`.

### Session 2026-09-21 (feedback "vinculé 2 pagos en Visa Galicia y siguen apareciendo como pendientes")

**Tolerancia de conciliación: $0.10 fijo (antes $0.02), con la diferencia siempre expuesta, nunca oculta.** Caso real reportado: `IdResumen=430` (Visa Galicia), `totalCalculado=45410.88`, pago real vinculado `45410.85` — diferencia real de $0.03, mayor a la tolerancia original de $0.02, por eso el semáforo quedaba en rojo pese a estar efectivamente pagado.

Consultado el especialista de dirección financiera (`.github/agents/07-financial-direction-specialist.agent.md`), que investigó contra los 293 resúmenes reales antes de recomendar nada:

- De 188 resúmenes con al menos un pago vinculado: 170 (90,4%) coinciden exacto, 18 (9,6%) difieren hasta $0.03 — **no hay un solo caso real entre $0.05 y $0.50**. El máximo real observado es $0.03, muy por debajo del techo teórico de error acumulado (~$0.07 sumando 14 cargos redondeados independientemente a 2 decimales cada uno en su origen bancario).
- La tolerancia debe ser un **monto fijo, no proporcional al total** — el ruido de redondeo depende de *cuántos* términos se suman (14 cargos + N líneas), no de *cuánto* suman; un resumen de $561.809 real difiere solo $0.01, uno de $45.410 difiere $0.03 — no correlaciona con el tamaño.
- **La diferencia nunca debe ocultarse silenciosamente** (principio de trazabilidad financiera, COSO) — aunque el resumen se marque conciliado dentro de tolerancia, el monto de la diferencia se expone siempre (`diferenciaRedondeo`), distinguiendo explícitamente "ajuste por redondeo" (diferencia positiva, falta cobrar centavos) de "sobre-pago" (diferencia negativa, 4 casos reales de $0.01–$0.02) — nunca fundidos en el mismo verde silencioso.

Implementado: `TOLERANCIA_CONCILIACION = 0.10` (constante en `tarjetas_resumenes/repository.py`, importada por `tarjetas/repository.py` para no duplicarla). Campo nuevo `diferenciaRedondeo` (= `totalCalculado - pagado`, con signo) en `ResumenListItem` y `MovimientoTarjeta` — `null` en las filas `origen="Pago"` de la cuenta corriente (no aplica). El frontend muestra el semáforo verde con la leyenda "Conciliado (ajuste $X)" o "Conciliado (sobre-pago $X)" cuando la diferencia es distinta de cero pero dentro de tolerancia, y "Pendiente $X" / "Sobre-pago $X" cuando la supera.

### Historia 3 (compras en cuotas): solo lectura

Evidencia real: las 18 filas de `[Tarjetas de Credito]` van de julio 2013 a diciembre 2015, ninguna posterior — el mecanismo está abandonado hace una década. El mecanismo de financiación en cuotas vigente (AgroNacion, hoja "Compras" de `Listado Resumenes.xlsx`) es otro: cada cuota se factura como una línea de consumo repetida en el resumen mensual, con `CreditoContingente`/`InteresPagoDiferido` calculados por línea — campos que ya existían sin usar en `Tarjetas_Resumenes_Lineas` (research.md §2, marcados entonces como "no confirmado si se usan"; ahora confirmado con el Excel real). No se implementó ese mecanismo de financiación por línea en este alcance (fuera de lo pedido); solo se bajó la escritura del módulo obsoleto.
