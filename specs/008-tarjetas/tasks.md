---

description: "Task list for 008-tarjetas"
---

# Tasks: Tarjetas de Crédito

**Input**: Design documents from `specs/008-tarjetas/` (plan.md, spec.md, research.md, data-model.md, contracts/tarjetas-api.md, quickstart.md)

**Tests**: Incluidos — este proyecto usa contract tests (`backend/tests/contract/test_*.py`) como parte del flujo estándar (constitución principio V).

**Organization**: Tareas agrupadas por historia de usuario (spec.md, 4 historias). Setup y Foundational son prerrequisito bloqueante de todas las historias. FR-013 (edición/eliminación con lock) se resuelve dentro de la historia que ya posee cada entidad (US1 para resúmenes, US3 para compras en cuotas) porque spec.md no las desglosa en historias propias.

---

## Phase 1: Setup

- [X] T001 Verificar con `curl -X OPTIONS` que `main.py` sigue aceptando `PUT`/`DELETE`/`PATCH` en `allow_methods` de CORS (ya corregido en 006/007 — solo confirmar, no reimplementar).
- [X] T002 [P] Confirmar contra `WC` (nunca `LaHerencia`) que `dbo.Tarjetas`, `dbo.Tarjetas_Resumenes`, `dbo.Tarjetas_Resumenes_Lineas`, `dbo.[Tarjetas de Credito]`, `dbo.[Cuotas Tarjetas de Credito]` existen con las mismas columnas documentadas en `data-model.md` (ya verificado en la fase de plan por los especialistas — repetir el `INFORMATION_SCHEMA.COLUMNS` apuntando a `WC` antes de escribir ahí, mismo criterio que T002 de 007).

**Checkpoint**: Esquema confirmado en `WC`, CORS verificado — el resto de las fases puede empezar.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Tablas de bloqueo de edición y catálogo de tarjetas — dependencias compartidas por varias historias.

**⚠️ CRITICAL**: Ninguna historia de escritura (US1, US3) puede completarse sin las tablas de lock. US2 (cuenta corriente) y US4 (catálogo) necesitan el endpoint de catálogo de esta fase.

- [X] T003 [P] Ejecutar contra `WC` el DDL de `dbo.TarjetaResumenEditLocks` (`IdResumen` int, `LockToken` uniqueidentifier, `LockedAt` datetime, `ExpiresAt` datetime) — mismo patrón que `VentaHaciendaEditLocks`/`CompraEditLocks`, con el guard `assert DATABASE == "wc"` antes del DDL.
- [X] T004 [P] Ejecutar contra `WC` el DDL de `dbo.TarjetaCuotasEditLocks` (mismas columnas que T003, clave `IdPagoTarjeta`).
- [X] T005 `backend/src/features/tarjetas/{__init__.py,schemas.py,repository.py,router.py}`: `TarjetaResponse` (`idTarjeta`, `nombre`, `banco`, `activa`), `get_tarjetas(solo_activas: bool = False) -> list[dict]` (`SELECT` simple sobre `dbo.Tarjetas`, filtra `Activa = 1` si `solo_activas`), `GET /api/tarjetas?soloActivas=` — catálogo compartido por US1 (combo de resumen), US2 (selector de tarjeta) y US4.
- [X] T006 `backend/src/main.py`: registrar `tarjetas_router`.

**Checkpoint**: Tablas de lock y catálogo listos — las historias de usuario pueden implementarse.

---

## Phase 3: User Story 1 - Consultar resúmenes de tarjeta y sus consumos (Priority: P1) 🎯 MVP

**Goal**: Un usuario puede buscar resúmenes de tarjeta por rango de fechas, abrir uno (con o sin líneas) y ver su total calculado; puede cargar un resumen nuevo (con o sin líneas) y editarlo/eliminarlo con bloqueo exclusivo (FR-013).

**Independent Test**: `POST /api/tarjetas-resumenes` con cabecera completa + 1 línea → `201`, `totalCalculado` correcto; `GET /api/tarjetas-resumenes?idTarjeta=&fechaCierreDesde=&fechaCierreHasta=` lo encuentra (quickstart.md Escenarios 2-4).

### Tests for User Story 1

