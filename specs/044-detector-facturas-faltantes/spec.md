# Feature Specification: Detector de facturas faltantes de proveedores

**Feature Branch**: `044-detector-facturas-faltantes`

**Created**: 2026-10-28

**Status**: Draft

**Input**: User description: "Detector de facturas faltantes de proveedores (044). Diseño acordado en specs/036-revision-sistematica-cuentas/auditoria-aplicaciones-20261028.md §7 (y §9/§9bis: lección de falsos positivos). Avisar qué comprobantes de proveedores probablemente faltan cargar, sin crear facturas provisorias ni tocar saldos; recurrentes por ciclo y período facturado; no recurrentes por señales; tablero 'Facturas esperadas este mes'; aviso al cargar un pago sin factura; marca de pendiente vinculada al pago; alarmas rotuladas como 'a verificar'; sin cosas internas en pantalla; excluir Ganadera San Justo; cuentas con resumen del proveedor siguen su resumen; ARCA solo con autorización; integrar con la rutina 043 (aviso el día 5)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Tablero de facturas esperadas del mes (Priority: P1)

Sergio abre "Facturas esperadas" y ve, para cada proveedor que factura con regularidad (Movistar, Coop. Eléctrica, Estudio Criado, Sancor, Starlink, Fideicomiso La Esperanza, etc.), si la factura del período en curso **llegó**, está **pendiente** (todavía dentro del plazo esperable) o está **atrasada** (pasó el plazo). Cada fila dice el período que debería cubrir, la fecha aproximada en que suele llegar y el monto esperado. Desde la fila puede abrir la cuenta del proveedor o cargar la factura.

**Why this priority**: es la prevención: detectar el faltante en el mes en que ocurre evita que el FIFO arrastre pagos a facturas posteriores (problema masivo de la auditoría 036) y que el Cash Flow muestre comprobantes equivocados.

**Independent Test**: con los datos reales de WC, el tablero muestra Movistar con la factura de jun-2025 como faltante histórico conocido, Coop. Eléctrica como bimestral sin falsos atrasos, y Estudio Criado sin falsos faltantes en nov/dic-2024.

**Acceptance Scenarios**:

1. **Given** un proveedor que factura todos los meses y cuya factura del período llegó, **When** Sergio abre el tablero, **Then** la fila figura como "Llegó" con el comprobante.
2. **Given** un proveedor bimestral (Coop. Eléctrica), **When** pasa un mes sin factura, **Then** no figura como atrasado.
3. **Given** un proveedor cuya factura del período no llegó y ya pasó la fecha esperada más el margen, **When** Sergio abre el tablero, **Then** figura como "Atrasada — a verificar", con el período, el monto esperado y la última factura recibida.
4. **Given** dos comprobantes en el mismo mes calendario de un proveedor mensual (uno tapa al otro, caso Movistar jun-2025), **When** se evalúa el período, **Then** el detector controla por período facturado y marca el período que quedó sin comprobante.

---

### User Story 2 - Alarmas de faltantes no recurrentes (Priority: P2)

Para proveedores sin ciclo regular, el detector lista alarmas a verificar: pago al proveedor sin factura compatible, pago a cuenta o saldo a favor de más de 90 días, retención de Ganancias (SICORE) emitida sin factura asociada, y remito sin facturar a los 60 días. Cada alarma explica la señal, muestra el pago/retención/remito que la origina y permite abrir el movimiento.

**Why this priority**: cubre el resto de los faltantes que el tablero recurrente no ve (compras sueltas), que son la otra fuente de huecos que corren el FIFO.

**Independent Test**: sobre WC, el listado incluye los casos ya verificados en la auditoría 036 como faltantes reales y no presenta ninguno como error confirmado.

**Acceptance Scenarios**:

1. **Given** un pago a un proveedor sin factura compatible (importe y fecha razonables), **When** se genera el listado, **Then** aparece como "Pago sin factura — a verificar".
2. **Given** una retención de Ganancias sin factura del proveedor en el período, **When** se genera el listado, **Then** aparece como alarma.
3. **Given** un remito de compra sin factura vinculada con más de 60 días, **When** se genera el listado, **Then** aparece como alarma.

---

### User Story 3 - Marcar un pago "a cuenta, falta factura" (Priority: P2)

