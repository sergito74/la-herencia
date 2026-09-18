# Feature Specification: Tarjetas de Crédito

**Feature Branch**: `008-tarjetas`

**Created**: 2026-09-18

**Status**: Draft

**Input**: User description: "Módulo Tarjetas (008-tarjetas): migración del módulo de tarjetas de crédito de Access a la web app, escribiendo exclusivamente contra la DB de trabajo `WC`. Alcance: catálogo de tarjetas (solo lectura), cuenta corriente por tarjeta (resolviendo el origen 'Tarjetas' hoy fuera de alcance en Cuentas Corrientes), compras en cuotas con tarjeta (con generación automática de cuotas), y resúmenes de tarjeta con sus líneas de consumo. Fuera de alcance: conciliación automática línea↔cuota y distribución de una línea entre varios contactos — ambas features del esquema real tienen 0 filas en producción, nunca se usaron."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Consultar resúmenes de tarjeta y sus consumos (Priority: P1)

Un usuario administrativo necesita revisar los resúmenes de tarjeta de crédito ya cargados (293 resúmenes reales, 1694 líneas de consumo) para verificar cargos, impuestos y el detalle de compras de un período, y cargar los resúmenes nuevos a medida que llegan del banco.

**Why this priority**: Es el subdominio con mayor volumen de uso real del módulo — la funcionalidad que la operación diaria más necesita, y la que hoy no tiene ningún equivalente web.

**Independent Test**: Buscar los resúmenes de una tarjeta real por rango de fechas, abrir uno y verificar que sus líneas de consumo y cargos coinciden con los datos reales en `WC`. Cargar un resumen nuevo (cabecera + líneas) y confirmar que queda guardado solo en `WC`.

**Acceptance Scenarios**:

1. **Given** una tarjeta con resúmenes cargados, **When** el usuario busca por tarjeta y rango de fechas de cierre, **Then** ve los resúmenes que coinciden, con su fecha de cierre/vencimiento y total de cargos.
2. **Given** un resumen existente, **When** el usuario lo abre, **Then** ve la cabecera completa de cargos/impuestos y la lista de líneas de consumo (fecha, detalle, importe, contacto y documento si están cargados).
3. **Given** un resumen sin líneas de consumo (solo cabecera, ej. un resumen sin movimientos en el período), **When** el usuario lo abre, **Then** el sistema lo muestra igual, sin exigir al menos una línea.
4. **Given** los datos de un resumen nuevo (tarjeta, código, fechas, cargos, líneas de consumo), **When** el usuario lo guarda, **Then** el sistema lo persiste en `WC` y lo muestra en el listado.

---

### User Story 2 - Ver la cuenta corriente de una tarjeta (Priority: P2)

Un usuario necesita ver los movimientos y el saldo acumulado de una tarjeta específica, de la misma forma que ya puede hacerlo con cualquier otra cuenta corriente del sistema (proveedores, contactos), y poder navegar desde un movimiento de tarjeta en Cuentas Corrientes hacia el resumen o la cuota que lo originó.

**Why this priority**: Resuelve una laguna concreta y ya identificada: hoy cualquier movimiento de cuenta corriente con origen "Tarjetas" queda marcado como "fuera de alcance", sin poder verse el detalle.

**Independent Test**: Abrir la cuenta corriente de una tarjeta real y verificar que el saldo acumulado final coincide con la suma de sus movimientos reales en `WC`; hacer clic en un movimiento de origen "Tarjetas" desde Cuentas Corrientes y verificar que lleva al resumen o cuota correspondiente en vez de mostrar "sin detalle disponible".

**Acceptance Scenarios**:

1. **Given** una tarjeta con movimientos, **When** el usuario abre su cuenta corriente, **Then** ve los movimientos ordenados cronológicamente con el saldo acumulado por movimiento (mismo criterio que Cuentas Corrientes, 004).
2. **Given** un movimiento de cuenta corriente cuyo origen es un resumen de tarjeta, **When** el usuario hace clic en él, **Then** navega al resumen correspondiente.
3. **Given** un movimiento de cuenta corriente cuyo origen es una cuota de una compra en cuotas, **When** el usuario hace clic en él, **Then** navega a la compra en cuotas correspondiente, con esa cuota identificada.

---

### User Story 3 - Cargar una compra en cuotas con tarjeta (Priority: P3)

Un usuario necesita registrar una compra financiada con tarjeta de crédito (fecha, contacto, comprobante, cantidad de cuotas) y que el sistema genere automáticamente el cronograma de cuotas, tal como lo hace hoy el formulario Access.

**Why this priority**: Es un flujo de alta activo (18 compras / 183 cuotas reales) pero de menor volumen que los resúmenes, y no bloquea a las otras dos historias.

