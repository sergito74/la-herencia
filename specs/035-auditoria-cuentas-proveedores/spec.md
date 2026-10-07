# Feature Specification: Auditoría de cuentas corrientes de proveedores

**Feature Branch**: `035-auditoria-cuentas-proveedores`

**Created**: 2026-10-06

**Status**: Draft

**Input**: User description: "Auditoría de cuentas corrientes de proveedores (035): preparar y ejecutar la verificación metódica de las cuentas corrientes de proveedores (y clientes) con cuatro piezas: (1) completar el recálculo FIFO de la feature 032 para todos los contactos; (2) regla de plazo razonable para las aplicaciones de pagos a facturas; (3) fecha de corte 25/09/2026 contra los saldos de referencia de Access; (4) un control propio de cuentas corrientes, de solo lectura, que compara cada saldo contra Access, clasifica por causa y agrupa las excepciones. Se corrige por regla general, nunca cuenta por cuenta."

## Contexto

Sergio revisó las cuentas de a una y cada lote descubría una fuente o una regla nueva: sentía que daba un paso y retrocedía tres. El 01/10/2026 se acordó cambiar de método: comparar todas las cuentas de una vez contra el Access (el Access tenía las cuentas conciliadas desde el inicio y es la base sólida), clasificar cada diferencia por su causa y corregir por regla general. Las cinco tarjetas y Mercado Pago ya están cerradas (feature 034). Esta feature arma esa verificación metódica para las cuentas de proveedores y clientes.

Casos conocidos que la verificación debe encontrar sola, sin que nadie los señale:

- **Cargill**: el movimiento 3240 de Galicia ($7.868.575,41, del 28/05/2026) quedó repartido sobre unas 90 facturas de 2019 a 2024 (entre ellas facturas de abril de 2023 que ya estaban pagadas con tarjeta). Pagar facturas tres años después no tiene sentido: está mal conciliado.
- **Cooperativa Agropecuaria**: las aplicaciones automáticas sobre los movimientos 14417 y 14418 del Banco Nación duplican cuotas que ya pagó la tarjeta. El sistema muestra unos −$454.000 y el real es 0.
- **Lartirigoyen**: las aplicaciones automáticas de Galicia sobre las notas de débito 5212, 5213, 5216 y 5219 duplican lo que cubrió la tarjeta; además la retención del certificado 32 ($19.251,58) no tiene recibo.
- **Nidera**: la nota de débito 7028-00011189 ($180.411,30) no está imputada.

## Clarifications

### Session 2026-10-06

- Q: ¿Cuántos meses como máximo puede pasar entre la factura y el pago que se le aplica antes de marcarlo como sospechoso? → A: 24 meses (permisivo: solo casos muy viejos; ajustable).
- Q: Una cuenta que difiere del Access por una causa ya conocida y deliberada (reasignaciones, fuentes que el Access no contaba), ¿se muestra como coincide o como diferencia? → A: como "coincide con causa conocida": grupo aparte, visible y abrible, que no cuenta como excepción.
- Q: Al aprobar una corrección para un grupo de excepciones, ¿se aprueba el grupo entero o cuenta por cuenta? → A: cuenta por cuenta dentro del grupo: la regla de corrección es una sola para todo el grupo, pero Sergio tilda una a una las cuentas a las que se aplica (ninguna viene tildada de antemano); las no tildadas quedan en el grupo.
- Q: Si el saldo coincide pero el FIFO cambia qué pago cubre qué factura, ¿se informa como diferencia? → A: no; el control compara saldos, no imputaciones. Los cambios de imputación quedan en el historial del FIFO, consultable y reversible.

### Session 2026-10-06 (alineación con Sergio)

