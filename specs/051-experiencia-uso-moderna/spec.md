# Feature Specification: Experiencia de uso moderna

**Feature Branch**: `main` (sin rama propia; push a main autorizado)
**Created**: 2026-11-18
**Status**: Draft
**Input**: Recomendación del especialista 12 (diseño visual de frontend) del 18/11/2026, aprobada por Sergio: Inicio "Para hacer hoy", selector de fechas con atajos de campaña, filas clicables con panel lateral de detalle y búsqueda global Ctrl+K.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Inicio "Para hacer hoy" (Priority: P1)

Sergio abre el sistema y, sin buscar en los menús, ve qué tiene pendiente hoy, con la cantidad y el importe de cada cosa. Un clic lo lleva a la pantalla donde se resuelve. Debajo ve cómo está la empresa: disponible en bancos, deuda con proveedores, stock valuado, cajas, flujo de los últimos meses y campaña actual.

**Why this priority**: es la primera pantalla de cada día. Hoy muestra tarjetas que repiten el menú, indicadores en 0 y un "Deuda total…" que no termina de cargar.

**Independent Test**: abrir Inicio con datos reales y comprobar que cada pendiente coincide con su pantalla de origen y que el enlace lleva a donde se resuelve.

**Acceptance Scenarios**:

1. **Given** hay movimientos de banco sin conciliar, **When** se abre Inicio, **Then** aparece "N movimientos de banco sin conciliar", con la misma cantidad que Tesorería, y el enlace abre Tesorería.
2. **Given** no hay ningún pendiente, **When** se abre Inicio, **Then** se ve "Todo al día" en lugar de la lista.
3. **Given** un indicador todavía se está calculando, **When** se abre Inicio, **Then** se muestra un esqueleto de carga, nunca un texto cortado ni un 0 falso.
4. **Given** una fuente de pendientes falla, **When** se abre Inicio, **Then** el resto se muestra igual y esa línea dice "no se pudo calcular".

---

### User Story 2 - Fechas con atajos de campaña (Priority: P2)

Al filtrar por fecha, Sergio elige "Campaña actual", "Mes pasado" u otro atajo con un clic, en lugar de escribir dos fechas.

**Why this priority**: se usa en casi todos los listados, y el campo de fecha nativo no conoce las campañas (1/7 al 30/6).

**Independent Test**: en Tesorería, elegir "Campaña actual" filtra del 01/07 del año de inicio al 30/06 siguiente; "Mes pasado" filtra el mes calendario anterior.

**Acceptance Scenarios**:

1. **Given** el filtro de fechas de un listado, **When** se elige un atajo, **Then** el listado se filtra al rango correspondiente y el selector muestra el nombre del atajo.
2. **Given** se elige "Rango libre", **When** se cargan desde y hasta, **Then** el listado se filtra a ese rango y el selector muestra las dos fechas en formato dd/mm/aaaa.
3. **Given** un filtro activo, **When** se elige "Sin filtro", **Then** el listado vuelve a mostrar todo.

---

### User Story 3 - Detalle en panel lateral (Priority: P3)

En los listados, Sergio hace clic en una fila y ve el detalle en un panel a la derecha, sin perder el listado ni el filtro. Las acciones de esa fila están en un menú.

**Why this priority**: hoy cada "Ver detalle", "Editar" o "Abrir" lleva a otra página, y al volver se pierde el contexto.

**Independent Test**: en Compras, filtrar, hacer clic en una fila, ver el detalle, cerrar con Esc y comprobar que el filtro y la posición siguen iguales.

**Acceptance Scenarios**:

1. **Given** un listado filtrado, **When** se hace clic en una fila, **Then** se abre el panel con el detalle de ese registro y el listado queda visible detrás.
2. **Given** el panel abierto, **When** se presiona Esc o la cruz, **Then** el panel se cierra y el listado conserva el filtro, la página y la posición.
3. **Given** una fila, **When** se abre su menú de acciones, **Then** aparecen las acciones que antes eran links sueltos (abrir completo, editar, etc.).

---

### User Story 4 - Búsqueda global Ctrl+K (Priority: P4)

Desde cualquier pantalla, Sergio aprieta Ctrl+K, escribe parte de un nombre o número y llega al contacto, a la compra, al producto, al lote, a la orden o a la pantalla, sin pasar por los menús. También puede ejecutar acciones frecuentes.

**Why this priority**: es lo que más tiempo ahorra a quien usa el sistema todos los días. Depende de que las pantallas de destino ya existan.

**Independent Test**: Ctrl+K, escribir "baya" muestra el contacto Bayá Casal y sus compras recientes; Enter abre su cuenta corriente.

**Acceptance Scenarios**:

1. **Given** cualquier pantalla, **When** se presiona Ctrl+K, **Then** se abre la búsqueda con el cursor listo para escribir.
2. **Given** se escribieron al menos 2 caracteres, **When** hay coincidencias, **Then** se agrupan por tipo (Contactos, Compras, Productos, Lotes, Órdenes, Pantallas, Acciones) y se navega con flechas y Enter.
3. **Given** se elige la acción "Nueva compra", **When** se presiona Enter, **Then** se abre la pantalla de alta de compra.

---

### Edge Cases