- [X] T007 [P] [US1] Contract test `GET /api/tarjetas-resumenes` sin filtro → `items: []` (FR-010) en `backend/tests/contract/test_tarjetas_resumenes_api.py`.
- [X] T008 [P] [US1] Contract test `GET /api/tarjetas-resumenes?idTarjeta=&fechaCierreDesde=&fechaCierreHasta=` con datos reales → devuelve coincidencias con `totalCalculado` ya calculado.
- [X] T009 [P] [US1] Contract test `GET /api/tarjetas-resumenes/{id}` de un resumen con líneas → cabecera completa (14 cargos de FR-008) + `lineas[]` + `totalCalculado` correcto, incluyendo un caso con línea o cargo de importe negativo (Edge Cases: sumar con signo real, sin `ABS()`).
- [X] T010 [P] [US1] Contract test `GET /api/tarjetas-resumenes/{id}` de un resumen sin líneas ("solo cabecera") → `200` con `lineas: []`, sin error (FR-009, Acceptance Scenario 3).
- [X] T011 [P] [US1] Contract test `POST /api/tarjetas-resumenes` con cabecera + 2 líneas (una negativa) → `201`, `totalCalculado` = `Σ(lineas.Importe)` + los 14 cargos de cabecera con su propio signo (data-model.md).
- [X] T012 [P] [US1] Contract test `POST /api/tarjetas-resumenes` con `lineas: []` → `201` igual, sin exigir al menos una línea (FR-009).
- [X] T013 [P] [US1] Contract test `POST /api/tarjetas-resumenes` sin `idTarjeta`/`codigo`/`fechaCierre`/`fechaVencimiento` → `400`.
- [X] T014 [P] [US1] Contract test `POST /api/tarjetas-resumenes` con el mismo `idTarjeta`+`codigo` de un resumen ya existente → `201` (no `400`) con `warnings` no vacío (FR-012).
- [X] T015 [P] [US1] Contract test `POST /api/tarjetas-resumenes/{id}/lock`: primer token adquiere (`200`), segundo token mientras el primero está vigente → `409`, `force: true` del segundo lo toma igual (`200`); `DELETE .../lock` libera con el token correcto (`204`), rechaza con otro token (`409`).
- [X] T016 [P] [US1] Contract test `PUT /api/tarjetas-resumenes/{id}`: sin lock vigente del token usado → `409`; con lock válido, cambia un cargo de cabecera → `200` con `totalCalculado` recalculado; `idResumen` inexistente → `404`.
- [X] T017 [P] [US1] Contract test `DELETE /api/tarjetas-resumenes/{id}`: `404` si no existe, `409` sin lock del token usado, `204` con lock válido — verificar (test de repository) que no quedan líneas huérfanas en `Tarjetas_Resumenes_Lineas`.

### Implementation for User Story 1

