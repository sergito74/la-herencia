# Research: Cuentas de tarjetas y de Mercado Pago

Investigación hecha el 2026-10-06 contra `WC` y el código vigente. No quedan puntos "NEEDS CLARIFICATION".

## D1 — La pata deuda vive en la vista compartida, por consumo y por cargo

- **Decisión**: se agregan ramas `UNION ALL` a `vw_MovimientosCuenta_Base`: `Tarjeta consumo` (una fila por línea de consumo en `FechaCompra`) y `Tarjeta cargo` (una fila por cada cargo del resumen en `FechaCierre`), asignadas al contacto de la tarjeta. Quedan excluidos los resúmenes con `EstadoResumen = 'Cerrado'` (saldo inicial).
- **Razón**: la lista general de cuentas corrientes y sus totales salen de esa vista, así que FR-016 se cumple sin código adicional; la fecha de consumo era el pedido de Sergio.
- **Alternativas**: (a) una fila por resumen en la fecha de cierre (la pantalla actual de 008): descartada por la aclaración del 2026-10-06; (b) calcular la deuda solo en el backend: descartada porque los totales generales no la verían.
- **Hechos medidos**: 1.805 líneas vigentes y 14 columnas de cargos por resumen; el volumen es bajo para una vista de unas 22.000 filas. Los cargos se "despivotan" con `CROSS APPLY (VALUES …)`; `IdOrigen = IdResumen * 100 + n` (n = 1..14) para que sea único dentro del origen.

## D2 — Los pagos bancarios ya están en la vista y no cambian

- **Decisión**: los 343 pagos de resumen ($58,3 M) ya acreditan la cuenta de la tarjeta porque `Movimientos BNA`/`Movimientos Galicia` tienen `IdContacto` de la tarjeta. No se agrega una rama de pagos.
- **Razón**: evita duplicar un crédito que ya existe; verificado el 2026-10-06 que ninguno de esos pagos está asignado a un proveedor.
- **Efecto a corregir con datos**, no con código: 22 pagos de la administración anterior de AgroNacion (21 del Banco Nación de 2010 a 2012 por $23.575,00, "PM/TOT. RES. AGRONACION", y 1 pago en efectivo del 26/06/2012 por $1.677,58 que figura en `Pagos efectivo` y que Codex no había encontrado en los bancos) y el débito devuelto del 01/09/2025 ($966.654,20) hoy inflan el crédito de AgroNacion (ver D3 y D4).

## D2b — Pagos de resumen sin movimiento bancario

- **Decisión**: una quinta rama `Tarjeta pago` acredita la cuenta de la tarjeta con los pagos de resumen que no tienen movimiento bancario de origen (hoy uno: "Crédito banco", $3.195,96, Visa Galicia, 31/01/2025). El control sigue señalándolos (categoría c).
- **Razón**: descubierto en el ensayo con rollback del 2026-10-06: sin esa rama, Visa Galicia mostraba una deuda de $3.196,16 contra un pendiente de $0,20; con la rama cierra en −$0,20.

## D3 — Saldo inicial: cuenta separada para la administración anterior

- **Decisión**: se crea un contacto "AgroNacion (administración anterior)" y se reasignan a él, con `ReasignacionesContacto` (el mecanismo ya usado 34 veces), los 22 pagos de 2010 a 2012 (21 del Banco Nación y 1 en efectivo). Los resúmenes `Cerrado` quedan fuera de la deuda por las ramas de D1.
- **Razón**: cumple la apertura informativa de FR-004 sin modificar las ramas bancarias de la vista y de forma reversible; es lo que Sergio describió ("punto de inicio" de la administración de Oscar y Albina).
- **Alternativas**: (a) filtrar por una fecha de apertura dentro de las ramas bancarias: toca ramas críticas de la vista; (b) contar la deuda de los resúmenes `Cerrado`: dejaría un saldo de unos $343,60 sin respaldo documental.
- **Mastercard BNA**: el pago del 05/06/2024 ($15.180,50, "MASTER XXXX3813") no tiene resumen vigente (la tarjeta no tiene resúmenes desde 05/2023). Resuelto el 2026-10-06 por Sergio: fue un débito indebido del banco contra una tarjeta ya dada de baja, reclamado sin respuesta positiva; se registra como pérdida y gasto bancario (script `registrar_debito_indebido_mastercard_bna.py`: reasignación del movimiento BNA 18020 al contacto 369 "Banco Nacion" con la explicación en el motivo; Tesorería no admite una nota aparte porque, con el movimiento asignado al banco, lo da por resuelto). Mastercard BNA queda en −$0,03, igual a su pendiente.

