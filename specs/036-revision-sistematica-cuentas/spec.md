# Feature Specification: Método sistemático de revisión, conciliación y FIFO de cuentas

**Feature Branch**: `036-revision-sistematica-cuentas`

**Created**: 2026-10-09

**Status**: Implementado (09/10/2026). Pendientes: T057 (guía de agentes, requiere la aprobación de Sergio) y el cierre en bloque de la cola A (decisión de Sergio, ver `research.md` D16).

**Input**: User description: "Método sistemático de revisión, conciliación y FIFO de todas las cuentas de Giamigli (036): plasmar la realidad financiera de cada cuenta (proveedores, clientes y otros contactos; socios y entidades aparte) desde el inicio de cada cuenta, con criterios de cierre medibles, etapas iguales para toda cuenta, colas por tipo de problema trabajadas de las más fáciles a las más complejas, detector de pagos sin factura, saldos externos del proveedor, control de archivos incompletos en Dropbox y FIFO como última etapa. Solo Sergio audita y aprueba."

## Contexto

La spec 035 (auditoría de cuentas) dio la herramienta para comparar saldos, clasificar diferencias y corregir por regla, y la 032 dio el recálculo FIFO con respaldo y reversión. Pero el trabajo cuenta por cuenta seguía haciéndose a prueba y error: cada revisión descubría un tipo de error nuevo, y no había un orden ni un criterio común de cuándo una cuenta está terminada.

El caso testigo es **Jauregui y Morales** (contacto 48), resuelto el 09/10/2026. Mostró que:

- El saldo estaba mal por **10 facturas sin cargar**, no por pagos de más: el sistema mostraba +$1,87 M a favor cuando en realidad solo se debía la última factura. Dos facturas estaban en Dropbox con la extensión `.crdownload` (descarga incompleta) y fueron salteadas; siete no tenían archivo y se encontraron en el portal del propio proveedor; una era un ticket nuevo.
- La pista fueron **pagos sin factura que los respaldara**: transferencias cuyo importe y fecha apuntaban a una factura que no estaba cargada. Hoy nada del sistema detecta eso.
- Las imputaciones automáticas estaban groseramente mal (cheques de 2015 imputados a una factura de 2023, una transferencia de 2025 imputada a una factura de 2026, pagos del banco pegados a facturas que la tarjeta ya había cubierto) y eso **no cambiaba el saldo**.
- Hay dos clases de error que se corrigen con herramientas distintas: errores de **saldo** (faltan o sobran documentos o movimientos) y errores de **imputación** (a qué factura se aplicó cada pago). El FIFO solo corrige los segundos; aplicarlo antes de completar los documentos es retrabajo.
- El proveedor mostró su propio estado de cuenta, que cerraba en −$0,01: la evidencia externa fue la que dijo la verdad.

El objetivo final de todo el trabajo es **plasmar la realidad financiera de cada una de las cuentas con las que trabaja Giamigli**.

## Clarifications

### Session 2026-10-09 (alineación con Sergio, 25 preguntas)

- **Alcance**: todas las cuentas con movimientos (proveedores, clientes y otros contactos), desde el inicio de cada cuenta. Para cuentas muy viejas, el Access se usa para fijar el saldo inicial (su implementación se difiere a una entrega posterior, acordado el 09/10/2026). Los clientes siguen el mismo método que los proveedores. Los socios y entidades (por ejemplo Condominio LSC) van **aparte**, en su propia cola.
- **Cuenta cerrada**: se cierra con excepciones documentadas y con su motivo, **auditadas por Sergio**. Solo él valida (no hay segundo validador). Una cuenta con saldo cero se revisa igual: se le aplica FIFO y, si cierra en cero, se aprueba rápidamente.
- **Diferencias menores a $300 en pesos**: se dan por cerradas y se **registran con su importe**. En dólares se mantiene el criterio vigente (tolerancia relativa, nunca un monto fijo).
- **Fuente de verdad**: gana el proveedor (con documento). El banco gana para el pago y el proveedor para la factura. El Access es referencia para reconstruir la cuenta y solo se descarta cuando la evidencia externa lo contradice, tras un análisis detallado.
- **Facturas faltantes**: se cargan sin archivo solo si un estado de cuenta o un portal del proveedor las respalda. No hay plazo de espera de documentos (no es relevante).
- **Portales y mails de proveedores**: caso a caso, con doble autorización, siempre bajo la regla de oro. Muchos proveedores no tienen portal, y no se piden resúmenes por movimientos viejos.
- **Reglas por tema**: la diferencia de cambio en dólares se ajusta con nota; las retenciones esperan el certificado; la tarjeta nunca suma el pago bancario a la cuenta del proveedor; las compras particulares se tratan por regla; anticipos y notas de crédito se imputan por FIFO automático; los hallazgos de plazo (24 meses) se resuelven en lote.
- **Orden de trabajo**: de las cuentas más fáciles a las más complejas (la dificultad la define la cantidad de movimientos; ver la sesión "clarify"). Tablero semanal. Prioridad inmediata.

### Session 2026-10-09 (clarify, después del plan)

