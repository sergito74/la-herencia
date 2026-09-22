---

description: "Task list for Resultado y Costos de Cultivo (012)"
---

# Tasks: Resultado y Costos de Cultivo

**Input**: Design documents from `/specs/012-resultado-costos-cultivo/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api-resultado-cultivo.md, quickstart.md

**Tests**: No se pidieron tests exhaustivos en la spec; se incluyen los tests focalizados que ya son el estándar del proyecto (constitución, Principio V) para la lógica de cálculo con mayor riesgo de error silencioso: parseo de "Campaña actual", anti-doble-conteo (FR-004) y las reglas de "—" en vez de división por cero (rinde, costo/ha).

**Organization**: Tareas agrupadas por historia de usuario (spec.md), en el orden real de dependencia funcional: US1 (consolidado de Campaña) es la pantalla de entrada y ya requiere poder calcular el resultado de cada Cultivo por debajo, así que US2 (resultado de un Cultivo puntual) se construye primero como función de backend reutilizada por US1, y su UI de drill-down se completa en la fase de US2. US3 (detalle de costos) y US4 (exportar) son extensiones independientes sobre esa base.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Puede ejecutarse en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: A qué historia de usuario pertenece (US1-US4, spec.md)

## Path Conventions

Web app existente: `backend/src/`, `frontend/src/` — mismo layout que 010-remitos y 011-ordenes-trabajo (ver `plan.md` → Project Structure).

---

## Phase 1: Setup

**Purpose**: Estructura de carpetas del módulo, sin lógica todavía

- [ ] T001 Crear el paquete `backend/src/features/resultado_cultivo/` con `__init__.py` vacío, siguiendo la estructura de `backend/src/features/ordenes/`
- [ ] T002 [P] Crear `frontend/src/app/produccion/resultado-cultivo/` (carpeta con `page.tsx` placeholder) y `frontend/src/components/resultado-cultivo/`, per `plan.md` → Project Structure
- [ ] T003 [P] Crear `frontend/src/services/resultadoCultivoApi.ts` con el cliente base (fetch/TanStack Query wrapper), siguiendo el patrón de `frontend/src/services/ordenesApi.ts`

**Checkpoint**: estructura de carpetas lista, sin funcionalidad.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Traducción de claves heredadas y cálculo de "Campaña actual" — usados por todas las historias

**⚠️ CRITICAL**: Ninguna historia puede empezar hasta que esta fase esté completa

- [ ] T004 Implementar `backend/src/features/resultado_cultivo/mapeo.py`: `idCultivo_a_destino(idCultivo) -> int | None`, `idCultivo_a_grano(idCultivo) -> int | None` (ambos vía `Map_CultivoResultado`, 1:1 confirmado en `research.md` §3) y `campania_texto_a_id(texto) -> int | None` (vía tabla `Campañas`)
- [ ] T005 Implementar `backend/src/features/resultado_cultivo/campania_actual.py::campania_actual() -> int`: parsea `Campañas.Campaña` con las dos expresiones regulares de `research.md` §5 (`^\d{4}/\d{4}$`, `^\d{4}$`), devuelve la Campaña cuyo rango contiene la fecha de hoy; si ninguna coincide, cae a la Campaña más reciente con datos en `vw_ResultadosCultivo_CostosBase`, `vw_ResultadosCultivo_Ventas` o `PlanAgricola` (FR-001)
- [ ] T006 Crear `backend/src/features/resultado_cultivo/router.py` con `APIRouter(prefix="/api/resultado-cultivo", tags=["resultado-cultivo"])` vacío y el helper `_ejecutar` (errores de negocio → 404), copiando el patrón de `backend/src/features/ordenes/router.py`
- [ ] T007 Registrar `resultado_cultivo_router` en `backend/src/main.py` (import + `app.include_router(resultado_cultivo_router)`, junto a `ordenes_router`)
- [ ] T008 [P] Endpoint `GET /api/resultado-cultivo/campanias` en `router.py`: catálogo de Campañas + `campaniaActualId` (usa T004, T005)
- [ ] T009 [P] Agregar "Resultado de Cultivo" al submenú Producción en `frontend/src/components/layout/NavHeader.tsx` y a `frontend/src/components/remitos/RemitosSubNav.tsx` (mismo patrón que "Órdenes de trabajo" y "Planificación agrícola")
- [ ] T010 [P] Test `backend/tests/test_resultado_cultivo_campania_actual.py`: parseo de `"2026/2027"` (contiene hoy), `"2026"`, `"No Aplica"` (no parseable), y el resguardo a la Campaña más reciente con datos cuando ninguna coincide

**Checkpoint**: catálogo de Campañas con la actual preseleccionada disponible por API; navegación al módulo lista.

---

## Phase 3: User Story 1 — Ver el resultado consolidado de una Campaña (Priority: P1) 🎯 MVP

**Goal**: Pantalla de entrada del módulo: tarjetas KPI consolidadas de una Campaña completa + tabla resumen de una fila por Cultivo (spec.md Historia 1).

**Independent Test**: Elegir una Campaña con varios Cultivos cargados y verificar que el consolidado (superficie, costo, venta, margen, rentabilidad) coincide con la suma manual de sus Cultivos (SC-004); entrar sin elegir nada y verificar que preselecciona la Campaña actual (T005).

### Implementation for User Story 1

- [ ] T011 [P] [US1] Implementar `backend/src/features/resultado_cultivo/costos.py::costos_heredados(idCultivo, idCampania) -> list[dict]`: líneas de `vw_ResultadosCultivo_CostosBase` + `Seguros` vía `IdDestino` (mapeo.py, T004), respetando `Signo` (cargo/crédito, confiable per `research.md` §3 — no hace falta reemplazarlo)
- [ ] T012 [P] [US1] Implementar `costos.py::costo_ordenes_trabajo(idCultivo, idCampania) -> list[dict]`: insumos + maquinaria + contratista de `Ordenes_Trabajo_Insumos`/`Maquinaria`/`Contratista_Factura` (vía `Ordenes_Trabajo_Distrib.IdCultivo`/`IdCampania`), **excluyendo** cualquier `Ordenes_Trabajo_Contratista_Factura.IdCompra` que ya esté en `vw_ResultadosCultivo_CostosBase` (FR-004, anti-doble-conteo — `research.md` §6)
- [ ] T013 [US1] Implementar `costos.py::costo_total(idCultivo, idCampania) -> dict` combinando T011 + T012 (depende de T011, T012)
- [ ] T014 [P] [US1] Implementar `backend/src/features/resultado_cultivo/resultado.py::superficie_sembrada(idCultivo, idCampania) -> float`: `SUM(Lotes.Superficie)` vía `PlanAgricola` (`research.md` §1)
- [ ] T015 [P] [US1] Implementar `resultado.py::superficie_cosechada(idCultivo, idCampania) -> float | None`: `ResultadoCultivo_Cierre.SuperficieCosechada`, `None` si no hay fila (`research.md` §2)
- [ ] T016 [P] [US1] Implementar `resultado.py::venta_neta(idCultivo, idCampania) -> dict`: `vw_ResultadosCultivo_Ventas` (+ `Bonif*`) − `vw_ResultadosCultivo_Deducciones`, vía `idCultivo_a_grano` (mapeo.py, T004)
- [ ] T017 [US1] Implementar `resultado.py::resultado_cultivo(idCultivo, idCampania) -> dict`: combina T013-T016 en el shape `ResultadoCultivo` de `data-model.md` — costo/ha `None` si la superficie es 0 (nunca división por cero), `margenBruto`/`rentabilidad` por moneda como series independientes (spec.md Assumptions), `costeoIncompleto=True` si `idCultivo_a_destino` es `None` (FR-010), `advertenciaMargenNoRepresentativo=True` si `ventaNeta > 0` y `costoTotal < 0.20 * ventaNeta` (FR-011) (depende de T013, T014, T015, T016)
- [ ] T018 [US1] Implementar `resultado.py::costo_sin_clasificar(idCampania) -> dict`: suma de `vw_ResultadosCultivo_CostosBase` con `IdCampaña IS NULL` o `IdDestino` sin fila en `Map_CultivoResultado` (FR-012)
- [ ] T019 [US1] Implementar `resultado.py::resultado_campania(idCampania) -> dict`: consolidado sumando `resultado_cultivo()` (T017) de todos los Cultivos con algún dato en esa Campaña, más `costo_sin_clasificar()` (T018) — invariante FR-014/SC-004 (depende de T017, T018)
- [ ] T020 [US1] Agregar a `router.py` el endpoint `GET /api/resultado-cultivo/campania/{idCampania}` según `contracts/api-resultado-cultivo.md`
- [ ] T021 [P] [US1] Test `backend/tests/test_resultado_cultivo_costos.py`: T012 excluye un `IdCompra` que ya está en `vw_ResultadosCultivo_CostosBase` (simulado, ya que hoy `Ordenes_Trabajo_Contratista_Factura` está vacía); `Signo=-1` resta del total
- [ ] T022 [P] [US1] Test `backend/tests/test_resultado_cultivo_resultado.py`: `resultado_campania` == suma de sus `resultado_cultivo` (FR-014); costo/ha y rinde devuelven `None` con superficie 0
- [ ] T023 [US1] Crear `frontend/src/components/resultado-cultivo/SelectorCampania.tsx`: selector de Campaña, preselecciona `campaniaActualId` (T008)
- [ ] T024 [US1] Crear `frontend/src/components/resultado-cultivo/ConsolidadoCampaniaView.tsx`: tarjetas KPI (superficie, costo, venta, margen, rentabilidad en pesos y dólares) + tabla resumen de una fila por Cultivo; estado vacío neutro sin colores de advertencia cuando no hay datos (FR-009)
- [ ] T025 [US1] Crear `frontend/src/app/produccion/resultado-cultivo/page.tsx` consumiendo `SelectorCampania` + `ConsolidadoCampaniaView`
- [ ] T026 [US1] Extender `resultadoCultivoApi.ts` con `fetchCampanias`, `fetchResultadoCampania`, tipados según `contracts/api-resultado-cultivo.md`

**Checkpoint**: US1 funcional de punta a punta — entrar al módulo muestra el consolidado de la Campaña actual con su tabla por Cultivo. MVP demostrable.

---

## Phase 4: User Story 2 — Consultar el resultado de un Cultivo puntual (Priority: P1)

**Goal**: Drill-down desde la tabla resumen de US1 a un Cultivo específico dentro de la Campaña (spec.md Historia 2).

**Independent Test**: Hacer clic en una fila de la tabla resumen (US1) y verificar que el detalle del Cultivo (superficie, rinde, costo, venta, margen, rentabilidad) coincide con lo reconstruido a mano sumando las vistas heredadas de ese Cultivo (SC-002).

### Implementation for User Story 2

- [ ] T027 [US2] Agregar a `router.py` el endpoint `GET /api/resultado-cultivo/campania/{idCampania}/cultivo/{idCultivo}` (reutiliza `resultado.resultado_cultivo`, T017)
- [ ] T028 [P] [US2] Crear `frontend/src/components/resultado-cultivo/ResultadoCultivoView.tsx`: tarjetas KPI de un Cultivo puntual, con el badge ocre "costeo incompleto" (FR-010) y el badge de advertencia "costos incompletos — margen no representativo" (FR-011)
- [ ] T029 [US2] Crear `frontend/src/app/produccion/resultado-cultivo/[idCampania]/[idCultivo]/page.tsx` consumiendo `ResultadoCultivoView` (depende de T028)
- [ ] T030 [US2] Hacer clickeable cada fila de la tabla resumen de `ConsolidadoCampaniaView.tsx` (T024) navegando a `[idCampania]/[idCultivo]`
- [ ] T031 [US2] Extender `resultadoCultivoApi.ts` con `fetchResultadoCultivo`

**Checkpoint**: US1 + US2 funcionan juntas — desde el consolidado se llega al detalle de cualquier Cultivo, y ambos números son consistentes entre sí.

---

## Phase 5: User Story 3 — Ver el detalle de costos que componen el total (Priority: P2)

**Goal**: Drill-down de auditoría: desglose del costo por concepto, con trazabilidad hasta la línea de origen (spec.md Historia 3).

**Independent Test**: Sobre un Cultivo/Campaña con costos de varias fuentes, expandir el detalle y verificar que la suma de las líneas coincide con el costo total (US2), y que una línea de Orden de Trabajo navega correctamente a su detalle.

### Implementation for User Story 3

- [ ] T032 [US3] Implementar `resultado.py::detalle_costos(idCultivo, idCampania) -> list[dict]`: combina T011 + T012 en el shape `DetalleCosto` de `data-model.md` (`concepto`, `rubro`, `montoPesos`/`Dolares`, `origen`, `idCompra`/`idDetalleCompra` como texto si `origen="Compra"`, `idOrdenTrabajo` si `origen="OrdenTrabajo"`)
- [ ] T033 [US3] Agregar a `router.py` el endpoint `GET /api/resultado-cultivo/campania/{idCampania}/cultivo/{idCultivo}/costos` según `contracts/api-resultado-cultivo.md`
- [ ] T034 [P] [US3] Test en `backend/tests/test_resultado_cultivo_resultado.py`: `SUM(detalle_costos().montoPesos)` == `resultado_cultivo().costoTotalPesos` para un Cultivo/Campaña con costos heredados y de Órdenes de Trabajo
- [ ] T035 [US3] Crear `frontend/src/components/resultado-cultivo/DetalleCostosPanel.tsx`: tabla densa agrupable por concepto/rubro, con link "Ver orden" hacia `/produccion/ordenes/[idOrden]` cuando `origen="OrdenTrabajo"` (reutiliza el patrón de link ya usado en 011)
- [ ] T036 [US3] Integrar `DetalleCostosPanel` en `frontend/src/app/produccion/resultado-cultivo/[idCampania]/[idCultivo]/page.tsx` (T029)
- [ ] T037 [US3] Extender `resultadoCultivoApi.ts` con `fetchDetalleCostos`

**Checkpoint**: el resultado de un Cultivo es auditable hasta su línea de origen, no solo un número agregado.

---

## Phase 6: User Story 4 — Exportar el resultado a Excel (Priority: P2)

**Goal**: Exportar el resultado (y su detalle de costos) a una planilla `.xlsx` de 2 hojas (spec.md Historia 4).

**Independent Test**: Exportar el resultado de una Campaña y verificar que el archivo tiene las hojas "Resultado" y "Detalle de costos", con las mismas filas/columnas visibles en pantalla.

### Implementation for User Story 4

- [ ] T038 [P] [US4] Implementar `backend/src/features/resultado_cultivo/exportacion.py::resultado_campania_xlsx(idCampania) -> bytes`: hoja "Resultado" (una fila por Cultivo, T019) + hoja "Detalle de costos" (T032 de cada Cultivo), siguiendo el patrón multi-hoja de `backend/src/features/ordenes/exportacion.py` (`research.md` §7)
- [ ] T039 [US4] Agregar a `router.py` el endpoint `GET /api/resultado-cultivo/campania/{idCampania}/exportar` según `contracts/api-resultado-cultivo.md`
- [ ] T040 [P] [US4] Implementar `exportacion.py::resultado_cultivo_xlsx(idCampania, idCultivo) -> bytes`: mismas 2 hojas, acotado a un solo Cultivo
- [ ] T041 [US4] Agregar a `router.py` el endpoint `GET /api/resultado-cultivo/campania/{idCampania}/cultivo/{idCultivo}/exportar`
- [ ] T042 [US4] Agregar botón "Exportar a Excel" en `ConsolidadoCampaniaView.tsx` (T024) y `ResultadoCultivoView.tsx` (T028)
- [ ] T043 [US4] Extender `resultadoCultivoApi.ts` con `urlExportarCampania`, `urlExportarCultivo`

**Checkpoint**: todas las historias completas — el módulo cubre el mismo caso de uso que la vista parcial de 011, y más.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Retirar la vista parcial de 011 y verificación final, después de que el módulo nuevo funciona de punta a punta

- [ ] T044 Retirar la entrada "Costo por cultivo/campaña" de `frontend/src/components/remitos/RemitosSubNav.tsx` (la que apunta a `/produccion/ordenes/resultado-cultivo`, 011) y decidir con el usuario si se elimina también la página/componente (`frontend/src/app/produccion/ordenes/resultado-cultivo/page.tsx`, `ResultadoCultivoListado.tsx`) o se deja sin acceso desde el menú (FR-015) — no eliminar sin confirmación explícita, es código en producción
- [ ] T045 [P] Aplicar formato numérico y monetario del sistema (miles `.`, decimales `,`, `$`/`us$`) en todos los componentes nuevos de `frontend/src/components/resultado-cultivo/`, usando los helpers ya existentes (nunca `type=number` ni `toLocaleString`, regla de memoria del proyecto)
- [ ] T046 Ejecutar los 7 escenarios de `quickstart.md` de punta a punta sobre el sistema integrado y confirmar los 5 criterios de éxito de `spec.md` (SC-001 a SC-005)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias — arranca de inmediato
- **Foundational (Phase 2)**: depende de Setup — BLOQUEA todas las historias
- **US1 (Phase 3)**: depende de Foundational; es la base de cálculo (`resultado.py`, `costos.py`) que reutilizan US2 y US3
- **US2 (Phase 4)**: depende de Foundational y de las funciones de cálculo creadas en US1 (T017); su UI depende de `ConsolidadoCampaniaView` (T024) para el link de entrada
- **US3 (Phase 5)**: depende de Foundational y de T011/T012 (US1); independiente de US2 salvo por dónde se integra en la UI (T029)
- **US4 (Phase 6)**: depende de US1 (T019) y US3 (T032) para las 2 hojas del export
- **Polish (Phase 7)**: depende de que todas las historias deseadas estén completas

### Parallel Opportunities

- Setup: T002, T003 en paralelo
- Foundational: T008, T009, T010 en paralelo (después de T004-T007)
- US1: T011, T012, T014, T015, T016 en paralelo (distintas funciones, sin dependencias entre sí); T021, T022 en paralelo entre sí
- US3/US4: T038, T040 en paralelo

## Implementation Strategy

### MVP First (User Story 1)

1. Completar Phase 1 (Setup) y Phase 2 (Foundational)
2. Completar Phase 3 (US1) — consolidado de Campaña
3. **Parar y validar**: Escenarios 1 y 3 de `quickstart.md`
4. Demostrar si está listo

### Entrega incremental

1. Setup + Foundational → catálogo de Campañas con la actual preseleccionada
2. US1 → consolidado de Campaña navegable (MVP)
3. US2 → drill-down a Cultivo puntual
4. US3 → auditoría del detalle de costos
5. US4 → exportación a Excel
6. Polish → retirar la vista parcial de 011, formato numérico, validación final
