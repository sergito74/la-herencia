# Feature Specification: Órdenes de Trabajo

**Feature Branch**: `011-ordenes-trabajo`
**Created**: 2026-09-22
**Status**: Draft — especificación funcional, pendiente de implementación

**Input**: Módulo Órdenes de Trabajo del sistema Access real (`FrmOrdenTrabajo` + `FrmAsignarInsumoACultivos`), migrado a la web app sobre `WC`. Es el módulo siguiente a Remitos (`specs/010-remitos/spec.md`): consume el stock de insumos costeado por FIFO y lo imputa a Lote, Cultivo y Campaña, con el objetivo de poder calcular el costo total (y eventualmente el resultado) de cada Cultivo/Campaña.

## Clarifications

### Sesión 2026-09-22 (30 preguntas, con los agentes especialistas: SQL Server, producción agrícola, dirección financiera, gestión agro integrada, arquitectura de producto/UX, y datos reales de `WC`)

- **Lotes (40), Cultivos (11) y Campañas (32)** ya existen como catálogos reales en `WC` y se reutilizan tal cual. El lote de prueba `PRUE` se elimina en la migración. La campaña `No Aplica` es un valor válido y se conserva.
- **Tipo de Labor**: el catálogo real (Pulverización terrestre, Pulverización aérea, Siembra, Fertilización terrestre, Disqueado) es correcto como punto de partida, pero debe quedar abierto: tiene que existir una pantalla de administración para agregar nuevos tipos de labor (no hardcodeado en el código).
- **Contratistas**: hoy hay dos campos heredados (`IdContratistaContacto`, FK real a `Contactos` con 21 marcados `EsContratistaLabores=1`; y `Contratista`, entero 1-13 sin tabla de referencia, tabla vieja en desuso). Son el mismo concepto de negocio. La fuente de verdad es `Contactos` vía `IdContratistaContacto`; la columna `Contratista` no se migra.
- **Maquinaria propia**: la planilla heredada `Labores Maquinaria propia` (costo por hectárea en pesos y dólares) no tiene ningún vínculo a `Ordenes`. Se vincula al módulo nuevo porque la maquinaria propia también ejecuta órdenes de trabajo y su costo se imputa igual que el de un contratista.
- **Alcance**: todas las historias de este módulo son P1 (imprescindibles para el primer corte, sin fase 2 pendiente): registro de la orden con consumo de insumos e imputación de costo; costeo de maquinaria propia; gestión de contratistas con su factura imputada a Cultivo/Campaña; y el cálculo del costo total por Cultivo/Campaña (conectando con el motor de costeo heredado). **Mano de obra propia** (jornales de empleados) queda fuera de alcance. Trazabilidad fitosanitaria formal (recetas agronómicas, BPA) también queda fuera; el registro normal de dosis/producto/lote/fecha ya deja rastro suficiente para este corte.
- **Flujo**: la orden se carga **antes** de ejecutar la labor, como planificación, completa de una sola vez (sin pantallas separadas de planificación/ejecución). Al guardar se emite el **Formulario de Retiro**: el documento que usa el encargado de campo para preparar los insumos que entrega al contratista o a la maquinaria propia. La Orden de Trabajo **es** el parte diario formalizado (no hay dos conceptos separados).
- **Estado explícito**: se agrega un estado a la orden (hoy Access no tenía ninguno, se infería de la fecha de ejecución vacía). Estados: Planificada, Ejecutada, Anulada.
- **Edición y anulación**: misma regla que Remitos — edición libre mientras no haya consumo asociado; después solo anulación con motivo (sin borrado físico); anular devuelve las capas FIFO de stock consumidas.
- **Devoluciones**: lo que el contratista devuelve sin usar (sobrante por redondeo o ajuste) reingresa al stock como una entrada, no como una baja.
- **Multi-lote y distribución**: una orden puede cubrir varios lotes, y estos lotes pueden pertenecer a distintos cultivos y campañas dentro de la misma orden (confirmado con datos reales: promedio 5,3 distribuciones por renglón de insumo). El Lote/Cultivo/Campaña son atributos de **cada renglón de distribución**, nunca de la cabecera de la orden.
- **Reparto manual por dosis**: el ingeniero agronómico a cargo de la planificación carga la dosis por hectárea (`DosisHa`) para cada lote elegido; el sistema calcula la cantidad total de cada insumo sumando dosis/ha × superficie de los lotes elegidos, y de ahí sale el total a retirar del stock.
- **Lote incluido pero no aplicado**: es una decisión válida del ingeniero agronómico (no todos los lotes de un mismo cultivo reciben siempre los mismos agroquímicos); se conserva el concepto heredado (`Aplicar`).
- **Regla de integridad nueva**: el total retirado de cada insumo debe coincidir siempre con la suma de lo repartido entre lotes, ajustado por las devoluciones al stock. No debe quedar cantidad sin asignar (a diferencia del dato heredado, donde el 1,6% de los renglones no cerraba).
- **Mermas de aplicación**: lo que ocurre en el campo (ajuste de la mezcla, pérdida del aplicador) no se distingue ni se carga en el sistema; el sistema solo ve total retirado, total repartido y total devuelto.
- **Stock**: el consumo de una orden descuenta stock por FIFO reutilizando el costeo de Remitos (010); las unidades reutilizan `Unidades_Medida`/`Producto_Unidad` ya creadas en ese módulo, sin catálogo nuevo. Si el consumo solicitado supera el stock disponible, se advierte con fuerza y se permite continuar (como en Remitos), porque lo entregado a terceros es siempre aproximado; un stock negativo resultante es señal de posible error a revisar, no un bloqueo duro.
- **Sin superposición con bajas de stock**: el consumo de una orden y una baja manual de stock (Historia 4 de Remitos) son flujos independientes que no compiten por el mismo insumo; no hace falta una validación cruzada especial.
- **Costeo de contratistas**: se pagan igual que un proveedor de insumos (mismo circuito de Compras/cuentas corrientes), con su propia factura, que también se imputa a Cultivo/Campaña. No hay contratistas que facturen en dólares, pero todo costo del módulo debe poder expresarse en pesos y en dólares, dolarizando con el **dólar vendedor BNA**.
- **Cierre de campaña**: no hay una fecha de cierre formal. El costeo de un cultivo/campaña arranca con la primera pulverización/fumigación y cierra conceptualmente con la fecha de cosecha, pero pueden seguir llegando costos después (control de cosecha, seguimiento agrícola, seguros agrícolas). El sistema debe poder seguir sumando costos a una campaña ya cosechada sin ningún bloqueo de fecha.
- **Órdenes sin cultivo específico** (mantenimiento de infraestructura, etc.): llevan Rubro y Centro de Costos, igual que las bajas de stock sin orden de Remitos, y quedan fuera de la imputación a Cultivo/Campaña.
- **Objetivo central del módulo**: conectar con el motor de costeo heredado (`vw_ResultadoCultivo_Campaña`, `vw_Costos_BaseLineas`, `vw_ResultadosCultivo_CostosBase/CostosAgrupados`, etc.) para poder calcular el costo total —y a futuro el resultado— de cada Cultivo/Campaña. No es un objetivo de una fase posterior: es la razón de ser de este módulo.