- [X] T018 [US1] `backend/src/features/tarjetas_resumenes/{__init__.py,schemas.py}`: `LineaConsumoInput` (`fechaCompra`: date requerido, `detalle`: str requerido máx. 255 caracteres, `importe`: money requerido — admite negativo, `fechaVencimientoCompra`: date opcional, `idContacto`: int opcional, `nroDocumento`: str opcional máx. 50 caracteres), `ResumenAltaRequest` (`idTarjeta`: int requerido, `codigo`: str requerido máx. 80 caracteres, `fechaCierre`/`fechaVencimiento`: date requeridos, los 14 cargos de FR-008 como `float` opcionales default 0 — admiten negativo, sin validación de mínimo, `lineas`: list default `[]`), `ResumenDetalleResponse` (cabecera + `totalCalculado` + `lineas` + `warnings: list[str]`), `ResumenListItem`, `LockRequest`/`LockResponse` (mismo shape que `ventas_hacienda`).
- [X] T019 [US1] `backend/src/features/tarjetas_resumenes/repository.py`: `validar_resumen(id_tarjeta) -> list[str]` — `idTarjeta` debe existir en `Tarjetas`.
- [X] T020 [US1] `backend/src/features/tarjetas_resumenes/repository.py`: `calcular_total(cabecera: dict, lineas: list[dict]) -> float` puro (sin acceso a base) que implementa exactamente `Σ(lineas.Importe) + ImpuestoSellos + GastosAdmin + MantCuenta + RenovAnual + PromocionBNA + CreditoContingente + IntFinanc + IntCompens + IVA105 + PercepIVA105 + IVA21 + PercepIVA21 + PercepIIBB + AjusteResAnterior`, cada término con su propio signo (data-model.md, research.md §5) — sin `ABS()` en ningún término.
- [X] T021 [US1] `backend/src/features/tarjetas_resumenes/repository.py`: `search_resumenes(id_tarjeta, fecha_cierre_desde, fecha_cierre_hasta, fecha_vencimiento_desde, fecha_vencimiento_hasta, page, page_size) -> tuple[list[dict], int]` — sin ningún filtro, no ejecuta la query principal (devuelve `[], 0` — FR-010, mismo patrón que `ventas_granos.repository.search_ventas`).
- [X] T022 [US1] `backend/src/features/tarjetas_resumenes/repository.py`: `get_resumen_detalle(id_resumen) -> dict | None`, `get_lineas(id_resumen) -> list[dict]`.
- [X] T023 [US1] `backend/src/features/tarjetas_resumenes/repository.py`: `create_resumen(cabecera, lineas) -> int` — valida con T019, arma la transacción (1 INSERT a `Tarjetas_Resumenes` con `OUTPUT INSERTED.IdResumen`, N INSERT a `Tarjetas_Resumenes_Lineas`) vía `execute_write_transaction`.
- [X] T024 [US1] `backend/src/features/tarjetas_resumenes/repository.py`: `hay_resumen_duplicado(id_tarjeta, codigo, excluir_id_resumen=None) -> bool` (FR-012, advertencia no bloqueante).
- [X] T025 [US1] `backend/src/features/tarjetas_resumenes/router.py`: `GET /api/tarjetas-resumenes`, `GET /api/tarjetas-resumenes/{id}` (`totalCalculado` vía T020), `POST /api/tarjetas-resumenes` (valida, crea, arma `warnings` con T024, `201`).
- [X] T026 [US1] `backend/src/features/tarjetas_resumenes/repository_locks.py`: `adquirir_lock`/`liberar_lock`/`verificar_lock` sobre `dbo.TarjetaResumenEditLocks` — copia exacta del patrón de `ventas_hacienda/repository_locks.py`, mismo TTL.
- [X] T027 [US1] `backend/src/features/tarjetas_resumenes/repository.py`: `update_resumen(id_resumen, cabecera, lineas) -> dict` — reemplazo total en una sola `execute_write_transaction` (DELETE de líneas existentes, UPDATE de cabecera, INSERT de líneas nuevas, recalcula `totalCalculado` con T020).
- [X] T028 [US1] `backend/src/features/tarjetas_resumenes/repository.py`: `delete_resumen(id_resumen) -> None` — transacción única que borra `Tarjetas_Resumenes_Lineas`, `TarjetaResumenEditLocks`, y por último `Tarjetas_Resumenes`.
- [X] T029 [US1] `backend/src/features/tarjetas_resumenes/router.py`: `POST/DELETE /api/tarjetas-resumenes/{id}/lock`, `PUT /api/tarjetas-resumenes/{id}` (requiere `X-Lock-Token`, `409`/`404` según corresponda), `DELETE /api/tarjetas-resumenes/{id}` (`204`).
- [X] T030 [US1] `frontend/src/services/tarjetasResumenesApi.ts`: `fetchResumenes`, `fetchResumenDetalle`, `crearResumen`, `actualizarResumen`, `eliminarResumen`, `adquirirLock`, `liberarLock`, tipos espejando el contrato.
- [X] T031 [P] [US1] `frontend/src/components/tarjetas-resumenes/ResumenesListado.tsx`: vacío por defecto hasta aplicar un filtro (FR-010, mismo patrón que `ComprasListado.tsx`), filtro de tarjeta vía `GET /api/tarjetas` (T005), filtros/orden/página persistidos en la URL.
- [X] T032 [P] [US1] `frontend/src/components/tarjetas-resumenes/ResumenForm.tsx`: cabecera (combo de tarjeta filtrado a `soloActivas=true` salvo que la tarjeta de un resumen existente ya sea inactiva — Historia 4, Acceptance Scenario 2; los 14 cargos de FR-008 en grid responsive) + grilla editable de líneas (agregar/quitar filas: fecha, detalle, importe, fecha vencimiento, contacto opcional vía `ContactoSelect`, documento opcional) + `totalCalculado` en vivo + modo edición con lock (mismo patrón que `VentaHaciendaForm.tsx`: adquiere al montar, renueva, libera al desmontar/`pagehide`, botón "Forzar edición" en `409`) + botón "Eliminar resumen" con `window.confirm`.
- [X] T033 [US1] `frontend/src/app/finanzas/tarjetas/resumenes/{page.tsx,nuevo/page.tsx,[idResumen]/page.tsx,[idResumen]/editar/page.tsx}`: listado, alta, detalle de solo lectura y edición, montando `ResumenesListado`/`ResumenForm`.

