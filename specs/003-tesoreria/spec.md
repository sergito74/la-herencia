# Feature Specification: Tesorería por banco, caja, valores y tarjetas (solo lectura)

**Feature Branch**: `003-tesoreria`

**Created**: 2026-09-15

**Status**: Draft

**Input**: User description: "Diseñar el módulo web de tesorería en modo solo lectura, usando Python, SQL Server, Next.js, TypeScript, Tailwind CSS y TanStack Query. Debe permitir consultar movimientos por banco (BNA, Galicia), caja/efectivo, valores propios/recibidos y tarjetas, cada uno respetando su propia forma de datos. Tesorería ya no es fuente de imputación de rubro/centro de costo/destino: eso pasa a ser responsabilidad exclusiva del módulo de compras. Tesorería debe mostrar, cuando exista, la referencia a la compra u operación que originó cada movimiento. Debe contemplar la futura automatización de carga de resúmenes bancarios y de tarjeta mediante archivos Excel, hoy un proceso híbrido. Preparado para multiusuario aunque hoy lo use una sola persona. No modificar datos reales."

## Clarifications

### Session 2026-09-15

- Q: ¿Cómo se vincula un movimiento de tesorería con la compra que lo originó? → A: El vínculo es indirecto por `IdContacto` + fecha + importe, sin clave explícita

### Session 2026-09-16

- Q: `Valores propios` no tiene campo de contacto (confirmado contra `INFORMATION_SCHEMA` el 2026-09-16), por lo que la heurística `IdContacto`+fecha+importe no se le puede aplicar. ¿Qué se hace para ese medio? → A: No aplicar la heurística; el estado de referencia para movimientos de `Valores propios` es siempre "sin coincidencia"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Consultar movimientos por banco, caja o medio de pago (Priority: P1)

Un usuario administrativo necesita seleccionar un medio (Banco Nación, Banco Galicia, caja/efectivo, valores o tarjeta) y ver sus movimientos, para controlar el estado de fondos disponibles y conciliar contra el resumen real.

**Why this priority**: Es el uso diario del módulo y el que reemplaza directamente la consulta manual de resúmenes en el sistema anterior. Sin esto no hay módulo de tesorería.

**Independent Test**: Puede probarse seleccionando Banco Nación y verificando que se listan sus movimientos (fecha, concepto, importe, contacto) ordenados por fecha, igual que en el prototipo ya validado.

**Acceptance Scenarios**:

1. **Given** el usuario está en el módulo de tesorería, **When** selecciona un banco (BNA o Galicia), **Then** el sistema muestra los movimientos de ese banco con su forma propia de datos (concepto/importe para BNA; débitos/créditos/saldo para Galicia).
2. **Given** el usuario selecciona caja/efectivo, **When** consulta, **Then** el sistema muestra los pagos en efectivo registrados.
3. **Given** el usuario selecciona valores (propios o recibidos), **When** consulta, **Then** el sistema muestra los valores correspondientes con su estado.
4. **Given** el usuario selecciona tarjetas, **When** consulta, **Then** el sistema muestra los resúmenes de tarjeta y sus líneas de detalle.
5. **Given** el usuario aplica un filtro por rango de fechas en cualquier medio, **When** consulta, **Then** la lista se actualiza mostrando solo los movimientos dentro de ese rango.

---

### User Story 2 - Ver la referencia de origen de un movimiento de tesorería (Priority: P1)

Un usuario administrativo, viendo un movimiento de tesorería, necesita saber si corresponde a una compra registrada y cuál, para conciliar el pago con el gasto sin tener que buscar manualmente en otro sistema.

**Why this priority**: Es la contrapartida directa del módulo de compras (donde la imputación ya vive) — sin esta referencia, tesorería queda desconectada del resto del sistema y el usuario pierde la trazabilidad que hoy reclama como prioritaria.

**Independent Test**: Puede probarse tomando un movimiento de tesorería vinculado a una compra conocida y verificando que el sistema muestra la referencia a esa compra (documento, proveedor, importe).

**Acceptance Scenarios**:

1. **Given** un movimiento de tesorería originado en una compra, **When** el usuario lo consulta, **Then** el sistema muestra la referencia a esa compra (documento, proveedor).
2. **Given** un movimiento de tesorería sin compra asociada (por ejemplo, un movimiento manual o de otro origen), **When** el usuario lo consulta, **Then** el sistema indica explícitamente que no hay compra asociada, sin error ni dato inventado.
3. **Given** el usuario ve la referencia a una compra desde tesorería, **When** el módulo de compras esté disponible, **Then** el sistema NO recalcula ni muestra rubro/centro de costo/destino en tesorería — ese dato se consulta únicamente en compras.
4. **Given** un movimiento de tesorería cuya coincidencia por `IdContacto`/fecha/importe arroja más de una compra candidata, **When** el usuario lo consulta, **Then** el sistema muestra todas las candidatas y señala explícitamente que la referencia es ambigua.

