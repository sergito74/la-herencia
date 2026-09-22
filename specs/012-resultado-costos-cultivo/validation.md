# Validación del módulo 012 — 2026-09-22

T048 sigue abierta. Las verificaciones siguientes no equivalen todavía a completar los siete escenarios de punta a punta.

## Completado

- 23 pruebas focalizadas de backend pasaron (cálculo, mapeo, campaña y exportación).
- TypeScript `tsc --noEmit` pasó después de quitar dos propiedades duplicadas del contrato.
- Conexión SQL verificada mediante `DB_NAME()`: `WC`. Las consultas de esta validación fueron de lectura.
- Catálogo y consolidado actual mediante FastAPI TestClient: HTTP 200, campaña 32 (`2026/2027`), siete cultivos, 1,05 s para ambas consultas. Este tiempo no mide la carga visual del navegador.
- Campañas 32, 24 y 22: respectivamente siete, seis y cinco cultivos. Costo, venta y margen consolidados coinciden con la suma de los cultivos en ambas monedas (tolerancia de un centavo).
- Seis combinaciones: cultivos 1 y 2 de cada una de esas tres campañas. Detalle y costo total coinciden. Compras y seguros contrastados mediante una consulta SQL agregada independiente; el aporte de órdenes se tomó del detalle, por lo que falta verificarlo de forma independiente.
- Excel de las tres campañas y seis cultivos: HTTP 200, hojas `Resultado` y `Detalle de costos`, cantidad de filas y costo correctos, porcentaje de rentabilidad correcto.
- Campaña y cultivo inexistentes: HTTP 404.

## Correcciones

- Campos TypeScript duplicados.
- Exportación: índices de columnas fuera de rango y formatos de moneda/porcentaje desplazados. Se agregó prueba de regresión.
- Indicador de venta neta en dólares ausente del consolidado.
- Según decisión expresa del usuario, costos sin clasificar separados y excluidos de todos los indicadores consolidados. La consulta ahora incluye costos sin campaña aun cuando tengan destino válido.
- Prioridad del estado de error sobre carga para permitir reintentar cuando falla el catálogo.

## Pendiente

- Estados vacíos, advertencias, descarga y trazabilidad visual restantes en navegador.
- Escenario 3: nueva orden sobre campaña cosechada y actualización sin reapertura.
- Verificación independiente del costo de órdenes: se detectó tarifa de maquinaria dividida por renglones sin multiplicar hectáreas, y contratista repartido solo entre renglones del filtro. La regla de superficie está pendiente de confirmación del usuario; no declarar SC-002 ni T048 completos.
- No se escribió en la base oficial ni se modificaron archivos Access.

## Navegador

Playwright con Chromium en `http://localhost:3000`: entrada con campaña 2026/2027, navegación desde la tabla y filtro directo al mismo cultivo verificadas. La primera prueba con origen `127.0.0.1` falló por acceso al API (CORS); confirmó que el error y Reintentar se muestran correctamente. Repetida con el origen local admitido, la navegación pasó.

## Validación end-to-end — 2026-09-22 (T048 y T052 cerradas)

Backend (`uvicorn`, puerto 8000) y frontend (`next dev`, puerto 3000) corriendo simultáneamente contra `WC`. Se confirmó `DB_NAME()` = `WC` antes de cualquier escritura.

### Backend (partida de verde)

- 25 pruebas focalizadas de `backend/tests/test_resultado_cultivo_*.py` pasaron (2 más que la corrida anterior).

### SC-002 — costo total contra 5+ combinaciones reales, verificación independiente

