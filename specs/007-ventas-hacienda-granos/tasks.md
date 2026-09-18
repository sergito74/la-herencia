---

description: "Task list for 007-ventas-hacienda-granos"
---

# Tasks: Ventas de Hacienda (alta) y Ventas de Granos (lectura + alta)

**Input**: Design documents from `specs/007-ventas-hacienda-granos/` (plan.md, spec.md, research.md, data-model.md, contracts/ventas-api.md, quickstart.md)

**Tests**: Incluidos — este proyecto usa contract tests (`backend/tests/contract/test_*.py`) como parte del flujo estándar (constitución principio V).

**Organization**: Tareas agrupadas por historia de usuario (spec.md, 7 historias). Setup y Foundational son prerrequisito bloqueante de todas las historias. Hacienda (US1-US4) y Granos (US5-US7) son dominios independientes entre sí — pueden implementarse en cualquier orden relativo una vez cerrada Foundational, aunque se recomienda Hacienda primero (research.md, menor riesgo).

---

## Phase 1: Setup

- [X] T001 Verificar con `curl -X OPTIONS` que `main.py` sigue aceptando `PUT`/`DELETE` en `allow_methods` de CORS (ya corregido en 006 — solo confirmar, no reimplementar, research.md §6).
- [X] T002 [P] Confirmar contra `WC` (nunca `LaHerencia`) que `dbo.[Venta Hacienda]`, `dbo.[Det_Ventas Hacienda]`, `dbo.[Vencimientos Ventas]`, `dbo.[Venta Granos]`, `dbo.[Venta Granos_Ajustes]`, `dbo.[Venta Granos_Deducciones]` existen con las mismas columnas documentadas en `data-model.md` (ya verificado contra `LaHerencia` en la fase de plan — repetir el `INFORMATION_SCHEMA.COLUMNS` apuntando a `WC` antes de escribir ahí).

**Checkpoint**: Esquema confirmado en `WC`, CORS verificado — el resto de las fases puede empezar.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Infraestructura de bloqueo/vínculo que TODAS las historias de escritura necesitan.

**⚠️ CRITICAL**: Ninguna historia de usuario de escritura puede completarse sin esta fase. La Historia 5 (listado de lectura de Granos) no depende de esta fase.

- [X] T003 [P] Ejecutar contra `WC` el DDL de `dbo.VentaHaciendaEditLocks` (`IdVenta` int, `LockToken` uniqueidentifier, `LockedAt` datetime, `ExpiresAt` datetime) — mismo patrón que `CompraEditLocks` de 006, con el guard `assert DATABASE == "wc"` antes del DDL.
- [X] T004 [P] Ejecutar contra `WC` el DDL de `dbo.VentaGranosEditLocks` (mismas columnas que T003, ámbito Granos).
- [X] T005 [P] Ejecutar contra `WC` el DDL de `dbo.VentaDocumentosRelacionados` (`IdVenta` int, `IdVentaRelacionada` int, `TipoVenta` nvarchar(10) — 'Hacienda'|'Granos', `CreatedAt` datetime) — una sola tabla para ambos dominios, distinguidos por `TipoVenta` dado que `IdVenta` de Hacienda y Granos son autoincrementales independientes entre sí.

**Checkpoint**: Tablas de infraestructura listas — las historias de usuario de escritura pueden implementarse.

---

## Phase 3: User Story 1 - Cargar una venta de hacienda nueva completa (Priority: P1) 🎯 MVP

**Goal**: Un usuario puede crear una venta de hacienda completa (cabecera + al menos una línea con comprador propio, con o sin vencimientos) que queda escrita en `WC` y visible en el listado existente de Ventas de Hacienda (005).

**Independent Test**: `POST /api/ventas-hacienda` con un consignatario real, una línea con comprador/categoría/cantidad/precio y sin vencimientos → `201`, totales calculados correctamente, la venta aparece en `GET /api/ventas-hacienda` (quickstart.md Escenario 1).

### Tests for User Story 1

- [X] T006 [P] [US1] Contract test `POST /api/ventas-hacienda` (alta exitosa, cabecera + 1 línea, sin vencimientos) en `backend/tests/contract/test_ventas_hacienda_alta_api.py`, verificando `subTotal`/`comision`/`iva`/`importe`/`importeTotal` calculados según data-model.md.
- [X] T007 [P] [US1] Contract test `POST /api/ventas-hacienda` con dos líneas de compradores distintos → ambas se guardan con su propio `idComprador`, sin exigir uno único de cabecera (Acceptance Scenario 2).
- [X] T008 [P] [US1] Contract test `POST /api/ventas-hacienda` sin `idConsignatario`, sin `idEstablecimiento` o con `lineas: []` → `400`, sin crear ningún registro parcial (Acceptance Scenario 3).
- [X] T008a [P] [US1] Contract test `POST /api/ventas-hacienda` con una línea presente pero sin `idComprador` → `400` (Edge Cases spec.md: "una venta de hacienda no tiene ninguna línea con comprador asignado" debe rechazarse, distinto del caso de `lineas: []` que ya cubre T008).
- [X] T009 [P] [US1] Contract test `POST /api/ventas-hacienda` con `idConsignatario`/`idComprador` de tipo no permitido (ej. contacto tipo "Organismo") → `400` (research.md §2: Consignatario ∈ {Comprador, Consignatario, Multiple}; Comprador de línea ∈ {Comprador, Multiple}).
- [X] T010 [P] [US1] Contract test `POST /api/ventas-hacienda` con el mismo `numeroDocumento` del mismo `idConsignatario` que otra venta ya existente → `201` con `warnings` no vacío, **nunca** `400` (FR-009a, decisión Q3 — a diferencia del bloqueo duro de Compras).

