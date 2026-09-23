# Feature Specification: Exportar Saldos de Cuentas Corrientes y Valores Propios a Excel

**Feature Branch**: `014-informes-cuentas-valores`

**Created**: 2026-09-22

**Status**: Draft

**Input**: User description: "Auditoría de los 20 informes de Access (2026-09-22) encontró 17 sin cubrir en la web. De esos, dos dominios activos con valor real y ya migrados como consulta (solo les falta la capa de reporte/export): Cuentas Corrientes (resumen de cuenta por proveedor + saldos de todos los proveedores a la vez) y Valores Propios/cheques (listado y resumen anual de cheques emitidos). El usuario confirmó que Valores Propios sigue siendo parte del flujo real aunque hoy no tenga carga reciente. El reporte de Flujo de Fondos (Rubro x mes) se descarta de esta spec — el usuario pidió rediseñarlo aparte, la fuente de Rubro por movimiento es ambigua entre bancos."

## Clarifications

### Session 2026-09-22

- Q1 (alcance): la auditoría también encontró duplicados entre sí en Access ("Compras por proveedor" vs "Inf documentos_Fecha", mismo dato con otro orden) y el Flujo de Fondos (7 variantes). ¿Entran en esta spec? → **A: No** — Compras ya tiene su propio listado web sin export, que puede resolverse en una spec de Compras aparte si se prioriza; Flujo de Fondos queda descartado por decisión explícita del usuario (ver Input).
- Q2 (saldos de todos los proveedores): el saldo de un contacto ya existe (`get_saldo`, un contacto a la vez). Un reporte de "saldos de todos los proveedores" necesita el saldo final de cada uno en una sola consulta. ¿Se limita a proveedores con saldo distinto de cero, o incluye a todos? → **A: Todos los contactos con al menos un movimiento** — un proveedor con saldo exactamente $0 (cuenta saldada) sigue siendo información útil para el Estudio Contable, y filtrar "distinto de cero" escondería justo el caso de una cuenta bien saldada.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Exportar el resumen de cuenta de un proveedor (Priority: P1)

Un usuario administrativo, viendo la cuenta corriente de un proveedor puntual, necesita exportarla a Excel para enviarla o archivarla, en vez de tener que armarla a mano copiando la tabla en pantalla.

**Why this priority**: Es el reemplazo directo del informe Access "Resumen de cuenta por proveedor" — el caso de uso más frecuente (un proveedor puntual, no todos a la vez).

**Independent Test**: Puede probarse exportando la cuenta corriente de un proveedor con movimientos reales y verificando que el Excel tiene las mismas filas (fecha, documento, deuda, crédito, saldo acumulado) que ya muestra la pantalla de cuenta corriente (004).

**Acceptance Scenarios**:

1. **Given** la pantalla de cuenta corriente de un proveedor con movimientos, **When** el usuario exporta, **Then** el sistema genera un `.xlsx` con una fila por movimiento (fecha, documento, número de documento, deuda, crédito, saldo acumulado) y el saldo final del contacto.
2. **Given** un filtro de fechas ya aplicado en pantalla (004 FR-012), **When** el usuario exporta, **Then** el Excel respeta el mismo filtro, no exporta el historial completo por accidente.
3. **Given** un proveedor sin ningún movimiento, **When** el usuario exporta, **Then** el sistema genera un Excel válido con el encabezado y sin filas de datos, sin error.

---

### User Story 2 - Exportar los saldos de todos los proveedores (Priority: P1)

Un usuario administrativo necesita ver y exportar de una sola vez el saldo actual de todos los proveedores con movimientos, para armar un resumen de deuda total sin abrir cuenta por cuenta.

**Why this priority**: Es el reemplazo directo de "Inf Saldos Compras" — un reporte que hoy no tiene ningún equivalente, ni siquiera de consulta en pantalla (solo existe saldo de a uno).

**Independent Test**: Puede probarse exportando el listado completo y verificando, para 3 proveedores elegidos al azar, que el saldo exportado coincide exactamente con lo que devuelve la pantalla de cuenta corriente de cada uno por separado (004 US2).

**Acceptance Scenarios**:

1. **Given** el listado de saldos, **When** el usuario lo consulta o exporta, **Then** el sistema muestra una fila por contacto con al menos un movimiento (razón social, saldo actual), incluidos los saldados en $0 (Clarifications Q2).
2. **Given** el listado de saldos, **When** el usuario lo consulta en pantalla, **Then** puede ordenarlo por razón social o por saldo (mayor deuda primero), para priorizar a quién pagar o reclamar.
3. **Given** el saldo de un contacto puntual en este listado, **When** se compara contra el saldo mostrado en su cuenta corriente individual (004), **Then** ambos números coinciden exactamente (misma fuente, `vw_MovimientosCuenta_Saldo`).

---

### User Story 3 - Ver y exportar el listado de cheques propios (Priority: P2)

Un usuario administrativo necesita ver el listado de cheques propios emitidos, con su estado (cobrado/pendiente) y datos (número, fecha, vencimiento, importe, banco/cuenta), y exportarlo a Excel.

**Why this priority**: Valores Propios ya tiene consulta básica en tesorería (003) pero sin exponer todos los campos del cheque en un formato de listado imprimible ni exportación — P2 porque el volumen de carga real está discontinuado desde 2021 según los datos actuales de `WC`, aunque el usuario confirmó que el dominio sigue vigente operativamente.

**Independent Test**: Puede probarse exportando el listado completo de valores propios y verificando que incluye número de cheque, fechas de emisión/vencimiento/cobro, importe, estado y comentarios, con el mismo total que la consulta de tesorería (003, medio `valores-propios`).

**Acceptance Scenarios**:

1. **Given** el listado de valores propios, **When** el usuario lo exporta, **Then** el Excel incluye número de cheque, fecha de emisión, fecha de vencimiento, importe, estado (cobrado/pendiente), fecha de cobro si aplica, número de cuenta y comentarios.
2. **Given** un filtro de fechas ya aplicado en pantalla (mismo filtro que ya soporta 003 para este medio), **When** el usuario exporta, **Then** el Excel respeta ese filtro.
3. **Given** un cheque con estado distinto a los dos valores documentados ("S"/"N" — Assumptions), **When** aparece en el listado, **Then** el sistema lo muestra tal cual está en la base (sin inventar un tercer estado ni ocultarlo).

### Edge Cases

- ¿Qué pasa si dos proveedores tienen el mismo saldo? El orden por saldo es estable pero no define un criterio de desempate — cualquier orden secundario consistente (ej. razón social) es aceptable, mientras no cambie entre refrescos sin razón.
- ¿Qué pasa si un contacto tiene movimientos pero su razón social está vacía o nula? Se muestra igual, con la razón social en blanco en vez de ocultarlo del listado (mismo criterio que el resto del sistema: nunca esconder un registro real por un campo faltante).
- ¿Qué pasa si se exporta el listado de saldos con miles de contactos? El export debe completarse sin degradar la respuesta del resto del sistema (mismo criterio de FR-014 de 003/002 sobre lecturas concurrentes).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST permitir exportar a `.xlsx` el resumen de cuenta corriente de un contacto puntual, respetando cualquier filtro de fechas ya aplicado (mismas columnas que la pantalla de 004: fecha, documento, número de documento, deuda, crédito, saldo acumulado).
- **FR-002**: El sistema MUST calcular el saldo de todos los contactos con al menos un movimiento en una sola operación, sin recorrer contacto por contacto desde el cliente.
- **FR-003**: El sistema MUST permitir consultar y exportar ese listado de saldos, ordenable por razón social o por saldo.
- **FR-004**: El sistema MUST incluir en el listado de saldos a los contactos con saldo $0 (cuenta saldada), no solo a los que tienen deuda o crédito pendiente (Clarifications Q2).
- **FR-005**: El sistema MUST permitir consultar el listado completo de valores propios (cheques) con todos sus campos reales (número, fechas, importe, estado, comentarios, número de cuenta), no solo el subconjunto ya expuesto por 003.
- **FR-006**: El sistema MUST permitir exportar a `.xlsx` el listado de valores propios, respetando cualquier filtro de fecha ya aplicado en pantalla (mismo filtro que ya soporta 003 para este medio).
- **FR-007**: El sistema MUST operar en modo lectura respecto de `WC` — ninguna pantalla de esta spec persiste ni modifica datos (mismo criterio de 003/004).
- **FR-008**: El sistema MUST consultar los datos exclusivamente desde SQL Server (`WC`), sin acceder a `LaHerencia` ni `.accdb`.
- **FR-009**: El sistema MUST mostrar un estado vacío explícito cuando un export no tenga filas (contacto sin movimientos, sin resultados con el filtro aplicado), sin error.

### Key Entities *(include if feature involves data)*

- **Resumen de cuenta (export)**: mismas filas que `vw_MovimientosCuenta_Base`/`vw_MovimientosCuenta_Saldo` ya usadas por 004, para un contacto y rango de fechas.
- **Saldo por contacto (nuevo, agregado)**: una fila por contacto con al menos un movimiento — razón social, saldo actual (`SaldoParcial` de la última fila de `vw_MovimientosCuenta_Saldo` por contacto, mismo criterio que `get_saldo` de 004 pero para todos los contactos a la vez).
- **Valor propio (cheque)**: entidad ya existente en `dbo.[Valores propios]` (003), expuesta aquí con todos sus campos reales y su propia exportación.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un usuario puede exportar la cuenta corriente de un proveedor puntual en menos de 15 segundos desde que lo pide.
- **SC-002**: El listado de saldos de todos los proveedores carga en menos de 10 segundos y su total coincide exactamente, contacto por contacto, con el saldo individual de 004 (verificado en al menos 5 contactos reales).
- **SC-003**: El 100% de los contactos con movimientos aparecen en el listado de saldos, incluidos los saldados en $0.
- **SC-004**: Un usuario puede exportar el listado de valores propios en menos de 15 segundos.
- **SC-005**: Ningún endpoint de esta spec persiste o modifica datos en `WC` (verificable por ausencia de cualquier acción de escritura en el código).

## Assumptions

- El campo `Cobrado` de `Valores propios` tiene los valores reales confirmados contra `WC` el 2026-09-22: `'S'` (cobrado, 1133 filas), `'A'` (9 filas, significado a confirmar con el usuario si se vuelve relevante — se muestra tal cual, sin traducir), y potencialmente `'N'`/vacío para pendientes (0 filas hoy, pero el campo debe soportarlo).
- El dominio de Valores Propios no tiene carga real desde 2021-04-16 en los datos actuales de `WC`, pero el usuario confirmó que sigue siendo parte del flujo operativo real — esta spec expone lo que ya existe en la base, no asume que va a haber carga nueva (eso requeriría una spec de alta/edición aparte, fuera de este alcance de solo-lectura/export).
- El reporte de Flujo de Fondos (Rubro x mes) queda explícitamente fuera de esta spec — descartado por el usuario, pendiente de rediseño en una spec futura.
- Los informes de Compras duplicados entre sí (Clarifications Q1) quedan fuera de esta spec.
- Mismo criterio de formato numérico y monetario del sistema (miles `.`, decimales `,`, `$`) en cualquier pantalla nueva.
