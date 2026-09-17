---

description: "Task list for 006-carga-compras"
---

# Tasks: Carga de Compras (alta y edición)

**Input**: Design documents from `specs/006-carga-compras/` (plan.md, spec.md, research.md, data-model.md, contracts/compras-alta-api.md, quickstart.md)

**Tests**: Incluidos — este proyecto ya usa contract tests (`backend/tests/contract/test_*.py`) como parte del flujo estándar (principio V de la constitución).

**Organization**: Tareas agrupadas por historia de usuario (spec.md). Setup y Foundational son prerrequisito bloqueante de todas las historias.

## Phase 1: Setup

- [x] T001 Confirmar cómo resuelve el backend real (mismo pyodbc/DSN `SQL_LaHerencia` que usa `backend/src/db/connection.py`) las columnas `Campaña`/`IdCampaña` de `dbo.Det_Compras` (research.md §4). **Resuelto (2026-09-17)**: el carácter roto (`0xf1`) visto en `INFORMATION_SCHEMA.COLUMNS` es un artefacto de impresión en consola, no un problema real del driver — confirmado que `SELECT [Campaña] FROM dbo.Det_Compras` vía pyodbc (mismo código que usa el backend) funciona correctamente y devuelve datos reales (ej. "No Aplica"). Se usa el literal `[Campaña]`/`[IdCampaña]` normal en el SQL, sin workaround.
- [x] T002 [P] Ejecutar contra `WC` (nunca `LaHerencia`) el DDL de la tabla nueva `dbo.CompraEditLocks` (data-model.md). **Hecho (2026-09-17)**: tabla creada con un guard explícito (`assert DATABASE == "wc"` antes del DDL, ya que `execute_write` rechaza DDL por diseño) y verificada — existe en `WC` (1 tabla) y no existe en `LaHerencia` (0 tablas).

**Checkpoint**: Esquema y encoding confirmados; el resto de las fases puede empezar.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Infraestructura de escritura transaccional y de bloqueo que TODAS las historias de usuario necesitan.

**⚠️ CRITICAL**: Ninguna historia de usuario puede completarse sin esta fase.

- [x] T003 Agregar `execute_write_transaction(statements: list[tuple[str, tuple]]) -> list` a `backend/src/db/connection.py` (research.md §1): una sola conexión con `autocommit=False`, valida cada sentencia igual que `execute_write` (solo INSERT/UPDATE/DELETE, sin DDL, sin múltiples statements por entrada, `_assert_target_is_wc()` una vez), `commit()` si todas tienen éxito, `rollback()` ante cualquier excepción; soporta sentencias con `OUTPUT` devolviendo el valor escalar igual que `execute_insert_returning_id`.
- [x] T004 [P] Tests unitarios de `execute_write_transaction` en `backend/tests/test_db_connection.py`: rechaza si `DATABASE` es `LaHerencia`/`LAHERENCIA` (case-insensitive); hace rollback completo si una sentencia intermedia falla (mock de cursor que lanza en la 2da llamada, verificar que la 1ra no persiste); rechaza sentencias que no sean INSERT/UPDATE/DELETE; rechaza DDL/multi-statement igual que `execute_write`.
- [x] T005 [P] `backend/src/features/compras/repository_locks.py`: `adquirir_lock(id_compra, lock_token) -> LockInfo` (crea o renueva si no hay lock vigente de otro token; `ExpiresAt = ahora + 15 minutos`), `liberar_lock(id_compra, lock_token) -> bool` (solo si el token coincide), `verificar_lock(id_compra, lock_token) -> bool` (True si no hay lock vigente o el token coincide) — todas usan `execute_write`/`fetch_one` sobre `dbo.CompraEditLocks`, tratando un lock con `ExpiresAt < ahora` como inexistente.
- [x] T006 [P] Ampliar `get_filtros()` en `backend/src/features/compras/repository.py` para incluir además los catálogos `destinos` (`DestinoCompras`), `unidadesMedida` (`UnidadesMedida`) y `campañas` (`Campañas`, usando el nombre de columna confirmado en T001) — ampliación aditiva de `FiltrosComprasResponse` (no rompe los consumidores actuales de `GET /api/compras/filtros`, spec 002).