- La pantalla principal es la **revisión de una cuenta**: lista de movimientos con saldo acumulado (como una cuenta corriente), con detalle, enlace a los comprobantes originales (PDF) y a su origen. Los resúmenes por causa y las reglas son un apoyo, no el centro.
- **El Access es solo una referencia anecdótica**, no la verdad. Gana la lógica: que saldos y movimientos cierren de manera coherente. Si el sistema lo resuelve distinto que el Access, está bien.
- Una cuenta está "cerrada" cuando Sergio la mira y la da por buena. Sergio sabe qué cuentas pueden tener saldo y cuáles no: poder marcar, por cuenta, si el saldo esperado es cero o puede tener saldo.
- Desde la misma pantalla se corrige: cambiar el contacto de un movimiento, anular una imputación y cargar una nota de ajuste. Cada cuenta se marca "revisada" con fecha y nota. Se quiere ver el historial de lo que se cambió.
- Los movimientos del banco sin contacto se asignan de las tres formas: uno a uno, varios a la vez y por regla.
- Sin monto mínimo: las diferencias de redondeo no importan, el resto sí.
- Orden de trabajo: alfabético, empezando por las cuentas más fáciles y dejando para después las complicadas.
- El proceso tiene que ser ágil y llevar el menor tiempo posible. Solo Sergio la usa por ahora; el nivel de detalle lo define el agente financiero según usos y costumbres de las empresas.
- Para qué: todo (pagos, reclamos, balance, impuestos) y el flujo de caja pendiente. Listo = poder entrar a las cuentas, revisarlas y corregir lo que no esté correcto.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver de una vez el estado de todas las cuentas (Priority: P1)

Sergio abre una pantalla de control de cuentas corrientes y ve cuántas cuentas coinciden con el Access y cuántas no, y las que no coinciden agrupadas por causa (no una lista de 500 cuentas). Cada grupo muestra cuántas cuentas y cuánto dinero involucra, y se puede abrir para ver qué cuentas lo componen.

**Why this priority**: es el cambio de método que Sergio pidió. Sin esta vista no se puede decidir qué corregir ni en qué orden.

**Independent Test**: con los datos al corte del 25/09/2026, la pantalla muestra todas las cuentas de proveedores y clientes con su saldo del sistema, su saldo del Access y la causa de la diferencia; las que coinciden (hoy 436, incluidas las que coinciden con causa conocida) aparecen como "coincide" y las demás caen en un grupo de excepciones.

**Acceptance Scenarios**:

1. **Given** los saldos del sistema y los de referencia del Access al 25/09/2026, **When** Sergio abre el control, **Then** ve el total de cuentas, cuántas coinciden, cuántas no, y las no coincidentes agrupadas por causa con cantidad e importe por grupo.
2. **Given** una cuenta cuya diferencia con el Access es menor a $300 en pesos, **When** se clasifica, **Then** figura como cerrada ("diferencia menor al umbral") y no como excepción; en dólares nunca se aplica umbral.
3. **Given** movimientos cargados después del 25/09/2026, **When** se compara, **Then** esos movimientos quedan fuera de la comparación y la pantalla lo aclara.
4. **Given** una cuenta con una diferencia cuya causa no se reconoce, **When** se clasifica, **Then** cae en el grupo "otros" para revisión, nunca se oculta.

---

### User Story 2 - Detectar pagos aplicados a facturas fuera de plazo (Priority: P1)

El control marca como excepción todo pago aplicado a una factura cuando pasó más tiempo que el plazo máximo razonable entre ambos (inicial: 24 meses, ajustable por Sergio). Los anticipos se contemplan: normalmente son de hasta 60 días, sobre todo en labores, pero pueden ser mayores y entonces se marcan en lugar de descartarse.

**Why this priority**: es lo que hace que Cargill, Cooperativa, Lartirigoyen y Nidera aparezcan solos como grupo de excepciones, sin revisión manual cuenta por cuenta.

**Independent Test**: sin señalarlos, los cuatro casos conocidos aparecen en el grupo "aplicación fuera de plazo" o en su grupo de causa (doble descuento con tarjeta, nota sin imputar).

**Acceptance Scenarios**:

