# Feature Specification: Vincular líneas de resumen de tarjeta a pagos de Impuestos

**Feature Branch**: `025-conciliacion-tarjetas-impuestos`

**Created**: 2026-09-29

**Status**: Draft

**Input**: User description: "Vincular líneas de resumen de tarjeta a pagos de Impuestos: hoy, en la pantalla de conciliación de tarjetas (008/009), el buscador 'Sumar documentos de otro proveedor' solo encuentra registros de la tabla Compras — no encuentra pagos de impuestos/tasas a organismos como AFIP, ARBA, Municipalidad, UATRE, aunque esos pagos también se hacen con tarjeta y aparecen en el resumen mensual. Verificado contra datos reales (WC, 2026-09-29): hay 1.075 registros en la tabla Impuestos con organismo asignado (AFIP 749, UATRE 153, Municipalidad de Bolivar 100, ARBA 73) que hoy son invisibles para este buscador. Causa raíz: el vínculo vive en una tabla cuya columna de documento solo apunta a Compras, sin discriminador de origen — cambio de esquema real."

## Clarifications

### Session 2026-09-29

- Q: 009 (spec existente) definía explícitamente que "una línea sin documento (impuestos, intereses, compra nunca cargada) se marca 'sin documento / no aplica'" — es decir, los impuestos estaban deliberadamente fuera del mecanismo de documentos. ¿Esta feature reemplaza esa regla para los pagos de impuestos hechos con tarjeta, o conviven ambos caminos? → A: La reemplaza para los pagos de impuestos que SÍ tienen un registro real en la tabla Impuestos (la inmensa mayoría, 1.075 casos reales) — esos ahora se vinculan como documento, igual que una Compra. "Sin documento / no aplica" sigue existiendo para los casos genuinos sin ningún registro de origen (intereses de tarjeta, compras nunca cargadas), que no cambian.
- Q: ¿Un pago de impuesto puede combinarse en la misma línea junto con documentos de Compras (reparto mixto), o son mecanismos separados que no se mezclan? → A: Sí se combinan — una línea de resumen puede agrupar, por ejemplo, un pago a un proveedor y un pago a ARBA en el mismo cargo; el reparto proporcional ya agregado (para varias Compras) debe funcionar igual mezclando Compras e Impuestos.
- Q: ¿Un pago de Impuestos puede vincularse parcialmente a una línea (como una compra grande financiada en cuotas) y dejar el resto pendiente para otra línea futura, o siempre se vincula completo a una única línea? → A: Puede ser parcial — igual que una Compra grande, un pago de Impuestos puede repartirse entre varias líneas de resumen a lo largo del tiempo. El sistema debe calcular cuánto de ese pago ya está vinculado en otras líneas (saldo pendiente) antes de ofrecerlo como candidato completo — mismo mecanismo que ya existe para Compras (`vinculosPrevios`).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Encontrar y vincular un pago de impuesto desde la conciliación de tarjeta (Priority: P1) 🎯 MVP

Un usuario concilia una línea del resumen de tarjeta que corresponde a un pago de AFIP, ARBA, la Municipalidad o UATRE hecho con esa tarjeta. Hoy el buscador "Sumar documentos de otro proveedor" no encuentra ese pago porque solo busca en Compras. El usuario necesita poder encontrarlo y vincularlo, igual que ya puede hacerlo con una factura de Compras.

**Why this priority**: Es el caso real que motiva la feature — 1.075 pagos de impuestos reales ya cargados en el sistema, invisibles hoy para este buscador, obligando a marcar esas líneas como "sin documento / no aplica" aunque sí tienen un registro real de a qué correspondieron.

**Independent Test**: Sobre una línea de resumen de tarjeta que corresponde a un pago real de AFIP/ARBA/Municipalidad/UATRE, buscar por el nombre del organismo o el número de documento en "Sumar documentos de otro proveedor", encontrarlo, vincularlo, y verificar que la línea queda conciliada (exacta o parcial, según corresponda) con ese pago de impuesto como respaldo.

**Acceptance Scenarios**:

