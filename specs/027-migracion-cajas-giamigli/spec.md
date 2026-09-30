# Feature Specification: Migración histórica de Cajas Giamigli

**Feature Branch**: `027-migracion-cajas-giamigli`

**Created**: 2026-09-30

**Status**: Draft

**Input**: User description: "Migrar al sistema el archivo 'Cajas Giamigli.xlsx' (Documents/La Herencia/Administracion y gestion/Cuentas a pagar), que contiene el historial completo (2011-2026, ~7.000 filas) de: (1) las cuentas corrientes de los 4 socios/directores (Sergio, Lucy, Condominio LSC, Ceci) — gastos particulares pagados con fondos de la empresa y pagos que los socios hicieron de su bolsillo por cuenta de la empresa, en pesos, dólares y kg de carne (trueque); (2) la caja de efectivo de Giamigli SA (la sociedad que explota La Herencia); (3) la caja chica que administra el encargado del campo para gastos corrientes. Es información valiosa hoy solo disponible en una planilla Excel externa, descubierta al investigar por qué la cuenta corriente de un proveedor (El Luchador) no cerraba en $0: el pago real (hecho por un socio con fondos propios) y el gasto particular (una compra personal pagada con la tarjeta de la empresa) estaban documentados en esta planilla pero no en el sistema."

## Clarifications

### Session 2026-09-30

- Q: Para evitar duplicar un movimiento del Excel que ya existe en el sistema, ¿qué datos deben coincidir para considerar que es "el mismo movimiento"? → A: Fecha + proveedor + importe exactos (misma regla ya usada al confirmar a mano los casos El Luchador/GMRA/Coto/DER).
- Q: Para las 2 cajas nuevas (efectivo de Giamigli SA y caja chica del campo), ¿qué nivel de funcionalidad necesitan además de guardar el historial migrado? → A: Solo consulta de historial y saldo (solo lectura, como cuentas corrientes hoy); no hace falta poder cargar movimientos nuevos desde el sistema en esta primera versión.
- Q: Los movimientos de socios llevan saldo en pesos, Kg de carne y USD; la planilla además calcula una "Deuda Actualizada" revalorizando los saldos de Kg carne y USD a la cotización del día (Índice Novillo y Dólar BNA de un archivo externo, `Parametros financieros.xlsx`) — ¿la migración debe replicar ese motor de revalorización diaria, o alcanza con guardar los 3 saldos crudos? → A: Solo guardar los 3 saldos crudos (pesos históricos, Kg carne, USD) por ahora; el motor de revalorización a cotización del día queda fuera de alcance de esta iteración.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver el historial completo de la cuenta de cada socio en el sistema (Priority: P1)

Hoy el módulo de cuentas de socios (021) solo tiene los pocos movimientos cargados a mano durante correcciones puntuales. Sergio necesita que el sistema muestre el historial completo de cada socio (Sergio, Lucy, Condominio LSC, Ceci) tal como está en la planilla "Cajas Giamigli.xlsx", para dejar de depender del Excel y tener una única fuente de verdad.

**Why this priority**: Es el corazón del pedido — sin esto, el resto de la migración no tiene valor por sí solo. Ya se demostró con el caso "El Luchador" que sin esta información las cuentas corrientes de proveedores quedan con saldos incorrectos y sin explicación.

**Independent Test**: Se puede probar completamente cargando el historial de una sola cuenta (ej. Ceci, la más chica) y verificando que el saldo final calculado por el sistema coincide con el saldo final de la planilla para esa cuenta.

**Acceptance Scenarios**:

