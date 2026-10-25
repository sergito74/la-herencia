# Feature Specification: Impuestos particulares (a cargo de socio)

**Feature Branch**: `041-impuestos-particulares`

**Created**: 2026-10-25

**Status**: Draft

**Input**: User description: "Poder marcar un impuesto pagado por Giamigli de Bolívar S.A. como gasto a cargo de un socio (Sergio, Lucy, Ceci) o del Condominio LSC, igual que la compra particular, para que deje de contar como costo de Giamigli." Diseño consultado con los agentes 07 (dirección financiera) y administracion-cuentas (25/10/2026).

## Clarifications

### Session 2026-10-25

- Q: ¿Padrón de partidas con titular para avisar solo? → A: B — marca manual con partida; el padrón se arma con esas marcas y avisa en impuestos nuevos de la misma partida.
- Q: ¿A quién se cargan los impuestos de partidas a nombre de Oscar Vicente? → A: Siempre al Condominio LSC; Oscar no es titular aparte.
- Q: Si un socio no devuelve un impuesto cargado, ¿qué hace el sistema? → A: Queda como deuda en su cuenta; se cancela con devolución o con un asiento de compensación explícito (nunca automático).

## Contexto

- Las **compras** ya tienen el mecanismo de compra particular: el gasto de un socio pagado por la empresa sale de los costos de Giamigli y queda como Debe en la cuenta del socio. Los **impuestos** no tienen equivalente.
- **Caso real:** impuesto 3206, ARBA Inmobiliario Complementario cuota 3/2017, **$8.852,10**, pagado por Giamigli desde el BNA el 07/11/2017. Es del **Condominio LSC** (lo pagan los tres socios; Sergio, 25/10/2026). Lucy lo devolvió el 13/11/2017 (BNA 18537, ya en el contacto del Condominio). Hoy el impuesto sigue contando como costo de Giamigli; el 25/10 se cargó a mano un Debe y un Haber en la cuenta del Condominio para no perder el efecto.
- La cuenta de socio es la cuenta oficial de cada socio; el contacto del socio solo marca de quién es un movimiento de banco.
- Los impuestos no registran partida ni titular. Potencialmente afectados: 60 Inmobiliario (≈ $13 M) y 99 Tasa Vial (≈ $14,7 M), que podrían incluir partidas de socios, de Oscar Vicente o del Condominio.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cargar un impuesto a un socio (Priority: P1)

En la ficha de un impuesto ya pagado, el usuario indica que es a cargo de un socio o del Condominio, por el total o por una parte, con un motivo. El sistema lo deja como Debe de ese socio y lo saca de los costos de Giamigli.

**Why this priority**: es el objetivo de la funcionalidad y resuelve el caso del complementario 2017.

**Independent Test**: cargar el impuesto 3206 al Condominio por $8.852,10 y verificar que su cuenta de socio tiene un Debe de $8.852,10 al 07/11/2017 vinculado al impuesto, y que el impuesto ya no figura como costo de Giamigli.

**Acceptance Scenarios**:

1. **Given** un impuesto pagado, **When** se lo carga al Condominio por el total, **Then** la cuenta del Condominio muestra un Debe por ese importe a la fecha del impuesto, valuado en US$/kg con la regla vigente, y con enlace al impuesto.
2. **Given** un impuesto de $10.000, **When** se cargan $6.000 a un socio, **Then** solo $6.000 salen de los costos de Giamigli y $4.000 siguen como gasto de la empresa.
3. **Given** un impuesto ya cargado totalmente, **When** se intenta cargarlo otra vez, **Then** se rechaza porque la suma superaría el importe.
4. **Given** una cuenta de socio cerrada, **When** se intenta cargarle un impuesto, **Then** se avisa que la cuenta está cerrada y no se carga sin confirmación explícita.
5. **Given** un impuesto con un Debe manual equivalente ya cargado en la cuenta del socio (como el 3206), **When** se lo carga con el nuevo mecanismo, **Then** el sistema avisa la doble carga y propone reemplazar el asiento manual por el vinculado, conservando el historial.

---

### User Story 2 - Ver qué impuestos son de socios y si se devolvieron (Priority: P1)

En la lista de impuestos se distingue cuáles están a cargo de un socio, a quién, por cuánto y si el socio ya lo devolvió.

**Why this priority**: sin esto la carga no se puede controlar.

**Independent Test**: el 3206 figura con la etiqueta "A cargo de Condominio LSC — devuelto".

**Acceptance Scenarios**:

1. **Given** impuestos cargados a socios, **When** se abre la lista, **Then** cada uno muestra la etiqueta con el socio y el importe, y se puede filtrar por "a cargo de socio".
2. **Given** un impuesto a cargo de un socio, **When** existe en la cuenta del socio un Haber que lo cancela (devolución), **Then** el estado es "devuelto"; si no, "pendiente".

---

### User Story 3 - Anular una carga a socio (Priority: P2)

Una carga mal hecha se anula con motivo; vuelve a ser costo de Giamigli y el Debe del socio queda anulado en el historial.

**Independent Test**: anular la carga del 3206 y verificar que la cuenta del Condominio pierde el Debe (queda visible como anulado) y el impuesto vuelve a costos.

**Acceptance Scenarios**:

1. **Given** una carga vigente, **When** se anula con motivo, **Then** el Debe del socio queda anulado con usuario, fecha y motivo, y el impuesto vuelve a contar como costo.
2. **Given** un impuesto con carga a socio vigente, **When** se intenta dar de baja la boleta, **Then** se rechaza hasta anular la carga.