## D4 — Devoluciones y cruces: tabla nueva y una rama de la vista

- **Decisión**: la tabla `TarjetasCruces` registra los cruces aprobados. Un cruce `devolucion-debito` agrega la rama `Tarjeta devolución` (deuda por el importe, en la fecha de la devolución, a la cuenta de la tarjeta); un cruce `consumo-devolucion` (kit Starlink) no agrega fila contable: clasifica el consumo como resuelto y marca el ingreso de la billetera como devolución de compra.
- **Razón**: la devolución del 17/09/2025 tiene `IdContacto = 0` y por eso nunca entra en la vista; `ReasignacionesContacto` solo reemplaza el contacto de filas que la vista ya trae, no alcanza para este caso. Con el cruce, el neto de AgroNacion queda en cero.
- **Trazabilidad (FR-022)**: usuario, fecha, importe, si fue sugerido, y baja lógica con usuario y fecha; nada se borra físicamente.

## D5 — Sugerencias semi automáticas

- **Decisión**: dos reglas de sugerencia, ambas en el backend y solo de lectura, ordenadas por cercanía: (a) devolución bancaria sin contacto (ingreso) contra un pago a una tarjeta del mismo importe en una ventana de ±45 días; (b) ingreso de la billetera con descripción "Devolución de dinero" contra un consumo de tarjeta sin proveedor del mismo importe en ±45 días. Nunca se aplica sin confirmación.
- **Hechos medidos**: caso (a) BNA 17/09/2025 $966.654,20 contra BNA 18093 del 01/09/2025 (16 días); caso (b) ML mov. 20 del 20/08/2024 $249.999,00 contra la línea 505 de Visa Galicia del 15/08/2024 (5 días). Hay además 7 devoluciones de noviembre de 2025 en Visa Galicia que ya se compensan con una compra y no requieren cruce.
- **Alternativa descartada**: cruce automático masivo (Sergio pidió visto bueno).

## D6 — Mercado Pago: mismas reglas de datos, rama directa excluyendo el conducto

- **Decisión**: una rama `Mercado Pago` en la vista toma los movimientos de la billetera con `IdContacto` asignado, que no sean conducto y que no estén ya conciliados desde tesorería (para no duplicar). **Conducto** = existe otro movimiento de la misma operación (`IdOperacion`), del mismo día, con "Ingreso de dinero…" de importe opuesto (tolerancia $0,01). El crédito va al contacto cuando el importe es negativo.
- **Razón**: los 30 pagos mensuales de UATRE con ese esquema (30 pares, $721.599) ya los acredita el débito DEBIN de Galicia; sumar los de la billetera los duplicaría (lo que se corrigió el 2026-10-06 al quitar 6 conciliaciones).
- **Hecho nuevo**: el pago de UATRE del 04/09/2024 ($17.185,82, operación 86673304977) no tiene ingreso emparejado ni débito de Galicia ese mes: se pagó con fondos propios de la billetera y hoy no figura en la cuenta de UATRE. La rama nueva lo incorpora (+$17.185,82). Es el único efecto sobre contactos que no son tarjetas.
- **Sin pantalla nueva**: la marca "conducto" se expone en la lista de movimientos de Mercado Libre de Tesorería (campo `esConducto`) y en el control.
- **Flujo de caja**: `flujo_caja` lee solo `Movimientos BNA` y `Movimientos Galicia`; no consulta las ramas nuevas (verificado), así que FR-017 se cumple sin cambios.

## D7 — Mapeo tarjeta ↔ contacto explícito

- **Decisión**: tabla `TarjetasContacto` (una fila por tarjeta, `IdContacto` único), poblada con la regla actual (nombre igual y `Tipo Contacto = 'Tarjeta de Credito'`: 372, 373, 503, 532, 533) y con una columna para el contacto de la administración anterior (D3). `get_id_contacto_tarjeta` pasa a leerla.
- **Razón**: FR-006 pide asociación explícita y única; la coincidencia por nombre es frágil y no se puede usar dentro de la vista sin costo.
- **Alternativa**: una columna en `Tarjetas`; descartada para no modificar una tabla heredada.