1. **Given** el movimiento 3240 de Galicia aplicado a facturas de 2019 a 2024, **When** se corre el control con el plazo de 24 meses, **Then** aparece como aplicación fuera de plazo con la factura, el pago, los días de diferencia y el importe.
2. **Given** un pago aplicado a una factura dentro del plazo, **When** se corre el control, **Then** no se marca.
3. **Given** que Sergio cambia el plazo máximo, **When** vuelve a correr el control, **Then** el resultado se recalcula con el plazo nuevo y se ve con qué plazo se calculó.
4. **Given** una aplicación automática cuya factura ya figura pagada con tarjeta, **When** se corre el control, **Then** se marca como posible doble descuento con tarjeta (casos Cooperativa y Lartirigoyen).

---

### User Story 3 - Completar el recálculo FIFO para todos los contactos (Priority: P2)

Hoy el recálculo FIFO (feature 032) se aplicó solo a 7 contactos. Se completa para todos: primero se simula, Sergio revisa y aprueba, y recién después se aplica. Así la antigüedad de cada deuda y qué pago cubre qué factura quedan confiables en todas las cuentas. El saldo de ninguna cuenta cambia: solo cambian las imputaciones. Todo es reversible.

**Why this priority**: sin el FIFO completo no se puede juzgar la antigüedad ni el plazo (historia 2) en las cuentas que aún no pasaron por él; pero el control de la historia 1 ya sirve sin esto.

**Independent Test**: la simulación sobre todos los contactos muestra, para cada cuenta, el saldo antes y después (idéntico) y las cuentas que no cierran quedan en la lista de cuentas a revisar; aplicar y revertir deja los datos exactamente como estaban.

**Acceptance Scenarios**:

1. **Given** los contactos todavía sin recalcular, **When** se simula, **Then** se muestra por cuenta el saldo antes y después, el resultado de los controles y las excepciones, sin escribir nada.
2. **Given** una simulación revisada y aprobada por Sergio, **When** se aplica, **Then** se hace un respaldo verificado previo, el saldo de todas las cuentas queda igual y las imputaciones quedan por fecha de vencimiento.
3. **Given** una aplicación hecha, **When** se revierte, **Then** los datos vuelven exactamente al estado anterior.
4. **Given** una cuenta que no cierra con FIFO, **When** termina la simulación, **Then** queda en la lista de cuentas a revisar con su motivo y no se aplica.
5. **Given** las cuentas que Sergio ya dejó para después (Sierra, Pardo, Franco Rodríguez, Benedit Bursátil, Calderón) y las entidades excluidas, **When** se simula, **Then** se respetan esas exclusiones.

---

### User Story 4 - Corregir por causa, con respaldo y de forma reversible (Priority: P2)

Para cada grupo de excepciones, Sergio decide la regla de corrección y el sistema la aplica, de una vez, a las cuentas del grupo que él tilda una a una, con respaldo verificado previo y posibilidad de revertir. Nunca se corrige cuenta por cuenta ni en la base protegida original.

**Why this priority**: es el segundo paso del método acordado: clasificar, luego corregir por causa. Sin esto el control solo informa.

**Independent Test**: para un grupo (por ejemplo, doble descuento con tarjeta de la Cooperativa y Lartirigoyen) se muestra el efecto previsto de la corrección, se aplica con respaldo, la cuenta pasa a coincidir con el Access y la corrección se puede revertir.

**Acceptance Scenarios**:

1. **Given** un grupo de excepciones, **When** Sergio elige una regla de corrección, **Then** se muestra el detalle de lo que cambiaría en cada cuenta (importes, saldo antes y después), con las cuentas sin tildar; solo se aplica a las que él tilda y aprueba, y las demás siguen en el grupo.
2. **Given** una corrección aplicada, **When** el control se vuelve a correr, **Then** las cuentas corregidas salen del grupo y el control indica cuántas cuentas quedan.
3. **Given** una corrección aplicada, **When** Sergio pide revertirla, **Then** los datos vuelven al estado previo y las cuentas vuelven a aparecer en su grupo.
4. **Given** una excepción que necesita información que el sistema no tiene (por ejemplo, el recibo de la retención del certificado 32 de Lartirigoyen), **When** se clasifica, **Then** se informa como "falta documento" con lo que hay que conseguir, no se inventa nada.

---

### User Story 5 - Exportar y guardar la lista de excepciones (Priority: P3)

