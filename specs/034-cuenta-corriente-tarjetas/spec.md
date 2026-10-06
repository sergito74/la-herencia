# Feature Specification: Cuenta corriente de tarjetas

**Feature Branch**: `034-cuenta-corriente-tarjetas`

**Created**: 2026-10-06

**Status**: Draft

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

Hay además movimientos bancarios asignados a contactos de tarjeta que no están vinculados a ningún resumen (22 movimientos por $990.229,20 en AgroNacion, incluido el débito de $966.654,20 del 01/09/2025 que el banco devolvió el 17/09/2025, y 1 por $15.180,50 en Mastercard BNA), y la devolución de ese débito figura **sin contacto**.

## Clarifications

### Session 2026-10-06

- Q: ¿En qué fecha se registra la deuda con la tarjeta? → A: En la fecha del consumo, que es cuando la tarjeta realmente procesó la operación. Los cargos propios del resumen (sin fecha de consumo) van en la fecha de cierre.
- Q: ¿Cómo se cruzan las devoluciones con su débito? → A: De forma semi automática: el sistema sugiere el cruce y el usuario da el visto bueno.
- Q: ¿Cómo se tratan los resúmenes de saldo inicial de una administración anterior? → A: Como apertura informativa, sin afectar el saldo ni generar pendientes.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Saber cuánto se le debe a cada tarjeta (Priority: P1)

Sergio abre la cuenta corriente de una tarjeta y ve, en orden cronológico, cada consumo como deuda en la fecha en que la tarjeta lo procesó, los cargos propios de cada resumen (intereses, impuestos, gastos) como deuda en la fecha de cierre, y cada pago bancario como crédito, con el saldo acumulado. El saldo final es lo que hoy se le debe a esa entidad. Puede elegir un período y exportar el resultado.

**Why this priority**: es el requisito central: controlar lo que se debe a cada entidad. Sin la deuda del resumen la cuenta no sirve.

**Independent Test**: se prueba con una sola tarjeta (por ejemplo Visa Galicia): el saldo final coincide con el pendiente neto que ya informa el módulo de tarjetas y cada fila se puede rastrear a su resumen o a su movimiento bancario.

**Acceptance Scenarios**:

1. **Given** una tarjeta con resúmenes y pagos cargados, **When** se abre su cuenta corriente, **Then** cada consumo aparece como deuda en su fecha de consumo, los cargos del resumen aparecen como deuda en la fecha de cierre, los consumos negativos (devoluciones o notas de crédito del comercio) aparecen como crédito en su fecha, y cada pago aparece como crédito, con saldo acumulado en orden de fecha.
   - Además, **Given** un resumen cualquiera, **When** se lo agrupa, **Then** la suma de sus consumos y cargos coincide con el total del resumen del módulo de tarjetas.
2. **Given** la cuenta de AgroNacion, **When** se consulta el saldo, **Then** los resúmenes marcados como saldo inicial de una administración anterior no generan deuda ni pendiente, y el saldo final coincide con el pendiente neto del módulo de tarjetas ($0).
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

### User Story 5 - Navegar de la cuenta al detalle (Priority: P3)

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
- Tarjeta inactiva (Mastercard BNA): su historial se sigue pudiendo consultar.
- Resúmenes marcados como saldo inicial (AgroNacion 571 a 578): son informativos; si recibieran pagos, el control lo informa.
- Tarjeta sin contacto asociado o con más de un contacto: el control lo informa y la tarjeta no se muestra con un saldo engañoso.
- Pago sin movimiento bancario de origen (hay uno de $3.195,96 con origen "Crédito banco"): se muestra con su origen y el control lo señala.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: La cuenta corriente de cada tarjeta MUST registrar cada consumo como deuda en la fecha del consumo (la fecha real en que la tarjeta procesó la operación) y los cargos propios de cada resumen (impuestos, gastos, intereses, percepciones, ajustes) como deuda en la fecha de cierre del resumen; los consumos negativos MUST registrarse como crédito en su fecha. La suma de lo registrado por cada resumen MUST coincidir con el total del resumen que informa el módulo de tarjetas (consumos más cargos, menos las compensaciones de saldos a favor entre resúmenes de la misma tarjeta).
- **FR-002**: La cuenta corriente de cada tarjeta MUST incluir cada pago bancario de un resumen como crédito, por el importe asignado a cada resumen, sin duplicar el mismo movimiento.
- **FR-003**: Una devolución bancaria de un débito de resumen MUST poder cruzarse con su débito y quedar registrada en la cuenta de la tarjeta como contrapartida (deuda), sin movimientos huérfanos sin contacto. El sistema MUST sugerir el cruce (mismo importe, tarjeta compatible y fechas cercanas, ordenando las candidatas por probabilidad) y el usuario MUST dar el visto bueno antes de que se aplique; nunca se cruza sin confirmación.
- **FR-004**: Los resúmenes marcados como saldo inicial de una administración anterior (estado "Cerrado") MUST NOT generar deuda ni pendiente en la cuenta; se muestran como apertura informativa (sus consumos y cargos no se registran como deuda).
- **FR-005**: Los saldos de todos los contactos que no son tarjetas MUST permanecer idénticos a los actuales; los proveedores MUST seguir acreditados una sola vez por los vínculos consumo→documento.
- **FR-006**: Cada tarjeta MUST tener asociado de forma explícita y única el contacto de su cuenta; el sistema MUST informar cualquier tarjeta sin contacto asociado o con más de uno.
- **FR-007**: Cada fila de la cuenta MUST indicar su origen (resumen o pago), su documento o movimiento, fecha, deuda, crédito y saldo acumulado, y MUST poder rastrearse a su registro de origen.
- **FR-008**: La pantalla de la cuenta MUST permitir elegir la tarjeta, filtrar por período (el saldo inicial refleja todo lo anterior) y exportar las filas con sus saldos.
- **FR-009**: El saldo final de cada tarjeta MUST coincidir (diferencia menor a $1) con el pendiente neto que informa el módulo de tarjetas para la misma fecha.
- **FR-010**: El control de integridad MUST detectar y listar: (a) pagos de resúmenes asignados a un proveedor; (b) movimientos bancarios asignados a una tarjeta sin resumen vinculado; (c) pagos de resumen sin movimiento bancario de origen o con importe distinto al movimiento; (d) resúmenes con saldo pendiente mayor a la tolerancia; (e) devoluciones sin cruzar; (f) resúmenes de saldo inicial con pagos; (g) tarjetas sin contacto asociado.
- **FR-011**: El control MUST mostrar para cada hallazgo la tarjeta, el resumen o movimiento, el importe y el motivo, y MUST permitir exportarlo.
- **FR-012**: La tolerancia de pendiente MUST ser la misma que usa el módulo de tarjetas (diferencias menores a $300 en pesos se consideran cerradas; nunca se usa un umbral en dólares).
- **FR-013**: Solo los usuarios con permiso de escritura MUST poder cruzar devoluciones y asociar contactos; la consulta y el control MUST estar disponibles para todos los roles que ya pueden ver cuentas corrientes.
- **FR-014**: Las escrituras necesarias MUST realizarse únicamente en `WC`, con backup verificado previo a cualquier cambio de estructura o carga masiva, y sin alterar `LaHerencia` ni los archivos Access.

