# Feature Specification: Reasignación de contacto en movimientos de cuenta corriente

**Feature Branch**: `022-reasignacion-contacto`

**Created**: 2026-09-25

**Status**: Draft

**Input**: User description: "Módulo 022-reasignacion-contacto: mecanismo genérico para corregir el contacto (proveedor) mal asignado en cualquier movimiento que alimenta la cuenta corriente de proveedores, sin importar su origen (transferencias bancarias, vínculos de tarjeta, compras, alquileres, impuestos, remuneraciones, valores recibidos, retenciones). Motivación real: un movimiento bancario quedó con el proveedor equivocado (texto de la transferencia decía claramente otro nombre), corregido manualmente una sola vez sin mecanismo repetible. Un escaneo de movimientos bancarios detectó ese caso real más ~35 falsos positivos por coincidencias con términos genéricos (nombres de bancos, ciudades). Requiere: alcance genérico a cualquier origen, botón de reasignación en contexto (cuenta corriente del proveedor) + pantalla de auditoría/detección, trazabilidad completa (quién/cuándo/de qué contacto a cuál), la detección automática solo sugiere candidatos y nunca escribe sola."

## Clarifications

### Session 2026-09-25

- Q: Cuando se reasigna un movimiento que en realidad viene de un vínculo de tarjeta (el proveedor sale de la Compra vinculada, no del pago en sí), ¿la corrección debe cambiar el proveedor de esa Compra en todo el sistema, o solo corregir cómo se refleja ese pago puntual en la cuenta corriente? → A: Solo corrige el reflejo en cuenta corriente (override específico de esta función); la Compra original no se modifica en ningún otro módulo.
- Q: ¿La detección automática de candidatos (Historia 2) debe cubrir en el lanzamiento inicial solo los movimientos bancarios, o también los vínculos de tarjeta? → A: Solo movimientos bancarios — el único mecanismo de detección probado (comparar nombres de contactos contra el texto libre de la descripción) solo aplica donde ese texto existe. Los vínculos de tarjeta quedan disponibles para reasignación manual (Historia 1) desde el inicio, pero fuera de la detección automática por ahora.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Corregir un movimiento puntual desde la cuenta corriente (Priority: P1) 🎯 MVP

Un usuario revisando la cuenta corriente de un proveedor nota que un movimiento (por ejemplo, una transferencia bancaria o el pago de una tarjeta) no le corresponde a ese proveedor — el texto o los datos de origen del movimiento señalan claramente a otro contacto. El usuario necesita corregir esa asignación ahí mismo, sin salir de la pantalla ni tener que operar directamente sobre la base de datos.

**Why this priority**: Es el caso que ya ocurrió en la práctica (un pago de $159.720 quedó asignado al proveedor equivocado) y la única forma de resolverlo hoy es una intervención manual fuera de la aplicación. Sin esto, cada caso nuevo requiere de nuevo intervención técnica directa sobre la base.

**Independent Test**: Sobre la cuenta corriente de un proveedor con un movimiento mal asignado, usar la acción "Reasignar", elegir el contacto correcto, confirmar, y verificar que el movimiento desaparece del saldo del proveedor original y aparece en el del proveedor correcto, con el registro de auditoría correspondiente.

**Acceptance Scenarios**:

1. **Given** un movimiento visible en la cuenta corriente de un proveedor, **When** el usuario elige "Reasignar" sobre ese movimiento y busca y selecciona el contacto correcto, **Then** el sistema pide confirmación explícita antes de aplicar el cambio.
2. **Given** que el usuario confirmó la reasignación, **When** se aplica el cambio, **Then** el movimiento deja de aparecer en la cuenta corriente del proveedor original y pasa a aparecer en la del proveedor correcto, con el saldo de ambos recalculado correctamente.
3. **Given** una reasignación ya aplicada, **When** el usuario o cualquier otro consulta el historial de ese movimiento, **Then** puede ver quién hizo el cambio, cuándo, y de qué contacto a cuál (sin que el dato quede oculto ni sea necesario consultar la base directamente).
4. **Given** un movimiento cuyo origen no tiene todavía soporte para reasignación (un origen no cubierto en el lanzamiento inicial), **When** el usuario intenta reasignarlo, **Then** el sistema explica claramente que ese tipo de movimiento no admite reasignación por ahora, sin fallar de forma confusa.

---

### User Story 2 - Detectar sistemáticamente otros movimientos mal asignados (Priority: P2)

Un usuario quiere encontrar, de forma proactiva y no solo cuando lo nota "a ojo", otros movimientos donde el contacto asignado no coincide con lo que indica el propio movimiento (por ejemplo, un texto de transferencia que menciona a otra empresa).

**Why this priority**: Ya se demostró que existen más casos de este tipo además del que se corrigió manualmente; sin una forma sistemática de buscarlos, dependen de que el usuario los note revisando cuenta por cuenta.

