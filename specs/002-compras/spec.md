# Feature Specification: Compras como fuente de verdad de imputación (solo lectura)

**Feature Branch**: `002-compras`

**Created**: 2026-09-15

**Status**: Draft

**Input**: User description: "Diseñar el módulo web de compras en modo solo lectura, usando Python, SQL Server, Next.js, TypeScript, Tailwind CSS y TanStack Query. Compras pasa a ser la fuente de verdad de imputación (rubro, centro de costo, destino) para todo el sistema, reemplazando la imputación que hoy vive en los resúmenes bancarios. Debe permitir listar y buscar compras, ver su detalle (líneas, rubros, IVA, conceptos no gravados, ingresos brutos) y dejar explícita la imputación de cada línea. Debe permitir trazabilidad hacia adelante, hacia los movimientos de cuenta corriente y tesorería que cada compra genera. Reemplaza completamente la carga/consulta de compras del sistema VB.NET/Access. Preparado para multiusuario aunque hoy lo use una sola persona. No modificar datos reales."

**Amendment 2026-09-16** (post-MVP, con US1/US2 ya implementadas): ampliación basada en hallazgos confirmados del análisis del sistema Access legado (`docs/legacy-access-analysis.md`) — compras en dólares con doble criterio de tipo de cambio, remitos como control de entrega vs. facturación, cargos de cabecera (guías/comisión/financiación/gastos), e imputación de rubro/centro de costo que no es puramente manual (existe autocompletado por palabra clave con backfill retroactivo). Sigue siendo un módulo de solo lectura.

## Clarifications

### Session 2026-09-15

- Q: ¿Cuál es la clave que vincula una compra con sus movimientos de cuenta corriente y tesorería (FR-008/FR-009)? → A: `IdOrigen` (en los movimientos de cuenta corriente/tesorería) apunta al identificador de la compra (`IdDeuda` o `IdCompra`)
- Q: ¿Qué debe garantizar hoy la preparación "multiusuario"? → A: El backend debe soportar sesiones concurrentes reales y ya prever bloqueos/locks de lectura entre usuarios distintos

### Session 2026-09-16

- Q: `Det_Compras` tiene una columna `IdCampaña`/`Campaña` no contemplada originalmente en esta spec (confirmado contra `INFORMATION_SCHEMA` el 2026-09-16). ¿Se incluye la campaña como dato de imputación de esta primera versión? → A: Sí, se agrega como atributo de imputación de cada línea de compra, junto con rubro/centro de costo/destino
- Q: ¿El estado de remito por línea de compra (FR-018) debe calcularse en el momento de la consulta replicando el algoritmo de matching remito-factura de Access, o alcanza con consumir un cálculo ya persistido en SQL Server? → A: No está confirmado todavía; la spec deja ambas rutas contempladas y la decisión se resuelve verificando el esquema real en la fase de `/speckit-plan`, antes de comprometerse a una implementación
- Q: ¿El dólar de referencia BNA por fecha (FR-016) ya está disponible como dato consultable en SQL Server? → A: Mismo criterio que FR-018 — no confirmar ahora, dejarlo como verificación pendiente en `/speckit-plan`
- Q: ¿Existe en SQL Server algún dato que permita distinguir si la imputación de una línea de compra (FR-019) fue asignada automáticamente o manualmente? → A: No confirmado todavía — se verifica en `/speckit-plan` junto con los otros dos puntos de research pendientes (dólar BNA, cálculo de remito)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Buscar y listar compras (Priority: P1)

Un usuario administrativo necesita encontrar una compra específica (por proveedor, fecha o número de documento) o revisar el listado reciente de compras, para responder preguntas operativas sin abrir el sistema anterior.

**Why this priority**: Es el punto de entrada de todo el módulo; sin poder encontrar una compra, ninguna otra funcionalidad es accesible.

**Independent Test**: Puede probarse buscando una compra conocida por proveedor o número de documento y verificando que aparece en los resultados con sus datos principales (fecha, proveedor, tipo de documento, número).

**Acceptance Scenarios**:

1. **Given** el usuario está en el módulo de compras, **When** busca por razón social de proveedor, **Then** el sistema muestra las compras de ese proveedor ordenadas por fecha descendente.
2. **Given** el usuario está en el módulo de compras, **When** busca por número de documento, **Then** el sistema muestra la compra correspondiente si existe.
3. **Given** una búsqueda sin resultados, **When** el usuario consulta, **Then** el sistema muestra un estado vacío claro, sin error.

