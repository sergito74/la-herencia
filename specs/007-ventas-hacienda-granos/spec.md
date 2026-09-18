# Feature Specification: Ventas de Hacienda (alta) y Ventas de Granos (lectura + alta)

**Feature Branch**: `007-ventas-hacienda-granos`

**Created**: 2026-09-17

**Status**: Draft

**Input**: User description: "007-ventas-hacienda-granos: continuación del roadmap tras 006-carga-compras. Alta de Ventas de Hacienda (cabecera + detalle con comprador por línea + vencimientos con importe propio + documentos relacionados + bloqueo de edición), fundamentado en inspección read-only real de `Frm Venta Hacienda` / `Subformulario Detalle Venta Feria Hacienda` / `SbFrm Vencimientos Ventas`. Ventas de Granos (lectura + alta) desde cero, fundamentado en inspección read-only real de `Frm Venta Granos` / `SbFrm Venta Granos_Ajustes` / `SbFrm Venta Granos_Deducciones`, dominio nunca antes leído ni escrito en el sistema nuevo. Reusar al máximo la infraestructura de 006 (ContactoSelect, MoneyInput, bloqueo de edición, documentos relacionados con búsqueda acotada, patrón de filtros/orden en la URL). Todo alta/edición escribe exclusivamente contra WC."

## Clarifications

### Session 2026-09-17

- Q1 (alcance): ¿este spec incluye el alta de Ventas de Granos ya, junto con Ventas de Hacienda? → **A: Sí** — ambos quedan en este mismo spec, Ventas de Hacienda como Historia 1-4 (P1/P2/P3) y Ventas de Granos como Historia 5-7 (P2), sin separar a un spec 007b.
- Q2 (completitud de datos en Granos): ¿el alta de Venta de Granos captura todos los campos reales del formulario, incluidos los de significado ambiguo? → **A: Sí** — el formulario de alta captura todos los campos reales de `Frm Venta Granos` tal cual están en Access (incluidos `Grado Operacion`, `Grado Mercaderia`, `Cantidad entregada` y `Cantidad vendida` por separado), sin recortar información del histórico aunque su semántica exacta se termine de confirmar con el uso real.
- Q3 (duplicados): ¿bloqueo duro o advertencia no bloqueante ante el mismo número de documento del mismo comprador/consignatario? → **A: Advertencia no bloqueante** — mismo criterio en Ventas de Hacienda y de Granos, nunca bloqueo duro, porque una liquidación de feria/acopio puede cobrarse en varios parciales legítimos del mismo comprador.
- Q4 (eliminación de Venta de Hacienda): ¿la eliminación entra en el alcance de este spec desde el arranque? → **A: Sí** — se declara como requisito desde el día uno (mismo mecanismo de lock que Compras), en vez de agregarse después como parche reactivo.
- Q5 (edición/eliminación de Venta de Granos): ¿mismo alcance que Hacienda (alta+edición+eliminación) o solo alta? → **A: Mismo alcance que Hacienda** — Venta de Granos también soporta edición y eliminación, reusando el mismo mecanismo de bloqueo exclusivo que Hacienda.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cargar una venta de hacienda nueva completa (Priority: P1)

Un usuario administrativo necesita registrar la liquidación de una venta de hacienda recién recibida del consignatario/feria (cabecera + líneas de categoría/comprador + vencimientos de cobro), para que quede disponible en el sistema igual que las ventas migradas del histórico, cerrando el último módulo de Ventas de Hacienda que hoy solo tiene lectura.

**Why this priority**: Es el corazón del módulo — sin alta de cabecera + al menos una línea, no hay venta que registrar. Reusa directamente la infraestructura ya probada en producción de Compras (006): bloqueo de edición, documentos relacionados (Venta de Hacienda no maneja moneda/tipo de cambio — ver FR-001 —, a diferencia de Venta de Granos, que sí).

**Independent Test**: Puede probarse completamente creando una venta con un consignatario existente, una línea con categoría/comprador/cantidad/precio, y verificando que aparece en el listado de Ventas de Hacienda (005) con los totales calculados correctamente.

**Acceptance Scenarios**:

1. **Given** el formulario de alta de venta de hacienda vacío, **When** el usuario selecciona un consignatario (vía combo de contactos), completa fecha, establecimiento, tipo de documento y número, agrega una línea con categoría, comprador, cantidad de cabezas, peso y al menos un precio unitario, y guarda, **Then** el sistema crea la venta en `WC`, calcula el subtotal, la comisión, el IVA y el importe (según la fórmula real: subtotal menos deducciones/gastos más IVA), y la venta queda visible en el listado existente de Ventas de Hacienda.
2. **Given** una línea de detalle, **When** el usuario elige un comprador distinto al de otra línea de la misma venta, **Then** el sistema permite compradores distintos por línea dentro de la misma liquidación, sin exigir un comprador único de cabecera.
3. **Given** un intento de guardar sin consignatario, sin establecimiento o sin ninguna línea cargada, **When** el usuario presiona guardar, **Then** el sistema rechaza el guardado y muestra qué falta completar, sin crear ningún registro parcial.

---

### User Story 2 - Editar una venta de hacienda existente (Priority: P2)

Un usuario necesita corregir datos de una venta ya cargada (un precio unitario mal tipeado, un comprador equivocado en una línea, agregar un vencimiento que faltaba) antes de que se procesen sus cobros.

**Why this priority**: Los errores de carga son inevitables; sin edición obliga a recurrir a la base directamente, violando la regla de escritura controlada. Depende de que exista el alta (P1).

**Independent Test**: Puede probarse editando una venta creada por la Historia 1 (cambiar un precio unitario), guardando, y verificando que los totales de cabecera se recalculan.

**Acceptance Scenarios**:

1. **Given** una venta de hacienda existente con sus líneas, **When** el usuario modifica el precio unitario o el comprador de una línea y guarda, **Then** el sistema recalcula subtotal, comisión, IVA e importe con los nuevos valores.
2. **Given** una venta existente con vencimientos ya cargados (cada uno con su propio importe), **When** el usuario agrega, quita o modifica un vencimiento y guarda, **Then** el sistema conserva los vencimientos restantes sin afectar cabecera ni líneas.
3. **Given** dos sesiones intentando editar la misma venta al mismo tiempo, **When** la segunda sesión intenta guardar mientras la primera tiene la venta abierta, **Then** el sistema bloquea la edición concurrente (mismo mecanismo de bloqueo exclusivo con expiración corta y opción de "forzar" ya usado en Compras).

---

### User Story 3 - Eliminar una venta de hacienda cargada por error (Priority: P2)

Un usuario necesita poder borrar por completo una venta que se cargó mal (duplicada, con el proveedor/consignatario equivocado, o de prueba), en vez de dejarla corrompiendo el listado o los saldos.

**Why this priority**: Mismo valor operativo que la edición (P2) — los errores de carga son inevitables y, a diferencia de un error de precio, algunos no se corrigen editando sino borrando y volviendo a cargar. Depende de que exista el alta (P1).

**Independent Test**: Puede probarse creando una venta de prueba (Historia 1), eliminándola, y verificando que desaparece del listado y que sus líneas/vencimientos/vínculos también se eliminaron sin dejar registros huérfanos.

**Acceptance Scenarios**:

1. **Given** una venta de hacienda existente sin nadie más editándola, **When** el usuario confirma la eliminación, **Then** el sistema borra la venta junto con sus líneas, vencimientos y vínculos de documentos relacionados, sin dejar registros huérfanos.
2. **Given** una venta que otra sesión tiene bloqueada en edición, **When** el usuario intenta eliminarla, **Then** el sistema rechaza la eliminación con el mismo mecanismo de bloqueo (y opción de "forzar") que ya usa la edición.

---

### User Story 4 - Vincular documentos relacionados de una venta de hacienda (Priority: P3)

Un usuario necesita relacionar manualmente una Nota de Crédito/Débito con la venta original que complementa, para referencia futura, igual que ya existe para Compras.

**Why this priority**: Mejora la trazabilidad pero no bloquea el flujo principal de carga — depende de que existan ventas ya cargadas (P1).

**Independent Test**: Puede probarse creando dos ventas del mismo consignatario con tipos de documento complementarios, vinculándolas desde el panel de "Documentos relacionados", y verificando que el vínculo persiste al reabrir cualquiera de las dos.

**Acceptance Scenarios**:

1. **Given** una venta de hacienda en edición, **When** el usuario busca por número de documento del mismo consignatario en el panel de documentos relacionados, **Then** el sistema muestra solo los resultados que coinciden con la búsqueda (no una lista automática de todo el historial del consignatario).
2. **Given** un documento ya vinculado, **When** el usuario destilda el checkbox correspondiente, **Then** el vínculo se quita sin afectar el resto de la venta.

---

### User Story 5 - Consultar el listado de Ventas de Granos (Priority: P2)

