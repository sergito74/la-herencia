---

description: "Task list for 027-migracion-cajas-giamigli"
---

# Tasks: Migración histórica de Cajas Giamigli

**Input**: Design documents from `/specs/027-migracion-cajas-giamigli/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: incluidos — el proyecto ya tiene convención establecida de tests unitarios por feature (004/019/020/021, plan.md §Testing).

**Organization**: agrupadas por historia de usuario (spec.md) para poder implementar y probar cada una de forma independiente.

## Path Conventions

Web app existente: `backend/src/`, `backend/scripts/`, `backend/tests/`, `frontend/src/` — paths tomados de plan.md §Project Structure.

---

## Phase 1: Setup

**Purpose**: confirmar que el entorno tiene lo necesario antes de tocar código.

- [X] T001 Confirmar que `openpyxl` está en `backend/requirements.txt` (o agregarlo si falta) y que `python -c "import openpyxl"` corre sin error en el entorno del backend.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: esquema de base de datos y utilidades de parseo/deduplicación compartidas por las 4 historias de usuario — nada de Phase 3+ puede empezar sin esto.

**⚠️ CRITICAL**: ninguna historia de usuario puede implementarse hasta terminar esta fase.

- [X] T002 Backup verificado de `WC` antes de cualquier cambio de esquema (Constitución, Principio II) — documentar en el PR/commit que el backup se verificó.
- [X] T003 Crear `backend/scripts/crear_tablas_cajas_efectivo.py` (idempotente, mismo patrón que `crear_tablas_cuentas_socios.py`, `IF OBJECT_ID(...) IS NULL` / `IF COL_LENGTH(...) IS NULL`) con: (a) `ALTER TABLE dbo.MovimientosCuentaSocio` agregando `ImporteUSD money NOT NULL DEFAULT 0` y `ImporteKgCarne decimal(14,3) NOT NULL DEFAULT 0`, reemplazando `CK_MovimientosCuentaSocio_Importe` por `CK_MovimientosCuentaSocio_ImporteAlguno CHECK (Importe > 0 OR ImporteUSD > 0 OR ImporteKgCarne > 0)` (data-model.md §1); (b) `CREATE TABLE dbo.MovimientosCajaEfectivo` con `CHECK (Caja IN ('GiamigliSA', 'CampoChica'))` (data-model.md §2) + índice `IX_MovimientosCajaEfectivo_Caja (Caja, Fecha)`; (c) `CREATE TABLE dbo.MigracionCajasGiamigliRevision` (data-model.md §3).
- [X] T004 Correr `crear_tablas_cajas_efectivo.py` contra `WC` y confirmar por consulta directa que las 3 tablas/columnas quedaron creadas.
- [X] T005 [P] Crear paquete `backend/scripts/migracion_cajas_giamigli/__init__.py` (vacío).
- [X] T006 [P] Implementar `backend/scripts/migracion_cajas_giamigli/lector_excel.py`: `leer_hoja_socio(ruta_excel, nombre_hoja)` y `leer_hoja_caja(ruta_excel, nombre_hoja, caja)`, usando `openpyxl` en modo `data_only=True` (research.md §1). Debe: reconocer las columnas confirmadas de cada tipo de hoja (research.md §1); clasificar cada fila como migrable (tiene fecha Y al menos un importe no nulo/no cero) o como `CasoARevisar` (research.md §4); descartar en silencio las filas completamente vacías sin generar `CasoARevisar` (research.md §4, confirmado contra `Cuenta Ceci`); para `leer_hoja_caja`, normalizar `Caja chica campo` a `Importe = Haber - Debe` con signo (research.md §7).
- [X] T007 [P] Implementar `backend/scripts/migracion_cajas_giamigli/dedup.py`: `ya_existe_movimiento_socio(id_socio, fecha, importe_pesos)` (consulta `MovimientosCuentaSocio` por `IdSocio, Fecha, Importe` con tolerancia $0,01, `Anulada = 0`); `resolver_contacto_por_nombre(nombre)` (consulta `dbo.Contactos` por `[Razon Social]` exacto, case-insensitive); `ya_existe_pago_efectivo(id_contacto, fecha, importe)` (consulta `Pagos efectivo` por `IdContacto, Fecha, [Importe imputado]` con tolerancia $0,01) — regla de coincidencia fecha+proveedor+importe confirmada en spec Clarifications y research.md §3.
- [X] T008 [P] Crear módulo `backend/src/features/migracion_cajas_giamigli/` (`__init__.py`, `repository.py` con `listar_casos_a_revisar(resuelto: bool | None)`, `schemas.py`, `router.py` con `GET /api/migracion-cajas-giamigli/revision?resuelto=` per contracts/api.md) — sin esto no hay dónde ver los casos que generen los scripts de migración de las otras historias.

**Checkpoint**: esquema listo, utilidades de parseo/dedup listas, endpoint de revisión listo — las historias de usuario pueden empezar.

---

## Phase 3: User Story 1 - Ver el historial completo de la cuenta de cada socio en el sistema (Priority: P1) 🎯 MVP

**Goal**: las 4 cuentas de socios (Sergio, Lucy, Cond LSC, Ceci) muestran en el sistema el mismo historial y saldo (pesos/USD/Kg carne) que la planilla, sin duplicar lo ya cargado a mano.

**Independent Test**: migrar solo la hoja `Cuenta Ceci` (la más chica) y verificar que el saldo final en pesos calculado por el sistema coincide con el saldo final de esa hoja en la planilla.

### Tests for User Story 1

- [X] T009 [P] [US1] Test de `migrar_socios`/`lector_excel` con fixtures (sin abrir el Excel real): fila con Debe → `AsignacionGasto`; fila con Haber → `Devolucion`; fila con importe solo en USD o solo en Kg carne (sin pesos) → se migra con `Importe=0` y el componente correspondiente > 0 (nunca ambos 0 y nunca `None`); y un test que verifique la invariante de cobertura de SC-004 (`filas_leidas == migradas + deduplicadas + a_revisar`, ninguna fila se pierde sin contar) sobre un fixture con mezcla de los 3 casos, en `backend/tests/test_migracion_cajas_giamigli_lector.py`.
- [X] T010 [P] [US1] Test de `dedup.ya_existe_movimiento_socio` con fixtures: coincidencia exacta (mismo `IdSocio`, `Fecha`, `Importe`) devuelve `True`; importe con diferencia de $0,02 devuelve `False` (fuera de la tolerancia de $0,01) en `backend/tests/test_migracion_cajas_giamigli_dedup.py`.
- [X] T011 [P] [US1] Test de `cuentas_socios.repository.calcular_saldo` extendido: movimiento con `Importe=48841.02, ImporteUSD=21.71, ImporteKgCarne=8.49` devuelve los 3 saldos por separado, sin ninguna conversión entre ellos, en `backend/tests/test_cuentas_socios_repository.py` (extiende el archivo existente).

### Implementation for User Story 1

- [X] T012 [US1] Implementar `backend/scripts/migracion_cajas_giamigli/migrar_socios.py`: recorre las 4 hojas (`Cuenta Sergio`, `Cuenta Lucy`, `Cuenta Cond LSC`, `Cuenta Ceci`) con `lector_excel.leer_hoja_socio`; para cada fila migrable, si `dedup.ya_existe_movimiento_socio` es `False`, inserta en `MovimientosCuentaSocio` (`Tipo`, `Importe`, `ImporteUSD`, `ImporteKgCarne`, `Fecha`, `Medio`=forma_pago, `Motivo="{proveedor} — {detalle}"`, `Usuario='migracion-cajas-giamigli'`); cada `CasoARevisar` se inserta en `MigracionCajasGiamigliRevision` (contracts/schema-script.md §4); al final, por cada hoja, hace `assert filas_leidas == migradas + deduplicadas + a_revisar` (SC-004 — ninguna fila se pierde sin contar) e imprime por socio: filas leídas, migradas, deduplicadas, a revisar, y el saldo resultante en las 3 monedas (para comparar contra quickstart.md Paso 2).
- [X] T013 [US1] Extender `backend/src/features/cuentas_socios/repository.py`: `calcular_saldo(id_socio)` devuelve `{"saldoPesos", "saldoUSD", "saldoKgCarne"}` (data-model.md §1); `listar_movimientos(id_socio)` incluye `importeUSD`/`importeKgCarne` por movimiento.
- [X] T014 [US1] Extender `backend/src/features/cuentas_socios/schemas.py`: `MovimientoCuentaSocio` agrega `importeUSD: float` e `importeKgCarne: float`; `DetalleSocioResponse` agrega `saldoUSD: float` y `saldoKgCarne: float` (manteniendo `saldo` existente como el valor en pesos, compatibilidad con contracts/api.md).
- [X] T015 [US1] Ajustar `backend/src/features/cuentas_socios/router.py` si hace falta pasar los campos nuevos de `repository.py` a `schemas.py` (sin cambiar rutas existentes).
- [X] T016 [P] [US1] Extender `frontend/src/services/cuentasSociosApi.ts`: tipos `MovimientoCuentaSocio`/`DetalleSocioResponse` con `importeUSD`, `importeKgCarne`, `saldoUSD`, `saldoKgCarne`.
- [X] T017 [US1] Extender `frontend/src/components/cuentas-socios/CuentaSocio.tsx`: mostrar los 3 saldos (pesos/USD/Kg carne) en la cabecera y columnas de USD/Kg carne en la tabla de movimientos (mismo patrón de formato numérico ya usado en el resto del sistema, `formatMoneda`).
- [X] T018 [US1] Correr `migrar_socios.py` contra `WC` (con backup verificado, T002) y validar contra la planilla siguiendo quickstart.md Paso 2 (incluida la consulta SQL de verificación de no-duplicados de los 7 movimientos ya cargados a mano).

**Checkpoint**: las 4 cuentas de socios están migradas y visibles en el sistema con sus 3 saldos — historia de usuario 1 completa y verificable de forma independiente.

---

## Phase 4: User Story 2 - Revisar movimientos con dudas antes de darlos por buenos (Priority: P2)

**Goal**: cualquier fila de cualquier hoja que no se pudo migrar con confianza queda visible y explicada, nunca perdida en silencio.

**Independent Test**: correr `migrar_socios.py` (US1) sobre una hoja con casos conocidos de datos incompletos y confirmar, vía `GET /api/migracion-cajas-giamigli/revision`, que esos casos aparecen listados con su motivo.

### Tests for User Story 2

- [X] T019 [P] [US2] Test de `migracion_cajas_giamigli.repository.listar_casos_a_revisar` con fixtures: filtra por `resuelto=True`/`False`/sin filtro, en `backend/tests/test_migracion_cajas_giamigli_router.py`.

### Implementation for User Story 2

- [X] T020 [US2] Verificar que el endpoint `GET /api/migracion-cajas-giamigli/revision` (creado en T008, Foundational) devuelve correctamente los casos insertados por `migrar_socios.py` (T012) tras su corrida real (T018) — sin código nuevo si T008 quedó bien implementado, solo prueba de integración.
- [X] T021 [P] [US2] Crear `frontend/src/services/migracionCajasGiamigliApi.ts`: `fetchCasosARevisar(resuelto?: boolean)`.
- [X] T022 [US2] Crear `frontend/src/app/finanzas/migracion-cajas-giamigli/revision/page.tsx` + componente de tabla de solo lectura (hoja, fila, motivo, datos crudos) — mismo patrón `DataTable` ya usado en el resto del sistema.

**Checkpoint**: los casos a revisar de lo ya migrado en US1 son visibles y consultables en el sistema.

---

## Phase 5: User Story 3 - Ver la caja de efectivo de Giamigli SA en el sistema (Priority: P3)

**Goal**: la caja de efectivo de Giamigli SA tiene su historial y saldo en el sistema, sin duplicar lo que ya está en `Pagos efectivo`.

**Independent Test**: migrar la hoja `Caja Efectivo Pesos` y verificar que el saldo final calculado por el sistema coincide con el saldo final de esa hoja en la planilla.

### Tests for User Story 3

- [X] T023 [P] [US3] Test de `cajas_efectivo.repository.calcular_saldo`/`listar_movimientos` con fixtures (suma acumulada con signo, orden por `Fecha, IdMovimiento`) en `backend/tests/test_cajas_efectivo_repository.py`.
- [X] T024 [P] [US3] Test de `GET /api/cajas-efectivo/{caja}/saldo` y `/movimientos` (paginado, 404 si `{caja}` no es `giamigli-sa`/`campo-chica`) en `backend/tests/test_cajas_efectivo_router.py`.
- [X] T025 [P] [US3] Test de la lógica de dedup de `migrar_caja_giamigli_sa.py`: proveedor resuelve a contacto + coincide con `Pagos efectivo` → no se inserta; proveedor no resuelve → se inserta como movimiento nuevo, en `backend/tests/test_migracion_cajas_giamigli_dedup.py` (extiende T010).

### Implementation for User Story 3

- [X] T026 [US3] Crear módulo `backend/src/features/cajas_efectivo/` (`__init__.py`, `repository.py` con `listar_movimientos(caja, page, pageSize)` y `calcular_saldo(caja)` sobre `MovimientosCajaEfectivo`, `schemas.py`, `router.py` con `GET /api/cajas-efectivo/{caja}/saldo` y `GET /api/cajas-efectivo/{caja}/movimientos` — 404 si `caja` no es `'giamigli-sa'`/`'campo-chica'`, per contracts/api.md).
- [X] T027 [US3] Implementar `backend/scripts/migracion_cajas_giamigli/migrar_caja_giamigli_sa.py`: usa `lector_excel.leer_hoja_caja(..., caja='GiamigliSA')`; para cada fila intenta `dedup.resolver_contacto_por_nombre`; si resuelve y `dedup.ya_existe_pago_efectivo` es `True`, no inserta (cuenta como "duplicado detectado", no genera `CasoARevisar`); si no, inserta en `MovimientosCajaEfectivo` (`Caja='GiamigliSA'`, `Cuenta`=Blue/White, sin `FormaPago`); hace `assert filas_leidas == migradas + duplicados_detectados + a_revisar` (SC-004); imprime resumen + saldo final (contracts/schema-script.md §5).
- [X] T028 [P] [US3] Crear `frontend/src/services/cajasEfectivoApi.ts`: `fetchSaldoCaja(caja)`, `fetchMovimientosCaja(caja, {page, pageSize})`.
- [X] T029 [US3] Crear `frontend/src/components/cajas-efectivo/CajaEfectivo.tsx` (solo lectura, análogo a `CuentaCorriente.tsx` pero sin buscador de contacto — una caja fija por pantalla) y `frontend/src/app/finanzas/cajas-efectivo/[caja]/page.tsx`.
- [X] T030 [US3] Correr `migrar_caja_giamigli_sa.py` contra `WC` y validar contra la planilla siguiendo quickstart.md Paso 3 (incluye confirmar que `Pagos efectivo` no cambió, FR-010).

**Checkpoint**: la caja de Giamigli SA está migrada, visible, y no duplica `Pagos efectivo` — historia de usuario 3 completa y verificable de forma independiente.

---

## Phase 6: User Story 4 - Ver la caja chica del campo en el sistema (Priority: P4)

**Goal**: la caja chica del campo tiene su historial y saldo en el sistema.

**Independent Test**: migrar la hoja `Caja chica campo` (la más chica de las 2 cajas) y verificar que el saldo final coincide con el de la planilla.

### Tests for User Story 4

- [X] T031 [P] [US4] Test de normalización `Debe`/`Haber` → `Importe` con signo para `Caja chica campo` en `lector_excel.leer_hoja_caja` (fixtures) en `backend/tests/test_migracion_cajas_giamigli_lector.py` (extiende T009).

### Implementation for User Story 4

- [X] T032 [US4] Implementar `backend/scripts/migracion_cajas_giamigli/migrar_caja_chica_campo.py`: usa `lector_excel.leer_hoja_caja(..., caja='CampoChica')`; inserta en `MovimientosCajaEfectivo` (`Caja='CampoChica'`, `FormaPago`, sin `Cuenta`); idempotencia por `(Caja, Fecha, Importe, Concepto)` (sin overlap conocido con otra tabla, contracts/schema-script.md §6); hace `assert filas_leidas == migradas + a_revisar` (SC-004); imprime resumen + saldo final.
- [X] T033 [US4] Confirmar en `frontend/src/app/finanzas/cajas-efectivo/[caja]/page.tsx` (T029) que `caja='campo-chica'` funciona sin cambios de código (módulo genérico) — solo agregar el link de navegación correspondiente si hace falta.
- [X] T034 [US4] Correr `migrar_caja_chica_campo.py` contra `WC` y validar contra la planilla siguiendo quickstart.md Paso 4.

**Checkpoint**: las 4 historias de usuario están completas — las 6 hojas de la planilla están migradas y visibles en el sistema.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: verificación end-to-end y cierre de la migración.

- [X] T035 Correr quickstart.md Paso 5 (`GET /api/migracion-cajas-giamigli/revision?resuelto=false`) y revisar a mano cada caso pendiente contra la fila real del Excel.
- [X] T036 Correr quickstart.md Paso 6 completo: verificar en la UI las 4 cuentas de socios y las 2 cajas, y confirmar por conteo de filas que `Compras`, `Det_Compras`, `Tarjetas_Resumenes_Lineas_Compras` y `Pagos efectivo` no cambiaron respecto de antes de la migración (spec FR-010).
- [X] T037 [P] Correr toda la suite de tests nuevos/extendidos (`pytest backend/tests/test_migracion_cajas_giamigli_*.py backend/tests/test_cajas_efectivo_*.py backend/tests/test_cuentas_socios_repository.py`) y confirmar que pasan junto con el resto de la suite existente.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias.
- **Foundational (Phase 2)**: depende de Setup — bloquea todas las historias de usuario.
- **US1 (Phase 3, P1)**: depende de Foundational. Sin dependencia de otras historias.
- **US2 (Phase 4, P2)**: depende de Foundational (T008); su prueba independiente usa datos generados por US1, pero el código de US2 (endpoint + frontend) no depende de que US1 esté implementada, solo de que la tabla exista.
- **US3 (Phase 5, P3)**: depende de Foundational. Sin dependencia de US1/US2.
- **US4 (Phase 6, P4)**: depende de Foundational y reutiliza el módulo `cajas_efectivo` creado en US3 (T026/T029) — en la práctica va después de US3, aunque el modelo de datos ya lo soporta desde Foundational.
- **Polish (Phase 7)**: depende de que las historias que se quieran validar estén completas.

### Parallel Opportunities

- T005, T006, T007, T008 (Foundational) pueden avanzar en paralelo una vez creadas las tablas (T003/T004).
- Dentro de cada historia, las tareas marcadas [P] (tests con fixtures, archivos de frontend nuevos) son paralelizables entre sí.
- US1 y US3 pueden implementarse en paralelo por personas distintas una vez terminada Foundational (no comparten archivos, salvo el paquete común `migracion_cajas_giamigli` ya terminado en Foundational).

---

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 1 (Setup) + Phase 2 (Foundational).
2. Phase 3 (US1) completa → **STOP y VALIDAR** contra quickstart.md Paso 2 → esto ya resuelve el caso real que originó la feature (saber cuánto le debe la empresa a cada socio, spec SC-005).

### Entrega incremental

1. Setup + Foundational → base lista.
2. US1 → las 4 cuentas de socios migradas (MVP).
3. US2 → cola de revisión visible (aprovecha lo generado por US1).
4. US3 → caja de Giamigli SA.
5. US4 → caja chica del campo.

Cada historia agrega valor sin romper las anteriores — ninguna toca los datos que migran las otras.