### Sesión 2026-09-22 — Clarificación post-especificación

- Q: ¿De dónde sale la tarifa de costo por hectárea de la maquinaria propia usada en una orden? → A: Se carga a mano en cada orden, sin catálogo de máquinas ni tarifa persistente (opción B).
- Q: ¿Qué fecha determina el tipo de cambio (dólar vendedor BNA) para dolarizar el costo de un contratista? → A: La fecha de la factura del contratista, mismo criterio que Remitos con el TC de la factura vinculada.
- Q: ¿Quién puede crear, ejecutar y anular una orden de trabajo — todos los usuarios por igual, o hay roles diferenciados? → A: Sin roles distintos por ahora (opción A), igual que el resto del sistema; se revisará si el sistema pasa a ser multiusuario con permisos.
- Q: ¿El Formulario de Retiro necesita su propia numeración secuencial, o alcanza con el número de la Orden de Trabajo? → A: Numeración secuencial propia, independiente del número de orden (opción A).

## Hallazgos de datos reales (WC, 2026-09-22)

- **153 órdenes** (2015-10-18 a 2026-09-09), **820 renglones de insumo** (`Ordenes_Detalles`), **4.319 renglones de distribución** (`Ordenes_Detalles_Distrib`, prom. 5,3 por renglón de insumo), **879 filas** de lotes por orden (`Ordenes_Lotes`).
- Catálogos: 40 lotes (39 usados en alguna orden, falta solo el de prueba `PRUE`), 11 cultivos (10 usados, falta el genérico "Sin Cultivo"), 32 campañas (24 usadas), 5 tipos de labor.
- **Integridad referencial sana**: 0 huérfanos duros en las relaciones `Ordenes`/`Ordenes_Detalles`/`Ordenes_Detalles_Distrib`/`Ordenes_Lotes` contra sus catálogos.
- **4 órdenes sin fecha de ejecución** (185, 182, 127, 123): es el equivalente heredado al estado "pendiente/planificada" que hoy no tiene columna propia. Ninguna fecha de ejecución es anterior a la fecha de pedido.
- **Campaña de cabecera casi inútil**: nula en 149 de 153 órdenes; la campaña real y aplicable siempre estuvo a nivel de renglón de distribución, confirmando la decisión de no migrarla como dato de cabecera.
- **Contratista sin unificar**: `IdContratistaContacto` (FK real, 21 contratistas marcados en `Contactos`, 1 sola orden con inconsistencia menor) y `Contratista` (entero 1-13 sin tabla de referencia, tabla vieja en desuso) — se unifica a `Contactos` en la migración.
- **`Total Aplicado` vs. distribuido**: en 13 de 820 renglones (1,6%) la cantidad total del renglón es mayor a la suma de lo repartido entre lotes (diferencias entre 1,3 y 105 unidades) — el dato heredado no cerraba; el módulo nuevo exige que siempre cierre, ajustando con las devoluciones al stock.
- **Unidades no normalizadas** en `Ordenes_Detalles_Distrib.Unidad`: LTS (3.181) y LITROS (187) sin unificar, KGS (896) y KILOS (7) sin unificar, más PACK (25), BOL (14), UN (9) — mismo problema que resolvió Remitos con `Unidades_Medida`; se reutiliza esa tabla.
- **`Labores Maquinaria propia`** (55 filas, sin PK, sin vínculo a `Ordenes`): planilla de costeo de maquinaria propia por hectárea, en pesos y dólares con TC, cargada a mano; se vincula al módulo nuevo.
- **`DetCompra_OT`** (intento previo de vincular compras a labores) está **vacía** (0 filas): confirma que no hay nada que migrar de ahí; la imputación automática de costo de contratistas/insumos se construye desde cero.
- **Sin cantidades negativas** en `Total Aplicado` (0 de 820), a diferencia de Remitos que tenía 3 casos.
- Vistas heredadas de referencia (no se modifican, pueden reutilizarse como contrato o reemplazarse por cálculo propio si su convención de signo no es clara): `vw_InsumosOrden`, `vw_LotesPorOrden`, `vw_TotSuperficiePorCultivoCampania`, `vw_Cns_TotalesOrdenesPorProducto` (signo negativo, a confirmar antes de reusar), `vw_ExistenciaProductos` (ya usada por Remitos), `vw_Costos_BaseLineas`, `vw_ResultadosCultivo_CostosBase/CostosAgrupados/Deducciones/Seguros/Ventas`, `vw_ResultadoCultivo_Campaña`.
- Formularios Access reales identificados (`docs/legacy-access-analysis.md`): `FrmOrdenTrabajo` (formulario principal), `FrmAsignarInsumoACultivos` (distribución de insumo por dosis/ha), `FrmKardexInsumo`, `FrmCostos`/`FrmResultados` (costeo y rentabilidad por cultivo-campaña).

