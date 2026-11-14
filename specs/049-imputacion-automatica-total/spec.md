# Feature Specification: Imputación automática total a cultivo/campaña

**Feature Branch**: `049-imputacion-automatica-total`

**Created**: 2026-11-14

**Status**: Draft

**Input**: User description: "Toda factura que ingresó o ingrese se imputa sola a cultivo/campaña cuando aplica, sin doble conteo. Decisiones de Sergio (14/11/2026): insumos = lo aplicado; desde la campaña 2025/2026; aprobación automático + lista."

## Contexto (diagnóstico 14/11/2026)

- **Labores de contratista**: el reparto por órdenes respeta la imputación manual de cada renglón (048). La vinculación factura↔orden sigue siendo manual.
- **Insumos**: entran al costo del cultivo por dos caminos a la vez y quedan **contados dos veces**:
  - el renglón de factura imputado a mano;
  - el consumo de las órdenes valuado por stock.
- **Remitos sin factura**: sin el vínculo remito↔factura, el stock no tiene costo y lo consumido vale $0.
  - 2026: 0 de 32 renglones de remito vinculados.
  - 2025: 15 de 61 renglones vinculados.
- **Valuación sin explicar**: Maíz 2024/25 da $64 M por órdenes contra $5 M por factura.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Insumos: el costo es lo aplicado, sin doble conteo (Priority: P1)

Sergio mira el resultado de un cultivo/campaña 2025/2026 en adelante:
- Los insumos aparecen **una sola vez**: lo que las órdenes aplicaron, valuado al precio de su factura.
- Lo comprado que sigue en el depósito figura como "en stock sin consumir" y no como costo de ningún cultivo.

**Why this priority**: hoy el resultado está mal (doble conteo o consumo en $0). Es la base de todo lo demás.

**Independent Test**: tomar una campaña 2025/2026 y comprobar:
- el costo de insumos del cultivo = consumo de sus órdenes valuado;
- ningún renglón de factura de insumo que pasó por stock suma además por su imputación manual.

**Acceptance Scenarios**:

1. **Given** una factura de herbicida con remito y una orden que aplicó la mitad en Soja 2025/26, **When** se consulta el resultado, **Then** Soja 2025/26 suma solo esa mitad al costo de la factura y la otra mitad figura en stock sin consumir.
2. **Given** el mismo renglón imputado a mano a Soja 2025/26, **When** se consulta el resultado, **Then** ese renglón no se suma por segunda vez.
3. **Given** una campaña anterior a 2025/2026, **When** se consulta su resultado, **Then** queda exactamente como estaba.

---

### User Story 2 - Vínculo automático remito ↔ factura (Priority: P1)

Al cargar una factura de insumos o un remito, el sistema busca su par por proveedor, producto, cantidad y fecha y los vincula solo.
- Así el stock queda valuado al costo real.
- Lo que no encaja con certeza queda en una lista para revisar.

**Why this priority**: sin este vínculo lo aplicado vale $0 y la Historia 1 no puede funcionar.

**Independent Test**: correrlo sobre los remitos 2025/2026 sin factura y comprobar:
- cuántos quedan vinculados solos y cuántos en la lista;
- que ninguna cantidad de factura se vincule más de una vez.

**Acceptance Scenarios**:

1. **Given** un remito de 200 l de glifosato del proveedor X y una factura del mismo proveedor con 200 l de ese producto, de fecha cercana, **When** se carga cualquiera de los dos, **Then** quedan vinculados y aprobados, y aparecen en la lista de revisión.
2. **Given** dos facturas posibles para el mismo remito, **When** corre el vínculo, **Then** no vincula ninguna y lo deja en la lista de dudosos.
3. **Given** una entrega parcial (remito 100 l, factura 200 l), **When** llega el segundo remito, **Then** ambos remitos quedan vinculados a la misma factura hasta completar la cantidad.

---

### User Story 3 - Vínculo automático factura de contratista ↔ orden (Priority: P2)

