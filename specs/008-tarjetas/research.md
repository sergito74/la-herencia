# Research: Tarjetas de Crédito (008)

Consolidado de la investigación read-only contra `WC` (INFORMATION_SCHEMA, `sys.foreign_keys`, `OBJECT_DEFINITION`, conteos reales) hecha por los especialistas `sql-server-engineer`, `financial-direction-specialist` y `administracion-cuentas` antes de este plan. Todas las cifras están confirmadas contra datos reales, no contra la spec original.

## 1. Tablas reales y discrepancias de nombre contra la spec

| Concepto de la spec | Tabla real en `WC` | PK | Filas reales |
|---|---|---|---|
| Catálogo de tarjetas | `dbo.Tarjetas` | `IdTarjeta` | 5 |
| Resumen de tarjeta | `dbo.Tarjetas_Resumenes` | `IdResumen` | 293 |
| Línea de consumo | `dbo.Tarjetas_Resumenes_Lineas` | `IdLineaConsumo` | 1694 |
| Compra en cuotas | `dbo.[Tarjetas de Credito]` | `IdPagoTarjeta` | 18 |
| Cuota | `dbo.[Cuotas Tarjetas de Credito]` | `IdAuto` | 183 |

Las dos últimas tienen nombre con espacios (requieren `[corchetes]` en T-SQL) y **no** se llaman `Tarjetas_Compras`/`Tarjetas_Cuotas` como asumía el borrador inicial de la spec. Todas las cardinalidades de la spec (293/1694/5/18/183) quedaron confirmadas exactas.

**Fuera de alcance, confirmado 0 filas** (Assumptions de la spec, correcto): `Tarjetas_Conciliacion_Link`, `Tarjetas_Conciliacion_Propuesta`, `Tarjetas_Lineas_Distrib`.

**Fuera de alcance pero con datos reales** (la spec dice "0 filas" solo para las tres de arriba, no para estas): `Tarjetas_TipoLinea` (20 filas), `Tarjetas_MapeoConceptos` (43 filas, FK a `Tarjetas.IdTarjeta`). Se ignoran igual porque la carga de resúmenes en este alcance es manual, no importación automática de archivo bancario — pero no confundir con "no existen datos".

## 2. Columnas confirmadas

### `dbo.Tarjetas`
`IdTarjeta int, TarjetaNombre varchar(50) NOT NULL, Banco varchar(50) NULL, Activa bit NOT NULL`. Las 5 tarjetas reales: AgroNacion, Corporativa Nacion, Mastercard BNA (Banco Nación); Visa Galicia, Galicia Rural (Banco Galicia). Las 5 están `Activa=1` hoy.

### `dbo.Tarjetas_Resumenes` (FK `IdTarjeta` → `Tarjetas`, declarada)
`IdResumen, IdTarjeta, ResumenCodigo varchar(80) NOT NULL, FechaCierre datetime NULL, FechaVencimiento datetime NULL, FechaAlta datetime NOT NULL, SoloCabecera bit NULL, EstadoResumen varchar(20) NOT NULL` + campos de workflow (`FechaEstado`, `UsuarioEstado`, `UsuarioCierre`, `ObservacionesEstado`, `FechaCierreProceso`, `UsuarioCierreProceso`, `ArchivoOrigen`, `TablaOrigen`) que la spec no menciona y este alcance **no usa** (vestigios de un workflow/importación que no se migra).

Cargos/impuestos de cabecera (FR-008) — **nombres reales confirmados exactos, sin discrepancia**, todos `decimal(18,2)` NULL: `ImpuestoSellos, GastosAdmin, MantCuenta, RenovAnual, PromocionBNA, CreditoContingente, IntFinanc, IntCompens, IVA105, PercepIVA105, IVA21, PercepIVA21, PercepIIBB, AjusteResAnterior`.

**`SoloCabecera` no es confiable**: está en `NULL` en el 100% de los 293 resúmenes reales — nunca se usó. El criterio operativo para "resumen sin líneas" es la ausencia de filas en `Tarjetas_Resumenes_Lineas`, no el valor de esta columna. Confirmado: 70 de 293 resúmenes (24%) no tienen ninguna línea — no es un caso marginal.