### Implementation for User Story 1

- [X] T011 [US1] `backend/src/features/ventas_hacienda/schemas.py`: agregar `LineaVentaHaciendaInput` (`idComprador`: int requerido, `idTipoProducto`: int requerido, `cantidad`: float requerido sin mínimo, `unidadMedida`/`pesoTotal` opcionales, `precioUnitarioA`: money requerido, `precioUnitarioB`: money opcional default 0), `VencimientoVentaInput` (`fecha`: date requerido, `importe`: money requerido — a diferencia de Compras, acá el vencimiento SÍ tiene importe, data-model.md), `VentaHaciendaAltaRequest` (`idConsignatario`/`idEstablecimiento`/`idTipoDocumento`: int requeridos, `numeroDocumento`: str requerido máx. 50 caracteres, `fecha`: date requerido, resto de conceptos monetarios opcionales default 0, `lineas`: list mínimo 1 elemento, `vencimientos`: list default `[]`), `VentaHaciendaDetalleResponse` (cabecera + `subTotal`/`subtotalB`/`comision`/`iva`/`importe`/`importeTotal`/`lineas`/`vencimientos`/`warnings: list[str]`).
- [X] T012 [US1] `backend/src/features/ventas_hacienda/repository.py`: `validar_venta(id_consignatario, lineas) -> list[str]` — `idConsignatario` debe existir en `Contactos` con tipo ∈ {Comprador, Consignatario, Multiple} (research.md §2); `idEstablecimiento` debe existir en `Establecimientos`; cada línea: `idComprador` debe existir en `Contactos` con tipo ∈ {Comprador, Multiple}; `idTipoProducto` debe existir en `Tipo Hacienda`; `idTipoDocumento` debe existir en `Tipo Documento`.
- [X] T013 [US1] `backend/src/features/ventas_hacienda/repository.py`: `calcular_totales(lineas, cabecera) -> dict` puro (sin acceso a base) que implementa exactamente las fórmulas de data-model.md: por línea, `subtotalA`/`subtotalB`/`importe = subtotalA + subtotalB` (mismo nombre `importe` que ya usa `LineaVentaHacienda.importe` en el contrato de lectura existente, `backend/src/features/ventas_hacienda/schemas.py` — no introducir `total` como nombre alternativo); agregados de cabecera: `comision = (subTotal + subtotalB) * porcComision / 100`, `iva = (subTotal - visMunicipal - balanza - comision - gsVsNoGravados) * alicuotaIVA / 100`, `importe = subTotal - visMunicipal - balanza - comision - gsVsNoGravados + iva - leyDeSellos - retencionGanancias - ingresosBrutos - gastosVarios`, `importeTotal = importe + subtotalB`.
- [X] T014 [US1] `backend/src/features/ventas_hacienda/repository.py`: `create_venta(cabecera, lineas, vencimientos) -> int` — valida con `validar_venta` (T012), calcula con `calcular_totales` (T013), arma la lista de sentencias (1 INSERT a `[Venta Hacienda]` con `OUTPUT INSERTED.IdVenta`, N INSERT a `[Det_Ventas Hacienda]`, M INSERT a `[Vencimientos Ventas]`) y las ejecuta con `execute_write_transaction` (ya existente desde 006, sin cambios).
- [X] T015 [US1] `backend/src/features/ventas_hacienda/repository.py`: `hay_documento_duplicado(id_consignatario, numero_documento, excluir_id_venta=None) -> bool` (FR-009a) — usado por el router para poblar `warnings`, nunca bloquea el guardado (decisión Q3).
- [X] T016 [US1] `backend/src/features/ventas_hacienda/router.py`: `POST /api/ventas-hacienda` — valida con `validar_venta` (400 si falla), crea con `create_venta`, arma `warnings` con `hay_documento_duplicado`, devuelve `201` con `VentaHaciendaDetalleResponse`.
- [X] T017 [US1] `backend/src/features/ventas_hacienda/router.py`: `GET /api/ventas-hacienda/filtros` — expone catálogos `establecimientos` (`Establecimientos`), `tiposDocumento` (`Tipo Documento`), `tiposHacienda` (`Tipo Hacienda`, ya usado por 005) para los combos del formulario.
- [X] T018 [US1] `frontend/src/services/ventasHaciendaApi.ts`: agregar `crearVenta(input: VentaHaciendaAltaInput): Promise<VentaHaciendaDetalle>` (POST) y los tipos `VentaHaciendaAltaInput`/`LineaVentaHaciendaInput`/`VencimientoVentaInput`/`VentaHaciendaDetalle` espejando el contrato; `fetchFiltrosVentaHacienda()`.
- [X] T019 [P] [US1] `frontend/src/components/ventas-hacienda/VentaHaciendaForm.tsx`: cabecera (consignatario vía `ContactoSelect` filtrado a {Comprador, Consignatario, Multiple}, establecimiento, tipo de documento, número, fecha, conceptos monetarios) en grid responsive (mismo patrón que `CompraForm.tsx`).
- [X] T020 [P] [US1] `frontend/src/components/ventas-hacienda/VentaHaciendaGrid.tsx`: grilla de líneas tipo planilla con `ContactoSelect` embebido por fila (comprador, filtrado a {Comprador, Multiple}) compartiendo cache de búsqueda entre instancias (queryKey común), combo de categoría (`Tipo Hacienda`), cantidad, peso, unidad, precios A/B, subtotal en vivo.
- [X] T021 [US1] `frontend/src/components/ventas-hacienda/VentaHaciendaForm.tsx`: integrar `VentaHaciendaGrid` (T020) + editor de vencimientos con importe (reusar/extender `VencimientosEditor.tsx` de compras para aceptar un campo `importe` por fila) + totales de cabecera en vivo + botón guardar que llama a `crearVenta` (T018) en modo alta.
- [X] T022 [US1] `frontend/src/app/ventas/hacienda/nueva/page.tsx`: página que monta `VentaHaciendaForm` en modo alta y redirige a `/ventas/hacienda` al guardar con éxito; agregar botón "+ Nueva venta de hacienda" en `VentasHaciendaListado.tsx` (existente, 005).

