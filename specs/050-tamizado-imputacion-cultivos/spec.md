# Feature Specification: Estructura de costos por cultivo y tamizado de facturas

**Feature Branch**: `050-tamizado-imputacion-cultivos`

**Created**: 2026-11-14

**Status**: Draft

**Input**: "Preparar el sistema para que impute a cultivo/campaña las facturas que ingresan cuando corresponda. Armar una estructura de costos genérica para cada cultivo y tamizar las facturas para determinar si corresponde imputarlas. Una factura puede tener ítems que se imputan y otros que no."

Las decisiones salen de las 50 preguntas respondidas por Sergio el 14/11/2026 ([preguntas-20261114.md](preguntas-20261114.md)).

Esta spec se apoya en la 049 y no reabre sus decisiones: los insumos cuentan por lo aplicado, rige desde la campaña 2025/2026 y la aprobación es automática con lista de revisión.

**Alcance (14/11/2026)**:
- Lo ya imputado no se toca.
- Los insumos de stock siguen la imputación progresiva por renglón de la spec 049: entran "en stock" y se imputan a medida que las órdenes los usan.
- El resto de los renglones (labores, seguros, fletes, estructura) se imputa de una vez según este tamizado.

## Contexto (datos WC, renglones desde el 01/07/2025)

- Hay 1.869 renglones en 688 facturas; 687 tienen rubro de cultivo.
- 392 de 480 renglones de insumos (82%) no tienen producto del catálogo.
- 18 facturas son mixtas. 6 de los 22 proveedores de cultivo también venden otras cosas.
- 59 renglones de cultivo tienen campaña "No Aplica" y 14 tienen destino "General".
- Hoy hay solo 9 reglas de clasificación.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Estructura de costos genérica (Priority: P1)

Cada cultivo/campaña muestra su costo ordenado en una plantilla común de 9 partes:

1. Semilla
2. Fertilizantes
3. Agroquímicos
4. Labores
5. Cosecha
6. Fletes
7. Seguro agrícola
8. Asesoramiento/análisis
9. Comercialización

Cada cultivo usa solo las partes que le corresponden. El resultado es **margen bruto**: los gastos generales quedan aparte, en "Estructura" de la campaña. La plantilla la mantiene Claude a pedido de Sergio; no hay pantalla de configuración.

**Why this priority**: es el molde contra el que se tamiza todo lo demás.

**Independent Test**: un cultivo/campaña 2025/26 muestra sus 9 partes, y la suma de las partes coincide con su costo total.

**Acceptance Scenarios**:

1. **Given** el maíz 2025/26 con secada, **When** se consulta, **Then** la secada aparece en Comercialización.
2. **Given** la soja, que no tiene secada, **When** se consulta, **Then** Comercialización no la muestra y el total no cambia.

---

### User Story 2 - Tamizado renglón por renglón (Priority: P1)

Al ingresar una factura, cada renglón se clasifica solo por su **rubro**. Una tabla fija rubro → destino dice si el renglón va a una parte del cultivo, a stock, a estructura, a ganadería, a resultado financiero o a "no se imputa". En una factura mixta, cada renglón decide por sí mismo.

**Why this priority**: es el pedido central ("hay ítems que se imputan y otros que no").

**Independent Test**: se pasan las 18 facturas mixtas por el tamiz y cada renglón queda con su destino según la tabla. Ninguno queda sin destino ni sin motivo.

**Acceptance Scenarios**:

1. **Given** una factura con un renglón de herbicida y otro de repuestos, **When** se tamiza, **Then** el herbicida va a stock (después, a lo aplicado) y los repuestos a estructura.
2. **Given** un renglón de Movilidad con campaña cargada, **When** se tamiza, **Then** va a la lista de revisión porque el rubro y la campaña se contradicen.
3. **Given** un renglón de texto libre ("servicio varios") que no indica cultivo ni labor, **When** se tamiza, **Then** queda sin imputar y en la lista, con el texto a la vista.

---

### User Story 3 - Cultivo y campaña de cada renglón (Priority: P1)

Para los renglones que van a cultivo, el sistema determina el cultivo y la campaña. El orden de prioridad es fijo:

