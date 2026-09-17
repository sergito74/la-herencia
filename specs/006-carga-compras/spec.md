# Feature Specification: Carga de Compras (alta y edición)

**Feature Branch**: `006-carga-compras`

**Created**: 2026-09-17

**Status**: Draft

**Input**: User description: "006-carga-compras: Alta y edición de Compras (cabecera + líneas + vencimientos), fundamentado en inspección read-only real de Frm Compras / SbFrm Det_Compras / Sbfrm Vencimiento Compras. Alcance: crear/editar una compra completa contra WC únicamente. Cabecera: proveedor (vía ContactoSelect, incluye tipos Proveedor/Multiple/Organismo/Empleado/Banco), fecha, tipo comprobante (A/B/C/M/X), tipo de documento (Factura/Nota de Crédito/Nota de Débito/C. Deposito Cereales), nro documento (max 15 chars), moneda (Dólares/Pesos) + tipo de cambio, ingresos brutos, conceptos no gravados, guías, comisión, financiación, gastos varios, ley de sellos, res gral 4169/96, ajusta tipo cambio. Líneas: producto/servicio (texto libre con autocompletado), cantidad, precio unitario, IVA (%), unidad, centro de costos, rubro, destino, campaña, ajuste financiero. Vencimientos: solo fecha. Cálculos: IVA cabecera = suma IVA líneas + 10.5% fijo sobre (comisión+guías+financiación+gastos varios); importe total = subtotal líneas + IVA cabecera + resto de conceptos; bloque pesificado = todo x tipo de cambio cuando moneda=Dólares. Fuera de alcance v1: motor de auto-clasificación por aprendizaje automático. Validación referencial en aplicación. Reusar patrón de 002-compras para listado/filtros."

## Clarifications

### Session 2026-09-17

- Q: Si dos usuarios abren la misma compra para editarla al mismo tiempo y ambos guardan, ¿qué debe pasar con el segundo guardado? → A: Bloquear la compra mientras alguien la edita (nadie más puede abrirla en modo edición hasta que se libere).
- Q: El motor de sugerencia de rubro basado en compras anteriores (Historia 3, escenario 3) ¿entra en el alcance de esta v1? → A: Sí — buscar líneas anteriores con el mismo texto de producto/servicio y sugerir su rubro más frecuente.
- Q: ¿Debe el sistema impedir guardar una línea con cantidad o precio unitario en cero o negativo? → A: No — permitirlo igual que el sistema Access original, que no valida esto.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cargar una compra nueva completa (Priority: P1)

Un usuario administrativo necesita registrar una compra recién recibida (factura de un proveedor) con todos sus datos fiscales, sus líneas de detalle y las fechas en las que vence el pago, para que quede disponible en el sistema igual que las compras migradas del histórico.

**Why this priority**: Es el corazón del módulo — sin alta de cabecera + al menos una línea, no hay compra que registrar. Todo lo demás (edición, vencimientos, imputación) construye sobre esto.

**Independent Test**: Puede probarse completamente creando una compra con un proveedor existente, una línea y sin vencimientos, y verificando que aparece en el listado de Compras (002) con los totales calculados correctamente.

**Acceptance Scenarios**:

1. **Given** el formulario de alta de compra vacío, **When** el usuario selecciona un proveedor (vía combo de contactos), completa fecha, tipo de comprobante, tipo de documento, número de documento y moneda, agrega una línea con producto, cantidad, precio unitario e IVA, y guarda, **Then** el sistema crea la compra en `WC`, calcula el subtotal, el IVA y el importe total de la cabecera a partir de la línea cargada, y la compra queda visible en el listado de Compras.
2. **Given** una compra en moneda "Dólares" con tipo de cambio cargado, **When** el usuario guarda la compra, **Then** el sistema calcula y muestra el bloque de importes "pesificados" (cada componente multiplicado por el tipo de cambio) además de los importes en la moneda original.
3. **Given** un intento de guardar sin haber seleccionado un proveedor o sin ninguna línea cargada, **When** el usuario presiona guardar, **Then** el sistema rechaza el guardado y muestra qué falta completar, sin crear ningún registro parcial.

---

### User Story 2 - Editar una compra existente (Priority: P2)

Un usuario necesita corregir datos de una compra ya cargada (por ejemplo, un error de tipeo en el número de documento, un precio unitario mal cargado en una línea, o agregar una línea que faltaba) antes de que se procesen sus pagos.

