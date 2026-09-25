# Feature Specification: Cuentas corrientes de socios/directores y condominio

**Feature Branch**: `021-cuentas-socios`

**Created**: 2026-09-26

**Status**: Draft

**Input**: User description: "Módulo 019-cajas: cuentas corrientes de socios/directores y condominio. Retomando decisiones de diseño ya tomadas con el equipo de especialistas (2026-09-24), sin spec formal todavía. Catálogo cerrado de 4 socios (Sergio, Lucy, Cond LSC, Ceci) en una tabla `Socios`. Cuando un gasto o ingreso real (ej. una 'Compra particular' con tarjeta, o cualquier otro movimiento) se marca como 'pertenencia = socio X' en vez de la empresa, el sistema debe reflejar automáticamente un movimiento de deuda/crédito en la cuenta corriente de ese socio (tabla `MovimientosCuentaSocio`), sin que la empresa quede con una deuda falsa hacia el proveedor original ni un gasto que no le corresponde. Cada reflejo automático debe quedar registrado en una tabla de auditoría dedicada (`AuditoriaReflejoSocio`, no el patrón liviano de imputación usado en otras features) — quién, cuándo, de qué movimiento se originó. El reflejo debe ser reversible en un solo paso (deshacer sin dejar rastros duplicados), sin necesidad de notificación adicional al usuario. Los socios deben tener una pantalla de cuenta corriente propia (saldo + movimientos + origen, similar en espíritu a la feature 004 de cuentas corrientes de proveedores, pero para este catálogo cerrado de socios) donde también se puedan registrar compensaciones/devoluciones manuales cuando el socio le paga a la empresa. La cartera de cheques/préstamos relacionada se ubica dentro de Finanzas (no Planificación) — puede ser una relación a tener en cuenta pero no es el foco central de este módulo. Requiere tanto backend y frontend, siguiendo el mismo patrón arquitectónico de features anteriores del proyecto (004, 019, 020)."

## Clarifications

### Session 2026-09-26

- Q: ¿Cómo marca el usuario un movimiento/gasto como "pertenencia = socio X" en vez de la empresa? → A: Es una acción explícita sobre un movimiento/documento ya cargado (ej. la compra particular de Cumo Store), no un campo obligatorio en cada carga nueva — el flujo normal sigue siendo "todo es de la empresa" salvo que alguien lo marque distinto. Aplica sobre compras (el caso más frecuente, vía el patrón "Compra particular" ya usado) y, según se necesite, otros orígenes de movimiento (tesorería, tarjetas).
- Q: ¿Cómo se registra que un socio le devuelve/compensa dinero a la empresa? → A: Registro manual desde la pantalla de cuenta corriente del socio (monto, fecha, medio, motivo) — no hay, por ahora, un mecanismo automático de matching contra movimientos bancarios (eso podría ser un enriquecimiento futuro, no bloquea esta feature).
- Q: ¿"Cond LSC" (condominio) tiene reglas distintas a un socio individual (ej. reparto entre varias personas)? → A: No para esta primera versión — se modela como una fila más del catálogo cerrado de `Socios`, con su propia cuenta corriente independiente; el reparto interno del condominio (si existe) es un problema de otra instancia, fuera del alcance de este sistema.
- Q: ¿Deshacer una asignación borra el movimiento de la cuenta del socio, o lo anula dejando el registro visible? → A: Anulación no destructiva, igual que 019 (`AplicacionesPago`): el movimiento queda marcado "Anulada" con motivo, visible en el historial — nunca se hace `UPDATE`/`DELETE` sobre un movimiento ya generado.
- Q: ¿La asignación de un gasto a un socio y el registro de devoluciones quedan restringidos a un rol específico (ej. Administrador)? → A: No — cualquier usuario autenticado puede hacerlo, sin restricción de rol adicional a la ya existente para entrar al sistema (016-autenticación).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Marcar un gasto como perteneciente a un socio (Priority: P1)

Un usuario administrativo, revisando una compra ya cargada (por ejemplo, un "Compra particular" hecho con la tarjeta de la empresa), necesita indicar que ese gasto le corresponde a un socio específico, para que la empresa no quede con un gasto ni una deuda que no le pertenece, y en cambio quede reflejado como un monto que ese socio le debe a la empresa.

**Why this priority**: Es el caso que motivó la feature — sin esto, un gasto personal pagado por la empresa (vía tarjeta u otro medio) queda contablemente "perdido": ni es un gasto de la empresa, ni nadie le debe nada a nadie, porque el mecanismo actual ("Compra particular") solo neteaba la factura a $0 sin generar ningún registro de a quién correspondía en realidad.

**Independent Test**: Puede probarse tomando una compra real ya marcada como "particular" (ej. Cumo Store, $29.699,10), asignándola a un socio del catálogo, y verificando que aparece un movimiento de deuda por ese importe en la cuenta corriente de ese socio.