1. La imputación manual del renglón.
2. Lo aplicado por la orden, en el caso de los insumos.
3. La regla por producto.
4. La regla por rubro.
5. Si nada de lo anterior resuelve, la lista de revisión.

Si falta el cultivo o la campaña, el sistema lo deduce por grano, fecha u orden más cercana. Si queda una sola opción, imputa; si no, el renglón va a la lista.

**Why this priority**: sin cultivo/campaña el tamizado no llega al resultado.

**Independent Test**: los 59 renglones con "No Aplica" y los 14 con "General" quedan con una propuesta en la lista, y ninguno se imputa sin aprobación.

**Acceptance Scenarios**:

1. **Given** un seguro agrícola facturado en agosto, **When** se imputa, **Then** va a la campaña asegurada.
2. **Given** un flete de granos de maíz, **When** se imputa, **Then** va a la campaña de cosecha de ese maíz.
3. **Given** herbicida de barbecho de invierno, **When** se imputa, **Then** va al cultivo que se siembra después.
4. **Given** una fecha de labor entre dos campañas sin orden que lo resuelva, **When** se imputa, **Then** va a la lista.

---

### User Story 4 - Costos que se reparten (Priority: P2)

Algunos costos son de la campaña y no de un cultivo: asesoramiento sin cultivo y Comercialización común. (El arrendamiento es un ingreso de la empresa, no un costo.) Esos se reparten entre los cultivos de la campaña según la **superficie del plan agrícola**. El costo se lleva por cultivo/campaña, sin lote. Las labores de contratista mantienen el reparto por lote de la spec 048.

**Why this priority**: evita inflar un cultivo y dejar a otro sin costo.

**Independent Test**: un asesoramiento de una campaña con fina y gruesa se reparte entre los dos cultivos por superficie planificada y suma el total de la factura al centavo.

**Acceptance Scenarios**:

1. **Given** un asesoramiento de campaña de $1.000.000 y un plan con 60 ha de trigo y 40 ha de soja en el mismo campo, **When** se reparte, **Then** trigo recibe $600.000, soja $400.000, y no se asigna lote.

---

### User Story 5 - Insumos sin producto del catálogo (Priority: P2)

Para cada renglón de insumo sin producto del catálogo (hoy el 82%), el sistema propone el producto leyendo la descripción.
- Si está seguro, lo asigna; si no, el renglón va a la lista.
- Cuando Sergio corrige, el sistema pregunta "¿aplicar siempre a este producto?" y, si la respuesta es sí, guarda la regla.

**Why this priority**: sin producto, el insumo no se puede seguir hasta lo aplicado (spec 049).

**Independent Test**: sobre los 392 renglones, se mide cuántos quedan con producto asignado solo y cuántos en la lista.

**Acceptance Scenarios**:

1. **Given** un renglón "GLIFOSATO 66% x 20 L" sin producto, **When** se tamiza, **Then** se le asigna el producto de catálogo que coincide sin ambigüedad.
2. **Given** una descripción con dos productos posibles, **When** se tamiza, **Then** va a la lista con las dos opciones.

---

### User Story 6 - Pantalla "Para revisar" y sugerencia al cargar (Priority: P2)

Al cargar una compra, cada renglón ya viene con su sugerencia marcada como "sugerido" y una etiqueta clara: "A cultivo", "Va a stock", "Gasto general" o "Ganadería". Se puede cambiar con un clic.

La pantalla "Para revisar" muestra:
- los dudosos arriba;
- el resto agrupado por día de carga.

Un contador en el menú avisa cuántos hay para revisar. No se mandan mails.

**Why this priority**: es la contrapartida de "automático + lista".

**Independent Test**: se carga una factura mixta y se ve la sugerencia en cada renglón; después aparece en "Para revisar" y el contador suma uno.

**Acceptance Scenarios**:

1. **Given** tres dudosos, **When** Sergio abre el sistema, **Then** el menú muestra "3 para revisar".
2. **Given** un dudoso, **When** Sergio elige la opción correcta, **Then** queda aprobado y el resultado del cultivo se actualiza.

---

