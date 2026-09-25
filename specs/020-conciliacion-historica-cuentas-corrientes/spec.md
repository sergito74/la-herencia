# Feature Specification: Conciliación histórica de cuentas corrientes de proveedores y ventas

**Feature Branch**: `020-conciliacion-historica-cuentas-corrientes`

**Created**: 2026-09-25

**Status**: Draft

**Input**: User description: "Conciliar las cuentas corrientes de proveedores y las cuentas de ventas: aplicar retroactivamente el backlog histórico 2015-2026 de movimientos de tesorería contra los documentos (compras y ventas) usando la lógica de aplicación de pagos/cobros de la feature 019 (FIFO), para todos los contactos, con mejor esfuerzo cuando la coincidencia no sea 100% cierta (marcando esos casos como tales); y verificar que el saldo de cuenta corriente resultante por contacto (mostrado hoy por la feature 004, solo lectura) coincide con el saldo que mostraban los formularios Access del sistema anterior, dejando un listado de diferencias y de casos aplicados con mejor esfuerzo para revisión manual."

## Clarifications

### Session 2026-09-25

- Q: ¿Para qué contactos se aplica el backlog histórico? → A: Para todos los proveedores y clientes con movimientos en el rango 2015-2026, en una sola pasada (no por piloto).
- Q: ¿Qué hacer cuando la aplicación FIFO no es 100% cierta (documento no encontrado, importes que no cierran, ambigüedad entre varios documentos candidatos)? → A: Aplicar la mejor coincidencia disponible ("mejor esfuerzo") y marcarla explícitamente como tal, en vez de dejarla sin aplicar.
- Q: ¿Cómo se obtiene el "saldo de referencia" de Access para US3? → A: No hay exportación de Access disponible ni planeada en el corto plazo. El saldo reconstruido desde el arrastre de movimientos ya existe en el sistema (`vw_MovimientosCuenta_Saldo`, la misma fuente que usa la feature 004) — no hay que construirlo de nuevo. Falta un dato de verdad externo (saldo real de cada cuenta) para validar contra eso, que se conseguirá y analizará en una etapa posterior, fuera del alcance inmediato de esta feature.
- Q: ¿Qué tolerancia usar para marcar un contacto "conciliado" en la comparación de saldos? → A: 0.5% relativo al saldo (una vez que exista el dato externo contra el cual comparar).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Aplicar retroactivamente el backlog histórico de movimientos (Priority: P1)

Un usuario administrativo necesita que los movimientos de tesorería históricos (2015-2026) que hoy figuran "sin aplicar" queden vinculados a las compras o ventas que efectivamente cancelan, para que el saldo de cuenta corriente de cada contacto refleje la realidad del negocio y no dependa de un matching aproximado por fecha/importe.

**Why this priority**: Es la base de todo lo demás — sin el histórico aplicado, ni el saldo de cuenta corriente (004) ni el flujo de caja por rubro (018/019) pueden considerarse confiables para períodos anteriores al corte de septiembre 2025.

**Independent Test**: Puede probarse ejecutando el proceso de aplicación histórica sobre datos reales de `WC` y verificando que la cantidad de movimientos "sin aplicar" en el rango 2015-2026 se reduce, y que cada aplicación generada queda registrada en `AplicacionesPago` (misma tabla que usa la 019) con su motivo/origen.

**Acceptance Scenarios**:

1. **Given** un movimiento de tesorería histórico (pago o cobro) sin aplicaciones vigentes, **When** se ejecuta el proceso de conciliación histórica, **Then** el sistema busca documentos pendientes del mismo contacto por orden FIFO (fecha) y, si encuentra una coincidencia clara (importe exacto o combinación válida de documentos), genera la aplicación correspondiente.
2. **Given** un movimiento histórico para el cual no hay una coincidencia exacta pero sí una combinación razonable de documentos candidatos, **When** se ejecuta el proceso, **Then** el sistema aplica la mejor coincidencia disponible y la marca explícitamente como "aplicación de mejor esfuerzo" (distinta de una aplicación exacta).
3. **Given** un movimiento histórico para el cual no existe ningún documento candidato del contacto (ni exacto ni aproximado), **When** se ejecuta el proceso, **Then** el sistema lo deja sin aplicar y lo incluye en un listado de excepciones para revisión manual, sin bloquear el resto del proceso.
4. **Given** el proceso de conciliación histórica ya se ejecutó una vez, **When** se vuelve a ejecutar sobre el mismo rango de datos, **Then** el sistema no duplica aplicaciones ya generadas (es re-ejecutable de forma segura).

---

### User Story 2 - Revisar las aplicaciones de mejor esfuerzo y las excepciones (Priority: P1)

Un usuario administrativo necesita revisar, contacto por contacto, cuáles aplicaciones históricas se generaron con certeza y cuáles fueron "mejor esfuerzo" o quedaron sin aplicar, para poder corregir a mano los casos dudosos antes de dar por buena la conciliación.

