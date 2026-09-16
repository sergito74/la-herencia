# Feature Specification: Impuestos, remuneraciones, arrendamientos y ventas de hacienda (solo lectura)

**Feature Branch**: `005-egresos-y-ventas-menores`

**Created**: 2026-09-16

**Status**: Draft

**Input**: User description: "Consultar y navegar (solo lectura) los movimientos de Impuestos, Remuneraciones, Arrendamientos y Ventas de Hacienda, cerrando los estados 'fuera_de_alcance' que hoy devuelve el origen_resolver de cuentas corrientes (specs/004-cuentas-corrientes). Debe permitir: (1) listar/consultar movimientos de cada dominio con su contacto asociado cuando exista, (2) desde cuentas corrientes, un movimiento con Origen en {Impuestos, Remuneraciones, Alquileres, Retenciones, Ret. Ventas Hacienda} debe resolver a una referencia real hacia el registro de origen correspondiente. Igual que 002-004: 100% read-only, contract-first, tests, sin imputación cruzada."

## Clarifications

### Session 2026-09-16

- Q: El plan original de roadmap proponía cerrar 4 de los 6 estados `fuera_de_alcance` de cuentas corrientes (`Alquileres`, `Impuestos`, `Remuneraciones`, `Ret. Ventas Hacienda`), dejando `Retenciones` fuera. Pero la tabla `Retenciones` (retenciones impositivas genéricas) pertenece al mismo dominio de Impuestos que ya se va a construir en este módulo. → A: Se incluye `Retenciones` en el alcance de este módulo junto con `Impuestos`/`Tipo Impuesto` — cierra 5 de los 6 estados `fuera_de_alcance`. Solo `Ret. IVA Granos` queda pendiente porque es específico del dominio de Agricultura (fase posterior del roadmap).
- Q: Contra datos reales, `Venta Hacienda` tiene un consignatario único por venta (`IdConsignatario`, el intermediario que gestiona la venta) pero puede tener varios compradores distintos en sus líneas de detalle (`Det_Ventas Hacienda.IdComprador`) — se confirmaron casos reales con más de un comprador por venta. ¿Cómo se muestra esto? → A: El consignatario se muestra a nivel de la venta (cabecera); el comprador se muestra por línea de detalle, reflejando que una misma venta puede repartirse entre varios compradores.
- Q: `Remuneraciones` (la liquidación, a la que apunta `Origen`/`IdOrigen` de cuentas corrientes) y `Pagos Remuneraciones` (pagos efectivos por empleado, con su propia cuenta/caja) no están vinculadas por FK entre sí, pero representan el mismo ciclo liquidación→pago que ya se modela para Arrendamientos (contrato + cobros). ¿Remuneraciones debe seguir el mismo patrón? → A: Sí — se muestra la liquidación junto con sus pagos asociados (por empleado y período), igual que Arrendamientos muestra el contrato junto con sus cobros. **[CORREGIDO 2026-09-17, ver más abajo]**: al implementar, se confirmó contra datos reales que `Pagos Remuneraciones.IdEmpleado` no es una FK hacia `Contactos` (verificación insuficiente en esta sesión de clarificación) — se revierte a listado independiente, mismo criterio aplicado a las retenciones de venta de hacienda.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Consultar movimientos de Impuestos y Retenciones (Priority: P1)

Un usuario administrativo necesita ver los movimientos de impuestos y retenciones pagados o adeudados, con su tipo y monto, para responder consultas fiscales sin recurrir al sistema anterior.

**Why this priority**: Es uno de los seis huecos "fuera de alcance" ya identificados en cuentas corrientes; cerrar este de forma independiente ya entrega valor (visibilidad fiscal) aunque los otros dominios de este spec no estén listos todavía.

**Independent Test**: Puede probarse listando los movimientos de impuestos de un período conocido y verificando que aparecen con tipo de impuesto, fecha e importe.

**Acceptance Scenarios**:

