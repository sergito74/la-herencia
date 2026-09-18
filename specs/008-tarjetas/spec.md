# Feature Specification: Tarjetas de Crédito

**Feature Branch**: `008-tarjetas`

**Created**: 2026-09-18

**Status**: Draft

**Input**: User description: "Módulo Tarjetas (008-tarjetas): migración del módulo de tarjetas de crédito de Access a la web app, escribiendo exclusivamente contra la DB de trabajo `WC`. Alcance: catálogo de tarjetas (solo lectura), cuenta corriente por tarjeta (resolviendo el origen 'Tarjetas' hoy fuera de alcance en Cuentas Corrientes), compras en cuotas con tarjeta (con generación automática de cuotas), y resúmenes de tarjeta con sus líneas de consumo. Fuera de alcance: conciliación automática línea↔cuota y distribución de una línea entre varios contactos — ambas features del esquema real tienen 0 filas en producción, nunca se usaron."

## Clarifications

### Session 2026-09-18

- Q: Cuando se edita una compra en cuotas cambiando el importe total o la cantidad de cuotas, y algunas cuotas ya están marcadas como cobradas, ¿qué debe hacer el sistema con el cronograma existente? → A: Regenerar todo el cronograma (mismo criterio de PUT que Compras/Ventas — reemplaza todo); si alguna cuota ya estaba cobrada, ese estado se pierde y hay que volver a marcarla.
- Q: El listado de compras en cuotas (FR-006), ¿debe mostrar todo por defecto o quedar vacío hasta aplicar un filtro, como ya hacen Resúmenes/Compras/Ventas/Contactos? → A: Vacío hasta aplicar al menos un filtro, mismo criterio que el resto de los listados ya migrados.

### Session 2026-09-19 (feedback post-implementación, con Excel reales del usuario)

- Q: Con evidencia real (las 18 compras en cuotas de `[Tarjetas de Credito]` no tienen ninguna posterior a diciembre 2015, mientras AgroNacion sigue financiando en cuotas hoy mediante líneas repetidas dentro del resumen mensual con `CreditoContingente`/`InteresPagoDiferido` por línea) → A: Historia 3 (compras en cuotas) pasa a ser **solo lectura** — catálogo histórico de referencia, sin alta/edición/eliminación/lock. FR-004/FR-005/FR-007/FR-007a quedan sin efecto (nunca se vuelve a escribir en `[Tarjetas de Credito]`/`[Cuotas Tarjetas de Credito]`).
- Q: ¿Cómo se vincula una línea de consumo con la(s) factura(s)/NC/ND real(es) que la documentan? → A: Vínculo a Compras reales (`Compras.IdDeuda`), permitiendo varias por línea (más de un proveedor, o el pago parcial de una compra en cuotas) — nueva tabla `Tarjetas_Resumenes_Lineas_Compras`.
- Q: ¿Cómo se registran los pagos de un resumen para que la cuenta corriente de la tarjeta los muestre? → A: Se buscan candidatos reales en `Movimientos BNA`/`Movimientos Galicia` filtrando por el `IdContacto` de esa tarjeta (ya viene cargado así en los datos reales, sin necesidad de adivinar por fecha/importe) y se confirman como pago de un resumen — nueva tabla `Tarjetas_Resumenes_Pagos`. FR-002 pasa a incluir estos pagos como movimientos de crédito.
- Q: Mastercard BNA fue dada de baja y reemplazada por Corporativa Nacion → A: `Tarjetas.Activa` corregido a `false` para Mastercard BNA (dato de negocio, no de esquema).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Consultar resúmenes de tarjeta y sus consumos (Priority: P1)

Un usuario administrativo necesita revisar los resúmenes de tarjeta de crédito ya cargados (293 resúmenes reales, 1694 líneas de consumo) para verificar cargos, impuestos y el detalle de compras de un período, y cargar los resúmenes nuevos a medida que llegan del banco.

**Why this priority**: Es el subdominio con mayor volumen de uso real del módulo — la funcionalidad que la operación diaria más necesita, y la que hoy no tiene ningún equivalente web.

**Independent Test**: Buscar los resúmenes de una tarjeta real por rango de fechas, abrir uno y verificar que sus líneas de consumo y cargos coinciden con los datos reales en `WC`. Cargar un resumen nuevo (cabecera + líneas) y confirmar que queda guardado solo en `WC`.