Un usuario necesita buscar y revisar las ventas de granos ya liquidadas (histórico migrado), para verificarlas sin recurrir a Access — primer paso antes de poder cargar una nueva, dado que es un dominio nunca antes leído por el sistema.

**Why this priority**: Es la base necesaria para validar que el modelo de datos de Granos (cabecera única sin tabla de líneas, con ajustes y deducciones como subformularios) se entiende correctamente antes de ofrecer el alta — reduce el riesgo de modelar mal un dominio nuevo.

**Independent Test**: Puede probarse buscando por consignatario/comprador o número de documento y verificando que los resultados reales de `Venta Granos` aparecen con sus ajustes y deducciones.

**Acceptance Scenarios**:

1. **Given** el listado de Ventas de Granos vacío por defecto, **When** el usuario aplica al menos un filtro (consignatario, número de documento, fecha, campaña), **Then** el sistema muestra las ventas de granos reales que coinciden, con su importe neto a percibir ya calculado.
2. **Given** una venta de granos en el listado, **When** el usuario abre su detalle, **Then** el sistema muestra los ajustes y deducciones asociados por separado, sin mezclarlos en una única línea.

---

### User Story 6 - Cargar una venta de granos nueva (Priority: P2)

Un usuario necesita registrar una liquidación de venta de granos nueva (entrega a acopio/exportador, con sus ajustes y deducciones), para que quede disponible en el sistema igual que las demás ventas.

**Why this priority**: Cierra el último módulo de Ventas sin escritura, pero depende de que el modelo de datos de Granos (Historia 5) ya esté validado contra el histórico real — es deliberadamente de menor prioridad que Hacienda por ser un dominio 100% nuevo.

**Independent Test**: Puede probarse creando una venta de granos con un comprador existente, cargando al menos un ajuste o dejándolo vacío, y verificando que el total a pagar coincide con la fórmula real (subtotal + IVA − retenciones − percepciones − deducciones).

**Acceptance Scenarios**:

1. **Given** el formulario de alta de venta de granos vacío, **When** el usuario selecciona comprador/consignatario, grano, cantidad, precio unitario y campaña, agrega ajustes y/o deducciones si corresponde, y guarda, **Then** el sistema crea la venta en `WC` con el importe neto a percibir calculado según la fórmula real confirmada contra el formulario Access.
2. **Given** una venta de granos con al menos una deducción cargada, **When** el usuario guarda, **Then** el importe neto a percibir refleja la resta de esa deducción sobre el total de la operación.

---

### User Story 7 - Editar y eliminar una venta de granos existente (Priority: P2)

Un usuario necesita corregir una venta de granos ya cargada (un ajuste mal tipeado, una deducción que faltaba) o eliminarla por completo si se cargó por error, con el mismo criterio que ya aplica a Venta de Hacienda.

**Why this priority**: Mismo valor y mismo mecanismo que la edición/eliminación de Hacienda (Historias 2 y 3) — el costo incremental de reusarlo para Granos es bajo una vez construido. Depende de que exista el alta (Historia 6).

**Independent Test**: Puede probarse editando una venta creada por la Historia 6 (agregar una deducción), guardando, y verificando que el importe neto a percibir se recalcula; y por separado, eliminando una venta de prueba y verificando que desaparece del listado sin dejar ajustes/deducciones huérfanos.

**Acceptance Scenarios**:

1. **Given** una venta de granos existente, **When** el usuario modifica un ajuste o deducción y guarda, **Then** el sistema recalcula el importe neto a percibir con los nuevos valores.
2. **Given** dos sesiones intentando editar la misma venta de granos al mismo tiempo, **When** la segunda intenta guardar mientras la primera la tiene abierta, **Then** el sistema bloquea la edición concurrente (mismo mecanismo que Hacienda).
3. **Given** una venta de granos existente sin nadie más editándola, **When** el usuario confirma la eliminación, **Then** el sistema borra la venta junto con sus ajustes y deducciones, sin dejar registros huérfanos.

---

### Edge Cases

- ¿Qué pasa si una venta de hacienda no tiene ninguna línea con comprador asignado (campo vacío)? El sistema debe rechazar el guardado igual que rechaza la falta de proveedor en Compras — no permitir una línea sin comprador.
- ¿Qué pasa si el usuario intenta eliminar una venta que ya tiene documentos relacionados vinculados? El sistema debe quitar los vínculos como parte de la misma transacción de eliminación, igual que ya se resolvió para Compras.
- ¿Qué pasa si dos líneas de la misma venta de hacienda tienen el mismo comprador y la misma categoría? Se permite — no hay motivo de negocio para prohibirlo (pueden ser lotes distintos del mismo comprador y categoría).
- ¿Qué pasa si un vencimiento de venta se carga con importe mayor al importe total de la venta? El sistema no valida esto (mismo criterio que Compras: no inventar validaciones que el sistema Access original no tenía).