**Checkpoint**: Historia 1 funcional de punta a punta — alta de venta de hacienda desde el frontend, verificable contra `WC` sin tocar `LaHerencia` (quickstart.md Escenarios 1 y 2).

---

## Phase 4: User Story 2 - Editar una venta de hacienda existente (Priority: P2)

**Goal**: Un usuario puede editar una venta de hacienda ya cargada (cabecera, líneas, vencimientos) con bloqueo exclusivo mientras la edita.

**Independent Test**: Adquirir lock, `PUT /api/ventas-hacienda/{id}` con un precio de línea cambiado → totales recalculados; un segundo lock con otro token mientras el primero está vigente → `409`, `force: true` lo toma igual (quickstart.md Escenario 3).

### Tests for User Story 2

- [X] T023 [P] [US2] Contract test `POST /api/ventas-hacienda/{id}/lock`: primer token adquiere (`200`), segundo token mientras el primero está vigente → `409`, mismo token renueva sin conflicto, `force: true` del segundo token lo toma igual (200).
- [X] T024 [P] [US2] Contract test `DELETE /api/ventas-hacienda/{id}/lock`: libera con el token correcto (`204`), rechaza con un token distinto al que tiene el lock vigente (`409`).
- [X] T025 [P] [US2] Contract test `PUT /api/ventas-hacienda/{id}`: sin lock vigente del token usado → `409`; con lock válido, cambia el precio de una línea → `200` con totales recalculados; `idVenta` inexistente → `404`.

### Implementation for User Story 2