## D8 — El control reutiliza el patrón de 031

- **Decisión**: función pura `hallazgos(raw)` sobre lo que carga un lector de solo lectura, con las categorías (a)-(j) del spec; endpoint de lectura y exportación a Excel; UI como la de integridad de vínculos.
- **Medición inicial** (debe coincidir con SC-003; los 22 pagos de la administración anterior dejan de figurar tras la preparación de datos): categoría (b) 22 movimientos de AgroNacion (y 1 de Mastercard BNA, ya registrado como gasto bancario) hoy sin resumen; (e) la devolución sin cruzar; (c) un pago con origen "Crédito banco" ($3.195,96); (i) $249.998,99 en consumos sin proveedor, que al cruzar el kit Starlink quedan en $0,01 de redondeo.
- **Invariante SC-008** (verificada en solo lectura): consumos $46.367.054,14 = vinculados $46.116.601,17 + resto acreditado $453,98 + sin proveedor $249.998,99.

## D9 — Cuenta de la tarjeta en pantalla: extender 008 en vez de crear otra

- **Decisión**: la ruta `finanzas/tarjetas/[idTarjeta]/cuenta-corriente` pasa a leer el nuevo endpoint (consumos, cargos, pagos y devoluciones con saldo cronológico) con una vista alternativa "por resumen" que reproduce el total de cada resumen. El endpoint de 008 (`/api/tarjetas/{id}/movimientos`) se conserva sin cambios hasta que la pantalla migre.
- **Razón**: evita dos cuentas de tarjeta con criterios distintos; el cálculo de totales por resumen (`calcular_total`) sigue siendo la referencia para FR-001/FR-009.

## D10 — Cuotas a vencer informativas

- **Decisión**: se leen del cronograma de cuotas existente (`Cuotas Tarjetas de Credito`) las no cobradas y se devuelven aparte del saldo. Hoy hay 183 cuotas, todas cobradas (la última venció el 01/12/2016), por lo que la sección saldrá vacía.
- **Alternativa**: no mostrarlas: descartada por la decisión de Sergio (opción B).

## D11 — Escrituras y roles

- **Decisión**: solo `POST`/`DELETE` de cruces escriben; usan el rol de escritura ya vigente (el middleware rechaza `Lectura`). Cada escritura va dentro de una transacción corta; las altas verifican que el cruce no exista ya (idempotencia por origen+destino).

## D12 — Verificación antes/después

- **Decisión**: el script de la vista se ensaya primero con `--ensayo` (transacción con rollback, sin cambios persistentes), guarda una instantánea antes de ampliar la vista (saldo por contacto y totales mensuales del flujo de caja de 2024-01 a 2026-09) y la compara después con `--comparar`. Esperado: ninguna diferencia en contactos que no son tarjetas salvo UATRE (+$17.185,82); las tarjetas pasan a su saldo real; el total general cambia solo por la deuda vigente incorporada (hoy $58.336.654,56 menos), las devoluciones cruzadas ($966.654,20 menos) y UATRE (+$17.185,82) (SC-008); los totales del flujo de caja no cambian.
- **Reversión**: la definición previa de la vista se guarda en un archivo de respaldo y el script `--revertir` la restaura; las tablas nuevas se pueden quitar sin afectar nada más.

## Revisión de especialista (T001, 2026-10-06)

Revisión de solo lectura del especialista de dirección financiera sobre `spec.md`, `research.md` y `data-model.md` (no leyó `plan.md`). Es una opinión de apoyo: las decisiones siguen siendo de Sergio.

**Conclusiones**

| Punto | Conclusión | Reparos |
|---|---|---|
| Deuda por consumo en su fecha y cargos en el cierre | De acuerdo | El saldo por fecha de consumo no coincide con lo exigible en cada vencimiento; un resumen faltante subestima la deuda sin aviso; es información de gestión, no de IVA ni de impuestos. |
| Mercado Pago como banco y regla de conducto | De acuerdo | Si el ingreso y el pago caen en días distintos el par no se detecta y se contaría dos veces; confirmar que el pago de UATRE del 04/09/2024 ($17.185,82) no tiene un débito real en otro banco; conciliar el saldo de la billetera con su propio extracto. |
| Apertura de la administración anterior de AgroNacion | De acuerdo | Confirmar que los 22 pagos de 2010-2012 son de esa administración; decir explícitamente que se abandonan los ~$343,60 de los resúmenes cerrados. |