Sergio exporta a Excel cada grupo de excepciones (o todas) con las cuentas, importes, causa y la fecha de corte y plazo con que se calcularon, para trabajarlas o conservarlas como constancia.

**Why this priority**: es una comodidad; la verificación funciona sin ella.

**Independent Test**: exportar cada grupo y verificar que el archivo trae las mismas cuentas e importes que la pantalla.

**Acceptance Scenarios**:

1. **Given** el control con excepciones, **When** Sergio exporta, **Then** obtiene un Excel con el mismo contenido que la pantalla, más fecha de corte y plazo usados.

---

### Edge Cases

- Cuentas en dólares: nunca se aplica el umbral de $300; la comparación y la tolerancia del FIFO (0,5%) se hacen en la moneda de la cuenta.
- Cuentas de entidades que no son proveedores ni clientes (organismos, bancos, tarjetas, familia y empresa propia) y la caja sin contacto: quedan fuera de la comparación, como en el recálculo FIFO.
- Cuentas sin saldo de referencia en el Access (contactos nuevos): se informan aparte como "sin referencia", no como diferencia.
- Contactos duplicados: se informan agrupados para depuración; el control no los unifica por su cuenta.
- Pagos de más que no son anticipo (sobrepago): excepción propia, no se mezcla con la de plazo.
- Canjes con acopiadores (Cargill y otros), que se compensan con granos, cheques o depósitos: el control no los trata como error por el solo hecho de ser una compensación; Cargill se mide en dólares.
- Datos cargados después del 25/09/2026 (por ejemplo, extractos hasta el 30/09): no entran en la comparación contra el Access.
- Una cuenta con más de una causa a la vez: se informa en cada grupo que corresponda, pero cuenta una sola vez en el total de cuentas con diferencia.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST comparar el saldo de cada cuenta de proveedor y cliente contra el saldo de referencia del Access al 25/09/2026 y excluir de la comparación lo posterior a esa fecha. El Access es solo una referencia: una diferencia con él no es un error por sí sola.
- **FR-002**: El sistema MUST clasificar cada cuenta en una causa: coincide; coincide con causa conocida (diferencia deliberada y documentada, como reasignaciones de contactos o fuentes que el Access no contaba: se muestra en un grupo aparte, abrible, y no cuenta como excepción); diferencia menor a $300 en pesos (nunca umbral en dólares); aplicación fuera de plazo; fuera de plazo decidido a mano o por FIFO; doble descuento con tarjeta; nota sin imputar; impuesto sin boleta; movimiento sin contacto; sobrepago; contacto duplicado; falta documento; sin referencia en el Access; otros.
- **FR-003**: El sistema MUST mostrar las cuentas con diferencia agrupadas por causa, con cantidad de cuentas e importe por grupo, y permitir abrir cada grupo.
- **FR-004**: El sistema MUST marcar como excepción toda aplicación de un pago a una factura cuya diferencia de tiempo supere el plazo máximo configurado (inicial 24 meses), contemplando anticipos de hasta 60 días como normales y marcando los mayores. Las aplicaciones hechas a mano o por el FIFO que superen el plazo no se tratan como excepción: se informan en un grupo aparte ("fuera de plazo, decidido a mano o por FIFO"), visible y abrible, que no cuenta como excepción.
- **FR-005**: El plazo máximo MUST poder ajustarse por Sergio, y cada resultado MUST indicar con qué plazo y fecha de corte se calculó.
- **FR-006**: El control MUST encontrar sin señalarlos los cuatro casos conocidos (Cargill, Cooperativa Agropecuaria, Lartirigoyen y Nidera) y mostrar de cada uno el pago, la factura, los días de diferencia y el importe.
- **FR-007**: El control MUST marcar como posible doble descuento con tarjeta toda aplicación automática de un pago bancario sobre una factura que ya figura pagada con tarjeta.
- **FR-008**: El control MUST ser de solo lectura: informar no modifica ningún dato.
- **FR-009**: El sistema MUST completar el recálculo FIFO para todos los contactos que faltan, primero en simulación sin escribir, luego con aprobación explícita de Sergio, con respaldo verificado previo y reversible; el saldo de cada cuenta MUST permanecer idéntico.
- **FR-010**: El FIFO MUST respetar las reglas ya acordadas (por vencimiento; sin vencimiento = contado; desempate por número de comprobante más bajo; solo las facturas generan deuda; las retenciones son pago; las percepciones integran la factura; dólares al tipo de cambio de la factura; tolerancia de 0,5%) y las exclusiones vigentes (entidades, cuentas dejadas para después, caja sin contacto).
- **FR-011**: Las cuentas que no cierran con el FIFO MUST quedar en la lista de cuentas a revisar con su motivo, sin aplicarse.
- **FR-012**: Toda corrección MUST definirse como una regla general para un grupo de excepciones, mostrando antes el efecto previsto por cuenta (importes, saldo antes y después); Sergio MUST tildar una a una las cuentas a las que se aplica (ninguna viene tildada de antemano), las no tildadas siguen en el grupo, y solo se aplica con su aprobación, con respaldo verificado previo, y MUST poder revertirse.
- **FR-013**: Ninguna corrección MUST escribirse en la base protegida original ni hacerse cuenta por cuenta fuera de una regla de grupo.
- **FR-014**: El sistema MUST permitir exportar cada grupo, o todas las excepciones, a Excel con el mismo contenido que la pantalla más la fecha de corte y el plazo usados.
- **FR-015**: Los usuarios con rol de solo lectura MUST poder ver el control y exportarlo, pero no aplicar ni revertir correcciones.
- **FR-016**: Los textos y pantallas MUST estar en español simple, sin términos técnicos, indicando para cada hallazgo qué significa y qué decisión se pide.
- **FR-017**: Un cambio de imputación que no altera ningún saldo MUST NOT informarse como diferencia en el control; MUST quedar registrado en el historial del FIFO (qué imputaciones cambiaron, cuándo y cómo revertirlas), consultable por Sergio.
- **FR-020**: El sistema MUST ofrecer una pantalla de revisión por cuenta con la lista de movimientos, saldo acumulado, enlaces al comprobante original y al movimiento de origen, y los avisos propios de esa cuenta.
- **FR-021**: Desde esa pantalla MUST poder cambiarse el contacto de un movimiento, anularse una imputación (sin borrarla) y cargarse una nota de ajuste, todo con usuario y fecha y de forma reversible.
- **FR-022**: Cada cuenta MUST poder marcarse como revisada, con nota, fecha, usuario y el saldo del momento, y el sistema MUST avisar si el saldo cambió después; también MUST poder indicarse si su saldo esperado es cero o puede tener saldo, avisando cuando no se cumple.
- **FR-023**: El sistema MUST permitir pasar a la siguiente cuenta sin revisar en orden alfabético, ordenadas de las más fáciles (sin avisos) a las más complicadas, y poder asignar contacto a movimientos sin contacto uno a uno, varios a la vez o por regla.
- **FR-018**: El control MUST informar como causas propias los pagos aplicados de más que no son anticipo (sobrepago) y los contactos duplicados (mismo CUIT, o misma descripción si no hay CUIT), estos últimos solo agrupados para depuración, sin unificarlos; y MUST medir en dólares las cuentas de acopiadores en dólares (por ejemplo Cargill), sin tratar la compensación en sí como error.
- **FR-019**: Lo ya conocido MUST registrarse con un mecanismo único para todas las cuentas y todos los movimientos, sin umbral de importe: reglas de concepto que dan por explicados los movimientos del banco sin contacto (cualquier monto; los no explicados se agrupan por concepto y se decide una regla por grupo) y documentación de la diferencia de una cuenta con su motivo (deja de ser excepción mientras la diferencia siga siendo la documentada). Toda regla se puede dar de baja, con usuario y fecha, y nunca se borra.
- **FR-024**: En las cuentas con documentos en dólares, el sistema MUST mostrar cada documento en su moneda y los pagos y cobros en pesos, con un solo criterio: el saldo en pesos pesifica cada documento en dólares con el tipo de cambio de su factura (sin tipo de cambio se estima con el dólar BNA del día anterior y se avisa), y un saldo en dólares informativo convierte cada importe en pesos con el dólar BNA vendedor divisa del día anterior; la diferencia entre ambos es diferencia de cambio. Un pago en pesos nunca debe mostrarse como si fuera en dólares. Gobierna la moneda en la que el proveedor emite sus documentos (decisión de Sergio, 07/10/2026): si todos están en dólares, el saldo que gobierna es el de dólares; si están en pesos, el de pesos; si tiene de las dos (cuenta bimonetaria), cada documento gobierna en su moneda y, para separar los pagos por moneda, la cuenta necesita el FIFO completo que asigna cada pago a su documento.