## User Scenarios & Testing

### Historia 1 — Planificar y registrar una Orden de Trabajo (P1)

Un ingeniero agronómico (o administración a partir de su indicación) planifica una labor: fecha, tipo de labor, contratista o maquinaria propia asignada, los lotes a tratar (pudiendo pertenecer a distintos cultivos y campañas), y para cada insumo a usar, la dosis por hectárea en cada lote elegido.

1. Al elegir los lotes y la dosis/ha de cada uno, el sistema calcula la cantidad total de cada insumo a retirar (dosis/ha × superficie de cada lote elegido, sumado).
2. Un lote puede incluirse en la orden pero marcarse como no aplicado, sin que eso sea un error.
3. Al guardar, la orden queda en estado **Planificada**, se emite el **Formulario de Retiro** con su propio número secuencial (listado de insumos a preparar) y se descuenta el stock de cada insumo por FIFO (reutilizando el costeo de Remitos).
4. Si el consumo solicitado supera el stock disponible, el sistema advierte con fuerza y permite confirmar igual.
5. Editar: libre mientras la orden no tenga devoluciones ni facturas de contratista vinculadas; después solo anulación con motivo, que devuelve al stock las capas FIFO consumidas.
6. Marcar la orden como **Ejecutada** cuando la labor se realizó en el campo.

