# Feature Specification: Resultado y Costos de Cultivo

**Feature Branch**: `012-resultado-costos-cultivo`
**Created**: 2026-09-22
**Status**: Draft — especificación funcional, revisada por agentes especialistas, pendiente de implementación

**Input**: Módulo siguiente a Órdenes de Trabajo (`specs/011-ordenes-trabajo/spec.md`) en el roadmap de Producción/Agricultura. Corresponde a los dos últimos formularios agrícolas del sistema Access real que quedan sin migrar (`FrmResultados` y `FrmCostos`, ver `project_access_forms_analysis.md`): pantallas de consulta, no transaccionales, donde el usuario ve el resultado económico de una Campaña y puede bajar al detalle de un Cultivo puntual — superficie sembrada/cosechada/picada, rinde, márgenes y rentabilidad, en pesos y en dólares simultáneamente.

## Hallazgos de datos reales (WC, 2026-09-22, verificados en vivo por el agente `01-sql-server-engineer`)

- **`ResultadoCultivo_Resumen`** — la tabla heredada que parece diseñada para cachear el resultado ya calculado — está **vacía (0 filas)**. El cálculo debe hacerse en vivo contra las vistas en cada consulta; no hay caché heredado del que partir.
- **`ResultadoCultivo_Cierre`** (43 filas) registra `SuperficieCosechada`, `FechaInicioCosecha`, `FechaFinCosecha` por Cultivo/Campaña; 41 de las 43 filas están marcadas como *"Estimado automáticamente... Revisar manualmente"* — dato inferido, no cargado a mano. Ninguna pantalla existente permite corregirlo (queda fuera de alcance, ver Clarifications).
- **`Map_CultivoResultado` es 1:1, no 1:N**: 11 filas, una por cada uno de los 11 Cultivos (una con `IdDestino NULL`, "Sin Cultivo", inactiva). Cada fila trae `IdCultivo → IdDestino` (clave de las vistas de costeo) **e `IdCultivo → IdGrano`** (clave distinta, la que realmente usan las vistas de venta). Ningún Cultivo tiene más de un Destino.
- **7 de los 17 `IdDestino` usados en `vw_ResultadosCultivo_CostosBase`/`Seguros` no tienen ningún Cultivo asociado** en `Map_CultivoResultado` (huérfanos) — no es un caso raro, es más de un tercio de los códigos de costeo heredados.
- **El join real de `vw_ResultadosCultivo_Ventas`/`Deducciones` es por `IdGrano`, no por `IdDestino`**: `Map_CultivoResultado.IdGrano = [Venta Granos].IdProducto`. Para consolidar todo (ventas + costos + seguros) por Cultivo/Campaña hace falta pasar por `Map_CultivoResultado` con sus dos claves distintas, más traducir `Campaña` (texto, como viene en Ventas/Deducciones) a `IdCampaña` (numérico, como viene en CostosBase/Seguros) vía la tabla `Campañas` (32 filas — incluye pares "YYYY/YYYY", años sueltos como "2011"/"2014", y el valor especial "No Aplica"; todos son campañas reales, no basura).
- **Pastura no tiene venta como grano**: su fila en `Map_CultivoResultado` tiene `IdGrano NULL` con la observación *"Pastura sin venta como grano"* — se pastorea o se pica, no se cosecha en el sentido de los demás cultivos de grano.
- **10 filas de `vw_ResultadosCultivo_CostosBase` tienen `IdCampaña IS NULL`** (~$1,11M en pesos) — no se pueden atribuir a ningún Cultivo/Campaña.
- **`Signo`** de `vw_ResultadosCultivo_CostosBase` es confiable y sin ambigüedad (verificado: solo `1`/`-1`, definido explícitamente en la vista como `Nota de Crédito` → `-1`) — a diferencia de `vw_Cns_TotalesOrdenesPorProducto` en 011, no hace falta reemplazarlo por cálculo propio.
- **Riesgo real de doble conteo** (mismo patrón que el bug de stock corregido en 011): `Ordenes_Trabajo_Contratista_Factura.IdCompra` es una FK explícita a `Compras`, y `vw_ResultadosCultivo_CostosBase` también lee de `Compras`/`Det_Compras` (rubros con `IdClasifCostoCultivo` 1-4). Hoy `Ordenes_Trabajo_Contratista_Factura` está vacía (0 filas), así que no hay overlap real todavía, pero el día que se cargue la primera factura de contratista que además caiga en un rubro de costeo, sumar ambas fuentes duplicaría ese costo. Debe blindarse en el diseño, no solo confiar en que "hoy no pasa".
- **Maquinaria propia** también tiene dos fuentes sin vínculo entre sí: la tabla heredada `[Labores Maquinaria propia]` (55 filas, hasta 2022-01-31, ya sumada dentro de `vw_ResultadosCultivo_CostosBase`) y `Ordenes_Trabajo_Maquinaria` (011, sin escribir en la tabla heredada). Hoy no se superponen en fechas, pero es una coincidencia temporal, no una garantía de esquema.
- El módulo 011 (Órdenes de Trabajo) ya implementó una vista parcial de "costo por Cultivo/Campaña" (`/produccion/ordenes/resultado-cultivo`), que **solo cubre insumos + maquinaria + contratista de las órdenes nuevas** — no incluye superficie, rinde, ventas, deducciones, seguros ni rentabilidad, y no lee ninguna vista `vw_ResultadosCultivo_*` heredada.
- Vistas confirmadas y estables (solo lectura): `vw_ResultadoCultivo_Campaña` (13 columnas, agregada solo por Campaña — total consolidado), `vw_ResultadosCultivo_CostosBase` (14 columnas, detalle de líneas con `IdCompra`/`IdDetalleCompra`, origen y signo), `vw_ResultadosCultivo_CostosAgrupados` (7 columnas, ya agrupadas por Rubro/Concepto), `vw_ResultadosCultivo_Deducciones` (5 columnas), `vw_ResultadosCultivo_Seguros` (4 columnas), `vw_ResultadosCultivo_Ventas` (6 columnas, incluye bonificaciones).