---

### User Story 2 - Ver el detalle e imputación de una compra (Priority: P1)

Un usuario administrativo necesita abrir una compra puntual y ver sus líneas de detalle (producto/servicio, cantidad, precio unitario, IVA) junto con la imputación de cada línea (rubro, centro de costo, destino), para entender a qué corresponde el gasto y validar que está correctamente clasificado.

**Why this priority**: Es el corazón del cambio de estrategia: la imputación deja de vivir en tesorería y pasa a mostrarse aquí como dato central de cada compra. Sin esto, el módulo no cumple su propósito principal.

**Independent Test**: Puede probarse abriendo una compra existente y verificando que cada línea de detalle muestra su rubro y, cuando exista, centro de costo y destino, además de cantidad, precio e IVA.

**Acceptance Scenarios**:

1. **Given** el usuario abrió una compra, **When** revisa sus líneas de detalle, **Then** el sistema muestra para cada línea: producto/servicio, cantidad, precio unitario, IVA y rubro asignado.
2. **Given** una línea de detalle sin centro de costo o destino asignado, **When** el usuario la revisa, **Then** el sistema indica explícitamente que ese dato no está asignado, sin ocultarlo ni mostrarlo como error.
3. **Given** una compra con conceptos no gravados o ingresos brutos, **When** el usuario abre su detalle, **Then** el sistema muestra esos importes de forma diferenciada del resto de las líneas.

---

### User Story 3 - Navegar desde una compra hacia sus movimientos de cuenta corriente y tesorería (Priority: P2)

Un usuario administrativo, estando en el detalle de una compra, necesita ver qué movimientos de cuenta corriente y de tesorería generó esa compra, para seguir el proceso completo desde el gasto hasta el pago.

**Why this priority**: Da trazabilidad hacia adelante, valor de auditoría real, pero depende de que existan los módulos de tesorería y cuentas corrientes (fuera del alcance de esta spec) — por eso es P2 y no P1: el módulo de compras debe funcionar de forma independiente sin esto.

**Independent Test**: Puede probarse tomando una compra con pagos registrados y verificando que el sistema muestra al menos la referencia (aunque no navegue a una pantalla completa) a los movimientos de cuenta corriente/tesorería asociados a esa compra.

**Acceptance Scenarios**:

1. **Given** una compra con movimientos de cuenta corriente asociados, **When** el usuario consulta su trazabilidad, **Then** el sistema muestra la referencia a esos movimientos (documento, fecha, importe).
2. **Given** una compra sin movimientos asociados todavía (pendiente de pago), **When** el usuario consulta su trazabilidad, **Then** el sistema indica explícitamente que no hay movimientos registrados, sin error.

---

### User Story 4 - Ver el total en dólares de una compra en moneda extranjera (Priority: P2)

Un usuario administrativo, al abrir una compra pactada en dólares, necesita ver su total convertido, usando el mismo criterio de tipo de cambio que usa el negocio (el de la factura, o el dólar de referencia BNA cuando corresponde), para poder comparar compras entre sí de forma consistente.

**Why this priority**: Corrige una omisión real del MVP (no todas las compras son en pesos), pero el módulo ya entrega valor completo en pesos sin esto — es una ampliación, no un bloqueante.

**Independent Test**: Puede probarse abriendo una compra en dólares y verificando que se muestra el total convertido según el criterio de tipo de cambio que corresponda a esa compra.

**Acceptance Scenarios**:

1. **Given** una compra en dólares que usa el tipo de cambio de su propia factura, **When** el usuario la consulta, **Then** el sistema muestra el total convertido a pesos usando ese tipo de cambio, identificado como tal.
2. **Given** una compra en dólares marcada para ajustarse al dólar de referencia (BNA) de la fecha de compra, **When** el usuario la consulta, **Then** el sistema muestra el total convertido usando el dólar de referencia de esa fecha, identificado como tal (distinto del tipo de cambio de la factura).
3. **Given** una compra en pesos, **When** el usuario la consulta, **Then** el sistema no muestra ninguna conversión de moneda.

---

### User Story 5 - Ver el estado de remito de cada línea de compra (Priority: P2)

Un usuario administrativo, revisando el detalle de una compra, necesita saber si lo facturado ya fue efectivamente entregado (remitido), parcialmente o por completo, para controlar que la facturación coincide con la entrega física de insumos.