**Why this priority**: Sin esta visibilidad, el "mejor esfuerzo" es una caja negra — el usuario no puede confiar en el resultado ni priorizar dónde revisar primero.

**Independent Test**: Puede probarse tomando un contacto con casos de mejor esfuerzo conocidos y verificando que el listado los muestra identificados como tales, con la información suficiente para decidir si están bien o hay que corregirlos (anulando la aplicación y aplicando otra, con el mecanismo ya existente de la 019).

**Acceptance Scenarios**:

1. **Given** el proceso de conciliación histórica ya corrió, **When** el usuario consulta el listado de resultados, **Then** ve, por contacto, cuántos movimientos quedaron aplicados con certeza, cuántos con mejor esfuerzo y cuántos sin aplicar (excepciones).
2. **Given** el usuario revisa un caso de mejor esfuerzo y determina que está mal aplicado, **When** anula esa aplicación, **Then** puede aplicar el movimiento a otro documento usando el mecanismo existente de aplicación manual (019), y el listado refleja el cambio.

---

### User Story 3 - Verificar el saldo de cuenta corriente contra el sistema anterior (Priority: P2)

Un usuario administrativo necesita comparar, contacto por contacto, el saldo de cuenta corriente que muestra el sistema nuevo (feature 004) después de aplicar el histórico contra el saldo que mostraban los formularios Access del sistema anterior, para confirmar que la migración y la conciliación no introdujeron diferencias.

**Why this priority**: Es la validación final de que el trabajo de conciliación (US1) produjo un resultado correcto — sin esto, no hay forma de saber si el saldo nuevo es confiable.

**Independent Test**: Puede probarse tomando una muestra de contactos con saldo conocido en Access y verificando que el sistema nuevo reporta la misma diferencia (idealmente cero) para cada uno, o la señala explícitamente si no coincide.

**Acceptance Scenarios**:

1. **Given** un contacto con saldo conocido en el sistema Access anterior, **When** el usuario ejecuta la verificación de saldos, **Then** el sistema muestra ambos saldos (nuevo y Access) y la diferencia entre ellos.
2. **Given** un contacto cuyo saldo nuevo coincide con el de Access, **When** se ejecuta la verificación, **Then** el contacto se marca como "conciliado" y no requiere revisión adicional.
3. **Given** un contacto cuyo saldo nuevo NO coincide con el de Access, **When** se ejecuta la verificación, **Then** el contacto se marca como "con diferencia" mostrando el monto de la diferencia, para que el usuario decida si se debe a aplicaciones de mejor esfuerzo pendientes de revisar, a movimientos sin aplicar, o a un problema de datos.

---

### Edge Cases

- ¿Qué pasa con un movimiento de tesorería histórico cuyo contacto no existe o está mal identificado en los datos de origen? → Se trata igual que un caso sin documentos candidatos: queda en el listado de excepciones.
- ¿Qué pasa si un mismo movimiento histórico ya tenía una aplicación cargada manualmente antes de correr este proceso (por ejemplo, alguien ya usó el botón "Aplicar a factura/venta…" de la 019)? → El proceso no debe tocar movimientos que ya tienen aplicaciones vigentes; solo procesa los que están sin aplicar.
- ¿Qué pasa con documentos (compras o ventas) que ya estaban totalmente cancelados antes del rango 2015-2026 (por ejemplo, por un movimiento anterior al inicio de los datos digitalizados)? → Quedan fuera de la búsqueda de candidatos FIFO para nuevas aplicaciones, igual que hoy.
- ¿Qué pasa si, para un mismo contacto, el saldo no coincide con Access pero todos los movimientos están aplicados (sin mejor esfuerzo ni excepciones)? → Se marca igual como "con diferencia"; la causa raíz (dato de origen, período fuera de alcance de los módulos migrados, etc.) queda para investigación manual, no la resuelve este proceso automáticamente.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE identificar todos los movimientos de tesorería (pagos y cobros) en el rango 2015-2026 que no tengan aplicaciones vigentes, para todos los contactos con movimientos en ese rango.
- **FR-002**: El sistema DEBE reutilizar la lógica de aplicación FIFO existente (feature 019) para buscar documentos pendientes (compras u órdenes de venta, según corresponda) del mismo contacto, ordenados por fecha.
- **FR-003**: Cuando exista una coincidencia exacta de importe (o combinación exacta de documentos) para un movimiento histórico, el sistema DEBE generar la aplicación automáticamente, registrada en la misma tabla que usan las aplicaciones manuales (`AplicacionesPago`), de forma indistinguible en su estructura de una aplicación manual salvo por el campo que identifica su origen (proceso automático vs. manual).
- **FR-004**: Cuando no exista coincidencia exacta pero sí una combinación razonable de documentos candidatos, el sistema DEBE generar la aplicación de todos modos ("mejor esfuerzo") y marcarla explícitamente como tal, de forma visible y distinguible de una aplicación exacta.
- **FR-005**: Cuando no exista ningún documento candidato para un movimiento histórico, el sistema NO DEBE forzar una aplicación; DEBE dejarlo sin aplicar e incluirlo en un listado de excepciones.
- **FR-006**: El proceso de conciliación histórica DEBE ser re-ejecutable sin generar aplicaciones duplicadas ni tocar movimientos que ya tengan una aplicación vigente (manual o automática).
- **FR-007**: El sistema DEBE permitir anular una aplicación generada por el proceso histórico usando el mismo mecanismo de anulación no destructiva de la feature 019, preservando el historial.
- **FR-008**: El sistema DEBE ofrecer un listado, por contacto, de la cantidad de movimientos aplicados con certeza, aplicados con mejor esfuerzo, y sin aplicar (excepciones), dentro del rango 2015-2026.
- **FR-009**: El sistema DEBE permitir comparar, por contacto, el saldo de cuenta corriente actual (feature 004) contra un saldo de referencia registrado del sistema Access anterior, mostrando la diferencia entre ambos.
- **FR-010**: El sistema DEBE marcar cada contacto verificado como "conciliado" (diferencia igual a cero, dentro de una tolerancia a definir) o "con diferencia" (mostrando el monto), sin intentar corregir automáticamente las diferencias encontradas.
- **FR-011**: El sistema NO DEBE modificar el cálculo de saldo de cuenta corriente ni de flujo de caja existentes (features 004/018/019); el proceso histórico solo agrega aplicaciones a la tabla existente, reutilizando la lógica ya construida.

