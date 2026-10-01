# Feature Specification: Integridad de vínculos entre pagos y documentos

**Feature Branch**: `031-integridad-vinculos`

**Created**: 2026-09-30

**Status**: Draft

**Input**: User description: "Integridad de vínculos (031). Toda aplicación o conciliación debe tomarse en cuenta sin importar desde qué pantalla se vinculó, evitando duplicados y doble imputación. Hoy los vínculos se guardan en cinco lugares y el Flujo de caja por Rubro (030) solo lee uno. Corregir los errores de la conciliación automática (pagos años anteriores a la factura, importes en dólares tomados como pesos), anulando sin borrar y con revisión previa del usuario. Control de integridad permanente."

## Contexto

Un pago puede quedar vinculado a sus documentos desde cinco lugares distintos del sistema:

1. Aplicaciones de pago (019), manuales o cargadas por la conciliación automática.
2. Pago de un resumen de tarjeta desde el banco.
3. Consumo de tarjeta → factura.
4. Conciliación de tesorería: cheques propios, Mercado Libre y Galicia → compra, impuesto o sueldo.
5. Backfill de boletas de impuestos (029).

Cada pantalla que muestra "qué pagó este dinero" lee solo algunos de esos lugares, así que la misma realidad se ve distinta según dónde se mire.

Auditoría del 30-09-2026 sobre la base de producción:

- **Doble imputación:** 180 facturas quedan imputadas por encima de su total al sumar todas las vías (≈ $2,4 M de exceso):
  - 137 están pagadas por banco o efectivo y además por tarjeta.
  - 21 están pagadas con un cheque propio y además aplicadas al débito de ese cheque en el banco.
  - 22 tienen consumos de tarjeta imputados por más que su total.
- **Pagos anteriores a la factura:** 1.646 de 5.389 aplicaciones banco → compra de la conciliación automática (≈ $99 M) usan un movimiento de más de 60 días anterior a la factura; hay casos de años.
- **Monedas mezcladas:** 340 aplicaciones a facturas en dólares registran el importe en dólares contra un movimiento en pesos.

## Clarifications

### Session 2026-09-30

- Q: ¿Desde cuántos días antes de la factura un pago se considera erróneo? → A: Más de 60 días antes de la factura.
- Q: ¿Qué vínculo vale cuando una factura figura pagada por banco y por tarjeta o cheque propio? → A: El pago con tarjeta o con valor propio es una promesa de pago. Se efectiviza cuando el resumen o el cheque se debita del banco, y esa es la fecha real de pago. La cadena correcta es factura ← consumo de tarjeta / valor propio ← débito bancario. Una aplicación directa del débito bancario a la factura, además de esa cadena, es una doble imputación: se anula y la factura queda pagada una sola vez, vía la cadena.
- Q: Después de anular una aplicación errónea, ¿el sistema propone la correcta? → A: Sí. Anula y propone la aplicación correcta (misma factura con un movimiento de fecha coherente) para que Sergio la confirme.
- Q: Si una factura ya pagada vía tarjeta o valor propio tiene además una aplicación de un movimiento bancario que no es el débito de ese resumen o cheque, ¿qué se hace? → A: Se propone anularla. El movimiento bancario liberado busca, con la regla de reemplazo, la factura que realmente pagó.
- Q: ¿Cómo se confirman los ~1.800 ítems de la propuesta? → A: Agrupados por motivo (fecha incoherente, doble imputación, moneda) y por certeza. Cada grupo se confirma en bloque, destildando las excepciones. Los reemplazos ambiguos (más de un candidato) se revisan uno por uno.
- Q: Al guardar un vínculo que deja la factura o el movimiento por encima de su total, ¿el sistema avisa o bloquea? → A: Bloquea si el exceso supera el 2%. Dentro del 2% advierte y deja seguir.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver cada pago con todos sus vínculos, una sola vez (Priority: P1)

Sergio vincula pagos a facturas desde varias pantallas: aplicaciones de pago, conciliación de tarjetas y conciliación de tesorería. Quiere que el Flujo de caja por Rubro, las cuentas corrientes y el saldo pendiente de cada factura reflejen todos esos vínculos, sin importar desde dónde los cargó, y que ninguna factura se cuente dos veces.