**Why this priority**: Es un control real que el negocio ya usa (remitos), pero es información adicional sobre una compra que el módulo ya puede mostrar sin esto — no bloquea el valor principal.

**Independent Test**: Puede probarse abriendo una compra con remitos vinculados y verificando que cada línea muestra su estado de remito (sin remitir / parcialmente remitida / completamente remitida).

**Acceptance Scenarios**:

1. **Given** una línea de compra completamente cubierta por uno o más remitos, **When** el usuario la consulta, **Then** el sistema la marca como "completamente remitida".
2. **Given** una línea de compra parcialmente cubierta por remitos, **When** el usuario la consulta, **Then** el sistema la marca como "parcialmente remitida", indicando la cantidad pendiente.
3. **Given** una línea de compra sin ningún remito vinculado, **When** el usuario la consulta, **Then** el sistema la marca como "sin remitir".
4. **Given** una línea de compra que no es un insumo remitible (por ejemplo, un servicio), **When** el usuario la consulta, **Then** el sistema no muestra estado de remito para esa línea, en lugar de forzar un "sin remitir" engañoso.

---

### Edge Cases

- ¿Qué sucede con compras históricas cuya imputación (rubro/centro de costo/destino) nunca se cargó? El sistema debe mostrarlas igual, señalando la imputación como no disponible, sin bloquear la consulta ni inventar un valor.
- ¿Cómo se maneja una compra con múltiples líneas donde cada línea tiene un rubro distinto? El sistema debe mostrar la imputación a nivel de línea, no un único rubro por compra.
- ¿Qué sucede si el proveedor de una compra fue dado de baja o cambiado de tipo en `Contactos`? El sistema debe mostrar la compra igual, con los datos del proveedor tal como estaban al momento de la operación si están disponibles, o indicar que el contacto no está disponible.
- ¿Cómo se comporta el listado ante grandes volúmenes (miles de compras)? Debe soportar paginación o desplazamiento progresivo sin degradar el tiempo de respuesta.
- ¿Qué sucede si una compra en dólares no tiene definido el criterio de ajuste de tipo de cambio (dato histórico incompleto)? El sistema debe mostrar el tipo de cambio de la factura como criterio por defecto, sin bloquear la consulta, e indicar que no se aplicó ajuste.
- ¿Qué sucede si un remito fue eliminado o no es accesible pero una línea de compra todavía lo referencia? El sistema debe mostrar la línea igual, indicando que el estado de remito no está disponible, sin bloquear la consulta.
- ¿Qué sucede si el origen de una imputación (automática vs. manual) no está registrado para una línea histórica? El sistema debe mostrar la imputación igual, sin indicar origen, en lugar de asumir uno.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST permitir buscar compras por proveedor (razón social), por número de documento y por rango de fechas.
- **FR-002**: El sistema MUST listar compras mostrando como mínimo fecha, proveedor, tipo de documento y número de documento.
- **FR-003**: El sistema MUST mostrar el detalle completo de una compra, incluyendo todas sus líneas (`Det_Compras`).
- **FR-004**: El sistema MUST mostrar, para cada línea de detalle, la imputación de rubro y, cuando exista, centro de costo, destino y campaña.
- **FR-005**: El sistema MUST tratar la imputación de compras como la fuente de verdad para rubro/centro de costo/destino, sin derivarla ni sobrescribirla desde datos de tesorería.
- **FR-006**: El sistema MUST indicar explícitamente cuando una línea de compra no tiene imputación asignada, en lugar de omitir el dato o mostrar un valor por defecto engañoso.
- **FR-007**: El sistema MUST mostrar conceptos no gravados e ingresos brutos de forma diferenciada de las líneas de detalle gravadas.
- **FR-008**: El sistema MUST mostrar la referencia a los movimientos de cuenta corriente y tesorería asociados a una compra, cuando existan y sean accesibles, vinculando por el campo `IdOrigen` de esos movimientos contra el identificador de la compra (`IdDeuda`/`IdCompra`).
- **FR-009**: El sistema MUST indicar de forma explícita cuando una compra no tiene movimientos de cuenta corriente o tesorería asociados todavía.
- **FR-010**: El sistema MUST operar exclusivamente en modo lectura: ninguna pantalla del módulo debe permitir crear, editar ni eliminar compras ni sus líneas.
- **FR-011**: El sistema MUST consultar los datos exclusivamente desde SQL Server, sin acceder a bases Access ni fuentes locales duplicadas.
- **FR-012**: El sistema MUST mostrar un estado vacío explícito cuando una búsqueda de compras no tenga resultados.
- **FR-013**: El sistema MUST soportar paginación o desplazamiento progresivo en el listado de compras para volúmenes de miles de registros sin degradar el tiempo de respuesta.
- **FR-014**: El sistema MUST soportar sesiones de lectura concurrentes de múltiples usuarios sin degradar ni bloquear la consulta de otros usuarios (dado que todas las operaciones del módulo son de solo lectura, no se requieren bloqueos de escritura en esta etapa).
- **FR-015**: El sistema MUST mostrar la moneda de una compra (pesos o dólares) y, cuando sea en dólares, el tipo de cambio de la factura.
- **FR-016**: El sistema MUST mostrar, para una compra en dólares marcada para ajustar tipo de cambio, el total convertido usando el dólar de referencia (BNA) de la fecha de compra, identificado como distinto del total según tipo de cambio de factura. La disponibilidad de esa cotización como dato consultable en SQL Server queda pendiente de confirmar en `/speckit-plan` (clarificación 2026-09-16); si no está disponible, la fuente de ese dato deberá definirse antes de implementar este requisito.
- **FR-017**: El sistema MUST mostrar los cargos de cabecera de una compra (guías, comisión, financiación, gastos) de forma diferenciada de las líneas de detalle, cuando existan.
- **FR-018**: El sistema MUST mostrar, para cada línea de compra remitible, su estado de remito: "sin remitir", "parcialmente remitida" o "completamente remitida", con la cantidad pendiente cuando sea parcial. La fuente del cálculo (vista/cálculo ya existente en SQL Server, vs. réplica del algoritmo de matching remito-factura en este módulo) queda pendiente de confirmar en `/speckit-plan` contra el esquema real (clarificación 2026-09-16); el requisito funcional no cambia según cuál sea la fuente, solo la forma de implementarlo.
- **FR-019**: El sistema MUST indicar si la imputación de rubro/centro de costo de una línea fue asignada de forma automática o manual, cuando ese dato esté disponible; si no está disponible, MUST mostrar la imputación sin indicar origen, sin asumir uno por defecto. La existencia real de ese dato en SQL Server (a diferencia de las reglas de autocompletado, que sí están confirmadas en Access) queda pendiente de confirmar en `/speckit-plan` (clarificación 2026-09-16); si no existe ningún campo que lo registre, este requisito se reformula como "no disponible en esta versión" al planificar, sin bloquear el resto del módulo.