1. **Given** el usuario está en el módulo de impuestos, **When** consulta los movimientos, **Then** el sistema muestra fecha, tipo de impuesto, importe y contacto/organismo asociado cuando exista.
2. **Given** no hay movimientos de impuestos para el filtro aplicado, **When** el usuario consulta, **Then** el sistema muestra un estado vacío explícito.

---

### User Story 2 - Consultar liquidaciones de Remuneraciones y pagos efectivos (Priority: P1)

Un usuario administrativo necesita ver las liquidaciones de remuneraciones de cada empleado, y consultar por separado los pagos efectivos de remuneraciones registrados, para verificar montos y períodos sin recurrir al sistema anterior.

**Why this priority**: Cierra otro de los seis huecos "fuera de alcance"; es independiente de los demás dominios de este spec.

**Independent Test**: Puede probarse listando las liquidaciones de un contacto tipo "Empleado" conocido, y por separado listando los pagos de remuneraciones registrados.

**Acceptance Scenarios**:

1. **Given** el usuario está en el módulo de remuneraciones, **When** consulta las liquidaciones de un empleado, **Then** el sistema muestra fecha, período liquidado, empleado (contacto) e importe.
2. **Given** una liquidación de remuneración sin empleado identificado, **When** el usuario la consulta, **Then** el sistema la muestra igual, indicando explícitamente que el contacto no está disponible.
3. **Given** el usuario está en el listado de pagos de remuneraciones, **When** lo consulta, **Then** el sistema muestra cada pago (fecha, cuenta/caja, importe) sin intentar vincularlo a un empleado ni a una liquidación específica — no existe una clave confiable para esa relación (confirmado contra datos reales: `Pagos Remuneraciones.IdEmpleado` no es una FK hacia `Contactos`).

---

### User Story 3 - Consultar movimientos de Arrendamientos (Priority: P1)

Un usuario administrativo necesita ver los contratos de arrendamiento (alquileres) y sus cobros/pagos asociados, para verificar el estado de cada contrato sin recurrir al sistema anterior.

**Why this priority**: Cierra otro hueco "fuera de alcance"; los contratos de arrendamiento son una fuente de ingresos/egresos recurrente que hoy es invisible en el sistema nuevo.

**Independent Test**: Puede probarse listando los alquileres de un contacto conocido (arrendador o arrendatario) y verificando que se muestran sus detalles y cobros asociados.

**Acceptance Scenarios**:

1. **Given** el usuario está en el módulo de arrendamientos, **When** consulta un contrato, **Then** el sistema muestra el detalle del alquiler y sus cobros asociados, con fechas e importes.
2. **Given** un contrato de alquiler sin cobros registrados todavía, **When** el usuario lo consulta, **Then** el sistema muestra el contrato con un estado vacío explícito en la sección de cobros.

---

### User Story 4 - Consultar movimientos de Ventas de Hacienda (Priority: P1)

Un usuario administrativo necesita ver las ventas de hacienda realizadas, con su detalle por comprador, y consultar por separado las retenciones sobre ventas de hacienda registradas, para verificar el resultado comercial sin recurrir al sistema anterior.

**Why this priority**: Cierra el hueco "fuera de alcance" de `Ret. Ventas Hacienda`; cubre únicamente el lado comercial de la venta (no hay manejo sanitario/rodeo en el alcance de este sistema — no existe ese dato en ningún lado).

**Independent Test**: Puede probarse listando las ventas de hacienda de un período conocido y verificando que se muestra el detalle de cada venta por comprador, y listando por separado las retenciones de venta de hacienda de un contacto conocido.

**Acceptance Scenarios**:

1. **Given** el usuario está en el módulo de ventas de hacienda, **When** consulta una venta, **Then** el sistema muestra fecha, consignatario (contacto que gestionó la venta), y el detalle de la venta línea por línea, cada una con su propio comprador (contacto), tipo de hacienda, cantidad y los precios unitarios registrados (confirmado contra datos reales: existen dos precios unitarios por línea sin una regla clara de cuál es "el" importe final — se muestran ambos tal cual, sin calcular un total).
2. **Given** una venta de hacienda con líneas de detalle de más de un comprador, **When** el usuario la consulta, **Then** el sistema muestra cada línea con su comprador correspondiente, sin mezclar ni promediar entre compradores.
3. **Given** el usuario está en el listado de retenciones de venta de hacienda, **When** filtra por contacto, **Then** el sistema muestra las retenciones de ese contacto (fecha, documento, importe), sin intentar vincularlas a una venta específica — no existe una clave confiable para esa relación (confirmado contra datos reales).