**Acceptance Scenarios**:

1. **Given** una tarjeta con resúmenes cargados, **When** el usuario busca por tarjeta y rango de fechas de cierre, **Then** ve los resúmenes que coinciden, con su fecha de cierre/vencimiento y total de cargos.
2. **Given** un resumen existente, **When** el usuario lo abre, **Then** ve la cabecera completa de cargos/impuestos y la lista de líneas de consumo (fecha, detalle, importe, contacto y documento si están cargados).
3. **Given** un resumen sin líneas de consumo (solo cabecera, ej. un resumen sin movimientos en el período), **When** el usuario lo abre, **Then** el sistema lo muestra igual, sin exigir al menos una línea.
4. **Given** los datos de un resumen nuevo (tarjeta, código, fechas, cargos, líneas de consumo), **When** el usuario lo guarda, **Then** el sistema lo persiste en `WC` y lo muestra en el listado.

---

### User Story 2 - Ver la cuenta corriente de una tarjeta (Priority: P2)

Un usuario necesita ver los movimientos y el saldo acumulado de una tarjeta específica, de la misma forma que ya puede hacerlo con cualquier otra cuenta corriente del sistema (proveedores, contactos), y poder navegar desde un movimiento de tarjeta en Cuentas Corrientes hacia el resumen que lo originó.

**Why this priority**: Resuelve una laguna concreta y ya identificada: los movimientos de tarjeta no aparecen hoy en ninguna cuenta corriente del sistema (research.md) — esta historia los incorpora por primera vez.

**Independent Test**: Abrir la cuenta corriente de una tarjeta real y verificar que el saldo acumulado final coincide con la suma de los totales de sus resúmenes reales en `WC`; hacer clic en un movimiento de origen "Tarjetas" desde Cuentas Corrientes y verificar que lleva al resumen correspondiente en vez de mostrar "sin detalle disponible".

**Acceptance Scenarios**:

1. **Given** una tarjeta con resúmenes cargados, **When** el usuario abre su cuenta corriente, **Then** ve un movimiento por resumen, ordenados cronológicamente, con el saldo acumulado por movimiento (mismo criterio que Cuentas Corrientes, 004).
2. **Given** un movimiento de cuenta corriente cuyo origen es un resumen de tarjeta, **When** el usuario hace clic en él, **Then** navega al resumen correspondiente.
3. **Given** una compra en cuotas cuyas cuotas ya están incluidas en resúmenes cargados, **When** el usuario revisa la cuenta corriente de la tarjeta, **Then** no ve un movimiento separado por cada cuota — su importe ya forma parte del total del resumen que la contiene, evitando contar la misma deuda dos veces.

---

### User Story 3 - Cargar una compra en cuotas (Priority: P3)

Un usuario necesita registrar una compra financiada en cuotas (fecha, contacto, comprobante, cantidad de cuotas) y que el sistema genere automáticamente el cronograma de cuotas, tal como lo hace hoy el formulario Access. La compra en cuotas no se vincula a una tarjeta específica del catálogo — el esquema real nunca las relacionó (research.md).

**Why this priority**: Es un flujo de alta activo (18 compras / 183 cuotas reales) pero de menor volumen que los resúmenes, y no bloquea a las otras dos historias.

**Independent Test**: Cargar una compra en 6 cuotas con un importe total conocido y verificar que se generan 6 cuotas mensuales con las fechas e importes esperados (redondeando la diferencia de centavos en la última cuota), y que se pueden marcar como cobradas/no cobradas.

**Acceptance Scenarios**:

1. **Given** los datos de una compra en cuotas (fecha, contacto, comprobante, importe total, cantidad de cuotas), **When** el usuario la guarda, **Then** el sistema genera automáticamente esa cantidad de cuotas con fecha de vencimiento mensual sucesiva a partir de la fecha de compra, y persiste todo en `WC`.
2. **Given** una compra en cuotas ya cargada, **When** el usuario busca por contacto o fecha, **Then** la encuentra en el listado con su cantidad de cuotas y estado.
3. **Given** una cuota de una compra existente, **When** el usuario la marca como cobrada, **Then** ese estado queda reflejado en el listado de compras en cuotas.
4. **Given** un importe total que no se divide en partes iguales entre la cantidad de cuotas, **When** el sistema genera el cronograma, **Then** ajusta la diferencia de centavos en la última cuota, de forma que la suma de todas las cuotas sea exactamente igual al importe total.