### User Story 7 - Informe de costos por cultivo/campaña (Priority: P3)

El informe muestra cada cultivo/campaña:
- por parte de la estructura, con $/ha y US$/ha;
- con apertura hasta la factura o la orden;
- al pie, la Estructura de la campaña aparte y lo que sigue en stock sin consumir.

**Independent Test**: para un cultivo 2025/26, abrir una parte llega a los documentos que la forman, y la suma de esos documentos coincide con la parte.

### Edge Cases

- **Factura mixta de un proveedor que vende de todo**: cada renglón decide por su rubro, y nunca por el proveedor.
- **Semilla o insumo que pone el contratista dentro de su factura de labor**: se separa de la labor y entra a stock. Después lo consume la orden.
- **Semillas**: pasan por stock y las consume la orden de siembra. La semilla propia se valúa al precio del grano cuando se reservó.
- **Sobrante al cerrar la campaña**: sigue en stock con su costo y lo paga el cultivo que lo aplique.
- **Insumo vencido o dado de baja por mantenimiento**: va a Estructura como pérdida de la empresa. La diferencia normal del recuento sigue repartiéndose en las órdenes del período.
- **Bolsas de silo, hilo y mallas**: entran a stock como cualquier insumo y las imputa la orden de embolsado o enrollado, según lo que se guarda: grano para vender → Comercialización de ese cultivo; forraje → cultivo forrajero; grano para consumo propio → Ganadería.
- **Cultivo de cobertura**: es un cultivo propio, con su resultado.
- **Pasturas y verdeos**: son cultivo forrajero con campaña propia; su costo pasa después a la hacienda.
- **Rollos y silos**: van al cultivo forrajero; al consumirse pasan a ganadería al costo.
- **Sanidad, pastaje y rastrojo pastoreado**: van a ganadería y nunca al cultivo.
- **Gastos compartidos** (alambrados, molinos, sueldos de Sierra e Irma): van a Estructura.
- **Gasoil**: va al cultivo solo con una orden de labor propia que lo consume; si no, a Estructura.
- **Impuestos**: IVA y Ganancias no se imputan nunca. Inmobiliario y tasas van a Estructura. Ingresos Brutos de la venta va a Comercialización.
- **Intereses de un insumo financiado** (canje, plazo): van al cultivo de ese insumo. El resto de intereses, gastos bancarios y diferencias de cambio es resultado financiero.
- **Notas de crédito**: copian en proporción la imputación de la factura que corrigen. Si el insumo pasó por stock, bajan el precio de lo aplicado. Si no tienen factura relacionada, van a la lista.
- **Bienes de uso**: no son gasto del cultivo; se amortizan más adelante, a Estructura.
- **Facturas de la Sucesión o de socios que son gasto del campo**: se imputan por rubro. Las compras particulares (Particular L/S) no se imputan nunca.
- **Proveedor genérico de compras chicas**: se imputa si el rubro es de cultivo, y siempre pasa por la lista.
- **Cosecha pagada en grano**: se valúa con la liquidación del grano entregado y va a Cosecha.
- **US$**: se toma al TC del comprobante y el informe muestra $/ha y US$/ha.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST tener una única plantilla de estructura de costos con las 9 partes de la Historia 1. Cada cultivo puede desactivar partes.
- **FR-002**: El sistema MUST mantener una tabla fija rubro → destino. Los destinos posibles son: parte de la estructura, stock, Estructura, Ganadería, Resultado financiero o No se imputa. La tabla se arma con Sergio una sola vez, cubre todos los rubros en uso desde 2025/26 y la mantiene Claude a pedido.
- **FR-003**: Cada renglón MUST clasificarse por sí mismo, sin heredar el destino de otro renglón ni del proveedor. No hay reglas por proveedor.
- **FR-004**: El destino de un renglón MUST resolverse en este orden: imputación manual > lo aplicado por orden (insumos) > regla por producto > regla por rubro > lista de revisión.
- **FR-005**: Un renglón se imputa solo únicamente si no hay ninguna duda en producto o labor, cultivo y campaña. Cualquier diferencia de cantidad o hectáreas, ambigüedad o contradicción MUST mandarlo a la lista con el motivo.
- **FR-006**: La campaña MUST salir de la fecha de la labor u orden. Sin orden, sale de la campaña que el gasto atiende; si eso no se puede determinar, de la fecha del comprobante, y el renglón va a la lista.
- **FR-007**: Los costos de campaña sin cultivo puntual MUST repartirse entre los cultivos de la campaña según la superficie del plan agrícola, a nivel cultivo/campaña y sin lote. El reparto por lote de las labores de contratista (048) no cambia.
- **FR-008**: Para los renglones de insumo sin producto del catálogo, el sistema MUST proponer el producto. Lo asigna solo si la coincidencia es única; si no, el renglón va a la lista.
- **FR-009**: Al corregir una imputación, el sistema MUST ofrecer guardar la corrección como regla por producto.
- **FR-010**: Una semilla o un insumo incluido en una factura de labor MUST separarse de la labor y entrar a stock.
- **FR-011**: Las bajas por vencimiento o mantenimiento MUST imputarse a Estructura como pérdida. La diferencia de recuento conserva la regla vigente.
- **FR-012**: Las notas de crédito MUST seguir la imputación de la factura relacionada, en proporción.
- **FR-013**: Los intereses identificados como financiación de un insumo MUST ir al cultivo de ese insumo. El resto de los gastos financieros va a Resultado financiero.
- **FR-014**: Al cargar una compra, la pantalla MUST mostrar cada renglón con su destino sugerido y una etiqueta legible, editable con un clic. No se muestran identificadores internos.
- **FR-015**: El sistema MUST ofrecer la pantalla "Para revisar" (dudosos arriba, el resto por día de carga) y un contador en el menú.
- **FR-016**: El informe por cultivo/campaña MUST mostrar las partes de la estructura con $/ha y US$/ha, abrir hasta el documento o la orden, y mostrar aparte la Estructura y lo que sigue en stock sin consumir.
- **FR-017**: Cualquier cambio de orden, remito, regla o tabla MUST recalcular lo afectado desde 2025/26, nunca antes, y dejar historial (fecha, qué cambió, cuánto movió) visible en la lista.
- **FR-018**: Las compras particulares (Particular L/S) MUST NOT imputarse a cultivo. Lo de San Justo sigue bloqueado.

