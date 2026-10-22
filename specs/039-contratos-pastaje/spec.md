# Feature Specification: Contratos de pastaje (ingresos)

**Feature Branch**: `039-contratos-pastaje`

**Created**: 2026-10-22

**Status**: Draft

**Input**: User description: "Módulo de ingresos por contratos de pastaje para Giamigli de Bolívar S.A. (establecimiento La Herencia): parametrizar las condiciones del acuerdo, actualizar mensualmente el monto por el índice pactado (kg de novillo INMAG), emitir la liquidación mensual para el cliente y cargar las facturas emitidas en ARCA, con impacto en cuenta corriente, cobros y resultado." Respuestas de Sergio a 38 preguntas (22/10/2026) y consulta previa a agentes 06 (hacienda), 07 (dirección financiera) y 01/04 (datos).

## Clarifications

### Session 2026-10-22

- Q: Cuando la hacienda sale, muere o falta, ¿se cobra el día del evento? → A: No. Se cobra el día de ingreso; el día de egreso, muerte o faltante no se cobra.
- Q: ¿A qué campaña se imputa el ingreso de pastaje en el resultado? → A: Campaña ganadera julio–junio, según el mes liquidado (septiembre 2026 → 2026/27).
- Q: Si después de confirmar una liquidación cambia el índice o la bitácora, ¿qué pasa con ese mes? → A: La liquidación queda fija; la diferencia se alerta y se resuelve con ND/NC, acompañada de una liquidación de ajuste en PDF para el cliente.

## Contexto

- Un contrato de pastaje es un servicio: el dueño del campo recibe hacienda de un tercero para que coma pasto y agua por un tiempo; **no cede el uso de la tierra** (no es arrendamiento). El dueño del campo mantiene alambrados y aguadas; el dueño del ganado asume mortandad natural y sanidad.
- **Empresa**: solo Giamigli de Bolívar S.A. (CUIT 30-71211460-2). "La Herencia" es el nombre del establecimiento, no factura.
- **Contrato vigente (caso real)**: Ganadera San Justo S.S. (CUIT 30-71594327-8), 70 vaquillonas ingresadas el 25/09/2026, 5 kg de novillo por cabeza por mes, índice INMAG, mes vencido, IVA 21%, contado. Sin contrato escrito.
- **Caso de referencia que debe reproducirse al centavo** (liquidación del 05/10/2026 y factura A 0002-00000008 del 06/10/2026, CAE 86406417014230):
  70 cab × 5 kg × 6/30 días = 70 kg; INMAG promedio de los días con hacienda en el campo con índice publicado (25/09 $4.068,21 y 29/09 $4.241,83) = $4.155,02/kg; neto $290.851,40; IVA 21% $61.078,79; total $351.930,19.
- Fuentes: `C:\Users\Sergio\Documents\La Herencia\Ganaderia\Pastaje - La Herencia\Liquidación de Pastaje - Septiembre.pdf` (formato del informe al cliente) y `C:\Users\Sergio\Dropbox\Giamigli de Bolivar SA\Ventas\04 2026 - 03 2027\20261006_Giamigli.pdf` (factura).
- Antecedente: hasta 2023 Giamigli pagaba pastaje a Duffau Arricau (gasto). Aquí es el caso inverso (ingreso); los gastos de pastaje existentes no se tocan.
- La tabla existente de índice novillo (cargada desde 2020) **no coincide** con los valores INMAG usados (25/09: 4.166,21 vs 4.068,21). Es otro índice: no se usa para pastaje; se crea un registro propio de INMAG.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Registrar y consultar las condiciones del contrato (Priority: P1)

Sergio da de alta un contrato de pastaje con el cliente, las categorías de hacienda, la tarifa (kg de novillo/cabeza/mes o precio fijo), el índice, la modalidad de cobro, el plazo y las cláusulas de texto (infraestructura, sanidad, mortandad), y lo consulta en el menú **Condiciones**.

**Why this priority**: sin condiciones parametrizadas no hay cálculo ni liquidación.