---

### User Story 5 - Navegar desde cuentas corrientes hacia estos orígenes (Priority: P1)

Un usuario administrativo, viendo un movimiento de cuenta corriente marcado hoy como "origen fuera de alcance" (`Alquileres`, `Impuestos`, `Remuneraciones`, `Retenciones`, `Ret. Ventas Hacienda`), necesita ver la referencia real a su origen, igual que ya sucede con compras y tesorería.

**Why this priority**: Cierra el círculo de trazabilidad que motivó todo el roadmap — sin esto, cuentas corrientes sigue mostrando "fuera de alcance" para más de la mitad de sus valores de `Origen` reales, contradiciendo el objetivo de auditoría de punta a punta.

**Independent Test**: Puede probarse tomando un movimiento de cuenta corriente con cada uno de los 5 valores de `Origen` cubiertos y verificando que el sistema muestra la referencia real (no "fuera de alcance") hacia el registro correspondiente en el dominio nuevo.

**Acceptance Scenarios**:

1. **Given** un movimiento de cuenta corriente con `Origen = "Impuestos"` o `"Retenciones"`, **When** el usuario lo consulta desde cuentas corrientes, **Then** el sistema muestra la referencia al movimiento de impuesto/retención correspondiente.
2. **Given** un movimiento de cuenta corriente con `Origen = "Remuneraciones"`, **When** el usuario lo consulta, **Then** el sistema muestra la referencia al pago de remuneración correspondiente.
3. **Given** un movimiento de cuenta corriente con `Origen = "Alquileres"`, **When** el usuario lo consulta, **Then** el sistema muestra la referencia al contrato/cobro de alquiler correspondiente.
4. **Given** un movimiento de cuenta corriente con `Origen = "Ret. Ventas Hacienda"`, **When** el usuario lo consulta, **Then** el sistema muestra la referencia a la venta de hacienda correspondiente.
5. **Given** un movimiento de cuenta corriente con `Origen = "Ret. IVA Granos"`, **When** el usuario lo consulta, **Then** el sistema lo sigue mostrando como "origen fuera de alcance" (dominio de Agricultura, fuera de este spec).

### Edge Cases

