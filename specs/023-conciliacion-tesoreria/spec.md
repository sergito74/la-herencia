# Feature Specification: Conciliación de Tesorería

**Feature Branch**: `023-conciliacion-tesoreria`

**Created**: 2026-09-28

**Status**: Draft

**Input**: User description: "Nuevo módulo 'Conciliación de Tesorería': desde cada listado de movimientos de Tesorería (Banco Nación, Galicia, Mercado Libre, Efectivo, Valores propios, Valores recibidos — no Tarjetas, que ya tiene su propio flujo de conciliación en 009), permitir asignar manualmente uno o más contactos (proveedor, socio, entidad, organismo) a una línea/movimiento, para conciliar la cuenta y dejar el ingreso o egreso imputado a esa cuenta corriente. Convive con la sugerencia automática de 'Referencia de origen' ya existente. Al asignar, debe crear/actualizar un movimiento real en la cuenta corriente del contacto (no una etiqueta informativa). Debe soportar repartir un movimiento entre varios contactos. Es distinto de 022-reasignación-contacto (esa es una corrección puntual posterior de un movimiento que YA tiene contacto asignado; esta es la asignación inicial para movimientos que hoy no tienen ningún contacto reconocido)."

## Clarifications

### Session 2026-09-28

- Q: ¿Este módulo reemplaza la sugerencia automática de "Referencia de origen" (matching por fecha/importe/contacto ya existente en Tesorería) o convive con ella? → A: Convive. La sugerencia automática sigue mostrando candidatas en los listados de Tesorería; la conciliación manual es el lugar donde el usuario confirma esa sugerencia, la corrige, o asigna un contacto cuando no hay ninguna sugerencia automática, o cuando necesita repartir un movimiento entre varios contactos.
- Q: ¿Qué debe pasar en la cuenta corriente del contacto cuando se le asigna un movimiento desde este módulo? → A: Debe generar/actualizar un movimiento real (debe/haber) en la cuenta corriente de ese contacto, con el mismo criterio que ya aplican automáticamente Compras, Ventas, Impuestos y Remuneraciones — no debe ser una etiqueta puramente informativa sin efecto contable.
- Q: ¿La corrección de una conciliación ya aplicada por este módulo debe pasar por 022-reasignación-contacto, o este módulo necesita su propio mecanismo de corrección? → A: Pasa por 022-reasignación-contacto. Ese mecanismo se extiende para cubrir también los orígenes nuevos de este módulo (Efectivo, Valores propios, Valores recibidos, Mercado Libre), además de los que ya soporta (Galicia, Banco Nación, Tarjetas), de forma que siga habiendo un único lugar para corregir a quién quedó asignado un movimiento.
- Q: En un reparto entre varios contactos, ¿hay que completar y confirmar todas las partes en una sola sesión, o se puede conciliar una parte ahora y dejar el resto pendiente para más adelante? → A: Se permite reparto incremental — el usuario puede conciliar una parte del importe ahora y dejar el resto pendiente, retomándolo en otra sesión. El movimiento tiene un estado intermedio "parcialmente conciliado" mientras queda un saldo sin asignar a ningún contacto.
- Q: ¿El módulo debe aplicar también a los movimientos históricos ya cargados (años de datos), o solo a los nuevos de acá en adelante? → A: Aplica a todo el histórico. La acción de conciliar está disponible en cualquier movimiento sin contacto reconocido, sin importar su fecha — no hay una pantalla separada de "backlog histórico" ni un corte por fecha de lanzamiento; el usuario concilia lo que quiera, cuando quiera, desde el mismo listado de siempre.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Conciliar un movimiento con un único contacto (Priority: P1) 🎯 MVP

Un usuario revisando un listado de Tesorería (por ejemplo Banco Nación o Efectivo) encuentra un movimiento sin ningún contacto asociado todavía, y sabe a qué proveedor, socio, entidad u organismo corresponde. Necesita poder asignárselo ahí mismo, sin salir de la pantalla, de forma que ese movimiento pase a reflejarse en la cuenta corriente del contacto elegido.

**Why this priority**: Es el caso más frecuente — la mayoría de los movimientos de Tesorería no tienen hoy ningún contacto reconocido, y sin esto la única forma de conciliarlos es una intervención técnica directa sobre la base de datos.

**Independent Test**: Sobre un movimiento de Tesorería sin contacto asignado, usar la acción de conciliar, elegir un contacto, confirmar, y verificar que el movimiento pasa a aparecer con el importe correcto en la cuenta corriente de ese contacto, y que el listado de Tesorería refleja que la línea ya quedó conciliada.

**Acceptance Scenarios**:

1. **Given** un movimiento de Tesorería sin contacto asignado, **When** el usuario elige la acción de conciliar y selecciona un contacto, **Then** el sistema pide confirmación explícita antes de aplicar la asignación.
2. **Given** que el usuario confirmó la conciliación, **When** se aplica el cambio, **Then** el movimiento pasa a verse en la cuenta corriente del contacto elegido (debe o haber según corresponda) y el listado de Tesorería muestra la línea como conciliada.
3. **Given** un movimiento que "Referencia de origen" ya sugirió como candidata (coincidencia única), **When** el usuario concilia el movimiento, **Then** puede aceptar la candidata sugerida como atajo, sin tener que volver a buscar el contacto a mano.
4. **Given** un movimiento en un medio de Tesorería no cubierto por este módulo (Tarjetas, que ya tiene su propio flujo en 009), **When** el usuario intenta conciliarlo desde acá, **Then** el sistema explica claramente que ese medio se concilia desde su propia pantalla, sin fallar de forma confusa.

---

### User Story 2 - Repartir un movimiento entre varios contactos (Priority: P2)

Un usuario encuentra un movimiento que en realidad agrupa el pago a más de un contacto (por ejemplo, un cargo de Mercado Libre que corresponde a compras a varios proveedores distintos, o un pago en efectivo que cubre dos facturas de proveedores diferentes). Necesita repartir el importe del movimiento entre esos contactos, en vez de asignarlo entero a uno solo.

**Why this priority**: Es una necesidad real y frecuente en los medios que agrupan pagos (Mercado Libre, Efectivo), pero depende de que el mecanismo de asignación simple (Historia 1) ya exista — es una extensión de ese mecanismo, no un camino aparte.

**Independent Test**: Sobre un movimiento sin conciliar, repartirlo entre dos o más contactos con importes parciales que sumen el total del movimiento, confirmar, y verificar que cada contacto ve su parte correspondiente reflejada en su propia cuenta corriente.

**Acceptance Scenarios**:

1. **Given** un movimiento sin conciliar, **When** el usuario agrega uno o más contactos con un importe parcial para cada uno y confirma, **Then** el sistema aplica esa parte del reparto de inmediato — no exige completar el 100% del importe en la misma sesión.
2. **Given** un movimiento con parte de su importe ya conciliado y un saldo todavía sin asignar, **When** el usuario o cualquier otro lo ve en el listado de Tesorería, **Then** aparece distinguido como "parcialmente conciliado" (ni sin conciliar, ni conciliado por completo), con el saldo pendiente visible.
3. **Given** un movimiento parcialmente conciliado, **When** el usuario retoma la conciliación (en la misma sesión o en otra posterior), **Then** puede seguir agregando contactos e importes sobre el saldo pendiente, hasta que la suma de todas las partes (las ya confirmadas más las nuevas) coincida con el importe total del movimiento y quede marcado como conciliado por completo.
4. **Given** un reparto confirmado entre varios contactos, **When** se consulta la cuenta corriente de cada uno de esos contactos, **Then** cada uno ve reflejada únicamente su parte del movimiento, con el resto de los datos (fecha, documento de origen) identificando claramente que proviene de un movimiento compartido.
5. **Given** una parte del reparto ya confirmada, **When** el usuario quiere corregirla (cambiar el contacto o el importe de esa parte), **Then** lo hace a través de 022-reasignación-contacto (FR-008a), con el mismo criterio de auditoría que cualquier otra corrección — no se sobrescribe silenciosamente.

---

### User Story 3 - Evitar conciliar dos veces el mismo movimiento (Priority: P1)

Un usuario no debe poder conciliar un movimiento que ya tiene un contacto reconocido por otro camino (por ejemplo, un movimiento bancario que ya está vinculado automáticamente a una Compra, o que ya fue conciliado antes desde este mismo módulo), para no duplicar el efecto en las cuentas corrientes.

**Why this priority**: Es una condición de integridad de los datos contables — sin esto, el mismo ingreso o egreso podría terminar contado dos veces (una vez por el origen automático ya existente, otra por la conciliación manual), lo que rompe la confianza en los saldos de cuenta corriente.

**Independent Test**: Intentar conciliar un movimiento que ya tiene un contacto reconocido (por el origen que sea) y verificar que el sistema lo bloquea o lo muestra claramente como "ya conciliado", sin permitir una segunda asignación que duplique el efecto.

**Acceptance Scenarios**:

1. **Given** un movimiento de Tesorería que ya tiene un contacto reconocido por su origen habitual, **When** el usuario lo ve en el listado, **Then** el sistema lo distingue visualmente de los movimientos sin conciliar y no ofrece la acción de conciliar sobre él (o, si la ofrece para corregirlo, dirige al mecanismo de corrección ya existente — 022-reasignación-contacto — en vez de crear una asignación paralela).
2. **Given** un movimiento ya conciliado desde este módulo, **When** el usuario lo vuelve a ver en el listado, **Then** aparece marcado como conciliado y no se puede volver a conciliar de cero (solo corregir, con el mismo criterio de auditoría).

