# Feature Specification: Cuentas corrientes y tesorería (solo lectura)

**Feature Branch**: `001-cuentas-tesoreria`

**Created**: 2026-09-15

**Status**: Draft

**Input**: User description: "Diseñar el módulo web de cuentas corrientes y tesorería en modo solo lectura, usando Python, SQL Server, Next.js, TypeScript, Tailwind CSS y TanStack Query. Debe permitir seleccionar proveedor/cliente, consultar saldo y movimientos trazables, seleccionar banco/cuenta/caja y revisar movimientos financieros. No modificar datos reales."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Consultar cuenta corriente de un proveedor/cliente (Priority: P1)

Un usuario administrativo necesita seleccionar un contacto (proveedor, cliente u otro tipo registrado) y ver su saldo actual junto con el detalle de movimientos que lo componen, para responder preguntas de deuda/crédito sin recurrir al sistema anterior.

**Why this priority**: Es el caso de uso más frecuente del área administrativa y el que actualmente requiere consultar Access o el sistema VB.NET original. Sin esto no hay valor mínimo entregado.

**Independent Test**: Puede probarse seleccionando un contacto existente (por ejemplo "Rutas Sur Atlantico S.A.") y verificando que el saldo mostrado coincide con la suma de movimientos (deuda/crédito) trazables hasta ese contacto.

**Acceptance Scenarios**:

1. **Given** el usuario está en el módulo de cuentas corrientes, **When** busca y selecciona un contacto por razón social, **Then** el sistema muestra el saldo actual del contacto y la lista de movimientos que lo componen, ordenados por fecha.
2. **Given** un contacto sin movimientos registrados, **When** el usuario lo selecciona, **Then** el sistema muestra saldo cero y un estado vacío claro en la lista de movimientos.
3. **Given** el usuario está viendo el detalle de un movimiento, **When** consulta su origen (compra, operación, tesorería), **Then** el sistema muestra la referencia al documento/operación de origen que generó ese movimiento.

---

### User Story 2 - Consultar movimientos de tesorería por banco/cuenta/caja (Priority: P2)

Un usuario administrativo necesita seleccionar una combinación de cuenta y caja (por ejemplo banco y cuenta bancaria, o caja en efectivo) y revisar los movimientos financieros asociados, para controlar el estado de fondos disponibles.

**Why this priority**: Es el segundo flujo más usado del prototipo actual (tesorería, BNA, Galicia) y depende de datos ya identificados en SQL Server, pero es menos crítico que el saldo de un contacto puntual.

**Independent Test**: Puede probarse seleccionando la combinación cuenta "Blue" / caja "La Herencia" (ya validada en el prototipo) y verificando que se listan los movimientos correspondientes con fecha, importe y contacto asociado.

**Acceptance Scenarios**:

1. **Given** el usuario está en el módulo de tesorería, **When** selecciona una combinación de cuenta y caja, **Then** el sistema muestra los movimientos de esa combinación ordenados por fecha, con importe y contacto relacionado cuando exista.
2. **Given** el usuario está viendo movimientos de tesorería, **When** aplica un filtro por rango de fechas, **Then** la lista se actualiza mostrando solo los movimientos dentro de ese rango.
3. **Given** una combinación de cuenta/caja sin movimientos en el período filtrado, **When** el usuario consulta, **Then** el sistema muestra un estado vacío claro sin error.

---

### User Story 3 - Navegar desde un movimiento hacia su trazabilidad completa (Priority: P3)

Un usuario administrativo, estando en un movimiento de cuenta corriente o tesorería, necesita seguir la referencia hacia el documento u operación que lo originó (compra, venta, pago) para auditar el proceso de negocio completo.

**Why this priority**: Agrega valor de auditoría y confianza en los datos, pero el sistema ya entrega valor con P1 y P2 sin esta navegación cruzada.

**Independent Test**: Puede probarse tomando un movimiento de cuenta corriente originado en una compra y verificando que el usuario puede navegar al detalle de esa compra sin salir del módulo.

**Acceptance Scenarios**:

1. **Given** un movimiento de cuenta corriente con origen en una compra, **When** el usuario selecciona "ver origen", **Then** el sistema navega al detalle de esa compra.
2. **Given** un movimiento de tesorería vinculado a un contacto, **When** el usuario selecciona el contacto, **Then** el sistema navega a la cuenta corriente de ese contacto.

### Edge Cases