- ¿Qué sucede si un movimiento de impuesto/remuneración/alquiler/venta de hacienda no tiene contacto asociado (ej. un impuesto pagado directamente a un organismo sin registrar como contacto)? El sistema debe mostrarlo igual, indicando explícitamente que el contacto no está disponible, sin bloquear la consulta.
- ¿Qué sucede si el `IdOrigen` de un movimiento de cuenta corriente apunta a un registro de estos dominios que ya no existe? El sistema debe indicarlo como "no disponible" (mismo comportamiento que 004 para compras/tesorería), no como error.
- ¿Cómo se distingue un movimiento de "Ret. Ventas Hacienda" (retención sobre una venta) de la venta de hacienda en sí? Deben poder consultarse ambos, y la referencia desde cuentas corrientes debe dejar claro cuál de los dos es.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST permitir listar y consultar movimientos de impuestos/retenciones, mostrando como mínimo fecha, tipo, importe y contacto/organismo asociado cuando exista.
- **FR-002**: El sistema MUST permitir listar y consultar liquidaciones de remuneraciones, mostrando como mínimo fecha, período liquidado, empleado (contacto) e importe liquidado. El sistema MUST además permitir listar por separado los pagos efectivos de remuneraciones (fecha, cuenta/caja, importe pagado), sin forzar una relación con un empleado o liquidación específica (confirmado contra datos reales: `Pagos Remuneraciones.IdEmpleado` no es una FK hacia `Contactos` — sus valores no coinciden con los empleados reales de `Remuneraciones.IdContacto`).
- **FR-003**: El sistema MUST permitir listar y consultar contratos de arrendamiento con su detalle y cobros asociados, mostrando como mínimo contacto, fechas e importes.
- **FR-004**: El sistema MUST permitir listar y consultar ventas de hacienda mostrando, a nivel de venta, fecha y consignatario (contacto que gestionó la venta), y a nivel de cada línea de detalle, comprador (contacto), tipo de hacienda, cantidad y los dos precios unitarios registrados (confirmado contra datos reales: `Det_Ventas Hacienda` tiene dos columnas de precio unitario pobladas en casi todas las filas, sin una regla clara sobre cómo se combinan en un único importe — el sistema MUST NOT inventar ese cálculo, MUST mostrar ambos valores tal cual). El sistema MUST además permitir listar y consultar por separado las retenciones de venta de hacienda (fecha, contacto, documento, importe), sin forzar una relación con una venta específica cuando no exista una clave confiable para establecerla (confirmado contra datos reales: `Retenciones Ventas Hacienda` no tiene columna de venta y su contacto no siempre coincide con un comprador de la venta).
- **FR-005**: El sistema MUST resolver, para cada movimiento de cuenta corriente con `Origen` en `{Impuestos, Remuneraciones, Alquileres, Retenciones, Ret. Ventas Hacienda}`, una referencia real hacia el registro de origen correspondiente en el dominio respectivo, reemplazando el estado `fuera_de_alcance` que devuelve hoy `origen_resolver.py` (specs/004-cuentas-corrientes) para esos 5 valores.
- **FR-006**: El sistema MUST seguir devolviendo `fuera_de_alcance` para `Ret. IVA Granos` (dominio de Agricultura, fuera de este spec).
- **FR-007**: El sistema MUST NOT calcular ni mostrar imputación (rubro/centro de costo/destino) cruzada entre estos dominios y compras; cada dominio muestra únicamente sus propios datos.
- **FR-008**: El sistema MUST operar exclusivamente en modo lectura: ninguna pantalla de estos módulos debe permitir crear, editar ni eliminar datos reales.
- **FR-009**: El sistema MUST consultar los datos exclusivamente desde SQL Server, sin acceder a bases Access ni fuentes locales duplicadas.
- **FR-010**: El sistema MUST mostrar un estado vacío explícito cuando un dominio no tenga movimientos para el filtro aplicado, en lugar de una pantalla en blanco o error.
- **FR-011**: El sistema MUST soportar sesiones de lectura concurrentes de múltiples usuarios sin degradar ni bloquear la consulta de otros usuarios, consistente con la misma exigencia definida para compras/tesorería/cuentas corrientes.

### Key Entities *(include if feature involves data)*

- **Impuesto/Retención**: movimiento fiscal (pago o retención), con tipo, fecha, importe y organismo/contacto asociado cuando exista.
- **Remuneración (liquidación)**: liquidación periódica de un contacto tipo "Empleado", con fecha, período e importe.
- **Pago de Remuneración**: entidad independiente (fecha, cuenta/caja, importe); no tiene una relación confiable hacia un empleado ni hacia una liquidación específica en los datos reales, por lo que se consulta por separado, no como sub-lista de una liquidación.
- **Arrendamiento**: contrato de alquiler con detalle (condiciones, contacto) y sus cobros asociados (fecha, importe).
- **Venta de Hacienda**: venta comercial de hacienda con un consignatario (contacto que gestiona la venta) a nivel de cabecera, y una o más líneas de detalle cada una con su propio comprador (contacto), tipo de hacienda y cantidad.
- **Retención de Venta de Hacienda**: entidad independiente (fecha, contacto, documento, importe); no tiene una relación confiable hacia una venta específica en los datos reales, por lo que se consulta por separado, no como sub-lista de una venta.
- **Referencia resuelta (ampliación de 004)**: nuevos casos de la referencia de origen de cuentas corrientes — `tipo: "impuesto"`, `"retencion"`, `"remuneracion"`, `"arrendamiento"`, `"venta_hacienda"` — cada uno con los campos mínimos de su dominio (ver arriba), análogos a los casos `compra`/`tesoreria` ya existentes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un usuario puede encontrar el detalle de un movimiento conocido de cualquiera de los 4 dominios en menos de 30 segundos desde que abre el módulo correspondiente.
- **SC-002**: De los 6 valores de `Origen` que cuentas corrientes marca hoy como `fuera_de_alcance`, 5 (`Alquileres`, `Impuestos`, `Remuneraciones`, `Retenciones`, `Ret. Ventas Hacienda`) resuelven a una referencia real; solo `Ret. IVA Granos` permanece `fuera_de_alcance`.
- **SC-003**: Ningún usuario puede modificar, crear ni eliminar datos reales desde estos módulos (verificable por ausencia de cualquier acción de escritura en la interfaz).
- **SC-004**: El 100% de los movimientos consultados en cada dominio muestran sus campos mínimos sin errores, incluyendo los casos sin contacto asociado (mostrados explícitamente, no omitidos).