Al cargar una factura de labor:
- El sistema busca las órdenes del contratista que encajan por labor, cultivo, campaña, hectáreas y fecha. Pueden ser varias órdenes por factura.
- Si encaja, vincula y reparte solo, respetando la imputación de cada renglón.
- Si no encaja, la deja pendiente con el detalle.

**Why this priority**: el reparto ya existe (048); falta que la vinculación no dependa de Sergio.

**Independent Test**: cargar una factura de labor con sus renglones imputados y comprobar que queda vinculada y repartida sin intervención.

**Acceptance Scenarios**:

1. **Given** una factura de Pérez por 120 ha de pulverización de Soja 2025/26 y una orden ejecutada de 118 ha de Soja 2025/26, **When** se guarda la factura, **Then** queda vinculada, repartida por lote y aprobada.
2. **Given** una factura con un cultivo sin orden, **When** se guarda, **Then** ese importe queda en su cultivo/campaña sin lote y la factura aparece en la lista.
3. **Given** una nota de crédito que anula una factura, **When** se carga, **Then** se ofrece relacionarla con la factura anulada y esta deja de buscar orden.

---

### User Story 4 - Lista de revisión de lo imputado automáticamente (Priority: P2)

Sergio abre una pantalla con todo lo que el sistema vinculó o imputó solo, agrupado por día de carga:
- cada documento con su cultivo/campaña y lote;
- los dudosos aparte, para aprobar o corregir.

**Why this priority**: es la contrapartida de "automático + lista" (regla de revisión de cargas automáticas, 043).

**Independent Test**: después de cargar documentos nuevos, la pantalla muestra cada uno con su imputación y permite corregirla.

**Acceptance Scenarios**:

1. **Given** cinco documentos imputados solos hoy, **When** Sergio abre la lista, **Then** ve los cinco con su destino y puede abrir cada uno.
2. **Given** un vínculo dudoso, **When** Sergio elige la opción correcta, **Then** queda aprobado y el resultado del cultivo se actualiza.

---

### User Story 5 - Control de cierre por campaña (Priority: P3)

Por cada producto y campaña, el sistema muestra el control **comprado = aplicado + en stock + ajustes de recuento**, con la diferencia a la vista.

**Why this priority**: es la prueba de que no se pierde ni se duplica costo.

**Independent Test**: para la campaña 2025/2026, la diferencia por producto es cero o queda explicada.

**Acceptance Scenarios**:

1. **Given** un producto comprado, usado en parte y recontado, **When** se mira el control, **Then** las tres partes suman lo comprado al centavo, o se muestra la diferencia.

---

### Edge Cases

