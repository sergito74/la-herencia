# Feature Specification: Cuentas de tarjetas y de Mercado Pago

**Feature Branch**: `034-cuenta-corriente-tarjetas`

**Created**: 2026-10-06

**Status**: Implementado (06/10/2026)

**Input**: User description: "Cada entidad de tarjeta (AgroNacion, Corporativa Nación, Mastercard BNA, Visa Galicia, Galicia Rural) debe tener su propia cuenta corriente completa para controlar lo que se le debe. Hoy solo recibe los pagos bancarios como crédito y nunca la deuda del resumen. Debe haber además un control de integridad que detecte pagos duplicados." (Sergio, 2026-10-06)

## Contexto

Las cinco tarjetas ya existen como entidades con contacto propio y se cargan sus resúmenes, consumos y pagos (módulos 008 y 009). Hoy la cuenta corriente de cada tarjeta solo contiene los **pagos bancarios** de los resúmenes, como crédito. Nunca recibe la **deuda** del resumen, así que su saldo no significa nada (por ejemplo AgroNacion figura con +$31 M a favor, cuando en realidad no se le debe nada). Los proveedores, en cambio, ya quedan acreditados una sola vez a través de los vínculos consumo→documento; ese comportamiento es correcto y no debe cambiar.

Situación medida el 2026-10-06 (en pesos, antes de esta funcionalidad):

| Tarjeta | Contacto | Resúmenes | Total de resúmenes | Pagos bancarios | Pendiente neto |
|---|---|---|---|---|---|
| AgroNacion | 373 | 113 (2011-11 a 2026-07; 8 son saldo inicial) | $30.194.174,94 | $30.193.831,61 (149) | $0 |
| Corporativa Nación | 503 | 29 | $1.987.011,85 | $1.987.011,83 (21) | $0,02 |
| Mastercard BNA | 372 | 79 | $1.032.579,94 | $1.032.579,91 (80) | $0,03 |
| Visa Galicia | 532 | 63 | $19.787.623,22 | $19.787.623,02 (65) | $0,20 |
| Galicia Rural | 533 | 34 | $5.335.608,21 | $5.335.608,21 (28) | $0 |

Hay además movimientos bancarios asignados a contactos de tarjeta que no están vinculados a ningún resumen (22 movimientos por $990.229,20 en AgroNacion, incluido el débito de $966.654,20 del 01/09/2025 que el banco devolvió el 17/09/2025, y 1 por $15.180,50 en Mastercard BNA, resuelto el 06/10/2026 como débito indebido del banco: pérdida y gasto bancario), y la devolución de ese débito figura **sin contacto**.

Medición de la contrapartida con proveedores (2026-10-06, sin contar los resúmenes de saldo inicial): de $46.367.054,14 de consumos con tarjeta, $46.116.601,17 ya están vinculados a documentos de proveedores u organismos, $453,98 quedan como resto acreditado al proveedor de la línea y $249.998,99 no tienen proveedor asignado (de los cuales $210.662,00 no tienen ni proveedor ni vínculo). Esos $249.998,99 corresponden al kit Starlink comprado en Mercado Libre y luego cancelado: Visa Galicia registra el consumo "MERPAGO*BESTBOUTIQUE" del 15/08/2024 por $249.999,00 (ya marcado sin documento, con la nota "Devuelto el importe en Mercado Libre") y la billetera de Mercado Libre recibió la devolución de $249.999,00 el 20/08/2024, movimiento que hoy no está cruzado con nada; el resto son siete devoluciones de noviembre de 2025 por $39.337,00 contra una compra de $110.760,27 que ya se compensan entre sí. La tarjeta conserva la deuda por el consumo (se paga con el resumen) y la devolución es un crédito en la cuenta de Mercado Pago, no una deuda de proveedor ni un gasto.

## Clarifications

### Session 2026-10-06