**Acceptance Scenarios**:

1. **Given** una compra cargada y marcada como "particular" (neteada a $0 en su propio total), **When** el usuario la asigna a un socio del catálogo cerrado, **Then** el sistema genera automáticamente un movimiento de deuda en la cuenta corriente de ese socio, por el importe bruto real de la compra.
2. **Given** un movimiento ya asignado a un socio, **When** el usuario decide que la asignación fue un error, **Then** puede deshacer la asignación en un solo paso; el movimiento generado en la cuenta corriente del socio queda marcado "Anulada" (con motivo) y sigue visible en el historial — nunca se borra ni se modifica el registro original.
3. **Given** una asignación (creada o deshecha), **When** el usuario consulta el historial de auditoría, **Then** puede ver quién hizo la asignación/reversión, cuándo, y de qué movimiento/documento se originó.

---

### User Story 2 - Consultar la cuenta corriente de un socio (Priority: P1)

Un usuario administrativo necesita ver, para un socio determinado, su saldo actual y el detalle de los movimientos que lo componen (gastos personales pagados por la empresa, y las devoluciones/compensaciones que el socio hizo), para saber cuánto le debe o le sobra a cada uno en un momento dado.

**Why this priority**: Sin una pantalla de consulta, los movimientos generados por US1 no tienen forma de revisarse ni comunicarse — el valor de registrar la deuda depende de poder verla.

**Independent Test**: Puede probarse seleccionando uno de los 4 socios y verificando que el saldo mostrado coincide con la suma de sus movimientos (deudas por gastos asignados menos devoluciones registradas).

**Acceptance Scenarios**:

1. **Given** el usuario está en la pantalla de cuentas de socios, **When** selecciona uno de los 4 socios del catálogo, **Then** el sistema muestra su saldo actual y la lista de movimientos que lo componen, ordenados por fecha, cada uno con su origen (a qué compra/movimiento real corresponde, cuando aplica).
2. **Given** un socio sin movimientos, **When** el usuario lo selecciona, **Then** el sistema muestra saldo cero y un estado vacío claro.

---

### User Story 3 - Registrar una devolución/compensación de un socio (Priority: P2)

Un usuario administrativo necesita registrar que un socio le devolvió dinero a la empresa (total o parcialmente) para compensar gastos personales que la empresa pagó por él, para que el saldo de ese socio se actualice y refleje la situación real.

**Why this priority**: Completa el ciclo — sin esto, la cuenta corriente del socio solo puede crecer (deudas), nunca reflejar que se saldó, lo que le resta utilidad práctica a la feature en el mediano plazo.

**Independent Test**: Puede probarse registrando una devolución manual sobre un socio con saldo deudor, y verificando que su saldo se reduce en el monto registrado.

**Acceptance Scenarios**:

1. **Given** un socio con saldo deudor, **When** el usuario registra una devolución (monto, fecha, medio, motivo), **Then** el saldo del socio se reduce en ese monto y el movimiento aparece en su historial.
2. **Given** una devolución ya registrada, **When** el usuario la consulta, **Then** puede ver el detalle completo (medio, motivo, quién la cargó) igual que cualquier otro movimiento.

---

### Edge Cases

