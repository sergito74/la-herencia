# Feature Specification: Traspasos internos de Tesorería

**Feature Branch**: `024-traspasos-internos-tesoreria`

**Created**: 2026-09-28

**Status**: Draft

**Input**: User description: "Nuevo módulo 'Traspasos internos de Tesorería': desde los listados de movimientos de Tesorería (mismos medios que 023-conciliacion-tesoreria), permitir vincular un movimiento con OTRO movimiento de Tesorería que representa el mismo traspaso de dinero entre cuentas propias de la empresa — por ejemplo, un 'Ingreso de dinero Cuenta Banco de Galicia' en Mercado Libre con el depósito correspondiente en Galicia. Distinto de 023-conciliacion-tesoreria: no vincula a un contacto, no genera efecto en ninguna cuenta corriente. Motivación real verificada: de 75 movimientos de Mercado Libre sin contacto reconocido, 24 son este patrón (retiro mensual de fondos de Mercado Libre hacia Galicia); el resto son pagos/cobros a terceros reales, fuera de alcance de este módulo."

## Clarifications

### Session 2026-09-28

- Q: ¿Este módulo reemplaza a la conciliación (023) para los movimientos que hoy no tienen contacto, o convive como una tercera vía de resolución? → A: Convive como una tercera vía. Un movimiento de Tesorería puede resolverse por exactamente una de tres formas: reconocido automáticamente por su origen habitual, conciliado a un contacto (023), o vinculado como traspaso interno a otro movimiento (este módulo) — nunca por más de una a la vez.
- Q: ¿El vínculo de traspaso interno debe generar algún efecto contable (cuenta corriente, saldo de caja, etc.)? → A: Ninguno. Es puramente una anotación de trazabilidad ("este dinero salió de acá y entró allá dentro de la propia empresa") — no crea ni modifica ningún saldo.
- Q: La restricción de "no vincular un movimiento ya resuelto", ¿aplica solo al movimiento que inicia la acción, o también a la contraparte elegida? → A: A ambos. Si la contraparte elegida ya está conciliada a un contacto o ya reconocida por su origen automático, el vínculo se rechaza igual que si fuera el movimiento que inició la acción — la garantía de "ningún movimiento resuelto por más de una vía" (FR-006/SC-005) se valida simétricamente en los dos lados del vínculo.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Vincular dos movimientos como un mismo traspaso interno (Priority: P1) 🎯 MVP

Un usuario revisando un listado de Tesorería (por ejemplo Mercado Libre) encuentra un movimiento sin contacto reconocido y sin conciliar que en realidad no es un pago ni un cobro a nadie — es dinero que se movió entre dos cuentas propias de la empresa (por ejemplo, un retiro de fondos de Mercado Libre depositado en la cuenta de Banco Galicia). El usuario necesita poder identificar cuál es el movimiento correspondiente del otro lado y dejarlos vinculados como el mismo traspaso, sin tener que conciliarlo contra ningún contacto.

**Why this priority**: Es el caso real y frecuente ya verificado (24 de 75 movimientos sin contacto en Mercado Libre siguen este patrón, aproximadamente uno por mes) — sin este mecanismo, esos movimientos quedan indefinidamente "sin resolver" en los listados, o se resuelven incorrectamente conciliándolos contra un contacto que no corresponde (ej. un contacto que representa al banco).

**Independent Test**: Sobre un movimiento sin resolver de un medio, buscar y elegir el movimiento correspondiente en otro medio (o el mismo), confirmar el vínculo, y verificar que ambos movimientos quedan marcados como "traspaso interno" en sus respectivos listados, sin que ninguna cuenta corriente ni saldo de caja se haya modificado.

**Acceptance Scenarios**:

1. **Given** un movimiento sin resolver, **When** el usuario busca y selecciona el movimiento correspondiente en otro medio y confirma, **Then** el sistema pide confirmación explícita antes de aplicar el vínculo.
2. **Given** que el usuario confirmó el vínculo, **When** se aplica, **Then** ambos movimientos (el de origen y el elegido) quedan visualmente marcados como "traspaso interno" en el listado de su medio, cada uno mostrando una referencia al otro.
3. **Given** un vínculo de traspaso interno ya aplicado, **When** se consulta cualquier cuenta corriente o saldo de caja relacionado con esos movimientos, **Then** no aparece ningún cambio atribuible a este vínculo — el mecanismo es puramente informativo.
4. **Given** el patrón real conocido ("Ingreso de dinero Cuenta Banco de Galicia" en Mercado Libre, con un movimiento de importe igual o muy similar y fecha cercana en Galicia), **When** el usuario abre la acción de vincular sobre uno de esos movimientos, **Then** el sistema sugiere automáticamente el o los movimientos candidatos del otro medio, para no tener que buscarlos a mano.

