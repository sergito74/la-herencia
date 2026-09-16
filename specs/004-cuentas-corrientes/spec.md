# Feature Specification: Cuentas corrientes por proveedor/cliente (solo lectura)

**Feature Branch**: `004-cuentas-corrientes`

**Created**: 2026-09-15

**Status**: Draft

**Input**: User description: "Diseñar el módulo web de cuentas corrientes en modo solo lectura, usando Python, SQL Server, Next.js, TypeScript, Tailwind CSS y TanStack Query. Debe permitir seleccionar un contacto (proveedor, cliente u otro tipo) y consultar su saldo actual y sus movimientos de deuda/crédito. Cada movimiento de cuenta corriente debe permitir navegar hacia su origen: si proviene de una compra, mostrar la referencia a esa compra (que ya tiene su imputación definida en el módulo de compras); si proviene de un movimiento de tesorería, mostrar la referencia a ese movimiento. Cuentas corrientes no calcula ni muestra imputación (rubro/centro de costo/destino) propia: ese dato se consulta únicamente en compras. Preparado para multiusuario aunque hoy lo use una sola persona. No modificar datos reales."

## Clarifications

### Session 2026-09-15

- Q: Cuando un movimiento de cuenta corriente tiene origen en tesorería (FR-007), ¿cómo se identifica el movimiento de tesorería específico al que corresponde? → A: El propio movimiento de cuenta corriente trae `Origen` (tipo: compra/tesorería/otro) e `IdOrigen` (id del registro de origen), es una clave directa y confiable

### Session 2026-09-16

- Q: Confirmado contra `INFORMATION_SCHEMA`/datos reales que `Origen` en `vw_MovimientosCuenta_Base` tiene 12 valores distintos, no solo "Compra"/"Tesorería": `Compras`, `Banco Nacion`, `Galicia`, `Pagos efectivo`, `Cobros Valores Recibidos`, `Pagos Valores Recibidos`, y también `Alquileres`, `Impuestos`, `Remuneraciones`, `Ret. IVA Granos`, `Ret. Ventas Hacienda`, `Retenciones` — estos últimos 6 no corresponden a ningún módulo dentro del alcance de `002-compras`/`003-tesoreria`. ¿Cómo se muestran esos 6 casos? → A: Como un tercer estado explícito "origen fuera de alcance", mostrando el tipo de origen tal cual (ej. "Alquileres") sin navegación, distinto de "no disponible" (que implica dato faltante, no proceso fuera de alcance)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Consultar saldo y movimientos de un contacto (Priority: P1)

Un usuario administrativo necesita seleccionar un contacto (proveedor, cliente u otro tipo registrado) y ver su saldo actual junto con el detalle de movimientos que lo componen, para responder preguntas de deuda/crédito sin recurrir al sistema anterior.

**Why this priority**: Es el caso de uso más frecuente del área administrativa y el que hoy requiere consultar Access o el sistema VB.NET original. Sin esto no hay valor mínimo entregado.

**Independent Test**: Puede probarse seleccionando un contacto existente (por ejemplo "Rutas Sur Atlantico S.A.") y verificando que el saldo mostrado coincide con la suma de movimientos (deuda/crédito) trazables hasta ese contacto.

**Acceptance Scenarios**:

1. **Given** el usuario está en el módulo de cuentas corrientes, **When** busca y selecciona un contacto por razón social, **Then** el sistema muestra el saldo actual del contacto y la lista de movimientos que lo componen, ordenados por fecha.
2. **Given** un contacto sin movimientos registrados, **When** el usuario lo selecciona, **Then** el sistema muestra saldo cero y un estado vacío claro en la lista de movimientos.
3. **Given** el usuario aplica un filtro por rango de fechas, **When** consulta los movimientos de un contacto, **Then** la lista y el saldo parcial se actualizan mostrando solo lo correspondiente a ese rango.

---

### User Story 2 - Navegar desde un movimiento de cuenta corriente hacia su origen (Priority: P1)

Un usuario administrativo, viendo un movimiento de cuenta corriente, necesita saber si proviene de una compra o de un movimiento de tesorería, y acceder a esa referencia, para auditar el proceso completo sin perder de dónde salió cada deuda o crédito.

**Why this priority**: Cierra el círculo de trazabilidad entre los tres módulos (compras → tesorería → cuentas corrientes) que el usuario definió como prioridad máxima. Sin esto, cuentas corrientes queda aislado del resto del sistema.

**Independent Test**: Puede probarse tomando un movimiento de cuenta corriente originado en una compra conocida y verificando que el sistema muestra la referencia a esa compra (documento, proveedor); y otro originado en tesorería, verificando la referencia al movimiento correspondiente.

**Acceptance Scenarios**:

1. **Given** un movimiento de cuenta corriente con origen en una compra, **When** el usuario lo consulta, **Then** el sistema muestra la referencia a esa compra (documento, proveedor).
2. **Given** un movimiento de cuenta corriente con origen en un movimiento de tesorería, **When** el usuario lo consulta, **Then** el sistema muestra la referencia a ese movimiento (banco/caja/medio, fecha, importe).
3. **Given** un movimiento de cuenta corriente cuyo origen no está disponible o no es identificable (`IdOrigen` sin cargar o registro inexistente), **When** el usuario lo consulta, **Then** el sistema lo indica explícitamente como "no disponible", sin bloquear la vista del movimiento.
4. **Given** el usuario ve la referencia a una compra desde cuentas corrientes, **When** revisa ese movimiento, **Then** el sistema NO muestra ni calcula rubro/centro de costo/destino en cuentas corrientes — ese dato se consulta únicamente en compras.
5. **Given** un movimiento de cuenta corriente cuyo `Origen` corresponde a un proceso fuera del alcance de los módulos existentes (ej. "Alquileres", "Impuestos", "Remuneraciones", "Retenciones", "Ret. IVA Granos", "Ret. Ventas Hacienda"), **When** el usuario lo consulta, **Then** el sistema muestra el tipo de origen tal cual (ej. "Alquileres") marcado explícitamente como "origen fuera de alcance", distinto del caso "no disponible".

---

### User Story 3 - Distinguir tipos de contacto al buscar (Priority: P2)

Un usuario administrativo necesita filtrar la búsqueda de contactos por tipo (proveedor, cliente, banco, empleado, organismo, tarjeta de crédito, etc.) para encontrar más rápido al contacto correcto cuando hay nombres similares o ambiguos.

**Why this priority**: Mejora la eficiencia de búsqueda pero el módulo ya entrega su valor principal (P1) sin esto; se vuelve más relevante a medida que crece la cantidad de contactos consultados.

**Independent Test**: Puede probarse filtrando por tipo "Proveedor" y verificando que solo aparecen contactos de ese tipo en los resultados de búsqueda.

**Acceptance Scenarios**:

1. **Given** el usuario está buscando un contacto, **When** aplica un filtro por tipo de contacto, **Then** los resultados de búsqueda se limitan a ese tipo.
2. **Given** un contacto de tipo "Multiple", **When** aparece en resultados de cualquier filtro compatible, **Then** el sistema lo muestra sin duplicarlo entre tipos.

### Edge Cases

- ¿Qué sucede si un contacto tiene múltiples tipos (por ejemplo "Multiple") y aparece tanto en compras como en tesorería? El sistema debe mostrar todos sus movimientos combinados sin duplicarlos.
- ¿Cómo maneja el sistema un movimiento cuyo origen (compra u operación de tesorería) fue eliminado o no es accesible? Debe mostrar el movimiento igualmente, indicando que el origen no está disponible, sin bloquear la consulta.
- ¿Qué sucede si la búsqueda de contacto no encuentra resultados? El sistema debe mostrar un mensaje claro de "sin resultados" y permitir reintentar la búsqueda.
- ¿Cómo se muestran importes negativos o saldos a favor del contacto (crédito) versus en contra (deuda)? Deben distinguirse visualmente de forma inequívoca.
- ¿Qué sucede si un movimiento de cuenta corriente proviene de una compra cuya imputación todavía no está cargada? Cuentas corrientes debe mostrar igual la referencia a la compra; la ausencia de imputación se resuelve y comunica desde el módulo de compras, no aquí.
- ¿Qué sucede si `Origen` corresponde a un proceso fuera de alcance (alquileres, impuestos, remuneraciones, retenciones)? El sistema debe mostrar el tipo de origen tal cual, marcado como "fuera de alcance", sin intentar navegar a un módulo que no existe (clarificación 2026-09-16).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST permitir buscar y seleccionar un contacto (proveedor, cliente u otro tipo) por razón social o identificador.
- **FR-002**: El sistema MUST permitir filtrar la búsqueda de contactos por tipo de contacto.
- **FR-003**: El sistema MUST mostrar el saldo actual de un contacto seleccionado, calculado a partir de sus movimientos de cuenta corriente.
- **FR-004**: El sistema MUST listar los movimientos de cuenta corriente de un contacto, ordenados por fecha, mostrando como mínimo fecha, documento, deuda/crédito y origen.
- **FR-005**: El sistema MUST permitir filtrar movimientos de cuenta corriente por rango de fechas.
- **FR-006**: El sistema MUST mostrar, para cada movimiento de cuenta corriente originado en una compra, la referencia a esa compra (documento, proveedor), resuelta mediante los campos `Origen`/`IdOrigen` del movimiento de cuenta corriente.
- **FR-007**: El sistema MUST mostrar, para cada movimiento de cuenta corriente originado en tesorería, la referencia a ese movimiento (banco/caja/medio, fecha, importe), resuelta mediante los campos `Origen`/`IdOrigen` del movimiento de cuenta corriente.
- **FR-008**: El sistema MUST indicar explícitamente cuando `Origen`/`IdOrigen` de un movimiento de cuenta corriente no están cargados o el registro al que apuntan no está disponible ("no disponible").
- **FR-008b**: El sistema MUST mostrar, para movimientos cuyo `Origen` corresponda a un proceso fuera del alcance de los módulos de compras/tesorería (`Alquileres`, `Impuestos`, `Remuneraciones`, `Retenciones`, `Ret. IVA Granos`, `Ret. Ventas Hacienda`), el tipo de origen tal cual, marcado explícitamente como "origen fuera de alcance" — un tercer estado distinto de "no disponible" (clarificación 2026-09-16).
- **FR-009**: El sistema MUST NOT calcular ni mostrar imputación (rubro/centro de costo/destino) propia en cuentas corrientes; ese dato se consulta exclusivamente desde compras.
- **FR-010**: El sistema MUST operar exclusivamente en modo lectura: ninguna pantalla del módulo debe permitir crear, editar ni eliminar datos reales.
- **FR-011**: El sistema MUST consultar los datos exclusivamente desde SQL Server, sin acceder a bases Access ni fuentes locales duplicadas.
- **FR-012**: El sistema MUST mostrar un estado vacío explícito cuando un contacto no tenga movimientos, en lugar de una pantalla en blanco o error.
- **FR-013**: El sistema MUST distinguir visualmente los importes de deuda/débito de los de crédito/haber.
- **FR-014**: El sistema MUST evitar mostrar movimientos duplicados para contactos con más de un tipo asociado (por ejemplo, tipo "Multiple").
- **FR-015**: El sistema MUST soportar sesiones de lectura concurrentes de múltiples usuarios sin degradar ni bloquear la consulta de otros usuarios, consistente con la misma exigencia definida para compras (`specs/002-compras`) y tesorería (`specs/003-tesoreria`).