1. **Given** la planilla tiene un movimiento "Debe" (gasto particular del socio pagado por la empresa) con fecha, proveedor, detalle e importe, **When** se migra, **Then** el sistema registra ese movimiento en la cuenta del socio correspondiente con el mismo efecto sobre el saldo (aumenta lo que el socio debe a la empresa).
2. **Given** la planilla tiene un movimiento "Haber" (el socio pagó un gasto de la empresa con fondos propios) con fecha, proveedor, detalle e importe, **When** se migra, **Then** el sistema registra ese movimiento con el efecto contrario (disminuye lo que el socio debe, o aumenta lo que la empresa le debe a él).
3. **Given** un movimiento de la planilla ya fue cargado a mano en el sistema durante una corrección anterior (ej. los casos de El Luchador, GMRA SA, Coto y DER S.A. resueltos el 2026-09-29/30), **When** se migra el resto del historial, **Then** ese movimiento no se duplica.
4. **Given** el saldo final de una cuenta de socio en el sistema después de migrar, **When** se compara contra el saldo final de esa misma cuenta en la planilla, **Then** ambos coinciden (dentro de una tolerancia de redondeo menor a $1).

---

### User Story 2 - Revisar movimientos con dudas antes de darlos por buenos (Priority: P2)

Sergio necesita poder revisar, antes o después de la migración, los movimientos que no se pudieron interpretar con confianza (fechas faltantes, importes en blanco, proveedores no identificables, filas de la planilla que no siguen el patrón esperado), en vez de que el sistema los descarte en silencio o los cargue mal.

**Why this priority**: Una planilla de 15 años armada a mano inevitablemente tiene inconsistencias (la propia hoja de Ceci tiene filas vacías al final, por ejemplo). Migrar mal esos casos sería peor que no migrarlos, porque generaría una falsa sensación de exactitud en datos financieros.

**Independent Test**: Se puede probar corriendo la migración en modo de análisis (sin escribir nada) sobre una cuenta con casos conocidos de datos incompletos y confirmando que esos casos aparecen listados para revisión manual, no aplicados automáticamente.

**Acceptance Scenarios**:

1. **Given** una fila de la planilla sin fecha o sin importe, **When** se procesa, **Then** queda en una lista de "no migrados, requieren revisión" con el motivo, y no se inserta ningún movimiento a partir de ella.
2. **Given** una fila cuyo proveedor no coincide con ningún contacto existente en el sistema, **When** se procesa, **Then** el movimiento se migra igual (el registro de socios no depende de que el proveedor exista como contacto), pero el nombre de proveedor no reconocido queda visible para revisión posterior.

---

### User Story 3 - Ver la caja de efectivo de Giamigli SA en el sistema (Priority: P3)

Sergio necesita que el sistema muestre el historial e importe actual de la caja de efectivo de Giamigli SA (la sociedad que explota La Herencia), hoy solo visible en la planilla, incluyendo su relación con los pagos en efectivo a proveedores que el sistema ya registra.

**Why this priority**: Es información real de la operación, pero de menor urgencia que las cuentas de socios porque una parte ya está reflejada indirectamente en la tabla de pagos en efectivo existente — acá el valor es completar el cuadro, no resolver una cuenta que no cierra.

**Independent Test**: Se puede probar cargando el historial de la caja y verificando que el saldo resultante coincide con el saldo final de esa hoja en la planilla.

**Acceptance Scenarios**:

1. **Given** un movimiento de la caja de efectivo de Giamigli SA que corresponde a un pago a un proveedor que el sistema ya tiene registrado por otro medio, **When** se migra, **Then** el sistema lo identifica como el mismo movimiento (no lo duplica) y lo deja disponible para revisión si hay dudas de la correspondencia.
2. **Given** un movimiento de la caja que no tiene correspondencia con ningún registro existente, **When** se migra, **Then** se carga como movimiento nuevo de la caja.

---

### User Story 4 - Ver la caja chica del campo en el sistema (Priority: P4)

Sergio necesita que el sistema muestre el historial de la caja chica que administra el encargado del campo para gastos corrientes, hoy solo visible en la planilla.

**Why this priority**: Es la hoja más chica y la de menor impacto financiero (montos de caja chica, no de la operación general) — vale la pena migrarla, pero es la de menor urgencia relativa entre las seis hojas.

**Independent Test**: Se puede probar cargando el historial completo de esta caja (la más chica del archivo) y verificando que el saldo final coincide con el de la planilla.

**Acceptance Scenarios**:

1. **Given** el historial completo de la caja chica del campo en la planilla, **When** se migra, **Then** el sistema muestra el mismo saldo final y el mismo historial de movimientos (aportes y gastos).