**Checkpoint**: Transacción multi-tabla, bloqueo y catálogos listos — las historias de usuario pueden implementarse.

---

## Phase 3: User Story 1 - Cargar una compra nueva completa (Priority: P1) 🎯 MVP

**Goal**: Un usuario puede crear una compra completa (cabecera + al menos una línea, con o sin vencimientos) que queda escrita en `WC` y visible en el listado existente de Compras.

**Independent Test**: `POST /api/compras` con un proveedor real, una línea y sin vencimientos → `201`, totales calculados correctamente, la compra aparece en `GET /api/compras` (quickstart.md Escenario 1).

### Tests for User Story 1

- [x] T007 [P] [US1] Contract test `POST /api/compras` (alta exitosa, cabecera + 1 línea, sin vencimientos) en `backend/tests/contract/test_compras_alta_api.py`, verificando `subtotalNeto`/`ivaCabecera`/`importeTotal` calculados según data-model.md.
- [x] T008 [P] [US1] Contract test `POST /api/compras` con moneda `"Dolares"` y `tipoDeCambio` cargado → `pesificado.importeTotal == importeTotal * tipoDeCambio`; y sin `tipoDeCambio` → `400` (FR-007).
- [x] T009 [P] [US1] Contract test `POST /api/compras` sin `idContacto` o con `lineas: []` → `400`, sin crear ningún registro (FR-002, Historia 1 Escenario 3).
- [x] T010 [P] [US1] Contract test `POST /api/compras` con `idContacto` de tipo no permitido (ej. "Consignatario") o `idRubro`/`idCentroCosto`/`idDestino` inexistente → `400` (FR-013).

### Implementation for User Story 1