### `dbo.Tarjetas_Resumenes_Lineas` (FK `IdResumen` → `Tarjetas_Resumenes`, declarada)
`IdLineaConsumo, IdResumen, FechaCompra datetime, Detalle nvarchar(255), Importe money, FechaVencimientoCompra datetime, IdContacto int NULL, NroDocumento nvarchar(50) NULL` — coincide con la Key Entity de la spec. `IdContacto`/`NroDocumento` son FK implícitas (no declaradas) a `Contactos`; la mayoría de las 1694 líneas reales no las tiene cargada (edge case ya documentado en la spec).

Columnas extra no mencionadas en la spec: `CreditoContingente money`, `InteresPagoDiferido money` (a nivel de línea, además de existir también en la cabecera del resumen), `OrigenTabla`, `Observaciones`. **No se pudo confirmar si estos dos campos de línea ya están incluidos dentro de `Importe` o si habría que sumarlos aparte** — para evitar doble conteo silencioso, el `totalCalculado` (FR-011) usa únicamente `Σ(lineas.Importe)` + los 14 campos de cabecera de FR-008, ignorando `lineas.CreditoContingente`/`InteresPagoDiferido` como informativos. Si en implementación aparece un caso real donde estos campos de línea estén poblados y claramente no incluidos en `Importe`, revisar antes de dar el cálculo por cerrado.

31 de 1694 líneas reales (1.8%) tienen `Importe` negativo (devoluciones/notas de crédito del comercio, ej. reintegros de Mercado Libre) — se suman con su signo real, nunca con `ABS()`.

### `dbo.[Tarjetas de Credito]` (cabecera de compra en cuotas)
`IdPagoTarjeta int, Fecha datetime, IdContacto int NULL, [Nro Comprobante] int NULL, Cuotas int NULL` — **solo estas 5 columnas**. Sin `IdTarjeta`, sin FK a `Tarjetas`. Confirmado con las 18 filas reales completas: nunca existió un vínculo a tarjeta en el esquema real. Decisión de producto ya tomada (ver spec, Assumptions): la compra en cuotas no pide tarjeta, no se agrega columna al esquema.

### `dbo.[Cuotas Tarjetas de Credito]` (detalle de cuota)
`IdAuto smallint` (PK real), `IdCuotaTarjeta nvarchar(15)` (label de texto, no usar como clave), `IdPagoTarjeta int` (FK a la cabecera — existe solo como constraint residual `..._LOCAL_BACKUP${guid}`, no como FK real declarada, pero la relación de datos es consistente), `[Cuota nro] int`, `Importe money`, `Cobrado nvarchar(1)` (**`'S'`/`'N'`, no `bit`** — cuidado en el schema Pydantic/mapeo de columna), `IdOperacion int NULL` (solo 12 valores distintos entre 183 filas incluyendo NULLs; no es una FK 1:1 útil, no usar para navegación), `[Fecha Vencimiento] datetime`.

**Discrepancia real de fórmula (FR-005)**: de las 18 compras reales, 8 (44%) tienen cuotas de importe **creciente**, no iguales — evidencia de financiación con interés bancario cargada en su momento (ej. `IdPagoTarjeta=3`: cuotas de 2085.85 a 2392.17, la suma sí coincide con el importe total). El generador automático de este módulo asume financiación sin interés (cuota fija + ajuste de redondeo en la última) — es correcto para altas nuevas, pero no reproduce ese patrón histórico; esas 18 compras solo se leen, nunca se regeneran (documentado en spec, Edge Cases).

## 3. `vw_MovimientosCuenta_Base` / `vw_MovimientosCuenta_Saldo` (Cuentas Corrientes, 004)

Se leyó el `OBJECT_DEFINITION` completo de la vista real. Tiene 12 ramas `UNION ALL`, una por origen: Compras, Alquileres, Impuestos, Remuneraciones, Galicia, Banco Nacion, Pagos efectivo, Pagos/Cobros Valores Recibidos, Ret. IVA Granos, Retenciones, Ret. Ventas Hacienda.

