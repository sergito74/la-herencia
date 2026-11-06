# Feature Specification: Vínculo de órdenes de trabajo con documentos del contratista

**Feature Branch**: `main` (sin rama propia, como las specs 043-047)

**Created**: 2026-11-06

**Status**: Draft

**Input**: User description: "No funciona el vínculo desde la orden de trabajo con los documentos comerciales (Facturas, Notas de Débito y Crédito) del contratista que ejecutó la orden. El objetivo es no tener que imputar manualmente los documentos comerciales a cada Cultivo / Campaña, sino que el sistema lo haga automáticamente para luego imputar los costos a los Costos / Resultados de los cultivos y al Flujo de Caja." (Sergio, 06/11/2026)

## Contexto y diagnóstico (verificado en WC el 06/11/2026)

- La orden de trabajo pide tipear un número interno de compra para vincular la factura. Es inusable y contradice la premisa "interfaz sin cosas internas".
- Nunca se vinculó ningún documento: 0 vínculos para 152 órdenes ejecutadas. Access tampoco tenía este vínculo.
- Vincular no genera la imputación automática por cultivo/campaña: hay 0 imputaciones de contratista.
- El Resultado por cultivo busca los vínculos en un registro viejo (vacío), distinto del que escribe la orden. Además imputa la factura por el cultivo/campaña cargado a mano en cada renglón, que es justamente lo que se quiere dejar de hacer.
- Hay 12 contratistas con órdenes desde 2015, con 94 facturas y 6 NC/ND en ese período.

## Decisiones tomadas (Sergio, 06/11/2026)

- **D1 Siempre confirmar**: el sistema propone qué documentos corresponden a qué órdenes; ningún vínculo queda hecho sin el OK del usuario.
- **D2 NC/ND siguen a su factura**: se imputan igual (cultivos, campañas y proporción) que la factura que corrigen.
- **D3 Alcance histórico completo**: todas las órdenes ejecutadas desde 2015.
- **D4 Flujo de Caja fuera de alcance**: queda como está; solo importa el Resultado por cultivo.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Vincular desde la orden eligiendo de una lista (Priority: P1)

Al abrir una orden de trabajo, el usuario ve los documentos (facturas, NC, ND) del contratista que la ejecutó y no vinculados a otra orden, con fecha, número, hectáreas e importe. Los sugeridos aparecen primero y marcados como sugerencia. Tilda los que corresponden y confirma.

**Why this priority**: es lo que hoy no funciona y desbloquea todo lo demás.

**Independent Test**: abrir la orden 162 (Pérez, 25/10/2026, 198 ha); la factura 00002-00000735 (05/11/2026, 198 ha) aparece sugerida; al tildarla y confirmar queda vinculada sin tipear ningún número.

**Acceptance Scenarios**:

1. **Given** una orden con contratista, **When** se abre, **Then** la lista muestra solo documentos de ese contratista, sin números internos.
2. **Given** un documento vinculado, **When** el usuario lo destilda y confirma, **Then** se desvincula y su imputación se retira.
3. **Given** una orden de maquinaria propia o sin documentos del contratista, **Then** se informa que no hay documentos para vincular.

---

### User Story 2 - Imputación automática a cultivo y campaña (Priority: P1)

Al confirmarse el vínculo, el importe neto del documento se reparte entre los lotes/cultivos/campañas de las órdenes vinculadas en proporción a su superficie, sin que el usuario cargue cultivo ni campaña. El Resultado por cultivo toma ese reparto, una sola vez.

**Why this priority**: es el objetivo del pedido.

**Independent Test**: vincular una factura a una orden con dos cultivos; el Resultado de cada cultivo/campaña muestra la parte proporcional y la suma da el neto de la factura al centavo.

**Acceptance Scenarios**:

1. **Given** una factura vinculada a varias órdenes, **Then** se reparte por la superficie de todas ellas y la suma cierra al centavo.
2. **Given** una factura que ya tenía cultivo/campaña cargado a mano en sus renglones, **When** se confirma el vínculo, **Then** el Resultado usa el reparto de la orden y no cuenta el cargado a mano (sin doble conteo).
3. **Given** una NC/ND relacionada con una factura vinculada, **Then** se imputa en los mismos cultivos/campañas y proporción, con su signo.
4. **Given** una factura en dólares, **Then** se usa el tipo de cambio del comprobante.

---

### User Story 3 - Revisar en bloque las propuestas del histórico (Priority: P2)

Una pantalla lista, por contratista, cada factura con las órdenes que el sistema le propone (fecha, hectáreas facturadas, hectáreas de las órdenes, diferencia). El usuario confirma, corrige o descarta cada propuesta. Las que no cierran quedan a la vista con el motivo ("hectáreas no coinciden", "sin orden", "factura en otra unidad").

**Why this priority**: cubre el histórico (D3) sin ir orden por orden; depende de US1/US2.

**Independent Test**: abrir la revisión de Pérez; cada factura tiene su propuesta con la diferencia de hectáreas; confirmar una la vincula e imputa como en US1/US2.

