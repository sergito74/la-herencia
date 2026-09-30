# Feature Specification: Backfill de boletas de impuestos faltantes

**Feature Branch**: `029-backfill-boletas-impuestos`

**Created**: 2026-09-30

**Status**: Draft

**Input**: User description: "Backfill de boletas de impuestos faltantes (029). Muchos pagos de impuestos ya cargados en Tesorería no tienen la boleta correspondiente en el módulo de Impuestos: se cargó el pago pero no el comprobante, así que la cuenta corriente del organismo queda con saldo a favor ficticio. Dos fuentes para completar: (a) los comprobantes escaneados que sí existen en las carpetas `Impuestos\{ejercicio}` y `Compras\{ejercicio}`; (b) para los pagos sin ningún comprobante guardado, generar la boleta a partir del propio pago e incluirla en la base, distinguible de una boleta real. El usuario revisa lo propuesto antes de que se escriba."

## Clarifications

### Session 2026-09-30

- Q: ¿Desde qué fecha se completan las boletas faltantes? → A: Todo el histórico, sin fecha de corte (los pagos arrancan en 2010).
- Q: Cuando un pago cubre varias cosas a la vez (cuotas o varios impuestos), ¿cuántas boletas se generan? → A: Una sola boleta por el total del pago, marcada como generada; el desglose, si hace falta, se hace a mano después.
- Q: Si el concepto del pago no permite saber el tipo de impuesto, ¿cómo queda la boleta generada? → A: Con un tipo genérico "Sin identificar (generada desde el pago)", corregible después; no bloquea la confirmación.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver qué pagos de impuestos no tienen boleta (Priority: P1)

Quien administra la empresa quiere saber, por organismo (AFIP, ARBA, Municipalidad de Bolívar, UATRE, etc.), qué pagos ya registrados en bancos, Mercado Libre o efectivo no tienen una boleta cargada que los respalde, y cuánto suman. Hoy solo se ve el síntoma: la cuenta corriente del organismo muestra un saldo a favor que no es real (medido el 2026-09-30: AFIP −$12,97M, ARBA −$6,37M, Municipalidad de Bolívar −$5,44M, UATRE −$0,87M).

**Why this priority**: sin este diagnóstico no se puede completar nada con seguridad; además ya entrega valor solo, porque dice exactamente qué falta y dónde.

**Independent Test**: abrir el diagnóstico de un organismo y comprobar que la suma de los pagos listados como "sin boleta" explica el saldo a favor de su cuenta corriente.

**Acceptance Scenarios**:

1. **Given** un organismo con más pagado que boletas cargadas, **When** se abre el diagnóstico, **Then** se listan los pagos sin boleta con fecha, medio de pago, concepto e importe, y se explica su relación con el saldo; cualquier diferencia por otros documentos, duplicados o partidas pendientes se informa por separado, sin forzar el saldo a cero.
2. **Given** un pago que ya está respaldado por una boleta cargada, **When** se abre el diagnóstico, **Then** ese pago no aparece como faltante.
3. **Given** un organismo sin ninguna boleta cargada, **When** se abre el diagnóstico, **Then** aparecen sus pagos como candidatos y se separan los que ya tienen otro respaldo o requieren revisión. La ausencia de boletas por sí sola no autoriza generar deuda.

---

### User Story 2 - Completar con los comprobantes reales que sí están guardados (Priority: P2)

Para cada pago sin boleta, el sistema busca si existe un comprobante escaneado del mismo organismo en las carpetas de documentos de la empresa (`Impuestos\{ejercicio}` y `Compras\{ejercicio}`) y propone vincularlo. El usuario revisa la propuesta y, al confirmar, la boleta queda cargada con su comprobante real adjunto.

**Why this priority**: es la fuente más confiable — un comprobante real vale más que una boleta reconstruida — y hay que agotarla antes de generar nada.

**Independent Test**: tomar un pago a ARBA de 2025 con un PDF `20250715_ARBA.pdf` guardado, confirmar la propuesta, y comprobar que la boleta nueva abre ese PDF y que el pago dejó de figurar como faltante.

**Acceptance Scenarios**:

1. **Given** un pago sin boleta y un comprobante guardado del mismo organismo con fecha cercana, **When** se genera la propuesta, **Then** el pago aparece emparejado con ese comprobante, y el usuario puede abrirlo para verificarlo antes de confirmar.
2. **Given** un comprobante que podría corresponder a más de un pago, **When** se genera la propuesta, **Then** el sistema no elige solo: lo muestra como ambiguo para que el usuario decida.
3. **Given** un comprobante guardado que ya está vinculado a una boleta existente, **When** se genera la propuesta, **Then** no se vuelve a proponer.