### Key Entities

- **Cuenta de contacto**: proveedor o cliente con su saldo en el sistema, su saldo de referencia del Access al corte y la diferencia.
- **Causa de diferencia**: categoría de clasificación de una cuenta (ver FR-002).
- **Aplicación de pago**: relación entre un pago y la factura que cubre, con su fecha, importe y origen (manual, automática, FIFO).
- **Hallazgo**: una excepción concreta (cuenta, pago, factura, importe, días de diferencia, causa, motivo).
- **Grupo de excepciones**: conjunto de hallazgos con la misma causa sobre el que se decide una regla de corrección.
- **Regla de corrección**: acción aprobada por Sergio que se aplica a todo un grupo, con su respaldo y su reversión.
- **Plazo máximo**: cantidad de meses permitida entre la factura y el pago aplicado.
- **Cuenta a revisar**: cuenta que quedó fuera de la aplicación automática, con su motivo.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Sergio ve el estado de todas las cuentas (coinciden y diferencias por causa) en una sola pantalla, en menos de 10 segundos y sin tener que revisar cuentas individuales.
- **SC-002**: Los cuatro casos conocidos (Cargill, Cooperativa, Lartirigoyen, Nidera) aparecen en el control sin que nadie los señale, con su importe y la causa.
- **SC-003**: El 100% de las cuentas con diferencia queda asignado a una causa (incluido "otros"); ninguna se oculta.
- **SC-004**: Tras el FIFO completo, el saldo de todas las cuentas es idéntico al anterior (diferencia de $0 por cuenta) y toda aplicación puede revertirse devolviendo los datos exactamente al estado previo.
- **SC-005**: Las cuentas que hoy coinciden con el Access (436) siguen coincidiendo después de cualquier corrección.
- **SC-006**: Tras corregir los grupos acordados, la cantidad de cuentas con diferencia sin explicación baja a un número que Sergio pueda revisar a mano en una sesión (objetivo: menos de 30 cuentas en "otros").
- **SC-007**: Cada corrección aplicada deja constancia de quién la aprobó, cuándo, qué cambió y cómo revertirla.

