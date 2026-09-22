# Research: Órdenes de Trabajo (011)

No quedan `NEEDS CLARIFICATION` en el Technical Context del plan — todas las decisiones de negocio ya se resolvieron en `spec.md` (30 preguntas + 4 de clarificación). Este documento resuelve las decisiones técnicas necesarias para el diseño (Fase 1).

## 1. Reutilización del costeo FIFO de Remitos

- **Decisión**: `ordenes/costeo.py` importa directamente las funciones de `remitos/stock_fifo.py` y `remitos/stock_datos.py` (no se copian ni se reescriben). El consumo de un renglón de insumo de una orden se registra como una salida más del mismo motor FIFO que ya usan los consumos heredados y las bajas de stock de Remitos.
- **Rationale**: Es un requisito explícito de la spec (FR-001) y evita mantener dos implementaciones de FIFO. `stock_fifo.py` ya está probado (`test_stock_fifo.py`) y su cálculo coincide exactamente con `vw_ExistenciaProductos` (0 diferencias en 40 productos, según 010-remitos).
- **Alternativas consideradas**: Reimplementar FIFO específico para órdenes — descartado, viola el Principio VII (simplicidad) y duplicaría lógica ya validada.

## 2. Vistas heredadas de costeo por Cultivo/Campaña

- **Decisión**: `ordenes/resultado.py` consulta `vw_ResultadoCultivo_Campaña`, `vw_Costos_BaseLineas` y `vw_ResultadosCultivo_CostosBase/CostosAgrupados` tal como están, sumándoles el costo de las órdenes de trabajo nuevas (que hoy esas vistas heredadas no conocen, porque `DetCompra_OT` está vacía). No se modifican esas vistas.
- **Rationale**: Principio I y VII: son datos/lógica heredada ya en producción para otros costos (compras, seguros, comercialización); el módulo nuevo se conecta, no reemplaza.
- **Riesgo identificado**: `vw_Cns_TotalesOrdenesPorProducto` devuelve el consumo con signo negativo; antes de reutilizarla hay que confirmar esa convención con una consulta de verificación (Fase 1, no bloqueante: se puede calcular el consumo directamente desde las tablas nuevas si el signo no es confiable, igual que Remitos hizo con `vw_ExistenciaProductos`).
- **Alternativas consideradas**: Construir un motor de costeo por cultivo enteramente nuevo — descartado, es explícitamente fuera de alcance rehacer lo que ya funciona para compras/seguros/comercialización.

## 3. Numeración del Formulario de Retiro

- **Decisión**: Tabla nueva `Formularios_Retiro` con una columna identity propia (numeración secuencial independiente del `IdOrden`), 1 a 1 con la orden que lo generó.
- **Rationale**: Resuelto explícitamente en la clarificación (opción A): numeración propia, no reutiliza el número de orden.
- **Alternativas consideradas**: Usar `IdOrden` como número de documento — descartado por decisión explícita del usuario.

## 4. Costo de maquinaria propia

- **Decisión**: Sin catálogo de tarifas por máquina. El costo por hectárea se carga como un campo numérico manual en el renglón de maquinaria de cada orden (tabla nueva `Ordenes_Maquinaria`), en pesos, con dolarización al dólar BNA vendedor de la fecha de ejecución de la orden (no hay factura de la que tomar el TC).
- **Rationale**: Resuelto explícitamente en la clarificación (opción B). La planilla heredada `Labores Maquinaria propia` no se migra como catálogo activo; queda como referencia histórica sin vínculo automático.
- **Alternativas consideradas**: Catálogo de máquinas con tarifa vigente (opción A) — descartado por el usuario para el primer corte; se puede agregar después sin romper el modelo (el campo manual seguiría existiendo como override).

## 5. Costo de contratista y tipo de cambio

- **Decisión**: El costo de contratista se toma de la factura de Compras vinculada a la orden (mismo patrón que el vínculo remito↔factura de 010-remitos, pero orden↔factura). La dolarización usa el dólar BNA vendedor de la fecha de esa factura.
- **Rationale**: Resuelto explícitamente en la clarificación (opción A), consistente con el criterio ya usado en Remitos para insumos.
- **Fuente del tipo de cambio**: confirmado en `backend/src/features/remitos/costeo.py` (líneas 62-73) que el TC de una factura en dólares ya viene como columna `tipoDeCambio` en el propio registro de compra/factura — no hay un servicio de cotización aparte. El costo de contratista reutiliza ese mismo campo de su factura vinculada; solo el costo de maquinaria propia (sin factura) necesita una fuente de dólar BNA vendedor independiente por fecha. Se relevó el resto del sistema (`tarjetas`, `cuentas_corrientes`) y no existe hoy una tabla de cotizaciones histórica reutilizable — se resuelve con un campo manual de TC en el renglón de maquinaria de cada orden (mismo criterio "carga a mano" ya decidido para el costo en sí), documentado como `data-model.md` lo define.

## 6. Regla de cierre exacto (FR-004)

- **Decisión**: Validación en `distribucion.py` que se ejecuta al guardar una orden y al registrar una devolución: `suma(CantidadAsignada de los renglones de distribución) + suma(devoluciones del renglón) == Total del renglón de insumo`. Si no cierra, se rechaza con un mensaje claro (no es una advertencia opcional, es un requisito duro nuevo, a diferencia del dato heredado).
- **Rationale**: FR-004/SC-002, decisión explícita del usuario ("deben coincidir siempre").
- **Alternativas consideradas**: Permitir diferencia y marcarla para revisión (como se hizo con duplicados de Remitos) — descartado, el usuario pidió expresamente que nunca quede una diferencia sin explicar.

## 7. Migración de datos heredados

- **Decisión**: Migrar los 153 registros de `Ordenes`/`Ordenes_Detalles`/`Ordenes_Detalles_Distrib`/`Ordenes_Lotes` tal cual (mismo criterio que Remitos), unificando unidades (`LTS`/`LITROS`→`LTS`, `KGS`/`KILOS`→`KGS`) contra la tabla `Unidades_Medida` ya creada por 010-remitos, descartando la columna `Contratista` (se usa solo `IdContratistaContacto`), excluyendo el lote `PRUE`, y marcando para revisión los 13 renglones históricos donde `Total Aplicado` no cierra contra lo distribuido (no se corrigen retroactivamente).
- **Rationale**: Mismo patrón ya validado en `backend/scripts/migrar_remitos.py` (idempotente, sin alterar tablas heredadas, con banderas de revisión para inconsistencias históricas en vez de "arreglarlas" silenciosamente).
- **Estado de la orden migrado**: `Ejecutada` si tiene fecha de ejecución, `Planificada` si no (4 casos: órdenes 185, 182, 127, 123).

## 8. Integración con el nav y submenú Producción

- **Decisión**: Agregar "Órdenes de Trabajo" como cuarto ítem del submenú Producción (junto a Remitos, Stock), reutilizando `RemitosSubNav.tsx` como referencia de patrón para un nuevo `OrdenesSubNav.tsx` o extendiendo el componente existente si el árbol de navegación lo permite sin acoplar módulos.
- **Rationale**: Consistencia de UX ya validada por el arquitecto de producto en la sesión de preguntas.