- **Usuario de solo lectura:** en Inicio y en Ctrl+K no ve las acciones de alta (nueva compra, leer planilla).
- **Pantalla angosta:** el panel lateral ocupa todo el ancho y la lista de pendientes pasa a una columna.
- **Búsqueda sin resultados:** dice "Sin resultados" y sugiere las pantallas más usadas.
- **Pendientes con importe en dólares:** se muestran en us$ y no se suman a pesos.
- **Campaña actual a principios de julio:** el atajo cambia a la campaña nueva el 1 de julio.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Inicio MUST mostrar una lista "Para hacer hoy" con cada pendiente que tenga al menos un caso, cada uno con su cantidad, su importe si corresponde y un enlace a la pantalla donde se resuelve:
  - movimientos de banco sin conciliar;
  - facturas esperadas;
  - órdenes de la planilla de Matías para corregir;
  - productos usados con costo pendiente;
  - portales con error;
  - trabajos eventuales sin pagar;
  - facturas de compra que vencen en los próximos 7 días;
  - avisos del control de integridad de costos.
- **FR-002**: Las cantidades e importes de Inicio MUST ser los mismos que muestra la pantalla de origen; no se recalculan con otro criterio.
- **FR-003**: Inicio MUST mostrar "Todo al día" cuando no hay pendientes.
- **FR-004**: Inicio MUST mostrar 4 indicadores: disponible en bancos (último saldo de cada cuenta), deuda con proveedores en pesos y us$, stock valuado y saldo de las cajas.
- **FR-005**: Inicio MUST mostrar el neto del flujo de caja de los últimos 6 meses en barras chicas, con enlace a Flujo de caja.
- **FR-006**: Inicio MUST mostrar la campaña actual (cultivos con su superficie y las últimas órdenes) y accesos rápidos: nueva compra, nueva orden, movimiento de caja, trabajo eventual y leer la planilla de Matías. Los accesos de alta se ocultan para el rol de solo lectura.
- **FR-007**: Inicio MUST dejar de mostrar las tarjetas que repiten el menú.
- **FR-008**: El selector de fechas MUST ofrecer estos atajos: este mes, mes pasado, últimos 90 días, campaña actual (1/7 al 30/6), campaña anterior, año calendario, rango libre y sin filtro.
- **FR-009**: El selector de fechas MUST reemplazar los pares de fechas sueltos en Tesorería, Cuentas corrientes, Compras, Flujo de caja y Trabajos eventuales, sin cambiar qué filtra cada pantalla.
- **FR-010**: Los listados de Compras, Ventas de hacienda, Trabajos eventuales, Saldos y Órdenes MUST abrir el detalle en un panel lateral al hacer clic en la fila, conservando el filtro, la página y la posición.
- **FR-011**: El panel MUST cerrarse con Esc o con su botón de cierre, y MUST tener un acceso a la pantalla completa del registro.
- **FR-012**: Las acciones de fila que hoy son links sueltos MUST pasar a un menú de acciones de la fila.
- **FR-013**: Ctrl+K (o Cmd+K) MUST abrir una búsqueda global desde cualquier pantalla. Busca contactos, compras por número, productos, lotes, órdenes y pantallas, y ofrece acciones: nueva compra, nueva orden y leer la planilla de Matías.
- **FR-014**: La búsqueda MUST navegarse solo con teclado (flechas, Enter, Esc) y agrupar los resultados por tipo.
- **FR-015**: Todo el texto MUST estar en castellano rioplatense, sin códigos internos, y con los números en formato argentino (1.234,56; $ / us$).
- **FR-016**: Ninguna de estas funciones MUST modificar datos ni reglas de negocio. Solo leen y navegan.

### Key Entities

- **Pendiente**: tipo, cantidad, importe opcional (con su moneda), pantalla de destino y estado del cálculo (listo, calculando o error).
- **Indicador**: nombre, valor, moneda y fecha de referencia.
- **Resultado de búsqueda**: tipo, título, subtítulo y destino o acción.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Desde Inicio se llega a cualquier pendiente del día en un clic.
- **SC-002**: El 100% de las cantidades de "Para hacer hoy" coincide con su pantalla de origen en la prueba con datos reales.
- **SC-003**: Inicio muestra su contenido en menos de 3 segundos, y nunca muestra cifras cortadas ni ceros falsos mientras calcula.
- **SC-004**: Filtrar un listado por la campaña actual lleva 2 clics; hoy implica escribir 2 fechas.
- **SC-005**: Abrir y cerrar el detalle de un registro no cambia el filtro ni la posición del listado en ninguna de las 5 pantallas.
- **SC-006**: Desde cualquier pantalla se llega a un contacto o a una compra por número en menos de 5 segundos con Ctrl+K.

## Assumptions

- **Fuentes de datos:** los pendientes y los indicadores salen de cálculos que el sistema ya hace (Tesorería, facturas esperadas, planilla de Matías, stock, bóveda, trabajos eventuales, vencimientos de compras, control de integridad, saldos, cajas, flujo de caja). Si alguno no tiene un endpoint de lectura liviano, se agrega uno de solo lectura.
- **Panel lateral:** reutiliza las vistas de detalle que ya existen. Las altas y ediciones complejas siguen abriendo la pantalla completa desde el panel.
- **Búsqueda:** usa los buscadores que ya existen por entidad. Las pantallas y acciones son una lista fija.
- **Fuera de alcance:** edición en línea en tablas, vistas guardadas con nombre y modo oscuro.
