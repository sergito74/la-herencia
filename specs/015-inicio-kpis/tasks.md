---

description: "Task list for Inicio con indicadores reales del negocio"
---

# Tasks: Inicio con indicadores reales del negocio

**Input**: Design documents from `/specs/015-inicio-kpis/`

**Prerequisites**: plan.md, spec.md

**Tests**: sin backend nuevo — verificación manual contra los endpoints fuente (`quickstart.md`), `tsc --noEmit` como único chequeo automatizado.

## Phase 1: User Story 1 — Indicadores reales (Priority: P1)

- [X] [US1] Crear `frontend/src/components/inicio/DeudaTotalKpi.tsx`: `fetchSaldos("saldo")` (014, ya existente en `cuentasCorrientesApi.ts`), suma los `saldoParcial < 0`, muestra el total en rojo/danger (FR-001)
- [X] [US1] Crear `frontend/src/components/inicio/TarjetasPendientesKpi.tsx`: `fetchPendientes({ page: 1, pageSize: 1, ... })` (009, ya existente en `tarjetasResumenesApi.ts`) tomando `total` de la respuesta, link a `/finanzas/tarjetas/conciliacion` (FR-002)
- [X] [US1] Crear `frontend/src/components/inicio/ResultadoCampaniaKpi.tsx`: `fetchCampanias()` para obtener `campaniaActualId`, luego `fetchResultadoCampania(id)` (012, ya existente en `resultadoCultivoApi.ts`), muestra superficie/margen/rentabilidad, estado vacío si no hay campaña con datos (FR-003, FR-008), link a `/produccion/resultado-cultivo`
- [X] [US1] Cada componente maneja su propio estado de error/carga de forma aislada (try/catch de React Query por componente, sin un error boundary compartido) — verificar que un fallo en uno no rompe los otros (FR-005)

## Phase 2: User Story 2 — Contenido actualizado (Priority: P2)

- [X] [US2] Reescribir la tarjeta "Producción" de `frontend/src/app/page.tsx`: reemplazar el placeholder "próximamente" por `links` reales (Planificación agrícola, Remitos, Existencias de insumos, Órdenes de trabajo, Resultado de cultivo), mismo patrón que la tarjeta "Finanzas" (FR-006)
- [X] [US2] Agregar el link a Tarjetas (`/finanzas/tarjetas`) en los `links` de la tarjeta "Finanzas" de `page.tsx` (FR-007)

## Phase 3: Integración

- [X] Integrar los 3 componentes nuevos en `page.tsx`, junto a `CuotasArrendamientoKpis` ya existente, en una grilla de indicadores
- [X] Aplicar formato numérico y monetario del sistema (`formatMoneda`/`formatCantidad`, nunca `toLocaleString`) en los 3 componentes nuevos
- [X] Ejecutar `tsc --noEmit` y los escenarios de `quickstart.md`

## Dependencies

- US1 y US2 son independientes entre sí — pueden implementarse en cualquier orden.
- Integración depende de que existan los 3 componentes de US1 y los cambios de US2 en `page.tsx`.
