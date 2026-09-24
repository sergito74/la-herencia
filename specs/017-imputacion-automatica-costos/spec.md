# Feature Specification: Motor de auto-clasificación de Rubro/Centro de Costos/Cultivo/Campaña

**Feature Branch**: `017-imputacion-automatica-costos`

**Created**: 2026-09-23

**Status**: Draft

**Input**: User description: "Motor de auto-clasificación de Rubro/Centro de Costos/Cultivo/Campaña para facturas de insumos y contratistas. Hoy el usuario elige a mano el Centro de Costos/Rubro/Campaña de cada renglón de una Compra al cargarla (spec 006). Ese valor queda fijo aunque después el insumo se consuma (vía Remitos→FIFO→Órdenes de Trabajo, specs 010/011) en una campaña distinta a la declarada, o un contratista facture un trabajo que recién después se vincula a una Orden. Construir un motor que, siguiendo la cadena real factura→remito→consumo FIFO→orden→distribución por lote/cultivo/campaña, calcule automáticamente cómo se reparte el costo de cada renglón de factura (insumo o contratista) entre Agricultura/Ganadería y Cultivo/Campaña según el consumo real, como propuesta pendiente de aprobación, en paralelo al motor de costeo heredado (spec 012) sin reemplazarlo todavía."

## Clarifications

### Ampliación de presentación — 2026-09-24

- En Imputación automática y por documento comercial, cada fracción debe mostrar cantidad de insumo y unidad junto con su importe.
- Mostrar un resumen por Cultivo/Campaña con detalle desplegable de insumos y fracciones. Mantener stock, Ganadería, otros centros e intervención separados. Las cantidades solo se suman por insumo y unidad; los importes del motor se expresan en pesos.
- En automática, identificar la propuesta por nombre de insumo/servicio y encabezado del documento (proveedor, tipo, número, fecha y moneda), incluso al ingresar desde Revisar. Los identificadores internos quedan para navegación y trazabilidad.
- Conservar estados, correcciones e importes existentes. Las cantidades históricas solo se completan cuando pueden reconstruirse sin ambigüedad; de otro modo indicar que no están registradas. Contratistas no llevan cantidad de insumo.

### Sesión 2026-09-23 (25 preguntas + 3 de seguimiento, con los agentes especialistas: producción agrícola, dirección financiera, SQL Server)