## Clarifications

### Sesión 2026-09-22

- Q: ¿Qué relación tiene este módulo con la vista parcial "costo por Cultivo/Campaña" que ya existe en Órdenes de Trabajo? → A: Este módulo la reemplaza por completo. Incorpora ese costo (insumos/maquinaria/contratista de `Ordenes_Trabajo_*`) como una fuente más dentro del costo total de la Campaña, junto con los costos heredados, y agrega superficie, rinde, ventas, deducciones, seguros y rentabilidad. La pantalla parcial de 011 se **retira** del menú una vez que este módulo esté disponible — no queda como alternativa/redirección, para no dejar dos fuentes de verdad visibles.
- Q: `ResultadoCultivo_Cierre` (superficie y fechas de cosecha) hoy es mayormente autogenerado con datos "a revisar manualmente" — ¿este módulo debe permitir cargarlo/corregirlo? → A: Fuera de alcance de este corte, 100% solo lectura, igual que los formularios `FrmResultados`/`FrmCostos` originales. Poder editar `ResultadoCultivo_Cierre` es una necesidad real pero se especifica como módulo aparte más adelante.
- Q: ¿Con qué criterio de tipo de cambio se muestran los montos en dólares? → A: Cada vista heredada (`Pesos`/`Dolares`) ya trae ambos valores calculados a partir del TC vigente en la fecha de origen de **cada línea individual** (cada compra, cada venta, cada póliza tiene su propia fecha y su propio TC histórico) — se muestran tal cual vienen, sumados por columna, sin recalcular. Confirmado con datos reales (agente `07-financial-direction-specialist`) que esto significa que **la columna en pesos y la columna en dólares de un mismo Cultivo/Campaña son dos series independientes que no se pueden validar dividiendo una por la otra** (no existe un TC único de la campaña) — ver Assumptions y FR-003.
- Q: ¿Qué campaña se muestra por defecto al entrar al módulo, sin que el usuario elija nada (Historia 1)? → A: La campaña "actual" según la fecha de hoy — la tabla `Campañas` no tiene columnas de fecha, solo el nombre (`IdCampaña`/`Campaña`, ej. "2025/2026"), así que "actual" se deriva del rango de fechas implícito en el nombre (una campaña "YYYY/YYYY+1" cubre aproximadamente julio de `YYYY` a junio de `YYYY+1`; una campaña de un solo año "YYYY" cubre ese año calendario). Si la fecha de hoy no cae en el rango de ninguna campaña (o el nombre no es parseable, ej. "No Aplica"), el sistema cae a la campaña más reciente con algún dato cargado (venta, costo u orden de trabajo) como resguardo.
- Q: ¿Qué umbral dispara la advertencia de "costos incompletos" de FR-011? → A: Costo total menor al 20% de la venta neta (umbral fijo, no relativo a un histórico) — cubre tanto el caso de costo cero como el de un costo parcial cargado que todavía dejaría un margen artificialmente alto.