**Hallazgo crítico, confirmado por los 3 especialistas de forma independiente: no existe ninguna rama para "Tarjetas".** `SELECT DISTINCT Origen` sobre la vista real no devuelve ese valor. El comentario en `backend/src/features/cuentas_corrientes/origen_resolver.py` (línea ~130) que menciona "Tarjetas" como ejemplo de origen no relevado que cae al default `fuera_de_alcance` es un caso **hipotético** anticipado en el código, no un caso real hoy: los movimientos de tarjeta simplemente no están en la cuenta corriente de ningún contacto, ni siquiera marcados como "fuera de alcance". La premisa original de la spec ("hoy cualquier movimiento con origen Tarjetas queda marcado fuera de alcance") no es literal — se corrigió en la spec.

`vw_MovimientosCuenta_Saldo` es trivial: mismo `SELECT` de la base + `SUM(Credito-Deuda) OVER (PARTITION BY IdContacto ORDER BY Fecha, Origen, IdOrigen ROWS UNBOUNDED PRECEDING)`.

**No hay FK ni columna que vincule `Tarjetas` con `Contactos`.** El único vínculo posible es por coincidencia textual: existen 5 `Contactos` con `Tipo Contacto = 'Tarjeta de Credito'` cuyo `Razon Social` coincide 1:1 con `Tarjetas.TarjetaNombre` (Mastercard BNA, AgroNacion, Corporativa Nacion, Visa Galicia, Galicia Rural). Se documenta como vínculo frágil (un rename de cualquiera de los dos lados lo rompe), no se migra el dato.

### Decisión de diseño (confirmada por el usuario)

La cuenta corriente de una tarjeta se construye **exclusivamente a partir del total calculado de cada resumen** de esa tarjeta — no a partir de las cuotas de compras en cuotas. Motivo: evitar doble conteo. Cuando una compra en cuotas se paga con tarjeta, sus cuotas terminan reflejadas como líneas de consumo (o parte del cargo) dentro del resumen del período correspondiente — si además cada cuota generara su propio movimiento de cuenta corriente, la misma deuda se contaría dos veces. Esto nunca se resolvió en Access tampoco (`Tarjetas_Conciliacion_Link`/`Propuesta` existen para esto, con 0 filas — el problema fue identificado en su momento y nunca operativizado). No se implementa conciliación automática; se evita el problema por diseño, no resolviéndolo.

Consecuencia: no se necesita tocar `vw_MovimientosCuenta_Base` (la vista compartida de Cuentas Corrientes de contactos) — construir una consulta o vista propia `vw_TarjetaCuenta_Movimientos` (o directamente en el `repository.py` de 008) que arme un movimiento por resumen de `Tarjetas_Resumenes`, particionado por `IdTarjeta` (no por `IdContacto`, porque una tarjeta no es un contacto). Igual criterio de saldo acumulado que 004: `SUM(Deuda-Credito) OVER (PARTITION BY IdTarjeta ORDER BY FechaCierre, IdResumen ROWS UNBOUNDED PRECEDING)`.

## 4. Resolución de FR-003 (navegación desde Cuentas Corrientes)

Con la decisión de "solo resúmenes", la resolución es más simple que lo que se planteó originalmente (no hacen falta dos orígenes distintos para cuota vs. resumen, porque las cuotas no generan movimiento). Un único origen nuevo es suficiente si en el futuro se decide exponer movimientos de tarjeta también en la cuenta corriente de un Contacto — hoy esto no es necesario porque la Historia 2 pide la cuenta corriente **de la tarjeta**, no la de un contacto. `OrigenMovimiento.tsx`/`origen_resolver.py` no necesitan tocarse en este alcance: la navegación de FR-003 vive dentro de la propia pantalla nueva de cuenta corriente de tarjeta (cada movimiento — un resumen — linkea directo a `/finanzas/tarjetas/resumenes/{idResumen}`), no requiere extender el resolver genérico de 004.