### Key Entities *(include if feature involves data)*

- **Aplicación histórica**: una fila de `AplicacionesPago` generada por este proceso en vez de por un usuario; conserva todos los atributos de una aplicación normal más un indicador de origen ("automática exacta" / "automática mejor esfuerzo") para distinguirla en los listados de revisión.
- **Excepción de conciliación**: un movimiento de tesorería histórico sin documentos candidatos, listado para revisión manual; no persiste como registro nuevo más allá del propio movimiento ya existente, se deriva calculándolo en el momento.
- **Saldo de referencia (Access)**: el saldo de cuenta corriente por contacto tal como lo mostraba el sistema anterior, usado solo como término de comparación para la verificación; su origen y forma de carga se define en el plan de implementación.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Al finalizar el proceso, menos del 5% de los movimientos de tesorería históricos (2015-2026) quedan sin ningún tipo de aplicación (ni exacta ni de mejor esfuerzo).
- **SC-002**: El usuario puede identificar, para cualquier contacto, cuántas de sus aplicaciones históricas son "mejor esfuerzo" en menos de 30 segundos, sin consultar la base de datos directamente.
- **SC-003**: Al menos el 80% de los contactos con saldo verificado contra Access quedan marcados como "conciliados" (diferencia dentro de tolerancia) sin intervención manual adicional.
- **SC-004**: Para el 100% de los contactos marcados "con diferencia", el usuario puede ver el monto exacto de la diferencia sin tener que recalcularlo a mano.
- **SC-005**: El proceso completo puede re-ejecutarse sobre los mismos datos sin generar aplicaciones duplicadas, verificado en al menos 2 corridas consecutivas.

## Assumptions

- El "saldo de referencia (Access)" se puede obtener o reconstruir contacto por contacto (por ejemplo, desde una exportación puntual de los formularios Access, o desde un cálculo equivalente sobre datos migrados); su forma concreta de carga se decide en la fase de planificación, no en esta especificación.
- "Todos los contactos" se refiere a los proveedores y clientes con movimientos de tesorería en el rango 2015-2026 en la base `WC`; contactos de otro tipo (bancos, empleados, organismos) quedan fuera de alcance salvo que tengan documentos de compra/venta asociados.
- El rango 2015-2026 cubre la totalidad de movimientos sin aplicar, independientemente de la etiqueta que les asigne 018 (`FECHA_CORTE_APLICACION = 2015-09-01`, que en la práctica distingue solo un puñado de movimientos anteriores a esa fecha como "Histórico sin aplicar" del resto, etiquetado "Pendiente de aplicar"): este proceso aplica sobre ambos grupos por igual, ya que ambos están hoy sin aplicación real.
- La revisión y corrección manual de casos de "mejor esfuerzo" o "con diferencia" es un trabajo humano posterior a esta feature; el alcance aquí es generar la aplicación y la visibilidad, no garantizar que cada caso individual sea 100% correcto.
- No se modifica ni se tocan datos de la base `LaHerencia` (protegida); todo el proceso opera sobre `WC`, igual que el resto del sistema.
