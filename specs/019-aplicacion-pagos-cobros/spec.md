# Feature Specification: Aplicación de pagos y cobros (cuenta corriente)

**Feature Branch**: `019-aplicacion-pagos-cobros`

**Created**: 2026-09-25

**Status**: Draft

**Input**: User description: "Cuenta corriente para que los pagos se vayan asignando a las deudas (compras/egresos) y los cobros se vayan asignando a los documentos de crédito (ventas) a medida que ingresan al sistema. No es posible conciliar uno a uno los movimientos por importe/fecha exacta porque nunca van a dar exactos."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Aplicar un pago a una o más facturas de compra pendientes (Priority: P1)

Como usuario que carga un pago real (ya registrado en Tesorería/Flujo de caja), quiero aplicarlo contra una o más facturas de compra pendientes del mismo proveedor, para que el sistema sepa qué deuda se canceló sin depender de que la fecha y el importe coincidan exactos con la factura.

**Why this priority**: Es el problema concreto que motivó esta feature — sin esto, el flujo de caja por rubro (018 v2) no puede atribuir la enorme mayoría de los egresos reales a un Rubro/Centro de Costos.

**Independent Test**: cargar un pago real de un proveedor con facturas pendientes, aplicarlo contra la más antigua (sugerencia FIFO), confirmar, y verificar que esa factura pasa a "Parcialmente aplicada" o "Totalmente aplicada" según corresponda.

**Acceptance Scenarios**:

1. **Given** un pago real con contacto conocido y facturas de compra pendientes de ese contacto, **When** el usuario abre la pantalla de aplicación, **Then** el sistema sugiere automáticamente las facturas más antiguas (FIFO) hasta cubrir el importe del pago, editable antes de confirmar.
2. **Given** una sugerencia de aplicación, **When** el usuario la edita (cambia qué facturas y por cuánto se aplica) y confirma, **Then** se guarda la aplicación tal como la dejó el usuario, no la sugerencia original.
3. **Given** un pago que cubre exactamente el saldo pendiente de una factura, **When** se confirma la aplicación, **Then** esa factura queda "Totalmente aplicada".
4. **Given** un pago que cubre solo una parte del saldo de una factura, **When** se confirma, **Then** esa factura queda "Parcialmente aplicada" por el resto pendiente.
5. **Given** una aplicación ya confirmada, **When** el usuario la anula, **Then** la factura vuelve a su estado anterior (recalculado, no un valor guardado que quedó desactualizado) y la anulación queda registrada con motivo, usuario y fecha — la fila original nunca se borra ni se edita.

---

### User Story 2 - Aplicar un cobro a uno o más documentos de venta pendientes (Priority: P1)

Como usuario que carga un cobro real, quiero aplicarlo contra uno o más documentos de venta (hacienda o granos) pendientes del mismo cliente/consignatario, con el mismo mecanismo que para pagos.

**Why this priority**: Simétrico a la Historia 1, y del lado de Ventas hoy no existe ni siquiera un saldo neto — es la pieza que falta construir desde cero para que Ingresos del flujo de caja por rubro deje de mostrar casi todo como "Sin rubro asignado".

**Independent Test**: cargar un cobro real vinculado a un consignatario con ventas pendientes, aplicarlo, y verificar que la venta pasa a su estado correspondiente.

**Acceptance Scenarios**:

1. **Given** un cobro real con contacto conocido y documentos de venta pendientes de ese contacto, **When** el usuario abre la pantalla de aplicación, **Then** el sistema sugiere las ventas más antiguas (FIFO) hasta cubrir el importe, editable.
2. **Given** que hoy no existe ningún registro de "documentos de venta pendientes de cobro", **When** se implementa esta historia, **Then** el sistema debe poder listar el estado de cobro de cada venta (Hacienda y Granos) igual que ya lo hace para compras.

---

### User Story 3 - Ver el estado de aplicación de un documento (Priority: P2)

Como usuario, quiero ver en cualquier momento si una factura de compra o un documento de venta está Pendiente, Parcialmente aplicado o Totalmente aplicado, y qué pago/cobro(s) lo cubrieron.

**Why this priority**: Sin esta visibilidad, la aplicación de pagos es una caja negra — el valor de la feature depende de poder auditarla.

**Independent Test**: abrir un documento con aplicaciones ya cargadas y verificar que el estado mostrado coincide con `SUM(ImporteAplicado)` de sus aplicaciones vigentes (no anuladas) comparado contra su importe total.

**Acceptance Scenarios**:

1. **Given** un documento con aplicaciones parciales, **When** el usuario lo consulta, **Then** ve el importe aplicado, el saldo pendiente, y el listado de pagos/cobros que lo aplicaron (con fecha y usuario).
2. **Given** una aplicación anulada, **When** el usuario consulta el historial del documento, **Then** la ve marcada como anulada (con motivo) sin que afecte el saldo pendiente actual.

---

### User Story 4 - Un pago aplicado alimenta el Rubro/Centro de Costos del flujo de caja (Priority: P2)

Como usuario, quiero que una vez que un pago/cobro tiene aplicaciones, el flujo de caja por rubro (018 v2) use esa aplicación para saber a qué Rubro/Centro de Costos corresponde, en vez de depender del matching exacto por importe/fecha que hoy falla casi siempre.

**Why this priority**: Es el motivo de negocio de toda la feature — sin esto, construir la aplicación de pagos no mejora nada visible para el usuario.

**Independent Test**: aplicar un pago a una factura con Rubro/Centro de Costos conocido, y verificar que el flujo de caja por rubro del período correspondiente ya no lo muestra como "Sin rubro asignado".

**Acceptance Scenarios**:

1. **Given** un movimiento bancario con una o más aplicaciones confirmadas, **When** se consulta el flujo de caja por rubro, **Then** el importe de ese movimiento se reparte entre los Rubros/Centros de Costos de los documentos aplicados, ponderado por el importe aplicado a cada uno.
2. **Given** un movimiento sin ninguna aplicación y posterior a la fecha de corte (01-09-2015), **When** se consulta el flujo de caja por rubro, **Then** se muestra explícitamente como pendiente de aplicar (no como "Sin rubro asignado" genérico — son dos situaciones distintas y deben distinguirse).
3. **Given** un movimiento anterior a la fecha de corte sin aplicación, **When** se consulta el flujo de caja por rubro, **Then** se muestra como "Histórico sin aplicar", una categoría explícita y distinta de las dos anteriores.

### Edge Cases

- ¿Qué pasa si la suma de aplicaciones de un documento supera su importe total? El sistema no debe permitirlo — valida al confirmar (con la tolerancia de redondeo que se defina, ver Assumptions).
- ¿Qué pasa si la suma de aplicaciones de un movimiento bancario supera el importe real de ese movimiento? Mismo caso — no debe permitirse.
- ¿Qué pasa si un pago se aplica a facturas de más de un contacto (ej. un consignatario que cobra centralizado por varios proveedores)? Debe permitirse — la diferencia de contacto entre movimiento y documento se señala como información, nunca bloquea la operación.
- ¿Qué pasa con los movimientos y documentos anteriores a la fecha de corte (01-09-2015)? No se exige aplicarlos retroactivamente; quedan identificados como "Histórico sin aplicar", una categoría explícita y permanente, no un estado transitorio a resolver.
- ¿Qué pasa si se anula una aplicación y el pago/cobro ya no tiene ninguna aplicación vigente? El movimiento vuelve a verse como no aplicado (mismo tratamiento que un movimiento nuevo posterior al corte sin aplicar).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE permitir aplicar un movimiento bancario real (pago) contra uno o más documentos de compra pendientes del mismo (u otro, ver FR-006) contacto, total o parcialmente.
- **FR-002**: El sistema DEBE permitir aplicar un movimiento bancario real (cobro) contra uno o más documentos de venta (Hacienda o Granos) pendientes, total o parcialmente.
- **FR-003**: El sistema DEBE sugerir automáticamente, al iniciar una aplicación, las facturas/documentos pendientes más antiguos del contacto (FIFO) hasta cubrir el importe del movimiento — la sugerencia debe ser editable por el usuario antes de confirmar.
- **FR-004**: El sistema NO DEBE aplicar automáticamente sin confirmación explícita del usuario.
- **FR-005**: Una aplicación confirmada DEBE ser inmutable: para corregirla, se anula (con motivo, usuario y fecha) y se crea una nueva — nunca se edita ni se borra una fila existente.
- **FR-006**: El sistema DEBE permitir que un movimiento se aplique a documentos de un contacto distinto al del movimiento, mostrando esa diferencia como información visible, sin bloquear la operación.
- **FR-007**: El sistema DEBE calcular el estado de cada documento (Pendiente / Parcialmente aplicado / Totalmente aplicado) a partir de sus aplicaciones vigentes en el momento de la consulta — nunca como un campo guardado que pueda desincronizarse.
- **FR-008**: El sistema DEBE impedir que la suma de aplicaciones vigentes de un documento supere su importe total, y que la suma de aplicaciones vigentes de un movimiento supere el importe real de ese movimiento (con la tolerancia de redondeo de Assumptions).
- **FR-009**: El sistema DEBE tratar los movimientos y documentos anteriores al 2015-09-01 como "Histórico sin aplicar" — una categoría explícita, no una obligación retroactiva.
- **FR-010**: El flujo de caja por rubro (018 v2) DEBE usar las aplicaciones vigentes de un movimiento como fuente primaria de Rubro/Centro de Costos cuando existan, y distinguir explícitamente entre "aplicado" / "posterior al corte sin aplicar" / "histórico sin aplicar" (nunca una única etiqueta genérica "Sin rubro asignado" que mezcle los tres casos).
- **FR-011**: Cualquier usuario autenticado DEBE poder anular una aplicación existente (sin restricción de rol adicional a la autenticación ya vigente).
- **FR-012**: El sistema DEBE construir, para Ventas (Hacienda y Granos), el equivalente de lo que hoy existe solo para Compras: poder listar los documentos de venta pendientes/parciales/totales de un contacto.