### Key Entities

- **Entidad de tarjeta**: cada una de las cinco tarjetas con su banco, estado activo/inactivo y el contacto que representa su cuenta corriente.
- **Resumen de tarjeta**: documento mensual con consumos, cargos, fechas de cierre y vencimiento, estado (por ejemplo saldo inicial) y compensaciones; constituye la deuda con la entidad.
- **Pago de resumen**: asignación de un movimiento bancario (Banco Nación o Galicia) a un resumen por un importe; constituye el crédito.
- **Devolución de pago**: movimiento bancario que revierte un débito de resumen y se cruza con él.
- **Compensación**: saldo a favor de un resumen aplicado una sola vez a un resumen posterior de la misma tarjeta.
- **Hallazgo de control**: anomalía detectada por el control de integridad, con su tarjeta, movimiento o resumen, importe y motivo.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Para las cinco tarjetas, el saldo de su cuenta corriente coincide con el pendiente neto del módulo de tarjetas con una diferencia menor a $1 (hoy: AgroNacion $0, Corporativa Nación $0,02, Mastercard BNA $0,03, Visa Galicia $0,20, Galicia Rural $0).
- **SC-002**: El saldo de los contactos que no son tarjetas es idéntico antes y después de la funcionalidad en el 100% de los contactos comparados.
- **SC-003**: El control detecta el 100% de los casos conocidos de contexto: los 22 movimientos de AgroNacion y 1 de Mastercard BNA sin resumen vinculado, la devolución sin contacto y el pago con origen "Crédito banco".
- **SC-004**: Sergio responde "cuánto se debe hoy a cada tarjeta" consultando una sola pantalla, sin cálculo manual, y la exportación reproduce los mismos saldos.
- **SC-005**: La cuenta completa de la tarjeta con más historia (AgroNacion: 113 resúmenes y 149 pagos) se muestra en menos de 3 segundos.
- **SC-006**: Tras cruzar la devolución del 17/09/2025, la cuenta de AgroNacion deja de tener movimientos asignados a su contacto sin resumen por el débito/devolución de $966.654,20.

## Assumptions

- Los cargos del resumen que no tienen fecha de consumo (intereses, impuestos, gastos, percepciones, ajustes) se registran en la fecha de cierre; la fecha de vencimiento se muestra como dato informativo.
- Todas las tarjetas operan en pesos; el soporte de resúmenes en dólares queda fuera de alcance.
- La asociación tarjeta→contacto sigue la correspondencia actual por nombre (AgroNacion 373, Corporativa Nación 503, Mastercard BNA 372, Visa Galicia 532, Galicia Rural 533) y se registra de forma explícita.
- Los pagos y devoluciones se siguen cargando y vinculando desde los módulos de tarjetas y de conciliación de tesorería existentes; esta funcionalidad no agrega una nueva forma de cargar pagos.
- El cruce de una devolución con su débito es semi automático: el sistema lo sugiere y el usuario lo aprueba; no hay cruce automático sin confirmación.
- Fuera de alcance: recalcular o reasignar saldos de proveedores, Mercado Libre, caja de efectivo, pagos de sueldos, y la corrección de los 33 consumos o planes de cuotas históricos de Agronación (ya consolidados).
- Depende de los módulos 008 (tarjetas), 009 (conciliación de tarjetas), 026 (conciliación de tesorería), 031 (integridad de vínculos) y de la vista compartida de movimientos de cuenta corriente, que alimenta a otras pantallas y reportes y no debe alterar sus resultados.