### Historia 2 — Devoluciones de insumo (P1)

Cuando el contratista o el encargado devuelven insumo no utilizado (sobrante por redondeo o ajuste de la preparación), el usuario registra la devolución contra la orden.

1. La devolución reingresa la cantidad al stock (nueva capa de entrada).
2. El total retirado de la orden se ajusta para que la suma de lo repartido entre lotes vuelva a cerrar exactamente contra lo efectivamente consumido (retirado menos devuelto).
3. No se distinguen mermas de aplicación en el campo: solo se registra lo retirado, lo repartido por lote y lo devuelto.

### Historia 3 — Costeo de maquinaria propia (P1)

Cuando una orden usa maquinaria propia (en lugar de o junto a un contratista), el usuario la identifica y carga manualmente el costo por hectárea de esa orden (en pesos y, si corresponde, en dólares), sin depender de una tarifa persistente por máquina, imputándolo a los mismos Cultivo/Campaña que los insumos de esa orden.

1. El costo de maquinaria propia se prorratea entre los lotes de la orden por superficie, igual que el insumo.
2. Queda disponible para el cálculo del costo total de la orden y de la campaña.

### Historia 4 — Contratistas y su factura (P1)

El contratista que ejecuta una orden se gestiona como un proveedor: tiene su propia factura (vía Compras) que se vincula a la orden y se imputa a los Cultivo/Campaña que trató.

1. El costo del contratista se expresa en pesos; el sistema también lo dolariza con el dólar vendedor BNA de la fecha de la factura del contratista (mismo criterio que Remitos con el TC de la factura vinculada) para reportes en dólares.
2. El costo de contratista se prorratea entre los lotes de la orden igual que el insumo y la maquinaria propia.

### Historia 5 — Órdenes sin cultivo específico (P2)

Una orden de mantenimiento general (arreglo de infraestructura, camino interno, etc.) que no corresponde a ningún cultivo se registra con Rubro y Centro de Costos, sin imputación a Cultivo/Campaña, igual que las bajas de stock sin orden de Remitos.

### Historia 6 — Costo y resultado por Cultivo/Campaña (P1)

Un usuario consulta el costo total acumulado de un Cultivo/Campaña, sumando insumos (FIFO), maquinaria propia y contratistas de todas sus órdenes de trabajo, conectado con el motor de costeo heredado (compras, seguros, comercialización) para poder ver el costo total y, a futuro, el resultado económico.

1. La consulta no exige que la campaña esté "cerrada"; sigue acumulando costos que lleguen después de la cosecha (control de cosecha, seguimiento agrícola, seguros agrícolas).
2. Se puede filtrar por Cultivo, Campaña y Lote, y exportar a Excel.

### Historia 7 — Administración de catálogos abiertos (P2)

Un administrador agrega un nuevo Tipo de Labor cuando la finca incorpora una labor no contemplada en el catálogo inicial (por ejemplo, cosecha o riego).

### Edge Cases