### `/speckit-analyze` (2026-09-22) — correcciones aplicadas

- **FR-010 corregido** (hallazgo I1): el badge de "costeo incompleto" no puede depender de un `IdDestino` sin Cultivo asociado (ese caso no ocurre nunca a nivel de un Cultivo real, `Map_CultivoResultado` es 1:1) — se redefinió sobre las 41 de 43 filas de `ResultadoCultivo_Cierre` con superficie cosechada auto-estimada, que sí es un caso real, común y por Cultivo/Campaña.
- **FR-003 corregido** (hallazgo U1): el rinde consolidado por Campaña se elimina explícitamente (no es agronómicamente comparable entre Cultivos distintos); el costo por hectárea consolidado se mantiene (es una división de sumas, válida).
- **FR-006 corregido** (hallazgo G1): la traducción Campaña↔`IdCampaña` es en ambos sentidos, no solo texto→id — las vistas de venta exponen `Campaña` como texto y las de costeo `IdCampaña` numérico.

## User Scenarios & Testing

*Prioridad y perfiles de usuario revisados por el agente `09-agroux-lead-product-architect`: este módulo es predominantemente de perfil **Dirección** (márgenes, rentabilidad, comparación entre campañas — tarjetas de KPI, no tablas operativas como pantalla de entrada), con un drill-down de perfil **Administración/auditoría** para quien concilia con el estudio contable.*

### Historia 1 — Ver el resultado consolidado de una Campaña (P1)

**Perfil de usuario**: Dirección/socio. Pantalla de entrada del módulo: tarjetas de KPI a nivel Campaña, y debajo una tabla resumen de una fila por Cultivo (no el detalle completo) para ver de un vistazo qué cultivo traccionó o arrastró el resultado.

Un socio o el administrador entra al módulo sin elegir nada todavía y quiere ver, para una Campaña (ej. "2025/2026"), el número consolidado: cuánto costó, cuánto se vendió y qué margen dejó toda la Campaña entre todos sus Cultivos.

**Why this priority**: Es el objetivo final que motivó migrar Remitos y Órdenes de Trabajo — sin esta pantalla, esos módulos alimentan datos que nadie puede consultar de forma consolidada. Dirección no debería tener que elegir un Cultivo primero para ver un número.

**Independent Test**: Elegir una Campaña con varios Cultivos cargados y verificar que el consolidado (superficie, costo, venta, margen) coincide con la suma de los resultados individuales de sus Cultivos (Historia 2).

**Acceptance Scenarios**:

1. **Given** una Campaña con varios Cultivos cargados, **When** el usuario entra al módulo y la selecciona, **Then** ve tarjetas de KPI con superficie, costo total, venta neta, margen bruto y rentabilidad de toda la Campaña, en pesos y en dólares, y una tabla con una fila por Cultivo.
2. **Given** una Campaña sin ningún dato cargado todavía, **When** el usuario la selecciona, **Then** ve un estado vacío neutro (ceros/guiones, sin color de advertencia), no un error.
3. **Given** la tabla resumen por Cultivo de una Campaña, **When** el usuario hace clic en una fila, **Then** navega al detalle de ese Cultivo puntual (Historia 2).

---

### Historia 2 — Consultar el resultado de un Cultivo puntual dentro de la Campaña (P1)

**Perfil de usuario**: Dirección. Drill-down desde la tabla resumen de Historia 1 (clic en una fila), o accesible con filtro directo Cultivo + Campaña.

El usuario quiere el detalle completo de un Cultivo puntual dentro de una Campaña (ej. "Soja primera 2025/2026"): superficie, rinde, costo, venta y margen de ese Cultivo específico.

**Why this priority**: Es el nivel de detalle que explica por qué el consolidado de Campaña dio el número que dio.

**Independent Test**: Elegir un Cultivo y Campaña con datos reales y verificar que superficie, rinde, costo, venta y margen coinciden con lo que hoy se puede reconstruir a mano sumando las vistas heredadas correspondientes a ese Cultivo.

