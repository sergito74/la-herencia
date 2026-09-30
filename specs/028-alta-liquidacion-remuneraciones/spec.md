# Feature Specification: Alta de liquidación de remuneraciones

**Feature Branch**: `028-alta-liquidacion-remuneraciones`

**Created**: 2026-09-30

**Status**: Draft

**Input**: User description: "Alta de liquidación de remuneraciones (028): un flujo para cargar una liquidación mensual nueva de un empleado — subir el PDF del recibo de sueldo (se guarda en la carpeta real de Dropbox... con un nombre de archivo consistente...) y cargar en la misma pantalla los conceptos/importes de la liquidación (los ~15 conceptos monetarios de dbo.Remuneraciones...), eligiendo el empleado de un combo de Contactos tipo Empleado. Es la primera escritura del módulo Remuneraciones — hoy el router es 100% GET-only. Debe integrarse con lo ya construido: el listado de liquidaciones (con gating por empleado) y el endpoint de recibo. El alta debe escribir contra WC (nunca LaHerencia), con backup verificado, siguiendo el patrón ya usado en otros módulos de alta."

## Clarifications

### Session 2026-09-30

- Q: Cuando se cargan los conceptos de descuento (Jubilación, Obra Social, Aporte Sindical, Ley 19032, Servicio de Sepelio) en el formulario nuevo, ¿se ingresan como importe positivo tal como aparecen en el recibo de sueldo? → A: Sí, todo en positivo (como en el recibo) — el formulario resta internamente los conceptos de descuento para calcular el neto, igual que ya hace `vw_MovimientosCuenta_Base`, y de paso se corrige el bug del listado existente (`_IMPORTE_SQL`) para que muestre el neto real en vez de sumar descuentos como si fueran ganancias.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cargar una liquidación mensual nueva (Priority: P1)

Quien administra Personal recibe cada mes, de la liquidadora de sueldos, los importes de la liquidación de cada empleado (sueldo básico, antigüedad, aguinaldo, retenciones, etc.). Hoy esos datos solo se pueden ver (el módulo Remuneraciones es 100% de lectura) — no hay forma de cargar la liquidación del mes actual sin tocar la base de datos directamente. Esta historia permite elegir un empleado ya existente, completar los importes de la liquidación del período y guardarla.

**Why this priority**: Sin esto no hay alta posible — es el corazón de la funcionalidad pedida; las demás historias son mejoras sobre esta base.

**Independent Test**: Elegir un empleado existente, completar fecha de pago + período + al menos un concepto monetario, guardar, y verificar que la liquidación aparece en el listado existente (`RemuneracionesListado`) con el importe calculado correcto.

**Acceptance Scenarios**:

1. **Given** un empleado (Contacto tipo Empleado) ya existente en el sistema, **When** se completa fecha de pago, período liquidado y los importes de los conceptos monetarios (todos en positivo) y se guarda, **Then** la liquidación queda persistida en `WC` y visible en el listado de liquidaciones filtrado por ese empleado, con el importe neto correcto (haberes menos descuentos, ver Clarifications).
2. **Given** un formulario de alta a medio completar, **When** no se eligió ningún empleado, **Then** el sistema no permite guardar y señala que el empleado es obligatorio.
3. **Given** una liquidación ya cargada para un empleado en un período determinado, **When** se intenta cargar otra liquidación para el mismo empleado y el mismo período, **Then** el sistema avisa que ya existe una liquidación para ese período antes de guardar, pero permite continuar si la persona confirma (hay casos reales de más de un pago legítimo en el mismo período — ver Assumptions).

---

### User Story 2 - Adjuntar el PDF del recibo al cargar la liquidación (Priority: P2)

En la misma pantalla de alta, quien carga la liquidación puede adjuntar el PDF del recibo de sueldo ya firmado/escaneado, para no tener que copiarlo a mano después a la carpeta correspondiente con el nombre correcto.

**Why this priority**: Complementa la historia 1 — el dato numérico es lo esencial, el PDF puede llegar unos días después (la liquidadora manda los números antes que el escaneo firmado), así que se modela como un paso que puede ir junto o después, nunca bloqueante.

**Independent Test**: Con una liquidación ya cargada (con o sin PDF), adjuntar un PDF y verificar que el link "Recibo" del listado existente lo abre correctamente.

**Acceptance Scenarios**:

1. **Given** el formulario de alta con los datos de la liquidación completos, **When** se adjunta un archivo PDF del recibo antes de guardar, **Then** el archivo se guarda en la carpeta real de recibos (dentro de la carpeta del año correspondiente) con un nombre que el sistema pueda encontrar después sin ambigüedad, y la liquidación guardada queda con ese recibo ya vinculado.
2. **Given** una liquidación ya guardada sin PDF adjunto, **When** se sube el PDF después desde el listado existente, **Then** el recibo queda vinculado a esa liquidación y aparece disponible en el link "Recibo".
3. **Given** un archivo que no es PDF, **When** se intenta adjuntar, **Then** el sistema lo rechaza con un mensaje claro y no guarda nada.

---

### Edge Cases

- ¿Qué pasa si se elige un contacto que no es de tipo Empleado? El combo de selección solo debe ofrecer contactos tipo Empleado (mismo patrón que el resto de la app), así que esto no debería llegar a ocurrir desde la UI.
- ¿Qué pasa si todos los conceptos monetarios quedan en cero? Se permite guardar (puede ser una liquidación real en $0, ej. licencia sin goce de sueldo) — no hay validación de importe mínimo.
- ¿Qué pasa si la fecha de pago es futura? Se permite — las liquidaciones a veces se cargan por adelantado.
- ¿Qué pasa si el PDF subido pesa varios MB (escaneo de mala calidad)? El sistema debe rechazar archivos por encima de un límite razonable (ver SC-004) con un mensaje claro, no fallar en silencio.
- ¿Qué pasa si dos personas cargan la misma liquidación al mismo tiempo? Fuera de alcance (uso mono-usuario de esta app, mismo criterio que el resto de los módulos de alta).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST permitir elegir el empleado de una liquidación nueva de entre los Contactos existentes de tipo Empleado (combo de búsqueda, mismo componente ya usado en Compras/Arrendamientos/Ventas/Remuneraciones lectura) — nunca da de alta un contacto nuevo desde acá.
- **FR-002**: El sistema MUST permitir cargar fecha de pago, período liquidado (texto) y el importe de cada uno de los conceptos monetarios existentes en `dbo.Remuneraciones` (Sueldo básico, Antigüedad, Adic. futuros aumentos, Día Gremio, Aguinaldo, Vacaciones, Ajuste, Ajuste No Remunerativo, Jubilación, Ley 19032, Obra Social, Obra Social Acuerdos, Aporte Sindical, Servicio de Sepelio, Redondeo, Bonificación adicional), cada uno opcional (por defecto $0), siempre como importe positivo tal como figura en el recibo de sueldo (ver Clarifications).
- **FR-003**: El sistema MUST guardar la liquidación nueva exclusivamente contra `WC` (nunca `LaHerencia`), reusando el patrón de escritura ya validado en otros módulos de alta.
- **FR-004**: El sistema MUST advertir, antes de guardar, si ya existe una liquidación para el mismo empleado y el mismo período liquidado — sin bloquear el guardado (hay pagos legítimos duplicados en el histórico real, ver Assumptions).
- **FR-005**: El sistema MUST permitir adjuntar un PDF del recibo de sueldo, tanto al momento de cargar la liquidación como después, sobre una liquidación ya existente.
- **FR-006**: El sistema MUST guardar el PDF adjuntado en la carpeta real de recibos de esta PC, dentro de la subcarpeta del año de la fecha de pago, con un nombre de archivo que incluya año, mes y el nombre del empleado de forma que quede vinculado sin ambigüedad.
- **FR-007**: El sistema MUST registrar la ruta del PDF guardado en la liquidación correspondiente (columna `Recibo`, mismo campo que ya lee el listado existente), de forma que el link "Recibo" del listado ya construido lo abra sin cambios adicionales.
- **FR-008**: El sistema MUST rechazar archivos adjuntos que no sean PDF, con un mensaje claro, antes de guardar cualquier dato.
- **FR-009**: El sistema MUST hacer disponible la liquidación recién creada en el listado de liquidaciones existente (`RemuneracionesListado`) inmediatamente después de guardar, sin pasos adicionales.
- **FR-010**: Esta feature NO cambia el esquema de `dbo.Remuneraciones` (la tabla y la columna `Recibo` ya existen) ni hace escrituras masivas — es una escritura de tarea normal contra `WC`, que la Constitución (Principio II) permite sin backup verificado por operación. Un backup verificado solo sería necesario si, en el camino, apareciera una necesidad real de cambio de esquema no prevista hoy.
- **FR-011**: El sistema MUST mantener sin cambios de comportamiento los endpoints de lectura existentes del módulo (listado de liquidaciones, listado de pagos, recibo) — esta es una extensión, no un reemplazo.
- **FR-012**: Este alcance NO incluye editar ni eliminar una liquidación ya cargada, ni dar de alta empleados nuevos — ambos quedan fuera de esta feature (ver Assumptions).
- **FR-013**: El sistema MUST ocultar o deshabilitar el alta de liquidaciones (y la carga de recibos) para usuarios con rol de solo lectura, mismo patrón ya aplicado a todos los demás botones de alta del sistema (ej. Cuentas de Socios).
- **FR-014**: El sistema MUST calcular y mostrar en pantalla, mientras se completa el formulario, el importe neto de la liquidación como la suma de los conceptos de haberes menos la suma de los conceptos de descuento (Jubilación, Ley 19032, Obra Social, Obra Social Acuerdos, Aporte Sindical, Servicio de Sepelio) — misma fórmula que ya usa `vw_MovimientosCuenta_Base` para la cuenta corriente del empleado, no la fórmula del listado existente (que hoy suma todo, incluidos los descuentos, sin restar — bug preexistente).
- **FR-015**: El sistema MUST corregir el cálculo de "Importe liquidado" que ya muestra el listado existente de liquidaciones para que reste los conceptos de descuento en vez de sumarlos, de forma que quede consistente con FR-014 y con la cuenta corriente del empleado.