**Why this priority**: Los errores de carga son inevitables; sin edición, cualquier error obliga a borrar y recrear manualmente en la base, violando la regla de oro de escritura controlada.

**Independent Test**: Puede probarse editando una compra creada por la Historia 1 (cambiar un precio unitario), guardando, y verificando que los totales de cabecera se recalculan y el listado refleja el nuevo valor.

**Acceptance Scenarios**:

1. **Given** una compra existente con sus líneas, **When** el usuario modifica el precio unitario de una línea y guarda, **Then** el sistema recalcula el subtotal, el IVA y el importe total de la cabecera con el nuevo valor.
2. **Given** una compra existente, **When** el usuario agrega una nueva línea o elimina una línea existente y guarda, **Then** los totales de cabecera reflejan el conjunto de líneas final.
3. **Given** una compra existente con vencimientos ya cargados, **When** el usuario agrega o quita una fecha de vencimiento y guarda, **Then** el sistema conserva las fechas restantes sin afectar cabecera ni líneas.

---

### User Story 3 - Clasificar cada línea con Centro de Costos, Rubro, Destino y Campaña (Priority: P2)

Un usuario necesita indicar, para cada línea de una compra, a qué centro de costos, rubro contable, destino y campaña agropecuaria corresponde, para que la información esté disponible en los reportes de gestión que ya usan esos catálogos (Compras 002 ya filtra por Centro de Costos y Rubro).

**Why this priority**: Sin esta clasificación la compra queda cargada pero "huérfana" de la información de gestión que el resto del sistema (filtros de 002-compras, futuros reportes) espera — es igual de importante que el alta básica, pero depende de que la línea ya exista (P1).

**Independent Test**: Puede probarse cargando una línea, seleccionando Centro de Costos, Rubro, Destino y Campaña de listas desplegables con datos reales, guardando, y verificando que el filtro de Compras (002) por esos mismos valores encuentra la compra recién creada.

**Acceptance Scenarios**:

1. **Given** una línea en edición, **When** el usuario abre el desplegable de Rubro, **Then** ve la lista real de rubros existentes (no una lista vacía o rota) y puede seleccionar uno.
2. **Given** una línea sin Centro de Costos, Destino o Campaña seleccionados explícitamente, **When** el usuario guarda, **Then** el sistema aplica los valores por defecto históricos ("Adm. General", "General", "No Aplica" respectivamente) en vez de dejar el campo vacío, preservando el comportamiento que ya conocen los usuarios del sistema Access.
3. **Given** una línea con un producto/servicio ya usado antes en otras compras con un rubro asignado, **When** el usuario carga el mismo texto de producto/servicio, **Then** el sistema sugiere (de forma no vinculante, editable) el rubro más frecuente entre las compras anteriores con ese mismo texto — el usuario siempre puede aceptar la sugerencia o cambiarla antes de guardar.

---

### Edge Cases