**Independent Test**: Cargar una compra en 6 cuotas con un importe total conocido y verificar que se generan 6 cuotas mensuales con las fechas e importes esperados (redondeando la diferencia de centavos en la última cuota), y que se pueden marcar como cobradas/no cobradas.

**Acceptance Scenarios**:

1. **Given** los datos de una compra en cuotas (fecha, contacto, comprobante, importe total, cantidad de cuotas), **When** el usuario la guarda, **Then** el sistema genera automáticamente esa cantidad de cuotas con fecha de vencimiento mensual sucesiva a partir de la fecha de compra, y persiste todo en `WC`.
2. **Given** una compra en cuotas ya cargada, **When** el usuario busca por contacto o fecha, **Then** la encuentra en el listado con su cantidad de cuotas y estado.
3. **Given** una cuota de una compra existente, **When** el usuario la marca como cobrada, **Then** ese estado queda reflejado en el listado y en la cuenta corriente de la tarjeta.
4. **Given** un importe total que no se divide en partes iguales entre la cantidad de cuotas, **When** el sistema genera el cronograma, **Then** ajusta la diferencia de centavos en la última cuota, de forma que la suma de todas las cuotas sea exactamente igual al importe total.

---

### User Story 4 - Consultar el catálogo de tarjetas (Priority: P4)

Un usuario necesita ver qué tarjetas existen en el sistema y cuáles están activas, como referencia rápida y como origen de los combos de selección de tarjeta en las otras historias.

**Why this priority**: Es un catálogo chico (5 registros reales) y de solo lectura — el valor que aporta por sí solo es bajo, pero es una dependencia natural de las historias 1 y 3.

**Independent Test**: Abrir el listado de tarjetas y verificar que muestra las tarjetas reales de `WC` con su banco y si están activas.

**Acceptance Scenarios**:

1. **Given** el catálogo de tarjetas cargado en `WC`, **When** el usuario abre el listado, **Then** ve todas las tarjetas con su nombre, banco y si están activas.
2. **Given** una tarjeta inactiva, **When** el usuario intenta seleccionarla para cargar una compra en cuotas o un resumen nuevo, **Then** no aparece entre las opciones seleccionables (pero sigue viéndose en su historial ya cargado).

---

### Edge Cases

- Un resumen marcado como "solo cabecera" (sin líneas de consumo) debe poder cargarse y mostrarse igual que uno con líneas — no es un error, es un tipo de resumen real (ver `SoloCabecera` en el esquema).
- Una línea de consumo de un resumen sin contacto ni número de documento asociado (la mayoría de los casos reales) debe mostrarse igual, sin exigir esos datos.
- Una compra en cuotas con una sola cuota (pago en un solo pago con tarjeta, sin financiación real) debe aceptarse igual.
- Dos resúmenes de la misma tarjeta con el mismo código de resumen (posible reimportación) — el sistema debe advertir, no bloquear (mismo criterio que otros módulos: FR-009a/FR-012a de Ventas de Hacienda/Granos).
- Una tarjeta inactiva con movimientos históricos sigue siendo consultable en su cuenta corriente y en resúmenes/compras ya cargadas, aunque no se pueda usar para cargar nuevos.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE mostrar el catálogo de tarjetas (nombre, banco, activa/inactiva) en modo solo lectura — el alta de tarjetas nuevas no es parte de este alcance.
- **FR-002**: El sistema DEBE mostrar, para una tarjeta dada, sus movimientos de cuenta corriente ordenados cronológicamente con el saldo acumulado por movimiento, con el mismo criterio ya usado en Cuentas Corrientes (004).
- **FR-003**: El sistema DEBE resolver un movimiento de cuenta corriente con origen "Tarjetas" a un destino navegable: el resumen de tarjeta o la cuota de compra en cuotas que lo originó, en vez de mostrarlo como "fuera de alcance".
- **FR-004**: El sistema DEBE permitir cargar una compra en cuotas con tarjeta (fecha, contacto, número de comprobante, importe total, cantidad de cuotas).
- **FR-005**: Al guardar una compra en cuotas, el sistema DEBE generar automáticamente el cronograma de cuotas (una cuota por mes desde la fecha de compra), dividiendo el importe total en partes iguales y ajustando la diferencia de redondeo en la última cuota.
- **FR-006**: El sistema DEBE permitir buscar y listar las compras en cuotas cargadas, por contacto, tarjeta y rango de fechas.
- **FR-007**: El sistema DEBE permitir marcar una cuota individual como cobrada o no cobrada.
- **FR-008**: El sistema DEBE permitir cargar un resumen de tarjeta (tarjeta, código de resumen, fecha de cierre, fecha de vencimiento, y los cargos/impuestos de cabecera: Impuesto de Sellos, Gastos de Administración, Mantenimiento de Cuenta, Renovación Anual, Promoción BNA, Crédito Contingente, Interés de Financiación, Interés Compensatorio, IVA 10,5%, Percepción IVA 10,5%, IVA 21%, Percepción IVA 21%, Percepción IIBB, Ajuste de Resumen Anterior) junto con sus líneas de consumo (fecha de compra, detalle, importe, fecha de vencimiento de la compra, contacto opcional, número de documento opcional).
- **FR-009**: El sistema DEBE permitir cargar un resumen sin líneas de consumo ("solo cabecera"), sin exigir al menos una línea.
- **FR-010**: El sistema DEBE permitir buscar y listar los resúmenes cargados, por tarjeta y rango de fechas de cierre/vencimiento, sin mostrar nada hasta que se aplique al menos un filtro (mismo criterio ya usado en Compras/Ventas/Contactos).
- **FR-011**: Al abrir un resumen, el sistema DEBE mostrar el total calculado a partir de sus líneas y cargos, para que el usuario pueda contrastarlo contra el total declarado por el banco.
- **FR-012**: El sistema DEBE advertir (sin bloquear el guardado) si se carga un resumen con el mismo código para la misma tarjeta que uno ya existente.
- **FR-013**: El sistema DEBE permitir editar y eliminar una compra en cuotas o un resumen ya cargado, usando el mismo mecanismo de bloqueo exclusivo de edición que Compras y Ventas (evita que dos personas editen el mismo registro a la vez).
- **FR-014**: El sistema NO DEBE incluir conciliación automática entre líneas de consumo y cuotas/deudas, ni distribución de una línea de consumo entre varios contactos — ambas funcionalidades existen en el esquema de origen pero nunca se usaron en producción (0 registros reales).
- **FR-015**: Todas las escrituras de este módulo (alta/edición/eliminación de compras en cuotas y resúmenes) DEBEN hacerse exclusivamente contra la base de datos de trabajo `WC`, nunca contra `LaHerencia`.