- ¿Qué sucede si un contacto tiene múltiples tipos (por ejemplo "Multiple") y aparece tanto en compras como en tesorería? El sistema debe mostrar todos sus movimientos combinados sin duplicarlos.
- ¿Cómo maneja el sistema un movimiento cuyo origen (compra/operación) fue eliminado o no es accesible? Debe mostrar el movimiento igualmente, indicando que el origen no está disponible, sin bloquear la consulta.
- ¿Qué sucede si la búsqueda de contacto no encuentra resultados? El sistema debe mostrar un mensaje claro de "sin resultados" y permitir reintentar la búsqueda.
- ¿Cómo se muestran importes negativos o saldos a favor del contacto (crédito) versus en contra (deuda)? Deben distinguirse visualmente de forma inequívoca.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST permitir buscar y seleccionar un contacto (proveedor, cliente u otro tipo) por razón social o identificador.
- **FR-002**: El sistema MUST mostrar el saldo actual de un contacto seleccionado, calculado a partir de sus movimientos de cuenta corriente.
- **FR-003**: El sistema MUST listar los movimientos de cuenta corriente de un contacto, ordenados por fecha, mostrando como mínimo fecha, documento, deuda/crédito y origen.
- **FR-004**: El sistema MUST permitir consultar el documento u operación de origen de un movimiento de cuenta corriente cuando dicho origen exista y sea accesible.
- **FR-005**: El sistema MUST permitir seleccionar una combinación de cuenta y caja para consultar movimientos de tesorería.
- **FR-006**: El sistema MUST listar los movimientos de tesorería de la combinación cuenta/caja seleccionada, mostrando como mínimo fecha, importe y contacto asociado cuando exista.
- **FR-007**: El sistema MUST permitir filtrar movimientos de tesorería por rango de fechas.
- **FR-008**: El sistema MUST operar exclusivamente en modo lectura: ninguna pantalla del módulo debe permitir crear, editar ni eliminar datos reales.
- **FR-009**: El sistema MUST consultar los datos exclusivamente desde SQL Server, sin acceder a bases Access ni fuentes locales duplicadas.
- **FR-010**: El sistema MUST mostrar un estado vacío explícito cuando un contacto o combinación cuenta/caja no tenga movimientos, en lugar de una pantalla en blanco o error.
- **FR-011**: El sistema MUST distinguir visualmente los importes de deuda/débito de los de crédito/haber en cuentas corrientes y tesorería.

### Key Entities *(include if feature involves data)*

- **Contacto**: proveedor, cliente, banco, empleado u otro tercero con el que existe relación de cuenta corriente. Atributos clave: identificador, razón social, tipo de contacto.
- **Movimiento de cuenta corriente**: registro que afecta el saldo de un contacto. Atributos clave: fecha, documento, deuda, crédito, origen (compra, operación, tesorería u otro), referencia al documento de origen.
- **Cuenta/Caja**: combinación que identifica un fondo (banco/cuenta bancaria o caja en efectivo) sobre el que se registran movimientos de tesorería.
- **Movimiento de tesorería**: registro de ingreso o egreso de fondos en una cuenta/caja. Atributos clave: fecha, importe, contacto asociado (si existe), referencia a la operación relacionada.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un usuario puede encontrar el saldo actual de un contacto conocido en menos de 30 segundos desde que abre el módulo.
- **SC-002**: Un usuario puede identificar el origen de cualquier movimiento de cuenta corriente o tesorería sin salir del módulo, en el 100% de los casos donde el origen esté disponible.
- **SC-003**: El 100% de las consultas de saldo mostradas coinciden con el saldo calculado por las vistas de origen en SQL Server (sin discrepancias).
- **SC-004**: Ningún usuario puede modificar, crear ni eliminar datos reales desde el módulo (verificable por ausencia de cualquier acción de escritura en la interfaz).

## Assumptions

- Los usuarios de este módulo son personal administrativo interno de La Herencia, con acceso ya autorizado al sistema (no se define aquí un nuevo esquema de autenticación).
- El cálculo de saldo se basa en las vistas ya existentes en SQL Server (`vw_MovimientosCuenta_Base`, `vw_MovimientosCuenta_Saldo`) como fuente de verdad, evitando recalcular reglas de negocio ya resueltas en la base.
- El módulo es de solo lectura en esta primera versión; cualquier capacidad de registrar movimientos requerirá una especificación y autorización separadas, conforme a la constitución del proyecto.
- La navegación hacia compras, operaciones u otras pantallas de origen asume que esas pantallas existen o serán construidas en módulos relacionados; si no existen aún, se muestra la referencia sin navegación activa.
- El volumen de datos a mostrar es el observado en el prototipo (miles de compras y movimientos), por lo que las listas deben soportar paginación o desplazamiento sin degradar la experiencia.