- Q: Para cerrar en bloque las cuentas "ya sanas" (cola A) sin pedir un estado de cuenta a cada proveedor, ¿alcanza como evidencia que su saldo coincida con el del Access al corte? → A: sí, siempre que además la cuenta no tenga hallazgos ni pagos sin factura: cierra en bloque con la fuente `access` registrada; los movimientos del 26 al 30/09/2026 (posteriores a la referencia del Access, que llega al 25/09) se muestran y se revisan en el lote.
- Q: Los pagos sin respaldo anteriores a 2021, ¿deben impedir el cierre igual que los recientes? → A: no, siempre que el saldo de la cuenta cierre contra la evidencia: se listan aparte y quedan anotados como excepción documentada con motivo.
- Q: Cuando una cuenta tiene varios problemas a la vez, ¿cuál se resuelve primero? → A: se sigue el orden de las etapas, primero lo que cambia el saldo y al final las imputaciones: H (socios, entidades y compras particulares), D (pago sin factura), E (contacto duplicado o movimiento sin contacto), C (doble conteo con tarjeta), G (retenciones e impuestos), F (dólares y mixtas), I (excepciones), B (solo imputación) y A (ya sanas); la cuenta va a la primera cola que le corresponde y las demás quedan como otros problemas.
- Q: En el lote de la cola A, ¿hay un botón para tildar todas las cuentas que cumplen o se tilda siempre cuenta por cuenta? → A: hay un botón explícito "tildar todas las que cumplen" (acción de Sergio; nada viene tildado de antemano) y se pueden desmarcar cuentas sueltas antes de aprobar.

### Session 2026-10-09 (clarify)

- Q: ¿Qué cambios vuelven a abrir una cuenta cerrada: cualquier movimiento nuevo, o solo lo que modifique su saldo a la fecha del cierre? → A: la cuenta se cierra "al corte" (una fecha) y se reabre solo si cambia su saldo a esa fecha; los movimientos posteriores al corte no la reabren y se revisan en el siguiente corte.
- Q: Para ordenar cada cola de las más fáciles a las más complejas, ¿qué manda: la cantidad de movimientos, el importe o una combinación? → A: la cantidad de movimientos (menos primero); a igual cantidad, el menor importe primero.
- Q: ¿El tablero debe mostrar solo el estado actual o también guardar una foto semanal para medir el avance? → A: estado actual siempre, más una foto guardada cada semana con comparación contra la semana anterior.
- Q: En las cuentas de clientes y mixtas, ¿qué documentos cuentan como respaldo de un pago o cobro? → A: todo documento que ya genera movimiento en la cuenta: facturas y notas, liquidaciones de venta de granos y de hacienda, y alquileres.
- Q: ¿Qué fecha se usa como corte para el primer cierre de las cuentas? → A: 30/09/2026, el último día con extractos bancarios cargados. Así se cierra el mes 9 y se arranca limpio el mes 10.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Encontrar los documentos que faltan a partir de los pagos sin factura (Priority: P1)

Sergio abre una cuenta y ve la lista de **pagos que no tienen factura que los respalde**: créditos sin deuda correspondiente. Para cada uno, el sistema sugiere cómo sería la factura faltante: el importe esperado (el pago más la retención que lo acompañe, si hay) y la fecha aproximada (unos días antes del pago, según el comportamiento habitual de esa cuenta). Sergio usa esa pista para buscar el documento en Dropbox, en el estado de cuenta del proveedor o donde corresponda, y marcar cada caso como "factura cargada", "sin documento (decisión mía)" o "pendiente".

**Why this priority**: es el error más grave y el que más distorsiona (+$1,87 M en una sola cuenta), y hoy no hay nada que lo detecte. Sin completar documentos, nada de lo que viene después (saldo, FIFO) vale.

**Independent Test**: sobre la cuenta Jauregui y Morales tal como estaba antes de cargar las 10 facturas, la lista muestra los 8 pagos sin factura de 2024 a 2026 (que corresponden a 9 facturas faltantes, porque el pago de $79.114,02 cubre dos) con el importe esperado de cada uno, y el pago de $1.563.484,73 aparece junto a la retención de $18.515,27 sugiriendo una factura de $1.582.000.

**Acceptance Scenarios**:

1. **Given** una cuenta con un pago de $79.114,02 sin factura que lo cubra, **When** Sergio abre la lista de pagos sin factura, **Then** ve ese pago con importe esperado de factura y fecha aproximada, y puede marcar su estado.
2. **Given** un pago acompañado de una retención de la misma fecha, **When** se calcula el importe esperado, **Then** el sistema sugiere la suma de ambos como total de la factura faltante.
3. **Given** un pago que sí está cubierto por una o varias facturas cargadas, **When** se calcula, **Then** no aparece como pago sin factura.
4. **Given** una cuenta con un pago sin factura que Sergio marcó "sin documento", **When** se vuelve a calcular, **Then** el pago sigue marcado con su decisión y no vuelve a aparecer como pendiente.
5. **Given** un pago de tarjeta (resumen) que cubre una factura, **When** se calcula, **Then** no se cuenta como pago sin factura ni se suma el débito bancario que canceló la tarjeta.
6. **Given** una cuenta de cliente o mixta con un cobro cubierto por una liquidación de venta de granos, de hacienda o por un alquiler, **When** se calcula, **Then** ese cobro no aparece como pago sin factura.