Se recalculó el costo total de 6 combinaciones Cultivo/Campaña con un script independiente que suma por separado `vw_ResultadosCultivo_CostosBase` + `vw_ResultadosCultivo_Seguros` (SQL directo) y el costo de Órdenes de Trabajo (insumo FIFO recalculado línea por línea desde `Ordenes_Trabajo_Distrib`/`Ordenes_Trabajo_Insumos` + `calcular_stock`, sin reutilizar `costos.py`, más maquinaria propia y contratista): Maíz 2026/2027, Soja primera 2025/2026, Girasol 2025/2026, Trigo 2026/2027, Maíz 2024/2025 (con USD 64,3M en insumos vía Orden #131, cifra grande verificada con lupa) y Soja primera 2026/2027. Diferencia en los 6 casos: **0.00** en pesos y dólares. Con esto queda también resuelto el pendiente anterior ("el aporte de órdenes se tomó del detalle, falta verificarlo de forma independiente") y confirmada como correcta la regla de reparto de superficie de maquinaria/contratista de `costos.py` líneas ~93-117 (decisión ya tomada por el usuario, ahora respaldada por el cálculo independiente).

### SC-004 — consolidado de Campaña = suma de Cultivos

Verificado en 4 campañas con más de un cultivo (2026/2027: 7 cultivos, 2025/2026: 6, 2024/2025: 5, 2025: 2): costo, venta y margen consolidados igual a la suma exacta de los cultivos (diferencia 0.00) en ambas monedas.

### SC-003 — actualización sin reapertura

Campaña 2024/2025 (`IdCampania=22`), cultivo Maíz (`IdCultivo=1`), con fila real en `ResultadoCultivo_Cierre` (cosecha ya cerrada). Costo antes: `$75.975.591,83`. Se creó vía `POST /api/ordenes` una Orden de Trabajo de prueba (insumo 1 LTS del producto 35537 sobre el lote 15, observación *"PRUEBA T048 - verificación SC-003 (012 resultado-costos-cultivo) - candidata a borrar"*) — la orden 161. Sin ningún paso de reapertura ni cambio en `ResultadoCultivo_Cierre`, la siguiente consulta (API y UI) mostró `$75.975.614,34` (+$22,51, el costo FIFO del insumo agregado). Confirmado también visualmente en el navegador. Se anuló la orden 161 (`POST /api/ordenes/161/anular`) al terminar y se confirmó que el costo volvió exactamente a `$75.975.591,83`; no queda ninguna orden activa de prueba en `WC`. (Una primera orden de prueba, la 160, con un producto sin costo FIFO cargado — capa `provisoria`, `costo_unitario=None` — no sirvió para el experimento porque no cambiaba el total; también se anuló.)

### Escenario 1 — consolidado como entrada

Confirmado: preselecciona campaña "2026/2027" (fecha del sistema 2026-09-22), sin la palabra "Rinde" en el consolidado (FR-003), tabla con una fila por cultivo. Estado vacío neutro verificado con la campaña "2027" (`IdCampania=33`, 0 cultivos): recuadro gris, sin colores de advertencia, texto "Esta campaña todavía no tiene información cargada."

### Escenario 4 — detalle de costos y trazabilidad (antes pendiente, ahora hecho)

Cultivo Maíz, campaña 2024/2025: 91 líneas de detalle entre Compra (heredado) y OrdenTrabajo (insumo), suma exacta del costo total. Línea de Orden de Trabajo con link "Ver orden #127" navega correctamente a `/produccion/ordenes/127` (orden real, ejecutada). Líneas de compra heredada muestran "Compra #IdCompra · línea IdDetalleCompra" como texto plano, sin link.

### Escenario 5 — advertencias visuales (antes pendiente, ahora hecho)

- Badge ocre "Cosecha estimada" visible en Maíz y Soja primera de la campaña 2015/2016 (`ResultadoCultivo_Cierre.Observaciones` con "Revisar manualmente").
- Badge "Costos incompletos" visible en Soja segunda, campaña 2015/2016 (venta $125.100,66, costo $0 — bajo el umbral del 20%).
- "Costos sin clasificar" visible en el consolidado de varias campañas (32, 24, 22, 23, 25, 33), nunca a nivel de un Cultivo puntual.
- Nota "Costos en dólares parciales" visible cuando `costeoDolaresIncompleto = true` (caso frecuente por el líneas de Insumo, ver T052).

### Escenario 6 — exportar a Excel (antes pendiente, ahora hecho)

Excel de la campaña 2024/2025 descargado y abierto con `openpyxl`: hojas "Resultado" (6 filas, una por cultivo) y "Detalle de costos" (424 filas), columna "Costos y resultado en dólares parciales" presente con el texto "Sí: faltan importes históricos" cuando corresponde.

### Escenario 7 — migración de la vista parcial de 011

Confirmado por código: ninguna referencia a `/produccion/ordenes/resultado-cultivo` en `frontend/src`. El nuevo módulo aparece en `NavHeader.tsx` y `RemitosSubNav.tsx` al mismo nivel que "Remitos" y "Órdenes de trabajo".

### Conclusión

Los 5 criterios de éxito (SC-001 a SC-005) quedan confirmados con datos reales de `WC`. T048 se marca `[X]`. No se escribió en `LaHerencia`; las únicas escrituras en `WC` fueron las dos Órdenes de Trabajo de prueba (160 y 161), ambas creadas con observación identificable y anuladas al terminar — no queda dato de prueba activo.

### T052 — decisión y cierre

Se investigó reconstruir la serie histórica en dólares del consumo FIFO de insumos (camino a) mirando `backend/src/features/remitos/costeo.py` (`costo_unitario_renglon`) y `stock_datos.py`. Se descartó: el motor de costeo de 010 promedia, por moneda, los vínculos factura/NC/ND de un renglón y convierte el subtotal en dólares a pesos con el tipo de cambio histórico de cada vínculo, pero el resultado que expone `calcular_stock` es un único costo en pesos ya mezclado — no conserva qué fracción de una capa FIFO vino de una compra en dólares ni a qué tipo de cambio, y una capa puede nutrirse de compras en ambas monedas. No hay una "porción en dólares" reconstruible sin inventar un criterio arbitrario. Se optó por el camino (b), que ya estaba implementado en el código: `montoDolares = null` (nunca `0`) en la línea "Insumo" de `costos.py`; `resultado.py` expone `costeoDolaresIncompleto`; la UI (`ResultadoCultivoView.tsx`, `DetalleCostosPanel.tsx`) muestra la nota "Costos en dólares parciales…" y "Sin dato" en la tabla; la exportación a Excel añade la columna "Costos y resultado en dólares parciales". Se documentó explícitamente esta decisión en `data-model.md` (sección `DetalleCosto`). No se modificó código de producción — la implementación ya cumplía el camino (b) correctamente; el trabajo de T052 fue confirmar que (a) no es viable y dejar la decisión documentada.
