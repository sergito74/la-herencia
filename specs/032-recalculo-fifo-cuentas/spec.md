# Feature Specification: Recálculo FIFO de cuentas corrientes

**Feature Branch**: `032-recalculo-fifo-cuentas`
**Created**: 2026-10-01
**Status**: Draft
**Input**: Reemplazar la estrategia de lotes de corrección de 031 por un recálculo FIFO automático, por contacto, de los vínculos pago→documento en cuentas de proveedores y clientes.

## Contexto

La estrategia 031 corregía vínculos de a uno. Esa estrategia anulaba anticipos, anulaba facturas enteras por "doble imputación" y exigía reemplazos de igual importe. Aplicada, rompía cuentas que hoy cierran, como J y M de la Serna, Ganaderos de Elordi o Jauregui y Morales. Ningún lote se aplicó. El dueño no puede revisar 15 años de registros a mano. El sistema tiene que resolver solo y mostrar excepciones por contacto.

## Clarifications

### Session 2026-10-01

- Q: ¿Cuál es el desempate entre documentos de la misma fecha? → A: Primero el número de comprobante más bajo.
- Q: ¿El FIFO ordena por emisión o por vencimiento? → A: Por vencimiento. Un documento sin vencimiento se considera de contado, con vencimiento igual a la fecha de emisión.
- Q: ¿Qué orden siguen las compras con plazo, por ejemplo a cosecha? → A: Primero la que vence primero.
- Q: ¿Los remitos y órdenes sin factura generan deuda? → A: No. Solo cuentan las facturas.
- Q: ¿Cómo se tratan las retenciones? → A: Son parte del pago, cancelan deuda e integran la cuenta.
- Q: ¿Las percepciones y recargos integran el total de la factura? → A: Sí.
- Q: ¿Cómo se tratan los contactos duplicados? → A: Se unifican para el recálculo y se marcan como duplicados para depurarlos después.
- Q: ¿Hay canjes sin documento? → A: No. Siempre hay un documento que respalda el canje.
- Q: ¿En qué moneda se compensa una cuenta como la de Cargill? → A: En dólares.
- Q: ¿Se sabe a quién se endosó cada e-cheq o cheque de terceros? → A: Sí. La tabla "Valores Recibidos" registra la fecha de endoso y el destino.
- Q: ¿Con qué frecuencia se corre el recálculo? → A: Una sola vez, para sanear el histórico. Después, los movimientos nuevos se aplican periódicamente y el saldo se mantiene al día.
- Q: ¿Hay períodos cerrados? → A: No. Todo puede ajustarse.
- Q: ¿Los vínculos manuales son fijos? → A: No. El recálculo puede ajustarlos.
- Q: ¿Quién aplica y confirma? → A: Solo Sergio.
- Q: ¿Qué tolerancia de cierre se usa? → A: 0,5% del total.
- Q: ¿Un pago nuevo se aplica solo? → A: Sí, si la cuenta sigue cumpliendo los controles. Si no, queda como propuesta pendiente. El disparador es que el movimiento tenga contacto identificado.
- Q: ¿Qué pasa si se paga una factura puntual que no es la más vieja? → A: Se respeta la elección explícita, y el FIFO reparte solo lo que no tiene destino.
- Q: ¿Hay facturas en reclamo? → A: Conviene poder suspender una factura para que el FIFO la saltee, aunque es poco habitual.
- Q: ¿Para qué son las notas de crédito sin factura de origen? → A: Ajuste de tipo de cambio, devolución de mercadería o anulación de una factura mal emitida. Cuando se anula, se registran la factura y la nota de crédito.
- Q: ¿Cómo se emiten los ajustes de tipo de cambio? → A: Uno por cada documento en dólares.
- Q: ¿Qué tipo de cambio pesifica los pagos en pesos de facturas en dólares? → A: El oficial vendedor del BNA del día anterior al pago.
- Q: ¿Hay cuentas separadas por moneda? → A: No, una sola cuenta por contacto. Ejemplo: Cargill factura en dólares y paga las liquidaciones en pesos.
- Q: ¿De dónde sale el saldo inicial? → A: Solo de los datos del sistema. Las cuentas viejas se conciliaron en Access hace años. Los últimos 4 o 5 años no se conciliaron.
- Q: ¿Qué se hace con las excepciones? → A: Quedan pendientes para trabajarlas una a una.
- Q: ¿Qué relación hay entre las dos razones sociales? → A: Oscar V. Giamberardini (CUIT 20-04602264-6) fue la etapa de transición; después operó Giamigli de Bolivar S.A. (CUIT 30-71211460-2). En la mayoría de los casos el saldo pasó de una a otra, así que cada contacto es una sola cuenta continua. La transición se ve en el BNA: la cuenta 1640001709 de Oscar (2010-08 a 2012-06) pasa a la 1640029280 de Giamigli (2012-03 a 2022-07), reemplazada por la 6150111899 (desde 2022-02).
- Q: ¿Desde qué fecha se concilia? → A: Desde el primer comprobante cargado, que es del 19/04/2010. Es el inicio de la administración bajo este sistema.
- Q: ¿Se usan los PDF de comprobantes? → A: Por ahora solo para consultar. Hay unos 6.800 en Dropbox y en Documentos, nombrados por fecha de emisión y proveedor. Ventas contiene liquidaciones de granos y de hacienda.
- Q: ¿Hay facturas faltantes? → A: Puede haberlas, sobre todo en la cuenta XXXXXXXXX (contacto 97). ASP (contacto 17) no envió todas las notas de ajuste: su cuenta está en 0, pero faltan comprobantes.
- Q: ¿Qué vencimiento tienen las facturas que no lo traen? → A: Se tratan como contado. No hay condiciones de pago fijas.
- Q: ¿Los cobros siguen la misma regla? → A: Sí, igual que en compras.
- Q: ¿Qué avisos hacen falta? → A: Un aviso semanal con los vencimientos de los próximos 15 días.
- Q: ¿Por dónde empieza el saneamiento? → A: Por los contactos de mayor volumen.
- Q: ¿Cómo se registra el vencimiento de las compras nuevas? → A: El alta tiene un selector "Contado / A plazo", con "Contado" por defecto. Si es a plazo, se cargan una o más cuotas con su fecha de vencimiento.
- Q: ¿Cuántos contactos entran en la primera etapa? → A: 5 contactos complejos y 4 simples, para validar el criterio antes de seguir.
- Q: ¿Qué pasa con las cuentas que no continuaron de Oscar a Giamigli? → A: Tienen que cerrar en 0. No hay ejemplos conocidos.
- Q: ¿Cómo se detectan los duplicados? → A: Manda el CUIT. Si falta, se deducen por la descripción y quedan como posibles duplicados para confirmar.
- Q: ¿Los movimientos de caja de efectivo tienen contacto? → A: No siempre. Muchos son retiros o aportes a la caja, no pagos a proveedores.
- Q: ¿Cómo y cuándo se muestra el aviso semanal? → A: Los lunes, como un aviso del sistema al entrar.
- Q: ¿Qué vencimiento tienen las ventas? → A: La fecha de la liquidación. La base no guarda una fecha de pago pactada (decisión del 2026-10-01, tras el análisis).
- Q: ¿Cómo se distingue la factura elegida al pagar de un vínculo manual ajustable? → A: Lo diseña el equipo (ver FR-024).
- Q: ¿Cómo se mide el cierre en cuentas en dólares? → A: En la moneda del documento. La diferencia en pesos entre el tipo de cambio de la factura y el del pago va a un renglón de diferencia de cambio.
- Q: ¿Qué pasa con un pago de más que no es anticipo? → A: Aparece como excepción para ver qué pasó.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Simular el recálculo FIFO y ver el impacto por contacto (Priority: P1)

