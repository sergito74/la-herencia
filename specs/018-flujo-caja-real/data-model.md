# Data Model: Flujo de caja real

Sin tablas nuevas (ver research.md §2). Este documento mapea las entidades conceptuales de spec.md a las tablas reales de `WC`.

## CuentasBancarias (ya existe, migración previa)

| Columna | Tipo | Notas |
|---|---|---|
| IdCuentaBancaria | int PK | |
| Banco | varchar(30) | 'BNA' \| 'Galicia' |
| NumeroCuenta | varchar(30) | Único por banco |
| FechaApertura | datetime NULL | |
| FechaBaja | datetime NULL | NULL = vigente hoy |
| SaldoApertura | money | Saldo antes del primer movimiento conocido |
| Moneda | varchar(3) | 'ARS' |

4 filas reales: BNA 12301640001709 (2010-08-31→2012-06-29, apertura -$24.219,37), BNA 12301640029280 (2012-03-30→2022-07-05, apertura $0), BNA 6150111899 (2022-02-25→vigente, apertura $0), Galicia 0000798-8 383-4 (2021-05-27→vigente, apertura $0 — Galicia trae su propio `Saldo` corrido en cada movimiento, no depende de este campo).

## Movimientos BNA (ya existe, migración previa)

| Columna relevante | Uso en esta feature |
|---|---|
| `[Fecha / Hora Mov#]` | Fecha del movimiento, clave de agregación mensual/semanal |
| `Importe` | Monto con signo (ingreso positivo, egreso negativo) |
| `Concepto` | Insumo de la regla de clasificación interno (research.md §1.2) |
| `IdContacto` | NULL → candidato a "sin clasificar" (FR-009) |
| `IdCuentaBancaria` | Distingue las 3 cuentas BNA (FR-003) |
| `CertezaCuenta` | 'Alta' en el 100% de las filas migradas — informativo, no bloquea |

## Movimientos Galicia (ya existe)

| Columna relevante | Uso en esta feature |
|---|---|
| `Fecha` | Fecha del movimiento |
| `Débitos` / `Créditos` | Se combinan en un único importe con signo para agregación (crédito positivo, débito negativo) |
| `[Grupo de Conceptos]` | Insumo de la regla de clasificación interno (research.md §1.1) |
| `Saldo` | Saldo corrido real de Galicia — usable para validar el neto agregado (no se persiste nada nuevo) |
| `IdContacto` | NULL → candidato a "sin clasificar" |

## Entidades derivadas (no persistidas, calculadas en cada consulta)

- **Período agregado**: `{fecha_inicio, fecha_fin, granularidad}` → `{ingresos, egresos, neto, movimientosInternos: {ingresos, egresos, total}}` por cuenta y total.
- **Movimiento clasificado**: un `Movimiento BNA`/`Movimiento Galicia` con un campo calculado `esInterno: bool` (resultado de las reglas de research.md §1), nunca almacenado — se recalcula en cada consulta para que un ajuste de regla no requiera migrar datos.