---

### User Story 3 - Cargar resúmenes bancarios y de tarjeta mediante archivo Excel (Priority: P3)

Un usuario administrativo necesita subir un archivo Excel con el resumen de un banco o tarjeta para que sus movimientos queden disponibles en el sistema, reemplazando la carga manual híbrida actual.

**Why this priority**: Es una mejora de eficiencia operativa deseada por el usuario, pero el módulo ya entrega valor completo en modo consulta (P1/P2) sin esto. Además implica una futura vía de escritura controlada, que debe quedar preparada pero no obligatoria para el MVP de solo lectura.

**Independent Test**: Puede probarse subiendo un archivo Excel de ejemplo con formato de resumen bancario y verificando que el sistema valida su estructura y muestra una vista previa de los movimientos detectados antes de cualquier confirmación.

**Acceptance Scenarios**:

1. **Given** el usuario tiene un archivo Excel de resumen bancario o de tarjeta, **When** lo sube al sistema, **Then** el sistema valida su estructura y muestra una vista previa de los movimientos detectados.
2. **Given** un archivo con formato no reconocido, **When** el usuario intenta subirlo, **Then** el sistema rechaza el archivo con un mensaje claro sobre qué no coincide.
3. **Given** una vista previa de movimientos cargados desde Excel, **When** el usuario la revisa, **Then** el sistema deja explícito que esos movimientos son una previsualización y no fueron aún confirmados como escritura en la base real (ver Assumptions sobre alcance de escritura).

### Edge Cases

- ¿Qué sucede si un movimiento de tesorería está vinculado a una compra que fue eliminada o no está disponible? El sistema debe mostrar el movimiento igual, indicando que la compra de origen no está disponible.
- ¿Cómo se muestran los saldos de Banco Galicia (que trae su propio campo `Saldo`) frente a Banco Nación (que no lo trae explícito)? Cada banco debe mostrarse con los campos que realmente tiene, sin forzar un saldo donde no existe en el origen.
- ¿Qué sucede si un resumen de tarjeta tiene líneas sin resumen padre asociado? El sistema debe mostrar la inconsistencia de forma visible, no ocultarla.
- ¿Cómo maneja el sistema un archivo Excel subido con columnas de rubro/centro de costo/destino (herencia del formato anterior)? Esas columnas deben ignorarse para fines de imputación, ya que esa responsabilidad quedó en compras.
- ¿Qué sucede ante un medio de pago (banco/caja/tarjeta) sin movimientos en el período filtrado? El sistema debe mostrar un estado vacío claro, sin error.
- ¿Qué sucede si un movimiento de tesorería coincide por `IdContacto`/fecha/importe con más de una compra del mismo contacto? El sistema debe mostrar todas las candidatas como referencias posibles y señalar explícitamente que la coincidencia es ambigua, sin asumir una por defecto.
- ¿Qué sucede con los movimientos de `Valores propios`, que no tienen campo de contacto? El sistema debe mostrar siempre "sin coincidencia" para ese medio, sin intentar una búsqueda parcial solo por fecha/importe (clarificación 2026-09-16).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST permitir seleccionar un medio de tesorería (Banco Nación, Banco Galicia, caja/efectivo, valores propios, valores recibidos, tarjetas) antes de mostrar movimientos.
- **FR-002**: El sistema MUST mostrar los movimientos de cada medio respetando su propia estructura de datos, sin forzar un modelo único entre bancos distintos.
- **FR-003**: El sistema MUST permitir filtrar movimientos de cualquier medio por rango de fechas.
- **FR-004**: El sistema MUST mostrar, para cada movimiento de tesorería, la referencia a la compra de origen cuando pueda identificarse mediante coincidencia de `IdContacto`, fecha e importe contra las compras del mismo contacto (no existe una clave explícita de vínculo directo entre tesorería y compras). Para movimientos de `Valores propios` (sin campo de contacto), el sistema MUST devolver siempre "sin coincidencia" sin intentar la heurística.
- **FR-005**: El sistema MUST indicar explícitamente cuando un movimiento de tesorería no tiene compra asociada, o cuando la coincidencia por `IdContacto`/fecha/importe es ambigua (más de una compra candidata), sin elegir una al azar.
- **FR-006**: El sistema MUST NOT usar ni mostrar las columnas de rubro/centro de costo/destino de los registros bancarios como fuente de imputación; ese dato se consulta exclusivamente desde compras.
- **FR-007**: El sistema MUST permitir subir un archivo Excel de resumen bancario o de tarjeta y validar su estructura antes de aceptarlo.
- **FR-008**: El sistema MUST mostrar una vista previa de los movimientos detectados en un archivo Excel subido, sin escribir datos en la base real como parte de esta funcionalidad.
- **FR-009**: El sistema MUST rechazar con un mensaje claro un archivo Excel cuya estructura no coincida con el formato esperado.
- **FR-010**: El sistema MUST operar en modo lectura respecto de la base real: ninguna pantalla debe confirmar ni persistir movimientos nuevos como parte de esta especificación.
- **FR-011**: El sistema MUST consultar los datos exclusivamente desde SQL Server, sin acceder a bases Access ni fuentes locales duplicadas.
- **FR-012**: El sistema MUST mostrar un estado vacío explícito cuando un medio de tesorería no tenga movimientos en el período consultado.
- **FR-013**: El sistema MUST soportar paginación o desplazamiento progresivo en listados de movimientos con alto volumen (por ejemplo, miles de movimientos BNA) sin degradar el tiempo de respuesta.
- **FR-014**: El sistema MUST soportar sesiones de lectura concurrentes de múltiples usuarios sin degradar ni bloquear la consulta de otros usuarios, consistente con la misma exigencia definida para compras (`specs/002-compras`).