- **Valor del costo vs. destino del costo**: el importe de cada renglón de factura se fija en el momento de la compra, igual que hoy (el FIFO de Remitos, spec 010, no revaloriza) — invariable en dólares, ajustable en pesos solo por notas de crédito/débito de diferencia de cambio ya vinculadas a esa factura. Lo que decide este motor nuevo es **a qué Cultivo/Campaña/Centro de Costos se imputa** ese importe ya fijado, nunca su valor.
- **Criterio de imputación**: manda el consumo real (qué campaña efectivamente usó el insumo vía FIFO/distribución de orden, o qué orden cubrió la factura de un contratista), no la clasificación declarada a mano al cargar la compra ni la fecha en que llegó la factura.
- **Insumo sin consumir**: se reporta como inventario activado (valor de stock a la espera de destino), no como costo de ninguna campaña.
- **Sin cierre duro de campaña**: si se detecta consumo no contabilizado de una campaña ya reportada, el motor reabre y ajusta ese resultado. Mismo criterio ante anulación/reversión de una compra o remito ya imputado: el ajuste es retroactivo.
- **Alcance**: corre solo sobre (a) facturas de insumos que ya entran por Remitos (agroquímicos, semillas, fertilizantes) y (b) facturas de contratistas/maquinaria vinculadas a una Orden de Trabajo. El resto de las compras (repuestos, combustible general, fletes, administrativas) queda 100% fuera, se sigue clasificando a mano.
- **Reparto multidestino**: una factura de insumo dentro de alcance se reparte proporcionalmente entre Agricultura y/o Ganadería y, dentro de eso, entre Cultivo/Campaña — una misma línea puede terminar repartida entre varios destinos.
- **Órdenes sin cultivo** (mantenimiento/infraestructura, ya definidas así en spec 011): se imputan a Centro de Costos "Adm. General" con su Rubro correspondiente, sin Cultivo ni Campaña.
- **Contratistas — cobertura N a N**: una factura de contratista puede cubrir varias Órdenes de Trabajo; por redondeo, la suma de lo repartido entre órdenes puede no cerrar exacto contra el total de la factura — se tolera esa diferencia menor.
- **Sin umbral de materialidad**: el motor reclasifica cualquier diferencia entre lo declarado a mano y lo calculado, sin piso mínimo de importe.
- **Aprobación obligatoria**: el resultado del motor nunca se aplica solo — queda como propuesta pendiente hasta que el usuario la apruebe o la corrija.
- **Aprendizaje simple**: cuando el usuario aprueba o corrige una propuesta, el motor ajusta su criterio para casos futuros parecidos (mismo espíritu que la sugerencia de rubro por texto histórico exacto que ya existe en Compras, spec 006). No hace falta guardar un registro de auditoría de cada corrección.
- **Intervención manual ante inconsistencias grandes**: cuando el reparto no cierra razonablemente contra el total de la factura, o no se encuentra ninguna orden que vincule una factura de contratista, el usuario debe intervenir para resolverlo (el umbral concreto de "grande" se define en la fase de planificación).
- **Vínculo factura de contratista↔Orden persistente**: se guarda en una tabla nueva (hoy es una búsqueda manual que no queda registrada).
- **Trazabilidad interna completa**: el motor debe poder remontar, para cualquier fracción de costo, qué remito, qué capa FIFO, qué orden y qué renglón de distribución la originó — no alcanza con el total agregado.
- **Persistencia y performance a criterio técnico**: la decisión de recalcular siempre al vuelo vs. guardar una tabla de snapshot, y cualquier estrategia de índices/vistas, quedan a criterio de la implementación, optimizando por eficiencia de recursos. Cuando cambia el dato fuente (remito recargado, distribución corregida, capa FIFO revinculada), el resultado se recalcula silenciosamente, sin marcar nada como "desactualizado".
- **Cortes por Cultivo/Campaña, no por mes**: los reportes de este motor no tienen un corte mensual — se cierran por Cultivo/Campaña.
- **Arranca en modo paralelo/benchmark**: el motor nuevo corre junto al motor de costeo heredado que ya alimenta Resultado y Costos de Cultivo (spec 012, vistas `vw_ResultadoCultivo_*`), como punto de comparación contra campañas pasadas ya imputadas correctamente. El motor heredado sigue siendo la fuente de verdad de esos reportes mientras se valida el nuevo. Reemplazar esa fuente es una iteración futura, fuera de esta spec.
- **Reemplazo completo, no ajuste incremental**: cuando una propuesta ya aprobada queda desactualizada por un cambio posterior (anulación de Orden, remito revinculado, etc.), la nueva propuesta pendiente representa el **reparto completo corregido**, no un delta a sumar sobre lo anterior. Siempre hay un único reparto vigente por renglón de factura — no se acumulan ajustes encadenados en el tiempo, consistente con que el motor no necesita guardar auditoría de cada corrección (ver más arriba).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver la propuesta de reclasificación de una factura de insumo (Priority: P1)

Un usuario de administración quiere saber, para una factura de insumo ya vinculada a un remito y consumida por una o más Órdenes de Trabajo, cómo propone el motor repartir su costo entre Agricultura/Ganadería y Cultivo/Campaña — comparado contra lo que se cargó a mano al momento de la compra.

**Why this priority**: Es la base de todo el módulo — sin poder ver la propuesta calculada, no hay nada que aprobar ni que comparar contra el motor heredado.

**Independent Test**: Puede probarse abriendo una factura de insumo con consumo real registrado en Órdenes de Trabajo y verificando que el sistema muestra el reparto propuesto por Cultivo/Campaña, con el desglose de qué remito/orden/distribución originó cada fracción.