El administrador ejecuta el recálculo en modo simulación. Para cada contacto ve el aplicado actual, el aplicado recalculado, si la cuenta cierra antes y después, y los controles que fallan. No se escribe nada.

**Why this priority**: Sin una simulación confiable no se puede decidir aplicar nada.

**Independent Test**: Correr la simulación y comprobar que no cambió ningún registro. Verificar también que los contactos que hoy cierran siguen cerrando: J y M de la Serna, Ganaderos de Elordi y Colombo y Colombo.

**Acceptance Scenarios**:

1. **Given** un contacto con pagos y facturas, **When** se simula, **Then** cada pago cubre la factura pendiente más antigua según la fecha real de erogación, y lo aplicado es igual al menor entre lo pagado y lo facturado.
2. **Given** un contacto que hoy cierra, **When** se simula, **Then** sigue cerrando. Si no cierra, aparece en excepciones con el motivo.
3. **Given** la simulación terminada, **When** se consulta, **Then** se ve una lista por contacto, filtrable por "cierra / no cierra / empeora / mejora". No se muestra registro por registro.

---

### User Story 2 - Aplicar el recálculo con respaldo y reversión (Priority: P1)

El administrador aplica el resultado simulado a todos los contactos o a los que elija. Antes se hace una copia de respaldo, y se puede revertir en un paso.

