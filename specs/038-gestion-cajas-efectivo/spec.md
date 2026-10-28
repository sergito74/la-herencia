# Feature Specification: Gestión de cajas de efectivo

## Ampliación solicitada por Sergio — 28/10/2026

**FR-018 / US7 — Efectivo contra transferencia al socio.** Una sola carga registra el efectivo que entrega un socio y la transferencia del banco de Giamigli al mismo socio por idéntico importe. Elegir socio, fecha, importe y transferencia existente; mostrar ambas piernas y saldo del socio sin cambio. No cargar un aporte y un retiro por separado. Es un canje de disponibilidades: caja +X, banco −X, sin gasto, ganancia ni deuda/crédito económico nuevo del socio. Conservar la identidad del socio en operación y filtros, sin dos asientos de valuación sin sustancia económica.

Tipo `canje_socio`, caja Giamigli en pesos o caja chica. Exige socio y débito bancario íntegro del mismo importe/fecha. Si el débito identifica un contacto, debe ser el contacto bancario de ese socio (Sergio socio5670, nunca empleado375); sin contacto, la elección del socio identifica el destinatario. Rechazar aporte o retiro previo del socio del mismo importe/fecha, vínculos/aplicaciones ajenos, moneda distinta, otro contacto o crédito bancario. No ejecuta transferencias ni genera otro débito: vincula el extracto cargado. Si falta, informar el dato faltante y conservar borrador. Confirmación/anulación atómicas e idempotentes; conservar banco original.

Aceptación: carga500000 deja caja+500000, banco−500000 y socio sin cambio; reintento no duplica; anulación restaura vínculos/caja; fallo intermedio no deja efectos. Cubrir destinatario equivocado, banco usado, retiro previo, importes/fechas distintos y estado vacío/error con datos simulados.

**Feature Branch**: `038-gestion-cajas-efectivo`

**Created**: 2026-10-22

**Status**: Implemented (verificación con datos simulados y lecturas de WC; sin operaciones de prueba reales)

**Input**: User description: "Módulo de administración y gestión de cajas de efectivo (Giamigli SA, caja chica del campo y caja del Condominio LSC). Hoy las cajas son solo lectura (027) y se cargan desde la planilla Cajas Giamigli.xlsx. Se necesita operar las cajas desde el sistema: aportes y retiros de socios, pagos a proveedores, cobros, traspasos entre cajas y con bancos, y arqueos; cada movimiento reflejado una sola vez en las cuentas que correspondan, auditable."

## Clarifications

### Session 2026-10-22

- Q: ¿La caja del Condominio se administra completa o solo sus movimientos con Giamigli? → A: Solo los movimientos que tienen relación con Giamigli (aportes, préstamos, pagos de gastos de Giamigli, retiros vinculados). El Condominio tiene su propio sistema de administración independiente; alquileres y gastos de los inmuebles quedan fuera.
- Q: ¿Se deja de usar la planilla Cajas Giamigli.xlsx desde un corte o conviven? → A: Conviven hasta que Sergio confíe en que el sistema es robusto y funciona sin errores; durante ese período el sistema importa lo nuevo de la planilla sin duplicar y se compara contra ella.

## Contexto

- Hay tres cajas cargadas en el sistema, todas de **solo lectura** hoy:

  | Caja | Saldo | Fecha |
  |---|---:|---|
  | Giamigli SA | $381.785,15 | 15/10/2026 |
  | Caja chica del campo | $96.907 | 15/10/2026 |
  | Condominio LSC | $0,23 | 11/09/2026 |

- Origen de cada una:
  - **Giamigli y caja chica:** se reconstruyeron desde la planilla Cajas Giamigli.xlsx (spec 027 y revisión 036).
  - **Condominio LSC:** desde su planilla "Movimientos LSC desde Abr 2016".
- Hoy cada operación se anota en las planillas. Si además afecta a un proveedor o a un socio, se vuelve a cargar a mano en el sistema. Esto genera duplicados y omisiones, que se vieron en la revisión 036.
- **Reglas de negocio vigentes (036):**
  - Compras particulares: el pago queda en el proveedor, con un asiento Particular y la deuda del socio.
  - Retiros iguales de los socios = retiro de ganancias, no deuda.
  - La cuenta de Sergio está separada en empleado (375) y socio (5670).
  - Sueldos cobrados y devueltos a caja = no cobrados + traspaso.
  - Valuación de la cuenta de socio en kg de novillo / US$.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Pagar a un proveedor en efectivo desde una caja (Priority: P1)