### Key Entities *(include if feature involves data)*

- **Movimiento bancario (BNA)**: movimiento con fecha/hora, concepto, importe y contacto asociado.
- **Movimiento bancario (Galicia)**: movimiento con fecha, descripción, débitos, créditos, saldo y contacto asociado; sus columnas heredadas de centro de costo/rubro/destino quedan sin uso para imputación.
- **Pago en efectivo**: movimiento de caja.
- **Valor propio / Valor recibido**: instrumento de pago o cobro (cheque u otro valor) con su estado.
- **Tarjeta / Resumen de tarjeta / Línea de resumen**: jerarquía de tarjeta, resumen periódico y líneas de detalle de ese resumen.
- **Referencia de origen**: coincidencia (no clave explícita) entre un movimiento de tesorería y una o más compras candidatas del mismo contacto, determinada por `IdContacto` + fecha + importe (documento, proveedor, importe mostrados como referencia), marcada como ambigua si hay más de una candidata.
- **Archivo de resumen (Excel)**: archivo subido por el usuario con movimientos de un banco o tarjeta, sujeto a validación de estructura y previsualización antes de cualquier confirmación futura.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un usuario puede consultar los movimientos de cualquier banco, caja, valores o tarjeta en menos de 30 segundos desde que abre el módulo.
- **SC-002**: El 100% de los movimientos de tesorería consultados muestran un estado de referencia claro: sin compra asociada, una compra candidata, o varias compras candidatas marcadas explícitamente como ambiguas — nunca una asignación silenciosa o incierta.
- **SC-003**: Ningún dato de imputación (rubro/centro de costo/destino) se muestra ni se deriva desde tesorería; ese dato se obtiene únicamente desde compras.
- **SC-004**: Un usuario puede subir un archivo Excel de resumen y ver la vista previa de sus movimientos en menos de 1 minuto, sin que la base real se modifique.
- **SC-005**: Ningún usuario puede confirmar ni persistir movimientos nuevos en la base real desde este módulo (verificable por ausencia de cualquier acción de escritura efectiva en la interfaz).

## Assumptions

- Los usuarios de este módulo son personal administrativo interno de La Herencia, con acceso ya autorizado; el diseño no debe impedir agregar más de un usuario concurrente en el futuro, aunque roles y permisos específicos se definen en una etapa posterior.
- La carga de resúmenes vía Excel se especifica aquí solo hasta el punto de validación y previsualización; la confirmación real (persistencia en SQL Server) requiere una especificación y autorización de escritura separadas, conforme a la constitución del proyecto y al estado actual de solo lectura.
- El formato exacto de los archivos Excel de BNA, Galicia y tarjetas no está definido todavía; se asume que existe (o existirá) un formato reconocible por banco/tarjeta, y su definición detallada de columnas es trabajo de `/speckit-plan`, no de esta spec.
- Las columnas de imputación (rubro/centro de costo/destino) que puedan traer los archivos Excel o las tablas bancarias existentes se ignoran a los fines de este módulo, conforme a la decisión de que compras es la única fuente de verdad de imputación.
- El volumen de datos a mostrar es el observado en el prototipo (miles de movimientos BNA), por lo que las listas deben soportar paginación o desplazamiento sin degradar la experiencia.
- Integraciones fiscales (AFIP/ARCA) quedan fuera de alcance de esta primera versión.