- [X] T026 [US2] `backend/src/features/ventas_hacienda/repository_locks.py`: `adquirir_lock(id_venta, lock_token, force=False)`, `liberar_lock(id_venta, lock_token)`, `verificar_lock(id_venta, lock_token)` sobre `dbo.VentaHaciendaEditLocks` — copia exacta del patrón de `compras/repository_locks.py` (006), TTL de 5 minutos (no 15, lección aprendida — research.md §5).
- [X] T027 [US2] `backend/src/features/ventas_hacienda/schemas.py`: `VentaHaciendaEditRequest` (mismos campos que `VentaHaciendaAltaRequest`), `LockRequest` (`lockToken: str`, `force: bool = False`), `LockResponse` (`idVenta`, `lockToken`, `expiresAt`).
- [X] T028 [US2] `backend/src/features/ventas_hacienda/repository.py`: `update_venta(id_venta, cabecera, lineas, vencimientos) -> dict` — reemplazo total dentro de una sola `execute_write_transaction`: DELETE de líneas/vencimientos existentes, UPDATE de cabecera, INSERT de líneas/vencimientos nuevas (mismo cálculo de totales que T013, misma validación que T012).
- [X] T029 [US2] `backend/src/features/ventas_hacienda/router.py`: `POST /api/ventas-hacienda/{id}/lock` (usa `adquirir_lock`, `409` si está tomado por otro token y `force=False`), `DELETE /api/ventas-hacienda/{id}/lock` (usa `liberar_lock`), `PUT /api/ventas-hacienda/{id}` (requiere header `X-Lock-Token`, `409` vía `verificar_lock` antes de tocar la base, `404` si no existe, si no `update_venta` + `warnings`).
- [X] T030 [US2] `frontend/src/services/ventasHaciendaApi.ts`: `adquirirLock(idVenta, lockToken, force?)`, `liberarLock(idVenta, lockToken, keepalive?)`, `actualizarVenta(idVenta, input, lockToken)`.
- [X] T031 [US2] `frontend/src/components/ventas-hacienda/VentaHaciendaForm.tsx`: modo edición — genera `lockToken` al montar, adquiere lock (muestra error con botón "Forzar edición" si `409`, igual que `CompraForm.tsx`), renueva cada 2 minutos, libera al desmontar y en `pagehide` con `keepalive` (mismas lecciones de 006).
- [X] T032 [US2] `frontend/src/app/ventas/hacienda/[idVenta]/editar/page.tsx`: monta `VentaHaciendaForm` en modo edición precargado con `GET /api/ventas-hacienda/{id}`; agregar enlace desde `VentasHaciendaListado.tsx` (existente, 005) a esta ruta; botón "← Volver a Ventas de Hacienda" con `router.back()` (mismo patrón que Compras).
- [X] T032a [US2] `frontend/src/components/ventas-hacienda/VentasHaciendaListado.tsx` (existente, 005): migrar sus filtros/orden/página a la URL (`useSearchParams`/`router.replace`, mismo patrón que `ComprasListado.tsx` de 006) — sin esto, "← Volver a Ventas de Hacienda" (T032) no recupera la búsqueda anterior, y el listado sigue mostrando resultados por defecto sin filtro en vez de vacío (FR-014, FR-010 no aplica acá pero el criterio de "vacío por defecto" es consistente con el resto de la app).

**Checkpoint**: Historias 1 y 2 funcionan juntas — alta y edición con bloqueo exclusivo verificado, listado de Hacienda con el mismo patrón de persistencia de estado que Compras/Granos.

---

## Phase 5: User Story 3 - Eliminar una venta de hacienda cargada por error (Priority: P2)

**Goal**: Un usuario puede eliminar por completo una venta de hacienda mal cargada, sujeto al mismo bloqueo exclusivo que la edición.

**Independent Test**: Crear una venta de prueba, eliminarla, verificar que desaparece del listado y que líneas/vencimientos/vínculos también se eliminaron (quickstart.md Escenario 3, paso 5).

### Tests for User Story 3

- [X] T033 [P] [US3] Contract test `DELETE /api/ventas-hacienda/{id}` inexistente → `404`.
- [X] T034 [P] [US3] Contract test `DELETE /api/ventas-hacienda/{id}` sin lock vigente del token usado → `409`.
- [X] T035 [P] [US3] Contract test `DELETE /api/ventas-hacienda/{id}` con lock válido → `204`, y `repository.delete_venta` fue invocado con el `id_venta` correcto.

### Implementation for User Story 3

- [X] T036 [US3] `backend/src/features/ventas_hacienda/repository.py`: `delete_venta(id_venta) -> None` — transacción única que borra `[Det_Ventas Hacienda]`, `[Vencimientos Ventas]`, `VentaDocumentosRelacionados` (ambas direcciones, `TipoVenta = 'Hacienda'`), `VentaHaciendaEditLocks`, y por último `[Venta Hacienda]` (mismo patrón que `compras.delete_compra` de 006).
- [X] T037 [US3] `backend/src/features/ventas_hacienda/router.py`: `DELETE /api/ventas-hacienda/{id}` (requiere `X-Lock-Token`, `404` si no existe, `409` si el lock pertenece a otro token, `204` en éxito).
- [X] T038 [US3] `frontend/src/services/ventasHaciendaApi.ts`: `eliminarVenta(idVenta, lockToken)`.
- [X] T039 [US3] `frontend/src/components/ventas-hacienda/VentaHaciendaForm.tsx`: botón "Eliminar venta" en modo edición (deshabilitado si `lockError`), con `window.confirm` antes de eliminar (mismo patrón que `CompraForm.tsx`).

**Checkpoint**: Historias 1-3 cubren el ciclo completo de alta/edición/eliminación de Venta de Hacienda.

---

## Phase 6: User Story 4 - Vincular documentos relacionados de una venta de hacienda (Priority: P3)

**Goal**: Un usuario puede relacionar manualmente una Nota de Crédito/Débito con la venta original que complementa, buscando por número de documento del mismo consignatario.