- Q: ¿En qué fecha se registra la deuda con la tarjeta? → A: En la fecha del consumo, que es cuando la tarjeta realmente procesó la operación. Los cargos propios del resumen (sin fecha de consumo) van en la fecha de cierre.
- Q: ¿Cómo se cruzan las devoluciones con su débito? → A: De forma semi automática: el sistema sugiere el cruce y el usuario da el visto bueno.
- Q: ¿Cómo se tratan los resúmenes de saldo inicial de una administración anterior? → A: Como apertura informativa, sin afectar el saldo ni generar pendientes.
- Q: ¿La deuda con las tarjetas se suma también a los totales generales (cuentas a pagar) y al flujo de caja? → A: Sí a los totales generales de cuentas corrientes y sus exportaciones; el flujo de caja real no se modifica porque se arma con movimientos bancarios y ya refleja la salida de dinero cuando se paga el resumen (sumarle la deuda contaría la misma plata dos veces).
- Q: ¿Qué se hace con el débito de $15.180,50 del 05/06/2024 contra la Mastercard BNA sin resumen? → A: Fue un débito indebido del banco contra una tarjeta ya dada de baja, reclamado sin respuesta positiva: se registra como pérdida y gasto bancario (decisión de Sergio, 2026-10-06), reasignándolo al contacto del Banco Nación con su explicación; la cuenta de la Mastercard queda en $0,03 (su pendiente).
- Q: ¿Se incorporan las tres sugerencias del especialista financiero (saldo exigible, continuidad de resúmenes, moneda)? → A: Sí (Sergio, 2026-10-06): la cuenta separa el saldo exigible del consumo aún no resumido; el control agrega una categoría de continuidad con evidencia (no por simple mes sin resumen, porque las tarjetas no emiten resumen en meses sin actividad) y una de indicios de otra moneda (no existe un campo de moneda); se documenta que el saldo es de gestión.
- Q: ¿Mercado Pago necesita una pantalla nueva o alcanza con las reglas de datos de un banco? → A: Alcanza con las mismas reglas de datos que un banco (movimientos con contacto, conducto, traspasos y cruce de devoluciones) usando las pantallas de Tesorería existentes; no se crea una pantalla nueva para Mercado Pago.
- Q: ¿Mercado Pago queda fuera del alcance? → A: No: es una entidad financiera como un banco y debe tratarse igual (movimientos, saldo, asignación de contactos, traspasos con bancos propios, sin contar dos veces un mismo pago).
- Q: En los pagos mensuales de UATRE, ¿qué movimiento es el pago real? → A: El débito del Banco Galicia (DEBIN). Mercado Pago solo se usa para leer el código de barras y generar el DEBIN (conducto); en otros casos la billetera sí actúa como medio de pago.
- Q: ¿Qué contrapartida tiene un consumo cancelado cuya devolución no volvió a la tarjeta sino a la billetera de Mercado Pago (caso Starlink)? → A: Un débito en la tarjeta (el consumo, que se sigue pagando con el resumen) y un crédito en la cuenta de Mercado Pago (la devolución); el cruce entre ambos se sugiere y el usuario lo aprueba.
- Q: ¿Cómo se evita que la deuda de la tarjeta se duplique con la deuda de los proveedores? → A: Cada peso de consumo que la tarjeta registra como deuda debe tener como contrapartida un único crédito en el proveedor u organismo (vínculo con su documento o resto sin imputar), de modo que la obligación se cuente una sola vez, en la tarjeta; el control detecta los consumos donde esto no se cumple.
- Q: Cuando una compra se paga en cuotas con la tarjeta, ¿la deuda incluye las cuotas futuras que todavía no llegaron en ningún resumen? → A: No se suman al saldo; se muestran aparte como "cuotas a vencer", solo informativas.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Saber cuánto se le debe a cada tarjeta (Priority: P1)

Sergio abre la cuenta corriente de una tarjeta y ve, en orden cronológico, cada consumo como deuda en la fecha en que la tarjeta lo procesó, los cargos propios de cada resumen (intereses, impuestos, gastos) como deuda en la fecha de cierre, y cada pago bancario como crédito, con el saldo acumulado. El saldo final es lo que hoy se le debe a esa entidad. Puede elegir un período y exportar el resultado.

**Why this priority**: es el requisito central: controlar lo que se debe a cada entidad. Sin la deuda del resumen la cuenta no sirve.

**Independent Test**: se prueba con una sola tarjeta (por ejemplo Visa Galicia): el saldo final coincide con el pendiente neto que ya informa el módulo de tarjetas y cada fila se puede rastrear a su resumen o a su movimiento bancario.

**Acceptance Scenarios**:

1. **Given** una tarjeta con resúmenes y pagos cargados, **When** se abre su cuenta corriente, **Then** cada consumo aparece como deuda en su fecha de consumo, los cargos del resumen aparecen como deuda en la fecha de cierre, los consumos negativos (devoluciones o notas de crédito del comercio) aparecen como crédito en su fecha, y cada pago aparece como crédito, con saldo acumulado en orden de fecha.
   - Además, **Given** un resumen cualquiera, **When** se lo agrupa, **Then** la suma de sus consumos y cargos coincide con el total del resumen del módulo de tarjetas.