## Assumptions

- Los usuarios de estos módulos son el mismo personal administrativo interno ya definido en 002/003/004; no se introducen roles ni permisos nuevos.
- El módulo de ventas de hacienda cubre únicamente el lado comercial (venta, detalle, retenciones); no incluye manejo sanitario, identificación animal ni rodeo, porque esos datos no existen en ningún origen hoy (confirmado con el usuario).
- Cuando un dominio no tenga una relación directa y confiable con `Contactos` (por ejemplo, un impuesto pagado a un organismo no registrado como contacto), el sistema muestra el dato igual, sin forzar una relación inexistente.
- El volumen de datos es comparable al ya observado en compras/tesorería/cuentas corrientes; las listas deben soportar paginación sin degradar la experiencia.
- **Confirmado contra `INFORMATION_SCHEMA` y datos reales (2026-09-16)**: en las 5 tablas cuyo `IdOrigen` referencia cuentas corrientes, el vínculo es una clave primaria directa (sin intermediarios): `Impuestos.IdImpuesto`, `Retenciones.IdRetencionSQL`, `Remuneraciones.IdSalario`, `Alquileres.IdAlquiler`, `Retenciones Ventas Hacienda.Id`. `Impuestos.IdOrganismo` y `Pagos Remuneraciones.IdEmpleado` son claves foráneas hacia `Contactos.IdContacto` (organismo tipo "Organismo", empleado tipo "Empleado" respectivamente). No existe un valor de `Origen` para la venta de hacienda en sí (solo para su retención) — el vínculo de cuentas corrientes hacia una venta de hacienda es indirecto (vía la retención), no directo. Además, se confirmó que `Retenciones Ventas Hacienda` no tiene columna `IdVenta` ni un `IdContacto` que siempre coincida con un comprador de `Det_Ventas Hacienda` — por lo tanto las retenciones se modelan y consultan como entidad independiente, no como sub-lista de una venta.
- **Corrección durante implementación (2026-09-17)**: la verificación de `/speckit-clarify` sobre `Pagos Remuneraciones.IdEmpleado` como FK hacia `Contactos` fue insuficiente (solo confirmó 3 filas con IDs bajos, sin validar `Tipo Contacto`). Al implementar se confirmó que es incorrecta: `IdEmpleado` va de 1 a 6 y resuelve a contactos tipo "Proveedor", mientras que los empleados reales de `Remuneraciones.IdContacto` van de 46 a 632. `Pago de Remuneración` se modela como entidad independiente, igual que `Retención de Venta de Hacienda`. Lección para futuras specs: verificar el `Tipo Contacto` resultante de un join, no solo que el join no falle.
- Este módulo depende de que `specs/004-cuentas-corrientes` exista (ya migrado) para ampliar su `origen_resolver.py`; no depende de Agricultura ni de Bancos/Tarjetas (fases posteriores del roadmap).