- ¿Qué pasa si un usuario intenta abrir en modo edición una compra que otro usuario ya tiene abierta? El sistema debe informarle que está bloqueada y por quién, sin permitirle editar hasta que se libere.
- ¿Qué pasa si el usuario intenta guardar una compra con un número de documento repetido para el mismo proveedor? El sistema real no valida unicidad; este módulo debe advertir (sin bloquear) cuando detecta un número de documento igual para el mismo proveedor, dado que puede ser una carga duplicada por error.
- ¿Qué pasa si el usuario elige moneda "Dólares" pero no carga un tipo de cambio? El sistema debe exigir el tipo de cambio como obligatorio en ese caso (no puede pesificar sin ese dato).
- ¿Qué pasa si se borra una línea que ya tiene un vencimiento asociado con pagos registrados en Tesorería? Fuera de alcance de este módulo (los pagos se modelan en el spec 008-pagos-compras-pendientes); aquí alcanza con impedir borrar la compra completa si tiene vencimientos con pagos ya vinculados, dejando la relación real para cuando 008 exista.
- ¿Qué pasa si el proveedor seleccionado no tiene ningún dato fiscal cargado (CUIT vacío)? El alta de compra debe permitirlo igual (dato histórico: `CUIT/CUIL` es nullable en Contactos) — no bloquear la compra por eso.
- ¿Qué pasa con compras en Pesos? El bloque de importes "pesificados" no debe mostrarse o debe coincidir exactamente con los importes originales (tipo de cambio implícito 1).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE permitir crear una compra nueva seleccionando un contacto de tipo Proveedor, Multiple, Organismo, Empleado o Banco mediante una lista desplegable con búsqueda (no texto libre).
- **FR-002**: El sistema DEBE requerir, para guardar una compra, al menos: proveedor, fecha, tipo de comprobante, tipo de documento, número de documento, moneda y al menos una línea de detalle.
- **FR-003**: El sistema DEBE permitir cargar y editar, por cada línea de una compra: producto/servicio (texto libre con sugerencias basadas en compras anteriores), cantidad, precio unitario, alícuota de IVA (porcentaje), unidad de medida, centro de costos, rubro, destino y campaña.
- **FR-004**: El sistema DEBE calcular automáticamente, por línea, el subtotal (cantidad × precio unitario) y el importe de IVA (subtotal × alícuota / 100), sin que el usuario los tipee manualmente.
- **FR-004a**: El sistema NO DEBE exigir que cantidad, precio unitario o alícuota de IVA sean mayores a cero — se permiten valores en cero o negativos, igual que el sistema Access original, para no bloquear casos legítimos como correcciones o notas de crédito.
- **FR-005**: El sistema DEBE calcular el IVA total de la cabecera como la suma del IVA de todas las líneas más un 10.5% aplicado sobre la suma de Comisión, Guías, Financiación y Gastos Varios de la cabecera.
- **FR-006**: El sistema DEBE calcular el importe total de la compra como la suma del subtotal de líneas, el IVA de cabecera, Ingresos Brutos, Conceptos no gravados, Guías, Comisión, Financiación, Gastos Varios, Ley de Sellos y Res. Gral. 4169/96.
- **FR-007**: Cuando la moneda de la compra sea "Dólares", el sistema DEBE calcular y mostrar, además de los importes originales, el equivalente de cada importe multiplicado por el tipo de cambio cargado ("importes pesificados"). El tipo de cambio es obligatorio en ese caso.
- **FR-008**: El sistema DEBE permitir cargar, para cada compra, una o más fechas de vencimiento de pago, sin exigir que tengan un monto asociado (el sistema real no desglosa monto por vencimiento).
- **FR-009**: El sistema DEBE permitir editar una compra existente (cabecera, líneas y vencimientos) y recalcular los totales derivados cada vez que cambian los datos que los originan.
- **FR-009a**: El sistema DEBE bloquear una compra para edición exclusiva mientras un usuario la tiene abierta en modo edición, impidiendo que otro usuario la abra en modo edición hasta que se libere (al guardar, cancelar, o expirar el bloqueo por inactividad).
- **FR-010**: El sistema DEBE permitir eliminar líneas y vencimientos individuales de una compra existente, y agregar líneas o vencimientos nuevos.
- **FR-011**: El sistema DEBE aplicar, cuando el usuario deja Centro de Costos, Destino o Campaña sin seleccionar en una línea, los valores por defecto "Adm. General", "General" y "No Aplica" respectivamente (comportamiento heredado del sistema Access).
- **FR-012**: El sistema DEBE ofrecer los catálogos de Centro de Costos, Rubro, Destino, Unidad de Medida y Campaña como listas desplegables con datos reales (no listas vacías ni texto libre) para cada línea.
- **FR-012a**: El sistema DEBE sugerir, al cargar el texto de producto/servicio de una línea, el rubro más frecuente entre las líneas anteriores con el mismo texto (si existen), sin aplicarlo automáticamente: el usuario decide si acepta la sugerencia o elige otro rubro.
- **FR-013**: El sistema DEBE validar en la aplicación (no depende de restricciones de la base de datos) que el proveedor, el centro de costos, el rubro y el destino elegidos existan realmente en sus catálogos respectivos antes de guardar.
- **FR-014**: El sistema DEBE advertir (sin bloquear el guardado) cuando el número de documento cargado ya existe para el mismo proveedor, dado que no hay restricción de unicidad en el sistema original y puede tratarse de una carga duplicada.
- **FR-015**: El sistema DEBE escribir toda alta y edición de compras exclusivamente contra la base de datos `WC`, nunca contra `LaHerencia`, reutilizando el mecanismo de protección existente (`execute_write`/`execute_insert_returning_id`).
- **FR-016**: El sistema NO DEBE reescribir masivamente el historial de compras/líneas anteriores como efecto secundario de clasificar una línea nueva (a diferencia del sistema Access original, que ofrecía reescribir retroactivamente el centro de costos de líneas pasadas al aprender un nuevo mapeo palabra→centro de costos).
- **FR-017**: El listado y los filtros de Compras ya existentes (spec 002) DEBEN seguir funcionando sin cambios sobre las compras creadas por este módulo nuevo, dado que ambos operan sobre las mismas tablas.

