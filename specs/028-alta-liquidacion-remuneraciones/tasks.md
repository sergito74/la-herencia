---

description: "Task list for Alta de liquidación de remuneraciones (028)"
---

# Tasks: Alta de liquidación de remuneraciones

**Input**: Design documents from `/specs/028-alta-liquidacion-remuneraciones/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md, quickstart.md

**Tests**: se incluyen tareas de test unitario para la lógica pura (fórmula de neto, chequeo de duplicado, nombrado de archivo) — mismo criterio ya usado en este módulo (`test_remuneraciones_recibo.py`, sesión anterior). La validación del flujo completo contra `WC` real es manual (dry-run, quickstart.md), nunca automatizada (Constitución Principio II).

**Organization**: agrupadas por historia de usuario (spec.md) para poder entregar US1 (P1) como incremento independiente antes de US2 (P2).

## Phase 1: Setup

**Purpose**: sin infraestructura nueva que crear — es una extensión de un módulo existente, sin dependencias nuevas ni tablas nuevas.

- [X] T001 Confirmar que `backend/src/features/remuneraciones/repository.py` ya expone `CARPETA_RECIBOS` y el patrón de tokenización CamelCase (`_TOKEN_RE`) reusables para el nombrado de archivo de esta feature (sesión anterior) — sin cambios, solo verificación antes de tocar el archivo.

**Checkpoint**: sin bloqueos — Setup no tiene tareas de código.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: la fórmula correcta de importe neto (FR-014/FR-015) y los schemas de request/response son compartidos por ambas historias — deben quedar listos antes de implementar cualquiera de las dos.

**⚠️ CRITICAL**: ninguna historia de usuario puede implementarse hasta cerrar esta fase.

- [X] T002 En `backend/src/features/remuneraciones/repository.py`, extraer `calcular_importe_neto(conceptos: dict) -> float`: suma de haberes (`Sueldo basico`, `Antiguedad`, `Adic futuros aumentos`, `Dia Gremio`, `Aguinaldo`, `Vacaciones`, `Ajuste`, `Ajuste No Remunerativo`, `Redondeo`, `Bonificacion adicional`) menos suma de descuentos (`Jubilacion`, `Ley 19032`, `Obra Social`, `Obra Social Acuerdos`, `Aporte Sindical`, `Servicio de Sepelio`) — todos siempre tratados como valores positivos en la entrada (research.md §1).
- [X] T003 [P] En `backend/tests/test_remuneraciones_alta.py`, test unitario de `calcular_importe_neto` con el caso real confirmado en clarify: haberes `Sueldo basico=85096.38`, descuentos `Jubilacion=18631.02` + `Obra Social=5081.19` + `Aporte Sindical=3471.43` → neto `57912.74`; y un caso con todos los conceptos en 0 → neto `0`.
- [X] T004 En `backend/src/features/remuneraciones/repository.py`, reemplazar `_IMPORTE_SQL` (usado por `search_remuneraciones` y `get_remuneracion_referencia`) para que use la misma fórmula de `calcular_importe_neto` (resta los 6 conceptos de descuento en vez de sumarlos) — corrige FR-015 sin cambiar la forma de los endpoints `GET /api/remuneraciones` y `GET /api/remuneraciones/pagos` (contracts/api.md, sección "Sin cambios").
- [X] T005 [P] En `backend/src/features/remuneraciones/schemas.py`, agregar `NuevaLiquidacionRequest` (idContacto: int, fechaPago: date, periodoLiquidado: str, los 16 conceptos monetarios opcionales con default 0, confirmarDuplicado: bool = False — todos positivos, ver data-model.md), `NuevaLiquidacionResponse` (idSalario: int, importeNeto: float, recibo: str | None) y `AdjuntarReciboResponse` (idSalario: int, recibo: str).

**Checkpoint**: fórmula de neto corregida y verificada, contratos de datos listos — las historias de usuario pueden empezar.

---

## Phase 3: User Story 1 - Cargar una liquidación mensual nueva (Priority: P1) 🎯 MVP

**Goal**: elegir un empleado existente, completar los conceptos monetarios de su liquidación (todos en positivo) y guardarla contra `WC`, viéndola aparecer de inmediato en el listado ya existente con el importe neto correcto.

**Independent Test**: `POST /api/remuneraciones` con un empleado real y algunos conceptos (quickstart.md Escenario 1) → `201` con `importeNeto` correcto, y la liquidación visible en `GET /api/remuneraciones?empleado=...` con ese mismo importe.

### Tests for User Story 1

- [X] T006 [P] [US1] En `backend/tests/test_remuneraciones_alta.py`, test de `existe_liquidacion_periodo(id_contacto, periodo_liquidado)`: `True` cuando ya hay una fila con el mismo `IdContacto` y el mismo texto exacto de `Periodo liquidado` (comparación literal, sin normalizar — research.md §3), `False` para un período con texto distinto aunque sea el mismo mes calendario (ej. "Noviembre 2025" vs "30/11/2025" no cuentan como el mismo período).
- [X] T007 [P] [US1] En `backend/tests/test_remuneraciones_alta.py`, test de `crear_liquidacion(...)` con `monkeypatch` sobre `execute_write`/`fetch_one` (sin tocar `WC` real): confirma que inserta con `OUTPUT INSERTED.IdSalario`, que los conceptos se graban tal cual se reciben (positivos) y que devuelve `importeNeto` calculado con `calcular_importe_neto`.

### Implementation for User Story 1

- [X] T008 [US1] En `backend/src/features/remuneraciones/repository.py`, implementar `existe_liquidacion_periodo(id_contacto: int, periodo_liquidado: str) -> int | None` (devuelve el `IdSalario` existente o `None`) y `crear_liquidacion(request: NuevaLiquidacionRequest) -> dict` (INSERT contra `dbo.Remuneraciones` con `OUTPUT INSERTED.IdSalario`, exclusivamente contra `WC` vía `execute_write`/`execute_write_transaction` ya usado en el resto del proyecto — nunca contra `LaHerencia`).
- [X] T009 [US1] En `backend/src/features/remuneraciones/repository.py`, agregar validación: `id_contacto` debe corresponder a un Contacto de `[Tipo Contacto] = 'Empleado'` (mismo criterio que `existe_contacto_consignatario` en `ventas_granos/repository.py`) — si no, `crear_liquidacion` debe fallar antes de escribir.
- [X] T010 [US1] En `backend/src/features/remuneraciones/router.py`, implementar `POST ""` (alta): valida el contacto, si `existe_liquidacion_periodo` devuelve un id y `confirmarDuplicado` es `False` responde `409` con `idSalarioExistente` (contracts/api.md); si no, llama `crear_liquidacion` y responde `201` con `NuevaLiquidacionResponse`. Requiere sesión sin rol `SoloLectura` (mismo middleware ya usado en el resto de las escrituras del backend).
- [X] T011 [P] [US1] En `frontend/src/services/remuneracionesApi.ts`, agregar `crearLiquidacion(request): Promise<{idSalario, importeNeto, recibo}>` (POST `/api/remuneraciones`, maneja la respuesta `409` como un caso esperado, no como error genérico) y los tipos `NuevaLiquidacionRequest`/`NuevaLiquidacionResponse`.
- [X] T012 [US1] Crear `frontend/src/components/remuneraciones/NuevaLiquidacionForm.tsx`: `ContactoSelect` (tipoContacto="Empleado"), input de fecha de pago, input de período liquidado (texto libre, sugerido por defecto como "Mes Año" a partir de la fecha elegida — editable, Assumptions de spec.md), un input por cada uno de los 16 conceptos monetarios (todos positivos, default vacío = 0), y un importe neto calculado en vivo en el cliente con la misma fórmula de T002 (haberes − descuentos) mientras se completa el formulario (FR-014). Al guardar, si la respuesta es `409`, muestra el aviso de duplicado con un botón "Guardar de todos modos" que reintenta con `confirmarDuplicado: true` (FR-004, no bloquea).
- [X] T013 [US1] En `frontend/src/components/remuneraciones/RemuneracionesListado.tsx`, agregar un botón "Nueva liquidación" envuelto en `<SoloLectura>` (mismo patrón que `CuentaSocio.tsx`/`AsignarGastoForm.tsx`, FR-013) que abre `NuevaLiquidacionForm`; al guardar con éxito, refresca el listado (invalidar la query de `useQuery`) para que la liquidación nueva aparezca sin recargar la página (FR-009).

**Checkpoint**: User Story 1 funcional y verificable de punta a punta (quickstart.md Escenarios 1, 3 y 5) sin depender de la carga de PDF.

---

## Phase 4: User Story 2 - Adjuntar el PDF del recibo al cargar la liquidación (Priority: P2)

**Goal**: adjuntar el PDF del recibo, junto con el alta o después sobre una liquidación ya existente, y que quede vinculado sin ambigüedad al link "Recibo" que ya usa el listado (columna `Recibo`, sesión anterior).

**Independent Test**: `POST /api/remuneraciones/{idSalario}/recibo` con un PDF real (quickstart.md Escenario 2) → `200` con la ruta relativa esperada, y el link "Recibo" existente del listado abre ese mismo archivo.

### Tests for User Story 2

- [X] T014 [P] [US2] En `backend/tests/test_remuneraciones_alta.py`, test de `nombre_archivo_recibo(fecha_pago, empleado) -> str`: para `fecha_pago=2026-09-30`, `empleado="Armando Oscar Mori"` devuelve `"2026 09 Armando Oscar Mori.pdf"` (data-model.md, "Entidad: Recibo (PDF)").
- [X] T015 [P] [US2] En `backend/tests/test_remuneraciones_alta.py`, con `tmp_path`/`monkeypatch` sobre `CARPETA_RECIBOS` (mismo patrón que `test_remuneraciones_recibo.py`): `guardar_recibo(...)` escribe el archivo en `{tmp}/{año}/{nombre}` y devuelve la ruta relativa `Personal\Recibos\{año}\{nombre}` para guardar en la columna `Recibo` (data-model.md); rechaza un archivo que no empieza con los bytes mágicos de PDF (`%PDF`).

### Implementation for User Story 2

- [X] T016 [US2] En `backend/src/features/remuneraciones/repository.py`, implementar `nombre_archivo_recibo(fecha_pago: date, empleado: str) -> str` (formato `"{año} {mes:02d} {empleado}.pdf"`, research.md §2) y `guardar_recibo(id_salario: int, fecha_pago: date, empleado: str, contenido: bytes) -> str`: valida que `contenido` empiece con `%PDF`, escribe el archivo en `CARPETA_RECIBOS/{año}/`, hace `UPDATE dbo.Remuneraciones SET Recibo = ? WHERE IdSalario = ?` con la ruta relativa, y devuelve esa ruta.
- [X] T017 [US2] En `backend/src/features/remuneraciones/router.py`, implementar `POST "/{id_salario}/recibo"` (`UploadFile`, mismo patrón que `tesoreria/router.py::validar_excel`): responde `404` si el `id_salario` no existe, `400` si el archivo no es PDF o supera 10 MB (SC-004), y `200` con `AdjuntarReciboResponse` si se guardó. Requiere sesión sin rol `SoloLectura`.
- [X] T018 [P] [US2] En `frontend/src/services/remuneracionesApi.ts`, agregar `subirRecibo(idSalario: number, archivo: File): Promise<{idSalario, recibo}>` (POST multipart a `/api/remuneraciones/{idSalario}/recibo`).
- [X] T019 [US2] En `NuevaLiquidacionForm.tsx` (T012), agregar un input de archivo opcional ("Adjuntar recibo (PDF)") que, si se completa, llama `subirRecibo` inmediatamente después de que `crearLiquidacion` devuelve el `idSalario` nuevo — sin bloquear el guardado de los datos numéricos si no se adjunta nada (Assumptions de spec.md: son pasos independientes).
- [X] T020 [US2] En `frontend/src/components/remuneraciones/RemuneracionesListado.tsx`, agregar, junto al link "Recibo" ya existente de cada fila (columna agregada en la sesión anterior), una acción "Adjuntar/reemplazar recibo" envuelta en `<SoloLectura>` para liquidaciones existentes que aún no tienen `recibo` (o para reemplazarlo) — reusa `subirRecibo` de T018.

**Checkpoint**: ambas historias funcionales — quickstart.md completo (Escenarios 1-6) verificable de punta a punta.

---

## Phase 5: Polish & Cross-Cutting Concerns

- [X] T021 Correr `backend/.venv/Scripts/python.exe -m pytest -q` completo y confirmar que no hay regresiones en los tests existentes del módulo (`test_remuneraciones_recibo.py` y el resto de la suite).
- [X] T022 Validar manualmente contra `WC` real los 6 escenarios de `quickstart.md` (dry-run con un empleado y un período de prueba, sin dejar datos basura — o limpiando el registro de prueba al terminar), incluido el Escenario 6 (rol `SoloLectura`).
- [X] T023 [P] Correr `npx tsc --noEmit` y `npx eslint` sobre los archivos de frontend tocados (mismo criterio que el resto de las features de este proyecto).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias — es solo una verificación.
- **Foundational (Phase 2)**: depende de Setup — bloquea ambas historias de usuario (la fórmula de neto y los schemas los usan las dos).
- **User Story 1 (Phase 3)**: depende de Foundational. No depende de User Story 2.
- **User Story 2 (Phase 4)**: depende de Foundational. Se integra con la UI de User Story 1 (T012/T019, T013/T020) pero su backend (T016-T018) es independiente y podría probarse contra una liquidación creada a mano en SQL, sin esperar a que US1 esté en producción.
- **Polish (Phase 5)**: depende de que las historias que se vayan a entregar estén completas.

### Parallel Opportunities

- T003 (test) puede escribirse en paralelo con T004 (ambos tocan `repository.py`/`tests`, pero son ediciones independientes hasta integrarse).
- T005 (schemas) es paralelo a T002-T004 (archivo distinto).
- Dentro de US1: T006/T007 (tests) en paralelo entre sí; T011 (frontend API) en paralelo con T008-T010 (backend).
- Dentro de US2: T014/T015 (tests) en paralelo entre sí; T018 (frontend API) en paralelo con T016-T017 (backend).
- T023 (typecheck/lint) en paralelo con T021-T022 (no comparten archivos).

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Completar Phase 1 (verificación) + Phase 2 (fórmula de neto + schemas, corrige además el bug del listado existente).
2. Completar Phase 3 (User Story 1) — ya es un incremento entregable: alta de liquidaciones sin PDF, con el importe neto correcto en toda la app.
3. **Validar**: quickstart.md Escenarios 1, 3 y 5 contra `WC` real.

### Incremental Delivery

1. Setup + Foundational → fórmula de neto corregida en producción (ya mejora el listado existente, incluso antes de tener alta).
2. + User Story 1 → alta de liquidaciones sin recibo, ya usable.
3. + User Story 2 → alta completa con PDF adjunto, feature cerrada.