- ¿Qué pasa si se intenta asignar a un socio un movimiento que ya fue asignado a otro socio? El sistema no debe permitir una doble asignación silenciosa — debe rechazarla o requerir deshacer la asignación anterior primero.
- ¿Qué pasa si el movimiento original (la compra/documento) se elimina o se modifica después de haber sido asignado a un socio? El reflejo en la cuenta del socio debe quedar señalado como huérfano/inconsistente para revisión, no desaparecer silenciosamente ni quedar con un monto que ya no corresponde a nada real.
- ¿Qué pasa si se intenta registrar una devolución mayor al saldo deudor actual del socio? Se permite (puede quedar en saldo a favor del socio, análogo a un cliente con saldo acreedor en cuentas corrientes de proveedores), mostrado explícitamente como tal, no oculto.
- ¿Qué pasa con un socio sin ningún movimiento todavía? Debe aparecer igual en el listado con saldo $0, no debe estar ausente.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE mantener un catálogo cerrado de socios/directores (`Socios`): Sergio, Lucy, Cond LSC, Ceci — sin alta/baja libre desde la interfaz en esta primera versión.
- **FR-002**: El sistema DEBE permitir marcar un movimiento o documento ya cargado (inicialmente: compras marcadas como "particular") como perteneciente a uno de los socios del catálogo.
- **FR-003**: Al marcar un movimiento como perteneciente a un socio, el sistema DEBE generar automáticamente un movimiento de deuda en la cuenta corriente de ese socio, por el importe bruto real del gasto (no el importe neteado a $0 a nivel del documento original).
- **FR-004**: El sistema NO DEBE dejar, como resultado de este proceso, una deuda de la empresa hacia el proveedor original ni un gasto computado como de la empresa, para un movimiento marcado como perteneciente a un socio.
- **FR-005**: El sistema DEBE registrar cada asignación (y cada reversión de asignación) en una tabla de auditoría dedicada (`AuditoriaReflejoSocio`), incluyendo quién la realizó, cuándo, y de qué movimiento/documento se originó.
- **FR-006**: El sistema DEBE permitir deshacer una asignación en un solo paso mediante anulación no destructiva (el movimiento queda marcado "Anulada" con motivo, visible en el historial — nunca `UPDATE`/`DELETE` sobre el registro), sin generar movimientos duplicados ni requerir una notificación adicional al usuario.
- **FR-007**: El sistema DEBE ofrecer una pantalla de cuenta corriente por socio, con su saldo actual y el detalle de movimientos (deudas por gastos asignados, devoluciones registradas), cada uno navegable hacia su origen cuando corresponda.
- **FR-008**: El sistema DEBE permitir registrar manualmente una devolución/compensación de un socio hacia la empresa (monto, fecha, medio, motivo), reduciendo su saldo deudor.
- **FR-009**: El sistema DEBE impedir la doble asignación de un mismo movimiento a más de un socio simultáneamente.
- **FR-010**: El sistema DEBE mostrar el saldo de un socio sin movimientos como $0, nunca omitirlo de un listado general de socios.
- **FR-011**: El sistema DEBE señalar como inconsistente (visible, nunca oculto) un movimiento de cuenta de socio cuyo documento de origen (`IdOrigen`) ya no exista — sin ocultarlo del historial ni recalcular su importe como si fuera válido.

### Key Entities *(include if feature involves data)*

- **Socio**: uno de los 4 directores/condominio del catálogo cerrado (Sergio, Lucy, Cond LSC, Ceci). Tiene una cuenta corriente propia, independiente de `Contactos` (no es un proveedor ni un cliente).
- **Movimiento de cuenta de socio**: una fila de deuda o crédito en la cuenta corriente de un socio — se origina automáticamente al asignar un gasto (deuda) o se carga manualmente al registrar una devolución (crédito). Referencia, cuando aplica, al documento/movimiento real de origen (ej. una Compra). Es inmutable una vez creado: deshacer una asignación no lo borra ni lo modifica, lo marca "Anulada" con motivo (mismo patrón que `AplicacionesPago` en 019), y el registro sigue visible en el historial.
- **Registro de auditoría de reflejo**: quién asignó o revirtió una asignación de gasto a un socio, cuándo, y sobre qué movimiento — independiente de los movimientos de cuenta en sí, para no perder el rastro aunque el movimiento se revierta.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un usuario puede asignar un gasto ya cargado a un socio y ver reflejada la deuda en la cuenta de ese socio en menos de 30 segundos, sin tocar la base de datos directamente.
- **SC-002**: El 100% de las asignaciones y reversiones quedan trazables en el historial de auditoría, sin excepción.
- **SC-003**: Deshacer una asignación nunca dejar un movimiento duplicado ni residual en la cuenta del socio — verificable revisando el saldo antes y después.
- **SC-004**: Los 4 socios del catálogo son consultables desde una única pantalla, con su saldo visible sin necesidad de entrar a cada uno individualmente.

## Assumptions

- El catálogo de socios es fijo (4 filas) para esta primera versión; agregar/quitar socios, si hace falta en el futuro, es una ampliación posterior, no bloquea esta feature.
- El origen inicial y principal de "gastos que pueden marcarse como de un socio" son las compras con el patrón "Compra particular" ya existente (tarjetas, 008/009); extender la asignación a otros orígenes de movimiento (tesorería, remuneraciones, etc.) puede hacerse incrementalmente, reusando el mismo mecanismo de reflejo/auditoría.
- No hay, en esta versión, conciliación automática entre devoluciones registradas y movimientos bancarios reales (ej. una transferencia del socio a la cuenta de la empresa) — la devolución se carga manualmente, igual que otros registros manuales del sistema (ej. Pagos efectivo).
- La cartera de cheques/préstamos relacionada a socios vive dentro de Finanzas como una feature/relación aparte; esta spec no la incluye, solo deja documentado que existe la relación conceptual.
- `WC` es la base de producción (post-corte, 2026-09-25); todo el desarrollo de esta feature sigue el mismo flujo de backup-antes-de-escribir que el resto del sistema desde el corte.
- Cualquier usuario autenticado puede asignar gastos a un socio y registrar devoluciones — no hay un rol restringido para esta acción, más allá del control de acceso general ya existente (016-autenticación).
