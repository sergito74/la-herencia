# Data Model: Cuentas de tarjetas y de Mercado Pago

Todo en la base `WC`. Se agregan dos tablas y cuatro ramas a la vista compartida; no se modifican las tablas heredadas ni las ramas existentes.

## Tablas nuevas

### `dbo.TarjetasContacto` (FR-006)

Asociación explícita y única entre cada tarjeta y el contacto que representa su cuenta corriente.

| Columna | Tipo | Notas |
|---|---|---|
| `IdTarjeta` | int, PK | Referencia a `Tarjetas`. |
| `IdContacto` | int, NOT NULL, único | Referencia a `Contactos`; un contacto no puede pertenecer a dos tarjetas. |
| `IdContactoAnterior` | int, NULL | Contacto de la cuenta de la administración anterior (hoy solo AgroNacion). |
| `Usuario` | varchar(60) | Quién la cargó. |
| `Fecha` | datetime2 | Cuándo. |

Carga inicial: 1→373, 2→503, 3→372, 4→532, 5→533 (la regla actual de nombre y tipo). `IdContactoAnterior` de AgroNacion apunta al contacto nuevo "AgroNacion (administración anterior)" (D3 de research).

### `dbo.TarjetasCruces` (FR-003, FR-019, FR-022)

Cruces aprobados por el usuario. Nunca se borran filas: se marcan como deshechos.

| Columna | Tipo | Notas |
|---|---|---|
| `IdCruce` | int identity, PK | |
| `Tipo` | varchar(30), CHECK | `devolucion-debito` o `consumo-devolucion`. |
| `IdTarjeta` | int, NOT NULL | Tarjeta involucrada. |
| `MedioOrigen` | varchar(20), NOT NULL | Medio de la devolución: `bna`, `galicia` o `mercado-libre`. |
| `IdMovimientoOrigen` | int, NOT NULL | Movimiento de la devolución. |
| `MedioDestino` | varchar(20), NULL | Para `devolucion-debito`: medio del débito original. |
| `IdMovimientoDestino` | int, NULL | Para `devolucion-debito`: movimiento del débito original. |
| `IdLineaConsumo` | int, NULL | Para `consumo-devolucion`: línea de consumo cancelada. |
| `Importe` | money, NOT NULL | Importe cruzado (positivo). |
| `Sugerido` | bit | Si el cruce vino de una sugerencia del sistema. |
| `Usuario`, `Fecha` | varchar(60), datetime2 | Quién aprobó y cuándo. |
| `Deshecho` | bit, default 0 | Baja lógica. |
| `UsuarioDeshecho`, `FechaDeshecho` | varchar(60), datetime2, NULL | Quién y cuándo lo deshizo. |

Restricciones: único por (`MedioOrigen`, `IdMovimientoOrigen`) entre los cruces no deshechos; `devolucion-debito` exige `MedioDestino` e `IdMovimientoDestino`; `consumo-devolucion` exige `IdLineaConsumo`.

## Ramas nuevas de `vw_MovimientosCuenta_Base`

Formato común de la vista: `Fecha, IdContacto, [Razon Social], Documento, [Nro Documento], Deuda, Credito, Origen, IdOrigen`. El saldo sigue siendo `Credito − Deuda` ordenado por `Fecha, Origen, IdOrigen`.

| Origen | Fuente | Fecha | Contacto | Deuda / Crédito | IdOrigen |
|---|---|---|---|---|---|
| `Tarjeta consumo` | `Tarjetas_Resumenes_Lineas` de resúmenes con estado distinto de `Cerrado` | `FechaCompra` | `TarjetasContacto.IdContacto` de la tarjeta del resumen | Importe positivo = Deuda; negativo = Crédito (por el valor absoluto) | `IdLineaConsumo` |
| `Tarjeta cargo` | Las 14 columnas de cargos de `Tarjetas_Resumenes`, no nulas y distintas de cero, de resúmenes distintos de `Cerrado` | `FechaCierre` | Ídem | Positivo = Deuda; negativo = Crédito | `IdResumen * 100 + n`, n de 1 a 14 |
| `Tarjeta devolución` | `TarjetasCruces` de tipo `devolucion-debito` no deshechas | Fecha del movimiento de la devolución | Contacto de la tarjeta | Deuda por `Importe` | `IdCruce` |
| `Mercado Pago` | `Movimientos Mercado Libre` con `IdContacto` asignado, que no sean conducto y sin conciliación en `ConciliacionesTesoreria` | `Fecha` del movimiento | `IdContacto` del movimiento | Importe negativo = Crédito; positivo = Deuda | `IdMovimiento` |

**Conducto**: el movimiento tiene otro de la misma `IdOperacion`, del mismo día, de descripción que empieza con "Ingreso de dinero" y de importe opuesto (diferencia menor a $0,01).

Los cargos del resumen son: `ImpuestoSellos`, `GastosAdmin`, `MantCuenta`, `RenovAnual`, `PromocionBNA`, `CreditoContingente`, `IntFinanc`, `IntCompens`, `IVA105`, `PercepIVA105`, `IVA21`, `PercepIVA21`, `PercepIIBB`, `AjusteResAnterior`. Las compensaciones de saldos a favor entre resúmenes no generan filas: ya están contenidas en los totales negativos de los resúmenes.

Ramas existentes que no cambian: `Tarjetas` (vínculo consumo→compra, acredita al proveedor), `Tarjeta sin imputar`, `Tarjeta impuesto`, `Banco Nacion`, `Galicia` y las demás.

## Entidades derivadas (no se almacenan)

- **Saldo de la tarjeta**: suma de `Credito − Deuda` sobre las filas del contacto de la tarjeta en la vista. Debe coincidir con el pendiente neto del módulo de tarjetas (diferencia menor a $1).
- **Cuota a vencer**: cuota no cobrada del cronograma de cuotas de tarjeta, informada aparte (hoy ninguna).
- **Hallazgo de control**: `{categoria, idTarjeta, idResumen, medio, idMovimiento, idLineaConsumo, importe, fecha, motivo}` con categoría en: `pago-en-proveedor` (a), `movimiento-sin-resumen` (b), `pago-sin-origen-o-importe` (c), `resumen-con-pendiente` (d), `devolucion-sin-cruzar` (e), `saldo-inicial-con-pagos` (f), `tarjeta-sin-contacto` (g), `consumo-sin-vinculo-con-deuda-abierta` (h), `consumo-sin-proveedor` (i), `diferencia-contrapartida` (j).
- **Sugerencia de cruce**: `{tipo, origen, destino, diasDiferencia, diferenciaImporte, puntaje}`; solo lectura.

## Reglas de validación

- Un movimiento no puede estar en dos cruces vigentes a la vez.
- El importe de un cruce `devolucion-debito` debe igualar el de la devolución y no superar el del débito (tolerancia de $0,01).
- Un cruce `consumo-devolucion` exige que la línea pertenezca a la tarjeta indicada y no tenga proveedor ni vínculo, o que su importe coincida con la devolución.
- Un resumen `Cerrado` no recibe pagos nuevos; si ya los tiene, el control lo informa.
- Los saldos de contactos que no son tarjetas deben permanecer idénticos salvo UATRE (+$17.185,82).

## Transiciones de estado

- Cruce: `vigente` → `deshecho` (con usuario y fecha). Rehacerlo crea una fila nueva.
- Consumo: `sin proveedor` → `cruzado con devolución` (por un cruce `consumo-devolucion`) → de nuevo `sin proveedor` si el cruce se deshace.
- Devolución bancaria: `sin cruzar` → `cruzada` → `sin cruzar` al deshacer.