---

### Edge Cases

- ¿Qué pasa si el usuario intenta conciliar un movimiento con un contacto y luego, antes de terminar el reparto de la Historia 2, decide que en realidad debía ir a un único contacto? Debe poder cambiar de "un contacto" a "varios contactos" (o viceversa) antes de confirmar, sin perder lo ya cargado.
- ¿Qué pasa si dos usuarios intentan conciliar el mismo movimiento al mismo tiempo? Debe aplicarse solo una conciliación consistente; el segundo intento debe ver el estado ya actualizado (movimiento ya conciliado), no crear una segunda asignación.
- ¿Qué pasa si se concilia un movimiento por error con el contacto equivocado? Debe poder corregirse después (mismo criterio que 022-reasignación-contacto: nunca se pierde el historial de a quién estuvo asignado antes).
- ¿Qué pasa si el importe repartido entre varios contactos no cierra exacto contra el total del movimiento (por redondeo de centavos)? El sistema debe aplicar la misma tolerancia de redondeo ya usada en el resto del sistema para este tipo de controles, no exigir una igualdad matemática perfecta al centavo si la diferencia es solo de redondeo.
- ¿Qué pasa si el usuario intenta conciliar más importe del que queda pendiente en un movimiento parcialmente conciliado (por ejemplo, quedan $300 sin asignar y carga una parte de $500)? El sistema debe rechazarlo, mostrando claramente cuánto queda pendiente de ese movimiento.
- ¿Qué pasa si un movimiento queda parcialmente conciliado por mucho tiempo sin que nadie complete el resto? Debe seguir siendo visible y distinguible como pendiente en el listado (FR-009), sin un vencimiento ni una reversión automática del saldo ya conciliado.
- ¿Qué pasa con un movimiento de un medio donde "Referencia de origen" ya encontró una coincidencia ambigua (varias candidatas posibles)? El usuario debe poder elegir cuál de esas candidatas es la correcta al conciliar, en vez de tener que buscar el contacto de cero.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE permitir, desde el listado de movimientos de cada medio de Tesorería cubierto (Banco Nación, Galicia, Mercado Libre, Efectivo, Valores propios, Valores recibidos), iniciar la conciliación de un movimiento sin contacto reconocido.
- **FR-002**: El sistema DEBE excluir explícitamente a Tarjetas de este módulo — ese medio sigue conciliándose exclusivamente por su flujo ya existente (008/009).
- **FR-003**: El sistema DEBE requerir una confirmación explícita del usuario antes de aplicar cualquier conciliación.
- **FR-004**: El sistema DEBE permitir asignar un movimiento a un único contacto (Historia 1) o repartirlo entre varios contactos con importes parciales (Historia 2).
- **FR-005**: El sistema DEBE, al confirmar una conciliación (simple o repartida), reflejar el o los importes correspondientes en la cuenta corriente del o de los contactos elegidos (debe/haber), con el mismo criterio contable que ya aplican automáticamente Compras, Ventas, Impuestos y Remuneraciones sobre sus propios movimientos.
- **FR-006**: El sistema DEBE permitir confirmar un reparto entre varios contactos de forma incremental — cada confirmación aplica la parte cargada en ese momento, sin exigir que la suma llegue al importe total del movimiento en la misma sesión. El movimiento queda "conciliado por completo" recién cuando la suma acumulada de todas las partes confirmadas (en una o más sesiones) coincide con el importe total, dentro de la tolerancia de redondeo ya usada en el resto del sistema; hasta entonces queda "parcialmente conciliado", con el saldo pendiente visible.
- **FR-007**: El sistema DEBE mostrar, junto a cada candidata sugerida automáticamente por "Referencia de origen", la posibilidad de aceptarla directamente como conciliación, sin que el usuario tenga que volver a buscar el contacto a mano.
- **FR-008**: El sistema DEBE impedir que un movimiento que ya tiene un contacto reconocido (por su origen automático habitual, o por una conciliación previa de este mismo módulo) se concilie de nuevo desde cero — un movimiento ya conciliado solo admite corrección, nunca una segunda asignación paralela que duplique el efecto en cuentas corrientes.
- **FR-008a**: La corrección de una conciliación ya aplicada por este módulo DEBE hacerse a través de 022-reasignación-contacto — no un mecanismo de corrección separado. 022-reasignación-contacto DEBE extenderse para soportar, como un único origen nuevo, las conciliaciones aplicadas por este módulo (sin importar de qué medio de Tesorería — Efectivo, Valores propios, Valores recibidos, Mercado Libre, etc. — provino la conciliación original), sumándose a los orígenes que ya soporta (Galicia, Banco Nación, Tarjetas), de forma que exista un único lugar en todo el sistema para corregir a quién quedó asignado un movimiento.
- **FR-009**: El sistema DEBE distinguir visualmente, en cada listado de Tesorería cubierto, tres estados por movimiento: sin conciliar, parcialmente conciliado (con saldo pendiente visible), y conciliado por completo (por cualquier vía, incluido el reconocimiento automático de su origen habitual).
- **FR-010**: El sistema DEBE resolver de forma consistente el caso de dos usuarios conciliando el mismo movimiento al mismo tiempo, de forma que se aplique una sola conciliación y el segundo intento vea el estado ya actualizado.
- **FR-011**: El sistema DEBE conservar un registro de auditoría de cada conciliación aplicada (movimiento, contacto o contactos asignados, importes, quién y cuándo), con el mismo criterio de trazabilidad permanente ya exigido en 022-reasignación-contacto.