**Acceptance Scenarios**:

1. **Given** una factura de insumo vinculada a un remito cuyo stock fue consumido íntegramente por una única Orden de Trabajo de un solo Cultivo/Campaña, **When** el usuario abre la propuesta de reclasificación, **Then** el sistema muestra el 100% del costo de esa línea imputado a ese Cultivo/Campaña, con el remito, la capa FIFO y el renglón de distribución que lo originan.
2. **Given** una factura de insumo cuyo stock fue consumido parcialmente por dos Órdenes de distinto Cultivo/Campaña y el resto sigue en stock, **When** el usuario abre la propuesta, **Then** el sistema muestra el costo repartido proporcionalmente entre ambos Cultivo/Campaña más una porción "en stock, sin consumir" valorizada como inventario.
3. **Given** una factura de insumo cuyo producto se usó tanto en una Orden agrícola como en un consumo ganadero, **When** el usuario abre la propuesta, **Then** el sistema muestra el reparto entre Agricultura y Ganadería antes de bajar a Cultivo/Campaña.
4. **Given** una compra fuera de alcance (repuestos, combustible general, administrativas), **When** el usuario la busca en este módulo, **Then** el sistema no ofrece ninguna propuesta — sigue mostrando solo la clasificación manual ya existente.

---

### User Story 2 - Aprobar o corregir una propuesta de reclasificación (Priority: P1)

Un usuario de administración revisa las propuestas pendientes y decide, para cada una, aprobarla tal cual o corregir el reparto antes de que quede firme.

**Why this priority**: Sin aprobación explícita el motor no puede afectar ningún reporte — es el control que el usuario pidió para no aplicar reclasificaciones a ciegas.

**Independent Test**: Puede probarse aprobando una propuesta y verificando que pasa a formar parte del resultado comparado contra el motor heredado; y corrigiendo otra, verificando que la corrección queda registrada como el reparto vigente para esa factura.

**Acceptance Scenarios**:

1. **Given** una propuesta de reclasificación pendiente, **When** el usuario la aprueba sin cambios, **Then** el reparto propuesto pasa a ser el vigente para esa factura y deja de aparecer como pendiente.
2. **Given** una propuesta de reclasificación pendiente, **When** el usuario corrige manualmente el reparto (por ejemplo, reasigna una fracción a otro Cultivo/Campaña) y confirma, **Then** el reparto corregido queda como vigente, y el motor ajusta su criterio para reconocer mejor casos parecidos en el futuro.
3. **Given** una factura cuyo consumo cambia después de aprobada (por ejemplo, se anula una Orden que la consumía), **When** el motor recalcula, **Then** genera una nueva propuesta pendiente con el reparto completo corregido (no un ajuste parcial) y no reemplaza el reparto vigente hasta que el usuario la apruebe explícitamente.

---

### User Story 3 - Resolver una inconsistencia grande (Priority: P2)

Un usuario de administración necesita que el sistema le señale los casos donde el reparto automático no cierra razonablemente (por ejemplo, la suma de lo repartido entre Órdenes no coincide con el total de la factura del contratista, o no se encuentra ninguna Orden que la cubra), para intervenir manualmente.

**Why this priority**: Evita que el motor proponga repartos silenciosamente incorrectos en los casos límite — es la red de seguridad del sistema, pero no bloquea el flujo principal de las Historias 1 y 2.

**Independent Test**: Puede probarse cargando una factura de contratista sin ninguna Orden de Trabajo vinculada y verificando que el sistema la señala como pendiente de intervención manual en vez de dejarla sin clasificar silenciosamente.

**Acceptance Scenarios**:

1. **Given** una factura de contratista sin ninguna Orden de Trabajo que la vincule, **When** el motor intenta generar una propuesta, **Then** el sistema la marca como "requiere intervención manual" en vez de proponer un reparto.
2. **Given** una factura de contratista vinculada a varias Órdenes cuya suma repartida difiere del total de la factura por más del margen tolerado por redondeo, **When** el motor calcula la propuesta, **Then** el sistema señala la diferencia y pide que el usuario la resuelva antes de aprobar.

