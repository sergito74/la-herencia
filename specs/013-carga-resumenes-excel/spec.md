# Feature Specification: Confirmar la carga de resúmenes bancarios (BNA/Galicia) desde Excel

**Feature Branch**: `013-carga-resumenes-excel`

**Created**: 2026-09-22

**Status**: Draft

**Input**: User description: "Completar la Historia 3 de 003-tesoreria (hoy solo preview/validación de Excel, sin persistir) agregando la confirmación real: que el usuario, tras ver la vista previa de un Excel de resumen bancario (BNA/Galicia), pueda confirmar la carga y que los movimientos queden persistidos en WC. Necesita: detectar y evitar duplicados si el mismo resumen se sube dos veces, mostrar un resumen de 'se van a insertar N movimientos nuevos, M ya existentes se omiten' antes de confirmar, y dejar trazabilidad de qué archivo/carga originó cada movimiento importado. Tarjetas queda fuera de esta spec (008/009 ya cubren su propio flujo). Se acota a BNA y Galicia."

## Clarifications

### Session 2026-09-22

- Q1 (contacto): los archivos Excel de BNA y Galicia no traen ningún campo de contacto estructurado (confirmado contra `excel_import.py` y el research de 003) — pero las tablas reales `Movimientos BNA`/`Movimientos Galicia` sí tienen `IdContacto`/`Contacto`, y la Historia 2 de tesorería (003) usa ese campo para la referencia de origen contra compras. ¿Cómo se resuelve el contacto al confirmar una carga desde Excel? → **A: el movimiento se inserta con `IdContacto`/`Contacto` en blanco** (igual que hoy conviven filas sin contacto en las tablas reales), y la referencia de origen (003 US2) simplemente los muestra como "sin coincidencia" hasta que se complete manualmente en otra instancia; no se agrega en esta spec una pantalla de asignación de contacto post-carga — queda documentado como mejora futura si el volumen real lo justifica.
- Q2 (duplicados): sin una clave natural provista por el banco (ningún ID de movimiento viaja en los Excel), ¿qué combinación de campos define "el mismo movimiento" para no insertarlo dos veces? → **A: fecha + importe (o débito/crédito según el banco) + concepto/descripción normalizado (mayúsculas, espacios colapsados) + número de comprobante si existe**, comparado contra los movimientos ya persistidos de ese banco. No es una clave perfecta (dos movimientos idénticos el mismo día son indistinguibles), pero es el mismo criterio que usaría un humano revisando el resumen a ojo, y evita el caso real más común: subir el mismo archivo dos veces por error.
- Q3 (trazabilidad): ¿se agrega una columna nueva a `Movimientos BNA`/`Movimientos Galicia` (tablas reales migradas de Access) o se registra en tablas nuevas de infraestructura de esta app? → **A: tablas nuevas en `WC`**, mismo criterio que `Tarjetas_Resumenes_Lineas_Estado` (009) — no se altera el esquema de las tablas de movimientos reales. Ver Key Entities.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Confirmar la carga de un resumen ya previsualizado (Priority: P1)

Un usuario administrativo, después de subir un Excel de resumen bancario (BNA o Galicia) y revisar la vista previa ya existente (003), necesita confirmar esa carga para que los movimientos queden disponibles en tesorería sin tener que cargarlos a mano uno por uno.

**Why this priority**: Es el corazón de esta spec — sin la confirmación real, el módulo sigue exactamente donde lo dejó 003 (solo preview). Sin esto no hay automatización de carga.

**Independent Test**: Puede probarse subiendo un Excel real de ejemplo, revisando la vista previa, confirmando la carga, y verificando que los movimientos aparecen en el listado de tesorería del banco correspondiente (003 US1) con los mismos valores mostrados en la vista previa.

**Acceptance Scenarios**:

1. **Given** una vista previa válida de un resumen BNA o Galicia, **When** el usuario confirma la carga, **Then** el sistema inserta los movimientos nuevos en `WC` y quedan visibles de inmediato en el listado de tesorería de ese banco (003).
2. **Given** una carga recién confirmada, **When** el usuario vuelve a consultar el listado de movimientos de ese banco, **Then** el orden y los valores mostrados coinciden exactamente con los de la vista previa que confirmó.
3. **Given** un intento de confirmar sin haber pasado antes por una vista previa válida (por ejemplo, llamando la confirmación directamente), **When** el sistema recibe la solicitud, **Then** la rechaza, exigiendo una previsualización válida como paso previo.

---

### User Story 2 - Evitar duplicar movimientos ya cargados (Priority: P1)

Un usuario administrativo, al subir por error el mismo resumen dos veces (o un resumen que se superpone parcialmente en fechas con uno ya cargado), necesita que el sistema detecte qué movimientos ya existen y no los duplique.

**Why this priority**: Sin esto, cada carga accidental duplicada rompe los saldos de tesorería — es un requisito de integridad, no una mejora opcional, e igual de crítico que la carga misma.