### Key Entities *(include if feature involves data)*

- **Movimiento conciliable**: un movimiento de Tesorería (Banco Nación, Galicia, Mercado Libre, Efectivo, Valores propios o Valores recibidos) que hoy no tiene ningún contacto reconocido por su origen automático habitual, y por lo tanto tampoco se refleja todavía en ninguna cuenta corriente.
- **Conciliación**: la asignación de un contacto a una parte (o a la totalidad) del importe de un movimiento conciliable. Un movimiento puede tener más de una conciliación a lo largo del tiempo (reparto incremental) — cada una genera su propio efecto en la cuenta corriente del contacto correspondiente. El movimiento en su conjunto tiene un estado derivado de la suma de sus conciliaciones: sin conciliar, parcialmente conciliado, o conciliado por completo.
- **Candidata de Referencia de origen**: la sugerencia automática ya existente (matching por contacto/fecha/importe) que este módulo puede usar como atajo para completar una conciliación, sin tener que resolverla desde cero.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un usuario puede conciliar un movimiento simple (un único contacto) desde que lo identifica hasta que queda reflejado en la cuenta corriente correcta, en menos de 1 minuto, sin intervención técnica directa sobre la base de datos.
- **SC-002**: El 100% de las conciliaciones aplicadas (simples o repartidas) quedan con un registro consultable de qué contacto(s), qué importe(s), quién y cuándo — verificable en cualquier auditoría posterior.
- **SC-003**: Ningún movimiento conciliado por este módulo puede quedar contado dos veces en cuentas corrientes (ni por conciliarse dos veces desde acá, ni por coexistir con un reconocimiento automático de otro origen).
- **SC-004**: En el 100% de los movimientos marcados como "conciliado por completo", la suma de todas sus conciliaciones (una o varias, aplicadas en una o más sesiones) es igual al importe total del movimiento, dentro de la tolerancia de redondeo del sistema.

## Assumptions

- "Sin contacto reconocido" se refiere a movimientos de Tesorería cuyo origen automático habitual no les asignó ningún contacto — no a una propiedad visible distinta por cada medio; el sistema ya sabe, para cada medio, cuándo un movimiento cae en ese caso.
- El módulo aplica por igual a movimientos históricos y nuevos — no hay corte por fecha de lanzamiento ni una pantalla separada de "backlog histórico"; cualquier movimiento sin contacto reconocido, sin importar cuán viejo sea, puede conciliarse desde el mismo listado de Tesorería de siempre.
- Este módulo no reemplaza a 022-reasignación-contacto: ese sigue siendo el único mecanismo para corregir un contacto ya asignado (por este módulo o por cualquier otro origen); este módulo cubre exclusivamente la asignación inicial de movimientos que hoy no tienen ningún contacto. Como parte de este trabajo, 022-reasignación-contacto se extiende para soportar las conciliaciones que este módulo introduce, como un único origen nuevo (no uno por cada medio de Tesorería) — ver FR-008a.
- La búsqueda de contacto al conciliar reutiliza el mismo mecanismo de búsqueda ya existente en el resto del sistema (por nombre/razón social, con sugerencias mientras se escribe).
- Cualquier usuario autenticado con permisos de escritura puede conciliar movimientos, con el mismo criterio de roles ya usado en el resto del sistema (sin un rol especial adicional para esta función).
- Se opera sobre la base de datos de trabajo (`WC`); toda conciliación real que se aplique durante el desarrollo/validación de esta función sigue el mismo resguardo ya usado en features anteriores.
- El reparto entre varios contactos (Historia 2) no tiene un límite fijo de cantidad de contactos por movimiento — el límite práctico lo da la cantidad de partes que tengan sentido para ese importe.