1. **Given** una línea de resumen sin conciliar que corresponde a un pago de AFIP hecho con esa tarjeta, **When** el usuario busca "AFIP" (o el número de documento) en el buscador de documentos, **Then** el pago de impuesto real aparece entre los resultados, con la misma información que ya se muestra para un documento de Compras (fecha, tipo/descripción, importe).
2. **Given** un pago de impuesto encontrado, **When** el usuario lo agrega a la selección y confirma, **Then** la línea queda vinculada a ese pago de impuesto, con el mismo criterio de cierre exacto/parcial ya usado para Compras (tolerancia de $0,10).
3. **Given** una línea que agrupa un pago a un proveedor y un pago de impuesto en el mismo cargo, **When** el usuario selecciona un documento de Compras y un pago de Impuestos juntos, **Then** el sistema los trata igual que hoy trata varios documentos de Compras — incluido el reparto proporcional cuando lo elegido supera la línea (una o más de las partes es una cuota).
4. **Given** una línea ya vinculada a un pago de impuesto, **When** el usuario la revisa después, **Then** puede ver claramente que el respaldo es un pago de impuesto (organismo, tipo) y no una Compra — la distinción de origen nunca se pierde ni se muestra ambigua.

---

### User Story 2 - No perder lo que ya funciona para Compras (Priority: P1)

Todo lo que hoy funciona conciliando líneas contra documentos de Compras (búsqueda, sugerencias automáticas, reparto entre varios documentos, aceptar diferencia con motivo, "sin documento / no aplica") debe seguir funcionando exactamente igual después de agregar Impuestos como otro origen posible.

**Why this priority**: Es una condición de no regresión — el mecanismo de conciliación de tarjetas ya está en uso real (008/009 en producción), y esta feature se monta encima sin alterar su comportamiento actual para Compras.

**Independent Test**: Correr los escenarios ya existentes de conciliación contra Compras (documento único, varios documentos, documento en dólares con ajuste de tipo de cambio, aceptar diferencia, sin documento/no aplica) y verificar que dan exactamente el mismo resultado que antes de esta feature.

**Acceptance Scenarios**:

1. **Given** cualquier escenario de conciliación ya cubierto por 008/009 usando solo documentos de Compras, **When** se ejecuta después de esta feature, **Then** el resultado (estado, importes imputados, diferencia) es idéntico al de antes.
2. **Given** una línea marcada "sin documento / no aplica" por no tener ningún registro de origen (intereses de tarjeta, compra nunca cargada), **When** el usuario la revisa, **Then** ese camino sigue disponible sin cambios — no todo pago sin conciliar tiene necesariamente un pago de Impuestos esperando del otro lado.

---

### Edge Cases

- ¿Qué pasa si un pago de impuesto ya está parcialmente vinculado a otra línea (una "cuota" ya tomada) y el usuario intenta vincularlo de nuevo? El sistema debe mostrar cuánto queda de saldo pendiente de ese pago (importe total menos lo ya vinculado) y solo permitir imputar hasta ese saldo — igual que ya pasa hoy con una Compra grande financiada en varias cuotas.
- ¿Qué pasa si el saldo pendiente de un pago de impuesto ya vinculado llega a cero (ya se cubrió entre varias líneas)? No debe volver a aparecer como candidato en el buscador — mismo criterio que un documento de Compras ya completamente vinculado.
- ¿Qué pasa si el pago de impuesto está en la tabla Impuestos pero no tiene organismo asignado (`IdOrganismo` nulo)? No debe aparecer como candidato — no hay forma de mostrarlo de forma significativa en el buscador ("¿de quién es este pago?").
- ¿Qué pasa con un pago de impuesto que en realidad no se pagó con tarjeta (otro medio)? El buscador es manual — el usuario decide qué vincular, igual que hoy con Compras (el sistema no valida el medio de pago original del registro, solo que el importe/fecha tengan sentido). No es responsabilidad de esta feature filtrar por medio de pago, ya que Impuestos no registra esa información.
- ¿Qué pasa si se revierte un vínculo (desvincular) que era un pago de Impuestos? Debe quedar disponible de nuevo para buscarse y vincularse a otra línea, igual que un documento de Compras desvinculado.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE incluir los pagos de Impuestos con organismo asignado como resultados posibles en el buscador "Sumar documentos de otro proveedor" de la conciliación de tarjetas, buscando por nombre del organismo o número de documento — mismo criterio que ya aplica a Compras.
- **FR-002**: El sistema DEBE permitir vincular una línea de resumen de tarjeta a uno o más pagos de Impuestos, con el mismo mecanismo de cierre (exacto/parcial, tolerancia $0,10) ya usado para Compras.
- **FR-003**: El sistema DEBE permitir combinar, en la misma línea, documentos de Compras y pagos de Impuestos a la vez, incluido el reparto proporcional cuando la selección combinada supera el importe de la línea.
- **FR-004**: El sistema DEBE distinguir siempre, en cualquier vista de una línea conciliada, si su respaldo es un documento de Compras o un pago de Impuestos — nunca debe mostrarse de forma ambigua ni mezclarse la terminología (ej. "proveedor" para un organismo).
- **FR-005**: El sistema DEBE permitir vincular un pago de Impuestos a más de una línea de resumen a lo largo del tiempo cuando su importe supera el de una sola línea (mismo criterio "cuota" ya usado para una Compra grande) — pero DEBE impedir que la suma de lo vinculado en todas las líneas supere el importe real del pago de Impuestos, calculando su saldo pendiente (importe total menos lo ya vinculado en otras líneas) antes de ofrecerlo como candidato.
- **FR-006**: El sistema NUNCA DEBE mostrar como candidato un registro de Impuestos sin organismo asignado.
- **FR-007**: El sistema DEBE mantener sin cambios todo el comportamiento ya existente de conciliación contra Compras (búsqueda, sugerencias, reparto, aceptar diferencia, sin documento/no aplica) — esta feature solo agrega un origen más, no reemplaza ni modifica el existente.
- **FR-008**: El sistema DEBE permitir desvincular un pago de Impuestos de una línea con el mismo criterio ya usado para desvincular un documento de Compras, dejándolo disponible de nuevo para vincularse a otra línea.
- **FR-009**: El sistema DEBE resolver de forma consistente el caso de dos usuarios vinculando el mismo pago de Impuestos casi al mismo tiempo, de forma que la suma de ambos vínculos nunca supere el importe real del pago — el saldo pendiente se recalcula en el momento de escribir, no se confía en el que el cliente vio al abrir la pantalla (mismo criterio ya usado en 023/024).