### Key Entities *(include if feature involves data)*

- **Aplicación de pago/cobro**: vincula un movimiento bancario real con un documento de deuda (compra) o crédito (venta), con un importe aplicado (puede ser parcial), fecha, usuario, y estado (vigente/anulada, con motivo si fue anulada).
- **Documento de deuda**: una compra (`Compras`/`Det_Compras`) con su importe total y las aplicaciones que la cubren.
- **Documento de crédito**: una venta (Hacienda o Granos) con su importe total y las aplicaciones que la cubren — hoy sin representación equivalente en el sistema, se construye en esta feature.
- **Movimiento bancario aplicable**: un ingreso o egreso real (BNA/Galicia/Efectivo/Valores) que puede tener cero, una o varias aplicaciones.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un pago nuevo (posterior al 2015-09-01) puede aplicarse a su(s) factura(s) correspondiente(s) en menos de 1 minuto desde que se identifica el contacto, gracias a la sugerencia automática.
- **SC-002**: Ningún documento ni movimiento queda nunca sobre-aplicado (0 casos, validado en cada confirmación).
- **SC-003**: Después de aplicar los pagos/cobros de un mes con volumen normal de operación, el % de movimientos "Sin rubro asignado" (excluyendo histórico e informativos) del flujo de caja por rubro baja sustancialmente respecto del matching exacto actual (referencia: hoy cercano al 90-100% en meses probados).
- **SC-004**: El estado de cualquier documento (Pendiente/Parcial/Total) mostrado en pantalla siempre coincide con el cálculo en vivo de sus aplicaciones — 0 discrepancias, porque nunca se guarda como valor fijo.

## Assumptions

- Fecha de corte confirmada por el dueño: **2015-09-01**. Los movimientos/documentos anteriores no requieren aplicación retroactiva; quedan permanentemente identificados como "Histórico sin aplicar". Aplicar ese backlog (2015-2026) si se decide hacerlo alguna vez es una decisión operativa separada, fuera del alcance de esta feature — esta feature solo construye la herramienta, no migra datos históricos.
- Criterio de sugerencia: FIFO (documento pendiente más antiguo primero), confirmado por el dueño, siempre editable antes de confirmar.
- Un pago puede aplicarse a documentos de un contacto distinto al del movimiento (confirmado por el dueño — ej. consignatarios que centralizan cobros/pagos de varios).
- Tolerancia de redondeo para considerar un documento "totalmente aplicado": el dueño pidió "ajustarse a usos y costumbres" sin dar un número — se toma como valor de partida una tolerancia de $1 (un peso), a confirmar/ajustar con el equipo de datos (`sql-server-engineer`) contra diferencias reales observadas de tipo de cambio/redondeo antes de implementar.
- Anulación de aplicaciones: sin restricción de rol — cualquier usuario autenticado puede hacerlo (confirmado por el dueño).
- Esta feature no incluye una pantalla de "conciliación uno a uno" (eso fue explícitamente descartado por el dueño como imposible en la práctica) ni migra/aplica el historial 2015-2026 — ambas cosas quedan fuera de alcance, a decidir en el futuro.
- Depende de 018-flujo-caja-real (movimientos bancarios ya normalizados) y de `Compras`/`Det_Compras` ya existentes. El lado de Ventas (Historia 2/FR-012) es la única pieza sin ningún precedente en el sistema y es la de mayor incertidumbre de diseño de datos — corresponde a `sql-server-engineer` definir si conviene una vista (como `vw_MovimientosCuenta_Base`) o una tabla nueva.