**Checkpoint**: Historia 1 funcional de punta a punta — alta/edición/eliminación de resúmenes con bloqueo exclusivo, verificable contra `WC` sin tocar `LaHerencia`.

---

## Phase 4: User Story 2 - Ver la cuenta corriente de una tarjeta (Priority: P2)

**Goal**: Un usuario puede ver los movimientos y el saldo acumulado de una tarjeta (un movimiento por resumen, FR-002) y navegar de cada movimiento al resumen de origen (FR-003).

**Independent Test**: `GET /api/tarjetas/{idTarjeta}/movimientos` de una tarjeta con varios resúmenes reales → un movimiento por resumen ordenado por `fechaCierre`, `saldoAcumulado` correcto; clic en un movimiento navega al resumen (quickstart.md Escenarios 7-8).

### Tests for User Story 2

- [X] T034 [P] [US2] Contract test `GET /api/tarjetas/{idTarjeta}/movimientos` en `backend/tests/contract/test_tarjetas_api.py`: un movimiento por resumen de esa tarjeta, ordenados por `fechaCierre`, `deuda`/`credito` con el signo correcto (`totalCalculado > 0` → deuda, `< 0` → crédito) y `saldoAcumulado` = suma corrida (data-model.md).
- [X] T035 [P] [US2] Contract test que confirma que ninguna cuota de `tarjetas_cuotas` aparece en la respuesta de `movimientos` (decisión de "solo resúmenes", evita doble conteo — research.md §3).

### Implementation for User Story 2

- [X] T036 [US2] `backend/src/features/tarjetas/schemas.py`: `MovimientoTarjetaResponse` (`idResumen`, `fecha`, `codigo`, `deuda`, `credito`, `saldoAcumulado`), `MovimientosTarjetaResponse` (`idTarjeta`, `tarjeta`, `movimientos: list[MovimientoTarjetaResponse]`).
- [X] T037 [US2] `backend/src/features/tarjetas/repository.py`: `get_movimientos(id_tarjeta) -> list[dict]` — trae los resúmenes de esa tarjeta ordenados por `FechaCierre`/`IdResumen`, calcula `totalCalculado` por resumen reutilizando `tarjetas_resumenes.repository.calcular_total` (T020) + sus líneas (T022), arma `deuda`/`credito` con el criterio de signo de `research.md §5`, y `saldoAcumulado` como suma corrida en Python (no requiere `OVER()` de SQL Server dado el volumen bajo por tarjeta — máx. decenas de resúmenes).
- [X] T038 [US2] `backend/src/features/tarjetas/router.py`: `GET /api/tarjetas/{idTarjeta}/movimientos`.
- [X] T039 [US2] `frontend/src/services/tarjetasApi.ts`: `fetchMovimientos(idTarjeta)`.
- [X] T040 [US2] `frontend/src/components/tarjetas/TarjetaCuentaCorriente.tsx`: tabla de movimientos con saldo acumulado (mismo patrón visual que `cuentas-corrientes/page.tsx` sin reusar el componente — research.md §7), cada fila linkea a `/finanzas/tarjetas/resumenes/{idResumen}` (FR-003).
- [X] T041 [US2] `frontend/src/app/finanzas/tarjetas/[idTarjeta]/cuenta-corriente/page.tsx`: monta `TarjetaCuentaCorriente`; enlace desde el catálogo de tarjetas (US4) a esta ruta.

