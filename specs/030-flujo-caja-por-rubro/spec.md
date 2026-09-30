# Feature Specification: Flujo de caja por Rubro

**Feature Branch**: `030-flujo-caja-por-rubro`

**Created**: 2026-09-30

**Status**: Draft

**Input**: User description: "Pantalla de Flujo de caja por Rubro (030). Adaptar el sistema al formato del Excel que Sergio usa hoy ('Cash Flow 2025-2026.xlsx', hoja 'Cash Flow 1'): filas = rubros, Ingresos arriba y Egresos abajo agrupados por Centro de Costos con subtotal, saldo inicial por cuenta y total, columnas = períodos con granularidad seleccionable (semana/mes/trimestre/año), moneda ARS o USD. Las categorías 'Pendiente de aplicar' e 'Histórico sin aplicar' deben verse explícitamente. Drill-down al detalle y exportación a Excel."

## Clarifications

### Session 2026-09-30

- Q: ¿Qué cotización BNA se usa para convertir a dólares? → A: Cada movimiento se convierte con la cotización BNA vendedor de su propio día y después se suma (no hay un único tipo de cambio por columna).
- Q: Si un pago se aplicó a facturas de rubros distintos, ¿cómo se reparte? → A: Según el importe aplicado a cada factura: cada rubro recibe exactamente lo que se le imputó.
- Q: ¿Las transferencias entre cuentas propias aparecen en la tabla? → A: Sí, en filas propias ("Colocación FIMA", "Rescate FIMA", "Traspaso entre bancos"), en una sección separada de los rubros operativos.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver el flujo de caja real por rubro y período (Priority: P1)

Sergio quiere ver en qué se fue y de dónde vino el dinero real de la empresa, con el mismo formato con el que arma su planilla de Cash Flow: el saldo inicial de cada cuenta, los ingresos por rubro (ej. Venta Terneros, Venta Soja, Alquiler agrícola) y los egresos agrupados por centro de costo (ej. Personal, Servicios, Administración), cada grupo con su subtotal, en columnas por período. Hoy ese cálculo ya lo hace el sistema, pero no hay pantalla: solo lo ve armando la planilla a mano.

**Why this priority**: es el pedido original; sin la tabla no hay nada que ver ni exportar.

**Independent Test**: elegir un rango de fechas con movimientos reales y comprobar que la tabla muestra el saldo inicial, los ingresos por rubro, los egresos agrupados por centro de costo con subtotales, el total de cada período y el saldo final, y que esos totales coinciden con los movimientos bancarios del rango.

**Acceptance Scenarios**:

1. **Given** un rango de fechas con movimientos bancarios, **When** se abre la pantalla, **Then** se ven las filas de saldo inicial (por cuenta y total), Ingresos por rubro con su total, Egresos agrupados por centro de costo con subtotal por grupo y total general, y saldo final por período.
2. **Given** movimientos sin aplicación a un documento, **When** se muestra la tabla, **Then** aparecen en las filas "Pendiente de aplicar" o "Histórico sin aplicar" (según sean posteriores o anteriores al 01-09-2015), nunca ocultos ni mezclados con otros rubros.
3. **Given** un período sin movimientos, **When** se muestra la tabla, **Then** la columna aparece igual, con valores en cero, y el saldo se arrastra al período siguiente.

---

### User Story 2 - Cambiar granularidad y moneda (Priority: P2)

Sergio alterna entre una mirada de corto plazo (semanas) y una de largo plazo (meses, trimestres, años), y necesita ver los montos en pesos o en dólares, porque en contextos de inflación los pesos de meses distintos no se pueden comparar directamente.

**Why this priority**: amplía el valor de la tabla, pero la vista mensual en pesos ya es útil sola.

**Independent Test**: sobre el mismo rango, cambiar la granularidad y comprobar que los totales del rango no cambian; cambiar a dólares y comprobar que cada período se convirtió con el tipo de cambio de ese período.

**Acceptance Scenarios**:

1. **Given** la tabla en vista mensual, **When** se elige trimestral, **Then** las columnas pasan a trimestres y el total de todo el rango sigue siendo el mismo.
2. **Given** la tabla en pesos, **When** se elige dólares, **Then** cada movimiento se convierte con la cotización BNA vendedor de su día y los importes de la tabla son la suma de esas conversiones; en el detalle de una celda se ve la cotización usada en cada movimiento.
3. **Given** un movimiento de un día sin cotización cargada, **When** se elige dólares, **Then** se usa la última cotización anterior disponible dentro de los 7 días; si no hay ninguna, la celda muestra un aviso de "sin tipo de cambio" en vez de un valor inventado.

---

### User Story 3 - Ver qué movimientos componen un rubro (Priority: P2)

Cuando un número le llama la atención, Sergio quiere ver los movimientos bancarios que lo componen (fecha, cuenta, concepto, importe, contacto y documento aplicado) sin salir de la pantalla.

**Why this priority**: es lo que permite confiar en la tabla y corregir clasificaciones; sin esto, un número dudoso obliga a buscar en otra pantalla.

**Independent Test**: hacer clic en una celda (rubro × período) y comprobar que la lista de movimientos suma exactamente el valor de la celda.

**Acceptance Scenarios**:

1. **Given** una celda con importe, **When** se hace clic, **Then** se abre el detalle con los movimientos que la componen, y su suma es igual al valor de la celda.
2. **Given** un movimiento en "Pendiente de aplicar", **When** se ve en el detalle, **Then** hay un acceso directo para aplicarlo a su factura o venta (flujo ya existente de aplicación de pagos).

---

### User Story 4 - Exportar a Excel (Priority: P3)

Sergio quiere llevar la tabla a su planilla para seguir trabajando (escenarios, proyección), con la misma estructura de filas y columnas que ve en pantalla.

**Why this priority**: útil, pero la pantalla ya resuelve la consulta.

**Independent Test**: exportar y abrir el archivo: mismas filas, columnas, subtotales y moneda que en pantalla, con importes numéricos (no texto).

**Acceptance Scenarios**:

1. **Given** la tabla con cierta granularidad y moneda, **When** se exporta, **Then** el archivo reproduce esa vista, con importes numéricos y la moneda y el rango indicados en el encabezado.

---

### Edge Cases

- Un movimiento aplicado a varios documentos de distintos rubros se reparte según el importe aplicado a cada documento (confirmado); la suma de las partes es igual al movimiento. Si lo aplicado es menor que el movimiento, la diferencia va a "Pendiente de aplicar".
- Traspasos internos entre cuentas propias (ej. Galicia a FIMA): aparecen en la sección "Movimientos entre cuentas propias", no en los rubros operativos. Como salen de una cuenta y entran en otra, su neto en el total es cero. En un traspaso entre bancos (ej. BNA → Galicia), la pata del otro banco se reconoce por mismo importe dentro de los 3 días; si no se encuentra, la pata sola se muestra igual, señalada como "traspaso sin contraparte".
- Rango que empieza antes del 01-09-2015: los movimientos anteriores aparecen como "Histórico sin aplicar" si no tienen aplicación.
- Rango muy largo (ej. varios años semanales): la tabla debe seguir siendo usable y recorrible horizontalmente.
- Rubros sin movimientos en el rango no se muestran; los grupos de centro de costo vacíos tampoco. Excepción: las tres filas de "Movimientos entre cuentas propias" se muestran siempre, aunque estén en cero, para que la sección sea estable.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST mostrar, para un rango de fechas elegido, una tabla con filas de saldo inicial por cuenta (Galicia cuenta corriente, Nación, Galicia Fondo FIMA) y su total, Ingresos por rubro con total, Egresos agrupados por centro de costo con subtotal por grupo y total, resultado neto operativo del período, sección de movimientos entre cuentas propias y saldo final.
- **FR-002**: El sistema MUST mostrar las columnas por período según la granularidad elegida: semana, mes, trimestre o año. El mes es la granularidad por defecto.
- **FR-003**: El sistema MUST mostrar siempre las categorías "Pendiente de aplicar" e "Histórico sin aplicar" como filas propias, visualmente distinguibles, con su importe por período.
- **FR-004**: El sistema MUST permitir ver los importes en pesos o en dólares; en dólares, cada movimiento se convierte con la cotización BNA vendedor de su propio día y los importes mostrados son la suma de esas conversiones. Los saldos (inicial por cuenta y final de cada período) se convierten con la cotización del día de corte correspondiente, con el mismo aviso si falta.
- **FR-005**: El sistema MUST usar, para un día sin cotización, la última cotización anterior disponible dentro de los 7 días, y MUST indicar explícitamente las celdas con movimientos sin ninguna cotización en ese plazo, sin mostrar un valor convertido inventado.
- **FR-006**: El sistema MUST permitir abrir el detalle de movimientos de cualquier celda con importe; la suma del detalle MUST ser igual al valor de la celda.
- **FR-007**: El detalle MUST mostrar por movimiento: fecha, cuenta, concepto, importe, contacto y documento aplicado (o "sin aplicar"), con acceso a aplicar los pendientes.
- **FR-008**: El sistema MUST mostrar los traspasos entre cuentas propias en una sección separada, "Movimientos entre cuentas propias", con filas "Colocación FIMA", "Rescate FIMA" y "Traspaso entre bancos", fuera de los totales de Ingresos y Egresos operativos.
- **FR-009**: El sistema MUST recalcular la tabla cada vez que se consulta, sin guardar resultados previos, para que refleje las aplicaciones de pago más recientes.
- **FR-010**: El sistema MUST permitir exportar la vista actual (rango, granularidad y moneda) a Excel, con importes numéricos y la misma estructura de filas y subtotales.
- **FR-011**: El sistema MUST mostrar los importes con el formato de moneda del sistema, y los negativos con signo y en rojo.
- **FR-012**: La pantalla MUST estar en la sección Finanzas, junto a "Flujo de caja real".