Quien administra la caja paga una factura (o un gasto sin comprobante) en efectivo: elige la caja, el proveedor, las facturas a cancelar y el importe. La caja baja, y la cuenta corriente del proveedor muestra el pago aplicado a esas facturas, una sola vez.

**Why this priority**: Es la operación más frecuente de la caja (la mayoría de las 1.844 filas históricas son pagos) y la que hoy se duplica entre planilla y sistema.

**Independent Test**: Registrar un pago en efectivo de una factura pendiente y verificar que la caja baja en el importe, la factura queda cancelada y la cuenta del proveedor muestra un solo pago.

**Acceptance Scenarios**:

1. **Given** una factura pendiente de un proveedor, **When** se registra un pago en efectivo desde la caja Giamigli por su total, **Then** el saldo de la caja baja ese importe, la factura queda cancelada y el pago aparece una vez en la cuenta del proveedor y una vez en la caja.
2. **Given** un gasto sin comprobante ("XXXXXXXX"), **When** se registra desde la caja con concepto y rubro, **Then** baja la caja y queda imputado al rubro sin crear deuda con ningún contacto.
3. **Given** una compra particular de un socio pagada con la caja, **When** se registra el pago, **Then** el pago queda en el proveedor, se genera el asiento Particular y la deuda en la cuenta del socio (regla 036).

---

### User Story 2 - Aportes y retiros de socios en efectivo (Priority: P1)

Un socio (Sergio, Lucy, Ceci o el Condominio LSC) aporta efectivo a una caja, o retira. En los retiros, el usuario elige si es **retiro a cuenta** (queda como deuda del socio) o **retiro de ganancias** (distribución, no es deuda).

**Why this priority**: Es el hilo que une las cajas con las cuentas de socios, y hoy es la principal fuente de diferencias (ver 036).

**Independent Test**: Registrar un aporte de Sergio de $100.000 a la caja Giamigli y verificar que la caja sube y que la cuenta de socio de Sergio muestra el aporte a su favor, valuado en kg/US$ a la fecha.

**Acceptance Scenarios**:

1. **Given** la caja Giamigli, **When** se registra un aporte en efectivo de un socio, **Then** la caja sube y la cuenta de socio refleja el aporte a su favor, valuado a la fecha, una sola vez.
2. **Given** un retiro marcado como "retiro de ganancias" de varios socios por partes iguales, **When** se registra, **Then** la caja baja y no se genera deuda en las cuentas de socio.
3. **Given** un retiro "a cuenta", **When** se registra, **Then** la caja baja y la cuenta del socio refleja la deuda.

---

### User Story 3 - Traspasos entre cajas y con bancos (Priority: P2)

Reponer la caja chica desde la caja grande, extraer efectivo del banco para la caja o depositar efectivo de la caja en el banco, incluido el caso en que el dinero pasa por la cuenta personal de un socio (retiro del banco a la cuenta de Sergio, que lo trae en efectivo).

**Why this priority**: Evita que un mismo dinero aparezca como gasto o como aporte cuando solo cambió de lugar.

**Independent Test**: Registrar una reposición de $100.000 de caja Giamigli a caja chica y verificar que una baja y la otra sube, sin efecto en cuentas de contactos ni de socios.

**Acceptance Scenarios**:

1. **Given** dos cajas, **When** se registra un traspaso, **Then** el origen baja y el destino sube el mismo importe, en la misma fecha, vinculados entre sí.
2. **Given** una extracción del banco vinculada a un movimiento del extracto, **When** se registra el ingreso a la caja, **Then** el movimiento bancario queda vinculado y no figura en la cuenta de ningún contacto.

---

### User Story 4 - Cobros en efectivo (Priority: P2)

Registrar un cobro en efectivo de un cliente o comprador (venta, alquiler) aplicado a su documento.

**Why this priority**: Menos frecuente que los pagos, pero necesario para que la caja refleje todos sus ingresos.