### Key Entities *(include if feature involves data)*

- **Compra**: Registro de cabecera de una operación de compra. Incluye proveedor (contacto), fecha, tipo de comprobante fiscal, tipo de documento, número de documento, moneda, tipo de cambio, y los distintos conceptos monetarios adicionales (Ingresos Brutos, Conceptos no gravados, Guías, Comisión, Financiación, Gastos Varios, Ley de Sellos, Res. Gral. 4169/96). Se relaciona con cero o más Líneas de Detalle y cero o más Vencimientos.
- **Línea de Detalle**: Un ítem comprado dentro de una Compra: producto/servicio, cantidad, precio unitario, alícuota de IVA, unidad, y su clasificación de gestión (Centro de Costos, Rubro, Destino, Campaña).
- **Vencimiento**: Una fecha en la que se espera pagar (total o parcialmente) una Compra. No lleva monto propio en el sistema actual.
- **Contacto (Proveedor)**: Reutiliza la entidad Contacto ya existente (módulo de Contactos); una Compra referencia un contacto de tipo Proveedor, Multiple, Organismo, Empleado o Banco.
- **Catálogos de clasificación**: Centro de Costos, Rubro, Destino, Unidad de Medida y Campaña — catálogos existentes que este módulo consume mediante listas desplegables, sin modificar su estructura.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un usuario puede cargar una compra completa (cabecera + al menos una línea) en menos de 3 minutos usando únicamente listas desplegables para todos los campos que tienen opciones fijas o catálogos existentes.
- **SC-002**: El 100% de las compras cargadas por este módulo aparecen correctamente en el listado y los filtros existentes de Compras (spec 002) sin ninguna adaptación adicional de esos filtros.
- **SC-003**: Los importes totales calculados (subtotal, IVA, importe total, pesificado) coinciden exactamente con los que produciría el formulario Access original para los mismos datos de entrada, verificado contra al menos 5 compras históricas reales recalculadas manualmente.
- **SC-004**: Cero compras, líneas o vencimientos quedan escritos en la base de datos `LaHerencia` original como resultado de usar este módulo (verificable en cualquier momento comparando ambas bases).
- **SC-005**: Un usuario puede corregir un error en una compra ya cargada (dato de cabecera o de una línea) sin necesitar soporte técnico ni acceso directo a la base de datos.

## Assumptions

- El backend de esta feature reutiliza el mismo mecanismo de escritura protegida (`WC`-only) ya implementado para Arrendamientos y Contactos; no se introduce un mecanismo nuevo.
- El motor de auto-clasificación de Rubro/Centro de Costos por aprendizaje de palabras del sistema Access original (alias normalizados, reglas LIKE con prioridad, frecuencia de palabras, reescritura retroactiva del histórico) queda fuera de alcance de la v1. En su lugar, v1 incluye una versión simplificada (FR-012a): sugerir el rubro más frecuente entre líneas anteriores con el mismo texto exacto de producto/servicio, sin normalización de texto ni aprendizaje por palabras sueltas, y sin escritura automática sobre datos históricos (FR-016). El matching por alias/reglas/palabras más sofisticado del sistema original puede evaluarse en una iteración futura si el usuario lo pide explícitamente.
- Las columnas `Fecha Vto` (en Compras) e `IdOperacion` (en Compras), e `IdFormulado` (en Det_Compras), detectadas en el esquema real pero sin uso visible en los formularios Access inspeccionados, se consideran fuera de alcance de esta v1 hasta que se confirme su propósito real; no se exponen en el alta/edición.
- La corrección del combo de Rubro roto en el Access original (RowSource inválido) se resuelve de forma natural al construir el combo nuevo correctamente contra el catálogo real de Rubros.
- No existe requerimiento de adjuntar el documento original (factura escaneada); el campo "Documento Original" se trata como texto libre/observaciones, igual que en el sistema actual.
- La validación de "advertencia por número de documento duplicado" (FR-014) es informativa: el usuario puede confirmar y guardar igual si sabe que es intencional (por ejemplo, notas de crédito relacionadas a la misma factura).