---

### User Story 4 - Consultar el catálogo de tarjetas (Priority: P4)

Un usuario necesita ver qué tarjetas existen en el sistema y cuáles están activas, como referencia rápida y como origen de los combos de selección de tarjeta en las otras historias.

**Why this priority**: Es un catálogo chico (5 registros reales) y de solo lectura — el valor que aporta por sí solo es bajo, pero es una dependencia natural de las historias 1 y 3.

**Independent Test**: Abrir el listado de tarjetas y verificar que muestra las tarjetas reales de `WC` con su banco y si están activas.

**Acceptance Scenarios**:

1. **Given** el catálogo de tarjetas cargado en `WC`, **When** el usuario abre el listado, **Then** ve todas las tarjetas con su nombre, banco y si están activas.
2. **Given** una tarjeta inactiva, **When** el usuario intenta seleccionarla para cargar una compra en cuotas o un resumen nuevo, **Then** no aparece entre las opciones seleccionables (pero sigue viéndose en su historial ya cargado).

---

### Edge Cases

- Un resumen sin líneas de consumo ("solo cabecera") debe poder cargarse y mostrarse igual que uno con líneas — 70 de 293 resúmenes reales (24%) no tienen ninguna línea, no es un caso marginal. La columna `SoloCabecera` del esquema real está en NULL en el 100% de los casos y no debe usarse como indicador — el criterio es la ausencia de líneas.
- Una línea de consumo de un resumen sin contacto ni número de documento asociado (la mayoría de los casos reales) debe mostrarse igual, sin exigir esos datos.
- Una línea de consumo o un cargo de cabecera con importe negativo (devolución del comercio, o un ajuste a favor del cliente) debe sumarse tal cual, con su signo real, nunca con valor absoluto — existen casos reales de ambos.
- Una compra en cuotas con una sola cuota (pago en un solo pago, sin financiación real) debe aceptarse igual.
- Dos resúmenes de la misma tarjeta con el mismo código de resumen (posible reimportación) — el sistema debe advertir, no bloquear (mismo criterio que otros módulos: FR-009a/FR-012a de Ventas de Hacienda/Granos).
- Una tarjeta inactiva con movimientos históricos sigue siendo consultable en su cuenta corriente y en resúmenes ya cargados, aunque no se pueda usar para cargar nuevos.
- El cronograma automático de cuotas (FR-005) asume financiación sin interés — no reproduce el patrón de cuotas de importe creciente que existe en 8 de las 18 compras en cuotas históricas reales (financiación con interés bancario cargada manualmente en su momento). Esas compras históricas solo se leen, nunca se regeneran.
- Editar una compra en cuotas que cambia el importe total o la cantidad de cuotas regenera todo el cronograma (FR-007a) — cualquier cuota que ya estuviera marcada como cobrada pierde ese estado y debe volver a marcarse.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE mostrar el catálogo de tarjetas (nombre, banco, activa/inactiva) en modo solo lectura — el alta de tarjetas nuevas no es parte de este alcance.
- **FR-002**: El sistema DEBE mostrar, para una tarjeta dada, sus movimientos de cuenta corriente ordenados cronológicamente con el saldo acumulado por movimiento, con el mismo criterio ya usado en Cuentas Corrientes (004). El saldo se construye a partir de los resúmenes de la tarjeta (deuda, un movimiento por resumen) **y de los pagos registrados contra cada resumen** (crédito — Session 2026-09-19, antes solo se mostraba la deuda) — las cuotas de compras en cuotas no generan un movimiento de cuenta corriente propio, para evitar contar dos veces la misma deuda cuando una cuota ya está incluida en el resumen del período (ver Assumptions).
- **FR-002a**: El sistema DEBE permitir registrar el pago de un resumen, ya sea confirmando un movimiento bancario real candidato (`Movimientos BNA`/`Movimientos Galicia` con `IdContacto` de esa tarjeta) o cargándolo manualmente. (Session 2026-09-19.)
- **FR-003**: El sistema DEBE resolver un movimiento de cuenta corriente con origen "Tarjetas" (un cargo de resumen o un pago) a un destino navegable: el resumen de tarjeta que lo originó, en vez de mostrarlo como "fuera de alcance". Esta rama de origen no existe hoy en la vista de movimientos de Cuentas Corrientes — hay que agregarla (research.md).
- ~~**FR-004**~~/~~**FR-005**~~/~~**FR-007**~~/~~**FR-007a**~~ (Session 2026-09-19, ver Clarifications): sin efecto — Historia 3 pasa a ser solo lectura. El texto original queda tachado como registro histórico de la decisión inicial, ya revertida con evidencia real.
- **FR-006**: El sistema DEBE permitir buscar y listar las compras en cuotas cargadas (histórico, solo lectura), por contacto y rango de fechas, sin mostrar nada hasta que se aplique al menos un filtro (mismo criterio que FR-010).
- **FR-008**: El sistema DEBE permitir cargar un resumen de tarjeta (tarjeta, código de resumen, fecha de cierre, fecha de vencimiento, un link/ruta al resumen original en PDF, y los cargos/impuestos de cabecera: Impuesto de Sellos, Gastos de Administración, Mantenimiento de Cuenta, Renovación Anual, Promoción BNA, Crédito Contingente, Interés de Financiación, Interés Compensatorio, IVA 10,5%, Percepción IVA 10,5%, IVA 21%, Percepción IVA 21%, Percepción IIBB, Ajuste de Resumen Anterior) junto con sus líneas de consumo (fecha de compra, detalle, importe, fecha de vencimiento de la compra, contacto opcional, número de documento opcional).
- **FR-008a**: Al consultar un resumen, el sistema DEBE mostrar la cabecera completa (todos los cargos/impuestos de FR-008 con valor distinto de cero), no solo el total calculado. (Session 2026-09-19 — omisión real en la primera implementación.)
- **FR-009**: El sistema DEBE permitir cargar un resumen sin líneas de consumo ("solo cabecera"), sin exigir al menos una línea.
- **FR-009a**: El sistema DEBE permitir vincular una línea de consumo con una o varias Compras reales ya cargadas (factura/NC/ND, por `IdDeuda`), cada vínculo con su propio importe imputado — cubre tanto una línea documentada por más de un proveedor como el pago parcial de una compra en cuotas. (Session 2026-09-19.)
- **FR-010**: El sistema DEBE permitir buscar y listar los resúmenes cargados, por tarjeta y rango de fechas de cierre/vencimiento, sin mostrar nada hasta que se aplique al menos un filtro (mismo criterio ya usado en Compras/Ventas/Contactos).
- **FR-011**: Al abrir un resumen, el sistema DEBE mostrar el total calculado a partir de sus líneas y cargos (`Σ líneas.Importe` + todos los cargos/impuestos de cabecera de FR-008, cada uno con su propio signo). El esquema real no guarda un "total declarado por el banco" — el contraste contra el resumen en papel/PDF lo hace el usuario a simple vista, no es una validación automática del sistema.
- **FR-012**: El sistema DEBE advertir (sin bloquear el guardado) si se carga un resumen con el mismo código para la misma tarjeta que uno ya existente.
- **FR-013**: El sistema DEBE permitir editar y eliminar un resumen ya cargado, usando el mismo mecanismo de bloqueo exclusivo de edición que Compras y Ventas (evita que dos personas editen el mismo registro a la vez). Ya no aplica a compras en cuotas (Historia 3, solo lectura desde Session 2026-09-19).
- **FR-014**: El sistema NO DEBE incluir conciliación automática entre líneas de consumo y cuotas/deudas, ni distribución de una línea de consumo entre varios contactos — ambas funcionalidades existen en el esquema de origen pero nunca se usaron en producción (0 registros reales).
- **FR-015**: Todas las escrituras de este módulo (alta/edición/eliminación de compras en cuotas y resúmenes) DEBEN hacerse exclusivamente contra la base de datos de trabajo `WC`, nunca contra `LaHerencia`.