**Independent Test**: Registrar un cobro en efectivo de una venta pendiente y verificar que la caja sube y el documento queda cobrado.

**Acceptance Scenarios**:

1. **Given** una venta pendiente de cobro, **When** se registra el cobro en efectivo en una caja, **Then** la caja sube y la cuenta del cliente muestra el cobro aplicado, una sola vez.

---

### User Story 5 - Arqueo de caja (Priority: P2)

Contar el efectivo por denominación de billete y compararlo con el saldo del sistema; si hay diferencia, registrarla explícitamente como "diferencia de arqueo".

**Why this priority**: La planilla hoy tiene arqueos periódicos ("Recuento Caja Efectivo") y son la única prueba física del saldo.

**Independent Test**: Cargar un arqueo cuyo total difiere del saldo en $249,10 y verificar que queda registrado el arqueo y, si se confirma, un movimiento de diferencia que iguala el saldo.

**Acceptance Scenarios**:

1. **Given** el saldo de una caja, **When** se carga un recuento por denominaciones, **Then** el sistema muestra el total contado y la diferencia contra el saldo.
2. **Given** una diferencia, **When** el usuario la confirma, **Then** se registra un movimiento "diferencia de arqueo" y el saldo queda igual al contado.

---

### User Story 6 - Consultar y corregir movimientos (Priority: P3)

Ver cada caja con su saldo, movimientos y filtros (fecha, tipo, socio, contacto); anular un movimiento erróneo sin borrarlo; ver quién y cuándo registró o anuló cada movimiento.

**Why this priority**: Auditoría y corrección, sobre lo ya existente en 027.

**Independent Test**: Anular un pago mal cargado y verificar que caja, proveedor y socio vuelven al estado anterior y que el movimiento sigue visible como anulado.

**Acceptance Scenarios**:

1. **Given** un movimiento registrado, **When** se anula con motivo, **Then** todos sus efectos (caja, contacto, socio, vínculo bancario) se revierten juntos y el movimiento queda visible como anulado con usuario y motivo.

### Edge Cases