Cuando Sergio confirma que a un pago le falta la factura, lo marca como pendiente: queda "a cuenta, falta factura de [período] ≈ $[monto]" en la cuenta del proveedor y en el tablero hasta que se carga la factura real, momento en que la marca se cierra sola. La marca nunca crea comprobantes ni mueve saldos.

**Why this priority**: es la alternativa acordada a las facturas provisorias; deja el hueco a la vista sin contaminar deuda ni Cash Flow.

**Independent Test**: marcar un pago, verificar que el saldo de la cuenta no cambió al centavo, cargar la factura y verificar que la marca se cerró.

**Acceptance Scenarios**:

1. **Given** una alarma de pago sin factura, **When** Sergio la marca como "falta factura", **Then** queda visible en la cuenta y en el tablero, y el saldo no cambia.
2. **Given** un pago marcado, **When** se carga una factura compatible del proveedor, **Then** la marca se cierra y queda registrado cuándo y con qué comprobante.
3. **Given** una alarma que resultó falsa, **When** Sergio la descarta con un motivo, **Then** no vuelve a aparecer por la misma señal.

---

### User Story 4 - Aviso al cargar un pago sin factura (Priority: P3)

Al registrar un pago a un proveedor sin aplicarlo a ninguna factura, el sistema avisa (sin bloquear) y ofrece dejarlo marcado como "a cuenta, falta factura".

**Why this priority**: prevención en el origen; secundaria al tablero.

**Independent Test**: cargar un pago sin aplicación y ver el aviso con la opción de marcarlo.

**Acceptance Scenarios**:

1. **Given** un pago sin aplicaciones, **When** Sergio lo confirma, **Then** ve el aviso y puede marcarlo o seguir sin marcar.

---

### User Story 5 - Aviso de cierre de mes y ajustes por proveedor (Priority: P3)

El día 5 de cada mes la rutina de documentos nuevos (043) muestra un resumen de facturas atrasadas del mes anterior. Desde la ficha del proveedor Sergio puede fijar a mano su ciclo (mensual, bimestral, trimestral, sin ciclo) y el margen; si un proveedor no factura en 3 ciclos, el sistema pregunta una vez si se dio de baja.

**Why this priority**: completa la rutina y corrige al detector cuando aprende mal; depende de las historias 1 y 2.

**Independent Test**: fijar el ciclo de un proveedor y ver que el tablero lo respeta; simular 3 ciclos sin factura y ver la pregunta única.

**Acceptance Scenarios**:

1. **Given** el día 5 del mes, **When** corre la rutina 043, **Then** el aviso lista las facturas atrasadas del mes anterior.
2. **Given** un proveedor sin facturas en 3 ciclos, **When** Sergio abre el tablero, **Then** ve una sola pregunta "¿se dio de baja?" y no aparece como atrasado; si responde que sí, deja de esperarse.

### Edge Cases