### Edge Cases

- Un pago bancario que cubre varias boletas, algunas de Giamigli y otras de un socio: la marca va por boleta, no por pago.
- Devolución parcial o en varias veces: el estado muestra lo devuelto y el saldo pendiente.
- El socio pagó una boleta de Giamigli (caso inverso): fuera de alcance; se resuelve con un asiento de Haber en la cuenta del socio, como hoy.
- Impuesto sin pago vinculado: se puede cargar igual; la carga no depende del medio de pago.
- Impuestos históricos en dólares: no aplica (los impuestos se registran en pesos).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE permitir cargar un impuesto a la cuenta de un socio (Sergio, Lucy, Ceci o Condominio LSC), por el total o por un importe parcial (o porcentaje), con motivo obligatorio y partida inmobiliaria opcional.
- **FR-002**: Cada carga DEBE generar un único Debe en la cuenta del socio, con la fecha del impuesto, valuado con la regla vigente de cuentas de socios (antes del 16/03/2020: 100% US$; después: 50% US$ y 50% kg de novillo INMAG), y enlazado al impuesto.
- **FR-003**: La suma de las cargas vigentes de un impuesto NO DEBE superar su importe; un impuesto puede tener cargas a distintos socios.
- **FR-004**: El Condominio LSC DEBE tratarse como un único socio; el sistema no reparte internamente entre condóminos. Las partidas a nombre de Oscar Vicente se asignan siempre al Condominio LSC (no existe titular «Oscar»).
- **FR-005**: La boleta, su pago y la cuenta corriente del organismo NO DEBEN cambiar: el organismo sigue viendo la deuda y el pago completos.
- **FR-006**: La parte cargada a socios DEBE excluirse de los costos de Giamigli: en el flujo de caja por rubro la salida se mantiene pero se clasifica como "Cuenta de socios" (no "Impuestos"); la revisión de cuentas lo muestra como "cargado a socio"; el libro de impuestos lo conserva con la etiqueta "a cargo de socio".
- **FR-007**: La lista de impuestos DEBE mostrar la etiqueta del socio y el importe cargado, permitir filtrar por "a cargo de socio" y mostrar el estado devuelto/pendiente según los Haber de la cuenta del socio que lo cancelan. Lo no devuelto queda como deuda del socio; solo se cancela con una devolución o con un asiento de compensación explícito cargado por el usuario, nunca de forma automática.
- **FR-008**: La anulación DEBE ser no destructiva: el Debe queda anulado con usuario, fecha y motivo, y el impuesto vuelve a costos.
- **FR-009**: NO DEBE poder darse de baja un impuesto con cargas vigentes.
- **FR-010**: El sistema DEBE avisar antes de cargar a una cuenta de socio cerrada y exigir confirmación explícita.
- **FR-011**: El sistema DEBE detectar un Debe manual equivalente (mismo socio, importe y fecha cercana) y ofrecer reemplazarlo por el vinculado, sin duplicar.
- **FR-012**: Usuarios de solo lectura DEBEN poder consultar sin poder cargar ni anular; toda carga y anulación queda auditada.
- **FR-013**: Toda escritura DEBE ir solo a la base de trabajo, con respaldo verificado antes de cambios de esquema o de carga en lote.
- **FR-015**: Cada carga con partida (inmobiliaria, patente o tasa) DEBE alimentar un padrón partida → titular (socio o Condominio). Al cargar un impuesto nuevo de una partida del padrón, el sistema DEBE avisar y proponer la carga al mismo titular; la decisión sigue siendo del usuario.
- **FR-014**: El caso 3206 DEBE migrarse al mecanismo nuevo: el Debe manual del 25/10/2026 se reemplaza por la carga vinculada; el Haber de la devolución de Lucy se conserva.

### Key Entities

- **Carga de impuesto a socio**: impuesto, socio, importe, motivo, partida inmobiliaria (opcional), Debe generado en la cuenta del socio, estado (vigente/anulada), usuario y fechas.
- **Impuesto** (existente): organismo, tipo, período, importe, pago; gana el estado derivado "a cargo de socio" (total/parcial) y devuelto/pendiente.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El impuesto 3206 queda a cargo del Condominio por $8.852,10, con estado "devuelto", y deja de figurar como costo de Giamigli; la cuenta del Condominio no tiene un Debe duplicado.
- **SC-002**: La cuenta corriente de ARBA y su conciliación no cambian (mismo saldo antes y después).
- **SC-003**: Cargar un impuesto a un socio lleva menos de 1 minuto desde la ficha del impuesto.
- **SC-004**: El 100% de los impuestos a cargo de socios se identifican en la lista con su socio y estado.

## Assumptions

- La regla de valuación y el signo de la cuenta de socio son los vigentes (Tipo da el signo, magnitudes positivas).
- El resultado por campaña hoy no incluye impuestos; si en el futuro se incorporan, se excluye la parte cargada a socios.
- La devolución del socio se sigue registrando como Haber en su cuenta (por banco o caja), como hoy; esta funcionalidad no crea cobros.
- Implicancia fiscal (gasto no deducible para la S.A.) se informa al estudio contable; el sistema no calcula impuestos.
- Fuera de alcance: carga inicial masiva del padrón y marcado automático sin confirmación; el caso inverso (socio que paga impuestos de Giamigli).