**Why this priority**: Es la corrección real de las cuentas.

**Independent Test**: Aplicar, verificar los controles, revertir y comprobar que todo queda igual que antes.

**Acceptance Scenarios**:

1. **Given** una simulación, **When** se aplica, **Then** los vínculos recalculados reemplazan a los anteriores no protegidos (protegido = cadena real de tarjeta o cheque; las elecciones manuales se respetan mientras pasen los controles, según FR-024), quedan identificados como generados por FIFO y se guarda un respaldo.
2. **Given** un recálculo aplicado, **When** se vuelve a correr sin cambios en los datos, **Then** el resultado es idéntico y no genera cambios.
3. **Given** un recálculo aplicado, **When** se revierte, **Then** los vínculos vuelven exactamente al estado anterior.

---

### User Story 3 - Cuentas mixtas y saldo inicial (Priority: P2)

En contactos que compran y venden, como los acopiadores (Cargill), ventas y compras se compensan entre sí. Para contactos con arrastre de saldo antiguo, el sistema estima un saldo inicial.

**Why this priority**: Son las cuentas más complejas y de mayor volumen. Sin esto no pueden cerrar.

**Independent Test**: Simular Cargill. Verificar que las ventas de granos compensan las compras de insumos y que el saldo neto coincide con la cuenta corriente.

**Acceptance Scenarios**:

1. **Given** un contacto con ventas y compras, **When** se simula, **Then** las ventas cubren las compras pendientes en orden FIFO y el resto se cancela con dinero. El saldo neto coincide con la cuenta corriente.
2. **Given** un contacto cuyo primer movimiento es un pago o cobro sin documentos previos, **When** se simula, **Then** el sistema propone un saldo inicial estimado, lo marca como estimado y lo muestra en excepciones para confirmarlo.

---

### User Story 4 - Alimentar el flujo de caja por rubro (Priority: P2)

Cada aplicación resultante se reparte en los rubros de la factura, prorrateada por sus líneas. Los anticipos sin factura van a un rubro de anticipos.

**Why this priority**: Es el objetivo final: saber en qué se gastó cada peso.

**Independent Test**: Comparar el flujo por rubro de un período antes y después. La suma por rubro tiene que ser igual a los pagos del período.

**Acceptance Scenarios**:

1. **Given** un pago aplicado a dos facturas de rubros distintos, **When** se ve el flujo por rubro, **Then** el pago aparece repartido según lo aplicado a cada factura y sus líneas.
2. **Given** un anticipo sin factura, **When** se ve el flujo, **Then** aparece en "Anticipos a proveedores" o "Anticipos de clientes" hasta que se aplique.

---

### User Story 5 - Mantener las cuentas aplicadas y ver el saldo por vencimiento (Priority: P2)

Después del saneamiento inicial, los pagos y cobros nuevos se aplican periódicamente con la misma regla FIFO. El saldo de cada cuenta muestra, para lo no vencido, cuánto vence en cada fecha.

**Why this priority**: Evita que las cuentas se vuelvan a desordenar y muestra cuándo hay que pagar o cobrar.

**Independent Test**: Cargar un pago nuevo y correr la aplicación periódica. El pago tiene que cubrir la factura que vence primero. Para un contacto con us$ 30.000 adeudados, el saldo tiene que mostrar us$ 20.000 con vencimiento en marzo y us$ 10.000 en junio.

**Acceptance Scenarios**:

1. **Given** un pago nuevo, **When** corre la aplicación periódica, **Then** cubre los documentos pendientes por vencimiento sin modificar las aplicaciones ya hechas que siguen siendo válidas.
2. **Given** un saldo pendiente, **When** se consulta la cuenta, **Then** se ve el saldo separado en vencido y en tramos por fecha de vencimiento, en la moneda de la cuenta.

### Edge Cases

- **Documento sin vencimiento:** se trata como contado y vence en su fecha de emisión.
- **Retenciones:** las de Ganancias, IIBB y otras practicadas al pagar cancelan deuda junto con el dinero.
- **Contactos duplicados:** se unifican para el recálculo y quedan marcados para depurarse.

- **Anticipo de más de 60 días:** se acepta y se marca para revisión. Nunca se anula.
- **Tarjeta o cheque propio:** se respeta la factura vinculada al consumo o al cheque, y la fecha de erogación es la del débito bancario.
- **Cheque sin débito:** se usa la fecha de emisión y se marca como provisorio.
- **Valores recibidos y endosados:** la fecha es la del endoso.
- **Factura pagada en parte por tarjeta:** el FIFO cubre solo el saldo restante, y la factura nunca se anula entera.
- **Nota de crédito con factura de origen:** se aplica primero a esa factura. Sin factura de origen, entra como crédito en su fecha.
- **Factura en USD:** se pesifica con el tipo de cambio de la factura. Los documentos marcados "Ajusta tipo de cambio" ajustan la diferencia.
- **Pagos que exceden lo facturado:** el excedente queda como anticipo abierto y nunca sobreaplica.
- **Contacto sin pagos o sin facturas:** no genera vínculos ni excepciones.
- **Venta de hacienda cobrada antes de la liquidación:** se trata como anticipo de cliente.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST recalcular por contacto los vínculos pago→documento con FIFO. Cada crédito cubre el documento pendiente que vence primero. Un documento sin vencimiento vence en su fecha de emisión. El desempate es por número de comprobante más bajo. Solo las facturas y notas de débito generan deuda; los remitos y órdenes no.
- **FR-002**: Cada pago o cobro MUST tomar su fecha real de erogación.
  - Banco y efectivo: fecha del movimiento.
  - Tarjeta y cheque propio: fecha del débito bancario.
  - Valores endosados: fecha del endoso.
- **FR-003**: Un crédito sin documento pendiente MUST quedar como anticipo y cubrir el siguiente documento. Los anticipos de más de 60 días MUST marcarse para revisión.
- **FR-004**: Las cadenas reales factura←consumo de tarjeta/cheque←débito MUST respetarse. El FIFO solo reparte pagos directos sobre el saldo restante.
- **FR-005**: Las notas de crédito MUST aplicarse primero a su factura de origen, si la tienen. Si no, entran como crédito en su fecha.
- **FR-006**: Los documentos USD MUST pesificarse con el tipo de cambio de la factura. El cierre de un documento USD MUST medirse en dólares. La diferencia en pesos entre el tipo de cambio de la factura y el del pago (FR-026) MUST registrarse como un renglón de diferencia de cambio, sin afectar el control de cierre. Los documentos "Ajusta tipo de cambio" MUST incorporarse como ajuste de esa diferencia.
- **FR-007**: En contactos con compras y ventas, ventas y compras pendientes MUST compensarse entre sí en orden FIFO antes de aplicar dinero. Cada canje se respalda con su documento. Si la cuenta opera en dólares, la compensación MUST hacerse en dólares.
- **FR-008**: El sistema MUST estimar un saldo inicial cuando los primeros movimientos no se explican con documentos cargados. Ese saldo MUST marcarse como estimado y requiere confirmación antes de aplicarse.
- **FR-009**: El sistema MUST ofrecer una simulación sin escrituras, con comparación antes/después por contacto. La comparación incluye aplicado, si cierra, sobreaplicaciones, anticipos abiertos y marcas.
- **FR-010**: Los controles automáticos por contacto MUST verificar tres condiciones. Los contactos que fallen MUST listarse como excepciones con su motivo.
  - Ningún documento tiene aplicado mayor que su total.
  - Ningún pago tiene aplicado mayor que su importe.
  - El aplicado es igual al menor entre pagado y facturado, con una tolerancia de 0,5%.