---

### User Story 3 - Generar la boleta desde el pago cuando no hay comprobante (Priority: P3)

Para los pagos que no tienen ningún comprobante guardado, el sistema propone crear una boleta a partir del propio pago (mismo organismo, importe y fecha). El usuario revisa el lote y confirma; las boletas quedan cargadas y señaladas como "generadas desde el pago", distinguibles a simple vista de las que tienen comprobante real.

**Why this priority**: es el último recurso, pero es el que cierra las cuentas — la mayoría de los faltantes no tiene comprobante guardado.

**Independent Test**: confirmar el lote de un organismo y comprobar que su cuenta corriente queda sin saldo a favor ficticio y que cada boleta generada se reconoce como tal en el listado de Impuestos.

**Acceptance Scenarios**:

1. **Given** un pago sin boleta ni comprobante, **When** se confirma la propuesta, **Then** existe una boleta nueva del mismo organismo, por el mismo importe y fecha, marcada como generada desde el pago.
2. **Given** un lote ya confirmado, **When** se vuelve a generar la propuesta, **Then** no se proponen de nuevo los mismos pagos (no se duplican boletas).
3. **Given** una boleta generada desde el pago, **When** más adelante aparece el comprobante real, **Then** se puede adjuntar a esa boleta y deja de figurar como generada.

---

### Edge Cases

- Un pago que cubre varias boletas a la vez, o varias cuotas de un plan: se genera una sola boleta por el total del pago, sin dividirlo (confirmado); el desglose posterior es manual y queda fuera de esta feature.
- Un pago cuyo importe difiere por centavos de una boleta ya cargada: con vínculo documental verificable y dentro de la tolerancia se considera respaldado; sin vínculo es respaldo probable, pendiente de revisión y excluido de generación. La coincidencia de importe no crea un vínculo ni autoriza sobreimputación.
- Movimientos a favor del organismo que no son pagos (devoluciones, reintegros, retenciones): no generan boleta.
- Pagos sin organismo identificado: quedan fuera de la propuesta y se informan aparte, para asignarles contacto primero.
- Comprobante guardado con un nombre que no permite identificar el organismo: no se propone; se lista como "no reconocido".
- No se puede determinar el tipo de impuesto a partir del pago: la boleta se carga con el tipo genérico "Sin identificar (generada desde el pago)", filtrable y corregible después.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST identificar, por organismo, los pagos registrados en cualquier medio (bancos, Mercado Libre, efectivo) que no están respaldados por una boleta cargada.
- **FR-002**: El sistema MUST mostrar por organismo la cantidad y el total de pagos sin boleta, junto al saldo actual de su cuenta corriente, de modo que se vea si lo faltante explica el saldo.
- **FR-003**: El sistema MUST buscar comprobantes guardados en las carpetas de documentos de impuestos y de compras, reconociendo el organismo y la fecha a partir de cada archivo.
- **FR-004**: El sistema MUST proponer el emparejamiento de un pago con un comprobante solo cuando la correspondencia es única; los casos con más de un candidato MUST presentarse como ambiguos para decisión del usuario.
- **FR-005**: El sistema MUST proponer, para cada pago sin boleta y sin comprobante, una boleta con el mismo organismo, importe y fecha del pago.
- **FR-006**: El sistema MUST permitir revisar la propuesta completa antes de escribir nada, distinguiendo qué pagos se completan con comprobante real, cuáles con boleta generada y cuáles quedan sin resolver, y permitir excluir o corregir casos individuales.
- **FR-007**: El sistema MUST dejar toda boleta generada desde el pago marcada de forma visible en Impuestos y en la cuenta corriente hasta adjuntar su comprobante real; su origen generado se conserva permanentemente en la auditoría.
- **FR-008**: El sistema MUST dejar cada boleta creada vinculada al pago que la originó, de modo que el pago quede respaldado y no vuelva a figurar como faltante.
- **FR-009**: El sistema MUST ser repetible sin duplicar: volver a generar la propuesta después de confirmar un lote no propone de nuevo lo ya resuelto.
- **FR-010**: El sistema MUST permitir adjuntar más adelante el comprobante real a una boleta generada desde el pago, quitándole esa marca.
- **FR-011**: El sistema MUST registrar qué se creó en cada confirmación (cuántas boletas, de qué organismo, con qué fuente), de modo que un lote pueda identificarse y revertirse.
- **FR-012**: El sistema MUST exigir un backup verificado de la base antes de confirmar una carga masiva, y escribir únicamente en la base de producción `WC`.
- **FR-013**: El sistema MUST impedir la confirmación a usuarios con rol de solo lectura.
- **FR-015**: El sistema MUST permitir filtrar las boletas de tipo "Sin identificar (generada desde el pago)" y corregir su tipo de impuesto.
- **FR-014**: El sistema MUST NOT modificar ni borrar boletas preexistentes al backfill ni pagos existentes; la carga solo agrega boletas y vínculos. FR-010 y FR-015 permiten actualizar únicamente las boletas creadas por esta feature. La reversión retira solo lo creado por el lote y se bloquea si hubo cambios o vínculos posteriores.

