# Data Model: Exportar Saldos de Cuentas Corrientes y Valores Propios (014)

Sin cambios de esquema en `WC` — toda la data ya existe (`vw_MovimientosCuenta_Base`, `vw_MovimientosCuenta_Saldo`, `dbo.[Valores propios]`). Esta spec agrega consultas nuevas y exportaciones sobre datos ya modelados.

## Saldo por contacto (nueva consulta agregada, sin tabla propia)

| Campo | Origen |
|---|---|
| `idContacto` | `vw_MovimientosCuenta_Saldo.IdContacto` |
| `razonSocial` | `vw_MovimientosCuenta_Saldo.[Razon Social]` |
| `saldoParcial` | `SaldoParcial` de la última fila por contacto (`ROW_NUMBER() OVER (PARTITION BY IdContacto ORDER BY Fecha DESC, Origen DESC, IdOrigen DESC) = 1`, mismo orden que `get_saldo` de 004) |

## Valor propio (extiende el shape ya expuesto por 003)

| Campo API | Columna SQL | Notas |
|---|---|---|
| `idValor` | `IdValor` | ya expuesto |
| `numeroCheque` | `[Numero cheque]` | ya expuesto (float/string legacy) |
| `fechaEmision` | `[Fecha emision]` | ya expuesto |
| `fechaVencimiento` | `[Fecha vencimiento]` | ya expuesto |
| `importe` | `Importe` | ya expuesto |
| `cobrado` | `Cobrado` | ya expuesto — valores reales `'S'`/`'A'`, campo soporta `'N'`/vacío |
| `fechaCobro` | `[Fecha Cobro]` | ya expuesto |
| `numeroCuenta` | `[Numero Cuenta]` | ya expuesto |
| `comentarios` | `Comentarios` | **nuevo** — no estaba en el `select_columns` de 003, se agrega para US3 |

## Reglas de validación

- El listado de saldos incluye todo `IdContacto` con al menos una fila en `vw_MovimientosCuenta_Saldo` (FR-004) — nunca filtra por saldo distinto de cero.
- El export de cuenta corriente y el de valores propios respetan exactamente los mismos filtros (`fechaDesde`/`fechaHasta`) que ya validan sus endpoints de consulta existentes (004, 003) — no se agregan filtros nuevos no soportados hoy en pantalla.