**Acceptance Scenarios**:

1. **Given** un Cultivo con Órdenes de Trabajo, costos heredados y ventas cargadas en una Campaña, **When** el usuario lo consulta, **Then** ve superficie sembrada/cosechada/picada, rinde, costo total, costo por hectárea, venta neta, margen bruto y rentabilidad — en pesos y en dólares.
2. **Given** una Campaña ya cosechada (con fecha de cierre en `ResultadoCultivo_Cierre`), **When** se carga una Orden de Trabajo nueva de ese Cultivo/Campaña, **Then** el resultado se actualiza en la próxima consulta sin ningún paso de reapertura.
3. **Given** un Cultivo/Campaña sin ningún dato cargado todavía, **When** el usuario lo consulta, **Then** ve un estado vacío neutro, no un error.
4. **Given** un Cultivo como Pastura (sin venta como grano, `IdGrano NULL`), **When** el usuario lo consulta, **Then** el rinde se muestra como no aplicable ("—"), sin forzar un cálculo sin sentido; superficie y costo se muestran igual que para el resto.
5. **Given** un Cultivo/Campaña con venta registrada y costo total en cero, **When** el usuario lo consulta, **Then** ve el margen calculado igual (venta − 0) junto con una advertencia visual clara de "costos incompletos — margen no representativo".

---

### Historia 3 — Ver el detalle de costos que componen el total (P2)

**Perfil de usuario**: Administración/auditoría. Tabla densa (drawer o expansión), es el segundo nivel de drill-down, no la vista de entrada.

El usuario quiere entender de qué está compuesto el costo total de un Cultivo/Campaña, y poder rastrear cada monto hasta su comprobante de origen.

**Why this priority**: El total solo es confiable si se puede auditar; los costos heredados vienen de fuentes distintas (compras, órdenes de trabajo, seguros) y conviene poder desglosarlos y rastrearlos.

**Independent Test**: Sobre un Cultivo/Campaña con costos de varias fuentes, expandir el detalle, verificar que la suma de las líneas coincide con el total de Historia 2, y que cada línea originada en una Orden de Trabajo permite navegar a esa orden.

**Acceptance Scenarios**:

1. **Given** un Cultivo/Campaña con costos heredados y costos de Órdenes de Trabajo, **When** el usuario abre el detalle, **Then** ve cada concepto/rubro por separado con su monto en pesos y dólares, y la suma coincide con el costo total de Historia 2.
2. **Given** una línea de costo originada en una compra heredada, **When** el usuario la ve en el detalle, **Then** puede identificar el `IdCompra`/`IdDetalleCompra` de origen (como texto, ya que el módulo de Compras aún no está migrado a la web).
3. **Given** una línea de costo originada en una Orden de Trabajo (insumo, maquinaria o factura de contratista), **When** el usuario la ve en el detalle, **Then** tiene un link "Ver orden" que navega a `/produccion/ordenes/[idOrden]`.
4. **Given** un Cultivo/Campaña con seguros agrícolas cargados, **When** se consulta el detalle, **Then** el costo del seguro aparece identificado como tal, no mezclado sin etiqueta dentro de "otros costos".

---

### Historia 4 — Exportar el resultado a Excel (P2)

**Perfil de usuario**: Administración/estudio contable.

El estudio contable o el productor necesita llevarse el resultado de una o varias Campañas/Cultivos fuera del sistema, con el mismo nivel de detalle auditable que ofrece la pantalla.

**Why this priority**: Mismo patrón ya establecido en Remitos y Órdenes de Trabajo; bajo costo de implementación, alto valor para el usuario administrativo.

**Independent Test**: Exportar el resultado filtrado y verificar que el archivo generado contiene las mismas filas/columnas que la pantalla, en dos hojas.

**Acceptance Scenarios**:

1. **Given** una consulta de resultado con filtros aplicados, **When** el usuario exporta, **Then** recibe un `.xlsx` con dos hojas: "Resultado" (una fila por Cultivo/Campaña, mismas columnas de Historia 2) y "Detalle de costos" (desglose por concepto de Historia 3) — mismo patrón multi-hoja ya usado en `exportacion.py` de Órdenes de Trabajo.

### Edge Cases