---

### User Story 2 - Ver cada cuenta por etapas y cerrarla con criterios claros (Priority: P1)

Cada cuenta tiene una **ficha** que muestra en qué etapa está (inventario de fuentes, documentos, movimientos y contactos, tarjetas, conciliación contra evidencia, FIFO, cierre), su estado (pendiente, en proceso, esperando evidencia, esperando a Sergio, cerrada, reabierta), su cola, la evidencia reunida y las decisiones tomadas. La cuenta solo pasa a la etapa siguiente si cumple la condición de salida de la actual. Al llegar al cierre, el sistema muestra los **7 criterios** con su resultado medido, y Sergio aprueba el cierre o lo deja con excepciones documentadas y motivo.

**Why this priority**: es el corazón del método; sin criterio común de "terminada" seguimos a prueba y error.

**Independent Test**: tomar la cuenta Jauregui y Morales ya cerrada y reconstruir su ficha: los 7 criterios figuran cumplidos con los números del 09/10/2026 (cero pagos sin factura, saldo de −$3,31 hasta el corte contra el estado del proveedor, cero doble descuento, FIFO aplicado con saldo idéntico). El criterio de saldo explicado por evidencia externa se verifica con el saldo externo que se registra en la historia 4.

**Acceptance Scenarios**:

1. **Given** una cuenta con pagos sin factura sin decisión, **When** se intenta pasar a la etapa de FIFO, **Then** el sistema no lo permite y explica qué falta.
2. **Given** una cuenta que cumple los 7 criterios, **When** Sergio la audita, **Then** puede marcarla cerrada con fecha, saldo al cierre y nota.
3. **Given** una cuenta con una diferencia que no se puede explicar, **When** Sergio decide cerrarla igual, **Then** debe registrar el motivo y la cuenta queda cerrada "con excepción", visible como tal.
4. **Given** una cuenta cerrada al corte de una fecha, **When** su saldo a esa fecha cambia después (por ejemplo, una factura vieja cargada tarde o una imputación corregida), **Then** pasa sola a "reabierta" y vuelve a su etapa de revisión.
5. **Given** una cuenta cerrada al corte de una fecha, **When** se cargan movimientos posteriores a ese corte, **Then** la cuenta sigue cerrada y esos movimientos quedan para el siguiente corte.
6. **Given** una cuenta con saldo cero, **When** se revisa, **Then** pasa igual por las comprobaciones (documentos y tarjeta) y por el FIFO, y si todo cierra en cero Sergio la aprueba con un solo gesto.

---

### User Story 3 - Trabajar en colas por tipo de problema, de las más fáciles a las más complejas (Priority: P1)

El sistema asigna cada cuenta a una **cola** según su problema dominante: A (ya sanas), B (solo imputación), C (doble conteo con tarjeta), D (pago sin factura), E (contacto duplicado o movimiento sin contacto), F (dólares y mixtas), G (retenciones e impuestos), H (socios, entidades y compras particulares) e I (excepciones). Dentro de cada cola, las cuentas se ordenan de las más fáciles a las más complejas: primero las de menos movimientos y, a igual cantidad, las de menor importe. Sergio resuelve cada cola con **una regla aplicada a todas sus cuentas en lote**, tildando las cuentas que aprueba; solo la cola de excepciones se trabaja una por una.

**Why this priority**: es lo que evita volver al cuenta por cuenta y permite avanzar rápido con control.

**Independent Test**: con los datos actuales, todas las cuentas con movimientos quedan en exactamente una cola y con un orden de dificultad; la cola de excepciones es una fracción pequeña del total.

**Acceptance Scenarios**:

1. **Given** todas las cuentas con movimientos, **When** se calculan las colas, **Then** cada cuenta tiene una cola y ninguna queda sin asignar.
2. **Given** una cuenta con más de un problema (por ejemplo, un pago sin factura y un doble descuento), **When** se asigna cola, **Then** va a la cola del problema que debe resolverse primero según el orden de las etapas, y la ficha muestra los demás.
3. **Given** una cola con varias cuentas, **When** Sergio abre un lote, **Then** ve las cuentas de la más fácil a la más compleja (menos movimientos primero; a igual cantidad, menor importe), ninguna tildada de antemano, y la regla que se aplicaría.
4. **Given** un lote aplicado, **When** Sergio lo revisa después, **Then** puede ver qué cuentas lo recibieron y revertirlo.
5. **Given** una cuenta de socio o entidad, **When** se asigna cola, **Then** va siempre a la cola H, separada del resto.

---

### User Story 4 - Comparar el saldo contra el estado de cuenta del proveedor (Priority: P2)