- [x] T011 [US1] `backend/src/features/compras/schemas.py`: agregar `LineaInput` (productoServicio: str requerido, cantidad: float requerido sin mínimo — FR-004a, precioUnitario: float requerido sin mínimo — FR-004a, iva: float requerido, unidad/idCentroCosto/idDestino/idRubro/campaña opcionales, ajusteFinanciero: bool default False), `VencimientoInput` (fechaVencimiento: date requerido), `CompraAltaRequest` (idContacto: int requerido, fecha: date requerido, tipo: Literal["A","B","C","M","X"] requerido, tipoDocumento: Literal["Factura","Nota de Crédito","Nota de Débito","C. Deposito Cereales"] requerido, numeroDocumento: str requerido máx. 15 caracteres, moneda: Literal["Pesos","Dolares"] requerido, tipoDeCambio: float opcional, resto de conceptos monetarios opcionales default 0, lineas: list[LineaInput] mínimo 1 elemento, vencimientos: list[VencimientoInput] default []), `CompraDetalleResponse` (cabecera + `subtotalNeto`/`ivaCabecera`/`importeTotal`/`pesificado: PesificadoBlock | None`/`lineas`/`vencimientos`/`warnings: list[str]`).
- [x] T012 [US1] `backend/src/features/compras/repository.py`: `validar_compra(id_contacto, moneda, tipo_de_cambio, lineas) -> list[str]` — devuelve la lista de errores (vacía si todo válido): `idContacto` debe existir en `Contactos` con `Tipo Contacto` ∈ {Proveedor, Multiple, Organismo, Empleado, Banco}; cada `idRubro`/`idCentroCosto`/`idDestino` no nulo debe existir en su catálogo real; **si `moneda == "Dolares"`, `tipoDeCambio` debe venir no nulo y mayor a 0 (FR-007) — agregar el error "El tipo de cambio es obligatorio para compras en Dólares" si no se cumple.**
- [x] T013 [US1] `backend/src/features/compras/repository.py`: `calcular_totales(lineas, cabecera) -> dict` puro (sin acceso a base) que implementa exactamente las fórmulas de data-model.md: subtotal/importeIva por línea, `ivaCabecera = Σ(importeIva línea) + 0.105 × (comision+guias+financiacion+gastosVarios)`, `importeTotal`, y `pesificado` (todo × tipoDeCambio) solo si moneda = "Dolares".
- [x] T014 [US1] `backend/src/features/compras/repository.py`: `create_compra(cabecera, lineas, vencimientos) -> int` — valida con `validar_compra` (T012, incluye el chequeo de tipo de cambio obligatorio de FR-007), calcula con T013, arma la lista de sentencias (1 INSERT a `Compras` con `OUTPUT INSERTED.IdDeuda`, N INSERT a `Det_Compras`, M INSERT a `[Vencimiento Compras]`, todas con el `IdCompra` recién obtenido) y las ejecuta con `execute_write_transaction` (T003). Aplica los defaults de línea si vienen nulos: `idCentroCosto` → el Id de "Adm. General", `idDestino` → el Id de "General", `campaña` → "No Aplica" (FR-011).
- [x] T015 [US1] `backend/src/features/compras/repository.py`: `hay_documento_duplicado(id_contacto, numero_documento, excluir_id_compra=None) -> bool` (FR-014) — usado por el router para poblar `warnings`, nunca bloquea el guardado.
- [x] T016 [US1] `backend/src/features/compras/router.py`: `POST /api/compras` — valida con `validar_compra` (T012, 400 con el mensaje de error correspondiente si falla, incluyendo el caso de tipo de cambio faltante en moneda Dólares), crea con T014, arma `warnings` con T015, devuelve `201` con `CompraDetalleResponse`.
- [x] T017 [US1] `frontend/src/services/comprasApi.ts`: agregar `crearCompra(input: CompraAltaInput): Promise<CompraDetalle>` (POST) y los tipos `CompraAltaInput`/`LineaInput`/`VencimientoInput`/`CompraDetalle` espejando el contrato.
- [x] T018 [P] [US1] `frontend/src/components/compras/DetalleLineaForm.tsx`: fila editable de línea (producto/servicio texto, cantidad, precio unitario, IVA %, combos de Unidad/Centro de Costos/Rubro/Destino/Campaña poblados desde `GET /api/compras/filtros` ampliado) con subtotal/importeIVA calculados en vivo en el cliente (mismo cálculo que T013, solo para feedback inmediato — el valor de verdad lo recalcula el backend al guardar).
- [x] T019 [P] [US1] `frontend/src/components/compras/VencimientosEditor.tsx`: lista editable de fechas de vencimiento (agregar/quitar filas de solo fecha).
- [x] T020 [US1] `frontend/src/components/compras/CompraForm.tsx`: formulario de cabecera (proveedor vía `ContactoSelect` filtrado a los 5 tipos permitidos, fecha, combos de tipo/tipoDocumento/moneda con las opciones fijas del spec, tipo de cambio condicional cuando moneda="Dolares", conceptos monetarios) + lista de `DetalleLineaForm` + `VencimientosEditor`, con totales de cabecera mostrados en vivo (subtotal/IVA/importe total/pesificado) y botón guardar que llama a `crearCompra` (T017) en modo alta.
- [x] T021 [US1] `frontend/src/app/compras/nueva/page.tsx`: página que monta `CompraForm` en modo alta y redirige a `/compras` (o muestra el detalle) al guardar con éxito; agregar botón "+ Nueva compra" en `frontend/src/components/compras/ComprasListado.tsx` que enlaza a esta ruta.

**Checkpoint**: Historia 1 funcional de punta a punta — alta de compra desde el frontend, verificable contra `WC` sin tocar `LaHerencia` (quickstart.md Escenarios 1 y 2).

---

## Phase 4: User Story 2 - Editar una compra existente (Priority: P2)

**Goal**: Un usuario puede editar una compra ya cargada (cabecera, líneas, vencimientos) con bloqueo exclusivo mientras la edita.

**Independent Test**: Adquirir lock, `PUT /api/compras/{id}` con un precio de línea cambiado → totales recalculados; un segundo lock con otro token mientras el primero está vigente → `409` (quickstart.md Escenarios 3 y 4).

### Tests for User Story 2

