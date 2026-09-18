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
- `dbo.TarjetaCuotasEditLocks` (`IdPagoTarjeta` int, `LockToken` uniqueidentifier, `LockedAt` datetime, `ExpiresAt` datetime) — mismo patrón, para FR-013 sobre compras en cuotas.