Para cada cuenta cuya evidencia lo permita, se registra el **saldo externo**: el saldo que informa el proveedor (o el banco o la tarjeta) con su fecha y su fuente (portal, PDF, mail). El sistema compara ese saldo con el saldo de la cuenta y muestra la diferencia; mientras no cierre, la cuenta no avanza. Registrar el saldo externo no requiere acceder a ningún portal: se carga lo que Sergio obtuvo por su cuenta, y cualquier acceso a un portal sigue la regla de oro (caso a caso, doble autorización).

**Why this priority**: es lo que confirmó el cierre de Jauregui. Sin evidencia externa, el saldo de WC es solo un resultado, no una prueba. Es P2 porque requiere que el detector y las etapas existan primero.

**Independent Test**: registrar el estado de cuenta de Jauregui (cierra en −$0,01 al 09/10/2026) y comprobar que el sistema muestra la diferencia contra el saldo de WC y la da por cerrada por estar bajo el umbral.

**Acceptance Scenarios**:

1. **Given** un saldo externo cargado con fecha y fuente, **When** se compara con el saldo de la cuenta a esa fecha, **Then** se muestra la diferencia y su clasificación (cierra, menor al umbral, con diferencia).
2. **Given** una diferencia mayor al umbral, **When** se revisa, **Then** la cuenta queda en la etapa de conciliación con la diferencia a la vista hasta que se explique.
3. **Given** un proveedor sin portal ni estado de cuenta disponible, **When** Sergio decide no pedirlo (movimientos viejos), **Then** puede registrar esa decisión y la cuenta se concilia contra el resto de la evidencia, con la excepción anotada.
4. **Given** evidencia externa que contradice al Access, **When** Sergio decide descartar el Access para esa cuenta, **Then** queda registrada la decisión con el análisis que la respalda.

---

### User Story 5 - Aplicar el FIFO solo cuando la cuenta está lista (Priority: P2)

La etapa de FIFO usa el recálculo ya existente (simular, revisar, aplicar con respaldo, revertir) pero solo se habilita cuando la cuenta pasó las etapas de documentos, movimientos, tarjetas y conciliación. El sistema exige que el saldo sea idéntico antes y después, muestra qué imputaciones cambian y deja la aplicación reversible. Las notas de crédito y los anticipos se imputan automáticamente por FIFO; los hallazgos de plazo de 24 meses se resuelven en lote.

**Why this priority**: aplicar FIFO antes de completar documentos obliga a rehacerlo. El motor ya existe; lo nuevo es ponerlo en el lugar correcto del proceso.

**Independent Test**: una cuenta con un pago sin factura pendiente no puede entrar a la etapa de FIFO; la misma cuenta, con documentos completos, simula y aplica con saldo idéntico antes y después.

**Acceptance Scenarios**:

1. **Given** una cuenta que no pasó las etapas previas, **When** se intenta simular el FIFO, **Then** el sistema lo bloquea y dice qué etapa falta.
2. **Given** una simulación que dejaría un saldo distinto al actual, **When** se intenta aplicar, **Then** se rechaza.
3. **Given** un FIFO aplicado, **When** quedan imputaciones de origen tarjeta duplicadas que el FIFO no reemplaza, **Then** se listan como pendientes de la etapa para anularlas con la corrección registrada.
4. **Given** un FIFO aplicado, **When** Sergio decide revertirlo, **Then** la cuenta vuelve exactamente a su estado anterior.

---

### User Story 6 - Detectar archivos incompletos en las carpetas de comprobantes (Priority: P2)

El sistema revisa las carpetas de compras de Dropbox y avisa de los **archivos que no son comprobantes completos o legibles** (por ejemplo `.crdownload`, archivos vacíos o ilegibles), mostrando proveedor, fecha, período y si el comprobante está o no cargado en la cuenta. Así ninguna factura se saltea en silencio.

**Why this priority**: dos de las diez facturas de Jauregui no estaban cargadas por este motivo; el mismo problema puede repetirse en otras cuentas.

**Independent Test**: en la carpeta `04 2025 - 03 2026` aparecen los archivos `.crdownload` de Jauregui con indicación de si su factura ya está cargada.

**Acceptance Scenarios**:

1. **Given** un archivo `.crdownload` cuyo contenido es un comprobante legible, **When** se revisa, **Then** se informa como "comprobante legible con extensión incorrecta" y se indica si ya está cargado.
2. **Given** un archivo ilegible, **When** se revisa, **Then** se informa como "no legible" con su ruta, sin modificarlo ni borrarlo.
3. **Given** un comprobante legible que no está cargado en ninguna cuenta, **When** se revisa, **Then** aparece como "falta cargar" con proveedor, fecha e importe.

---

### User Story 7 - Ver el avance y las preguntas pendientes en un tablero semanal (Priority: P3)

Sergio ve un tablero con las colas contra las etapas: cuántas cuentas hay en cada casilla y cuánto dinero está en juego. El tablero muestra siempre el estado actual y guarda además una foto cada semana, para comparar el avance contra la semana anterior (cuentas cerradas en la semana, tamaño de la cola de excepciones). Incluye la lista de **preguntas que bloquean** cuentas (una por cuenta, con qué se necesita y por qué). El tablero muestra cuántas cuentas están cerradas, cerradas con excepción, esperando evidencia o esperando a Sergio.

