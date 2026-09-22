# Quickstart: validar Resultado y Costos de Cultivo (012)

## Prerrequisitos

- Backend y frontend corriendo igual que para Órdenes de Trabajo (ver `specs/011-ordenes-trabajo/quickstart.md`).
- Conexión de solo lectura a `WC` — este módulo no escribe nada, no hace falta backup ni autorización previa.

## Escenario 1 — Consolidado de Campaña como pantalla de entrada

1. Entrar al módulo sin elegir nada. Verificar que preselecciona la Campaña "actual" según la fecha de hoy (`research.md` §5) — hoy (2026-09-22) debería ser "2026/2027".
2. Verificar que se ven tarjetas KPI (superficie, costo, costo/ha, venta, margen, rentabilidad en pesos y dólares — **sin rinde**, que no se consolida entre Cultivos distintos, FR-003) y una tabla con una fila por Cultivo.
3. Cambiar a una Campaña sin ningún dato cargado y verificar el estado vacío neutro (sin colores de advertencia).

**Resultado esperado**: SC-001 (menos de 10 segundos), FR-001, FR-009.

## Escenario 2 — Drill-down a un Cultivo puntual

1. Desde la tabla resumen de la Campaña, hacer clic en una fila (ej. "Soja primera"). Verificar también el segundo camino: usar el filtro directo de Cultivo (`SelectorCultivo`) y llegar al mismo resultado.
2. Verificar que se ven los mismos indicadores pero acotados a ese Cultivo: superficie sembrada (vía `PlanAgricola`), rinde, costo total, costo/ha, venta neta, margen bruto, rentabilidad.
3. Verificar contra los datos reales: sumar a mano `vw_ResultadosCultivo_CostosBase` + `Seguros` + costo de `Ordenes_Trabajo_*` de ese Cultivo/Campaña y comparar con el costo total mostrado (diferencia menor al redondeo de centavos). Repetir en **al menos 5 combinaciones** Cultivo/Campaña reales distintas (SC-002 exige verificación contra 5 combinaciones, no una sola).

**Resultado esperado**: SC-002, FR-002, FR-003.

## Escenario 3 — Consistencia del consolidado y actualización sin reapertura

1. Elegir una Campaña con al menos 2 Cultivos con datos. Repetir la comparación en **al menos 3 campañas reales** con más de un cultivo (SC-004).
2. Sumar a mano el costo/venta/margen de cada Cultivo (Escenario 2) y compararlo con el consolidado de la Campaña (Escenario 1).
3. Sobre una Campaña ya cosechada (con fila en `ResultadoCultivo_Cierre`), cargar una Orden de Trabajo nueva de un Cultivo de esa Campaña (módulo 011) y volver a consultar el resultado de ese Cultivo/Campaña — verificar que el costo se actualiza en la siguiente consulta, sin ningún paso de "reapertura" (SC-003, spec.md Historia 2 Acceptance Scenario 2).

**Resultado esperado**: SC-003, SC-004, FR-005, FR-014 (deben coincidir exactamente).

## Escenario 4 — Detalle de costos y trazabilidad

1. Sobre un Cultivo/Campaña con costos de varias fuentes, abrir el detalle de costos.
2. Verificar que la suma de las líneas coincide con el costo total del Escenario 2.
3. Verificar que una línea originada en una Orden de Trabajo tiene el link "Ver orden" y navega correctamente a `/produccion/ordenes/[idOrden]`.
4. Verificar que una línea originada en una compra heredada muestra su `IdCompra`/`IdDetalleCompra` como texto (sin link, ver `research.md` §8).

**Resultado esperado**: FR-007, Historia 3.

## Escenario 5 — Advertencias visuales

1. Buscar (o simular con datos de prueba) un Cultivo/Campaña con venta registrada y costo total menor al 20% de la venta neta.
2. Verificar el badge de advertencia "costos incompletos — margen no representativo" (FR-011).
3. Buscar un Cultivo/Campaña cuya fila en `ResultadoCultivo_Cierre` tenga `Observaciones` de estimación automática (41 de 43 filas reales tienen "Revisar manualmente") y verificar el badge ocre "superficie cosechada estimada — revisar" (FR-010, corregido en `/speckit-analyze` — ya no depende de un `IdDestino` huérfano, que nunca ocurre a nivel de un Cultivo real).
4. Buscar un `IdDestino` huérfano (sin fila en `Map_CultivoResultado`, 7 de 17 casos reales) y verificar que su costo aparece como "sin clasificar" en el **consolidado de Campaña** (Escenario 1), no como un badge sobre un Cultivo puntual (FR-012).

**Resultado esperado**: FR-010, FR-011, FR-012, Edge Cases de `spec.md`.

## Escenario 6 — Exportar a Excel

1. Exportar el resultado de una Campaña completa.
2. Verificar que el `.xlsx` tiene 2 hojas: "Resultado" (una fila por Cultivo) y "Detalle de costos".

**Resultado esperado**: FR-008, Historia 4.

## Escenario 7 — Migración de la vista parcial de 011

1. Verificar que `/produccion/ordenes/resultado-cultivo` (la vista parcial de 011) ya no aparece en el menú de Órdenes de Trabajo.
2. Verificar que el nuevo módulo aparece en el menú de Producción, al mismo nivel que Remitos y Órdenes de Trabajo.

**Resultado esperado**: FR-015.