- Una línea de `vw_ResultadosCultivo_CostosBase` con `Signo = -1` (Nota de Crédito) debe restar del costo total, no sumarse como un cargo más.
- Un `IdDestino` usado en las vistas de costeo sin ningún Cultivo asociado en `Map_CultivoResultado` (7 de 17 casos reales) hace que ese costo heredado no pueda ubicarse en ningún Cultivo — no es un caso por Cultivo/Campaña (ningún Cultivo real tiene `IdDestino` NULL, es 1:1), es un costo sin clasificar a nivel de Campaña (FR-012).
- Una fila de `ResultadoCultivo_Cierre` con `Observaciones` de estimación automática (41 de 43 filas reales) hace que la superficie cosechada de ese Cultivo/Campaña sea un dato inferido, no confirmado — se muestra con la nota visible de FR-010 (badge ocre + tooltip, no bloqueante), sin bloquear la consulta del resto de los datos.
- Costos heredados con `IdCampaña IS NULL` (10 filas reales, ~$1,11M) no se pueden atribuir a ningún Cultivo/Campaña — no se ocultan silenciosamente: se muestran como un total "sin clasificar" visible en el nivel consolidado de Campaña (Historia 1).
- Venta registrada antes de cerrar todos los costos de la campaña (venta anticipada/forward, o venta de granos antes de imputar el costo de cosecha) es una situación comercial real y común — el margen se calcula igual, sin bloquear, pero con la advertencia visual de FR-011.
- Un Cultivo sin venta como grano (Pastura, `IdGrano NULL` en `Map_CultivoResultado`) muestra el rinde como no aplicable ("—") en vez de forzar un cálculo sin unidad comparable.
- Superficie cosechada en cero o sin cargar: el rinde se muestra como "—", nunca se calcula dividiendo por superficie sembrada (serían números no comparables).
- Superficie sembrada o cosechada en cero al calcular costo por hectárea: se muestra "—" en vez de dividir por cero (mismo criterio que el rinde).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST mostrar, como pantalla de entrada del módulo, el resultado consolidado de una Campaña completa (todos sus Cultivos juntos) con una tabla resumen de una fila por Cultivo (Historia 1). Al entrar sin elegir ninguna Campaña, MUST preseleccionar la campaña "actual" según la fecha de hoy (derivada del rango de fechas implícito en el nombre de la Campaña — "YYYY/YYYY+1" ≈ julio de `YYYY` a junio de `YYYY+1`, "YYYY" ≈ ese año calendario); si ninguna Campaña coincide con la fecha de hoy, MUST caer en la Campaña más reciente con algún dato cargado. El usuario MUST poder cambiar la Campaña seleccionada libremente.
- **FR-002**: El sistema MUST permitir bajar al detalle de un Cultivo puntual dentro de la Campaña, por clic desde la tabla resumen o por filtro directo Cultivo + Campaña (Historia 2).
- **FR-003**: El sistema MUST mostrar, por Cultivo/Campaña: superficie sembrada, superficie cosechada, superficie picada, rinde, costo total, costo por hectárea (sembrada y cosechada), venta neta, margen bruto y rentabilidad. El consolidado por Campaña (Historia 1) MUST mostrar los mismos indicadores salvo **rinde**, que no se consolida (sumar/promediar rinde de Cultivos distintos —ej. kg/ha de soja y de girasol— no es un número agronómicamente comparable; el rinde se muestra únicamente al nivel de un Cultivo puntual, Historia 2). Cada monto en pesos y en dólares, calculados como dos series independientes (cada una a partir del TC histórico de cada línea de origen; no se validan ni recalculan dividiendo una por la otra, ver Assumptions).
  - **Rinde** = cantidad cosechada / superficie cosechada (nunca dividido por superficie sembrada); se muestra "—" si la superficie cosechada es cero o no está cargada, o si el Cultivo no tiene venta como grano (`IdGrano NULL`, ej. Pastura).
  - **Costo por hectárea** (sembrada y cosechada) = costo total / superficie correspondiente; sí se consolida a nivel de Campaña (es una división de dos sumas, matemáticamente válida entre Cultivos distintos).
  - **Margen bruto** = venta neta − costos directos de la campaña (insumos, labores, maquinaria, contratistas, seguros); no incluye costos de estructura/administración, que el sistema no imputa a nivel de Cultivo/Campaña.
  - **Rentabilidad** = margen bruto / costo total, calculada por separado en pesos y en dólares.