---

### User Story 2 - Evitar resolver un movimiento por más de una vía a la vez (Priority: P1)

Un movimiento de Tesorería no debe poder quedar vinculado como traspaso interno si ya tiene un contacto reconocido (por su origen automático o por una conciliación de 023-conciliacion-tesoreria), y viceversa: no debe poder conciliarse a un contacto si ya está vinculado como traspaso interno.

**Why this priority**: Es una condición de integridad — sin esto, un mismo movimiento podría terminar con dos resoluciones contradictorias (aparecer conciliado a un contacto Y marcado como traspaso interno al mismo tiempo), lo que confunde cualquier lectura posterior de a qué corresponde ese dinero.

**Independent Test**: Intentar vincular como traspaso interno un movimiento que ya está conciliado a un contacto (o ya reconocido por su origen automático), tanto como iniciador como elegido como contraparte, y verificar que el sistema lo rechaza en ambos casos explicando por qué; y a la inversa, intentar conciliar a un contacto un movimiento que ya está vinculado como traspaso interno.

**Acceptance Scenarios**:

1. **Given** un movimiento ya conciliado a un contacto (023) o ya reconocido por su origen automático, **When** el usuario intenta vincularlo como traspaso interno (como el que inicia la acción), **Then** el sistema lo rechaza y explica que ese movimiento ya está resuelto por otra vía.
2. **Given** un movimiento sin resolver que el usuario intenta vincular, **When** la contraparte que elige ya está conciliada a un contacto o ya reconocida por su origen automático, **Then** el sistema rechaza el vínculo igual que en el escenario 1 — la validación es simétrica, no importa de qué lado del vínculo está el movimiento ya resuelto.
3. **Given** un movimiento ya vinculado como traspaso interno, **When** el usuario intenta conciliarlo a un contacto (023), **Then** el sistema lo rechaza de la misma forma.
4. **Given** un movimiento vinculado como traspaso interno, **When** el usuario lo ve en cualquier listado de Tesorería, **Then** el sistema lo distingue visualmente de "sin resolver", "conciliado" y "ya reconocido".

---

### Edge Cases

- ¿Qué pasa si el usuario vincula dos movimientos cuyo importe no coincide exactamente (por una pequeña diferencia, ej. un gasto de transferencia bancaria descontado de un lado)? El sistema debe permitirlo — a diferencia del reparto de 023 (que exige que la suma cierre contra el total), acá no hay un importe a repartir; el vínculo es entre dos movimientos completos, sea cual sea la diferencia entre ambos importes. El usuario es quien decide si dos movimientos corresponden al mismo traspaso.
- ¿Qué pasa si el usuario intenta vincular un movimiento consigo mismo? Debe rechazarse.
- ¿Qué pasa si el usuario intenta vincular un movimiento que ya está vinculado a otro (un tercer movimiento)? Debe rechazarse — cada movimiento admite un único vínculo de traspaso interno a la vez, salvo que se deshaga el vínculo anterior primero.
- ¿Qué pasa si el usuario quiere deshacer un vínculo aplicado por error? Debe poder deshacerse, dejando ambos movimientos otra vez como "sin resolver", con registro de quién y cuándo lo deshizo (mismo criterio de auditoría que el resto del sistema financiero).
- ¿Qué pasa si dos usuarios intentan vincular el mismo movimiento a la vez (a destinos distintos)? Debe aplicarse solo un vínculo consistente; el segundo intento debe ver el estado ya actualizado, no crear un vínculo contradictorio.
- ¿Qué pasa con Tarjetas? Igual que en 023-conciliacion-tesoreria, queda fuera de alcance de este módulo — Tarjetas se resuelve exclusivamente por su propio flujo (008/009).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE permitir, desde el listado de movimientos de cada medio de Tesorería cubierto (Banco Nación, Galicia, Mercado Libre, Efectivo, Valores propios, Valores recibidos), iniciar el vínculo de un movimiento sin resolver con otro movimiento de Tesorería (del mismo medio o de otro).
- **FR-002**: El sistema DEBE excluir explícitamente a Tarjetas de este módulo, igual que en 023-conciliacion-tesoreria.
- **FR-003**: El sistema DEBE requerir una confirmación explícita del usuario antes de aplicar cualquier vínculo de traspaso interno.
- **FR-004**: El sistema NUNCA DEBE generar ni modificar ningún saldo de cuenta corriente, caja o cuenta bancaria como consecuencia de un vínculo de traspaso interno — es exclusivamente informativo/de trazabilidad.
- **FR-005**: El sistema DEBE sugerir automáticamente movimientos candidatos para vincular, priorizando los que tengan importe igual o muy similar y fecha cercana en otro medio, para los movimientos que calcen con patrones ya conocidos (ej. "Ingreso de dinero Cuenta Banco de Galicia").
- **FR-006**: El sistema DEBE impedir vincular como traspaso interno un movimiento que ya está resuelto por otra vía (ya reconocido por su origen automático, o conciliado a un contacto por 023-conciliacion-tesoreria) — esta validación se aplica simétricamente tanto al movimiento que inicia la acción como a la contraparte elegida; si cualquiera de los dos ya está resuelto, el vínculo se rechaza.
- **FR-007**: El sistema DEBE impedir conciliar a un contacto (023) un movimiento que ya está vinculado como traspaso interno.
- **FR-008**: El sistema DEBE impedir que un movimiento tenga más de un vínculo de traspaso interno activo a la vez.
- **FR-009**: El sistema DEBE rechazar el intento de vincular un movimiento consigo mismo.
- **FR-010**: El sistema DEBE permitir deshacer un vínculo ya aplicado, dejando ambos movimientos nuevamente "sin resolver", con un registro de auditoría de quién y cuándo lo deshizo.
- **FR-011**: El sistema DEBE distinguir visualmente, en cada listado de Tesorería cubierto, los movimientos vinculados como traspaso interno de los demás estados posibles (sin resolver, conciliado, ya reconocido).
- **FR-012**: El sistema DEBE resolver de forma consistente el caso de dos usuarios vinculando el mismo movimiento a la vez, de forma que se aplique un solo vínculo y el segundo intento vea el estado ya actualizado.
- **FR-013**: El sistema DEBE conservar un registro de auditoría de cada vínculo aplicado y de cada uno deshecho (los dos movimientos involucrados, quién y cuándo).