- Orden planificada cuyo consumo de insumo dejaría el stock negativo: se advierte y se permite confirmar; queda para revisión posterior.
- Orden con lotes de distintas campañas mezclados en la misma pasada (confirmado en datos reales): cada renglón de distribución lleva su propia Campaña/Cultivo/Lote, sin restricción de que sean uniformes dentro de la orden.
- Anulación de una orden cuyas capas FIFO de stock ya fueron parcialmente reutilizadas por consumos posteriores de otra orden: mismo problema ya resuelto en Remitos (recalcular, no bloquear).
- Devolución que supera la cantidad originalmente retirada para ese insumo en esa orden: se rechaza o se advierte (no puede devolverse más de lo retirado).
- Orden con contratista y maquinaria propia a la vez en la misma labor: ambos costos se registran y se prorratean, no son mutuamente excluyentes.

## Requirements

- **FR-001** El consumo de insumos de una orden descuenta stock por FIFO reutilizando el costeo de Remitos (010); no se modifica el motor de costeo existente, se conecta a él.
- **FR-002** El Lote, Cultivo y Campaña son atributos de cada renglón de distribución de insumo (y de los costos de maquinaria/contratista prorrateados), nunca de la cabecera de la orden.
- **FR-003** La cantidad total a retirar de cada insumo se calcula como la suma de (dosis por hectárea × superficie) de cada lote elegido para ese insumo; el usuario carga la dosis por hectárea, no la cantidad total.
- **FR-004** El total retirado de cada insumo debe coincidir siempre con la suma de lo repartido entre lotes, ajustado por las devoluciones a stock; el sistema no permite guardar una diferencia sin explicar.
- **FR-005** Toda orden tiene un estado explícito: Planificada, Ejecutada o Anulada.
- **FR-006** No hay borrado físico de órdenes: solo anulación con motivo, que devuelve al stock las capas FIFO consumidas por esa orden.
- **FR-007** Edición libre de una orden mientras no tenga devoluciones ni factura de contratista vinculada; después, corrección solo vía anulación con motivo.
- **FR-008** Al guardar una orden se genera el Formulario de Retiro con su propio número de documento secuencial, independiente del número de orden (listado de insumos a preparar), exportable/imprimible.
- **FR-009** Una devolución de insumo no utilizado reingresa esa cantidad al stock como una nueva entrada (capa), nunca como una baja.
- **FR-010** El catálogo de Tipos de Labor es administrable desde una pantalla propia (alta de nuevos tipos), no está fijo en el código.
- **FR-011** El maestro de contratistas es `Contactos` (los marcados `EsContratistaLabores`); no existe un catálogo de contratistas separado.
- **FR-012** El costo de maquinaria propia usada en una orden se carga a mano por hectárea en cada orden (sin catálogo de tarifas persistente por máquina) y se prorratea entre los lotes de esa orden por superficie, igual que el insumo.
- **FR-013** El costo de un contratista se vincula a su factura de Compras y se imputa a los Cultivo/Campaña de la orden, prorrateado por superficie.
- **FR-014** Todo costo del módulo (insumo, maquinaria propia, contratista) puede expresarse en pesos y en dólares. El costo de contratista se dolariza con el dólar vendedor BNA de la fecha de la factura del contratista vinculada (mismo criterio que Remitos); el costo de insumo ya viene dolarizado desde el FIFO de Remitos; el costo de maquinaria propia, cargado a mano, se dolariza con el dólar vendedor BNA de la fecha de ejecución de la orden.
- **FR-015** El costo acumulado de un Cultivo/Campaña no tiene fecha de cierre: sigue sumando costos de órdenes de trabajo posteriores a la cosecha sin necesidad de reabrir ningún período.
- **FR-016** Una orden sin cultivo específico (mantenimiento general) se imputa a Rubro y Centro de Costos, sin pasar por Cultivo/Campaña.
- **FR-017** Toda escritura va exclusivamente contra `WC`; las tablas y vistas heredadas no se modifican, solo se leen o se reemplazan por consultas propias cuando su convención (ej. de signo) no sea confiable.
- **FR-018** Formato numérico y monetario del sistema (miles `.`, decimales `,`, `$` / `us$`).
- **FR-019** Exportación a Excel de: listado de órdenes, Formulario de Retiro, y costo por Cultivo/Campaña, con los filtros aplicados.

### Key Entities