**Why this priority**: sin esto, "Pendiente de aplicar" queda inflado con dinero que ya está vinculado (por ejemplo, los $31 M de pagos de resúmenes de tarjeta). Además, el trabajo de conciliar en una pantalla no se ve en las otras.

**Independent Test**: se toma un pago de resumen de tarjeta cuyo resumen tiene consumos imputados a facturas. En el Flujo por Rubro, ese pago debe repartirse entre los rubros de esas facturas y no caer en "Pendiente de aplicar".

**Acceptance Scenarios**:

1. **Given** un débito bancario "Pago Visa" vinculado a un resumen cuyos consumos están imputados a facturas, **When** se abre el Flujo por Rubro, **Then** el importe se reparte entre los rubros de esas facturas en proporción a lo imputado. La parte del resumen sin imputar queda en "Pendiente de aplicar".
2. **Given** un cheque propio conciliado con una factura y luego debitado en el banco, **When** se consulta el débito, **Then** el débito hereda la factura del cheque y la factura figura pagada una sola vez.
3. **Given** una factura vinculada desde dos vías que representan el mismo pago, **When** se consulta su saldo pendiente (al aplicar o conciliar), **Then** el pago se descuenta una sola vez.
4. **Given** un vínculo cargado desde la conciliación de tesorería a un impuesto o a un sueldo, **When** se abre el Flujo por Rubro, **Then** ese dinero aparece en el rubro del impuesto o del sueldo.

---

### User Story 2 - Revisar y corregir las aplicaciones automáticas erróneas (Priority: P1)

La conciliación automática cargó aplicaciones que no pueden ser correctas: pagos hechos años antes que la factura y facturas en dólares con el importe en dólares puesto contra movimientos en pesos. Sergio quiere ver la lista de esas aplicaciones con el motivo de cada una, revisarla y confirmar su corrección. Nada debe borrarse: las aplicaciones erróneas se anulan y queda el registro.

**Why this priority**: son ≈ $99 M mal atribuidos. Distorsionan el flujo, las cuentas corrientes y los saldos de facturas.

**Independent Test**: se genera la propuesta de corrección, se confirma un lote y se verifica tres cosas: que las aplicaciones quedaron anuladas con motivo, que se tomó un backup verificado antes, y que el lote puede revertirse.

**Acceptance Scenarios**:

1. **Given** aplicaciones cuyo movimiento es anterior a la factura por más del margen permitido, **When** Sergio abre la revisión, **Then** las ve listadas con proveedor, factura, fecha de factura, fecha e importe del movimiento, y el motivo.
2. **Given** una aplicación a una factura en dólares registrada en dólares contra un movimiento en pesos, **When** se corrige, **Then** el importe aplicado queda expresado en la moneda del movimiento (pesificado con el tipo de cambio de la factura), sin cambiar a qué factura apunta.
3. **Given** una propuesta revisada, **When** Sergio confirma, **Then** se toma primero un backup verificado de la base. Si el backup falla, no se escribe nada.
4. **Given** un lote de corrección aplicado, **When** Sergio lo revierte, **Then** las aplicaciones anuladas por ese lote vuelven a quedar vigentes.
5. **Given** aplicaciones hechas a mano por Sergio, **When** se genera la propuesta, **Then** esas aplicaciones nunca se incluyen.

---

### User Story 3 - Control de integridad permanente (Priority: P2)

Sergio quiere un control que pueda consultar en cualquier momento y que le avise cuando algo queda mal. Ese "algo" es:

- una factura imputada por encima de su total;
- un movimiento aplicado por encima de su importe;
- el mismo pago contado por dos vías;
- una aplicación con el pago muy anterior a la factura;
- una aplicación con monedas mezcladas.

**Why this priority**: evita que el problema vuelva a crecer sin que nadie lo note, pero no bloquea el uso de lo anterior.

**Independent Test**: se provoca una doble imputación en un caso de prueba y se verifica que el control la informa, con un enlace al documento.

**Acceptance Scenarios**:

1. **Given** la base sin inconsistencias, **When** se abre el control, **Then** muestra cero en cada categoría.
2. **Given** una factura imputada por encima de su total, **When** se abre el control, **Then** figura con el total, lo imputado por cada vía y el exceso.
3. **Given** un intento de cargar un vínculo que dejaría una factura por encima de su total, **When** se guarda desde cualquier pantalla, **Then** el sistema lo impide si el exceso supera el 2%, o lo advierte y deja confirmar si está dentro del 2%.

