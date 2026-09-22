# Implementation Plan: Resultado y Costos de Cultivo

**Branch**: `012-resultado-costos-cultivo` | **Date**: 2026-09-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/012-resultado-costos-cultivo/spec.md`

## Summary

Módulo de solo lectura que consolida, por Campaña (pantalla de entrada) y por Cultivo dentro de una Campaña (drill-down), el resultado económico completo: superficie sembrada/cosechada, rinde, costo total (heredado + Órdenes de Trabajo de 011), venta neta, margen bruto y rentabilidad, en pesos y en dólares. Reemplaza la vista parcial de costo por Cultivo/Campaña que hoy vive dentro de Órdenes de Trabajo. Se calcula en vivo en cada consulta (no existe caché heredado utilizable: `ResultadoCultivo_Resumen` y su vista `vw_ResultadoCultivo_Resumen` están vacías) combinando vistas heredadas de costeo/venta con las tablas nuevas de 011, traduciendo Cultivo → Destino/Grano vía `Map_CultivoResultado` y Campaña (texto) → `IdCampaña` vía la tabla `Campañas`.

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript / Next.js (frontend) — mismo stack que el resto del sistema.

**Primary Dependencies**: FastAPI (backend), Next.js + TanStack Query + Tailwind CSS (frontend); `pyodbc`/conexión SQL Server ya existente en `backend/src/db/connection.py`; reutiliza `backend/src/features/ordenes/repository.py` (lectura de `Ordenes_Trabajo_*`) y `backend/src/features/ordenes/exportacion.py` como patrón de exportación multi-hoja, sin modificarlos.

**Storage**: SQL Server, base `WC` exclusivamente. Módulo 100% de solo lectura (FR-013): no crea, actualiza ni elimina ninguna fila. Fuentes heredadas de solo lectura: `vw_ResultadoCultivo_Campaña`, `vw_ResultadosCultivo_CostosBase`, `vw_ResultadosCultivo_CostosAgrupados`, `vw_ResultadosCultivo_Deducciones`, `vw_ResultadosCultivo_Seguros`, `vw_ResultadosCultivo_Ventas`, `Map_CultivoResultado`, `Campañas`, `ResultadoCultivo_Cierre`. Fuentes nuevas ya existentes (011/PlanAgricola), también de solo lectura desde este módulo: `Ordenes_Trabajo_Insumos`, `Ordenes_Trabajo_Maquinaria`, `Ordenes_Trabajo_Contratista_Factura`, `PlanAgricola`.

**Testing**: pytest para backend (funciones de cálculo con datos mockeados/fixtures, sin escribir en `WC`; consultas SELECT reales solo para verificación manual como en 011), verificación de compilación TypeScript/Next build para frontend — mismo patrón que 010/011.

**Target Platform**: Aplicación web interna (oficina), perfil de usuario predominante **Dirección/socio** para la pantalla de entrada (Historia 1/2, tarjetas de KPI) y **Administración/auditoría** para el drill-down de costos (Historia 3/4, tabla densa) — ver spec.md, revisión de `09-agroux-lead-product-architect`.

**Project Type**: Web application (backend FastAPI + frontend Next.js), feature dentro del monorepo existente.

**Performance Goals**: Uso interno, sin metas de throughput; SC-001 exige que la primera pantalla (consolidado de Campaña) responda en menos de 10 segundos. Alcance de datos acotado (≤33 campañas, ≤11 cultivos → ≤363 combinaciones posibles, muchas menos con datos reales), sin necesidad de paginación ni de índices nuevos.

**Constraints**: Toda lectura exclusivamente contra `WC`; ninguna escritura (FR-013); no modificar ninguna vista/tabla heredada; evitar doble conteo entre `Ordenes_Trabajo_Contratista_Factura.IdCompra` y `vw_ResultadosCultivo_CostosBase` (FR-004); traducir `Cultivo` a dos claves heredadas distintas (`IdDestino` para costeo, `IdGrano` para venta) vía `Map_CultivoResultado`, nunca asumir que son intercambiables.

**Scale/Scope**: Alcance funcional: 4 historias de usuario (spec.md), 2 en P1 (consolidado de Campaña, resultado por Cultivo) y 2 en P2 (detalle de costos, exportar Excel). Fuentes de datos reales confirmadas: 29 campañas con costos base cargados, 233 filas en `PlanAgricola` (superficie sembrada real por Cultivo/Campaña, ya construida en 011), 43 filas en `ResultadoCultivo_Cierre` (superficie cosechada, mayormente auto-estimada).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Cumplimiento |
|---|---|
| I. SQL Server es el sistema de registro | ✅ Toda la lectura pasa por el backend Python existente contra `WC`; no se usa Access ni `.accdb`. |
| II. Protección de datos reales | ✅ Módulo 100% de solo lectura — no hay fase de escritura ni migración que autorizar. |
| III. Procesos de negocio, no tablas crudas | ✅ La pantalla sigue el proceso real de Dirección: ver el resultado de la Campaña → bajar a un Cultivo puntual → auditar el detalle de costos, no un CRUD ni un volcado de vistas. |
| IV. Trazabilidad y significado financiero explícito | ✅ Cada línea de costo expone su origen (`IdCompra`/`IdDetalleCompra` o la Orden de Trabajo, con link) y su moneda/TC histórico, sin ocultar montos sin clasificar (FR-012). |
| V. Contrato SQL/API primero, con pruebas | ✅ `data-model.md` y `contracts/` se definen antes de UI; funciones de cálculo (traducción Cultivo→Destino/Grano, reparto, umbrales) con tests unitarios antes de exponerlas por API. |
| VI. Colaboración de especialistas | ✅ Ya ejecutada: 3 preguntas de clarificación inicial + revisión de 4 agentes especialistas (`01-sql-server-engineer`, `05-agricultural-production-specialist`, `07-financial-direction-specialist`, `09-agroux-lead-product-architect`) + 2 preguntas de `/speckit-clarify`, todas resueltas en `spec.md`. |
| VII. Simplicidad y reversibilidad | ✅ Reutiliza vistas heredadas y las tablas nuevas de 011 tal cual, sin tabla propia nueva (el cálculo es 100% en vivo, sin caché); retira la vista parcial de 011 en vez de mantener dos fuentes de verdad. |
| VIII. Stack aprobado | ✅ Python/FastAPI + SQL Server + Next.js/TypeScript/Tailwind/TanStack Query, sin introducir otra tecnología. |

Sin violaciones. No aplica Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/012-resultado-costos-cultivo/
├── plan.md              # Este archivo
├── research.md          # Fase 0
├── data-model.md         # Fase 1
├── quickstart.md         # Fase 1
├── contracts/            # Fase 1 (contrato de API)
└── tasks.md              # Fase 2 (/speckit-tasks, no generado por /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── src/features/resultado_cultivo/
│   ├── __init__.py
│   ├── mapeo.py          # Traducción Cultivo→IdDestino/IdGrano (Map_CultivoResultado) y Campaña texto↔IdCampaña (ambos sentidos, ver research.md §3-4)
│   ├── campania_actual.py # Cálculo de la Campaña "actual" según la fecha de hoy (FR-001), con resguardo
│   ├── costos.py          # Combina CostosBase/CostosAgrupados/Seguros + costo de Ordenes_Trabajo_*, anti-doble-conteo (FR-004)
│   ├── resultado.py       # Superficie (PlanAgricola + ResultadoCultivo_Cierre), rinde, venta, margen, rentabilidad por Cultivo/Campaña y consolidado de Campaña
│   ├── exportacion.py     # Export a Excel de 2 hojas (Resultado + Detalle de costos), sigue el patrón de ordenes/exportacion.py
│   └── router.py          # Endpoints /api/resultado-cultivo
├── src/main.py              # Registrar resultado_cultivo_router
└── tests/
    ├── test_resultado_cultivo_mapeo.py
    ├── test_resultado_cultivo_campania_actual.py
    ├── test_resultado_cultivo_costos.py
    └── test_resultado_cultivo_resultado.py

frontend/src/
├── app/produccion/resultado-cultivo/
│   ├── page.tsx                          # Historia 1: consolidado de Campaña (pantalla de entrada)
│   └── [idCampania]/[idCultivo]/page.tsx # Historia 2/3: resultado + detalle de costos de un Cultivo puntual
├── components/resultado-cultivo/
│   ├── ConsolidadoCampaniaView.tsx        # Tarjetas KPI + tabla resumen por Cultivo
│   ├── ResultadoCultivoView.tsx           # Tarjetas KPI de un Cultivo puntual
│   ├── DetalleCostosPanel.tsx             # Tabla densa por concepto, con link "Ver orden"
│   ├── SelectorCampania.tsx               # Selector de Campaña, preselecciona la "actual"
│   └── SelectorCultivo.tsx                # Filtro directo Cultivo (FR-002, segundo camino de acceso además del clic en la tabla resumen)
├── services/resultadoCultivoApi.ts
└── components/layout/NavHeader.tsx         # Agregar "Resultado de Cultivo" al submenú Producción; retirar la entrada de la vista parcial de 011
```