**Independent Test**: cargar el contrato San Justo y verificar que Condiciones muestra partes, 70 vaquillonas, 5 kg/cab/mes, INMAG, mes vencido, IVA 21%, contado y cláusulas.

**Acceptance Scenarios**:

1. **Given** un cliente existente, **When** se crea un contrato con una o más categorías y tarifa en kg/cab/mes, **Then** queda Vigente y visible en Condiciones con su ficha completa.
2. **Given** un contrato con PDF de contrato escrito, **When** se adjunta, **Then** puede abrirse desde Condiciones; sin PDF el contrato es igualmente válido.
3. **Given** dos contratos simultáneos de distintos clientes, **When** se listan, **Then** cada uno muestra sus cabezas actuales, monto estimado del mes en curso y estado de facturación.
4. **Given** un usuario de solo lectura, **When** entra a Condiciones, **Then** consulta todo pero no puede crear ni modificar.

---

### User Story 2 - Bitácora de hacienda (Priority: P1)

Sergio registra los movimientos fechados de la hacienda del cliente: ingresos, egresos parciales, muertes, faltantes y recuentos, con número de DTe cuando corresponde.

**Why this priority**: las cabezas-día por fecha son la base del cálculo proporcional.

**Independent Test**: ingreso de 70 vaquillonas el 25/09 con DTe; las cabezas vigentes al 30/09 son 70 y las cabezas-día de septiembre 420.

**Acceptance Scenarios**:

1. **Given** un contrato, **When** se registra un egreso parcial o una muerte con fecha, **Then** esas cabezas dejan de cobrarse desde ese día (el día del evento no se cobra) y la bitácora conserva el historial.
2. **Given** un recuento que no coincide con las cabezas del sistema, **When** se guarda, **Then** se muestra una alerta con la diferencia y no se ajustan cabezas hasta que Sergio registre el movimiento explicativo (muerte, faltante, egreso) o confirme el ajuste.
3. **Given** un nacimiento de terneros, **When** se registra, **Then** las crías figuran en la bitácora pero no se cobran hasta registrar su destete (desde esa fecha pagan con la tarifa de su categoría).
4. **Given** un movimiento cargado con error, **When** se anula con motivo, **Then** el cálculo de los meses no facturados se recalcula y el de meses ya facturados muestra diferencia (ver US5).

---

### User Story 3 - Índice INMAG diario automático (Priority: P1)

El sistema obtiene y registra todos los días el índice INMAG publicado por el Mercado Agroganadero de Cañuelas, y permite cargarlo o corregirlo a mano con respaldo.

**Why this priority**: el monto mensual depende del promedio del índice.

**Independent Test**: los valores del 25/09/2026 ($4.068,21) y 29/09/2026 ($4.241,83) quedan registrados; los días sin remate quedan sin valor (no cero).

**Acceptance Scenarios**:

1. **Given** un día con remate, **When** corre la búsqueda diaria, **Then** se registra fecha, valor, fuente y momento de obtención, una sola vez por fecha.
2. **Given** que la fuente no responde, **When** falla la búsqueda, **Then** se reintenta y se muestra en Condiciones un aviso de índice faltante; se puede cargar a mano con nota.
3. **Given** un valor corregido después de haber liquidado un mes, **When** se registra, **Then** el mes afectado muestra la diferencia de índice para resolver con ND/NC.

---

### User Story 4 - Liquidación mensual para el cliente (Priority: P1)

Al iniciar cada mes el sistema prepara la **Liquidación de Pastaje** del mes vencido con el mismo formato que la de septiembre, para que Sergio la revise y la envíe al cliente antes de facturar.

**Why this priority**: es la práctica comercial actual y la base de la factura.

**Independent Test**: la liquidación de septiembre 2026 del contrato San Justo reproduce exactamente 70 kg, $4.155,02, $290.851,40 + IVA.

**Acceptance Scenarios**:

1. **Given** el primer día del mes, **When** hay contratos con hacienda en el mes anterior, **Then** queda una liquidación en borrador por contrato con detalle por categoría (cabezas, días, kg), días de índice usados con sus valores, precio promedio, neto, IVA y total.
2. **Given** una liquidación en borrador, **When** Sergio la confirma, **Then** se genera el PDF con el formato de referencia y queda fijada (no cambia aunque luego cambien bitácora o índice; esos cambios aparecen como diferencia).
3. **Given** un mes con movimientos de cabezas a mitad de mes, **When** se liquida, **Then** el cálculo usa cabezas-día por tramos y el informe muestra cada tramo.
4. **Given** días del período sin índice publicado, **When** se calcula el promedio, **Then** se usan solo los días con índice publicado dentro de los días con hacienda en el campo; si no hay ninguno, la liquidación queda bloqueada con aviso.

---

### User Story 5 - Facturas emitidas y su seguimiento (Priority: P2)

En el menú **Facturas** (vinculado a Condiciones), Sergio sube el PDF de la factura emitida en ARCA; el sistema lee número, fecha, CAE, neto, IVA y total, la vincula a la liquidación del mes y la registra en la cuenta corriente del cliente para su cobro.

**Why this priority**: cierra el ciclo de ingreso; depende de la liquidación.

**Independent Test**: subir la factura A 0002-00000008 y verificar que queda vinculada a la liquidación de septiembre, sin diferencia, en la cuenta corriente de Ganadera San Justo por $351.930,19.

**Acceptance Scenarios**:

1. **Given** una liquidación confirmada, **When** se sube el PDF de la factura, **Then** los datos leídos se muestran para confirmar y se comparan con la liquidación; diferencias se señalan antes de guardar.
2. **Given** una liquidación confirmada sin factura, **When** Sergio va a emitirla, **Then** el sistema sugiere el texto del detalle ("Servicio de pastaje de 70 Vaquillonas del 25 al 30 de septiembre de 2026") e importes para copiar en ARCA.
3. **Given** una factura del mismo número ya cargada, **When** se intenta cargar de nuevo, **Then** se rechaza el duplicado.
4. **Given** una diferencia posterior (índice corregido, movimiento retroactivo), **When** Sergio la resuelve, **Then** carga una ND o NC emitida vinculada a la factura original; la factura original no se modifica.
5. **Given** una factura en cuenta corriente, **When** se registra el cobro (banco, caja o cheque) con o sin retenciones sufridas, **Then** la factura queda cancelada total o parcialmente usando los cobros existentes del sistema.

---

### User Story 6 - Panel de control devengado vs facturado (Priority: P2)

Condiciones muestra, por contrato y mes, lo devengado, liquidado, facturado y cobrado, con alertas.

**Independent Test**: con septiembre liquidado y facturado y octubre en curso, el panel muestra septiembre "Facturado — pendiente de cobro" y octubre "En curso" con monto estimado al día.

**Acceptance Scenarios**:

1. **Given** un mes cerrado sin liquidación o sin factura, **When** se abre el panel, **Then** aparece alerta "mes sin facturar".
2. **Given** una diferencia entre liquidado y recalculado (índice o bitácora), **Then** aparece alerta con el importe de la diferencia.
3. **Given** el ingreso facturado, **When** se consulta el resultado por campaña, **Then** aparece como ingreso "Pastaje" del establecimiento La Herencia, separado de arrendamientos y ventas de hacienda.

### Propuesta de pantallas

- **Condiciones** (lista + ficha): tarjetas por contrato con cliente, estado, cabezas actuales por categoría, tarifa (kg/cab/mes), último INMAG y promedio del mes en curso, monto estimado del mes, próximo paso ("Liquidar septiembre", "Cargar factura", "Cobro pendiente"). Ficha con pestañas: *Condiciones* (parámetros y cláusulas, contrato adjunto), *Bitácora* (línea de tiempo de movimientos con cabezas vigentes), *Liquidaciones*, *Facturas*, *Índice* (valores INMAG del período con días usados).
- **Facturas**: grilla por mes con liquidación, factura, ND/NC, cobrado y saldo, con acceso a PDFs.
- Formatos según la regla global de números y moneda del sistema.