- **Orden de Trabajo**: cabecera de una labor planificada/ejecutada — fecha de pedido, fecha de ejecución, tipo de labor, contratista o maquinaria propia, estado (Planificada/Ejecutada/Anulada), motivo de anulación.
- **Formulario de Retiro**: documento con numeración secuencial propia, emitido al guardar una orden, con el listado de insumos a preparar.
- **Renglón de insumo**: un insumo y su cantidad total a retirar dentro de una orden, vinculado al costeo FIFO de Remitos.
- **Renglón de distribución**: el reparto de un renglón de insumo (o de un costo de maquinaria/contratista) entre un Lote, su Cultivo y su Campaña, con la dosis por hectárea aplicada.
- **Lote de la orden**: cada lote incluido en la orden, con su superficie y si finalmente fue aplicado o no.
- **Devolución**: cantidad de un insumo retirado que no se usó y vuelve al stock, vinculada a la orden.
- **Costo de maquinaria propia**: costo por hectárea de una máquina propia usada en una orden, cargado a mano en esa orden (sin tarifa persistente), en pesos y dólares.
- **Contratista**: un `Contacto` marcado como contratista de labores, con su factura vinculada a la orden.
- **Tipo de Labor**: catálogo administrable de labores agrícolas (siembra, pulverización, fertilización, etc.).

## Success Criteria

- **SC-001**: Un usuario puede planificar una orden con varios lotes de distintos cultivos/campañas y obtener el Formulario de Retiro en menos de 5 minutos.
- **SC-002**: El total retirado de cada insumo de una orden cierra exactamente contra lo repartido más lo devuelto en el 100% de las órdenes nuevas (0% de diferencias sin explicar, contra el 1,6% que tenía el dato heredado).
- **SC-003**: El costo total de un Cultivo/Campaña (insumos + maquinaria propia + contratistas) puede consultarse sin necesidad de cerrar ni reabrir ningún período, incluyendo costos posteriores a la fecha de cosecha.
- **SC-004**: El 100% de las anulaciones de orden devuelve correctamente las capas de stock consumidas, verificable contra el saldo de existencias.

## Assumptions

- Los 153 registros heredados de `Ordenes`/`Ordenes_Detalles`/`Ordenes_Detalles_Distrib`/`Ordenes_Lotes` se migran tal cual (mismo criterio que Remitos), unificando unidades (`LTS`/`LITROS`, `KGS`/`KILOS`) y descartando la columna `Contratista` en favor de `IdContratistaContacto`.
- Las 13 diferencias heredadas entre `Total Aplicado` y lo distribuido se migran como están (dato histórico, no se corrige retroactivamente) y quedan marcadas para revisión, igual que se hizo con los duplicados de Remitos.
- El lote `PRUE` y las órdenes que eventualmente lo usaran (ninguna, según el relevamiento) se excluyen de la migración.
- Para maquinaria propia (sin factura asociada, costo cargado a mano), la dolarización usa el dólar vendedor BNA de la fecha de ejecución de la orden, a falta de una fecha de factura de la que tomarlo.
- La planilla heredada `Labores Maquinaria propia` no se migra como catálogo de tarifas: el costo de maquinaria propia se carga a mano en cada orden nueva; los datos heredados quedan como referencia histórica, sin vínculo automático a `Ordenes`.

- No hay roles ni permisos diferenciados por acción (crear/ejecutar/anular): cualquier usuario del sistema puede hacer cualquiera de las tres, igual que en el resto de los módulos ya migrados. Se revisará si el sistema pasa a ser multiusuario con permisos propios.

## Fuera de alcance de este módulo

- **Mano de obra propia** (jornales de empleados/cuadrillas): no se registra ni se costea en este módulo.
- **Trazabilidad fitosanitaria formal** (recetas agronómicas, condiciones climáticas de aplicación, cumplimiento BPA/SENASA): el registro normal de dosis, producto, lote y fecha queda disponible, pero no se modela como un requisito de cumplimiento explícito.
- **Tablero de planificación tipo calendario/kanban** de labores: queda para una eventual mejora de UX posterior.
- **Alertas de vencimiento de insumos, kardex valorizado y auditoría de quién/cuándo**: mismo alcance excluido que dejó Remitos (010).