**Checkpoint**: Historia 2 funcional — saldo acumulado por tarjeta y navegación al resumen de origen verificables contra `WC`.

---

## Phase 5: User Story 3 - Cargar una compra en cuotas (Priority: P3)

**Goal**: Un usuario puede registrar una compra en cuotas (sin tarjeta asociada, FR-004) y el sistema genera el cronograma automáticamente (FR-005); puede buscarlas, marcar cuotas como cobradas (FR-007), y editar/eliminar con bloqueo exclusivo (FR-013, regenerando el cronograma completo según FR-007a).

**Independent Test**: `POST /api/tarjetas-cuotas` con `importeTotal=10000`, `cantidadCuotas=3` → 3 cuotas de `3333.33/3333.33/3333.34` con vencimientos mensuales sucesivos (quickstart.md Escenario 5).

### Tests for User Story 3

- [X] T042 [P] [US3] Contract test `GET /api/tarjetas-cuotas` sin filtro → `items: []` (FR-006, Clarifications 2026-09-18) en `backend/tests/contract/test_tarjetas_cuotas_api.py`.
- [X] T043 [P] [US3] Contract test `GET /api/tarjetas-cuotas?idContacto=&fechaDesde=&fechaHasta=` con datos reales → devuelve coincidencias con `cantidadCuotas`/estado.
- [X] T044 [P] [US3] Contract test `GET /api/tarjetas-cuotas/{id}` → cronograma completo (`cuotas[]`) con `importeTotal = Σ(cuotas.importe)`.
- [X] T045 [P] [US3] Contract test `POST /api/tarjetas-cuotas` con `importeTotal=10000`, `cantidadCuotas=3` → `201`, cuotas `3333.33/3333.33/3333.34` (suma exacta `10000`), vencimientos mensuales sucesivos desde `fecha` (FR-005, Acceptance Scenario 4).
- [X] T046 [P] [US3] Contract test `POST /api/tarjetas-cuotas` con `cantidadCuotas=1` → `201`, una sola cuota con el importe total completo (Edge Case).
- [X] T047 [P] [US3] Contract test `POST /api/tarjetas-cuotas` sin `idContacto`/`importeTotal`/`cantidadCuotas` o con `cantidadCuotas < 1` → `400`.
- [X] T048 [P] [US3] Contract test `PATCH /api/tarjetas-cuotas/{id}/cuotas/{idCuota}` con `{"cobrado": true}` → `200`, reflejado en `GET` posterior (FR-007, Acceptance Scenario 3).
- [X] T049 [P] [US3] Contract test `POST/DELETE /api/tarjetas-cuotas/{id}/lock` — mismo comportamiento que resúmenes (T015), incluido `force: true`.
- [X] T050 [P] [US3] Contract test `PUT /api/tarjetas-cuotas/{id}`: sin lock → `409`; con lock válido y `importeTotal`/`cantidadCuotas` distintos → regenera el cronograma completo y una cuota previamente marcada `cobrado=true` vuelve a `false` (FR-007a, Clarifications 2026-09-18); `idPagoTarjeta` inexistente → `404`.
- [X] T051 [P] [US3] Contract test `DELETE /api/tarjetas-cuotas/{id}`: `404`/`409`/`204` según corresponda — verificar que no quedan cuotas huérfanas en `Cuotas Tarjetas de Credito`.

### Implementation for User Story 3