## Assumptions

- La base de trabajo es la única donde se escribe; la base original protegida se usa solo para leer y comparar.
- El saldo de referencia del Access al 25/09/2026 es la prueba objetiva de una cuenta bien conciliada; las diferencias con causa conocida y deliberada (reasignaciones, fuentes que el Access no contaba) ya están documentadas y se reconocen como causa, no como error.
- El plazo máximo inicial de 24 meses lo eligió Sergio (el 06/10/2026) y lo puede ajustar mirando los resultados; los anticipos siguen la regla acordada (normalmente hasta 60 días, mayores se marcan).
- El FIFO completo reutiliza el motor, los controles y el mecanismo de aplicación y reversión de la feature 032; esta feature no cambia sus reglas.
- Quedan fuera de alcance, y se tratan al final: la carga faltante de boletas de impuestos (impuestos sin boleta) y los residuos menores (los dos créditos "transferencias cash proveedores" de Galicia, Mario Gorosito). Caja efectivo y sueldos no se agregan a la vista de cuentas (duplicarían).
- Las cinco tarjetas y Mercado Pago ya están cerradas por la feature 034 y no se vuelven a auditar aquí.
- Solo Sergio aprueba y aplica correcciones; los demás usuarios con permisos de lectura solo consultan.
- Las excepciones que requieren información externa (recibos, facturas faltantes) se informan como faltante y no se resuelven inventando datos.