### Key Entities *(include if feature involves data)*

- **Pago de Impuestos vinculable**: un registro de la tabla de Impuestos con organismo asignado (AFIP, ARBA, Municipalidad, UATRE u otro) — candidato para vincularse a una línea de resumen de tarjeta, con el mismo rol que hoy cumple un documento de Compras en este mecanismo.
- **Vínculo línea-documento**: se extiende para poder apuntar tanto a una Compra como a un pago de Impuestos — conceptualmente el mismo vínculo que ya existe, ahora con dos orígenes posibles en vez de uno solo.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un usuario puede encontrar y vincular un pago de impuesto real conocido (ej. un pago de AFIP) a su línea de resumen correspondiente, buscándolo por el nombre del organismo, en menos de 1 minuto.
- **SC-002**: El 100% de los escenarios de conciliación contra Compras ya cubiertos por 008/009 siguen dando el mismo resultado después de esta feature (no regresión).
- **SC-003**: En el 100% de los pagos de Impuestos vinculados (a una o varias líneas, incluso si se vincularon casi al mismo tiempo desde sesiones distintas — FR-009), la suma de lo imputado en todas sus líneas nunca supera el importe real del pago — verificable sobre el 100% de los vínculos existentes tras la feature.
- **SC-004**: De los 1.075 pagos de impuestos reales con organismo asignado (`WC`, 2026-09-29), el 100% son encontrables por el buscador cuando corresponde (organismo u número de documento coincide con lo buscado).

## Assumptions

- Solo se consideran pagos de Impuestos con `IdOrganismo` asignado — el resto no es candidato (FR-006).
- No se agrega ninguna validación de "este pago se hizo con tarjeta" — Impuestos no registra el medio de pago original, así que, igual que con Compras, es el usuario quien decide qué vincular a partir de la fecha/importe/organismo.
- El caso real motivador (AFIP/ARBA/Municipalidad/UATRE) no agota los organismos posibles — cualquier organismo con pagos registrados en Impuestos queda cubierto por el mismo mecanismo, sin necesidad de una lista cerrada.
- Se opera sobre `WC`; el cambio de esquema (discriminador de origen en la tabla de vínculos) requiere el mismo resguardo de backup verificado ya usado en 023/024.
- Esta feature no toca la pantalla ni el flujo del módulo de Impuestos en sí (carga/edición de un pago) — solo lo hace visible y vinculable desde la conciliación de tarjetas.
- La auto-sugerencia por contacto de la línea (la lista de candidatos que hoy aparece automáticamente para el proveedor ya asociado a una línea) queda fuera de alcance — esta feature solo cubre la búsqueda manual ("Sumar documentos de otro proveedor", FR-001). Una línea de tarjeta no tiene un organismo "propio" precargado como sí tiene un proveedor, así que no hay un equivalente directo de esa auto-sugerencia para Impuestos.