## Requirements *(mandatory)*

### Functional Requirements

**Ventas de Hacienda (alta/edición)**

- **FR-001**: El sistema DEBE permitir crear una venta de hacienda con cabecera (consignatario, establecimiento, fecha, tipo de documento y número de documento — sin moneda ni tipo de cambio, columnas que no existen en el esquema real de `Venta Hacienda`) y al menos una línea de detalle.
- **FR-002**: El sistema DEBE permitir que cada línea de detalle tenga su propio comprador (vía selector de contactos), independiente del consignatario de cabecera.
- **FR-003**: El sistema DEBE calcular el importe de cabecera replicando la fórmula real del formulario Access (subtotal de líneas menos comisión/gastos/deducciones más IVA, con el segundo precio unitario sumado aparte al importe total).
- **FR-004**: El sistema DEBE permitir cargar múltiples vencimientos de cobro por venta, cada uno con su propia fecha e importe.
- **FR-005**: El sistema DEBE permitir editar una venta de hacienda existente (cabecera, líneas, vencimientos) reemplazando su contenido, igual que Compras (006).
- **FR-006**: El sistema DEBE bloquear la edición concurrente de una misma venta entre dos sesiones, con expiración automática del bloqueo y una opción explícita para forzar la edición si el bloqueo quedó abandonado.
- **FR-006a**: El sistema DEBE permitir eliminar por completo una venta de hacienda (cabecera, líneas, vencimientos y vínculos de documentos relacionados), sujeto al mismo bloqueo exclusivo que la edición.
- **FR-007**: El sistema DEBE permitir vincular/desvincular manualmente documentos relacionados de una venta (ej. Nota de Crédito/Débito), mediante una búsqueda explícita por número de documento del mismo consignatario — nunca una lista automática de todo el historial.
- **FR-008**: El sistema DEBE escribir toda alta/edición/eliminación de ventas de hacienda exclusivamente contra la base de trabajo (`WC`), nunca contra la base original.
- **FR-009**: El sistema DEBE reutilizar el catálogo real de categorías de hacienda ya existente (el mismo usado por el listado de solo lectura), sin introducir una lista propia de categorías.
- **FR-009a**: El sistema DEBE advertir (sin bloquear el guardado) cuando detecte el mismo número de documento para el mismo comprador/consignatario en otra venta de hacienda — nunca un bloqueo duro, porque una liquidación de feria puede cobrarse en varios parciales legítimos del mismo comprador.

**Ventas de Granos (lectura + alta)**

- **FR-010**: El sistema DEBE permitir buscar y listar ventas de granos existentes, sin mostrar ningún resultado hasta que el usuario aplique al menos un filtro.
- **FR-011**: El sistema DEBE mostrar, para cada venta de granos, sus ajustes (conceptos que suman al subtotal) y deducciones (conceptos que restan del total a pagar) por separado.
- **FR-012**: El sistema DEBE permitir crear una venta de granos nueva capturando todos los campos reales de la cabecera de `Frm Venta Granos` (incluidos los de significado ambiguo — `Grado Operacion`, `Grado Mercaderia`, `Cantidad entregada` y `Cantidad vendida` como campos separados, sin fusionarlos ni descartarlos), con ajustes y deducciones opcionales, calculando el importe neto a percibir con la fórmula real confirmada contra el formulario Access (subtotal más ajustes, IVA sobre ese subtotal, menos retenciones/percepciones/deducciones).
- **FR-012a**: El sistema DEBE advertir (sin bloquear el guardado) cuando detecte el mismo número de documento para el mismo comprador/consignatario en otra venta de granos — mismo criterio no bloqueante que Ventas de Hacienda (FR-009a).
- **FR-012b**: El sistema DEBE permitir editar una venta de granos existente (cabecera, ajustes, deducciones) reemplazando su contenido, con el mismo bloqueo de edición concurrente que Ventas de Hacienda (FR-006).
- **FR-012c**: El sistema DEBE permitir eliminar por completo una venta de granos (cabecera, ajustes y deducciones), sujeto al mismo bloqueo exclusivo que la edición.
- **FR-013**: El sistema DEBE escribir toda alta/edición/eliminación de ventas de granos exclusivamente contra la base de trabajo (`WC`), nunca contra la base original.