### Key Entities

- **Tarjeta**: una tarjeta de crédito de la empresa (nombre, banco emisor, activa/inactiva). Catálogo de solo lectura en este alcance.
- **Compra en cuotas**: una compra financiada en cuotas (fecha, contacto, número de comprobante, cantidad de cuotas), origen de un cronograma de cuotas. No está vinculada a una tarjeta del catálogo — el esquema real nunca las relacionó.
- **Cuota**: una cuota individual de una compra en cuotas (número de cuota, fecha de vencimiento, importe, si está cobrada). No genera un movimiento de cuenta corriente propio (ver FR-002).
- **Resumen de tarjeta**: el resumen mensual de una tarjeta (código, fecha de cierre, fecha de vencimiento, cargos e impuestos de cabecera), asociado a una tarjeta. Es la única fuente de movimientos de cuenta corriente de una tarjeta.
- **Línea de consumo**: un consumo individual dentro de un resumen (fecha de compra, detalle, importe, contacto y documento opcionales).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un usuario puede encontrar y abrir cualquiera de los 293 resúmenes reales existentes por tarjeta y fecha en menos de 30 segundos.
- **SC-002**: El saldo acumulado que muestra la cuenta corriente de cada una de las 5 tarjetas reales coincide, centavo a centavo, con la suma de los totales calculados de sus resúmenes reales en `WC`.
- **SC-003**: El 100% de los movimientos de cuenta corriente con origen "Tarjetas" (un cargo de resumen) navegan al resumen concreto que los originó.
- **SC-004**: Un usuario puede cargar una compra en cuotas nueva y ver sus cuotas generadas automáticamente en menos de 1 minuto, sin tener que calcular manualmente ninguna fecha ni importe de cuota.
- **SC-005**: Ninguna escritura de este módulo llega nunca a la base de datos `LaHerencia` (verificado contra SQL Server tras cada escenario de prueba).