- [x] T022 [P] [US2] Contract test `POST /api/compras/{id}/lock`: primer token adquiere (`200`), segundo token mientras el primero está vigente → `409`, mismo token renueva sin conflicto.
- [x] T023 [P] [US2] Contract test `DELETE /api/compras/{id}/lock`: libera con el token correcto (`204`), rechaza con un token distinto al que tiene el lock vigente (`409`).
- [x] T024 [P] [US2] Contract test `PUT /api/compras/{id}`: sin lock vigente del token usado → `409`; con lock válido, cambia el precio de una línea → `200` con totales recalculados; `idCompra` inexistente → `404`.

### Implementation for User Story 2

- [x] T025 [US2] `backend/src/features/compras/schemas.py`: `CompraEditRequest` (mismos campos que `CompraAltaRequest`), `LockRequest` (`lockToken: str`), `LockResponse` (`idCompra`, `lockToken`, `expiresAt`).
- [x] T026 [US2] `backend/src/features/compras/repository.py`: `update_compra(id_compra, cabecera, lineas, vencimientos) -> dict` — reemplazo total dentro de una sola `execute_write_transaction`: DELETE de las líneas/vencimientos existentes de esa compra, UPDATE de cabecera, INSERT de las líneas/vencimientos nuevas (mismo cálculo de totales que T013, misma validación de `validar_compra` que T012, incluyendo el chequeo de tipo de cambio obligatorio de FR-007).
- [x] T027 [US2] `backend/src/features/compras/router.py`: `POST /api/compras/{id_compra}/lock` (usa `repository_locks.adquirir_lock`, `409` si está tomado por otro token), `DELETE /api/compras/{id_compra}/lock` (usa `liberar_lock`, `409` si el token no coincide), `PUT /api/compras/{id_compra}` (requiere header `X-Lock-Token`, `409` vía `verificar_lock` antes de tocar la base, `404` si `id_compra` no existe, si no `update_compra` + `warnings` de T015).
- [x] T028 [US2] `frontend/src/services/comprasApi.ts`: `adquirirLock(idCompra, lockToken)`, `liberarLock(idCompra, lockToken)`, `actualizarCompra(idCompra, input, lockToken)` (manda `X-Lock-Token` como header).
- [x] T029 [US2] `frontend/src/components/compras/CompraForm.tsx`: modo edición — genera un `lockToken` (UUID) al montar, llama `adquirirLock` (muestra error bloqueante si `409`, indicando que la compra está en edición), renueva el lock periódicamente mientras el formulario sigue abierto, llama `liberarLock` al desmontar o al guardar con éxito.
- [x] T030 [US2] `frontend/src/app/compras/[idCompra]/editar/page.tsx`: monta `CompraForm` en modo edición precargado con los datos de la compra (reusa `GET /api/compras/{id}` si existe, o agrega el detalle que falte a 002-compras); agregar enlace "Editar" desde `ComprasListado.tsx` a esta ruta.

**Checkpoint**: Historias 1 y 2 funcionan juntas — alta y edición con bloqueo exclusivo verificado.

---

## Phase 5: User Story 3 - Clasificar cada línea con sugerencia de Rubro (Priority: P2)

**Goal**: Al cargar el texto de producto/servicio de una línea, el sistema sugiere el rubro más frecuente usado antes para ese mismo texto, sin forzarlo.

**Independent Test**: Crear una línea con un texto y rubro dados; `GET /api/compras/rubro-sugerido?productoServicio=<mismo texto>` devuelve ese rubro (quickstart.md Escenario 5).

### Tests for User Story 3

- [x] T031 [P] [US3] Contract test `GET /api/compras/rubro-sugerido`: texto con coincidencias previas → devuelve el `idRubro` más frecuente; texto sin coincidencias → `idRubro: null`.

### Implementation for User Story 3