- Pago que dejaría la caja en negativo: se advierte y se pide confirmación (la planilla histórica tuvo saldos negativos).
- Pago parcial de una factura, o un pago que cancela varias facturas.
- Pago en efectivo de una factura en US$: se sigue la regla vigente de TC del comprobante + nota de débito/crédito (036).
- Movimientos con fecha anterior a un arqueo ya confirmado: se advierte que modifica un período arqueado.
- Movimiento que afecta a un socio y a un proveedor a la vez (compra particular): un solo registro con todos sus efectos.
- Operación de un socio desde su cuenta personal hacia la caja (cobro del sueldo devuelto en efectivo): se registra como traspaso, no como aporte (opción A de 036).
- Caja del Condominio: solo se registran los movimientos con Giamigli (FR-014).
- Durante la convivencia, un movimiento cargado en el sistema y también anotado en la planilla: la importación lo reconoce y no lo duplica (FR-015).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST permitir registrar, en una caja elegida (Giamigli, caja chica, Condominio LSC), estos tipos de movimiento: pago, cobro, aporte de socio, retiro de socio (a cuenta o de ganancias), traspaso entre cajas, extracción/depósito bancario, gasto sin comprobante y diferencia de arqueo.
- **FR-002**: Cada movimiento MUST guardar fecha, caja, tipo, importe, concepto, contacto o socio cuando aplique, rubro/centro de costo cuando sea un gasto, comprobante cuando exista, la marca de cuenta A/B y el usuario que lo registró.
- **FR-003**: Un pago o cobro a un contacto MUST aplicarse a sus documentos (facturas, ventas), incluido el pago parcial y el pago de varios documentos, y MUST aparecer una sola vez en la cuenta corriente del contacto y una sola vez en la caja.
- **FR-004**: Un aporte o retiro "a cuenta" de un socio MUST reflejarse una sola vez en su cuenta de socio, valuado en kg de novillo / US$ a la fecha con las cotizaciones del sistema (regla de 021/036).
- **FR-005**: Un retiro marcado como "retiro de ganancias" MUST NOT generar deuda ni crédito en la cuenta del socio.
- **FR-006**: Un pago de compra particular desde una caja MUST aplicar la regla de compras particulares (pago en el proveedor, asiento Particular, deuda del socio).
- **FR-007**: Un traspaso entre cajas MUST generar la salida y la entrada vinculadas, por el mismo importe y en la misma fecha, sin efecto en contactos ni socios cuando ambas cajas pertenecen a Giamigli. Los cruces con la caja del Condominio son aportes/devoluciones con dos piernas físicas y un único efecto de socio.
- **FR-008**: Una extracción o depósito bancario MUST poder vincularse al movimiento del extracto bancario correspondiente (ya importado) y, una vez vinculado, ese movimiento bancario MUST NOT figurar en la cuenta de ningún contacto.
- **FR-009**: El sistema MUST permitir cargar un arqueo por denominación de billete y moneda, mostrar la diferencia contra el saldo y, si el usuario la confirma, registrar el movimiento de diferencia.
- **FR-010**: El sistema MUST mostrar para cada caja el saldo actual, los movimientos con saldo corrido y filtros por fecha, tipo, contacto y socio, y el último arqueo con su diferencia y estado de vigencia. Los filtros de tipo/contacto/socio solo restringen filas: saldo corrido real de caja y subtotal filtrado se muestran separados.
- **FR-011**: La anulación MUST ser no destructiva: el movimiento queda visible como anulado, con motivo, usuario y fecha, y se revierten juntos todos sus efectos (caja, cuenta corriente, cuenta de socio, vínculos).
- **FR-012**: Solo los usuarios con permiso de escritura MUST poder registrar o anular; los de solo lectura ven las cajas sin poder operar (mismo criterio que el resto del sistema).
- **FR-013**: Los movimientos históricos cargados desde las planillas (027/036) MUST seguir visibles y mantener sus vínculos (fila de planilla, pago de Access), sin duplicarse con los nuevos.
- **FR-014**: Para la caja del Condominio LSC, el sistema MUST registrar solo los movimientos que la vinculan con Giamigli (aportes y préstamos a Giamigli, pagos de gastos de Giamigli, devoluciones, retiros relacionados). Las operaciones propias del Condominio (alquileres, gastos de los inmuebles, retiros de los socios que no involucran a Giamigli) quedan fuera: el Condominio tiene su propio sistema. La historia 036 ajena o sin vínculo comprobado queda archivada fuera del libro operativo, conservando originales y clasificación auditada. Solo las relaciones documentadas se muestran como movimientos vinculados.
- **FR-015**: Durante un período de convivencia (hasta que Sergio lo dé por terminado), la planilla Cajas Giamigli.xlsx sigue en uso: el sistema MUST poder importar sus filas nuevas sin duplicar las ya registradas (en el sistema o importadas antes), identificando cada fila de la planilla, y MUST mostrar una comparación caja por caja (saldo y movimientos) entre planilla y sistema que señale diferencias. Al terminar la convivencia, el sistema pasa a ser la única fuente.
- **FR-016**: Un movimiento con fecha anterior a un arqueo confirmado MUST mostrar una advertencia antes de guardarse.
- **FR-017**: Un movimiento que deje la caja en saldo negativo MUST pedir confirmación explícita.

### Key Entities

- **Caja**: lugar físico de efectivo de Giamigli SA o caja chica, con su saldo. El Condominio LSC tiene un registro parcial de movimientos vinculados con Giamigli, cuyo neto no representa caja física ni saldo de socio.
- **Movimiento de caja**: entrada o salida de efectivo, con tipo, fecha, importe, cuenta A/B, contraparte (contacto, socio, otra caja o banco), usuario y estado (vigente/anulado).
- **Aplicación**: relación entre un pago/cobro de caja y los documentos del contacto que cancela.
- **Movimiento de socio**: efecto del aporte/retiro en la cuenta de socio valuada (existente, 021).
- **Traspaso**: par de movimientos vinculados (caja↔caja o caja↔banco).
- **Arqueo**: recuento por denominaciones en una fecha, con total, diferencia y estado (borrador/confirmado).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un pago en efectivo de una factura se registra en menos de 1 minuto y queda reflejado en la caja y en la cuenta del proveedor sin carga adicional.
- **SC-002**: Cero movimientos duplicados entre caja, cuentas corrientes y cuentas de socio en una muestra de 50 operaciones de prueba (cada operación produce exactamente un efecto en cada cuenta que corresponde).
- **SC-003**: Al terminar un mes, el saldo de cada caja coincide con el arqueo físico, o la diferencia queda registrada explícitamente.
- **SC-004**: Conservar los saldos reconstruidos de Giamigli $381.785,15 y caja chica $96.907. El $0,23 del Condominio corresponde al archivo completo 036 y deja de ser indicador operativo: la vista del Condominio contiene únicamente relaciones documentadas (31 históricas, neto -$9.298.765,84 al corte de la limpieza del 23/10/2026), sin ajustes ficticios para reproducir el saldo completo.
- **SC-005**: Toda anulación revierte el 100% de sus efectos en las cuentas relacionadas.

