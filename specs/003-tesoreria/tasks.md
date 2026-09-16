# Tasks: Tesorería por banco, caja, valores y tarjetas (solo lectura)

**Input**: Design documents from `specs/003-tesoreria/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/tesoreria-api.md, quickstart.md

**Tests**: Incluidos, mismo criterio que `specs/002-compras/tasks.md` (pytest + httpx con fixtures).

**Organization**: Tareas agrupadas por historia de usuario. Este módulo reutiliza la app backend/frontend creada en `specs/002-compras` (mismo `backend/src/db/connection.py`, mismo helper de paginación).

## Path Conventions

`backend/src/`, `backend/tests/`, `frontend/src/` (misma app que `specs/002-compras`).

---

## Phase 1: Setup

- [x] T001 Crear estructura `backend/src/features/tesoreria/` y `backend/tests/contract/fixtures/` en la app existente
- [x] T002 Agregar dependencias `openpyxl` (Galicia, `.xlsx`) y `xlrd` (BNA, `.xls` binario antiguo) al proyecto backend (per `research.md`)
- [x] T003 [P] Crear estructura `frontend/src/app/tesoreria/` y `frontend/src/components/tesoreria/` en la app existente

---

## Phase 2: Foundational (Blocking Prerequisites)

**⚠️ CRITICAL**: Ninguna historia de usuario puede comenzar hasta completar esta fase.

- [x] T004 Verificar que `backend/src/db/connection.py` (creado en `specs/002-compras`) esté disponible y reutilizable sin cambios; si no existe en este entorno, crearlo per `specs/002-compras/plan.md`
- [x] T005 [P] Verificar/reutilizar el helper de paginación compartido `backend/src/db/pagination.py` (creado en `specs/002-compras`)
- [x] T006 [P] Crear `backend/src/features/tesoreria/schemas.py` con los schemas base por medio (`MovimientoBNA`, `MovimientoGalicia`, `PagoEfectivo`, `ValorPropio`, `ValorRecibido`, `ResumenTarjeta`, `LineaResumenTarjeta`) per `data-model.md`

**Checkpoint**: Fundación lista.

---

## Phase 3: User Story 1 - Consultar movimientos por banco, caja o medio de pago (Priority: P1) 🎯 MVP

**Goal**: Un usuario selecciona un medio (BNA, Galicia, efectivo, valores, tarjetas) y ve sus movimientos, cada uno con su propia forma de datos.

**Independent Test**: Seleccionar Banco Nación y verificar que se listan sus movimientos (fecha, concepto, importe, contacto), ordenados por fecha (FR-001, FR-002).

### Tests for User Story 1

- [x] T007 [P] [US1] Contract test para `GET /api/tesoreria/medios` en `backend/tests/contract/test_tesoreria_medios.py`
- [x] T008 [P] [US1] Contract test para `GET /api/tesoreria/{medio}/movimientos` cubriendo BNA y Galicia (formas distintas, sin forzar campos inexistentes) y el caso sin resultados en `backend/tests/contract/test_tesoreria_movimientos.py` per `contracts/tesoreria-api.md`

### Implementation for User Story 1

- [x] T009 [US1] Implementar consultas parametrizadas por medio (BNA, Galicia, efectivo, valores propios, valores recibidos, tarjetas/resúmenes/líneas) con filtros `fechaDesde`/`fechaHasta` y paginación en `backend/src/features/tesoreria/repository.py` (depende de T006)
- [x] T010 [US1] Implementar endpoint `GET /api/tesoreria/medios` en `backend/src/features/tesoreria/router.py`
- [x] T011 [US1] Implementar endpoint `GET /api/tesoreria/{medio}/movimientos` (depende de T009) en `router.py` per `contracts/tesoreria-api.md`
- [x] T012 [US1] Registrar el router de tesorería en `backend/src/main.py` (depende de T010, T011)
- [x] T013 [P] [US1] Crear página de tesorería con selector de medio en `frontend/src/app/tesoreria/page.tsx`
- [x] T014 [P] [US1] Crear componentes de tabla específicos por medio (columnas propias de BNA vs. Galicia vs. efectivo vs. valores vs. tarjetas, sin forzar un modelo único) en `frontend/src/components/tesoreria/MovimientosPorMedio.tsx` per FR-002
- [x] T015 [US1] Implementar filtro de rango de fechas y estado vacío explícito en `MovimientosPorMedio.tsx` (depende de T014) per FR-003/FR-012
- [x] T016 [US1] Implementar paginación en `MovimientosPorMedio.tsx` (depende de T014) per FR-013

**Checkpoint**: User Story 1 funcional de forma independiente.

---

## Phase 4: User Story 2 - Ver la referencia de origen de un movimiento de tesorería (Priority: P1)

**Goal**: Un usuario ve, para un movimiento de tesorería, si corresponde a una compra registrada, incluyendo el caso de coincidencia ambigua.

**Independent Test**: Tomar un movimiento vinculado a una compra conocida y verificar que se muestra la referencia; forzar un caso con varias compras candidatas y verificar que se marca como ambiguo (FR-004, FR-005).

### Tests for User Story 2

- [x] T017 [P] [US2] Contract test para `GET /api/tesoreria/{medio}/movimientos/{id}/referencia` cubriendo los 3 estados (`sin_coincidencia`, `coincidencia_unica`, `ambigua`) en `backend/tests/contract/test_tesoreria_referencia.py` per `contracts/tesoreria-api.md`

### Implementation for User Story 2

- [x] T018 [US2] Implementar `backend/src/features/tesoreria/matching.py`: función pura que busca compras (`dbo.Compras`) del mismo `IdContacto` con fecha/importe compatibles contra un movimiento de tesorería y devuelve `estado` + `candidatas` (nunca elige una por defecto, per FR-005); para `Valores propios` devolver siempre `estado: "sin_coincidencia"` sin ejecutar la búsqueda, dado que ese medio no tiene campo de contacto (clarificación 2026-09-16); para `Valores Recibidos` usar `idEmisor` como equivalente de `IdContacto`
- [x] T019 [US2] Implementar endpoint `GET /api/tesoreria/{medio}/movimientos/{id}/referencia` en `backend/src/features/tesoreria/router.py` (depende de T018)
- [x] T020 [P] [US2] Crear componente de referencia de origen que renderiza explícitamente los 3 estados (sin coincidencia / única / ambigua con todas las candidatas) en `frontend/src/components/tesoreria/ReferenciaOrigen.tsx` per FR-005/SC-002
- [x] T021 [US2] Integrar `ReferenciaOrigen.tsx` en `MovimientosPorMedio.tsx` (depende de T014, T020) — sin mostrar ni derivar rubro/centro de costo/destino (FR-006)

**Checkpoint**: User Story 1 y 2 funcionan de forma independiente y en conjunto.

---

## Phase 5: User Story 3 - Cargar resúmenes bancarios y de tarjeta mediante archivo Excel (Priority: P3)

**Goal**: Un usuario sube un Excel de resumen, el sistema valida su estructura y muestra una vista previa, sin persistir nada.

**Independent Test**: Subir un Excel de ejemplo válido y verificar la vista previa; subir uno con estructura incorrecta y verificar el mensaje de rechazo (FR-007, FR-008, FR-009).

### Tests for User Story 3

- [x] T022 [P] [US3] Contract test para `POST /api/tesoreria/excel/validar` cubriendo BNA válido, Galicia válido y archivo inválido, usando fixtures `backend/tests/contract/fixtures/bna_ejemplo.xls` y `backend/tests/contract/fixtures/galicia_ejemplo.xlsx` (copias sanitizadas de los archivos reales confirmados el 2026-09-16, sin datos sensibles) en `backend/tests/contract/test_tesoreria_excel.py` per `contracts/tesoreria-api.md` — **implementado 2026-09-15 con una desviación**: no se generaron los archivos fixture `.xls`/`.xlsx` reales porque escribir un `.xls` binario legible por `xlrd` requiere `xlwt`, dependencia no incluida (solo se agregó `xlrd`, de solo lectura, per `research.md`). En su lugar: (a) el contrato del endpoint se testea mockeando `excel_import.validar_y_previsualizar` igual que el resto de la suite, y (b) la lógica real de parseo (`_parse_importe_arg`, detección de encabezado, mapeo de columnas Galicia) se cubre con tests unitarios que generan un `.xlsx` real en memoria vía `openpyxl`. El parseo de BNA (`.xls`) queda sin cobertura automatizada — validado manualmente sería el siguiente paso si aparece un archivo real de ejemplo

### Implementation for User Story 3

- [x] T023 Obtener del usuario un archivo Excel real de resumen — **resuelto 2026-09-16**: formato BNA (`.xls`, 5 filas de metadata + encabezado `Fecha/Comprobante/Concepto/Importe/Saldo`) y Galicia (`.xlsx`, hoja `Movimientos`, encabezado en fila 1) confirmados, ver `research.md`/`data-model.md`
- [x] T024 [US3] Implementar `backend/src/features/tesoreria/excel_import.py`: para Galicia usar `openpyxl` (hoja `Movimientos`, encabezado fila 1, 16 columnas); para BNA usar `xlrd` (saltar 5 filas de metadata, encabezado real en fila 6, parsear importes de texto `"$ 1.234,56"` a número); detectar medio por forma del encabezado, generar previsualización en memoria sin persistir ni intentar resolver contacto (depende de T023, ya resuelto)
- [x] T025 [US3] Implementar endpoint `POST /api/tesoreria/excel/validar` (multipart) en `backend/src/features/tesoreria/router.py` (depende de T024)
- [x] T026 [P] [US3] Crear componente de carga de Excel con vista previa y aviso explícito de "no persistido todavía" en `frontend/src/components/tesoreria/CargaExcel.tsx`
- [x] T027 [US3] Integrar `CargaExcel.tsx` en `frontend/src/app/tesoreria/page.tsx` (depende de T013, T026)

**Checkpoint**: Las 3 historias funcionan de forma independiente y en conjunto.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T028 Verificar contra `INFORMATION_SCHEMA.COLUMNS` la estructura real de `Pagos efectivo`, `Valores propios`, `Valores Recibidos` y `Tarjetas_Resumenes_Lineas` — **resuelto 2026-09-16**, ver `data-model.md` (incluye el hallazgo de que `Valores propios` no tiene campo de contacto)
- [x] T029 Revisar que ningún endpoint de consulta acepte `POST`/`PUT`/`DELETE`/`PATCH`, y que `POST /api/tesoreria/excel/validar` no escriba en SQL Server bajo ninguna condición (FR-010) — revisión manual de `router.py`: único `POST` es `/excel/validar`, `excel_import.py` no importa `pyodbc` ni el módulo de conexión, solo parsea bytes en memoria
- [x] T030 Ejecutar la validación completa de `quickstart.md` contra datos reales de solo lectura — **verificado 2026-09-15**: los 6 medios (bna, galicia, efectivo, valores-propios, valores-recibidos, tarjetas) devuelven datos reales correctos; `next build` y `tsc --noEmit` sin advertencias. Durante esta validación se detectó y corrigió un bug real de binding de fechas (ver nota en T032 de `specs/002-compras/tasks.md`): pyodbc rechazaba `datetime.date` contra columnas `datetime`, arreglado con `backend/src/db/params.py::as_sql_datetime`, aplicado también en `matching.py`
- [x] T031 [P] Confirmar que ninguna respuesta de este módulo expone las columnas de centro de costo/rubro/destino de `Movimientos Galicia` (FR-006) — revisión manual de `schemas.py` y `repository.py`: `MovimientoGalicia`/`select_columns["galicia"]` no incluyen esas columnas; el único campo `destino` del módulo pertenece a `ValorRecibido` (campo de texto libre propio de ese medio, sin relación con imputación, permitido explícitamente por `data-model.md`)
- [x] T032 Verificar que los endpoints de `backend/src/features/tesoreria/router.py` estén declarados `async def` y que ninguna función de `repository.py`/`matching.py` mantenga estado/caché en memoria entre requests, de forma que múltiples usuarios puedan leer en paralelo sin bloquearse entre sí (FR-014)
- [x] T033 [P] Contract test que dispara múltiples requests concurrentes (`asyncio.gather` sobre varios `httpx.AsyncClient.get`) contra `GET /api/tesoreria/{medio}/movimientos` para distintos medios y verifica que todas responden 200 sin degradación ni errores de bloqueo, en `backend/tests/contract/test_tesoreria_concurrencia.py` (depende de T011) per FR-014

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias (asume `specs/002-compras` ya en marcha o completo para T004/T005).
- **Foundational (Phase 2)**: depende de Setup; bloquea todas las historias.
- **User Stories (Phase 3-5)**: dependen de Foundational. US1 y US2 son ambas P1; US2 depende de que exista la tabla `Compras` (de `specs/002-compras`) para el matching, pero no depende de que su API esté implementada. US3 es independiente de US1/US2 salvo por compartir el router y la página de tesorería.
- **Polish (Phase 6)**: T028 ya está resuelto (ver `data-model.md`), disponible como referencia para T009. T032/T033 (FR-014, concurrencia) dependen de que exista el endpoint de movimientos (T011), pero no bloquean ninguna historia.

### Parallel Opportunities

- T002, T003 en paralelo con T001.
- T005, T006 en paralelo con T004.
- T007, T008 en paralelo al iniciar US1.
- T013, T014 en paralelo una vez exista el contrato (T011).
- T017 en paralelo con el inicio de US2.
- T022 en paralelo con el inicio de US3 (una vez resuelto T023).

---

## Parallel Example: User Story 1

```bash
Task: "Contract test para GET /api/tesoreria/medios en backend/tests/contract/test_tesoreria_medios.py"
Task: "Crear página de tesorería con selector de medio en frontend/src/app/tesoreria/page.tsx"
```

---

## Implementation Strategy

### MVP First

US1 y US2 son ambas P1 — el MVP es **Setup + Foundational + US1 + US2** (consultar movimientos y ver su referencia de origen, incluida la ambigüedad). US3 (carga por Excel) es una mejora de eficiencia declarada P3 y puede posponerse sin que el módulo pierda su valor principal.

1. Completar Phase 1 (Setup) y Phase 2 (Foundational).
2. Completar Phase 3 (US1) y Phase 4 (US2) — validar contra `quickstart.md` pasos 2-3.
3. **Detenerse y validar** el MVP de forma independiente.
4. Completar Phase 5 (US3), empezando por T023 (conseguir el archivo Excel real del usuario).
5. Completar Phase 6 (Polish).

### Nota sobre T023 y T028

Ambas quedaron resueltas el 2026-09-16 contra datos/archivos reales (ver `research.md` y `data-model.md`), por lo que T024 y T009 ya pueden implementarse directamente sin bloqueo pendiente.