**Independent Test**: Crear dos ventas del mismo consignatario con documentos complementarios, vincularlas, verificar que el vínculo persiste al reabrir cualquiera de las dos (quickstart.md, no tiene escenario numerado propio — cubierto por Acceptance Scenarios de la Historia 4 en spec.md).

### Tests for User Story 4

- [X] T040 [P] [US4] Contract test `GET /api/ventas-hacienda/{id}/relacionados` devuelve vacío si no hay vínculos.
- [X] T041 [P] [US4] Contract test `POST /api/ventas-hacienda/{id}/relacionados` vincula, `DELETE /api/ventas-hacienda/{id}/relacionados/{idRelacionada}` desvincula.

### Implementation for User Story 4

- [X] T042 [US4] `backend/src/features/ventas_hacienda/repository.py`: `get_documentos_relacionados(id_venta)`, `agregar_documento_relacionado(id_venta, id_venta_relacionada)`, `quitar_documento_relacionado(id_venta, id_venta_relacionada)` sobre `VentaDocumentosRelacionados` con `TipoVenta = 'Hacienda'` — mismo patrón que `compras.repository` (006), filtrando por `TipoVenta` en vez de usar una tabla dedicada.
- [X] T043 [US4] `backend/src/features/ventas_hacienda/router.py`: `GET/POST/DELETE /api/ventas-hacienda/{id}/relacionados[/{idRelacionada}]`.
- [X] T044 [US4] `frontend/src/services/ventasHaciendaApi.ts`: `fetchDocumentosRelacionados`, `agregarDocumentoRelacionado`, `quitarDocumentoRelacionado`.
- [X] T045 [US4] Extraer `DocumentosRelacionadosPanel.tsx` de `frontend/src/components/compras/` a `frontend/src/components/ui/` (o duplicar tal cual si la extracción genérica no es trivial por los tipos específicos de Compra) y usarlo en `VentaHaciendaForm.tsx` con búsqueda acotada por número de documento del consignatario (mismo patrón que Compras, sin listar automáticamente el historial completo).

**Checkpoint**: Ventas de Hacienda (Historias 1-4) completas y verificables end-to-end.

---

## Phase 7: User Story 5 - Consultar el listado de Ventas de Granos (Priority: P2)

**Goal**: Un usuario puede buscar y revisar las ventas de granos ya liquidadas, con ajustes y deducciones mostrados por separado.

**Independent Test**: Buscar por consignatario/número de documento/campaña y verificar que los resultados reales de `Venta Granos` aparecen con su importe neto a percibir calculado (quickstart.md Escenarios 6-7).

### Tests for User Story 5

- [X] T046 [P] [US5] Contract test `GET /api/ventas-granos` sin filtro → `items: []` (FR-010, mismo criterio que Compras/Contactos).
- [X] T047 [P] [US5] Contract test `GET /api/ventas-granos?numeroDocumento=...` con datos reales → devuelve coincidencias con `importeNetoAPercibir` ya calculado.
- [X] T048 [P] [US5] Contract test `GET /api/ventas-granos/{id}` devuelve `ajustes[]` y `deducciones[]` como listas separadas, no mezcladas en una línea (FR-011).

### Implementation for User Story 5

- [X] T049 [US5] `backend/src/features/ventas_granos/__init__.py`, `schemas.py`: `VentaGranosResponse` (cabecera completa de data-model.md, incluidos los campos de significado ambiguo `gradoOperacion`/`gradoMercaderia`/`cantidadEntregada`/`cantidadVendida` como campos separados — decisión Q2, no fusionar), `AjusteResponse`, `DeduccionResponse`, `VentaGranosListResponse`.
- [X] T050 [US5] `backend/src/features/ventas_granos/repository.py`: `search_ventas(consignatario, numero_documento, fecha_desde, fecha_hasta, campania, page, page_size, sort_by=None, sort_dir="asc") -> tuple[list[dict], int]` — mismo patrón de whitelist de columnas para `ORDER BY` dinámico que `compras.repository.search_compras` (006, previene SQL injection); sin filtro, no ejecuta la query principal (devuelve `[], 0` — FR-010).
- [X] T051 [US5] `backend/src/features/ventas_granos/repository.py`: `get_venta_detalle(id_venta) -> dict | None`, `get_ajustes(id_venta) -> list[dict]`, `get_deducciones(id_venta) -> list[dict]` (join con `Venta Granos_ConceptosDeducciones` para el nombre del concepto), y `calcular_totales(cabecera, ajustes, deducciones) -> dict` puro con la fórmula exacta de data-model.md (`precioKg` → `subTotal` → `iva` → `totalOperacion` → `totalDeducciones` → `importeNetoAPercibir`).
- [X] T052 [US5] `backend/src/features/ventas_granos/router.py`: `GET /api/ventas-granos`, `GET /api/ventas-granos/{id}`, `GET /api/ventas-granos/filtros` (catálogos `Granos`, `Tipo Documento`).
- [X] T053 [US5] `backend/src/main.py`: registrar el router nuevo `ventas_granos_router`.
- [X] T054 [US5] `frontend/src/services/ventasGranosApi.ts`: `fetchVentasGranos`, `fetchVentaGranosDetalle`, `fetchFiltrosVentasGranos`, tipos `VentaGranos`/`VentaGranosDetalle`/`AjusteGranos`/`DeduccionGranos`.
- [X] T055 [P] [US5] `frontend/src/components/ventas-granos/VentasGranosListado.tsx`: listado vacío por defecto hasta aplicar un filtro (mismo patrón que `ComprasListado.tsx`/`ContactosListado.tsx`), filtros/orden/página persistidos en la URL (mismo patrón `useSearchParams`/`router.replace` que `ComprasListado.tsx`).
- [X] T056 [US5] `frontend/src/app/ventas/granos/page.tsx`: página que monta `VentasGranosListado`.
- [X] T057 [US5] `frontend/src/components/layout/NavHeader.tsx`: convertir el ítem "Ventas" a `submenu: [{ href: "/ventas/hacienda", label: "Hacienda" }, { href: "/ventas/granos", label: "Granos" }]` (research.md §8).