## Assumptions

- Las tres cajas y sus saldos reconstruidos (036, 22/10/2026) son el punto de partida; no se vuelve a migrar la historia.
- Las cotizaciones (dólar BNA, índice novillo) ya están en el sistema y se actualizan solas (036).
- Los extractos bancarios se siguen importando como hoy; este módulo solo vincula movimientos, no importa extractos.
- La marca de cuenta A/B (blanco/negro) que usa la planilla se conserva como atributo del movimiento.
- Permisos: el mismo esquema de roles existente (016); no se crean roles nuevos.
- Moneda: las cajas son en pesos; la caja en dólares de la planilla (2023, 6 movimientos) queda fuera de alcance de esta versión.

## Precisiones posteriores al análisis — 22/10/2026

Sergio autorizó corregir los siete hallazgos. Estas precisiones complementan los requisitos; no registran operaciones reales.

- FR-007 / US2–US3: traspaso interno sin efecto de socio solo entre Giamigli y caja chica. Aporte del Condominio desde su caja: salida Condominio, entrada Giamigli/chica y un crédito al socio 3, en una operación. Devolución: piernas inversas y un débito al socio 3. No añadir otro pago al contacto 549. Pago directo de gasto de Giamigli desde caja Condominio: una salida física, un pago proveedor y un crédito socio, sin movimiento ficticio en caja Giamigli.
- FR-002 / US1: gasto sin comprobante persiste como gasto interno no fiscal y repartos rastreables. Entra una sola vez en costos; anulación revierte caja y costo juntos, sin factura ni deuda ficticia.
- FR-009 / US5: anular ajuste de arqueo invalida el arqueo en la misma transacción. Conservar recuento, saldo observado y diferencia original; mostrar saldo recalculado y diferencia vigente aparte. No reabrir el recuento: corregir con un nuevo arqueo enlazado. Operación retroactiva aceptada marca los arqueos posteriores afectados como Desactualizado; no acreditan conciliación vigente hasta nuevo recuento.
- FR-010: calcular saldo real antes de filtros de tipo/contacto/socio y paginación; mostrar subtotal filtrado separado. Filas anuladas visibles no afectan saldo.
- US3, opción A: exigir liquidación salarial, débito bancario y retorno de efectivo documentados. Para liquidación/débito/retorno de $10.000: caja +$10.000, banco −$10.000, débito excluido como pago salarial y liquidación cancelada por Ajuste Interno explícito «no cobrado» de 036; cero aporte al socio. No sumar otro cobro salarial. Anulación revierte efectos propios y restaura clasificación/aplicaciones previas bajo versión. Montos parciales o diferencias sin regla documentada quedan pendientes, sin cancelación automática. Los pares compensados de cuenta de socio desde noviembre de 2017 conservan su tratamiento histórico: no convertirlos automáticamente en opción A.


## Corrección de alcance aprobada — 23/10/2026
Sergio reemplaza la conservación visible de toda la caja del Condominio por un registro exclusivo de relaciones con Giamigli. Ver [criterios, contrato y plan de corrección](limpieza-condominio-20261023.md). Históricos ajenos/sin vínculo documentado permanecen archivados, fuera de saldos, filtros y comparaciones operativas. El neto parcial no representa tenencia física ni deuda; no admite arqueos físicos. Una sola entrada de Condominio con cuenta de socio y movimientos vinculados, sin sumar ni duplicar sus efectos.