### Edge Cases

- **Factura en dólares pagada en pesos:** se compara pesificada con el tipo de cambio de la factura, con la tolerancia del 2% ya usada en conciliación.
- **Anticipos legítimos:** un pago hasta 60 días anterior a la factura se acepta como anticipo. Más de 60 días antes se marca como erróneo.
- **Doble imputación entre vías:** si una factura está pagada con tarjeta o valor propio y además tiene una aplicación directa del débito bancario, la aplicación directa se anula. La factura queda pagada una sola vez, vía la cadena factura ← consumo / valor ← débito.
- **Fecha real de pago:** para el flujo de caja, la fecha del pago con tarjeta o valor propio es la del débito bancario, no la del consumo ni la de entrega del cheque.
- **Consumo o cheque todavía no debitado:** la factura figura pagada en su cuenta corriente, pero el dinero todavía no salió del banco, así que no aparece en el flujo.
- **Resumen de tarjeta parcialmente imputado:** la parte sin imputar queda en "Pendiente de aplicar", no se reparte.
- **Pago de resumen menor o mayor que el total del resumen** (pagos parciales o varios pagos para un mismo resumen): se reparte en proporción.
- **Aplicaciones anuladas:** nunca cuentan en ninguna vía.
- **Aplicaciones anuladas por erróneas:** el sistema propone la aplicación correcta, con la misma factura y un movimiento del mismo proveedor, de importe compatible y fecha coherente, no usado por otra aplicación. Si no encuentra candidato, el dinero queda en "Pendiente de aplicar". Una propuesta nunca se aplica sin confirmación.
- **Débitos anulados por doble imputación:** el débito del resumen o del cheque no queda pendiente. Hereda los documentos de su resumen o cheque, siempre que el débito esté vinculado a ellos.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST ofrecer una única fuente de vínculos pago → documento que combine las cinco vías existentes. El Flujo por Rubro y el saldo pendiente de cada factura (lo que se muestra al aplicar y conciliar) MUST leer de esa fuente. El saldo total por contacto de cuentas corrientes se calcula con los pagos del circuito heredado y queda fuera de alcance.
- **FR-017**: La fuente MUST distinguir dos niveles:
  - **Nivel documento** (cuánto tiene pagado una factura): cuenta los consumos de tarjeta imputados y los cheques conciliados aunque todavía no se hayan debitado.
  - **Nivel movimiento** (qué documentos paga cada movimiento de dinero, lo que usa el flujo): cuenta solo lo efectivamente debitado.
- **FR-002**: Un pago de resumen de tarjeta MUST repartirse entre las facturas imputadas a los consumos de ese resumen, en proporción a lo imputado. Lo no imputado MUST quedar como pendiente.
- **FR-003**: El débito bancario de un cheque propio MUST heredar los documentos vinculados a ese cheque.
- **FR-004**: Una factura MUST NOT contarse como pagada dos veces por el mismo dinero, aunque figure vinculada desde dos vías.
- **FR-005**: El sistema MUST detectar las aplicaciones automáticas con el movimiento anterior a la factura por más del margen permitido, y las que tienen monedas mezcladas. Cada una MUST llevar su motivo.
- **FR-006**: Las correcciones MUST presentarse como propuesta revisable antes de aplicarse. Solo se aplican con confirmación explícita de Sergio. La propuesta MUST agruparse por motivo (fecha incoherente, doble imputación, moneda mezclada) y por certeza. Cada grupo se confirma en bloque y se pueden destildar ítems puntuales. Un reemplazo con más de un candidato posible MUST elegirse de a uno y nunca se confirma en bloque.
- **FR-007**: Ninguna corrección MUST borrar registros: las aplicaciones erróneas se anulan con motivo, usuario y fecha. Cada lote MUST poder revertirse.
- **FR-008**: Antes de escribir un lote de corrección, el sistema MUST tomar un backup verificado de la base de producción. Si el backup falla, MUST abortar sin escribir.
- **FR-009**: Las aplicaciones cargadas a mano MUST quedar fuera de toda corrección automática.
- **FR-010**: Las aplicaciones a facturas en dólares desde movimientos en pesos MUST quedar expresadas en pesos, pesificadas con el tipo de cambio de la factura.
- **FR-011**: El sistema MUST ofrecer un control de integridad consultable que liste, con el total de cada categoría y el detalle por documento:
  - las facturas imputadas por encima de su total;
  - los movimientos aplicados por encima de su importe;
  - los pagos contados por dos vías;
  - las aplicaciones con fecha incoherente;
  - las aplicaciones con monedas mezcladas.