### Edge Cases

- Mes de 31 o 28/29 días: divisor = días reales del mes (los animales comen todos los días).
- Contrato que termina a mitad de mes: se liquida hasta el día anterior al egreso total.
- Ingreso y egreso el mismo mes; varios ingresos escalonados.
- Ningún día con índice INMAG en los días con hacienda: bloquear liquidación y permitir carga manual.
- Contrato con precio fijo en pesos o US$ (sin índice): monto = cabezas-día × precio; US$ siguen la regla del TC del comprobante.
- Varias categorías con tarifas distintas en el mismo contrato.
- Recuento con más cabezas que las registradas.
- Factura leída con datos ilegibles o de otro emisor/cliente: no se guarda sin confirmación manual.
- Redondeo: solo al importe final (neto e IVA a centavos); kg y precio promedio con su precisión, mostrados a 2 decimales.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE permitir crear, editar (sin afectar meses ya liquidados) y finalizar contratos de pastaje de Giamigli de Bolívar S.A. con: cliente, establecimiento (La Herencia), fecha de inicio, fecha de fin opcional, modalidad (mes vencido), condición de venta (contado), alícuota de IVA (21%), contrato escrito adjunto opcional y cláusulas de texto (infraestructura, sanidad, mortandad, otras).
- **FR-002**: Cada contrato DEBE admitir una o más categorías de hacienda, cada una con su tarifa: kg de novillo por cabeza por mes con índice INMAG, o precio fijo por cabeza por mes en pesos o US$.
- **FR-003**: DEBE soportar varios contratos vigentes simultáneos.
- **FR-004**: DEBE registrar una bitácora por contrato con movimientos fechados: ingreso, egreso parcial, egreso total, muerte, faltante, nacimiento, destete, recuento; con categoría, cabezas, DTe opcional, observación y usuario; anulación con motivo, sin borrado.
- **FR-005**: Un recuento DEBE comparar contra las cabezas vigentes y alertar la diferencia sin modificar cabezas automáticamente.
- **FR-006**: Las cabezas-día DEBEN calcularse por día calendario: el día de ingreso se cobra, el día de egreso/muerte/faltante no; crías cobran desde el destete.
- **FR-007**: El sistema DEBE obtener y registrar automáticamente cada día el índice INMAG (fuente Mercado Agroganadero de Cañuelas), con fecha, valor, fuente y momento de obtención; días sin remate sin valor; carga y corrección manual auditada.
- **FR-008**: El precio del mes DEBE ser el promedio simple del índice INMAG de los días del mes en que hubo hacienda del contrato en el campo y existe índice publicado.
- **FR-009**: Importe del mes por categoría = cabezas-día × kg/cab/mes ÷ días del mes × precio promedio; neto = suma; IVA = neto × 21%; redondeo a centavos solo en neto e IVA. El caso septiembre 2026 DEBE dar $290.851,40 / $61.078,79 / $351.930,19.
- **FR-010**: El primer día de cada mes el sistema DEBE preparar una liquidación en borrador por contrato del mes vencido; Sergio la revisa y confirma; al confirmar se genera el PDF con el formato de la liquidación de referencia, se guarda en la carpeta de documentos del contrato y la liquidación queda fijada. El envío al cliente lo hace Sergio; el sistema no envía mails.
- **FR-011**: DEBE permitir cargar la factura emitida subiendo su PDF, leyendo tipo, punto de venta, número, fecha, CAE, vencimiento CAE, cliente, neto, IVA y total, con confirmación manual y comparación contra la liquidación; una factura por liquidación mensual; sin duplicados por número.
- **FR-012**: DEBE sugerir el texto del renglón de factura con el formato "Servicio de pastaje de {cabezas} {categoría} del {día} al {día} de {mes} de {año}" (una línea por categoría si hay varias).
- **FR-013**: Diferencias posteriores a una factura DEBEN resolverse con ND/NC emitidas vinculadas a la factura original; la factura no se modifica. El sistema DEBE generar para el cliente una liquidación de ajuste en PDF (mismo formato, con original, recalculado y diferencia) que respalde la ND/NC.
- Q: ¿Cómo le llega la liquidación al cliente? → A: El sistema genera el PDF y lo guarda en la carpeta del contrato (hoy `Documents\La Herencia\Ganaderia\Pastaje - La Herencia`); Sergio lo envía. El sistema no envía mails.
- **FR-014**: Facturas, ND y NC DEBEN impactar una sola vez en la cuenta corriente del cliente y poder cobrarse con los mecanismos de cobro existentes (banco, cajas de efectivo, cheques), incluyendo retenciones sufridas.
- **FR-015**: El ingreso DEBE imputarse a establecimiento La Herencia y a la campaña ganadera julio–junio del mes liquidado, identificado como "Pastaje" en el resultado, separado de arrendamientos y ventas de hacienda.
- **FR-016**: Condiciones DEBE mostrar por contrato y mes: devengado, liquidado, facturado, cobrado, saldo y alertas (mes sin liquidar/facturar, índice faltante, diferencia entre liquidado y recalculado, recuento con diferencia).
- **FR-017**: Usuarios de solo lectura DEBEN poder consultar todo sin poder escribir; toda alta, cambio y anulación queda auditada (usuario, fecha, motivo).
- **FR-018**: Toda escritura DEBE ir a la base de trabajo, nunca a la base original protegida, y no modificar los gastos de pastaje históricos.