### Key Entities

- **Tarjeta**: una tarjeta de crédito de la empresa (nombre, banco emisor, activa/inactiva). Catálogo de solo lectura en este alcance.
- **Compra en cuotas**: una compra financiada con una tarjeta (fecha, contacto, número de comprobante, cantidad de cuotas), origen de un cronograma de cuotas.
- **Cuota**: una cuota individual de una compra en cuotas (número de cuota, fecha de vencimiento, importe, si está cobrada), asociada a una tarjeta a través de su compra.
- **Resumen de tarjeta**: el resumen mensual de una tarjeta (código, fecha de cierre, fecha de vencimiento, cargos e impuestos de cabecera), asociado a una tarjeta.
- **Línea de consumo**: un consumo individual dentro de un resumen (fecha de compra, detalle, importe, contacto y documento opcionales).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un usuario puede encontrar y abrir cualquiera de los 293 resúmenes reales existentes por tarjeta y fecha en menos de 30 segundos.
- **SC-002**: El saldo acumulado que muestra la cuenta corriente de cada una de las 5 tarjetas reales coincide exactamente con el que resulta de sumar sus movimientos reales en `WC`.
- **SC-003**: El 100% de los movimientos de cuenta corriente con origen "Tarjetas" dejan de mostrarse como "fuera de alcance" y navegan a un resumen o cuota concreto.
- **SC-004**: Un usuario puede cargar una compra en cuotas nueva y ver sus cuotas generadas automáticamente en menos de 1 minuto, sin tener que calcular manualmente ninguna fecha ni importe de cuota.
- **SC-005**: Ninguna escritura de este módulo llega nunca a la base de datos `LaHerencia` (verificado contra SQL Server tras cada escenario de prueba).

## Assumptions

- El alta de tarjetas nuevas (catálogo `Tarjetas`) es infrecuente y queda fuera de este alcance — se asume que, si hace falta, se agrega directo en la base de datos, igual que otros catálogos chicos del sistema (ej. `Establecimientos`).
- El usuario que marca una cuota como "cobrada" es el mismo usuario administrativo único del resto del sistema, sin necesidad de un flujo de aprobación separado.
- El cronograma de cuotas se genera con periodicidad mensual fija a partir de la fecha de compra — no hay evidencia en los datos reales de periodicidades distintas (quincenal, bimestral).
- La conciliación automática línea↔cuota y la distribución de una línea entre varios contactos (`Tarjetas_Conciliacion_Link`/`Propuesta`, `Tarjetas_Lineas_Distrib`) quedan explícitamente fuera de alcance: existen en el esquema pero tienen 0 filas en producción real — nunca se usaron en años de operación, y agregar esa complejidad sin evidencia de necesidad sería sobre-ingeniería.
- Los catálogos de apoyo `Tarjetas_TipoLinea` y `Tarjetas_MapeoConceptos` (usados originalmente para categorizar/normalizar líneas importadas automáticamente desde archivos de resumen) no son necesarios en este alcance porque la carga de resúmenes es manual, no una importación automática de archivos bancarios.