**Transversales**

- **FR-014**: El sistema DEBE mostrar los listados de Ventas de Hacienda y Ventas de Granos con filtros/orden/página persistidos de forma que volver desde la pantalla de una venta recupere la misma búsqueda, igual que Compras (006).
- **FR-015**: El sistema DEBE ofrecer acceso a la carga desde la navegación principal, bajo un ítem "Ventas" con sus dos módulos diferenciados.

### Key Entities *(include if feature involves data)*

- **Venta de Hacienda**: cabecera de una liquidación de feria/consignatario — fecha, consignatario, establecimiento, tipo/número de documento, conceptos de IVA/retenciones/gastos (sin moneda ni tipo de cambio, a diferencia de Compras y de Venta de Granos). Se relaciona con Contactos (consignatario) y con sus líneas de detalle.
- **Línea de Venta de Hacienda**: categoría de hacienda, comprador (independiente del consignatario), cantidad de cabezas, peso, unidad de medida, dos precios unitarios. Se relaciona con el catálogo de categorías y con Contactos (comprador).
- **Vencimiento de Venta**: fecha e importe de un cobro esperado de una venta (de hacienda o granos).
- **Venta de Granos**: registro único de una liquidación de granos — consignatario/comprador, grano, campaña, cantidad, precio, tipo de cambio, conceptos de IVA/retenciones/percepciones. A diferencia de Hacienda, no tiene tabla de líneas separada.
- **Ajuste de Venta de Granos**: concepto e importe que suma al subtotal de una venta de granos (ej. bonificaciones).
- **Deducción de Venta de Granos**: concepto, porcentaje y base de cálculo que resta del total a pagar de una venta de granos (ej. comisión, flete).
- **Documento relacionado**: vínculo manual entre dos ventas (o entre una venta y su Nota de Crédito/Débito), igual que en Compras.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un usuario puede cargar una venta de hacienda completa (cabecera + una línea) en menos de 2 minutos, sin tener que consultar Access en paralelo.
- **SC-002**: El importe calculado por el sistema para una venta de hacienda coincide exactamente con el importe que producía el formulario Access original, verificado contra al menos 5 ventas históricas reales.
- **SC-003**: El importe neto a percibir calculado por el sistema para una venta de granos coincide exactamente con el importe que producía el formulario Access original, verificado contra al menos 5 ventas históricas reales.
- **SC-004**: Ninguna escritura de este módulo llega a la base original (`LaHerencia`) — verificado con una auditoría directa en SQL Server tras cada escenario de prueba.
- **SC-005**: Dos sesiones que intentan editar la misma venta al mismo tiempo nunca sobrescriben los cambios una de la otra sin aviso explícito.

## Assumptions

- El comprador de cada línea de Venta de Hacienda es un contacto válido ya existente en el catálogo de Contactos — no se permite texto libre.
- No existe todavía ningún módulo de sanidad/trazabilidad SENASA en el sistema — este spec no introduce campos de guía de tránsito, RENSPA ni caravana, porque el formulario Access real no los tiene en el detalle de venta.
- La columna `Campaña` de Venta de Granos es texto libre (no un catálogo cerrado como en Compras) — se respeta tal cual viene del histórico, sin forzarla a un combo cerrado en esta primera versión.
- El vínculo entre `Retenciones IVA Granos` y la venta no se considera confiable (la columna real es `IdLiquidacion`, no `IdVenta`) — queda fuera del alcance de escritura de este spec; se puede mostrar como referencia de solo lectura si el vínculo se confirma en la fase de plan.
- El vínculo con Cuentas Corrientes/Tesorería sigue siendo indirecto (vía retenciones), igual que ya lo documentó el spec 005 para Ventas de Hacienda — este spec no crea un vínculo directo nuevo entre venta y cuenta corriente.
- Los campos de significado ambiguo de Venta de Granos (`Grado Operacion`, `Grado Mercaderia`, `Cantidad entregada`, `Cantidad vendida`) se capturan tal cual están en el Access real (decisión Q2) — su semántica exacta de negocio se termina de confirmar con el uso real del formulario, no se investiga más a fondo antes de implementar.
- Ventas de Hacienda y Ventas de Granos quedan en el mismo spec (decisión Q1), pero siguen siendo dos historias independientes con su propio riesgo — nada impide implementarlas en fases separadas (007a/007b) durante el plan si el trabajo de tasks lo amerita.
