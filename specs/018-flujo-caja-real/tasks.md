---

description: "Task list for 018-flujo-caja-real"
---

# Tasks: Flujo de caja real

**Input**: Design documents from `/specs/018-flujo-caja-real/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api-flujo-caja.md, quickstart.md

**Tests**: incluidos — el plan (Testing: pytest) y la constitución (Principio V, contract-first tested integration) los piden explícitamente.

**Organization**: tareas agrupadas por historia de usuario (spec.md), en orden de prioridad P1→P3.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: puede correr en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: a qué historia de usuario pertenece (US1..US5)

## Path Conventions

Web app existente: `backend/src/`, `frontend/src/` (ver plan.md → Project Structure).

---

## Phase 1: Setup

**Purpose**: esqueleto de archivos nuevos, sin lógica todavía.

- [X] T001 Crear esqueleto del feature backend: `backend/src/features/flujo_caja/__init__.py`, `router.py`, `repository.py`, `schemas.py`, `clasificacion.py` (archivos vacíos con docstring de propósito, sin lógica)
- [X] T002 [P] Crear esqueleto frontend: `frontend/src/app/finanzas/flujo-caja-real/page.tsx`, `frontend/src/components/flujo-caja/TablaFlujoCaja.tsx`, `frontend/src/services/flujoCajaApi.ts` (componentes vacíos que compilan)
- [X] T003 [P] Agregar entrada "Flujo de caja real" al menú de Finanzas en `frontend/src/components/layout/NavHeader.tsx` (junto a Tesorería/Cuentas corrientes/Tarjetas, según árbol de navegación validado)

**Checkpoint**: estructura de archivos lista, nada funcional todavía.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: clasificación de movimientos internos y lectura normalizada de ambos bancos — lo usan TODAS las historias.

**⚠️ CRITICAL**: ninguna historia de usuario puede implementarse hasta que esta fase esté completa.

- [X] T004 Implementar `es_interno(banco, concepto, grupo_conceptos)` en `backend/src/features/flujo_caja/clasificacion.py` con las dos reglas de research.md §1: Galicia con `[Grupo de Conceptos]` que contiene "Inversiones" → interno; BNA con `Concepto` que matchea el patrón de transferencia entre titulares propios (`MIS TIT`, `DIS TIT`, `TRANSF.INT.DIST.TITULAR`) y el CUIT de la empresa (30712114602) → interno. Cualquier otro caso → operativo (no interno por default, FR-009).
- [X] T005 [P] Test de clasificación en `backend/tests/test_flujo_caja_clasificacion.py`: casos reales conocidos de `WC` (un movimiento "Inversiones" de Galicia → interno; un "EMIS TRANSFERENCIA/GIRO" sin patrón de titular propio → operativo; un movimiento sin concepto reconocible → operativo, no excluido)
- [X] T006 Implementar `get_movimientos_normalizados(fecha_desde, fecha_hasta)` en `backend/src/features/flujo_caja/repository.py`: lee `Movimientos BNA` (JOIN `CuentasBancarias` por `IdCuentaBancaria`) + `Movimientos Galicia` (débitos/créditos combinados en un único importe con signo) y devuelve filas normalizadas `{fecha, banco, numeroCuentaBancaria, importe, concepto, idContacto, contacto, esInterno}` usando T004 para calcular `esInterno` por fila. Solo lectura (`fetch_all`), nunca escribe (constitución II).
- [X] T007 Definir schemas Pydantic `PeriodoResumen`, `CuentaResumen`, `MovimientosInternos`, `UltimaCarga`, `ResumenFlujoCajaResponse`, `MovimientoFlujoCaja`, `DetalleFlujoCajaResponse` en `backend/src/features/flujo_caja/schemas.py` según los ejemplos JSON de `contracts/api-flujo-caja.md`

**Checkpoint**: clasificación y lectura normalizada listas — las historias de usuario pueden empezar.

---

## Phase 3: User Story 1 - Ver el neto mensual real de la empresa (Priority: P1) 🎯 MVP

**Goal**: el dueño ve ingresos/egresos/neto por mes (o semana) de todas sus cuentas bancarias, en la nueva pantalla.

**Independent Test**: abrir "Flujo de caja real" con datos ya cargados y verificar que los totales mensuales coinciden con la suma manual de los extractos de Tesorería (quickstart.md Escenario 1).

### Tests for User Story 1

- [X] T008 [P] [US1] Contract test `GET /api/flujo-caja/resumen` (mensual) en `backend/tests/test_flujo_caja_endpoints.py`: verifica estructura de respuesta y que la suma de `porCuenta[].ingresos/egresos` de un mes coincide con la suma de movimientos reales de ese mes (sin excluir todavía internos, eso es US2)

### Implementation for User Story 1

- [X] T009 [US1] Implementar `agregar_por_periodo(movimientos, granularidad)` en `backend/src/features/flujo_caja/repository.py`: agrupa las filas de T006 por mes o semana según `granularidad` ('mensual'|'semanal'), calculando ingresos/egresos/neto totales y por cuenta (depende de T006)
- [X] T010 [US1] Implementar `GET /api/flujo-caja/resumen` en `backend/src/features/flujo_caja/router.py`: query params `fechaDesde?` (default hoy-24 meses), `fechaHasta?` (default hoy), `granularidad` (default 'mensual'); 400 si `fechaDesde < 2010-08-31` (edge case de spec.md); requiere sesión (depende de T009)
- [X] T011 [US1] Registrar `flujo_caja_router` en `backend/src/main.py`
- [X] T012 [US1] Implementar `fetchResumen(fechaDesde?, fechaHasta?, granularidad?)` en `frontend/src/services/flujoCajaApi.ts`
- [X] T013 [US1] Construir `TablaFlujoCaja.tsx`: tabla primaria (mes/semana × ingresos/egresos/neto por cuenta + total), formato de números estándar del sistema (miles '.', decimales ',', negativos en rojo con signo '-')
- [X] T014 [US1] Agregar selector Mensual/Semanal (toggle) en `frontend/src/app/finanzas/flujo-caja-real/page.tsx`, conectado a `fetchResumen`

**Checkpoint**: User Story 1 funcional de forma independiente — se puede ver el neto mensual real.

---

## Phase 4: User Story 2 - Distinguir la plata real del negocio de los movimientos internos (Priority: P1)

**Goal**: transferencias propias y movimientos de FIMA no contaminan el neto operativo, pero siguen siendo visibles.

**Independent Test**: cargar/ubicar un movimiento interno conocido y verificar que no suma al neto pero aparece en su propio bloque con detalle (quickstart.md Escenario 2).

### Tests for User Story 2

- [X] T015 [P] [US2] Contract test en `backend/tests/test_flujo_caja_endpoints.py`: un movimiento Galicia con `[Grupo de Conceptos]` "Inversiones" en el rango consultado NO está incluido en `totalNeto` del período, pero SÍ está incluido en `movimientosInternos.total`
- [X] T016 [P] [US2] Contract test `GET /api/flujo-caja/detalle?soloInternos=true` en `backend/tests/test_flujo_caja_endpoints.py`: todas las filas devueltas tienen `esInterno=true`

### Implementation for User Story 2

- [X] T017 [US2] Extender `agregar_por_periodo` (T009) para separar `movimientosInternos: {ingresos, egresos, total}` del `totalNeto`/`totalIngresos`/`totalEgresos`, usando el campo `esInterno` ya calculado por T006
- [X] T018 [US2] Agregar `sinClasificar: {cantidad, importeAbsoluto}` al resumen: movimientos con `idContacto` nulo y `esInterno=false` (FR-009 — nunca se ocultan, se cuentan aparte)
- [X] T019 [US2] Implementar `GET /api/flujo-caja/detalle` en `router.py` con params `fechaDesde`, `fechaHasta` (requeridos), `banco?`, `numeroCuenta?`, `soloInternos?` (depende de T006)
- [X] T020 [US2] Implementar `fetchDetalle(...)` en `flujoCajaApi.ts`
- [X] T021 [US2] Agregar bloque "Movimientos internos (no suman al neto)" debajo de la tabla principal en `page.tsx`, con fondo `surface-sunken` para diferenciarlo visualmente (preferencia de UX ya validada)

**Checkpoint**: User Stories 1 y 2 funcionan juntas — el neto mostrado ya es el operativo real.

---

## Phase 5: User Story 3 - Distinguir las 3 cuentas históricas del BNA (Priority: P2)

**Goal**: los movimientos de cada una de las 3 cuentas BNA se identifican por separado, respetando su vigencia real.

**Independent Test**: filtrar por una cuenta BNA específica y verificar que solo aparecen movimientos de esa cuenta dentro de su rango de vigencia (quickstart.md Escenario 3).

### Tests for User Story 3

- [X] T022 [P] [US3] Contract test en `backend/tests/test_flujo_caja_endpoints.py`: `GET /api/flujo-caja/detalle?banco=BNA&numeroCuenta=12301640001709` con rango 2011 devuelve solo filas de esa cuenta; el mismo filtro con rango 2023 devuelve 0 filas (cuenta dada de baja en 2012)

### Implementation for User Story 3

- [X] T023 [US3] Confirmar que `porCuenta[]` del resumen (T009) y el filtro `numeroCuenta` del detalle (T019) ya distinguen correctamente las 3 cuentas BNA vía `numeroCuentaBancaria` (dato ya provisto por el JOIN de T006) — sin cambios de lógica si T006/T009 están bien, solo test de confirmación
- [X] T024 [US3] Mostrar en `TablaFlujoCaja.tsx` una fila/columna por cuenta (BNA × 3 + Galicia), no solo un total "BNA" agregado

**Checkpoint**: las 3 cuentas BNA se distinguen en pantalla.

---

## Phase 6: User Story 4 - Saber si los datos están actualizados (Priority: P2)

**Goal**: se ve la última fecha con datos de cada cuenta, para no confundir "sin movimientos" con "no cargado".

**Independent Test**: comparar la fecha mostrada como "última carga" contra el `MAX(Fecha)` real de cada cuenta (quickstart.md Escenario 4).

### Tests for User Story 4

- [X] T025 [P] [US4] Contract test en `backend/tests/test_flujo_caja_endpoints.py`: `ultimaCarga` del resumen coincide con `MAX(Fecha)` real por cuenta

### Implementation for User Story 4

- [X] T026 [US4] Implementar `ultima_fecha_por_cuenta()` en `repository.py`: `MAX(Fecha)` de `Movimientos BNA`/`Movimientos Galicia` agrupado por `IdCuentaBancaria`
- [X] T027 [US4] Agregar `ultimaCarga` a la respuesta de `GET /api/flujo-caja/resumen` (router.py)
- [X] T028 [US4] Mostrar fila "Última carga: BNA Cta ... · Galicia ..." arriba de la tabla en `page.tsx`, distinguiendo visualmente una cuenta sin movimientos en el período de una cuenta sin datos cargados

**Checkpoint**: el usuario nunca confunde falta de datos con ausencia de movimientos.

---

## Phase 7: User Story 5 - Ver el detalle de un mes (Priority: P3)

**Goal**: clic en una celda abre el listado de movimientos individuales que la componen.

**Independent Test**: sumar los movimientos del panel de detalle y verificar que coincide con el valor de la celda que lo originó (quickstart.md, coherente con FR-005).

### Tests for User Story 5

- [X] T029 [P] [US5] Contract test en `backend/tests/test_flujo_caja_endpoints.py`: la suma de `importe` de `GET /api/flujo-caja/detalle` para un mes×cuenta coincide exactamente con la celda correspondiente de `GET /api/flujo-caja/resumen`

### Implementation for User Story 5

- [X] T030 [US5] Agregar manejo de click en celda (mes × cuenta) en `TablaFlujoCaja.tsx` que dispara `fetchDetalle` con el rango y cuenta de esa celda
- [X] T031 [US5] Mostrar el detalle en un `SideDrawer` (reusar `frontend/src/components/ui/SideDrawer.tsx` existente) con el listado de movimientos ordenados por fecha

**Checkpoint**: todas las historias de usuario funcionan de forma independiente.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: validación final end-to-end.

- [X] T032 [P] Ejecutar los 4 escenarios de `quickstart.md` contra datos reales de `WC` y documentar resultado
- [X] T033 [P] Revisar formato de números en toda la pantalla nueva contra el estándar del proyecto (memoria `feedback_formato_numeros`: miles '.', decimales ',', prefijo $, nunca `type=number` ni `toLocaleString` directo)
- [X] T034 Ejecutar `pytest backend/tests/test_flujo_caja_*.py` y confirmar 100% en verde antes de dar la feature por completa
- [X] T035 [P] Test en `backend/tests/test_flujo_caja_endpoints.py` que confirma que `/api/flujo-caja/*` no expone ningún método de escritura (POST/PUT/PATCH/DELETE devuelven 404/405) — refuerza FR-006 (solo lectura) contra una regresión futura

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias.
- **Foundational (Phase 2)**: depende de Setup — BLOQUEA todas las historias.
- **User Stories (Phase 3-7)**: todas dependen de Foundational. US1/US2 son P1 y conviene hacerlas en orden (US2 extiende directamente lo que arma US1). US3/US4 son P2 e independientes entre sí y de US1/US2 una vez que Foundational está listo. US5 es P3 y depende del endpoint `/detalle` que ya crea US2 (T019).
- **Polish (Phase 8)**: depende de que las historias que se vayan a entregar estén completas.

### Parallel Opportunities

- T002/T003 (Setup) en paralelo con T001.
- T005 (test de clasificación) en paralelo con T006/T007 una vez que T004 está listo.
- Los contract tests marcados [P] de cada historia pueden correr en paralelo con el resto de tareas de implementación de esa misma historia (son de solo lectura sobre datos ya existentes, no dependen de que la UI esté lista).
- US3 y US4 pueden implementarse en paralelo entre sí (no comparten archivos más allá de lecturas del mismo `repository.py`, cuidando merge).

---

## Implementation Strategy

### MVP First (User Story 1 + 2)

1. Completar Phase 1 (Setup) y Phase 2 (Foundational).
2. Completar Phase 3 (US1): ya es demostrable — neto mensual real.
3. Completar Phase 4 (US2): imprescindible para que el neto no mienta (FIMA/transferencias) — junto con US1 es el MVP real según spec.md (ambas P1).
4. **Parar y validar** con el dueño antes de seguir a P2/P3.

### Incremental Delivery

1. Setup + Foundational → base lista.
2. US1 + US2 → MVP demostrable (el neto real, limpio de movimientos internos).
3. US3 → se distinguen las 3 cuentas BNA.
4. US4 → se ve si los datos están al día.
5. US5 → drill-down a movimientos individuales.
6. Polish → validación final contra quickstart.md.