2. **Given** la cuenta de AgroNacion, **When** se consulta el saldo, **Then** los resúmenes marcados como saldo inicial de una administración anterior no generan deuda ni pendiente, y el saldo final coincide con el pendiente neto del módulo de tarjetas ($0); además la cuenta indica que existe una apertura informativa de la administración anterior y permite abrir esa cuenta.
3. **Given** un período elegido (desde/hasta), **When** se filtra, **Then** el saldo inicial del período refleja todo lo anterior y las filas listadas son solo las del período.
4. **Given** una cuenta con filas, **When** se exporta, **Then** el archivo contiene las mismas filas y saldos que la pantalla.

---

### User Story 2 - Que la deuda con las tarjetas no altere los saldos de proveedores (Priority: P1)

La cuenta de cada tarjeta incorpora la deuda del resumen sin duplicar nada. Los proveedores siguen acreditados una sola vez por sus vínculos consumo→documento, y los pagos bancarios de los resúmenes siguen contando solo en la cuenta de la tarjeta.

**Why this priority**: es la condición para poder confiar en todas las cuentas corrientes; un error aquí duplica o borra pagos en cuentas ajenas.

**Independent Test**: se compara el saldo de todos los contactos que no son tarjetas antes y después de la funcionalidad: no cambia ninguno. Los saldos de las tarjetas pasan a ser los de la historia 1.

**Acceptance Scenarios**:

1. **Given** el estado previo a la funcionalidad, **When** se activa la deuda de las tarjetas, **Then** el saldo de cada contacto que no es tarjeta es idéntico al anterior.
2. **Given** un consumo pagado con tarjeta y vinculado a una factura de un proveedor, **When** se paga el resumen por banco, **Then** el proveedor aparece acreditado una sola vez (por el vínculo) y el pago bancario aparece solo en la cuenta de la tarjeta.

---

### User Story 3 - Detectar pagos duplicados y datos inconsistentes (Priority: P2)

Un panel de control lista, por tarjeta, todo lo que rompe la integridad de las cuentas, para corregirlo antes de que distorsione un saldo: pagos de resúmenes asignados a un proveedor; movimientos bancarios asignados a una tarjeta sin resumen vinculado; pagos de resumen sin movimiento bancario o con importe distinto; resúmenes con saldo pendiente mayor a la tolerancia; débitos devueltos sin su devolución cruzada; resúmenes cerrados como saldo inicial que reciben pagos.

**Why this priority**: es la garantía contra la duplicación de pagos que pidió Sergio, pero se puede entregar después de ver los saldos.

**Independent Test**: se siembra o se identifica un caso de cada tipo (por ejemplo, un pago de tarjeta asignado a un proveedor) y el panel lo muestra con el movimiento, el resumen y la tarjeta involucrados; con los datos actuales muestra exactamente los casos conocidos del contexto.

**Acceptance Scenarios**:

1. **Given** un movimiento bancario que paga un resumen pero está asignado a un proveedor, **When** se abre el panel, **Then** aparece como "pago de tarjeta en cuenta de proveedor" con el proveedor, el resumen y el importe.
2. **Given** un movimiento asignado a una tarjeta sin resumen vinculado, **When** se abre el panel, **Then** aparece como "movimiento sin resumen" con su fecha e importe.
3. **Given** el débito de $966.654,20 del 01/09/2025 y su devolución del 17/09/2025, **When** están cruzados entre sí, **Then** no se informan como anomalía y la devolución cuenta como contrapartida del débito en la cuenta de la tarjeta.
4. **Given** un resumen con saldo pendiente mayor a la tolerancia, **When** se abre el panel, **Then** aparece con el importe pendiente neto.

---

### User Story 4 - Devoluciones de débitos de tarjeta (Priority: P2)

Cuando el banco devuelve un débito de un resumen, el sistema sugiere el cruce de la devolución con su débito y, con el visto bueno del usuario, la devolución se refleja en la cuenta de la tarjeta como contrapartida del pago original, de modo que el neto pagado sea correcto y ningún movimiento quede sin contacto.

**Why this priority**: sin esto la cuenta de AgroNacion muestra $966.654,20 pagados de más o un movimiento huérfano; corrige un caso real conocido.

**Independent Test**: con el caso del 01/09/2025 (débito) y 17/09/2025 (devolución) la cuenta de AgroNacion muestra el neto sin diferencia y la devolución deja de figurar sin contacto.

**Acceptance Scenarios**:

1. **Given** un débito de resumen y su devolución del mismo importe, **When** el sistema detecta la coincidencia, **Then** propone el cruce y, si el usuario lo aprueba, la cuenta de la tarjeta registra el pago como crédito y la devolución como deuda por el mismo importe.
2. **Given** varias candidatas posibles para una devolución, **When** se muestra la sugerencia, **Then** se listan ordenadas por cercanía de fecha e importe y el usuario elige una o las rechaza; si las rechaza, la devolución queda pendiente de cruzar.
3. **Given** una devolución sin débito identificable, **When** se revisa el panel, **Then** figura como pendiente de cruzar.

---

### User Story 5 - Mercado Pago tratado como un banco (Priority: P2)

Los movimientos de la billetera de Mercado Pago siguen las mismas reglas de datos que los de Banco Nación y Galicia: un pago hecho con fondos de la billetera acredita al contacto asignado; un pago que solo usa la billetera como conducto (leer el código de barras y generar el DEBIN) se atribuye al banco de origen y no se cuenta dos veces; y la devolución de una compra pagada con tarjeta (kit Starlink) se cruza con su consumo. Todo se ve en las pantallas de Tesorería existentes, sin una pantalla nueva.

**Why this priority**: corrige errores reales (el duplicado de UATRE y la devolución de $249.999,00 sin cruzar) y evita que vuelvan a ocurrir, pero las cuentas de las tarjetas ya son útiles sin esto.

**Independent Test**: con los pagos mensuales de UATRE y el kit Starlink: cada pago de UATRE aparece una sola vez en la cuenta de UATRE y la devolución queda cruzada con su consumo de Visa Galicia.

**Acceptance Scenarios**:

1. **Given** un ingreso desde Galicia y un pago de UATRE con el mismo identificador de operación, importe y día en la billetera, **When** se consulta la cuenta de UATRE, **Then** el pago figura una sola vez, atribuido al débito de Galicia, y los dos movimientos de la billetera figuran como conducto sin efecto en su saldo.
2. **Given** un movimiento de la billetera que paga con fondos propios y tiene un contacto asignado, **When** se consulta la cuenta de ese contacto, **Then** el movimiento la acredita sin necesidad de conciliación manual.
3. **Given** la devolución de $249.999,00 del kit Starlink en la billetera y su consumo en Visa Galicia, **When** el usuario aprueba el cruce sugerido, **Then** la tarjeta conserva el débito, la billetera registra el ingreso y el consumo deja de figurar como "sin proveedor".

---

### User Story 6 - Navegar de la cuenta al detalle (Priority: P3)

Desde cualquier fila de la cuenta de una tarjeta se llega al resumen (con sus consumos y vínculos) o al movimiento bancario que le dio origen.

**Why this priority**: mejora la trazabilidad (la constitución exige poder rastrear cada valor a su origen), pero la cuenta ya es útil sin esto.

**Independent Test**: se hace clic en un resumen y en un pago de la cuenta y se llega al detalle correcto de cada uno.

**Acceptance Scenarios**:

1. **Given** una fila de resumen, **When** se la abre, **Then** se muestra el resumen existente del módulo de tarjetas.
2. **Given** una fila de pago, **When** se la abre, **Then** se muestra el movimiento bancario de origen y el resumen que cancela.

---

### Edge Cases