**Why this priority**: da control y evita dispersión, pero se puede trabajar con las historias anteriores sin él.

**Independent Test**: el tablero suma todas las cuentas con movimientos exactamente una vez, y su total coincide con el listado de cuentas.

**Acceptance Scenarios**:

1. **Given** cuentas en distintas etapas y colas, **When** Sergio abre el tablero, **Then** ve la cantidad e importe por casilla y el total general.
2. **Given** cuentas esperando a Sergio, **When** abre la lista de preguntas, **Then** cada una indica qué decisión o dato hace falta.
3. **Given** que cierra una cuenta, **When** se refresca el tablero, **Then** la cuenta se mueve a "cerrada" y los totales se actualizan.
4. **Given** una foto semanal guardada, **When** Sergio abre el tablero, **Then** ve cuántas cuentas se cerraron desde la semana anterior y si la cola de excepciones creció o bajó.

---

### Edge Cases

- ¿Qué pasa con una cuenta de socio o entidad que tiene un problema de otra cola? Siempre va a la cola H y se trata con sus reglas propias.
- ¿Qué pasa si un solo pago cubre varias facturas faltantes (como el de $79.114,02, que cubría dos)? El detector sugiere el importe total esperado y Sergio puede dividirlo entre las facturas que encuentre.
- ¿Qué pasa si un pago sin factura corresponde en realidad a un anticipo? Sergio lo marca como anticipo y deja de ser un faltante; el FIFO lo imputa después a la factura que llegue.
- ¿Qué pasa con una cuenta bimonetaria o en dólares? Va a la cola F; manda la moneda del proveedor y la diferencia de cambio se ajusta con nota, siempre con tolerancia relativa.
- ¿Qué pasa si el estado de cuenta del proveedor y el Access discrepan? Gana el proveedor; el Access queda como referencia y solo se descarta tras análisis detallado.
- ¿Qué pasa si el pago está registrado con el contacto equivocado? Se resuelve en la etapa de movimientos y contactos (reasignación reversible), antes del FIFO.
- ¿Qué pasa si una cuenta cerrada vuelve a cambiar? Si cambia su saldo a la fecha del corte del cierre, se reabre sola y mantiene el historial de su cierre anterior. Si solo recibe movimientos posteriores al corte (facturas o pagos nuevos), sigue cerrada y se revisa en el siguiente corte.
- ¿Qué pasa si la retención no tiene certificado? La cuenta queda con ese pendiente tipificado hasta que llegue el certificado; no se inventa el documento.
- ¿Qué pasa si no hay forma de conseguir el comprobante de una factura vieja? Sergio puede dejar la cuenta cerrada con excepción documentada; no se carga una factura sin respaldo para que "cierre".
- ¿Qué pasa si un movimiento es el débito automático que cancela la tarjeta? No suma a la cuenta del proveedor; el crédito del proveedor sale solo de las imputaciones del resumen.
- ¿Qué pasa con los movimientos del 26 al 30/09/2026, que ya están cargados pero no están en la referencia del Access (que llega al 25/09)? Entran en el corte del 30/09 y se respaldan con extractos, estados del proveedor y demás evidencia; el Access no los puede confirmar. En el cierre en bloque de la cola A se muestran en el lote para que Sergio los revise antes de aprobar.
- ¿Qué pasa con cuentas de más de una década (desde 2011)? El método se aplica desde el inicio de la cuenta. Los pagos sin factura anteriores a 2021 se listan aparte y no bloquean el cierre si el saldo cierra contra la evidencia; quedan anotados como excepción con motivo. El saldo inicial del Access como apertura queda fuera de la primera entrega (ver `research.md` D8).
- ¿Qué pasa si hay un acceso a un portal o cuenta externa? Nunca se hace sin confirmación expresa de Sergio antes de cada acceso, con el sitio, el motivo y el alcance de solo lectura.

## Requirements *(mandatory)*

### Functional Requirements

**Alcance y ficha por cuenta**

- **FR-001**: El sistema MUST incluir en el método a todas las cuentas con movimientos (proveedores, clientes y otros contactos), desde el inicio de cada cuenta. Usar el Access para fijar el saldo inicial de las cuentas muy viejas queda para una entrega posterior (research D8); mientras tanto se informa "sin apertura" en las cuentas que arrancan antes de 2011.
- **FR-002**: El sistema MUST mantener una ficha por cuenta con su etapa actual, estado, cola, evidencia reunida, decisiones de Sergio (texto, fecha y quién), y la fecha de corte y el saldo al cerrar.
- **FR-003**: El sistema MUST permitir solo estos estados por cuenta: pendiente, en proceso, esperando evidencia, esperando a Sergio, cerrada, cerrada con excepción y reabierta. `Reabierta` es un estado calculado a partir del saldo al corte; no se guarda.
- **FR-004**: El sistema MUST cerrar cada cuenta "al corte" de una fecha, y MUST reabrirla automáticamente solo cuando cambie su saldo a esa fecha de corte, conservando el historial del cierre anterior. Los movimientos posteriores al corte MUST NOT reabrir la cuenta y MUST quedar para el siguiente corte. La tolerancia para considerar que el saldo al corte cambió es de $1 en pesos (redondeo) y, en dólares, la tolerancia relativa vigente; es distinta del umbral de $300 con el que se da por cerrada una diferencia contra la evidencia externa. El corte del primer cierre de todas las cuentas es el **30/09/2026**; el corte vigente debe estar definido de forma única para todas las cuentas, de modo que el tablero sea comparable entre cuentas y entre semanas.