### Key Entities *(include if feature involves data)*

- **Movimiento sin resolver**: un movimiento de Tesorería que no está reconocido por su origen automático habitual, no está conciliado a un contacto (023), y no está vinculado como traspaso interno — candidato para cualquiera de las tres vías de resolución.
- **Traspaso interno**: el vínculo entre dos movimientos de Tesorería (de cualquier medio cubierto, incluso el mismo) que representan el mismo movimiento de dinero entre cuentas propias de la empresa. No tiene importe propio ni genera ningún efecto contable — es una anotación de trazabilidad entre dos movimientos ya existentes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un usuario puede vincular dos movimientos como el mismo traspaso interno, desde que identifica el primero hasta que ambos quedan marcados, en menos de 1 minuto.
- **SC-002**: Para el patrón ya conocido ("Ingreso de dinero Cuenta Banco de Galicia" en Mercado Libre y su contraparte en Galicia), el sistema sugiere automáticamente el candidato correcto en al menos el 90% de los casos históricos reales.
- **SC-003**: Ningún vínculo de traspaso interno, aplicado o deshecho, modifica jamás un saldo de cuenta corriente, caja o cuenta bancaria — verificable comparando saldos antes y después de cualquier vínculo.
- **SC-004**: El 100% de los vínculos aplicados y deshechos quedan con un registro consultable de ambos movimientos, quién y cuándo — verificable en cualquier auditoría posterior.
- **SC-005**: Ningún movimiento puede terminar resuelto por más de una vía a la vez (reconocido automáticamente, conciliado a un contacto, y vinculado como traspaso interno son mutuamente excluyentes) — verificable sobre el 100% de los movimientos de los medios cubiertos.

## Assumptions

- Los medios cubiertos son los mismos 6 de 023-conciliacion-tesoreria (Banco Nación, Galicia, Mercado Libre, Efectivo, Valores propios, Valores recibidos); Tarjetas queda fuera en ambos módulos por el mismo motivo (flujo propio ya existente, 008/009).
- El vínculo es siempre entre exactamente dos movimientos (un traspaso interno "de a dos") — no se contempla en el lanzamiento inicial un traspaso repartido entre más de dos movimientos (a diferencia del reparto entre varios contactos de 023, que sí lo permite porque ahí el importe se divide; acá no hay importe que dividir).
- No se exige que los importes de ambos movimientos coincidan exactamente — el usuario es quien decide si dos movimientos corresponden al mismo traspaso, con la sugerencia automática (FR-005) como ayuda, no como validación bloqueante.
- Cualquier usuario autenticado con permisos de escritura puede vincular y deshacer traspasos internos, con el mismo criterio de roles ya usado en el resto del sistema.
- Se opera sobre la base de datos de trabajo (`WC`); todo cambio de esquema que este módulo requiera sigue el mismo resguardo (backup verificado previo) ya usado en 023-conciliacion-tesoreria.