- **FR-011**: Las cuentas que hoy cierran MUST recalcularse con la misma regla y seguir cerrando. Si una deja de cerrar, MUST mostrarse como excepción y no aplicarse sin confirmación.
- **FR-012**: Aplicar MUST incluir un respaldo previo y ser reversible en un paso. Solo se opera sobre la base WC.
- **FR-013**: El proceso MUST ser determinista e idempotente.
- **FR-014**: Los vínculos generados MUST identificarse como recálculo FIFO, con la ejecución y el usuario.
- **FR-015**: El flujo por rubro de 030 MUST usar los vínculos resultantes. Cada aplicación se reparte por las líneas de la factura, y los anticipos abiertos van a un rubro de anticipos.
- **FR-016**: Al adoptar este proceso, MUST descartarse el lote 4 de 031 y dejar de proponerse lotes con sus reglas. La regla de "documento sobreaplicado" queda cubierta por FR-010.
- **FR-017**: Solo un usuario con rol admin (hoy, únicamente Sergio) MUST poder aplicar, revertir y confirmar saldos iniciales. Los demás roles solo ven la simulación.
- **FR-018**: Las retenciones practicadas al pagar MUST contar como parte del pago. Las percepciones y recargos MUST integrar el total de la factura.
- **FR-019**: Los contactos duplicados MUST unificarse para el recálculo y marcarse como duplicados, con una lista para depurarlos.
- **FR-020**: Los cheques de terceros MUST cancelar la cuenta del emisor en la fecha de recepción y la del destinatario en la fecha de endoso, según el registro de valores recibidos.
- **FR-021**: Después del saneamiento inicial, los movimientos nuevos MUST aplicarse periódicamente con la misma regla. Las aplicaciones válidas no se mueven.
- **FR-022**: El saldo de cada cuenta MUST mostrarse separado en vencido y en tramos por fecha de vencimiento, en la moneda de la cuenta.
- **FR-023**: Todos los períodos MUST poder ajustarse en el recálculo. No hay ejercicios cerrados. Los vínculos manuales son ajustables en los términos de FR-024.
- **FR-024**: Una aplicación vigente cargada a mano en la pantalla de aplicaciones de pago (origen `manual`) es una elección explícita y MUST respetarse; el FIFO reparte solo el resto. Si la elección hace fallar un control del contacto (factura o pago sobreaplicado), el recálculo MUST reasignar solo el exceso por FIFO y marcar el contacto como 'manual-ajustado'. Las aplicaciones automáticas (`automatica-*`, `fifo-032`) nunca son elecciones. Un vínculo hecho a mano en la conciliación de tesorería (movimiento con documento) también se trata como elección explícita, con el mismo criterio de recorte.
- **FR-025**: Una factura MUST poder marcarse como suspendida o en reclamo, y el FIFO la saltea hasta que se libere.
- **FR-026**: Un pago en pesos de un documento en dólares MUST convertirse con el tipo de cambio oficial vendedor del BNA del día anterior al pago. Cada contacto tiene una sola cuenta, aunque mezcle monedas.
- **FR-027**: El recálculo MUST empezar el 19/04/2010, fecha del primer comprobante. Cada contacto es una cuenta continua a través de la etapa de Oscar V. Giamberardini y la de Giamigli de Bolivar S.A.
- **FR-028**: Un movimiento nuevo con contacto identificado MUST aplicarse automáticamente si la cuenta sigue cumpliendo los controles. Si no, MUST quedar como propuesta pendiente. Un movimiento sin contacto nunca se aplica solo.
- **FR-029**: Las excepciones MUST quedar pendientes para trabajarlas una a una. No se cierran automáticamente con ajustes.
- **FR-030**: El sistema MUST generar un aviso semanal con los vencimientos de los próximos 15 días.
- **FR-031**: El saneamiento MUST poder aplicarse por etapas. La primera etapa incluye 5 contactos complejos de gran volumen y 4 simples.
- **FR-032**: El vencimiento de una compra MUST tomarse de sus cuotas cargadas. Con varias cuotas, cada una es un tramo separado para el FIFO y para el saldo por vencimiento. Una compra de contado o sin cuotas vence en su fecha de emisión.
- **FR-033**: El vencimiento de una liquidación de granos o hacienda MUST ser su fecha de liquidación.
- **FR-034**: Los contactos sin continuidad entre la etapa de Oscar V. Giamberardini y la de Giamigli de Bolivar S.A. MUST cerrar en 0. Si no cierran, MUST aparecer como excepción.
- **FR-035**: Los duplicados MUST detectarse por CUIT. Si falta el CUIT, MUST proponerse por similitud de descripción y requieren confirmación.
- **FR-036**: Los movimientos de caja sin contacto, como retiros, aportes y traspasos, MUST quedar fuera del recálculo. Nunca se asignan a un proveedor por deducción.
- **FR-037**: Un pago o cobro que excede lo facturado y no puede imputarse como anticipo a un documento posterior MUST aparecer como excepción.
- **FR-038**: El aviso de vencimientos MUST mostrarse los lunes al entrar al sistema.