- [x] T032 [US3] `backend/src/features/compras/repository.py`: `get_rubro_sugerido(producto_servicio: str) -> dict | None` — `SELECT TOP 1 IdRubro, COUNT(*) AS frecuencia FROM Det_Compras WHERE [Producto/Servicio] = ? AND IdRubro IS NOT NULL GROUP BY IdRubro ORDER BY COUNT(*) DESC` (research.md §3), join con `Rubros` para el nombre.
- [x] T033 [US3] `backend/src/features/compras/router.py`: `GET /api/compras/rubro-sugerido?productoServicio=...`.
- [x] T034 [US3] `frontend/src/services/comprasApi.ts`: `fetchRubroSugerido(productoServicio: string)`.
- [x] T035 [US3] `frontend/src/components/compras/DetalleLineaForm.tsx`: al perder foco el campo producto/servicio, si el combo de Rubro de esa línea sigue vacío, llamar a `fetchRubroSugerido` y prellenar el combo con la sugerencia (editable, no vinculante — el usuario puede cambiarlo antes de guardar).

**Checkpoint**: Las 3 historias de usuario funcionan de punta a punta, integradas.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T036 [P] Verificar que `GET /api/compras` y sus filtros (spec 002) encuentran sin cambios las compras creadas por esta feature, filtrando por el Centro de Costos/Rubro usados en una compra de prueba (SC-002).
- [x] T037 [P] Mostrar el aviso no bloqueante de `warnings` (documento duplicado, FR-014) como toast (`useToast`, ya existente) al guardar una compra con `warnings` no vacío.
- [x] T038 Ejecutar `cd backend && python -m pytest -q` y confirmar que todos los tests (existentes + nuevos de esta feature) pasan.
- [x] T039 Ejecutar `cd frontend && npx tsc --noEmit -p . && npx eslint .` y confirmar cero errores.
- [x] T040 Correr manualmente los 7 escenarios de `specs/006-carga-compras/quickstart.md` contra el backend real (`WC`) y verificar contra SQL Server que ninguna escritura llegó a `LaHerencia` (SC-004).
- [x] T040a Ejecutar el Escenario 7 de `quickstart.md` (SC-003): tomar 5 `IdDeuda` reales de `Compras` con sus `Det_Compras`, recalcular manualmente subtotal/IVA de cabecera/importe total con la fórmula de `calcular_totales` (T013) y confirmar que coinciden con lo que produciría el formulario Access original (fórmulas de `research.md`/`data-model.md`); documentar el resultado de la comparación (los 5 casos y su resultado) en el propio quickstart o en un comentario del PR.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias — empieza de inmediato.
- **Foundational (Phase 2)**: depende de Setup (T001 confirma el nombre de columna que T006 necesita; T002 crea la tabla que T005 usa) — bloquea todas las historias.
- **Historias de usuario (Phase 3-5)**: todas dependen de Foundational. US1 es independiente. US2 depende de que exista `create_compra`/cálculo de totales de US1 (reutiliza T013/T012), pero es una historia separada y verificable por su cuenta una vez que US1 está lista. US3 es la más independiente — solo necesita el catálogo de Rubros (Foundational) y puede implementarse en paralelo a US2.
- **Polish (Phase 6)**: depende de que las historias que se quieran entregar estén completas.

### Parallel Opportunities

- T004, T005, T006 (Foundational) son paralelas entre sí (archivos distintos).
- T007-T010 (tests de US1) son paralelas entre sí.
- T018, T019 (componentes de frontend de US1) son paralelas entre sí.
- T022, T023, T024 (tests de US2) son paralelas entre sí.
- US3 completa (T031-T035) puede desarrollarse en paralelo a US2 una vez cerrada Foundational + US1.

---

## Implementation Strategy

### MVP First (User Story 1)

1. Completar Phase 1 (Setup) y Phase 2 (Foundational) — bloqueante.
2. Completar Phase 3 (US1) — alta de compra completa, sin edición ni sugerencia de rubro.
3. Validar con quickstart.md Escenarios 1 y 2 antes de seguir.

### Incremental Delivery

1. Setup + Foundational → base lista.
2. US1 → demo: alta de compras funcionando end-to-end (MVP).
3. US2 → demo: edición con bloqueo exclusivo.
4. US3 → demo: sugerencia de rubro.
5. Polish → verificación final de no regresión y de la regla de oro (`WC`-only).