**Independent Test**: Puede probarse confirmando la carga de un resumen, y volviendo a subir y confirmar el mismo archivo: el segundo intento no debe crear movimientos nuevos.

**Acceptance Scenarios**:

1. **Given** un resumen cuyos movimientos ya fueron cargados antes, **When** el usuario lo sube de nuevo y pide confirmar, **Then** el sistema identifica cuáles de esos movimientos ya existen (ver Clarifications Q2) y los omite, sin duplicarlos.
2. **Given** un resumen con algunos movimientos nuevos y otros ya existentes (superposición parcial de fechas), **When** el usuario confirma, **Then** el sistema inserta solo los nuevos y omite los repetidos, dejando claro cuántos de cada tipo hubo.
3. **Given** un resumen completo ya cargado antes sin ningún movimiento nuevo, **When** el usuario intenta confirmarlo, **Then** el sistema permite la confirmación igual (no la bloquea), pero el resultado indica 0 movimientos insertados.

---

### User Story 3 - Ver antes de confirmar cuántos movimientos son nuevos y cuántos se omiten (Priority: P1)

Un usuario administrativo necesita saber, antes de confirmar, cuántos movimientos de la vista previa son realmente nuevos y cuántos el sistema va a omitir por ya existir, para decidir con confianza si confirma la carga.

**Why this priority**: Es la contraparte visible de la Historia 2 — sin este resumen previo, el usuario confirma a ciegas y no puede detectar un problema (por ejemplo, "se van a insertar 0 de 40" cuando esperaba un archivo nuevo) antes de que ocurra.

**Independent Test**: Puede probarse subiendo un resumen con superposición parcial conocida y verificando que el conteo mostrado antes de confirmar coincide con el resultado real después de confirmar.

**Acceptance Scenarios**:

1. **Given** una vista previa de un resumen con movimientos nuevos y repetidos mezclados, **When** el usuario la revisa antes de confirmar, **Then** el sistema muestra cuántos son nuevos y cuántos se omitirán por ya existir, antes de cualquier escritura.
2. **Given** el resumen de "nuevos vs. omitidos", **When** el usuario decide no confirmar, **Then** el sistema no escribe nada en `WC`.

---

### User Story 4 - Rastrear el origen de un movimiento importado por Excel (Priority: P2)

Un usuario administrativo, viendo un movimiento en tesorería que fue cargado por esta vía, necesita saber de qué archivo y de qué carga proviene, para poder auditar o corregir un error de origen.

**Why this priority**: Es valor de auditoría, no bloqueante para la carga en sí — el módulo ya funciona sin esto (P1-P1-P1 arriba), pero sin trazabilidad un error de carga (archivo equivocado, resumen del mes incorrecto) es mucho más difícil de diagnosticar y revertir.

**Independent Test**: Puede probarse confirmando una carga y verificando que cada movimiento insertado, y la carga en sí, quedan identificables por nombre de archivo y fecha/hora de carga.

**Acceptance Scenarios**:

1. **Given** una carga confirmada, **When** el usuario consulta el historial de cargas de un banco, **Then** ve el nombre del archivo, banco, fecha/hora de carga, y cuántos movimientos insertó/omitió esa vez.
2. **Given** un movimiento visible en tesorería que fue importado por esta vía, **When** el usuario lo inspecciona, **Then** puede identificar a qué carga (archivo) pertenece.

### Edge Cases