**Etapas y puertas**

- **FR-005**: El sistema MUST aplicar a toda cuenta las mismas siete etapas, en este orden: inventario de fuentes, completitud de documentos, movimientos y contactos, tarjetas y vínculos, conciliación contra evidencia, FIFO y cierre.
- **FR-006**: El sistema MUST impedir que una cuenta avance a una etapa si no cumple la condición de salida de la anterior, y MUST explicar qué falta.
- **FR-007**: El sistema MUST impedir simular o aplicar el FIFO en una cuenta que no completó documentos, movimientos y contactos, tarjetas y conciliación.

**Criterios de cierre**

- **FR-008**: El sistema MUST calcular y mostrar, para cada cuenta, los siete criterios de cierre con su resultado medido: documentos completos, movimientos y contactos correctos, saldo explicado por evidencia, tarjeta sin doble conteo, imputaciones sanas, pendientes tipificados y trazabilidad.
- **FR-009**: El sistema MUST registrar las diferencias menores a $300 en pesos como cerradas, guardando su importe; en dólares MUST usar tolerancia relativa y nunca un monto fijo.
- **FR-010**: El sistema MUST permitir cerrar una cuenta con excepciones solo con el motivo registrado, y MUST dejarla visible como "cerrada con excepción".
- **FR-011**: El sistema MUST exigir la aprobación expresa de Sergio para cerrar cualquier cuenta y para aceptar cualquier excepción; no hay cierre automático.
- **FR-012**: El sistema MUST someter a las cuentas con saldo cero a las mismas comprobaciones y al FIFO, y MUST ofrecer aprobación rápida cuando todo cierra en cero.

**Detector de pagos sin factura**

- **FR-013**: El sistema MUST detectar los pagos de una cuenta que no tengan factura o documento que los respalde (créditos sin deuda correspondiente) y MUST listarlos con importe, fecha y medio. Cuentan como respaldo todos los documentos que ya generan movimiento en la cuenta: facturas y notas, liquidaciones de venta de granos y de hacienda, y alquileres; esto aplica igual a proveedores, clientes y cuentas mixtas.
- **FR-013b**: El sistema MUST listar aparte los pagos sin factura anteriores al 01/01/2021 y MUST NOT dejar que bloqueen el cierre si el saldo de la cuenta cierra contra la evidencia; en ese caso MUST registrarlos como excepción documentada, con el motivo, en la ficha. Los pagos sin factura desde el 01/01/2021 SÍ bloquean el cierre hasta tener decisión.
- **FR-014**: Para cada pago sin factura, el sistema MUST sugerir el importe esperado de la factura faltante (el pago más la retención de la misma fecha, si la hay) y la fecha aproximada, según el comportamiento habitual de esa cuenta.
- **FR-015**: El sistema MUST permitir marcar cada pago sin factura como factura cargada, sin documento (con decisión de Sergio), anticipo o pendiente, y MUST conservar esa marca en las recomputaciones.
- **FR-016**: El sistema MUST NOT considerar pago sin factura a un pago de tarjeta imputado en el resumen, ni al débito bancario que cancela la tarjeta.

**Evidencia externa**

- **FR-017**: El sistema MUST permitir registrar el saldo externo de una cuenta (del proveedor, banco o tarjeta) con su fecha y su fuente, y MUST compararlo con el saldo de la cuenta a esa fecha.
- **FR-017b**: El sistema MUST aceptar como evidencia de saldo, para el cierre en bloque de las cuentas de la cola A, que el saldo coincida con la referencia del Access al corte, solo si la cuenta además no tiene hallazgos ni pagos sin factura; MUST registrar la fuente `access` en el cierre y MUST mostrar en el lote los movimientos posteriores a la referencia (del 26 al 30/09/2026) para que Sergio los revise antes de aprobar. Para que la coincidencia con el Access cuente como evidencia solo importan los hallazgos que afectan el saldo; los de imputación se arreglan en el FIFO y de todos modos impiden cerrar, porque el cierre exige los 7 criterios (`research.md` D15).
- **FR-018**: El sistema MUST aplicar la jerarquía de evidencia: gana el proveedor con documento; el banco para el pago y el proveedor para la factura; el Access solo como referencia, que se descarta únicamente con evidencia externa y tras análisis detallado.
- **FR-019**: El sistema MUST permitir registrar la decisión de no solicitar un estado de cuenta (por ejemplo, movimientos viejos o proveedor sin portal) y MUST dejar anotada la excepción en la ficha.
- **FR-020**: El sistema MUST permitir cargar una factura sin archivo solo cuando exista un estado de cuenta o portal que la respalde, y MUST dejarla marcada como "sin archivo" con la fuente.
- **FR-021**: El sistema MUST NOT acceder a portales, bancos ni cuentas externas por sí mismo; cualquier acceso MUST pedirse caso a caso a Sergio, con doble autorización y solo lectura, conforme a la regla de oro.