**Checkpoint**: Listado de Ventas de Granos funcional, base para el alta (Historia 6).

---

## Phase 8: User Story 6 - Cargar una venta de granos nueva (Priority: P2)

**Goal**: Un usuario puede crear una venta de granos nueva (cabecera + ajustes/deducciones opcionales) que queda escrita en `WC`.

**Independent Test**: `POST /api/ventas-granos` con un consignatario real, cabecera completa y ajustes/deducciones opcionales → `201`, `importeNetoAPercibir` calculado correctamente (quickstart.md Escenario 7).

### Tests for User Story 6

- [X] T058 [P] [US6] Contract test `POST /api/ventas-granos` (alta exitosa, cabecera completa, sin ajustes ni deducciones) en `backend/tests/contract/test_ventas_granos_api.py`, verificando `importeNetoAPercibir` según data-model.md.
- [X] T059 [P] [US6] Contract test `POST /api/ventas-granos` con un ajuste → `subTotal` incluye el ajuste; con una deducción → `importeNetoAPercibir` refleja la resta (Acceptance Scenarios de Historia 6).
- [X] T060 [P] [US6] Contract test `POST /api/ventas-granos` sin `idConsignatario`/`idProducto`/`cantidadVendida`/`precioUnitario` → `400`.
- [X] T061 [P] [US6] Contract test `POST /api/ventas-granos` con el mismo `numeroDocumento` del mismo consignatario que otra venta ya existente → `201` con `warnings` no vacío, nunca `400` (FR-012a, decisión Q3).

### Implementation for User Story 6

- [X] T062 [US6] `backend/src/features/ventas_granos/schemas.py`: `AjusteInput` (`concepto`: str requerido, `importe`: money requerido, `alicuotaIVA`: float opcional default 0), `DeduccionInput` (`idConcepto`: int requerido, `detalle`: str opcional, `porc`: float requerido, `baseCalculo`: money requerido, `alicuota`: float opcional default 0), `VentaGranosAltaRequest` (`idConsignatario`/`idTipoDocumento`/`idProducto`: int requeridos, `numeroDocumento`: str requerido máx. 255 caracteres, `fecha`: date requerido, `precioUnitario`: money requerido, `cantidadEntregada`/`cantidadVendida`: float requeridos, `gradoOperacion`/`gradoMercaderia`: str opcionales máx. 5 caracteres — capturados tal cual sin validar semántica, decisión Q2 —, `campania`: str libre opcional máx. 10 caracteres, resto de conceptos monetarios opcionales default 0, `ajustes`/`deducciones`: list default `[]`).
- [X] T063 [US6] `backend/src/features/ventas_granos/repository.py`: `validar_venta(id_consignatario, id_producto, id_tipo_documento, deducciones) -> list[str]` — `idConsignatario` debe existir en `Contactos` (research.md §3: histórico real 100% tipo Multiple, admitir también Comprador/Consignatario); `idProducto` debe existir en `Granos`; `idTipoDocumento` debe existir en `Tipo Documento`; cada `idConcepto` de deducción debe existir en `Venta Granos_ConceptosDeducciones`.
- [X] T064 [US6] `backend/src/features/ventas_granos/repository.py`: `create_venta(cabecera, ajustes, deducciones) -> int` — valida con T063, calcula totales con `calcular_totales` (T051), arma la transacción (1 INSERT a `[Venta Granos]` con `OUTPUT INSERTED.IdVenta`, N INSERT a `[Venta Granos_Ajustes]`, M INSERT a `[Venta Granos_Deducciones]`) vía `execute_write_transaction`.
- [X] T065 [US6] `backend/src/features/ventas_granos/repository.py`: `hay_documento_duplicado(id_consignatario, numero_documento, excluir_id_venta=None) -> bool` (FR-012a, advertencia no bloqueante).
- [X] T066 [US6] `backend/src/features/ventas_granos/router.py`: `POST /api/ventas-granos` — valida, crea, arma `warnings`, devuelve `201` con detalle + totales calculados.
- [X] T067 [US6] `frontend/src/services/ventasGranosApi.ts`: `crearVentaGranos(input)`.
- [X] T068 [P] [US6] `frontend/src/components/ventas-granos/VentaGranosForm.tsx`: formulario de cabecera (consignatario vía `ContactoSelect`, grano vía combo `Granos`, campaña como input de texto libre — **no** combo cerrado, research.md §3 — resto de campos de data-model.md) en grid responsive.
- [X] T069 [P] [US6] `frontend/src/components/ventas-granos/AjustesEditor.tsx` y `DeduccionesEditor.tsx`: listas editables simples (agregar/quitar filas) para ajustes (concepto+importe+alícuota) y deducciones (concepto vía combo `Venta Granos_ConceptosDeducciones`+detalle+porcentaje+base+alícuota) — sin grilla tipo planilla completa, dado que no son líneas de producto sino ajustes puntuales (research.md §3).
- [X] T070 [US6] `frontend/src/components/ventas-granos/VentaGranosForm.tsx`: integrar `AjustesEditor`/`DeduccionesEditor` (T069) + totales en vivo (`subTotal`/`iva`/`importeNetoAPercibir`) + botón guardar que llama a `crearVentaGranos` (T067) en modo alta.
- [X] T071 [US6] `frontend/src/app/ventas/granos/nueva/page.tsx`: página que monta `VentaGranosForm` en modo alta; agregar botón "+ Nueva venta de granos" en `VentasGranosListado.tsx` (T055).