### Key Entities *(include if feature involves data)*

- **Contacto**: proveedor, cliente, banco, empleado u otro tercero con relación de cuenta corriente. Atributos clave: identificador, razón social, tipo de contacto.
- **Movimiento de cuenta corriente**: registro que afecta el saldo de un contacto. Atributos clave: fecha, documento, deuda, crédito, `Origen` (tipo: compra/tesorería/otro) e `IdOrigen` (identificador directo del registro de origen).
- **Referencia a compra**: vínculo directo, vía `IdOrigen`, hacia una compra del módulo de compras (documento, proveedor), sin traer su imputación, que se consulta allí.
- **Referencia a movimiento de tesorería**: vínculo directo, vía `IdOrigen`, hacia un movimiento del módulo de tesorería (banco/caja/medio, fecha, importe).
- **Referencia fuera de alcance**: caso donde `Origen` es un valor real (confirmado: `Alquileres`, `Impuestos`, `Remuneraciones`, `Retenciones`, `Ret. IVA Granos`, `Ret. Ventas Hacienda`) que no corresponde a ningún módulo dentro del alcance actual; se muestra el tipo tal cual, sin navegación.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un usuario puede encontrar el saldo actual de un contacto conocido en menos de 30 segundos desde que abre el módulo.
- **SC-002**: El 100% de los movimientos de cuenta corriente consultados indican su origen (compra, tesorería, "fuera de alcance", o "no disponible"), sin ambigüedad.
- **SC-003**: El 100% de las consultas de saldo mostradas coinciden con el saldo calculado por las vistas de origen en SQL Server (sin discrepancias).
- **SC-004**: Ningún dato de imputación (rubro/centro de costo/destino) se muestra ni se deriva desde cuentas corrientes; ese dato se obtiene únicamente desde compras.
- **SC-005**: Ningún usuario puede modificar, crear ni eliminar datos reales desde el módulo (verificable por ausencia de cualquier acción de escritura en la interfaz).

## Assumptions

- Los usuarios de este módulo son personal administrativo interno de La Herencia, con acceso ya autorizado; el diseño no debe impedir agregar más de un usuario concurrente en el futuro, aunque roles y permisos específicos se definen en una etapa posterior.
- El cálculo de saldo se basa en las vistas ya existentes en SQL Server (`vw_MovimientosCuenta_Base`, `vw_MovimientosCuenta_Saldo`) como fuente de verdad, evitando recalcular reglas de negocio ya resueltas en la base.
- El módulo es de solo lectura en esta primera versión; cualquier capacidad de registrar movimientos requerirá una especificación y autorización separadas, conforme a la constitución del proyecto.
- Este módulo depende de que los módulos de compras (`specs/002-compras`) y tesorería (`specs/003-tesoreria`) existan como referencia de navegación; si alguno de los dos no está implementado aún, cuentas corrientes debe mostrar la referencia igualmente (documento/datos básicos) sin exigir que la pantalla de destino ya exista.
- El volumen de datos a mostrar es el observado en el prototipo (miles de movimientos), por lo que las listas deben soportar paginación o desplazamiento sin degradar la experiencia.
- Integraciones fiscales (AFIP/ARCA) quedan fuera de alcance de esta primera versión.