**Recomendaciones y tratamiento**

| # | Recomendación | Tratamiento |
|---|---|---|
| 1 | Mostrar el saldo exigible (resúmenes cerrados) separado del consumo aún no resumido | A decidir con Sergio. Es una columna/subtotal adicional en la cuenta; no cambia el saldo. |
| 2 | Control de continuidad de resúmenes (meses faltantes por tarjeta) | A decidir con Sergio. Sería una categoría nueva (k) del control. |
| 3 | Qué hacer con el par de conducto que no coincide en el día | El par no emparejado se informa en el control; hoy hay un caso (UATRE 04/09/2024) y es el pago con fondos propios. Pendiente definir quién lo resuelve. |
| 4 | Confirmar con Sergio los 22 pagos de 2010-2012 y el pago de UATRE del 04/09/2024 | A confirmar con Sergio antes de ejecutar T012/T013 en `WC`. |
| 5 | Control que marque un resumen en moneda distinta de pesos | A decidir con Sergio (categoría nueva del control). |
| 6 | Documentar que el saldo es de gestión | Aplicado: el saldo de estas cuentas es de gestión y no sirve para IVA ni impuestos. |
| 7 | Revisar la tolerancia de $300 si crece el volumen | Se mantiene la regla vigente de Sergio; se revisa si se agregan tarjetas. |

Otros riesgos señalados sin regla hoy: devoluciones que llegan a un medio no modelado (efectivo u otra cuenta), qué pasa si se rechaza una sugerencia de cruce (queda pendiente en el control) y separación de funciones entre quien carga y quien aprueba (los cruces registran usuario y fecha).

## Límite conocido: cuotas a vencer por tarjeta (US1, T020)

El cronograma de cuotas (`dbo.[Tarjetas de Credito]`) guarda el proveedor de cada compra y no la tarjeta con la que se pagó, por lo que no se pueden atribuir cuotas futuras a una tarjeta. Hoy no hay cuotas pendientes (las 183 están cobradas; la última venció el 01/12/2016). La sección "Cuotas a vencer" queda vacía hasta que el cronograma registre la tarjeta. Medido el 06/10/2026: saldos de las cinco tarjetas calculados en ~1 s; cuenta de AgroNacion (779 movimientos) en 1,3 s; Visa Galicia saldo −$0,20 vs pendiente $0,20 (diferencia 0). AgroNacion muestra +$966.654,47 por la devolución BNA 9426 aún sin cruzar (se resuelve en US4).

## Cierre y revisión final del especialista financiero (06/10/2026)

Veredicto: cierre aprobado con reservas menores, ya registradas aquí.

**Diferencias aceptadas (todas menores al umbral de $300 en pesos o decididas por Sergio):**
- Saldos residuales de centavos: AgroNacion +$0,27, Visa Galicia −$0,20, Mastercard BNA −$0,03, Corporativa −$0,02; billetera de Mercado Pago $0,14.
- Nota de débito "SIN DOCUMENTO" de $332,87 en Syngenta: ajuste de gestión por diferencia de cambio (línea 5915), con respaldo previo.
- Mastercard BNA, $15.180,50 (05/06/2024): débito indebido del banco contra una tarjeta dada de baja, registrado como pérdida y gasto bancario por decisión de Sergio.
- Los 22 pagos de 2010–2012 de la administración anterior de AgroNacion ($25.252,58) quedan como apertura informativa, reasignados de forma reversible.
- Corporativa Nación: tarjeta vigente y activa por decisión de Sergio, sin uso desde 01/2026; no se desactiva.
- "Crédito banco" de $3.195,96 (Visa Galicia): pago dentro del propio resumen, sin movimiento bancario; el control no lo marca, pero si aparece el débito real del banco deberá revisarse para no duplicarlo.

**Reservas a vigilar:**
- Conducto de Mercado Pago: se detecta con misma operación, mismo día e importe opuesto; si un ingreso y su pago cayeran en días distintos se contaría doble. Hoy hay 30 pares y ningún caso así.
- UATRE 04/09/2024 (+$17.185,82): Sergio aclaró que los pagos de UATRE se debitan del Banco Galicia y que Mercado Pago solo lee el código de barras; este único pago es el que no tiene par de conducto. No se registró una confirmación expresa de que no exista un débito equivalente en Galicia: queda como punto a confirmar con Sergio.
