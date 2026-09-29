# Feature Specification: Conciliación de Tesorería con documentos

**Feature Branch**: `026-conciliacion-tesoreria-documentos`

**Created**: 2026-09-29

**Status**: Draft

**Input**: User description: "Tenés que aplicar el mismo mecanismo de conciliación para Mercado Libre que para las tarjetas de crédito. Lo mismo que para cualquier cuenta de crédito o de débito. Siempre se van a requerir los mismos datos y ayudas para buscar qué documentos y movimientos a conciliar."

## Clarifications

### Session 2026-09-29

- Q: ¿Qué otros orígenes de documentos (además de Compras) debe poder buscar el conciliador unificado de Tesorería? → A: Compras + Impuestos + Remuneraciones + Alquileres/Arrendamientos.
- Q: ¿La conciliación manual simple actual de 023 (elegir contacto + tipear importe a mano) se mantiene disponible, o queda reemplazada por el buscador de documentos? → A: Se mantiene disponible como alternativa — el buscador es la vía principal, pero el usuario puede seguir cargando a mano cuando ya sabe el contacto/importe exacto o no hay documento real.
- Q: ¿El alcance de esta feature cubre los 6 medios de Tesorería de una sola vez, o conviene entregarlo incrementalmente empezando por Mercado Libre? → A: Los 6 medios de una vez — el mecanismo es genérico por diseño, no hay motivo técnico para tratar un medio distinto de otro.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Buscar y elegir documentos para conciliar un movimiento (Priority: P1) 🎯 MVP

Hoy, para conciliar un movimiento de Tesorería (BNA, Galicia, Mercado Libre, Efectivo, Valores propios, Valores recibidos), el usuario tiene que saber de memoria a qué contacto corresponde y tipear el importe a mano — sin ver qué documentos pendientes tiene ese contacto ni si alguno de ellos coincide con el movimiento. Con esta historia, el usuario puede buscar los documentos pendientes relacionados (por proveedor/contacto y por importe cercano) directamente desde la pantalla de conciliación, igual que ya puede hacerlo hoy en la conciliación de Tarjetas.

**Why this priority**: Es el núcleo del pedido — sin el buscador de documentos, el resto de las capacidades (sugerencias, reparto, diferencia con motivo) no tienen sobre qué operar.

**Independent Test**: Abrir la conciliación de un movimiento de Mercado Libre sin contacto reconocido, buscar documentos por proveedor, y confirmar que aparecen los documentos pendientes reales de ese proveedor con su importe y saldo pendiente.

**Acceptance Scenarios**:

1. **Given** un movimiento de Tesorería sin conciliar, **When** el usuario busca documentos por proveedor o número de documento, **Then** el sistema muestra los documentos pendientes que coinciden, con su importe y saldo pendiente.
2. **Given** un movimiento de Tesorería sin conciliar, **When** el sistema encuentra un documento (o combinación de documentos) cuyo importe coincide exacto con el movimiento, **Then** se lo ofrece como sugerencia lista para confirmar, igual que en Tarjetas.

---

### User Story 2 - Conciliar contra varios documentos con reparto automático (Priority: P1)

El usuario elige uno o más documentos para un mismo movimiento. Si el total elegido es menor al importe del movimiento, el sistema imputa el valor real de cada documento y deja el resto pendiente (mismo criterio que hoy "permite parcial" en Tarjetas). Si el total elegido es mayor (por ejemplo, varias facturas que se están pagando de a partes, como una cuota), el sistema reparte el importe del movimiento entre los documentos elegidos en proporción a su valor, en vez de pedirle al usuario que calcule el reparto a mano.

**Why this priority**: Es el caso real que motivó el pedido (3 facturas de Mercado Libre pagadas en dos movimientos) y el que hoy obliga a hacer cuentas a mano fuera del sistema.

**Independent Test**: Elegir 2-3 documentos reales de un proveedor cuyo total sea distinto al importe del movimiento y confirmar que el sistema propone el reparto correcto sin que el usuario tipee ningún importe.

**Acceptance Scenarios**:

1. **Given** un movimiento de $ 3.717,61 y tres documentos elegidos por $ 23.051,11 / $ 43.195,98 / $ 13.798,00, **When** el usuario confirma la selección, **Then** el sistema reparte los $ 3.717,61 entre los tres documentos en proporción a su importe, sin pedir que el usuario calcule los montos.
2. **Given** un movimiento cuyo importe elegido de documentos es menor al importe del movimiento, **When** el usuario confirma, **Then** el movimiento queda parcialmente conciliado y disponible para seguir agregando documentos más tarde.