- **Factura de insumo sin remito** (entrega directa, compra chica): se considera ingresada a stock a la fecha de la factura, y la consume la orden que corresponda.
- **Insumo comprado y aplicado en otra campaña**: el costo va a la campaña de la orden que lo aplicó, no a la de la factura.
- **Factura en US$**: se valúa al tipo de cambio del comprobante (regla US$ al TC del comprobante).
- **Recuento con faltante**: se reparte en las órdenes del período, como hoy; sin órdenes no se imputa.
- **Orden anulada o modificada después de aprobada**: el reparto se recalcula solo y queda en la lista de revisión.
- **Documento de San Justo o de la Sucesión**: se aplican las reglas vigentes (San Justo bloqueado; Sucesión = gasto de Giamigli).
- **Costos directos sin stock** (seguros agrícolas, análisis, cosecha, fletes de granos): siguen por la imputación manual del renglón.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Desde la campaña 2025/2026, el costo de insumos de un cultivo/campaña MUST ser el consumo de sus órdenes de trabajo valuado al costo de la factura del insumo consumido, por orden de entrada.
- **FR-002**: Un renglón de factura de insumo que ingresó a stock MUST NOT sumar al resultado por su imputación manual. Su imputación manual queda solo como referencia.
- **FR-003**: Lo comprado y no consumido MUST figurar como "en stock sin consumir", valuado, y no como costo de cultivo.
- **FR-004**: El sistema MUST proponer y aplicar el vínculo remito↔factura por proveedor, producto, cantidad y cercanía de fecha, incluidas las entregas parciales. Cada cantidad facturada se vincula como máximo una vez.
- **FR-005**: Un vínculo con una única coincidencia clara MUST quedar aprobado solo. Uno con varias coincidencias o con cantidades que no cierran MUST quedar pendiente en la lista de revisión.
- **FR-006**: Al guardar una factura de labor, el sistema MUST buscar las órdenes ejecutadas del contratista que encajen (labor, cultivo, campaña, hectáreas, fecha), vincularlas y repartir según la regla de 048, que respeta la imputación manual por renglón.
- **FR-007**: El sistema MUST detectar notas de crédito que anulan una factura completa y proponer relacionarlas, para que la factura anulada no se impute.
- **FR-008**: Cualquier cambio en órdenes, remitos, vínculos o recuentos MUST recalcular solo lo afectado y dejar el cambio visible en la lista de revisión.
- **FR-009**: El sistema MUST ofrecer una pantalla de revisión con lo imputado automáticamente y lo pendiente. Desde ahí se puede aprobar o corregir, sin mostrar identificadores internos.
- **FR-010**: El sistema MUST mostrar por producto y campaña el control comprado = aplicado + stock + ajustes, con la diferencia a la vista.
- **FR-011**: Los resultados de campañas anteriores a 2025/2026 MUST NOT cambiar.
- **FR-012**: Antes de activar el criterio nuevo, el sistema MUST producir un informe de impacto por cultivo/campaña (antes/después). La valuación de Maíz 2024/25 se diagnostica en ese informe sin modificarla.
- **FR-013**: Una facturación de insumo sin remito MUST entrar a stock a la fecha de la factura para poder ser consumida.

### Key Entities

- **Renglón de factura**: producto o labor, cantidad, importe, imputación manual (cultivo/campaña).
- **Remito y su renglón**: entrada física de un producto; se vincula a uno o varios renglones de factura.
- **Capa de stock**: cantidad ingresada con su costo unitario (de la factura); se consume por orden de entrada.
- **Orden de trabajo**: labor aplicada en lotes con cultivo/campaña y superficie; consume capas.
- **Imputación**: fracción de costo con cultivo, campaña, lote, origen (consumo, labor, manual), estado (automática aprobada, pendiente) y fecha de cálculo.
- **Lista de revisión**: imputaciones y vínculos hechos por el sistema, con fecha y motivo.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: En las campañas 2025/2026 y siguientes, el costo de insumos de cada cultivo no tiene doble conteo: ningún renglón suma dos veces.
- **SC-002**: Al menos el 90% de los remitos y facturas de insumo 2025/2026 quedan vinculados sin intervención. El resto aparece en la lista con su motivo.
- **SC-003**: Al menos el 90% de las facturas de labor nuevas quedan vinculadas a sus órdenes y repartidas sin intervención.
- **SC-004**: En el control por campaña, comprado = aplicado + stock + ajustes cierra al centavo para el 100% de los productos, o cada diferencia queda listada.
- **SC-005**: Los resultados de campañas anteriores a 2025/2026 no cambian: diferencia $0,00 contra antes.
- **SC-006**: Un documento nuevo aparece imputado en la lista de revisión el mismo día en que se carga.

## Assumptions

- El recuento del 15/12/2025 es el corte desde el que el stock es confiable (memoria de recuentos históricos).
- Las facturas de insumos se cargan con producto vinculado al catálogo; los renglones sin producto quedan en la lista.
- La regla de 048 (la imputación manual por renglón manda, las órdenes ponen los lotes) se mantiene para las labores.
- No se trabaja sobre facturas anteriores a 2015.
- Las escrituras van solo a la base de trabajo WC, nunca a LaHerencia.
- No quedan registros de prueba en WC.