### Key Entities

- **Contrato de pastaje**: cliente, empresa, establecimiento, vigencia, modalidad, condición de venta, IVA, cláusulas, adjunto, estado.
- **Tarifa por categoría**: categoría de hacienda, tipo (kg novillo/índice o precio fijo), valor, moneda, vigencia desde.
- **Movimiento de bitácora**: contrato, fecha, tipo, categoría, cabezas, DTe, observación, estado/anulación.
- **Índice INMAG diario**: fecha, valor $/kg, fuente, origen (automático/manual), momento de obtención, nota.
- **Liquidación mensual**: contrato, período, tramos por categoría (cabezas, días, kg), días de índice usados, precio promedio, neto, IVA, total, estado (borrador/confirmada), PDF.
- **Comprobante emitido de pastaje**: tipo (factura/ND/NC), número, fecha, CAE, importes, PDF, liquidación o comprobante vinculado, cliente.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: La liquidación de septiembre 2026 del contrato San Justo coincide al centavo con la liquidación y la factura reales.
- **SC-002**: Sergio prepara la liquidación mensual de un contrato y la deja lista para enviar en menos de 5 minutos.
- **SC-003**: El índice INMAG de cada día con remate queda registrado sin intervención manual en al menos 95% de los días hábiles de un mes.
- **SC-004**: Ningún mes con hacienda en el campo queda sin alerta si no fue liquidado y facturado dentro del mes siguiente.
- **SC-005**: Cada factura de pastaje aparece una sola vez en la cuenta corriente del cliente y su saldo coincide con facturado − cobrado.
- **SC-006**: Cargar una factura desde su PDF requiere solo confirmar datos leídos (sin tipear importes) en el caso de referencia.

## Assumptions

- Mes vencido como modalidad única por ahora; adelantado queda fuera hasta que exista un contrato así.
- La liquidación se fija al confirmarse; recalcular un mes ya liquidado solo genera diferencia informativa.
- INMAG se obtiene de la publicación pública del Mercado Agroganadero; si cambia el formato de la fuente, la carga manual cubre el hueco.
- La categoría de hacienda se toma del catálogo existente de tipos de hacienda.
- Retenciones sufridas y cobros reutilizan los mecanismos existentes; no se crea un nuevo circuito de cobranza.
- Fuera de alcance: stock, sanidad y peso del ganado ajeno; emisión en ARCA; conexión con SENASA; mantenimiento de infraestructura; capitalización u hotelería con participación en kilos; contratos de otras empresas.