- Consumo cuya fecha cae dentro del período de un resumen anterior al de su cierre (compras en cuotas o consumos procesados días después): se registra en su fecha de consumo y se agrupa en el resumen donde figura.
- Resumen con saldo a favor (total negativo): reduce la deuda de la tarjeta y se compensa con el resumen posterior de la misma tarjeta, sin contarse dos veces.
- Resumen con total cero o solo cabecera (sin consumos): aparece con importe cero y no genera pendiente.
- Pago parcial o excedente de pago de un resumen: el saldo refleja la diferencia; el excedente queda como crédito a favor de Sergio.
- Un mismo movimiento bancario que paga varios resúmenes (distribución de un pago en varias asignaciones): se acredita una sola vez por cada asignación, nunca por el total en cada una.
- Compra en cuotas cuyas cuotas futuras aún no llegaron en un resumen: se informan como "cuotas a vencer" y no modifican el saldo; cuando la cuota llega en un resumen, deja de ser "a vencer" y pasa a ser deuda en su fecha de consumo.
- Mes sin resumen en una tarjeta sin actividad (por ejemplo AgroNacion tiene 64 meses sin resumen desde 2012 por falta de consumos): no es un hallazgo; solo se señala la falta de continuidad cuando hay evidencia (pendiente sin resumen posterior o último resumen de más de 92 días en una tarjeta activa).
- Tarjeta inactiva (Mastercard BNA): su historial se sigue pudiendo consultar.
- Resúmenes marcados como saldo inicial (AgroNacion 571 a 578): son informativos; si recibieran pagos, el control lo informa.
- Tarjeta sin contacto asociado o con más de un contacto: el control lo informa y la tarjeta no se muestra con un saldo engañoso.
- Pago sin movimiento bancario de origen (hay uno de $3.195,96 con origen "Crédito banco"): se muestra con su origen y el control lo señala.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: La cuenta corriente de cada tarjeta MUST registrar cada consumo como deuda en la fecha del consumo (la fecha real en que la tarjeta procesó la operación) y los cargos propios de cada resumen (impuestos, gastos, intereses, percepciones, ajustes) como deuda en la fecha de cierre del resumen; los consumos negativos MUST registrarse como crédito en su fecha. La suma de lo registrado por cada resumen MUST coincidir con el total del resumen que informa el módulo de tarjetas (consumos más cargos); las compensaciones de saldos a favor entre resúmenes de la misma tarjeta no cambian esa suma porque ya están contenidas en los totales negativos de los resúmenes.
- **FR-002**: La cuenta corriente de cada tarjeta MUST incluir cada pago bancario de un resumen como crédito, por el importe asignado a cada resumen, sin duplicar el mismo movimiento; los pagos de resumen que no tienen movimiento bancario de origen (hoy uno, "Crédito banco" de $3.195,96 en Visa Galicia) también acreditan la cuenta y quedan señalados por el control.
- **FR-003**: Una devolución bancaria de un débito de resumen MUST poder cruzarse con su débito y quedar registrada en la cuenta de la tarjeta como contrapartida (deuda), sin movimientos huérfanos sin contacto. El sistema MUST sugerir el cruce (mismo importe con tolerancia de $0,01, tarjeta compatible y hasta 45 días de diferencia entre las fechas, ordenando las candidatas por cercanía) y el usuario MUST dar el visto bueno antes de que se aplique; nunca se cruza sin confirmación.
- **FR-004**: Los resúmenes marcados como saldo inicial de una administración anterior (estado "Cerrado") y los pagos de esa misma administración MUST NOT generar deuda, crédito ni pendiente en la cuenta de la tarjeta vigente; se muestran como apertura informativa en una cuenta separada de la administración anterior (hoy AgroNacion: resúmenes 571 a 578 y 22 pagos de 2010 a 2012: 21 del Banco Nación por $23.575,00 y 1 en efectivo por $1.677,58).
- **FR-005**: Los saldos de todos los contactos que no son tarjetas MUST permanecer idénticos a los actuales, con la única excepción de los contactos que reciben pagos hechos con fondos propios de la billetera de Mercado Pago (FR-020a; hoy solo UATRE, por el pago del 04/09/2024 de $17.185,82, que no tiene débito en Galicia y hoy no figura en su cuenta); los proveedores MUST seguir acreditados una sola vez por los vínculos consumo→documento.
- **FR-006**: Cada tarjeta MUST tener asociado de forma explícita y única el contacto de su cuenta; el sistema MUST informar cualquier tarjeta sin contacto asociado o con más de uno.
- **FR-007**: Cada fila de la cuenta MUST indicar su origen (consumo, cargo del resumen, pago o devolución), su documento o movimiento, fecha, deuda, crédito y saldo acumulado, y MUST poder rastrearse a su registro de origen.
- **FR-008**: La pantalla MUST abrir con un resumen de las cinco tarjetas (saldo de cada una y total) y MUST permitir elegir una tarjeta para ver su cuenta, filtrar por período (el saldo inicial refleja todo lo anterior) y exportar las filas con sus saldos.
- **FR-009**: El saldo final de cada tarjeta MUST coincidir (diferencia menor a $1) con el pendiente neto que informa el módulo de tarjetas para la misma fecha.
- **FR-010**: El control de integridad MUST detectar y listar: (a) pagos de resúmenes asignados a un proveedor; (b) movimientos bancarios asignados a una tarjeta sin resumen vinculado; (c) pagos de resumen sin movimiento bancario de origen o con importe distinto al movimiento; (d) resúmenes con saldo pendiente mayor a la tolerancia; (e) devoluciones sin cruzar; (f) resúmenes de saldo inicial con pagos; (g) tarjetas sin contacto asociado; (h) consumos de tarjeta sin vincular a un documento cuyo proveedor tiene una deuda abierta por el mismo importe, que contarían la obligación dos veces en el total general; (i) consumos de tarjeta sin proveedor ni documento, para clasificarlos o cruzarlos con una devolución en otro medio propio (sugerencia con visto bueno); (j) diferencia entre la deuda de consumos de cada tarjeta y los créditos que recibieron los proveedores por esos mismos consumos; (k) continuidad de resúmenes: tarjetas activas cuyo último resumen cargado tiene más de 92 días, y resúmenes con pendiente mayor a la tolerancia sin un resumen posterior (no se señala un mes sin resumen por sí solo, porque una tarjeta sin actividad no emite resumen); (l) resúmenes con indicios de otra moneda (USD, U$S, dólar o euro en el detalle de los consumos o en las observaciones), porque el sistema no tiene un campo de moneda.
- **FR-011**: El control MUST mostrar para cada hallazgo la tarjeta, el resumen o movimiento, el importe y el motivo, y MUST permitir exportarlo.
- **FR-012**: La tolerancia de pendiente MUST ser la misma que usa el módulo de tarjetas (diferencias menores a $300 en pesos se consideran cerradas; nunca se usa un umbral en dólares).
- **FR-013**: Solo los usuarios con permiso de escritura MUST poder cruzar devoluciones; la consulta y el control MUST estar disponibles para todos los roles que ya pueden ver cuentas corrientes.
- **FR-014**: Las escrituras necesarias MUST realizarse únicamente en `WC`, con backup verificado previo a cualquier cambio de estructura o carga masiva, y sin alterar `LaHerencia` ni los archivos Access.
- **FR-023**: La cuenta de cada tarjeta MUST informar, a la fecha elegida, cuánto del saldo es **exigible** (consumos y cargos de resúmenes con fecha de cierre hasta esa fecha, menos los pagos) y cuánto es **consumo aún no resumido** (consumos hasta esa fecha que figuran en resúmenes que cierran después); la suma de ambos MUST coincidir con el saldo de la cuenta (diferencia menor a $1).
- **FR-024**: Toda pantalla y exportación de la cuenta de una tarjeta MUST indicar que el saldo es información de gestión y no sirve para IVA ni para impuestos.
- **FR-015**: Las cuotas futuras de compras pagadas en cuotas con la tarjeta, que todavía no figuran en ningún resumen cargado, MUST mostrarse aparte como "cuotas a vencer" (fecha de vencimiento e importe) y MUST NOT sumarse al saldo de la cuenta; el saldo solo incluye lo informado en resúmenes cargados.
- **FR-016**: La deuda con las tarjetas MUST incluirse en el listado general de cuentas corrientes y en sus totales y exportaciones (cuentas a pagar), de modo que cada tarjeta aparezca con su saldo real y deje de distorsionar los totales con créditos sin contrapartida.
- **FR-017**: El flujo de caja real (movimientos bancarios) MUST NOT cambiar: la salida de dinero por el pago de un resumen ya figura cuando se paga y no se le suma la deuda de la tarjeta, para no contarla dos veces.
- **FR-018**: La obligación por un consumo con tarjeta MUST contarse una sola vez en el total general de cuentas corrientes: la deuda de la tarjeta por el consumo MUST tener como contrapartida un único crédito equivalente en la cuenta del proveedor u organismo (vínculo con su documento, o resto sin imputar de la línea); un consumo sin proveedor ni documento MUST quedar señalado y contarse solo en la tarjeta.
- **FR-019**: Un consumo de tarjeta cancelado cuya devolución se acredita en otro medio propio (billetera de Mercado Pago) MUST poder cruzarse con el movimiento de devolución: la tarjeta conserva la deuda por el consumo, la cuenta de Mercado Pago registra el crédito por la devolución, y el consumo deja de figurar como "sin proveedor"; no es gasto ni deuda de proveedor. El cruce se sugiere y se aprueba con el mismo criterio de FR-003.
- **FR-020**: La cuenta de Mercado Pago MUST recibir el mismo tratamiento que los bancos y distinguir dos usos. (a) **Medio de pago**: cuando la billetera paga con fondos propios (compras, pagos con QR, transferencias), el movimiento con contacto asignado MUST acreditar o debitar la cuenta de ese contacto sin conciliación manual. (b) **Conducto**: cuando la billetera solo se usa para leer el código de barras de una boleta y generar el DEBIN con el que se paga desde un banco propio (un ingreso desde ese banco y un pago de la misma operación, mismo importe y día), el pago MUST atribuirse al movimiento del banco de origen (por ejemplo el débito DEBIN de Galicia), y los dos movimientos de la billetera MUST reconocerse como conducto: ni pago a un tercero ni traspaso, con efecto neto cero en su saldo. En ningún caso un mismo pago a un proveedor u organismo se cuenta más de una vez. Estas reglas se aplican con las pantallas de Tesorería existentes; esta funcionalidad no crea una pantalla nueva para Mercado Pago.
- **FR-021**: El saldo de la cuenta de Mercado Pago MUST coincidir con el saldo informado por la propia billetera en el último movimiento, y las devoluciones de compras pagadas con tarjeta MUST figurar como ingreso de la billetera (FR-019).
- **FR-022**: Cada cruce aprobado (devolución con su débito, devolución de billetera con su consumo) MUST registrar quién lo aprobó, cuándo y qué sugerencia se aceptó, y MUST poder deshacerse con registro de quién lo deshizo y cuándo.