- [X] T052 [US3] `backend/src/features/tarjetas_cuotas/{__init__.py,schemas.py}`: `CompraCuotasAltaRequest` (`idContacto`: int requerido, `fecha`: date requerido, `nroComprobante`: int requerido, `importeTotal`: money requerido, `cantidadCuotas`: int requerido mínimo 1), `CuotaResponse` (`idCuota`, `numeroCuota`, `fechaVencimiento`, `importe`, `cobrado: bool` — mapeado desde `'S'`/`'N'`, no `bit`, data-model.md), `CompraCuotasDetalleResponse` (cabecera + `importeTotal` + `cuotas: list[CuotaResponse]`), `MarcarCobradaRequest` (`cobrado: bool`), `LockRequest`/`LockResponse`.
- [X] T053 [US3] `backend/src/features/tarjetas_cuotas/calculo_cuotas.py`: `generar_cronograma(fecha_compra: date, importe_total: float, cantidad_cuotas: int) -> list[dict]` puro — `cuotaBase = round(importeTotal / cantidadCuotas, 2)`, cuotas `1..N-1` = `cuotaBase`, cuota `N` = `importeTotal - cuotaBase*(N-1)` (absorbe el resto), `fechaVencimiento[i] = fecha_compra + i meses` (data-model.md).
- [X] T054 [US3] `backend/src/features/tarjetas_cuotas/repository.py`: `validar_compra(id_contacto) -> list[str]` — `idContacto` debe existir en `Contactos`.
- [X] T055 [US3] `backend/src/features/tarjetas_cuotas/repository.py`: `search_compras(id_contacto, fecha_desde, fecha_hasta, page, page_size) -> tuple[list[dict], int]` — sin ningún filtro, devuelve `[], 0` (FR-006, Clarifications 2026-09-18).
- [X] T056 [US3] `backend/src/features/tarjetas_cuotas/repository.py`: `get_detalle(id_pago_tarjeta) -> dict | None`, `get_cuotas(id_pago_tarjeta) -> list[dict]`.
- [X] T057 [US3] `backend/src/features/tarjetas_cuotas/repository.py`: `create_compra(cabecera) -> int` — valida con T054, genera cronograma con T053, arma la transacción (1 INSERT a `[Tarjetas de Credito]` con `OUTPUT INSERTED.IdPagoTarjeta`, N INSERT a `[Cuotas Tarjetas de Credito]`) vía `execute_write_transaction`.
- [X] T058 [US3] `backend/src/features/tarjetas_cuotas/repository.py`: `marcar_cobrada(id_cuota, cobrado: bool) -> None` — `UPDATE` de un solo campo, mapea `bool` a `'S'`/`'N'`.
- [X] T059 [US3] `backend/src/features/tarjetas_cuotas/router.py`: `GET /api/tarjetas-cuotas`, `GET /api/tarjetas-cuotas/{id}`, `POST /api/tarjetas-cuotas`, `PATCH /api/tarjetas-cuotas/{id}/cuotas/{idCuota}` (sin lock, FR-007 — cambio de un solo campo).
- [X] T060 [US3] `backend/src/features/tarjetas_cuotas/repository_locks.py`: mismo patrón que `tarjetas_resumenes/repository_locks.py` (T026), sobre `dbo.TarjetaCuotasEditLocks`.
- [X] T061 [US3] `backend/src/features/tarjetas_cuotas/repository.py`: `update_compra(id_pago_tarjeta, cabecera) -> dict` — regenera el cronograma completo siempre (DELETE de todas las cuotas existentes + re-generación con T053 + INSERT, en una sola transacción — FR-007a, Clarifications 2026-09-18, sin excepción aunque no cambie `importeTotal`/`cantidadCuotas`) y `delete_compra(id_pago_tarjeta) -> None` (borra cuotas, lock, y cabecera).
- [X] T062 [US3] `backend/src/features/tarjetas_cuotas/router.py`: `POST/DELETE /api/tarjetas-cuotas/{id}/lock`, `PUT /api/tarjetas-cuotas/{id}`, `DELETE /api/tarjetas-cuotas/{id}`.
- [X] T063 [US3] `frontend/src/services/tarjetasCuotasApi.ts`: `fetchCompras`, `fetchCompraDetalle`, `crearCompra`, `actualizarCompra`, `eliminarCompra`, `marcarCobrada`, `adquirirLock`, `liberarLock`.
- [X] T064 [P] [US3] `frontend/src/components/tarjetas-cuotas/ComprasCuotasListado.tsx`: vacío por defecto hasta aplicar un filtro (FR-006, Clarifications 2026-09-18), filtros de contacto (`ContactoSelect`)/fecha persistidos en la URL.
- [X] T065 [P] [US3] `frontend/src/components/tarjetas-cuotas/CompraCuotasForm.tsx`: cabecera (contacto, fecha, comprobante, importe total, cantidad de cuotas) + cronograma generado de solo lectura tras guardar con toggle "cobrado"/"no cobrada" por fila + aviso visible de que editar importe/cantidad regenera el cronograma y pierde el estado cobrado (FR-007a) + modo edición con lock + botón "Eliminar compra" con confirmación.
- [X] T066 [US3] `frontend/src/app/finanzas/tarjetas/compras-en-cuotas/{page.tsx,nueva/page.tsx,[idPagoTarjeta]/editar/page.tsx}`.