- Proveedor con pocas facturas (menos de 6): no se le aprende ciclo; solo entra en alarmas no recurrentes.
- Proveedor que cambió de ciclo (de mensual a bimestral): el ciclo se aprende de las últimas facturas, no de toda la historia.
- Factura cargada con fecha errónea (caso Estudio Criado 676/693): puede generar un falso faltante; la alarma lo rotula "a verificar" y muestra la factura vecina para que se vea.
- Proveedores con cuenta en dólares o con resumen emitido por el proveedor (Cargill, Bayá Casal, FEDEA, Lartirigoyen): el detector no reimputa nada; solo avisa faltantes de comprobantes.
- Compras particulares de socios con total 0: cuentan como comprobante recibido del período.
- Ganadera San Justo: excluida siempre.
- Pago que cubre dos períodos juntos: no genera dos alarmas si el monto es compatible con dos facturas esperadas.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST aprender, para cada proveedor con al menos 6 facturas en los últimos 24 meses, su ciclo de facturación (mensual, bimestral, trimestral) a partir de la distancia típica entre sus últimas 12 a 24 facturas, con tolerancia ±25%; si no hay un ciclo claro, el proveedor es no recurrente.
- **FR-002**: Sergio MUST poder fijar a mano el ciclo y el margen de un proveedor, y el valor manual prevalece sobre el aprendido.
- **FR-003**: El sistema MUST evaluar por período facturado: cada período esperado (desde la última factura según el ciclo) queda "llegó" si hay un comprobante que lo cubre, "pendiente" si aún no venció la fecha esperada más el margen (15 días para mensual, 25 para ciclos mayores) y "atrasado" si venció.
- **FR-004**: El sistema MUST calcular un monto esperado por período (último monto ajustado por la tendencia reciente) y marcar como "cambio de monto" una factura recibida que difiera más de 30%.
- **FR-005**: El sistema MUST considerar señal fuerte de faltante un pago al proveedor en un período sin comprobante, y mostrarlo junto al período atrasado.
- **FR-006**: Si un proveedor recurrente no factura en 3 ciclos, el sistema MUST preguntar una sola vez si se dio de baja, sin marcarlo atrasado; la respuesta queda guardada.
- **FR-007**: El sistema MUST listar alarmas no recurrentes: pago sin factura compatible, pago a cuenta o saldo a favor de más de 90 días, retención de Ganancias sin factura del proveedor, remito sin factura a los 60 días.
- **FR-008**: Toda salida del detector MUST rotularse como alarma "a verificar"; nunca se presenta como error confirmado.
- **FR-009**: Sergio MUST poder marcar un pago como "a cuenta, falta factura" (período y monto aproximado opcionales) y descartar una alarma con un motivo; ninguna de las dos acciones crea comprobantes ni modifica saldos, aplicaciones o Cash Flow.
- **FR-010**: Una marca de falta factura MUST cerrarse automáticamente cuando se carga una factura compatible del proveedor, registrando el comprobante y la fecha.
- **FR-011**: El tablero MUST mostrar por proveedor: estado del período (llegó / pendiente / atrasada / ¿baja?), período, fecha esperada, monto esperado, último comprobante, y acceso a la cuenta del proveedor y a cargar la factura; sin identificadores ni códigos internos.
- **FR-012**: Al confirmar un pago a proveedor sin aplicaciones, el sistema MUST avisar sin bloquear y ofrecer marcarlo como falta factura.
- **FR-013**: El aviso de la rutina 043 MUST incluir, desde el día 5 de cada mes, el resumen de facturas atrasadas del mes anterior.
- **FR-014**: El detector MUST excluir a Ganadera San Justo y no consultar ARCA ni portales externos por sí mismo.
- **FR-015**: Las acciones de marcar, descartar y fijar ciclo MUST requerir rol con permiso de escritura y quedar auditadas (usuario y fecha).

### Key Entities

- **Perfil de facturación del proveedor**: ciclo aprendido o fijado, margen, monto esperado, estado (activo / dado de baja / sin ciclo), última pregunta de baja.
- **Período esperado**: proveedor, período (desde–hasta), fecha esperada, monto esperado, estado, comprobante que lo cubre.
- **Alarma**: tipo de señal, proveedor, movimiento que la origina (pago, retención, remito), estado (abierta / descartada con motivo / convertida en marca).
- **Marca de falta factura**: pago al que se vincula, período y monto aproximados, estado (abierta / cerrada con comprobante), usuario y fechas.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un período sin factura entre dos facturas de un proveedor mensual se detecta aunque otro comprobante caiga en ese mes (caso Movistar jun-2025, hoy ya cargada); la Coop. Eléctrica bimestral no genera atrasos por mes calendario; los faltantes falsos pueden descartarse con motivo y no reaparecen.
- **SC-002**: Entre los proveedores que facturan el 80% de los meses o más, ningún período con factura cargada aparece como atrasado.
- **SC-003**: Sergio identifica qué facturas del mes faltan en menos de 1 minuto desde abrir el tablero.
- **SC-004**: Marcar y descartar alarmas no cambia ningún saldo de cuenta al centavo (antes = después).
- **SC-005**: El tablero carga con toda la historia de proveedores en menos de 3 segundos.

## Assumptions

- La fuente es WC (Compras, pagos de bancos/caja/tarjeta, retenciones, remitos de la spec 010); no se usa Access.
- "Factura compatible" para un pago: del mismo proveedor, ±60 días e importe igual o suma de hasta 3 facturas; criterio inicial ajustable en el plan.
- Los proveedores con resumen emitido por el proveedor siguen su resumen para la imputación (regla 036); el detector solo avisa faltantes de comprobantes.
- El cruce con ARCA "Mis Comprobantes" queda fuera del alcance automático; se hace a pedido y con autorización explícita cada vez.
- Proveedor = contacto con compras; los socios y cuentas particulares no se evalúan como proveedores.
