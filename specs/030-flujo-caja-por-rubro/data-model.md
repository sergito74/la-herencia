# Data Model: Flujo de caja por Rubro

No hay tablas nuevas ni escrituras. Todo es calculado en cada consulta a partir de datos existentes de `WC`.

## Parte de movimiento (unidad de cálculo, en memoria)

Un movimiento bancario produce **una o más partes**. La suma de sus partes es igual al importe del movimiento.

| Campo | Origen | Nota |
|---|---|---|
| `origenMovimiento`, `idMovimiento` | `Movimientos BNA` / `Movimientos Galicia` | Identidad del movimiento real |
| `fecha` | fecha del movimiento | Define el período y la cotización |
| `cuenta` | `CuentasBancarias` | "Nación", "Galicia CC" |
| `concepto`, `contacto` | movimiento | Para el detalle |
| `seccion` | derivado | `ingresos` \| `egresos` \| `internos` |
| `rubro` | atribución (research §1) o tipo interno (§2) | Incluye "Pendiente de aplicar", "Histórico sin aplicar", "Colocación FIMA", "Rescate FIMA", "Traspaso entre bancos" |
| `centroCosto` | compra aplicada | Solo egresos; si falta, "Sin centro de costos" |
| `importeArs` | parte del importe del movimiento | Con signo: positivo = ingreso a la cuenta |
| `documentoAplicado` | `AplicacionesPago` | Tipo y número; `null` si es remanente sin aplicar |
| `cotizacion` | `Dolar BNA.Vend_Divisa` del día o anterior (≤ 7 días) | `null` = sin tipo de cambio |
| `fechaCotizacion` | fecha de la cotización usada | Puede ser anterior a `fecha` |
| `importeUsd` | `importeArs / cotizacion` | `null` si no hay cotización |

**Reglas**:
- La suma de `importeArs` de las partes de un movimiento es igual a su importe (tolerancia 0,01 por redondeo; la última parte absorbe la diferencia).
- `seccion = internos` si y solo si el movimiento es interno según `clasificacion.py`. Si no, ingreso o egreso según el signo de la parte.
- Con `moneda=USD`, una celda suma solo las partes con cotización y reporta aparte las partes sin tipo de cambio (cantidad e importe en ARS).

## Celda

Una celda es la agregación de las partes con la misma clave (`seccion`, `centroCosto`, `rubro`) dentro de un mismo período.

El período se define con `_clave_periodo`, ya existente: semana ISO, mes, trimestre o año. Una celda es exactamente la suma de las partes que devuelve su detalle.

## Saldo por cuenta

| Cuenta | Cálculo al inicio del rango |
|---|---|
| Nación | Σ `SaldoApertura` de las cuentas BNA + Σ `Importe` de `Movimientos BNA` antes de la fecha |
| Galicia cuenta corriente | `SaldoApertura` de Galicia + Σ (`Créditos` − `Débitos`) de `Movimientos Galicia` antes de la fecha |
| Galicia Fondo FIMA | −Σ de los movimientos Galicia "Inversiones" antes de la fecha (capital neto colocado, sin rendimiento) |
| Total | Suma de las tres |

El saldo final de cada período es el saldo inicial más el neto de todas las partes del período. Los internos se incluyen en este neto: dentro de Galicia se compensan entre la cuenta corriente y el FIMA.

## Cotización del día

Tabla `dbo.[Dolar BNA]`, columna `Vend_Divisa`, clave `Fecha`. Hay datos hasta 2026-04-23. La tabla `cotizacion_bna` está vacía y no se usa.