**Independent Test**: Ejecutar la detección sobre los movimientos bancarios existentes y verificar que devuelve una lista de candidatos a revisar (incluyendo el caso ya conocido), cada uno con el contacto actualmente asignado y el o los contactos que podrían ser el correcto, sin aplicar ningún cambio por sí sola.

**Acceptance Scenarios**:

1. **Given** el conjunto de movimientos con contacto asignado, **When** el usuario ejecuta la detección, **Then** el sistema muestra una lista de candidatos a revisar, cada uno con el contacto actual y el o los contactos sugeridos, y ningún dato se modifica todavía.
2. **Given** la lista de candidatos, **When** el usuario revisa uno y decide que sí corresponde corregirlo, **Then** puede pasar directamente a confirmar la reasignación (Historia 1) sin tener que buscar el movimiento de nuevo por otro camino.
3. **Given** la lista de candidatos, **When** el usuario revisa uno y decide que la sugerencia es un falso positivo (por ejemplo, una coincidencia con el nombre de un banco), **Then** puede descartarlo sin que vuelva a aparecer en futuras ejecuciones de la detección.
4. **Given** que la detección ya se corrió antes, **When** se vuelve a ejecutar, **Then** no repite candidatos ya revisados y descartados, para no obligar a revisar lo mismo una y otra vez.

---

### User Story 3 - Consultar el historial de reasignaciones (Priority: P3)

Un usuario (por ejemplo, al auditar la cuenta corriente de un proveedor, o al investigar un desvío) necesita ver qué movimientos fueron reasignados alguna vez, sin depender de la memoria de quién hizo el cambio.

**Why this priority**: Es una consecuencia natural de la trazabilidad exigida en la Historia 1; separado porque es una vista de consulta adicional, no bloquea el valor central (corregir y detectar).

**Independent Test**: Con al menos una reasignación ya aplicada, consultar el historial y verificar que muestra el movimiento afectado, el contacto anterior, el contacto nuevo, quién y cuándo lo hizo.

**Acceptance Scenarios**:

1. **Given** una o más reasignaciones aplicadas, **When** el usuario consulta el historial, **Then** ve cada una con movimiento afectado, contacto anterior, contacto nuevo, usuario y fecha/hora.

---

### Edge Cases

- ¿Qué pasa si el contacto correcto elegido para la reasignación es el mismo que ya tenía asignado el movimiento? El sistema debe rechazarlo o avisar que no hay cambio que aplicar, sin generar un registro de auditoría vacío.
- ¿Qué pasa si dos usuarios intentan reasignar el mismo movimiento al mismo tiempo? Debe aplicarse solo un cambio consistente; el segundo intento debe ver el estado ya actualizado, no sobrescribirlo a ciegas.
- ¿Qué pasa si el movimiento a reasignar proviene de un vínculo que en realidad resuelve el contacto desde otro registro relacionado (por ejemplo, un pago con tarjeta cuyo proveedor sale de la compra vinculada, no del propio pago)? La reasignación aplica un ajuste específico a cómo ese pago se refleja en cuentas corrientes, sin modificar la Compra original ni afectar otros módulos (Compras, stock, costos por cultivo) que dependen de ella — ver Clarifications.
- ¿Qué pasa si el movimiento a reasignar ya fue reasignado antes (una segunda corrección sobre el mismo movimiento)? Debe permitirse, y el historial debe reflejar la cadena completa de cambios, no solo el último.
- ¿Qué pasa si la detección automática (Historia 2) encuentra una coincidencia únicamente por palabras genéricas (nombre de un banco, una ciudad, términos como "S.A.")? Debe descartarse o marcarse con baja confianza para no saturar de falsos positivos la revisión humana.
- ¿Qué pasa si se intenta reasignar un movimiento cuyo origen todavía no tiene soporte en el sistema? Debe informarse claramente en vez de fallar sin explicación (ver Historia 1, escenario 4).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE permitir, desde la cuenta corriente de un proveedor, iniciar la reasignación de un movimiento visible a otro contacto.
- **FR-002**: El sistema DEBE requerir una confirmación explícita del usuario antes de aplicar cualquier reasignación (no debe aplicarse con una sola acción accidental).
- **FR-003**: El sistema DEBE aplicar la reasignación de forma que el movimiento deje de reflejarse en la cuenta corriente del contacto original y pase a reflejarse en la del contacto nuevo, con los saldos de ambos correctamente actualizados.
- **FR-004**: El sistema DEBE registrar, para cada reasignación aplicada, como mínimo: el movimiento afectado, el contacto anterior, el contacto nuevo, quién la realizó y cuándo. Este registro NUNCA se debe borrar ni sobrescribir, incluso si el movimiento se vuelve a reasignar después.
- **FR-005**: El sistema DEBE permitir consultar el historial completo de reasignaciones aplicadas (Historia 3), sin necesidad de acceso técnico directo a la base de datos.
- **FR-006**: El sistema DEBE soportar la reasignación sobre movimientos de más de un origen (como mínimo: transferencias bancarias y vínculos de pago con tarjeta), no limitarse a un único tipo de movimiento.
- **FR-007**: El sistema DEBE, si un usuario intenta reasignar un movimiento cuyo origen todavía no tiene soporte, informar claramente que ese tipo de movimiento no admite reasignación por el momento, en vez de fallar de forma genérica o silenciosa.
- **FR-008**: El sistema DEBE ofrecer una función de detección que analice los movimientos bancarios existentes (los que tienen un texto de descripción libre) y sugiera candidatos a reasignación cuando el contacto asignado no coincide con lo que indica ese texto. Los vínculos de tarjeta quedan fuera de la detección automática en el lanzamiento inicial — siguen disponibles para reasignación manual (Historia 1).
- **FR-009**: La detección del FR-008 NUNCA debe aplicar cambios por sí sola — solo debe producir sugerencias que un usuario revisa y decide, caso por caso, si confirmar (pasando a FR-001/002/003) o descartar.
- **FR-010**: El sistema DEBE permitir descartar un candidato sugerido por la detección (falso positivo) de forma que no vuelva a aparecer en ejecuciones futuras de la misma detección.
- **FR-011**: El sistema DEBE rechazar o avisar sin efecto cuando se intenta "reasignar" un movimiento al mismo contacto que ya tiene asignado.
- **FR-012**: El sistema DEBE resolver de forma consistente el caso de reasignaciones concurrentes sobre el mismo movimiento, de forma que no se pierda ni se sobrescriba silenciosamente un cambio ya aplicado.
- **FR-013**: El sistema DEBE permitir reasignar un movimiento más de una vez a lo largo del tiempo, conservando en el historial (FR-004/FR-005) cada cambio sucesivo, no solo el último.
- **FR-014**: Cuando el movimiento a reasignar proviene de un vínculo de tarjeta (el proveedor se resuelve hoy desde la Compra vinculada), la reasignación DEBE aplicarse como una corrección específica de cómo ese pago se refleja en cuentas corrientes, sin modificar el contacto de la Compra original ni de ningún otro dato que otros módulos (Compras, stock, resultado por cultivo) usen de esa misma Compra.