---

### User Story 4 - Vincular una factura de contratista a varias Órdenes de Trabajo (Priority: P2)

Un usuario de administración vincula la factura de un contratista a todas las Órdenes de Trabajo que ese trabajo cubrió — hoy el sistema (spec 011) ya persiste este vínculo, pero solo permite una factura por Orden y bloquea si la Orden ya tiene una cargada; hace falta generalizarlo para que una misma factura pueda cubrir varias Órdenes, como confirman los datos reales (Clarifications).

**Why this priority**: Es el insumo de entrada que necesita el motor para generar la propuesta de las Historias 1-3 en el caso de contratistas — sin poder expresar el caso N a N ya confirmado, el motor no puede repartir correctamente una factura entre varias Órdenes.

**Independent Test**: Puede probarse vinculando una misma factura de contratista a dos Órdenes de Trabajo distintas y verificando que ambos vínculos quedan guardados y disponibles para el motor, sin el bloqueo actual de "la Orden ya tiene una factura".

**Acceptance Scenarios**:

1. **Given** una factura de contratista sin vincular, **When** el usuario la asocia a una o más Órdenes de Trabajo, **Then** el sistema guarda todos los vínculos y los usa para generar la propuesta de reclasificación.
2. **Given** una Orden de Trabajo que ya tiene una factura de contratista vinculada (caso hoy soportado, 1 a 1), **When** el usuario intenta vincularle una factura adicional o vincular esa misma factura a otra Orden, **Then** el sistema lo permite en vez de bloquearlo con el error actual.
3. **Given** una factura de contratista ya vinculada a una o más Órdenes, **When** el usuario corrige el vínculo (agrega o quita una Orden), **Then** el sistema recalcula la propuesta pendiente en base al vínculo actualizado.

---

### User Story 5 - Comparar el motor nuevo contra el motor de costeo heredado (Priority: P2)

Un usuario de dirección financiera o producción quiere comparar, para una Cultivo/Campaña ya cerrada y reportada por el motor heredado (spec 012), el resultado que da el motor nuevo, para evaluar si es confiable antes de considerar reemplazar la fuente de esos reportes.

**Why this priority**: Es el objetivo declarado de esta primera iteración (modo benchmark) — sin esta comparación, no hay forma de validar el motor antes de confiar en él.

**Independent Test**: Puede probarse eligiendo una Cultivo/Campaña con datos históricos completos y verificando que el sistema muestra, lado a lado, el costo total que informa el motor heredado y el que calcula el motor nuevo (aprobado hasta el momento), con la diferencia entre ambos.

**Acceptance Scenarios**:

1. **Given** una Cultivo/Campaña con propuestas ya aprobadas que cubren todo su período, **When** el usuario pide la comparación, **Then** el sistema muestra el costo total según el motor heredado y según el motor nuevo, con la diferencia absoluta y porcentual.
2. **Given** una Cultivo/Campaña con propuestas todavía pendientes de aprobar, **When** el usuario pide la comparación, **Then** el sistema aclara que la comparación es parcial y cuánto del total todavía no tiene propuesta aprobada.

---

### Edge Cases