### Key Entities

- **Contacto**: proveedor, cliente o ambos. Es la unidad de recálculo y de excepción.
- **Documento (débito)**: factura, nota de débito, venta, liquidación de hacienda o saldo inicial, con fecha, total pesificado y aplicado.
- **Crédito**: pago, cobro, nota de crédito, compensación cruzada o anticipo, con fecha real de erogación e importe.
- **Aplicación**: crédito, documento e importe, con su origen (FIFO, cadena o manual) y la ejecución.
- **Ejecución de recálculo**: simulación o aplicación, con fecha, usuario, respaldo, estado y resumen.
- **Excepción por contacto**: los controles que fallan, las diferencias y las marcas (anticipo largo, saldo estimado, cheque provisorio).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100% de los contactos que hoy cierran siguen cerrando, o figuran como excepción con motivo.
- **SC-002**: Tras aplicar, ningún documento ni pago queda sobreaplicado en los contactos aplicados.
- **SC-003**: Al menos el 90% de los contactos con movimientos pasan todos los controles sin intervención manual.
- **SC-004**: La revisión humana se limita a la lista de excepciones por contacto y a los registros marcados.
- **SC-005**: Re-ejecutar sin cambios en los datos produce cero diferencias.
- **SC-006**: Revertir deja los vínculos idénticos al estado previo.
- **SC-007**: La simulación de todos los contactos termina en menos de 5 minutos.
- **SC-008**: En el flujo por rubro, la suma de rubros de cada período es igual al total de pagos del período.

## Assumptions

- Se trabaja solo sobre la base WC, según la regla de oro del proyecto.
- Las cuotas no guardan importe. Cada cuota vale el total de la compra dividido en partes iguales, con el redondeo en la última cuota.
- Los vencimientos de las compras están en la tabla de cuotas, no en el campo de vencimiento de la compra.

  | Condición | Compras |
  | --- | --- |
  | A plazo | 2.373 |
  | Contado | 2.787 |
  | Sin vencimiento, se trata como contado | 1.280 |

  64 compras tienen más de una cuota.
- Propuesta para la primera etapa, a confirmar en el plan:
  - Complejos: Cargill, J y M de la Serna, Jauregui y Morales, Coop. Eléctrica Bolívar y Ganaderos de Elordi.
  - Simples: Colombo y Colombo, Supermercado Actual, Autopistas del Sol y Miguel Basterrechea (contacto 220).
- Hay 2 compras sin fecha. Quedan como excepción de datos.
- Las cuentas de ASP y XXXXXXXXX pueden no cerrar por comprobantes faltantes. Se espera que queden como excepciones.
- Hoy no quedan aplicaciones manuales vigentes. Si aparecen, el recálculo puede ajustarlas. Solo las cadenas de tarjeta y cheque quedan fijas.
- 60 días es el plazo normal de un anticipo, sobre todo en labores. Un plazo mayor no invalida el pago.
- La mayoría de los contactos arranca en cero. El saldo inicial se estima como la diferencia entre el saldo de la cuenta corriente y lo que explican los documentos cargados.
- La compensación cruzada aplica a cualquier contacto con compras y ventas, no solo a Cargill.
- Un e-cheq de un acopiador cancela su cuenta en la fecha de recepción y la del tercero en la fecha de endoso.
- Se reutiliza la fuente unificada de vínculos de 031 para leer las cadenas de tarjeta y cheque.