---

### Edge Cases

- Una fila cuyo importe está en dólares o en Kg de carne pero no en pesos (trueque puro): se migra igual, sumando solo a los saldos de USD y/o Kg de carne del socio — no se inventa un equivalente en pesos (FR-004).
- ¿Qué pasa si dos filas de la planilla parecen ser el mismo movimiento cargado dos veces por error (mismo proveedor, fecha e importe repetidos)?
- ¿Qué pasa con las filas vacías al final de una hoja (ej. la hoja de Ceci tiene filas sin datos después del último movimiento real)? Deben ignorarse sin generar un "caso a revisar".
- ¿Qué pasa con un proveedor cuyo nombre en el sistema está anonimizado (ej. "XXXXXXXXX", ya existe como contacto así en el sistema)? Debe tratarse como cualquier otro proveedor, sin lógica especial.
- ¿Qué pasa si el saldo final calculado por el sistema no coincide con el saldo final de la planilla para una cuenta? La migración de esa cuenta debe señalarse como inconsistente en vez de darse por completa silenciosamente.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST permitir consultar el historial completo de movimientos de cada una de las 4 cuentas de socios/directores (Sergio, Lucy, Condominio LSC, Ceci) tal como figura en "Cajas Giamigli.xlsx", incluyendo fecha, proveedor/servicio, detalle, importe, forma de pago y el efecto sobre el saldo (a favor del socio o a favor de la empresa).
- **FR-002**: El sistema MUST calcular el saldo en pesos de cada cuenta de socio a partir de sus movimientos migrados con importe en pesos, y ese saldo MUST coincidir con el saldo nominal (columna "Saldo", no la "Deuda Actualizada" revalorizada) final de la hoja correspondiente en la planilla (tolerancia menor a $1 por redondeo).
- **FR-003**: El sistema MUST evitar duplicar movimientos que ya fueron cargados manualmente en el sistema antes de esta migración (los casos ya resueltos de El Luchador, GMRA SA, Coto y DER S.A.). Dos movimientos se consideran "el mismo" cuando coinciden fecha, proveedor/contacto e importe (en la moneda correspondiente).
- **FR-004**: El sistema MUST registrar, para cada movimiento migrado, sus componentes en pesos, dólares y kilogramos de carne cuando la planilla los tenga, sin perder ninguno de los tres, y MUST mantener los saldos acumulados de las tres monedas/unidades por separado (sin convertir Kg de carne o USD a un equivalente en pesos). El cálculo de una "deuda actualizada" que revalorice los saldos de Kg carne y USD a la cotización del día (Índice Novillo, Dólar BNA) queda fuera de alcance de esta iteración — ver Assumptions.
- **FR-005**: El sistema MUST dejar disponible para revisión manual, sin migrarlas automáticamente, las filas de la planilla que no tengan fecha, no tengan ningún importe cargado (ni pesos, ni dólares, ni kg de carne), o no puedan interpretarse con el mismo patrón que el resto de la hoja.
- **FR-006**: El sistema MUST ignorar silenciosamente las filas completamente vacías (sin ningún dato) dentro del rango de una hoja, sin generarlas como casos a revisar.
- **FR-007**: El sistema MUST permitir consultar el historial e importe actual de la caja de efectivo de Giamigli SA.
- **FR-008**: El sistema MUST identificar, al migrar la caja de efectivo de Giamigli SA, los movimientos que correspondan a pagos a proveedores ya registrados en el sistema por otro medio, y no migrarlos como movimientos nuevos duplicados, usando el mismo criterio de coincidencia de FR-003 (fecha + proveedor + importe).
- **FR-009**: El sistema MUST permitir consultar el historial e importe actual de la caja chica que administra el encargado del campo.
- **FR-010**: El sistema MUST mantener el criterio de solo-lectura sobre datos ya existentes de proveedores/documentos: la migración MUST agregar información nueva (movimientos de socios y cajas) sin modificar los datos ya cargados en compras, tarjetas, impuestos u otros módulos, excepto cuando la corrección puntual de un vínculo mal cargado sea el objetivo explícito (mismo criterio ya usado en los casos El Luchador/GMRA/Coto/DER).
- **FR-011**: Para la caja de efectivo de Giamigli SA y la caja chica del campo, el sistema MUST ofrecer solo consulta (historial y saldo) en esta primera versión — no es necesario poder cargar movimientos nuevos de estas cajas desde el sistema todavía.