## Assumptions

- El alta de tarjetas nuevas (catálogo `Tarjetas`) es infrecuente y queda fuera de este alcance — se asume que, si hace falta, se agrega directo en la base de datos, igual que otros catálogos chicos del sistema (ej. `Establecimientos`).
- `Tarjetas` no tiene ninguna columna ni FK hacia `Contactos` en el esquema real. El vínculo tarjeta↔contacto (necesario para saber a qué contacto pertenece cada tarjeta, si se lo necesitara) solo puede resolverse por coincidencia textual entre `Tarjetas.TarjetaNombre` y `Contactos.[Razon Social]` de los 5 contactos con `Tipo Contacto = 'Tarjeta de Credito'` — se documenta como vínculo frágil (research.md), no se migra el dato.
- La compra en cuotas no se vincula a una tarjeta del catálogo (decisión explícita del usuario, dado que el esquema real de `dbo.[Tarjetas de Credito]` nunca tuvo esa columna): FR-004/FR-006 no piden ni filtran por tarjeta.
- La cuenta corriente de una tarjeta se construye exclusivamente a partir de los totales de sus resúmenes (decisión explícita del usuario) — las cuotas de compras en cuotas no aportan un movimiento propio, evitando por diseño el doble conteo que podría darse si una cuota ya incluida en un resumen del período se contara también por separado.
- El usuario que marca una cuota como "cobrada" es el mismo usuario administrativo único del resto del sistema, sin necesidad de un flujo de aprobación separado.
- El cronograma de cuotas se genera con periodicidad mensual fija a partir de la fecha de compra y sin interés (cuota fija, ajuste de redondeo solo en la última) — no hay evidencia en los datos reales de periodicidades distintas (quincenal, bimestral), aunque sí existen compras históricas con cuotas de importe creciente por financiación con interés bancario que este generador no reproduce (ver Edge Cases).
- La conciliación automática línea↔cuota y la distribución de una línea entre varios contactos (`Tarjetas_Conciliacion_Link`/`Propuesta`, `Tarjetas_Lineas_Distrib`) quedan explícitamente fuera de alcance: existen en el esquema pero tienen 0 filas en producción real — nunca se usaron en años de operación, y agregar esa complejidad sin evidencia de necesidad sería sobre-ingeniería.
- Los catálogos de apoyo `Tarjetas_TipoLinea` (20 filas) y `Tarjetas_MapeoConceptos` (43 filas, sí tienen datos reales, a diferencia de las tablas de conciliación) no son necesarios en este alcance porque la carga de resúmenes es manual, no una importación automática de archivos bancarios.