### Key Entities

- **Entidad de tarjeta**: cada una de las cinco tarjetas con su banco, estado activo/inactivo y el contacto que representa su cuenta corriente.
- **Resumen de tarjeta**: documento mensual con consumos, cargos, fechas de cierre y vencimiento, estado (por ejemplo saldo inicial) y compensaciones; constituye la deuda con la entidad.
- **Pago de resumen**: asignación de un movimiento bancario (Banco Nación o Galicia) a un resumen por un importe; constituye el crédito.
- **Devolución de pago**: movimiento bancario que revierte un débito de resumen y se cruza con él.
- **Cuota a vencer**: cuota futura de una compra en cuotas con tarjeta que aún no llegó en un resumen; se informa aparte, sin afectar el saldo.
- **Cuenta de Mercado Pago (billetera)**: entidad financiera propia, tratada igual que un banco (hoy registrada como cuenta bancaria "Mercado Libre (CVU)"): sus movimientos de ingreso y egreso, su saldo, la asignación de contactos a sus pagos y sus traspasos con los bancos propios.
- **Compensación**: saldo a favor de un resumen aplicado una sola vez a un resumen posterior de la misma tarjeta.
- **Hallazgo de control**: anomalía detectada por el control de integridad, con su tarjeta, movimiento o resumen, importe y motivo.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Para las cinco tarjetas, el saldo de su cuenta corriente coincide con el pendiente neto del módulo de tarjetas con una diferencia menor a $1, una vez resuelto el movimiento que el control señala (hoy: el cruce de la devolución del 17/09/2025 de AgroNacion; el débito indebido de Mastercard BNA ya se registró como gasto bancario) (valores medidos antes de esa resolución: AgroNacion $0, Corporativa Nación $0,02, Mastercard BNA $0,03, Visa Galicia $0,20, Galicia Rural $0).
- **SC-002**: El saldo de los contactos que no son tarjetas es idéntico antes y después de la funcionalidad en el 100% de los contactos comparados, salvo la excepción de FR-005, y el total general de cuentas corrientes deja de incluir los créditos sin contrapartida de las tarjetas (hoy unos $58 M).
- **SC-003**: El control detecta el 100% de los casos conocidos de contexto: antes de preparar los datos de AgroNacion, los 22 movimientos de AgroNacion y el 1 de Mastercard BNA sin resumen vinculado; una vez reasignados los 22 pagos de la administración anterior y registrado el débito de Mastercard como gasto bancario, el débito 18093 de AgroNacion; en ambos momentos, la devolución sin contacto y el pago con origen "Crédito banco".
- **SC-004**: Sergio responde "cuánto se debe hoy a cada tarjeta" consultando una sola pantalla, sin cálculo manual, y la exportación reproduce los mismos saldos.
- **SC-005**: La cuenta completa de la tarjeta con más historia (AgroNacion: 113 resúmenes y 149 pagos) se muestra en menos de 3 segundos.
- **SC-006**: Tras cruzar la devolución del 17/09/2025, la cuenta de AgroNacion deja de tener movimientos asignados a su contacto sin resumen por el débito/devolución de $966.654,20.
- **SC-011**: En cualquier fecha elegida, para cada tarjeta, el saldo exigible más el consumo aún no resumido es igual al saldo de la cuenta con una diferencia menor a $1.
- **SC-012**: El control de continuidad (k) no señala meses sin resumen en tarjetas sin actividad; con los datos de hoy señala solo las tarjetas activas con último resumen de más de 92 días (hoy Corporativa Nación, cuyo último resumen cerró el 07/01/2026), y el de moneda (l) no señala ningún resumen.
- **SC-007**: Los totales del flujo de caja real de cualquier período son idénticos antes y después de la funcionalidad.
- **SC-008**: Después de la funcionalidad, el total general de cuentas corrientes cambia exactamente en cuatro importes y en nada más: la deuda vigente que se incorpora (consumos y cargos de resúmenes no cerrados; hoy $58.336.654,56 menos), las devoluciones cruzadas (hoy $966.654,20 menos), el pago de UATRE de la billetera (+$17.185,82) y los pagos de resumen sin movimiento bancario (+$3.195,96); además, para cada tarjeta, la deuda por consumos es igual a los créditos recibidos por proveedores y organismos por esos consumos más los consumos señalados como sin proveedor.
- **SC-009**: Tras cruzar la devolución de $249.999,00 del kit Starlink con su consumo, el control deja de informar ese consumo como "sin proveedor" y los consumos sin proveedor ni cruce de la tarjeta Visa Galicia suman menos de $1.
- **SC-010**: Cada pago mensual de UATRE figura una sola vez en la cuenta de UATRE, atribuido al débito de Galicia; los dos movimientos de la billetera del mismo pago se reconocen como conducto, con efecto neto cero (hoy 30 pares por $721.599), y el saldo de la billetera coincide con el informado por Mercado Pago (hoy $0,14). Los movimientos en que la billetera paga con fondos propios acreditan a su contacto sin conciliación manual.