- **FR-004**: El costo total de un Cultivo/Campaña MUST combinar los costos heredados (`vw_ResultadosCultivo_CostosBase`/`CostosAgrupados`, respetando `Signo`), los seguros agrícolas (`vw_ResultadosCultivo_Seguros`) y el costo de insumos + maquinaria propia + contratista de las Órdenes de Trabajo nuevas (`Ordenes_Trabajo_*`), **excluyendo** cualquier factura de contratista (`Ordenes_Trabajo_Contratista_Factura.IdCompra`) que ya esté incluida en `vw_ResultadosCultivo_CostosBase`, para evitar contar el mismo comprobante dos veces.
- **FR-005**: El sistema MUST calcular el resultado en vivo contra las vistas y tablas heredadas en cada consulta (no existe caché heredado utilizable) — una Campaña ya cosechada sigue sumando costo si se carga una Orden de Trabajo nueva, sin ningún paso de reapertura.
- **FR-006**: El sistema MUST traducir cada Cultivo a su `IdDestino` (vistas de costeo) y a su `IdGrano` (vistas de venta) vía `Map_CultivoResultado`, y traducir `Campaña` en ambos sentidos (texto → `IdCampaña` numérico, para las vistas que exponen `IdCampaña`; `IdCampaña` → texto, para `vw_ResultadosCultivo_Ventas`/`Deducciones`, que solo exponen `Campaña` como texto) vía la tabla `Campañas`, antes de unir las distintas fuentes.
- **FR-007**: El sistema MUST permitir ver el detalle de costos que componen el total de un Cultivo/Campaña, agrupado por concepto/rubro, con su monto en pesos y dólares, y la línea de origen individual identificable (`IdCompra`/`IdDetalleCompra`, o la Orden de Trabajo con link a su detalle) (Historia 3).
- **FR-008**: El sistema MUST permitir exportar el resultado filtrado a una planilla `.xlsx` con dos hojas — "Resultado" (una fila por Cultivo/Campaña) y "Detalle de costos" (desglose por concepto) — siguiendo el patrón multi-hoja ya usado en la exportación de Órdenes de Trabajo (Historia 4).
- **FR-009**: El sistema MUST mostrar un estado vacío neutro (sin colores de advertencia) cuando un Cultivo/Campaña o una Campaña completa no tiene ningún dato cargado todavía.
- **FR-010**: El sistema MUST señalar con un badge ocre y tooltip explicativo (no bloqueante, no rojo de error) cuando la superficie cosechada de un Cultivo/Campaña proviene de una fila de `ResultadoCultivo_Cierre` marcada como estimación automática sin revisar (`Observaciones` contiene *"Revisar manualmente"* — 41 de 43 filas reales), indicando "superficie cosechada estimada — revisar". *(Corregido en `/speckit-analyze`, hallazgo I1: la redacción original ataba este badge a un `IdDestino` sin Cultivo asociado — un caso que, según `Map_CultivoResultado` (1:1, ver Hallazgos), nunca ocurre a nivel de un Cultivo real; ese caso ya lo cubre FR-012 a nivel de Campaña.)*
- **FR-011**: El sistema MUST señalar con un badge/ícono de advertencia (no bloqueante) cuando un Cultivo/Campaña tiene venta registrada y el costo total es menor al 20% de la venta neta (umbral fijo, cubre tanto el caso de costo cero como el de costo parcial cargado), indicando "costos incompletos — margen no representativo".
- **FR-012**: El sistema MUST mostrar de forma visible (no ocultar silenciosamente) el total de costos heredados que no pudieron clasificarse en ningún Cultivo/Campaña (ej. líneas con `IdCampaña NULL`), en el nivel consolidado de Campaña.
- **FR-013**: El sistema MUST ser de solo lectura: no debe permitir crear, editar ni eliminar ningún dato desde este módulo, incluyendo `ResultadoCultivo_Cierre`.
- **FR-014**: El total consolidado de una Campaña (Historia 1) MUST coincidir exactamente con la suma de los resultados individuales de sus Cultivos (Historia 2).
- **FR-015**: El sistema MUST retirar del menú la vista parcial de costo por Cultivo/Campaña de Órdenes de Trabajo (`/produccion/ordenes/resultado-cultivo`) una vez que este módulo esté disponible, y MUST agregar una entrada nueva en el menú de Producción ("Resultado de Cultivo"), al mismo nivel que Remitos y Órdenes de Trabajo.