### Key Entities *(include if feature involves data)*

- **Movimiento reasignable**: cualquier movimiento de cuenta corriente de proveedores que hoy tiene un contacto asignado y puede necesitar corrección — incluye movimientos bancarios y vínculos de pago con tarjeta en el lanzamiento inicial (FR-006), con la posibilidad de sumar otros orígenes más adelante.
- **Reasignación**: el registro de un cambio de contacto sobre un movimiento — contacto anterior, contacto nuevo, quién y cuándo, y a qué movimiento corresponde. Es el historial permanente e inmutable de correcciones (FR-004).
- **Candidato de detección**: una sugerencia generada automáticamente (FR-008) de que un movimiento podría estar mal asignado, con el contacto actual y el o los contactos que podrían ser el correcto; tiene un estado (pendiente de revisión, confirmado como reasignación, o descartado como falso positivo).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un usuario puede corregir un movimiento mal asignado desde que lo detecta hasta que el saldo de ambos proveedores queda correcto, en menos de 2 minutos, sin intervención técnica directa sobre la base de datos.
- **SC-002**: El 100% de las reasignaciones aplicadas quedan con un registro consultable de quién, cuándo, y de qué contacto a cuál — verificable en cualquier auditoría posterior.
- **SC-003**: La función de detección, ejecutada sobre el conjunto real de movimientos bancarios, encuentra el caso ya conocido (transferencia mal asignada) sin necesidad de que el usuario lo busque manualmente.
- **SC-004**: Al menos el 80% de los candidatos descartados por el usuario en una ejecución de la detección no vuelven a aparecer en ejecuciones posteriores.

## Assumptions

- El lanzamiento inicial (FR-006) cubre como mínimo movimientos bancarios (transferencias) y vínculos de pago con tarjeta, por ser los orígenes donde ya se detectaron casos reales de mala asignación; sumar el resto de los orígenes existentes (compras, alquileres, impuestos, remuneraciones, valores recibidos, retenciones) puede hacerse de forma incremental sin bloquear el lanzamiento inicial.
- "Reasignar" corrige el contacto de un movimiento ya existente; no crea, elimina ni modifica ningún otro dato del movimiento (importe, fecha, documento) — sólo a quién corresponde.
- La búsqueda de contacto correcto al reasignar reutiliza el mismo mecanismo de búsqueda de contactos ya existente en otras partes del sistema (por nombre/razón social).
- La detección (Historia 2) es una herramienta de apoyo periódica, no un proceso en tiempo real — puede ejecutarse bajo demanda por el usuario.
- Cualquier usuario autenticado con permisos de escritura puede reasignar y descartar candidatos, siguiendo el mismo criterio de roles ya usado en el resto del sistema (sin un rol especial adicional para esta función).
- Se opera sobre la base de datos de producción; toda reasignación real que se aplique durante el desarrollo/validación de esta función requiere el mismo resguardo (respaldo previo) ya usado en features anteriores.