**Checkpoint**: Historia 3 funcional de punta a punta — alta/edición/eliminación de compras en cuotas con cronograma automático, verificable contra `WC`.

---

## Phase 6: User Story 4 - Consultar el catálogo de tarjetas (Priority: P4)

**Goal**: Un usuario puede ver el catálogo de tarjetas (nombre, banco, activa/inactiva) como referencia y como punto de entrada a la cuenta corriente de cada una.

**Independent Test**: Abrir el listado de tarjetas y verificar que muestra las 5 tarjetas reales de `WC` con su banco y si están activas (quickstart.md Escenario 1).

### Tests for User Story 4

- [X] T067 [P] [US4] Contract test `GET /api/tarjetas` (ya implementado en Foundational, T005) devuelve las 5 tarjetas reales con `nombre`/`banco`/`activa`; `GET /api/tarjetas?soloActivas=true` filtra correctamente en `backend/tests/contract/test_tarjetas_api.py`.

### Implementation for User Story 4

- [X] T068 [US4] `frontend/src/services/tarjetasApi.ts`: `fetchTarjetas(soloActivas?: boolean)` (el endpoint ya existe desde T005).
- [X] T069 [P] [US4] `frontend/src/components/tarjetas/TarjetasListado.tsx`: catálogo con nombre/banco/badge activa-inactiva, cada fila linkea a `/finanzas/tarjetas/{idTarjeta}/cuenta-corriente` (US2).
- [X] T070 [US4] `frontend/src/app/finanzas/tarjetas/page.tsx`: monta `TarjetasListado`.
- [X] T071 [US4] `frontend/src/components/layout/NavHeader.tsx`: agregar `{ href: "/finanzas/tarjetas", label: "Tarjetas" }` dentro del submenu de `Finanzas`, entre "Cuentas corrientes" e "Impuestos y retenciones" (research.md §7).