---

### User Story 3 - Aceptar una diferencia con motivo explícito (Priority: P2)

Cuando el importe de los documentos elegidos no cierra exacto contra el movimiento y la diferencia no es un reparto de cuota ni un saldo pendiente legítimo (por ejemplo, un descuento no facturado por el proveedor, un impuesto retenido como Ley 25413, o una diferencia de redondeo), el usuario puede aceptar esa diferencia indicando un motivo, igual que ya puede hacerlo hoy en Tarjetas — sin tener que editar los documentos ni el importe del movimiento para forzar que cierren.

**Why this priority**: Resuelve el caso real de la diferencia por Ley 25413/descuentos de plataforma sin tener que "maquillar" documentos fiscales — es la situación que el usuario señaló que "puede ocurrir en otras oportunidades".

**Independent Test**: Elegir documentos cuyo total no cierre contra el movimiento por una diferencia chica, aceptar la diferencia con motivo "Impuesto", y confirmar que el movimiento queda conciliado con la diferencia documentada (motivo, detalle, usuario, fecha).

**Acceptance Scenarios**:

1. **Given** una diferencia entre documentos elegidos e importe del movimiento, **When** el usuario elige un motivo (o "Otro" con detalle), **Then** el movimiento queda conciliado y la diferencia aceptada queda registrada con ese motivo.
2. **Given** un movimiento sin ningún documento real que le corresponda, **When** el usuario lo marca "sin documento" con motivo, **Then** el movimiento deja de aparecer como pendiente de conciliar sin necesitar un documento inexistente.

---

### Edge Cases

- ¿Qué pasa si el usuario busca documentos y no hay ningún origen (Compras, Impuestos, u otro) que tenga algo pendiente para ese contacto/importe? El buscador debe permitir buscar manualmente por proveedor/número igual que hoy permite Tarjetas, no solo mostrar sugerencias automáticas.
- ¿Qué pasa si un movimiento ya está resuelto por otra vía (contacto ya reconocido automáticamente, o vinculado como traspaso interno por 024)? No debe ofrecerse la búsqueda de documentos — mismo criterio que ya aplican 023/024 entre sí.
- ¿Qué pasa si dos usuarios concilian el mismo movimiento a la vez? El saldo pendiente y la lista de documentos disponibles se recalculan en el momento de guardar, no se confía en lo que el cliente vio al abrir la pantalla (mismo criterio ya vigente en 023).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST permitir, para los 6 medios de Tesorería ya conciliables (bna, galicia, mercado-libre, efectivo, valores-propios, valores-recibidos), buscar documentos pendientes de Compras, Impuestos, Remuneraciones y Alquileres/Arrendamientos por proveedor/contacto y por número de documento — mismo criterio que hoy ofrece la conciliación de Tarjetas.
- **FR-002**: El sistema MUST sugerir automáticamente combinaciones de documentos cuyo importe cierra exacto (dentro de la tolerancia ya vigente) contra el movimiento a conciliar.
- **FR-003**: El sistema MUST permitir elegir uno o más documentos para un mismo movimiento y calcular, sin intervención manual del usuario, si el resultado es "cierra exacto", "queda saldo pendiente del movimiento" (menos elegido que el importe) o "pago parcial/cuota" (más elegido que el importe, con reparto proporcional entre los documentos elegidos).
- **FR-004**: El sistema MUST permitir aceptar una diferencia entre lo elegido y el importe del movimiento indicando un motivo explícito (incluido, como mínimo, "Impuesto", "Redondeo" y "Otro" con detalle) — mismo catálogo de motivos ya vigente en Tarjetas.
- **FR-005**: El sistema MUST permitir marcar un movimiento como "sin documento" con motivo, para los casos donde no corresponde ningún documento real.
- **FR-006**: El sistema MUST seguir respetando el gate simétrico ya vigente entre 023 (conciliación) y 024 (traspasos internos): un movimiento ya reconocido, conciliado, marcado sin documento o vinculado como traspaso interno no admite nuevas imputaciones. Un movimiento parcialmente conciliado MUST permitir agregar documentos o conciliaciones manuales sobre su saldo restante, pero MUST NOT ofrecerse para vincular como traspaso interno.
- **FR-007**: El sistema MUST seguir integrando toda conciliación aplicada en `vw_MovimientosCuenta_Base` (o el mecanismo equivalente de cuentas corrientes) sin romper el comportamiento ya vigente de 023.
- **FR-008**: El sistema MUST recalcular el saldo pendiente y la disponibilidad de documentos en el momento de confirmar la conciliación, no confiar en el estado que el cliente cargó al abrir la pantalla (concurrencia).
- **FR-009**: El sistema MUST mantener disponible la conciliación manual simple ya vigente (elegir contacto + tipear importe, sin buscar documentos) como alternativa al buscador, para los casos donde el usuario ya sabe el contacto/importe exacto o no hay ningún documento real que corresponda.