**Structure Decision**: Módulo hermano de `ordenes/`, mismo patrón de `backend/src/features/<módulo>/` + `frontend/src/{app,components}/.../<módulo>/` ya validado en 010/011. No hay tablas nuevas ni scripts de migración — todo el cálculo es en vivo sobre datos existentes, así que no hay fase de escritura/backup que coordinar (a diferencia de 010/011). La vista parcial `/produccion/ordenes/resultado-cultivo` (011) se retira como último paso de implementación (FR-015), una vez que este módulo cubre el mismo caso de uso y más.


**Decisión del usuario (2026-09-22)**: los costos sin clasificar se muestran aparte, sin sumarlos al costo total de la campaña ni afectar su margen, rentabilidad o costo por hectárea. El total consolidado es la suma de los cultivos. El importe informativo incluye destinos sin cultivo de la campaña consultada y costos sin campaña asignada de todo el sistema; estos últimos no se atribuyen a la campaña seleccionada.


## Aclaración de costeo aplicada — 2026-09-22

El usuario aclaró que el contratista se costea por su factura y la maquinaria propia por el estimado por hectárea ingresado manualmente en su formulario. En 012, las facturas vinculadas se toman por sus renglones de `Det_Compras`, con el destino y la campaña registrados; no se reparten por superficie ni por cantidad de insumos. Una factura que ya aparece en CostosBase no vuelve a sumarse por la orden. Los identificadores de factura y renglón se conservan en el detalle. Vincular la misma factura a varias órdenes no multiplica sus renglones; se muestra como referencia la primera orden vigente vinculada.

Maquinaria propia nueva: se usa `CostoPorHectarea` manual y la superficie registrada del lote de la orden, una vez por lote (máxima superficie registrada para ese lote dentro del cultivo/campaña cuando se repite entre insumos). No hay tarifa calculada ni catálogo de tarifas. `TipoCambioBna`, cuando fue registrado, permite expresar ese estimado en dólares; si falta, el detalle no inventa conversión. La maquinaria heredada conserva los importes de su formulario incluidos en CostosBase y se identifica como `MaquinariaPropia`.

Verificación del SQL real: CostosBase ya firma `Pesos` y `Dolares` en notas de crédito. Se normaliza `ABS(importe) × Signo`, evitando volver a convertir el crédito en cargo. Esta corrección reemplaza cualquier indicación previa de multiplicar directamente el importe firmado por Signo.

El motor FIFO existente entrega los costos de insumos de órdenes en pesos. La serie en dólares de esos insumos no está reconstruida en este corte; no se debe interpretar su cero actual como una conversión validada. Esta limitación debe resolverse antes de considerar completos los indicadores en dólares cuando incluyen esas órdenes.