### Key Entities *(include if feature involves data)*

- **Compra**: documento de compra a un proveedor. Atributos clave: fecha, proveedor (contacto), tipo de documento, número de documento, conceptos no gravados, ingresos brutos.
- **Línea de compra**: detalle de una compra. Atributos clave: producto/servicio, cantidad, precio unitario, IVA, rubro, y (cuando existan) centro de costo, destino y campaña.
- **Rubro**: categoría de clasificación de una línea de compra, fuente de verdad de imputación junto con centro de costo, destino y campaña.
- **Campaña**: período/ciclo productivo al que se imputa una línea de compra (ej. "Cosecha 2026"), confirmado en el esquema real (`Det_Compras.IdCampaña`/`Campaña`).
- **Proveedor**: contacto de tipo proveedor asociado a una compra (subconjunto de `Contactos`).
- **Referencia de trazabilidad**: vínculo entre una compra y sus movimientos de cuenta corriente/tesorería asociados, identificado mediante el campo `IdOrigen` del movimiento apuntando al identificador de la compra (`IdDeuda`/`IdCompra`); se muestra como referencia (documento, fecha, importe) aunque los módulos de destino se especifiquen por separado.
- **Moneda y tipo de cambio**: atributos de la cabecera de compra — moneda (pesos/dólares), tipo de cambio de la factura y, cuando corresponda, indicador de ajuste al dólar de referencia BNA de la fecha de compra.
- **Cargos de cabecera**: montos adicionales al total de una compra no asociados a una línea específica (guías, comisión, financiación, gastos).
- **Remito**: entrega física vinculada a una o más líneas de compra; determina el estado de remito de cada línea (sin remitir/parcial/completo) por comparación entre cantidad remitida y cantidad facturada.
- **Origen de imputación**: atributo de la imputación de una línea (automática o manual) cuando esté disponible; indica cómo se asignó el rubro/centro de costo, sin ser en sí mismo una fuente de verdad distinta de la imputación (FR-005 sigue vigente).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un usuario puede encontrar una compra conocida (por proveedor o número de documento) en menos de 30 segundos.
- **SC-002**: El 100% de las líneas de compra consultadas muestran su imputación (rubro y, si existe, centro de costo/destino) o indican explícitamente que no está asignada.
- **SC-003**: Un usuario puede determinar, para cualquier compra, si tiene o no movimientos de cuenta corriente/tesorería asociados, sin salir del módulo.
- **SC-004**: Ningún usuario puede modificar, crear ni eliminar compras ni sus líneas desde el módulo (verificable por ausencia de cualquier acción de escritura en la interfaz).
- **SC-005**: El listado de compras responde en tiempos aceptables (percibidos como instantáneos por el usuario) incluso con miles de registros cargados.
- **SC-006**: El 100% de las compras en dólares consultadas muestran el o los totales convertidos según el criterio de tipo de cambio que corresponda, sin ambigüedad sobre cuál criterio se aplicó.
- **SC-007**: El 100% de las líneas de compra remitibles consultadas muestran un estado de remito explícito (sin remitir/parcial/completo), o indican explícitamente que no está disponible.