**Checkpoint**: Alta de Venta de Granos funcional de punta a punta — dominio nuevo cerrado end-to-end.

---

## Phase 9: User Story 7 - Editar y eliminar una venta de granos existente (Priority: P2)

**Goal**: Un usuario puede editar o eliminar una venta de granos ya cargada, con el mismo bloqueo exclusivo que Hacienda.

**Independent Test**: Editar una venta de granos agregando una deducción → `importeNetoAPercibir` baja; eliminar una venta de prueba → desaparece sin dejar ajustes/deducciones huérfanos (quickstart.md Escenario 8).

### Tests for User Story 7

- [X] T072 [P] [US7] Contract test `POST/DELETE /api/ventas-granos/{id}/lock` — mismo comportamiento que Hacienda (T023/T024), incluido `force: true`.
- [X] T073 [P] [US7] Contract test `PUT /api/ventas-granos/{id}` — sin lock → `409`; con lock válido, agrega una deducción → `importeNetoAPercibir` recalculado; `idVenta` inexistente → `404`.
- [X] T074 [P] [US7] Contract test `DELETE /api/ventas-granos/{id}` — `404` si no existe, `409` sin lock, `204` con lock válido; verificar (test de repository) que no quedan filas huérfanas en `Venta Granos_Ajustes`/`Venta Granos_Deducciones`.

### Implementation for User Story 7

- [X] T075 [US7] `backend/src/features/ventas_granos/repository_locks.py`: mismo patrón que `ventas_hacienda/repository_locks.py` (T026), sobre `dbo.VentaGranosEditLocks`.
- [X] T076 [US7] `backend/src/features/ventas_granos/schemas.py`: `VentaGranosEditRequest`, `LockRequest`, `LockResponse` (mismos shapes que Hacienda, T027).
- [X] T077 [US7] `backend/src/features/ventas_granos/repository.py`: `update_venta(id_venta, cabecera, ajustes, deducciones) -> dict` (reemplazo total, mismo patrón que T028) y `delete_venta(id_venta) -> None` (borra ajustes, deducciones, vínculos `VentaDocumentosRelacionados` con `TipoVenta = 'Granos'`, lock, y cabecera — mismo patrón que T036).
- [X] T078 [US7] `backend/src/features/ventas_granos/router.py`: `POST/DELETE /api/ventas-granos/{id}/lock`, `PUT /api/ventas-granos/{id}`, `DELETE /api/ventas-granos/{id}`.
- [X] T079 [US7] `frontend/src/services/ventasGranosApi.ts`: `adquirirLock`, `liberarLock`, `actualizarVentaGranos`, `eliminarVentaGranos`.
- [X] T080 [US7] `frontend/src/components/ventas-granos/VentaGranosForm.tsx`: modo edición con lock (mismo patrón que `VentaHaciendaForm.tsx`, T031) + botón "Eliminar venta" con confirmación (mismo patrón que T039).
- [X] T081 [US7] `frontend/src/app/ventas/granos/[idVenta]/editar/page.tsx`: monta `VentaGranosForm` en modo edición; enlace desde `VentasGranosListado.tsx`; botón "← Volver a Ventas de Granos" con `router.back()`.