**Checkpoint**: Las 4 historias funcionan de punta a punta, integradas.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T072 [P] Mostrar el aviso no bloqueante de `warnings` (resumen duplicado, FR-012) como toast en `ResumenForm.tsx` (`useToast`, ya existente).
- [X] T073 Ejecutar `cd backend && python -m pytest -q` y confirmar que todos los tests (existentes + nuevos de esta feature) pasan. Ejecutado 2026-09-18: 241 passed (39 contract tests nuevos de 008-tarjetas + toda la suite previa sin regresión).
- [X] T074 Ejecutar `cd frontend && npx tsc --noEmit -p . && npx eslint .` y confirmar cero errores. Ejecutado 2026-09-18: ambos comandos terminan sin errores.
- [X] T075 Correr manualmente los 10 escenarios de `specs/008-tarjetas/quickstart.md` contra el backend real (`WC`) y verificar contra SQL Server que ninguna escritura llegó a `LaHerencia` (SC-005) — mismo criterio que T086 de 007. Ejecutado 2026-09-18 contra `WC` real: catálogo (5 tarjetas reales), listado de resúmenes vacío por defecto y con filtro real, detalle con líneas y "solo cabecera" (`IdResumen=675` real), alta con línea negativa + ajuste negativo (`totalCalculado` verificado a mano: 15230-200+120.5+350.2-50=15450.7 ✓), lock/force/PUT recalcula total/DELETE sin huérfanos, alta de compra en cuotas con redondeo (3333.33/3333.33/3333.34, suma exacta 10000), cuota única, marcar cobrada, PUT regenera cronograma completo y pierde `cobrado` (FR-007a confirmado), DELETE sin huérfanos en `Cuotas Tarjetas de Credito`, cuenta corriente de tarjeta (80 movimientos reales de Mastercard BNA, saldo acumulado correcto), nav confirmado por código. **Dos bugs reales encontrados y corregidos durante esta verificación** (no eran evidentes hasta probar contra datos reales): (1) el aviso de duplicado (FR-012) se disparaba siempre en la primera alta porque comparaba contra la fila recién insertada sin excluirla — mismo bug preexistente encontrado también en `ventas_hacienda`/`ventas_granos` (007) y corregido ahí también; (2) `IdAuto` de `Cuotas Tarjetas de Credito` no es identity (a diferencia de lo asumido) y `IdCuotaTarjeta` tiene un índice único real que no admite múltiples NULL — se corrigió generando ambos valores a mano (`MAX(IdAuto)+1`, `'CUOT'+IdAuto`) igual que hacía Access. Todos los datos de prueba creados durante la verificación fueron eliminados al finalizar.
- [X] T076 Ejecutar el Escenario 9 de `quickstart.md` (SC-002): para las 5 tarjetas reales, sumar a mano `totalCalculado` de todos sus resúmenes reales y comparar contra `saldoAcumulado` final de `GET /api/tarjetas/{idTarjeta}/movimientos` — documentar el resultado (mismo criterio que T087 de 007). Ejecutado 2026-09-18: recalculado independientemente en SQL crudo (no reutilizando el código de la app) para las 5 tarjetas reales (AgroNacion, Corporativa Nacion, Mastercard BNA, Visa Galicia, Galicia Rural) — coincidencia exacta centavo a centavo contra el `saldoAcumulado` final de la API en las 5: 27361830.22 / 2987101.71 / 1132271.56 / 14359531.30 / 5334384.32.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias — empieza de inmediato.
- **Foundational (Phase 2)**: depende de Setup — bloquea US1 y US3 (tablas de lock) y provee el catálogo que necesitan US1/US2/US4.
- **US1 (Phase 3, P1)**: depende solo de Foundational. Es la historia con mayor volumen real (293 resúmenes) y la base para US2.
- **US2 (Phase 4, P2)**: depende de que existan resúmenes reales para mostrar (no depende técnicamente de que US1 esté "completa" como código, pero reutiliza `calcular_total`/`get_lineas` de `tarjetas_resumenes` — T037 depende de T020/T022).
- **US3 (Phase 5, P3)**: depende solo de Foundational — dominio de datos completamente independiente de US1/US2 (sin relación estructural, research.md).
- **US4 (Phase 6, P4)**: depende solo del catálogo de Foundational (T005) — la más independiente de las 4, aunque de menor prioridad de negocio.
- **Polish (Phase 7)**: depende de que las historias que se quieran entregar estén completas.

### Parallel Opportunities

- T003, T004 (Foundational) son paralelas entre sí (tablas distintas).
- T007-T017 (tests de US1) son paralelas entre sí.
- T031, T032 (componentes de frontend de US1) son paralelas entre sí.
- T034-T035 (tests de US2), T042-T051 (tests de US3), T067 (test de US4) son paralelas entre sí dentro de cada historia.
- T064, T065 (componentes de frontend de US3) son paralelas entre sí.
- US3 puede desarrollarse en paralelo a US1/US2 por un segundo desarrollador/sesión una vez cerrada Foundational — es un dominio de datos sin relación estructural con resúmenes/cuenta corriente (research.md). US4 puede hacerse en cualquier momento tras Foundational.

---

## Implementation Strategy

### MVP First (User Story 1)

1. Completar Phase 1 (Setup) y Phase 2 (Foundational) — bloqueante para escritura.
2. Completar Phase 3 (US1) — alta/consulta/edición/eliminación de resúmenes completa.
3. Validar con quickstart.md Escenarios 1-4 antes de seguir.

### Incremental Delivery

1. Setup + Foundational → base lista.
2. US1 → demo: resúmenes de tarjeta funcionando end-to-end (MVP).
3. US2 → demo: cuenta corriente por tarjeta con navegación al resumen de origen.
4. US3 → demo: compras en cuotas con cronograma automático (dominio independiente).
5. US4 → demo: catálogo de tarjetas como punto de entrada a la cuenta corriente.
6. Polish → verificación final de no regresión y de la regla de oro (`WC`-only).