## Assumptions

- Los usuarios de este módulo son personal administrativo interno de La Herencia, con acceso ya autorizado (no se define aquí un nuevo esquema de autenticación). El backend/API debe soportar múltiples sesiones de lectura concurrentes desde el inicio (ver FR-014); los roles y permisos específicos (quién puede ver qué) se definirán en una etapa posterior, ya que hoy solo hay un usuario real.
- El módulo es de solo lectura en esta primera versión; la carga de compras seguirá haciéndose por el medio actual hasta que se autorice explícitamente habilitar escritura, conforme a la constitución del proyecto.
- La imputación histórica de compras puede estar incompleta (rubro/centro de costo/destino faltante en registros antiguos); el módulo debe convivir con esos vacíos sin bloquear la consulta.
- Las columnas de rubro/centro de costo/destino en `Movimientos Galicia` (y equivalentes bancarios) quedan deprecadas como fuente de imputación a partir de este módulo; no se eliminan de la base, pero el sistema nuevo no las usa como fuente de verdad.
- La navegación hacia cuenta corriente y tesorería se limita a mostrar referencias/resúmenes en esta spec; las pantallas completas de esos módulos se especifican por separado (tesorería y cuentas corrientes, en ese orden).
- Integraciones fiscales (AFIP/ARCA: facturación electrónica, retenciones, percepciones, validación de CUIT) quedan fuera de alcance de esta primera versión.
- El volumen de datos a mostrar es el observado en el prototipo (miles de compras), por lo que las listas deben soportar paginación o desplazamiento sin degradar la experiencia.
- Las columnas reales de moneda/tipo de cambio/ajuste en la cabecera de `Compras`, aunque confirmadas en el sistema Access legado (`docs/legacy-access-analysis.md`), no fueron verificadas todavía contra `INFORMATION_SCHEMA` de SQL Server para este módulo — se asume que existen con nombre similar, a confirmar antes de planificar la implementación.
- El estado de remito y el origen de imputación (automática/manual) son datos que pueden no estar disponibles para compras históricas migradas antes de que existieran esos mecanismos; el módulo debe convivir con esa ausencia sin bloquear la consulta.
- La fuente del cálculo de estado de remito (FR-018) no está decidida en esta spec (clarificación 2026-09-16); `/speckit-plan` MUST incluir una tarea de research explícita para verificar contra `INFORMATION_SCHEMA`/datos reales si existe un cálculo ya persistido en SQL Server antes de diseñar la solución de este módulo.
- La disponibilidad de la cotización de dólar BNA por fecha (FR-016) tampoco está confirmada en SQL Server (clarificación 2026-09-16); `/speckit-plan` MUST verificarlo junto con el punto anterior, en la misma tarea de research o una equivalente.
- La existencia de un dato que distinga imputación automática de manual (FR-019) tampoco está confirmada (clarificación 2026-09-16); si no existe, FR-019 se reformula como "no disponible" al planificar, en vez de bloquear el módulo completo.