**Checkpoint**: Las 7 historias de usuario funcionan de punta a punta, integradas. Ambos dominios (Hacienda y Granos) tienen alta/edición/eliminación/documentos relacionados (Hacienda) completos.

---

## Phase 10: Polish & Cross-Cutting Concerns

- [X] T082 [P] Verificar que `GET /api/ventas-hacienda` y sus filtros (005) siguen encontrando sin cambios las ventas ya migradas, filtrando por consignatario/fecha de una venta de prueba (regresión de 005).
- [X] T083 [P] Mostrar el aviso no bloqueante de `warnings` (documento duplicado, FR-009a/FR-012a) como toast en ambos formularios (`useToast`, ya existente).
- [X] T084 Ejecutar `cd backend && python -m pytest -q` y confirmar que todos los tests (existentes + nuevos de esta feature) pasan.
- [X] T085 Ejecutar `cd frontend && npx tsc --noEmit -p . && npx eslint .` y confirmar cero errores.
- [ ] T086 Correr manualmente los 10 escenarios de `specs/007-ventas-hacienda-granos/quickstart.md` contra el backend real (`WC`) y verificar contra SQL Server que ninguna escritura llegó a `LaHerencia` (SC-004).
- [ ] T087 Ejecutar el Escenario 9 de `quickstart.md` (SC-002/SC-003): tomar 5 `IdVenta` reales de `Venta Hacienda` y 5 de `Venta Granos`, recalcular manualmente sus totales con las fórmulas de data-model.md y confirmar que coinciden con lo que produce `calcular_totales`; documentar el resultado (mismo criterio que el Escenario 7/T040a de 006-carga-compras).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias — empieza de inmediato.
- **Foundational (Phase 2)**: depende de Setup — bloquea todas las historias de escritura (US1-US4, US6-US7). US5 (listado de lectura de Granos) no depende de Foundational.
- **Historias de Hacienda (Phase 3-6, US1-US4)**: US1 es independiente tras Foundational. US2/US3 dependen de que exista `create_venta`/cálculo de totales de US1 (reutilizan T012/T013), pero son historias separadas y verificables por su cuenta. US4 depende de que existan ventas cargadas (US1).
- **Historias de Granos (Phase 7-9, US5-US7)**: US5 es la más independiente (solo lectura, sin Foundational). US6 depende de los catálogos expuestos en US5 (T052/T054) pero no de Foundational más allá de las tablas de lock. US7 depende de que exista `create_venta`/cálculo de totales de US6.
- **Hacienda vs. Granos**: ambos grupos son independientes entre sí una vez cerrada Foundational — pueden desarrollarse en paralelo o en cualquier orden relativo (research.md recomienda Hacienda primero por menor riesgo, no por dependencia técnica).
- **Polish (Phase 10)**: depende de que las historias que se quieran entregar estén completas.

### Parallel Opportunities

- T003, T004, T005 (Foundational) son paralelas entre sí (tablas distintas).
- T006-T010 (tests de US1) son paralelas entre sí.
- T019, T020 (componentes de frontend de US1) son paralelas entre sí.
- T023-T025 (tests de US2), T033-T035 (tests de US3), T040-T041 (tests de US4) son paralelas entre sí dentro de cada historia.
- T046-T048 (tests de US5), T058-T061 (tests de US6), T072-T074 (tests de US7) son paralelas entre sí dentro de cada historia.
- T068, T069 (componentes de frontend de US6) son paralelas entre sí.
- El grupo completo de Hacienda (US1-US4) puede desarrollarse en paralelo al grupo completo de Granos (US5-US7) por un segundo desarrollador/sesión, una vez cerrada Foundational — son dominios sin dependencias cruzadas.

---

## Implementation Strategy

### MVP First (User Story 1)

1. Completar Phase 1 (Setup) y Phase 2 (Foundational) — bloqueante para escritura.
2. Completar Phase 3 (US1) — alta de venta de hacienda completa, sin edición/eliminación/documentos relacionados.
3. Validar con quickstart.md Escenarios 1 y 2 antes de seguir.

### Incremental Delivery

1. Setup + Foundational → base lista.
2. US1 → demo: alta de Venta de Hacienda funcionando end-to-end (MVP).
3. US2 + US3 → demo: edición y eliminación con bloqueo exclusivo.
4. US4 → demo: documentos relacionados.
5. US5 → demo: listado de Ventas de Granos (dominio nuevo, solo lectura).
6. US6 → demo: alta de Venta de Granos.
7. US7 → demo: edición y eliminación de Venta de Granos.
8. Polish → verificación final de no regresión y de la regla de oro (`WC`-only) en ambos dominios.