- ¿Qué pasa si el usuario sube un Excel de un banco pero la fila que llega no tiene fecha o importe (fila vacía o mal formada en el medio del archivo)? El sistema debe descartar esa fila de la carga (igual que ya hace la previsualización de 003) y contarla como omitida por dato incompleto, no como duplicado ni como error fatal de todo el archivo.
- ¿Qué pasa si dos cargas confirmadas se superponen completamente en fechas pero son de bancos distintos (un Excel BNA y uno Galicia del mismo período)? No hay conflicto — la detección de duplicados es siempre dentro del mismo banco, nunca cruzada.
- ¿Qué pasa si el usuario confirma una carga y, en el medio, otro usuario también está confirmando una carga superpuesta del mismo banco? El sistema debe evitar una condición de carrera que duplique movimientos — la detección de duplicados y la inserción ocurren en una misma operación atómica contra `WC`.
- ¿Qué pasa si la vista previa que el usuario confirma ya no coincide con el archivo original (por ejemplo, quedó obsoleta en el navegador)? La confirmación reprocesa el archivo subido en el momento de confirmar (no reutiliza una vista previa vieja en memoria del servidor), para no persistir datos que el usuario no vio realmente.
- ¿Qué pasa con las columnas de imputación (rubro/centro de costo/destino) si vinieran en el Excel? Se ignoran igual que ya lo establece 003 (FR-006 de esa spec) — compras sigue siendo la única fuente de imputación.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST permitir confirmar una carga de movimientos a partir de un archivo Excel de BNA o Galicia ya validado como estructuralmente correcto (reutilizando la validación de 003), persistiendo los movimientos nuevos en `WC`.
- **FR-002**: El sistema MUST reprocesar el archivo Excel efectivamente subido en el momento de la confirmación (no una vista previa cacheada del lado servidor), para garantizar que lo confirmado sea exactamente lo que el usuario subió.
- **FR-003**: El sistema MUST detectar, antes de insertar, qué movimientos del archivo ya existen en `WC` para ese banco, usando fecha + importe (débito/crédito según corresponda) + concepto/descripción normalizado + número de comprobante (si existe) como criterio de coincidencia (Clarifications Q2).
- **FR-004**: El sistema MUST mostrar al usuario, antes de escribir cualquier dato, cuántos movimientos del archivo son nuevos y cuántos se omitirán por ya existir.
- **FR-005**: El sistema MUST insertar únicamente los movimientos identificados como nuevos, sin duplicar los ya existentes, en una operación que evite condiciones de carrera con otras confirmaciones concurrentes del mismo banco.
- **FR-006**: El sistema MUST insertar los movimientos nuevos con `IdContacto`/`Contacto` en blanco (Clarifications Q1), sin inventar ni inferir un contacto.
- **FR-007**: El sistema MUST registrar cada carga confirmada (banco, nombre de archivo, fecha/hora, cantidad insertada, cantidad omitida) en una tabla de infraestructura nueva en `WC`, sin alterar el esquema de `Movimientos BNA`/`Movimientos Galicia` (Clarifications Q3).
- **FR-008**: El sistema MUST permitir identificar, para cualquier movimiento insertado por esta vía, a qué carga (archivo) pertenece.
- **FR-009**: El sistema MUST permitir consultar el historial de cargas confirmadas de cada banco (archivo, fecha, insertados, omitidos).
- **FR-010**: El sistema MUST rechazar una confirmación si el archivo reprocesado ya no valida como estructuralmente correcto (mismo criterio de FR-007/008/009 de 003).
- **FR-011**: El sistema MUST seguir ignorando cualquier columna de imputación (rubro/centro de costo/destino) que pudiera venir en el archivo, igual que 003.
- **FR-012**: El sistema MUST escribir exclusivamente contra `WC`, nunca contra `LaHerencia`.
- **FR-013**: El sistema MUST dejar sin cambios el comportamiento de solo-previsualización ya existente (003 US3) para el caso en que el usuario solo quiera validar sin confirmar.

### Key Entities *(include if feature involves data)*

- **Carga de resumen (nueva, infraestructura de esta app)**: registro de cada confirmación — banco (BNA/Galicia), nombre de archivo, fecha/hora de carga, cantidad de movimientos insertados, cantidad omitidos por duplicado, cantidad omitidos por dato incompleto.
- **Vínculo movimiento↔carga (nuevo, infraestructura de esta app)**: relación entre un movimiento insertado en `Movimientos BNA`/`Movimientos Galicia` (por su Id real) y la carga que lo originó, para trazabilidad (FR-008).
- **Movimiento BNA / Movimiento Galicia (existentes, sin cambio de esquema)**: las mismas tablas reales que ya consulta 003; esta spec solo agrega filas nuevas con `IdContacto`/`Contacto` en blanco cuando vienen de Excel.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un usuario puede confirmar la carga de un resumen ya previsualizado y verlo reflejado en el listado de tesorería del banco correspondiente en menos de 1 minuto.
- **SC-002**: Subir el mismo archivo dos veces nunca duplica movimientos: la segunda confirmación siempre inserta 0 movimientos nuevos de ese archivo.
- **SC-003**: El 100% de las confirmaciones muestran, antes de escribir, el conteo de movimientos nuevos vs. omitidos, sin excepción.
- **SC-004**: El 100% de los movimientos insertados por esta vía son identificables hasta la carga (archivo) que los originó.
- **SC-005**: Ninguna carga concurrente del mismo banco produce movimientos duplicados, verificado confirmando el mismo archivo desde dos sesiones simultáneas.

## Assumptions

- Se reutiliza el parseo ya implementado en 003 (`excel_import.py`) para BNA (`.xls`) y Galicia (`.xlsx`); esta spec no cambia el formato reconocido ni agrega nuevos bancos.
- El volumen esperado por carga es el mismo observado en 003 (resúmenes mensuales, cientos de movimientos), no cargas masivas históricas de miles de filas de una sola vez.
- Tarjetas queda fuera de esta spec — 008/009 ya tienen su propio flujo de carga de resúmenes de tarjeta, con su propia tabla y su propia lógica de conciliación, que no se toca acá.
- No se agrega en esta spec una pantalla para asignar manualmente el contacto de un movimiento importado sin contacto (Clarifications Q1); si en el futuro se prioriza, es una spec separada.
- Integraciones fiscales (AFIP/ARCA) y roles/permisos de usuario quedan fuera de alcance, igual que en 003.