### Key Entities *(include if feature involves data)*

- **Movimiento de cuenta de socio**: un gasto particular de un socio pagado con fondos de la empresa, o un pago de la empresa hecho por el socio con fondos propios. Tiene fecha, socio, proveedor/servicio, detalle, importe (en pesos, dólares y/o kg de carne), forma de pago, y efecto sobre el saldo del socio.
- **Caja de efectivo de Giamigli SA**: el efectivo de la sociedad que explota La Herencia. Tiene un historial de movimientos (ingresos y egresos) y un saldo.
- **Caja chica del campo**: el efectivo que administra el encargado del campo para gastos corrientes. Tiene un historial de movimientos y un saldo.
- **Caso a revisar**: una fila de la planilla original que no pudo migrarse automáticamente con confianza, con el motivo por el que quedó pendiente.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El saldo nominal en pesos de cada una de las 4 cuentas de socios calculado por el sistema coincide con el saldo final (columna "Saldo", no la "Deuda Actualizada") de la planilla, con una diferencia menor a $1 por cuenta; los saldos acumulados de Kg de carne y de USD también coinciden con los de la planilla.
- **SC-002**: El saldo de la caja de efectivo de Giamigli SA y de la caja chica del campo calculados por el sistema coinciden con los saldos finales de sus hojas en la planilla, con una diferencia menor a $1 cada una.
- **SC-003**: Cero movimientos de la planilla quedan duplicados respecto de lo ya cargado manualmente en el sistema antes de esta migración.
- **SC-004**: El 100% de las filas de la planilla con datos completos (fecha e importe) quedan migradas o explícitamente listadas como caso a revisar — ninguna se pierde en silencio.
- **SC-005**: Sergio puede responder "¿cuánto le debe la empresa a Lucy hoy?" (o a cualquier otro socio) mirando únicamente el sistema, sin abrir la planilla.

## Assumptions

- La planilla "Cajas Giamigli.xlsx" es la fuente de verdad para todo lo que ya tiene registrado; el sistema no tiene que re-derivar esos importes de otra manera, solo migrarlos.
- Los 4 socios/entidades de la planilla (Sergio, Lucy, Condominio LSC, Ceci) son exactamente los mismos 4 registros que ya existen en el módulo de cuentas de socios (021) — no hay que crear entidades nuevas ahí.
- La caja de efectivo de Giamigli SA y la caja chica del campo son entidades nuevas para el sistema — no existe hoy ningún módulo que las contemple, aunque la caja de Giamigli SA se relaciona con pagos en efectivo a proveedores que el sistema ya registra por otro lado.
- Los montos en kilogramos de carne y en dólares son la verdadera reserva de valor del negocio (protección contra inflación) — se migran y se acumulan como saldos propios, no se convierten a un equivalente en pesos inventado por el sistema.
- La revalorización diaria de esos saldos ("Deuda Actualizada" en la planilla, que multiplica el saldo de Kg carne por el Índice Novillo del día y el saldo de USD por el Dólar BNA del día, usando el archivo externo `Bancos y finanzas/Parametros financieros.xlsx`) queda fuera de alcance de esta iteración; el sistema migra y muestra los 3 saldos crudos (pesos históricos, Kg carne, USD) tal cual están en la planilla, sin recalcular su valor a la cotización de hoy. Importar `Parametros financieros.xlsx` y construir ese motor de revalorización se evalúa como una iteración futura independiente.
- Esta migración es sobre datos históricos cerrados (2011-2026 hasta la fecha de la planilla); no se espera que la planilla siga siendo la fuente de carga de movimientos nuevos una vez migrada — los movimientos nuevos se cargarán directamente en el sistema de acá en adelante.