## 5. Fórmulas confirmadas

### Cuotas (FR-005)
```
cuotaBase = ROUND(importeTotal / cantidadCuotas, 2)
cuota[i]  = cuotaBase                          para i = 1..(N-1)
cuota[N]  = importeTotal - cuotaBase × (N-1)   absorbe el resto (+/- centavos)
fechaVencimiento[i] = fechaCompra + i meses    (mensual sucesiva, i = 1..N)
```
Todas las cuotas son deuda (positivas) salvo que `importeTotal` sea negativo (no observado en datos reales).

### Total calculado de un resumen (FR-011)
```
totalCalculado = Σ(lineas.Importe)                                  -- con signo real, incluye negativos
               + ImpuestoSellos + GastosAdmin + MantCuenta + RenovAnual
               + PromocionBNA + CreditoContingente + IntFinanc + IntCompens
               + IVA105 + PercepIVA105 + IVA21 + PercepIVA21 + PercepIIBB
               + AjusteResAnterior
```
Todos los campos de cabecera suman con su propio signo tal cual están almacenados — no forzar `ABS()`. Confirmado en datos reales: `AjusteResAnterior` es negativo en 2 de 293 resúmenes (resta del total, correcto); también hay negativos aislados en `RenovAnual`, `PromocionBNA`, `CreditoContingente`, `IntCompens`, `IVA105`, `IVA21`.

No existe ningún campo "Total"/"TotalBanco" en `Tarjetas_Resumenes` (confirmado contra `INFORMATION_SCHEMA`) — el contraste contra el resumen real del banco (papel/PDF) lo hace el usuario a simple vista; el sistema no lo valida automáticamente (documentado en spec, FR-011).

### Signo en la cuenta corriente de la tarjeta
Mismo criterio que la rama `Compras` de `vw_MovimientosCuenta_Base`: `Deuda = totalCalculado si > 0 else 0`, `Credito = -totalCalculado si < 0 else 0`. Un resumen con total positivo es deuda de la empresa hacia el banco; matemáticamente posible (aunque no observado) un total negativo si `AjusteResAnterior` domina el cálculo.

### Criterio de aceptación para SC-002
```
SaldoParcial(tarjeta, resumen_i) = Σ(j=1..i) [Deuda_j - Credito_j]
                                    ordenado por FechaCierre, IdResumen,
                                    para todos los resúmenes de esa tarjeta
```
Verificar contra las 5 tarjetas reales (mismo criterio que la validación manual T086/T087 de 006/007) antes de dar la feature por cerrada.

## 6. Patrón de código a reutilizar

`backend/src/db/connection.py`: `fetch_all`/`fetch_one` (solo lectura contra `WC`) y `execute_write`/`execute_insert_returning_id`/`execute_write_transaction` con `_assert_target_is_wc()` como barrera dura — sin cambios. `backend/src/features/ventas_hacienda/repository_locks.py` (o el de `compras/`) es el módulo de bloqueo exclusivo de edición a copiar para FR-013 (mismo mecanismo que Compras/Ventas: TTL + "forzar"). Estructura de referencia: `ventas_hacienda/{repository.py, repository_locks.py, router.py, schemas.py}`.

## 7. Navegación

`Tarjetas` entra en `frontend/src/components/layout/NavHeader.tsx`, dentro de `Finanzas`, como hermano de `Cuentas corrientes`/`Tesorería`/`Impuestos y retenciones`/`Arrendamientos`, entre "Cuentas corrientes" e "Impuestos y retenciones" (preserva el orden por volumen de uso ya implícito en la lista).

No se reutiliza el componente de cuenta corriente de 004 (`frontend/src/app/finanzas/cuentas-corrientes/page.tsx`) filtrado por tarjeta — la fuente de datos es estructuralmente distinta (agregada por `IdTarjeta`, no por `IdContacto`). Se construye una pantalla propia que reusa el mismo patrón visual (tabla de movimientos + saldo acumulado + link al origen).