### Key Entities

- **Documento conciliable**: un documento pendiente de pago/cobro que puede vincularse a un movimiento de Tesorería — Compras, Impuestos, Remuneraciones y Alquileres/Arrendamientos (Clarifications 2026-09-29), buscable desde cualquiera de los 6 medios.
- **Movimiento de Tesorería**: sin cambios respecto de 023 — un registro en la tabla de origen de cada medio (BNA/Galicia/Mercado Libre/Efectivo/Valores propios/Valores recibidos).
- **Conciliación con diferencia aceptada**: extiende el registro de conciliación ya existente (023) con motivo/detalle de la diferencia aceptada, mismo criterio que Tarjetas.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un usuario puede conciliar un movimiento contra 2 o más documentos sin calcular ningún importe a mano (el sistema propone el reparto).
- **SC-002**: Al menos el 90% de los movimientos de Tesorería con un documento de importe/fecha coincidente encuentran ese documento entre las sugerencias automáticas, sin búsqueda manual.
- **SC-003**: Una diferencia entre documentos y movimiento se puede resolver (aceptar con motivo) en la misma pantalla, sin tener que editar ningún documento fiscal ni el importe del movimiento.
- **SC-004**: Los 6 medios de Tesorería ofrecen la misma experiencia de conciliación (buscador, sugerencias, reparto, diferencia con motivo) — ninguno queda con el flujo manual anterior de "elegir contacto + tipear importe" como única opción.

## Assumptions

- El módulo de cálculo puro ya existente (`conciliacion_documentos.py`, usado por Tarjetas) se reusa o generaliza para esta feature en vez de duplicar su lógica — la fórmula de reparto proporcional, tolerancia y motivos válidos no cambia.
- El esquema insert-only de 023 (`ConciliacionesTesoreria`) y su integración con `vw_MovimientosCuenta_Base` y con 024 (`esta_resuelto`) se extienden, no se reemplazan — cualquier cambio de esquema sigue el mismo criterio de backup verificado antes de aplicarse.
- La conciliación manual simple de 023 (elegir contacto + tipear importe) se mantiene disponible como alternativa al buscador, para cuando el usuario ya sabe exactamente qué contacto/importe corresponde o no hay ningún documento real que buscar (Clarifications 2026-09-29).
- El alcance cubre los 6 medios de Tesorería de una sola vez, no incremental (Clarifications 2026-09-29).

## Decisiones de implementación confirmadas — 2026-09-29

- El usuario confirmó saldo documental compartido entre Tesorería y Tarjetas; se descuenta lo imputado por ambas vías, en pesos, conservando el signo. Este saldo es de conciliación documental, no reemplaza el saldo contable histórico del contacto ni presume que conciliaciones manuales sin documento correspondan a una factura.
- El usuario confirmó incluir notas de crédito con signo negativo. Se permiten imputaciones negativas de Compras con documento; el lote debe tener total neto positivo. La vía manual sigue exigiendo importes positivos. La vista existente conserva los signos y no requiere ALTER VIEW.
- Aceptar diferencia es una elección explícita frente a continuar parcial/cuota. Se guardan las imputaciones reales del motor y la diferencia original firmada como auditoría del movimiento; no se inventan pagos ni se condona saldo de documentos. Ejemplo: movimiento 110/documentos 100 => imputar 100 y aceptar +10; movimiento 90/documentos 100 => imputar 90 y aceptar -10, quedando 10 documentales pendientes. Quitar la excepción no quita esos pagos.
- Sin documento solo está disponible sin imputaciones previas. Quitar estado conserva historia mediante EstadoQuitado y recalcula desde los pagos existentes.