### Key Entities *(include if feature involves data)*

- **Movimiento de dinero**: débito o crédito real en una cuenta bancaria propia (fecha, cuenta, concepto, importe). Es la fuente de todos los valores; no se usan documentos sin movimiento.
- **Rubro**: categoría de ingreso o egreso, tomada del documento al que se aplicó el movimiento. Existen dos rubros especiales para lo no aplicado.
- **Centro de costo**: agrupador de rubros de egreso, con subtotal propio.
- **Período**: semana, mes, trimestre o año, según la granularidad elegida.
- **Cotización del día**: BNA vendedor de la fecha de cada movimiento, usada para convertirlo a dólares.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El saldo final de cada período de Nación y de Galicia cuenta corriente coincide al peso con el saldo real de los extractos a esa fecha. El Fondo FIMA se muestra como capital neto colocado (sin rendimiento), aclarado en pantalla.
- **SC-002**: El 100% del dinero movido en el rango aparece en algún rubro, en "Pendiente de aplicar", en "Histórico sin aplicar" o en "Movimientos entre cuentas propias": nada queda fuera.
- **SC-003**: Cambiar la granularidad no altera el total del rango (diferencia de cero).
- **SC-004**: Sergio puede obtener la vista mensual de los últimos 12 meses y exportarla en menos de 1 minuto, sin armar la planilla a mano.
- **SC-005**: En la vista en dólares, el 100% de los movimientos se convierte con la cotización de su día (o la anterior disponible en 7 días) o queda señalado sin tipo de cambio.

## Assumptions

- La atribución de movimientos a rubros y centros de costo es la que ya calcula el sistema (aplicaciones de pago de 019, con fecha de corte 01-09-2015); esta feature no la cambia, solo la muestra.
- El tipo de cambio para dólares es el BNA vendedor **divisa** (la cotización de transferencias) del día de cada movimiento (confirmado), tomado de la serie de parámetros financieros que ya existe en el sistema; fines de semana y feriados usan la cotización anterior (hasta 7 días).
- Las cuentas del saldo inicial son las cuentas bancarias propias registradas en el sistema (hoy Galicia, Nación y el Fondo FIMA); si se agregan cuentas, aparecen solas.
- Uso de escritorio, un único usuario; no se requiere diseño para celular.
- La proyección futura (premisas, escenarios, inflación estimada) queda fuera: corresponde a la planificación financiera a 12 meses, que es otra spec.