### Key Entities *(include if feature involves data)*

- **Liquidación de remuneraciones**: una liquidación mensual de un empleado — quién (empleado), cuándo (fecha de pago, período liquidado), cuánto por cada concepto monetario, y opcionalmente la ruta al PDF del recibo escaneado. Es la entidad que ya expone en solo lectura el módulo Remuneraciones; esta feature agrega la capacidad de crearla.
- **Recibo (PDF)**: el documento escaneado/firmado de una liquidación, un archivo por liquidación, guardado en la carpeta real de recibos de esta PC.
- **Empleado**: un Contacto existente de tipo Empleado — esta feature solo lo selecciona, nunca lo crea ni lo edita.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Quien administra Personal puede cargar la liquidación completa de un empleado (todos los conceptos + PDF) en menos de 2 minutos, sin salir de la pantalla de Remuneraciones.
- **SC-002**: El 100% de las liquidaciones cargadas por esta vía aparecen en el listado existente con el importe total correcto, sin intervención manual adicional.
- **SC-003**: El 100% de los PDF adjuntados por esta vía se encuentran correctamente al abrir el link "Recibo" de esa liquidación, sin ambigüedad ni error 404.
- **SC-004**: Un archivo adjunto que no sea PDF, o que supere el límite de tamaño razonable para un recibo escaneado (10 MB), se rechaza antes de guardar cualquier dato, con un mensaje que explica el motivo.

## Assumptions

- Duplicar una liquidación para el mismo empleado y período es una situación real (ej. pagos "Extra" fuera de la liquidación normal, confirmado contra archivos reales del histórico) — el sistema advierte pero no bloquea, en vez de impedirlo.
- Cargar la liquidación numérica y adjuntar el PDF son dos pasos independientes que pueden hacerse juntos o por separado — no se exige el PDF para guardar la liquidación.
- El empleado siempre existe ya como Contacto tipo Empleado antes del alta de la liquidación; dar de alta empleados nuevos es un flujo aparte, fuera de esta feature.
- Editar o eliminar una liquidación ya cargada (por esta vía o heredada de Access) queda fuera de esta feature — si hace falta corregir un error de carga, es un pedido aparte.
- El nombre de archivo que genera el sistema para un PDF nuevo sigue un único formato consistente (a diferencia de los años del archivo histórico, que tienen formatos muy variados) — esto no cambia los nombres ya existentes en disco, solo estandariza los que esta feature genera de acá en adelante.
- "Período liquidado" sigue siendo un campo de texto libre (no un selector estricto de mes/año) — el histórico real incluye valores legítimos que no son un mes calendario (ej. "Jornal 26/09", "Agosto 2023 - Bono", "Diciembre 2021 (Extra)"), así que restringirlo a un picker de mes/año dejaría afuera casos reales. El sistema sugiere por defecto "Mes Año" a partir de la fecha de pago elegida, pero permite editarlo libremente. La verificación de duplicados (FR-004) compara el texto del período tal cual (sin normalizar mes/año), consistente con cómo ya está cargado el histórico.