### Key Entities *(include if feature involves data)*

- **Pago de impuesto**: movimiento ya registrado en un medio de pago, atribuido a un organismo. Es el dato de partida; no se modifica.
- **Boleta de impuesto**: documento que respalda lo que se le debe o se le pagó a un organismo (organismo, tipo de impuesto, período, número, importe, fecha, comprobante adjunto). Esta feature agrega su **origen**: cargada desde comprobante real o generada desde el pago.
- **Comprobante guardado**: archivo escaneado en las carpetas de la empresa, del que se reconoce organismo y fecha.
- **Propuesta de backfill**: resultado revisable que asigna a cada pago sin boleta una de tres salidas — comprobante real, boleta generada, o sin resolver.
- **Lote confirmado**: registro de lo que se escribió en una confirmación, para auditoría y reversión.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Después de confirmar el backfill, ningún organismo conserva saldo a favor atribuible a pagos sin boleta (diferencia menor a la tolerancia de redondeo por pago).
- **SC-002**: El 100% de los pagos a organismos queda en uno de dos estados: respaldado por una boleta, o listado explícitamente como pendiente con su motivo.
- **SC-003**: El 100% de las boletas generadas desde el pago se distingue a simple vista de las que tienen comprobante real.
- **SC-004**: Repetir el proceso completo sobre datos ya resueltos crea cero boletas nuevas.
- **SC-005**: El usuario puede revisar y confirmar el backfill de un organismo en menos de 10 minutos, sin editar datos fuera de la pantalla.
- **SC-006**: Ningún comprobante real se vincula a un pago equivocado: todo emparejamiento automático es único; los dudosos se deciden a mano.

## Assumptions

- "Organismo" es todo contacto de tipo Organismo (hoy AFIP, ARBA, Municipalidad de Bolívar, Municipalidad de Tapalqué, UATRE, Ministerio de Desarrollo Agrario).
- Un pago está respaldado documentalmente si tiene un vínculo verificable que lo cubre. Una boleta del mismo organismo con saldo compatible por importe es respaldo probable: se reserva su capacidad una sola vez en la propuesta y se excluye de generación hasta revisar la correspondencia. Las colisiones, respaldos parciales y otros documentos contables quedan pendientes con motivo, no se consideran faltantes automáticamente.
- La boleta generada toma la fecha del pago; el período liquidado y el número de documento quedan vacíos salvo que se puedan leer del concepto del pago.
- El tipo de impuesto se infiere del concepto del pago cuando es reconocible (ej. "ARBA INMOB"); si no, se usa el tipo genérico "Sin identificar (generada desde el pago)".
- Los comprobantes guardados se reconocen por el nombre del archivo (fecha y organismo), que es la convención real de esas carpetas; no se lee el contenido del PDF para extraer importes en esta versión.
- El alcance es histórico completo, confirmado por el usuario: todos los pagos a organismos ya cargados desde 2010, sin fecha de corte.
- UATRE ya tuvo un backfill puntual previo; entra igual en el diagnóstico y solo se completa lo que siga faltando.

## Ajustes de diseño verificados — 2026-09-30

- Las tres respuestas del usuario se conservan. Los ajustes anteriores precisan controles de duplicación y coherencia entre FR-007/010/014/015.
- Lectura actual de WC: Tapalqué tiene saldo total cero y 22 movimientos de cuenta, por lo que no puede asumirse que sus pagos deban generar nuevas deudas por falta de registros en Impuestos. El diagnóstico debe identificar el respaldo contable antes de proponerlos.
- Reconocer el contacto de un movimiento no significa tener su boleta. El vínculo de backfill debe documentar el pago sin generar un segundo asiento de crédito.
- No se promete que todos los organismos queden en cero: se elimina únicamente el saldo ficticio atribuible a faltantes confirmados; las diferencias restantes se muestran con su explicación.