## Assumptions

- Los cargos del resumen que no tienen fecha de consumo (intereses, impuestos, gastos, percepciones, ajustes) se registran en la fecha de cierre; la fecha de vencimiento se muestra como dato informativo.
- La asociación tarjeta→contacto se carga una sola vez desde los datos actuales y cualquier cambio posterior se hace por script con backup; no hay pantalla para editarla.
- Todas las tarjetas operan en pesos; el soporte de resúmenes en dólares queda fuera de alcance.
- La asociación tarjeta→contacto sigue la correspondencia actual por nombre (AgroNacion 373, Corporativa Nación 503, Mastercard BNA 372, Visa Galicia 532, Galicia Rural 533) y se registra de forma explícita.
- Los 22 pagos de AgroNacion de septiembre de 2010 a junio de 2012 (21 del Banco Nación, "PM/TOT. RES. AGRONACION", $23.575,00, y 1 en efectivo del 26/06/2012, $1.677,58) pertenecen a la administración anterior (Oscar y Albina); no se ligan a ningún resumen vigente y se reasignan a la cuenta de la administración anterior. El débito de Mastercard BNA del 05/06/2024 por $15.180,50 (tarjeta dada de baja, sin resúmenes desde 05/2023) fue un cobro indebido del banco: se registró como pérdida y gasto bancario, asignado al contacto del Banco Nación.
- Hoy el cronograma de cuotas del módulo de tarjetas contiene 183 cuotas, todas cobradas (la última venció el 01/12/2016): por ahora no habrá cuotas a vencer para mostrar, y la información aparecerá a medida que se carguen compras en cuotas nuevas.
- El control de integridad se consulta a pedido desde su pantalla; no envía alertas automáticas en esta versión.
- Los pagos y devoluciones se siguen cargando y vinculando desde los módulos de tarjetas y de conciliación de tesorería existentes; esta funcionalidad no agrega una nueva forma de cargar pagos.
- El cruce de una devolución con su débito es semi automático: el sistema lo sugiere y el usuario lo aprueba; no hay cruce automático sin confirmación.
- Los totales generales de cuentas corrientes son hoy el único consumidor de las cuentas de las tarjetas; no existe un reporte de cuentas a pagar separado ni un flujo de caja proyectado. Una proyección de vencimientos de resúmenes en el flujo de caja sería una funcionalidad aparte.
- Mercado Pago es una entidad financiera y recibe el mismo tratamiento que Banco Nación y Galicia (Sergio, 2026-10-06). Su uso en los pagos de UATRE es de conducto: las 31 boletas mensuales se pagan desde Galicia con un DEBIN generado en la billetera, y 30 de ellas muestran en la billetera un ingreso desde Galicia y el pago con el mismo identificador de operación; la que no empareja se informa para revisión. Otros movimientos de la billetera (por ejemplo la compra de un Chromecast por $194.158 o un pago con QR por $125.554) son uso como medio de pago.
- Fuera de alcance: recalcular o reasignar saldos de proveedores, caja de efectivo, pagos de sueldos, y la corrección de los 33 consumos o planes de cuotas históricos de Agronación (ya consolidados).
- Depende de los módulos 008 (tarjetas), 009 (conciliación de tarjetas), 026 (conciliación de tesorería), 031 (integridad de vínculos) y de la vista compartida de movimientos de cuenta corriente, que alimenta a otras pantallas y reportes y no debe alterar sus resultados.