**Acceptance Scenarios**:

1. **Given** una factura con hectáreas coincidentes, **Then** figura como propuesta con diferencia menor al 10%, a la espera de confirmación (D1).
2. **Given** una factura sin orden que la explique, **Then** figura como "sin orden" y no se imputa.
3. **Given** una propuesta descartada, **Then** no vuelve a proponerse igual salvo que cambien los datos.

---

### Edge Cases

- Facturas de un contratista que factura en litros, pesos o "servicio" en vez de hectáreas: se proponen por fecha, con la diferencia marcada como "otra unidad".
- Una factura que cubre varias órdenes, y una orden con varias facturas (anticipo + saldo).
- Orden anulada después del vínculo: el vínculo se retira y la imputación se recalcula.
- Corrección de hectáreas en la orden después del vínculo: el reparto se recalcula.
- Orden de un rubro sin cultivo (ej. mantenimiento): va al centro de costo de la orden, como ya prevé la imputación 017.
- Contratista "Giamigli de Bolívar" (maquinaria propia, sin documentos): no se proponen documentos.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: La orden de trabajo MUST mostrar una lista tildable de documentos (Factura, NC, ND) del contratista de la orden, con fecha, número, hectáreas e importe formateados, sin identificadores internos.
- **FR-002**: El sistema MUST proponer vínculos factura→órdenes con esta regla: mismo contratista, órdenes ejecutadas en o antes de la fecha de la factura y después de la factura anterior del mismo contratista (máximo 90 días), comparando hectáreas facturadas con las de las órdenes.
- **FR-003**: Ningún vínculo MUST quedar hecho sin la confirmación explícita del usuario (D1); las propuestas no afectan costos hasta confirmarse.
- **FR-004**: Al confirmar o retirar un vínculo, el sistema MUST recalcular de inmediato el reparto del documento por cultivo/campaña/lote según la superficie de las órdenes vinculadas.
- **FR-005**: Las NC/ND relacionadas con una factura vinculada MUST imputarse con el mismo reparto proporcional y su signo (D2), sin vínculo propio a la orden.
- **FR-006**: El Resultado por cultivo MUST tomar el costo de contratista desde el reparto de los vínculos confirmados, y MUST excluir para esos documentos el cultivo/campaña cargado a mano en sus renglones (sin doble conteo).
- **FR-007**: Los documentos de contratista no vinculados MUST seguir contando como hoy (por su carga manual), para que el Resultado no pierda costos mientras se revisa el histórico.
- **FR-008**: La revisión en bloque MUST listar todas las facturas de contratistas desde 2015 con su propuesta, la diferencia de hectáreas y el motivo cuando no cierra.
- **FR-009**: Los saldos de cuentas corrientes MUST quedar iguales al centavo: el vínculo no modifica importes, fechas ni imputaciones de pago.
- **FR-010**: El Flujo de Caja queda como está; esta funcionalidad no lo modifica (D4). El reparto por cultivo/campaña se usa solo en Costos/Resultado por cultivo.
- **FR-011**: El vínculo MUST registrar quién y cuándo lo confirmó.

### Key Entities

- **Orden de trabajo**: labor ejecutada por un contratista, con fecha y distribución por lote/cultivo/campaña y superficie.
- **Documento del contratista**: factura, NC o ND, con renglones (hectáreas, precio), moneda y tipo de cambio.
- **Vínculo orden–documento**: relación muchos a muchos confirmada por el usuario; tiene un estado: propuesto, confirmado o descartado.
- **Reparto (imputación)**: porción del neto del documento asignada a cada lote/cultivo/campaña.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Vincular un documento a una orden toma menos de 30 segundos y no requiere conocer ningún número interno.
- **SC-002**: El 100% de los documentos vinculados queda imputado a cultivo/campaña sin carga manual, y la suma del reparto de cada uno coincide con su neto al centavo.
- **SC-003**: Tras la revisión del histórico, cada una de las 94 facturas de contratistas desde 2015 está vinculada, descartada con motivo o marcada "sin orden": ninguna queda sin estado.
- **SC-004**: El costo de contratista de una campaña en el Resultado no cambia por contar dos veces un mismo documento (control: total antes de vincular = total después, salvo diferencias de reparto entre cultivos que se muestran).
- **SC-005**: Ningún saldo de cuenta corriente cambia (comparación antes/después al centavo).

## Assumptions

- Se reutiliza la imputación automática existente (spec 017) para el reparto por superficie y el centro de costo de órdenes sin cultivo.
- El registro viejo de vínculos (vacío) se deja de usar; el Resultado pasa a leer el registro único que escribe la orden.
- "Hectáreas facturadas" = suma de cantidades en renglones con unidad hectárea (o sin unidad); otras unidades se marcan como "otra unidad".
- La regla de 10% es solo para ordenar y rotular propuestas; nunca confirma sola (D1).
- La NC/ND se asocia a su factura a través de los documentos relacionados ya cargados; si no tiene, se propone como un documento más para revisar.
- Todo se escribe en la base WC.