- **FR-012**: Al guardar un vínculo desde cualquier pantalla, el sistema MUST calcular el exceso sobre el total de la factura o el importe del movimiento, contando todas las vías. Si el exceso supera el 2%, MUST impedir el guardado. Si está dentro del 2%, MUST advertir y permitir confirmar.
- **FR-014**: Una aplicación directa de un débito bancario a una factura que ya está pagada vía consumo de tarjeta o valor propio, cuyo débito es ese mismo, MUST considerarse doble imputación y proponerse para anular. Lo mismo vale para cualquier otra aplicación bancaria o de efectivo a una factura ya pagada vía esa cadena, sea o no el débito del resumen o cheque. El movimiento liberado MUST pasar por la búsqueda de reemplazo (FR-016).
- **FR-015**: En el flujo de caja, los pagos con tarjeta o valor propio MUST figurar en la fecha del débito bancario.
- **FR-016**: Por cada aplicación anulada, sea por fecha incoherente o por doble imputación, el sistema MUST proponer un reemplazo cuando exista. Si la factura quedó impaga, el reemplazo es otro movimiento para esa factura. Si el movimiento quedó libre, es otra factura impaga para ese movimiento. En ambos casos debe ser un movimiento o una factura del mismo proveedor, con fecha dentro del margen permitido, importe compatible (tolerancia 2%) y sin otra aplicación. La propuesta MUST confirmarse explícitamente.
- **FR-013**: Todas las escrituras MUST ir a la base de producción WC y nunca a la base original LaHerencia.

### Key Entities

- **Vínculo de pago**: la relación entre dinero (movimiento de banco, efectivo, cheque, tarjeta o Mercado Libre) y un documento (compra, venta, impuesto o sueldo). Tiene un importe en la moneda del movimiento y una vía de origen (la pantalla donde se cargó).
- **Lote de corrección**: un conjunto de aplicaciones propuestas para anular o pesificar. Tiene estado (propuesto, aplicado o revertido), un motivo por ítem y la referencia al backup previo.
- **Hallazgo de integridad**: una inconsistencia detectada. Tiene categoría, documento o movimiento afectado, importes por vía y exceso.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Después de la corrección, el control de integridad muestra cero facturas imputadas por encima de su total y cero pagos contados dos veces.
- **SC-002**: Los pagos de resúmenes de tarjeta con consumos imputados (hoy ≈ $31 M en "Pendiente de aplicar") se reparten por rubro en el Flujo por Rubro.
- **SC-003**: Para un pago dado, el Flujo por Rubro y el saldo pendiente de las facturas que paga muestran los mismos documentos y los mismos importes.
- **SC-004**: El 100% de las aplicaciones anuladas por un lote vuelven a quedar vigentes al revertir ese lote.
- **SC-005**: El control de integridad se consulta en menos de 10 segundos sobre la base completa.
- **SC-006**: Ninguna aplicación manual resulta modificada por el proceso de corrección.

## Assumptions

- La tolerancia de montos es la misma del 2% ya calibrada en la conciliación de documentos en dólares.
- El total de una factura es el que ya usa el sistema en cuentas corrientes (el total del comprobante, no el neto de sus renglones).
- Los traspasos internos siguen detectándose por regla (030). La tabla de traspasos manuales hoy está vacía y, si se usa, prevalece sobre la regla.
- Los cheques propios cargados en el sistema llegan hasta 2021. Los Echeq de Galicia posteriores no tienen cheque con el cual emparejarse y siguen sin heredar documentos hasta que se carguen.
- Un reemplazo solo puede usar un candidato con saldo libre ≥ importe a aplicar (±2%). Dentro de un mismo lote, cada candidato se reserva para un único reemplazo.
- No se corrigen los datos heredados de la base original, solo los vínculos cargados en WC.
- Un único usuario (Sergio), uso de escritorio.