**Colas, orden y lotes**

- **FR-022**: El sistema MUST asignar cada cuenta a una sola cola entre A (ya sanas), B (solo imputación), C (doble conteo con tarjeta), D (pago sin factura), E (contacto duplicado o movimiento sin contacto), F (dólares y mixtas), G (retenciones e impuestos), H (socios, entidades y compras particulares) e I (excepciones), mostrando además los demás problemas de la cuenta. Cuando una cuenta tiene varios problemas, MUST asignarla a la primera cola que le corresponda según este orden de precedencia: H, D, E, C, G, F, I, B, A.
- **FR-023**: El sistema MUST ordenar las cuentas de cada cola de las más fáciles a las más complejas: por cantidad de movimientos (menos primero) y, a igual cantidad, por importe (menor primero).
- **FR-024**: El sistema MUST permitir aplicar una regla a un lote de cuentas de una cola, con las cuentas sin tildar de antemano, y MUST ofrecer una acción explícita "tildar todas las que cumplen" (decisión de Sergio) y permitir desmarcar cuentas sueltas antes de aprobar; MUST dejar el lote registrado y reversible.
- **FR-025**: El sistema MUST resolver los hallazgos de plazo de 24 meses en lote, con una lista previa que Sergio tilda; se resuelven con la regla de la cola B (anular y reimputar por FIFO).
- **FR-026**: El sistema MUST reservar el trabajo cuenta por cuenta para la cola de excepciones y MUST mostrar su tamaño, para detectar si crece más de lo esperable.

**Reglas por tema**

- **FR-027**: El sistema MUST ajustar la diferencia de cambio en dólares con una nota, preparada para que Sergio la apruebe, y MUST respetar que manda la moneda del proveedor.
- **FR-028**: El sistema MUST esperar el certificado de una retención antes de darla por documentada, y MUST mostrarla como pendiente tipificado hasta entonces.
- **FR-029**: El sistema MUST NOT sumar el pago bancario de una tarjeta a la cuenta del proveedor; el crédito del proveedor MUST salir de las imputaciones del resumen.
- **FR-030**: El sistema MUST tratar las compras particulares por regla (asiento de socio y deuda cuando pagó la empresa) y MUST mostrar los casos dudosos para revisión.
- **FR-031**: El sistema MUST imputar automáticamente por FIFO las notas de crédito y los anticipos, y MUST señalar las imputaciones de origen tarjeta duplicadas que el FIFO no reemplaza.

**Archivos de comprobantes**

- **FR-032**: El sistema MUST revisar las carpetas de comprobantes de compras e informar los archivos incompletos o ilegibles (por ejemplo `.crdownload`), indicando proveedor, fecha, período y si el comprobante está cargado.
- **FR-033**: El sistema MUST NOT modificar, renombrar ni borrar los archivos de las carpetas durante la revisión.

**Tablero y preguntas**

- **FR-034**: El sistema MUST mostrar un tablero de colas contra etapas con cantidad de cuentas e importe por casilla, y MUST reconciliar su total con el listado de cuentas.
- **FR-034b**: El sistema MUST guardar una foto del tablero cada semana y MUST mostrar la comparación contra la semana anterior (cuentas cerradas en la semana y variación de la cola de excepciones), conservando el historial de fotos.
- **FR-035**: El sistema MUST mostrar la lista de preguntas que bloquean cuentas, una por cuenta, con la decisión o el dato que falta.

**Trazabilidad y seguridad**

- **FR-036**: El sistema MUST registrar quién, cuándo y por qué en cada decisión, corrección y cierre, y MUST permitir ver el historial de una cuenta.
- **FR-037**: El sistema MUST aplicar toda corrección con respaldo verificado previo y con posibilidad de reversión, sin borrar filas.
- **FR-038**: El sistema MUST operar solo sobre la base de trabajo `WC` y MUST NOT escribir en la base oficial `LaHerencia` ni en los archivos Access.
- **FR-039**: El sistema MUST limitar las acciones de cambio al rol con permisos de escritura y ocultarlas al rol de solo lectura.
- **FR-040**: El sistema MUST reutilizar la auditoría de cuentas (035), el recálculo FIFO (032) y la cuenta corriente de tarjetas (034) sin duplicar sus reglas.

### Key Entities *(include if feature involves data)*