### Key Entities

- **Resultado de Campaña**: vista calculada (no una tabla propia) que consolida superficie, costo, venta, margen bruto y rentabilidad de todos los Cultivos de una Campaña, en pesos y dólares — la pantalla de entrada del módulo.
- **Resultado de Cultivo/Campaña**: el mismo cálculo, acotado a un Cultivo puntual dentro de una Campaña — el nivel de drill-down principal.
- **Detalle de costo**: cada línea que compone el costo total de un Cultivo/Campaña, con su concepto/rubro, origen (`IdCompra`/`IdDetalleCompra` o Orden de Trabajo) y signo (cargo o crédito/ajuste).
- **Mapeo Cultivo → Destino/Grano** (`Map_CultivoResultado`, ya existente, 1:1): traduce cada Cultivo operativo (usado en Órdenes de Trabajo, Remitos) a su `IdDestino` (vistas de costeo) y su `IdGrano` (vistas de venta) — ambas claves distintas, ninguna es 1:N.
- **Mapeo Campaña texto ↔ `IdCampaña`** (`Campañas`, ya existente): traduce en ambos sentidos, según lo que exponga cada vista heredada (`vw_ResultadosCultivo_CostosBase`/`Seguros` usan `IdCampaña`; `vw_ResultadosCultivo_Ventas`/`Deducciones` usan `Campaña` como texto).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un usuario puede consultar el resultado consolidado de una Campaña y, desde ahí, el detalle de un Cultivo puntual, en menos de 10 segundos desde que entra al módulo, sin tener que elegir un Cultivo antes de ver el primer número.
- **SC-002**: El costo total mostrado para cualquier Cultivo/Campaña con datos reales coincide, verificado contra al menos 5 combinaciones reales de `WC`, con la suma manual de las vistas heredadas correspondientes (diferencia menor al redondeo de centavos), sin ningún caso de doble conteo entre Órdenes de Trabajo y costos heredados.
- **SC-003**: Cargar una Orden de Trabajo nueva en una Campaña ya cosechada actualiza el resultado de esa Campaña en la siguiente consulta, sin ningún paso adicional de "reapertura".
- **SC-004**: El total consolidado de una Campaña (Historia 1) coincide exactamente con la suma de los resultados individuales de sus Cultivos (Historia 2), verificado contra al menos 3 campañas reales con más de un cultivo cargado.
- **SC-005**: Ningún monto de costo heredado queda oculto sin explicación: todo costo que no pudo clasificarse en un Cultivo/Campaña (por falta de mapeo o de campaña) es visible en algún nivel del módulo.

## Assumptions

- Los usuarios de este módulo son los mismos que ya usan Remitos/Órdenes de Trabajo/Compras — sin roles ni permisos diferenciados (consistente con el resto del sistema).
- El tipo de cambio de los montos en dólares se toma tal cual viene calculado en las columnas `Pesos`/`Dolares` de las vistas heredadas, cada una ya calculada al TC histórico de la fecha de origen de cada línea individual (compra, venta, póliza). **La columna en pesos y la columna en dólares de un mismo Cultivo/Campaña son dos series independientes**: no existe un TC único de la campaña, y no deben validarse ni recalcularse dividiendo una por la otra.
- `ResultadoCultivo_Cierre` (registrar la cosecha real de una campaña) queda fuera de alcance de este corte; puede ser una spec futura.
- El desglose de rinde/costo por Lote dentro de un Cultivo/Campaña queda fuera de alcance de este corte — las vistas heredadas confirmadas agregan a nivel Cultivo/Campaña, no por Lote.
- La pantalla parcial de costo por Cultivo/Campaña de 011 se retira del menú una vez implementado este módulo (FR-015) — no queda como una segunda fuente de verdad duplicada.
- Las vistas heredadas (`vw_ResultadoCultivo_Campaña`, `vw_ResultadosCultivo_*`) son estables y no requieren cambios de esquema; se leen tal cual, igual que el resto de vistas heredadas usadas en 010/011.
- El módulo de Compras aún no está migrado a la web — la trazabilidad de FR-007 hacia una línea de compra heredada se muestra como identificador (texto), no como link clickeable, hasta que exista esa pantalla.