- **Compra sin remito vinculado todavía** (el insumo entró al stock pero el vínculo factura↔remito no se cargó): la factura no tiene de dónde sacar su consumo real — queda fuera del cálculo hasta que se vincule, igual que hoy no se puede costear por FIFO sin ese vínculo (spec 010).
- **Remito con consumo, pero renglón de factura vinculado después de que la orden ya se ejecutó**: el motor debe poder generar la propuesta igual, con la fecha de vínculo posterior a la fecha de consumo — no hay bloqueo por orden temporal.
- **Anulación de una Orden de Trabajo que ya tenía una propuesta aprobada**: dispara una nueva propuesta que revierte esa imputación (ver User Story 2, Acceptance Scenario 3).
- **Producto usado en Agricultura y Ganadería en proporciones que cambian con el tiempo** (nuevas Órdenes/consumos ganaderos posteriores a una aprobación): cada nuevo consumo genera una propuesta incremental, no se reabre necesariamente todo el reparto ya aprobado salvo que la reapertura de campaña (ver Clarifications) aplique.
- **Factura de contratista vinculada a una Orden que después se anula por completo**: la propuesta correspondiente queda "requiere intervención manual" en vez de proponer un reparto a una Orden inexistente.
- **Insumo cuyo remito fue dado de baja después de haber sido consumido y aprobado**: dispara el ajuste retroactivo descrito en Clarifications (reapertura de campaña).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST calcular, para cada renglón de factura de insumo dentro de alcance (vinculado a un remito con consumo registrado en al menos una Orden de Trabajo), una propuesta de reparto de su costo entre Agricultura/Ganadería y Cultivo/Campaña, siguiendo la cadena real factura→remito→consumo FIFO→orden→distribución.
- **FR-002**: El sistema MUST dejar en inventario activado (sin imputar a ningún Cultivo/Campaña) la porción de un renglón de factura de insumo que todavía no fue consumida por ninguna Orden de Trabajo.
- **FR-003**: El sistema MUST permitir vincular una factura de contratista a una o más Órdenes de Trabajo (N a N), generalizando el vínculo persistente 1 a 1 que ya existe hoy (spec 011) y que bloquea si la Orden ya tiene una factura cargada.
- **FR-004**: El sistema MUST calcular, para cada factura de contratista vinculada a una o más Órdenes de Trabajo, una propuesta de reparto de su costo entre los Cultivo/Campaña de esas Órdenes, prorrateado por superficie igual que el costo de contratista ya calculado en Órdenes de Trabajo (spec 011).
- **FR-005**: El sistema MUST imputar a Centro de Costos "Adm. General" con su Rubro correspondiente (sin Cultivo ni Campaña) el costo de insumos o contratistas consumidos por una Orden de Trabajo sin Cultivo específico.
- **FR-006**: El sistema MUST mantener cada propuesta de reclasificación en estado pendiente hasta que un usuario la apruebe o la corrija — ninguna propuesta MUST afectar el resultado reportado sin esa aprobación explícita.
- **FR-007**: El sistema MUST permitir al usuario corregir manualmente el reparto propuesto antes de aprobarlo (reasignar Cultivo/Campaña o Centro de Costos de cualquier fracción).
- **FR-008**: El sistema MUST ajustar su criterio de clasificación futura en base a las aprobaciones y correcciones del usuario, sin requerir guardar un historial de auditoría de cada corrección individual.
- **FR-009**: El sistema MUST señalar como "requiere intervención manual", en vez de generar una propuesta automática, cualquier factura de contratista sin ninguna Orden de Trabajo vinculada.
- **FR-010**: El sistema MUST señalar como "requiere intervención manual" cualquier factura de contratista cuyo reparto entre las Órdenes vinculadas no cierre razonablemente contra su total (más allá de una diferencia menor tolerable por redondeo).
- **FR-011**: El sistema MUST recalcular automáticamente las propuestas pendientes (no las ya aprobadas) cuando cambien los datos fuente de los que dependen: un remito recargado, una distribución de Orden corregida, o una capa FIFO revinculada.
- **FR-012**: El sistema MUST generar una nueva propuesta con el reparto completo corregido (no un ajuste parcial encadenado), sin reemplazar el reparto vigente hasta que el usuario la apruebe, cuando se detecte consumo no contabilizado o una reversión (anulación de compra, remito u Orden) que afecte un Cultivo/Campaña ya reclasificado.
- **FR-013**: El sistema MUST poder explicar, para cualquier fracción de costo de una propuesta (aprobada o pendiente), el remito, la capa FIFO, la Orden y el renglón de distribución de origen.
- **FR-014**: El sistema MUST excluir de este motor cualquier renglón de compra que no sea un insumo vinculado a un remito con consumo por Orden de Trabajo, ni una factura de contratista/maquinaria vinculada a una Orden — esas compras siguen usando exclusivamente la clasificación manual ya existente (spec 006).
- **FR-015**: El sistema MUST permitir comparar, para un Cultivo/Campaña dado, el costo total que informa el motor de costeo heredado (spec 012) contra el costo total de las propuestas aprobadas por este motor nuevo, mostrando la diferencia y si la comparación es parcial (con propuestas todavía pendientes).
- **FR-016**: El sistema MUST NOT modificar ni reemplazar las vistas o el resultado del motor de costeo heredado (spec 012) — este motor nuevo corre en paralelo, sin alterar la fuente de verdad actual de Resultado y Costos de Cultivo.