### Key Entities

- **Parte de la estructura**: una de las 9 partes del costo de un cultivo.
- **Regla de rubro**: asocia un rubro con un destino (parte, Stock, Estructura, Ganadería, Financiero, No se imputa) o con "depende".
- **Regla de producto**: un producto con su destino o parte. Puede venir de una corrección de Sergio.
- **Renglón tamizado**: el renglón de factura con su destino, cultivo, campaña, motivo, origen de la decisión (manual, orden, producto, rubro) y estado (aprobado o pendiente).
- **Reparto de campaña**: la distribución de un costo común según la superficie del plan agrícola.
- **Historial de cambios**: la fecha, el cambio y el importe que movió.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100% de los renglones 2025/26 tienen destino o están en la lista con su motivo; ninguno queda sin clasificar.
- **SC-002**: Al menos el 85% de los renglones nuevos se clasifican sin intervención.
- **SC-003**: Al menos el 70% de los 392 insumos sin producto quedan con producto asignado solo; el resto está en la lista.
- **SC-004**: En cada cultivo/campaña 2025/26, la suma de las partes más la Estructura y lo que sigue en stock iguala lo facturado imputable, al centavo.
- **SC-005**: Las campañas anteriores a 2025/26 no cambian: la diferencia contra antes es $0,00.
- **SC-006**: Un documento cargado aparece en "Para revisar" el mismo día.

## Assumptions

- Depende de la spec 049 (lo aplicado manda, vínculo remito↔factura y factura↔orden).
- El plan agrícola tiene superficie por cultivo/campaña desde 2025/26; si falta, el reparto va a la lista.
- No se trabaja sobre facturas anteriores a 2015.
- Las escrituras van solo a WC y no quedan registros de prueba.
- La amortización de bienes de uso queda fuera de esta spec: solo se marca su destino como Estructura.