- **Ficha de cuenta**: el seguimiento de una cuenta: etapa, estado, cola, evidencia, decisiones, saldo al cerrar e historial. Extiende la revisión por cuenta existente.
- **Etapa**: cada uno de los siete pasos del procedimiento, con su condición de entrada y de salida.
- **Cola**: el grupo de cuentas con el mismo problema dominante, con su regla de resolución en lote.
- **Pago sin factura**: un crédito sin deuda que lo respalde, con importe, fecha, medio, importe y fecha esperados de la factura faltante y la marca de Sergio.
- **Saldo externo**: el saldo informado por el proveedor, el banco o la tarjeta, con fecha, fuente y diferencia contra el saldo de la cuenta.
- **Evidencia**: un documento o dato que respalda una conclusión (estado de cuenta, factura, extracto, resumen, certificado), con su origen y ubicación.
- **Decisión**: una resolución de Sergio sobre una cuenta o excepción, con motivo, fecha y alcance.
- **Lote**: un conjunto de cuentas tratadas con una misma regla, con sus cuentas tildadas, respaldo y estado (simulado, aplicado, revertido).
- **Foto semanal del tablero**: el registro, una vez por semana, de cuántas cuentas hay por cola, etapa y estado y su importe, para medir el avance.
- **Archivo de comprobante**: un archivo de las carpetas de compras con su estado (completo, incompleto, ilegible) y si está cargado.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100 % de las cuentas con movimientos tiene una ficha con etapa, estado y cola asignadas, y el total del tablero coincide con el listado de cuentas.
- **SC-002**: Sobre la cuenta Jauregui y Morales, tal como estaba antes de cargar las 10 facturas, el detector lista los 8 pagos sin factura con su importe esperado (el de $1.563.484,73 junto a la retención de $18.515,27), sin falsos positivos y sin omitir ninguno.
- **SC-003**: Ninguna cuenta se cierra con un pago sin factura sin decisión registrada (0 casos).
- **SC-004**: Ninguna cuenta recibe FIFO sin haber completado las etapas previas (0 casos), y en el 100 % de los FIFO aplicados el saldo es idéntico antes y después.
- **SC-005**: Una cuenta sana (cola A, o con saldo cero que cierra en cero) se revisa y aprueba en menos de 1 minuto.
- **SC-006**: Cada lote de una cola se resuelve con una sola regla y una sola aprobación de Sergio, sin revisar las cuentas una por una.
- **SC-007**: Menos del 10 % de las cuentas con movimientos termina en la cola de excepciones que se trabaja una por una.
- **SC-008**: Cada cierre y cada excepción tiene motivo, fecha y evidencia registrados (100 %), y cualquier corrección o lote se puede revertir dejando la cuenta exactamente como estaba.
- **SC-009**: Todo archivo incompleto o ilegible de las carpetas de comprobantes figura en el control, y ninguno se pierde sin aviso (0 comprobantes legibles sin cargar y sin informar).
- **SC-010**: Sergio puede saber en menos de 30 segundos cuántas cuentas están cerradas, con excepción, esperando evidencia y esperando a su decisión.
- **SC-011**: Al finalizar el trabajo, todas las cuentas con movimientos están cerradas o cerradas con excepción documentada, y el saldo de cada una es respaldado por evidencia o por una decisión registrada de Sergio.

## Assumptions

- Solo Sergio usa y audita el método; no hay segundo validador. El nivel de detalle de los controles lo define el agente financiero según los usos y costumbres de las empresas.
- El trabajo se hace de las cuentas más fáciles a las más complejas, y la prioridad es inmediata.
- "Mantenemos" el criterio de dólares se interpreta como confirmar la tolerancia relativa vigente (0,5 %) con aviso cuando se supera; no existe monto fijo en dólares. Si Sergio quiere otra cosa, lo indicará.
- El primer corte es el 30/09/2026, último día con extractos del banco cargados. Los cortes siguientes se asumen al fin de cada mes (el 31/10/2026 el próximo), con la idea de cerrar cada mes y arrancar el siguiente limpio; Sergio puede cambiarlo. La referencia del Access llega solo hasta el 25/09/2026, así que para los cinco días restantes el saldo se respalda con el resto de la evidencia.
- No hay plazo de espera de documentos: una cuenta no queda "vencida" por falta de un comprobante; queda en espera de evidencia hasta que llegue o Sergio la cierre con excepción.
- No se piden estados de cuenta por movimientos viejos; para cuentas antiguas se apoya en la referencia del Access al corte y en la evidencia disponible (el saldo inicial del Access como apertura queda para una entrega posterior).
- Los portales y mails de proveedores se consultan caso a caso, con confirmación expresa antes de cada acceso; muchos proveedores no tienen portal.
- Los estados de cuenta del proveedor se cargan en el sistema con lo que Sergio o el equipo obtengan; el sistema no los pide ni los descarga por su cuenta.
- La revisión de carpetas de Dropbox es de solo lectura sobre las rutas de comprobantes de compras existentes por período fiscal.
- Se reutilizan sin cambios de regla las funciones existentes: auditoría de cuentas (035), recálculo FIFO (032) y cuenta corriente de tarjetas (034); la spec 036 agrega el orden del proceso, el detector, la ficha y el tablero.
- Los socios y entidades (por ejemplo Condominio LSC) tienen sus propias reglas y quedan en su cola aparte, con validación de Sergio.
- Fuera de alcance de esta spec: cargar las facturas en sí (se hace con el alta de compras existente), modificar el Access, escribir en la base oficial y automatizar el acceso a portales.