### Key Entities *(include if feature involves data)*

- **Propuesta de reclasificación**: el reparto calculado por el motor para un renglón de factura (insumo o contratista) entre Agricultura/Ganadería, Cultivo y Campaña (o Centro de Costos "Adm. General", o "en stock sin consumir"). Tiene un estado (pendiente / aprobada / requiere intervención manual) y puede tener varias fracciones, cada una con su origen trazable (remito, capa FIFO, Orden, renglón de distribución). Por renglón de factura existe siempre un único reparto vigente (el de la última propuesta aprobada) — una propuesta nueva reemplaza completo al reparto vigente al aprobarse, no lo ajusta de forma incremental.
- **Vínculo Factura de Contratista↔Orden de Trabajo**: relación N a N entre una factura de Compras de un contratista/maquinaria y las Órdenes de Trabajo que cubre. Generaliza el vínculo 1 a 1 ya existente hoy (spec 011).
- **Comparación Cultivo/Campaña**: el costo total según el motor heredado (spec 012) y según las propuestas aprobadas de este motor nuevo, para un Cultivo/Campaña dado, con su diferencia.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Para el 100% de las facturas de insumo dentro de alcance con consumo ya registrado en Órdenes de Trabajo, el sistema genera una propuesta de reparto sin intervención manual previa.
- **SC-002**: El usuario puede revisar y aprobar o corregir una propuesta de reclasificación en menos de 2 minutos por factura, sin tener que buscar manualmente el remito, la orden o la distribución de origen (el sistema ya se los muestra).
- **SC-003**: Para al menos 3 Cultivo/Campaña históricos con datos completos, la comparación entre el motor heredado y el motor nuevo puede calcularse y mostrarse sin error, permitiendo evaluar si la diferencia es aceptable.
- **SC-004**: El 100% de las facturas de contratista sin Orden vinculada, o con reparto que no cierra, quedan visiblemente marcadas como "requiere intervención manual" en vez de generar una propuesta silenciosamente incorrecta.
- **SC-005**: Ningún reporte de Resultado y Costos de Cultivo (spec 012) cambia de valor como consecuencia de este módulo mientras esté en modo paralelo/benchmark.

## Assumptions

- El umbral concreto para considerar "grande" una diferencia de redondeo en el reparto de una factura de contratista (FR-010) no quedó definido por el usuario — se determina en la fase de planificación técnica, documentando el criterio elegido.
- El "aprendizaje simple" del motor (FR-008) se resuelve con una heurística equivalente a la sugerencia de rubro por texto histórico exacto que ya existe en Compras (spec 006) — no se asume machine learning ni un modelo entrenado.
- Este motor no reemplaza ni modifica `Det_Compras.IdCentroCosto/IdRubro/IdCampania` (la clasificación manual declarada al cargar la compra) durante esta iteración — ambas clasificaciones (declarada y calculada) conviven, ya que el modo es paralelo/benchmark.
- La decisión de si el resultado de este motor se persiste en una tabla nueva o se recalcula siempre al vuelo (como ya hace el FIFO de Remitos) es una decisión de implementación, no de producto, y se resuelve en la fase de planificación priorizando eficiencia de recursos.
- Los usuarios de este módulo son los mismos roles de administración que ya operan Compras, Remitos y Órdenes de Trabajo — no se introduce ningún rol o permiso nuevo (reutiliza 016-autenticacion).
