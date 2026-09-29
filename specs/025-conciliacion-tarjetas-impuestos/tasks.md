---

description: "Task list for 025-conciliacion-tarjetas-impuestos"
---

# Tasks: Vincular líneas de resumen de tarjeta a pagos de Impuestos

**Input**: Design documents from `specs/025-conciliacion-tarjetas-impuestos/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md, quickstart.md

**Tests**: incluidos — mismo criterio que 023/024 (Principio V, escrituras financieras) y porque esta feature toca un mecanismo ya en producción (008/009, 1.598 vínculos reales) donde la no-regresión es un requisito explícito (FR-007).

**Organización**: por historia de usuario. US1 y US2 son ambas P1 — US2 (no regresión) no es "extra", es la condición para poder tocar un mecanismo en producción con confianza.

## Format: `[ID] [P?] [Story] Description`

## Path Conventions (de plan.md)

- Backend: `backend/src/features/tarjetas_resumenes/`, `backend/scripts/`, `backend/tests/`
- Frontend: `frontend/src/components/tarjetas-conciliacion/`, `frontend/src/services/`

---

## Phase 1: Setup

No hay esqueleto nuevo que crear — se extienden archivos ya existentes de 008/009. Sin tareas de Setup propias.

---

## Phase 2: Foundational (Blocking Prerequisites)

**⚠️ CRÍTICO**: `ALTER TABLE` sobre `Tarjetas_Resumenes_Lineas_Compras`, que tiene 1.598 filas reales en producción — T002 requiere confirmar con el usuario el backup a usar antes de T003.

- [X] T001 Confirmar con el usuario y documentar el backup verificado de `WC` a usar para este cambio de esquema (Constitution Check del plan.md) — dejar constancia en `backend/scripts/extender_vinculos_tarjetas_impuestos.py`.
- [X] T002 En `backend/scripts/extender_vinculos_tarjetas_impuestos.py`, escribir el DDL re-corrible: `ALTER COLUMN IdCompra int NULL` (de `NOT NULL` a `NULL`, data-model.md); `ADD IdImpuesto int NULL` con `FOREIGN KEY REFERENCES dbo.Impuestos(IdImpuesto)`; `ADD CONSTRAINT CK_..._OrigenUnico CHECK ((IdCompra IS NOT NULL AND IdImpuesto IS NULL) OR (IdCompra IS NULL AND IdImpuesto IS NOT NULL))`. Verificar antes de aplicar que las 1.598 filas existentes ya cumplen la constraint (todas tienen `IdCompra`, ninguna tiene `IdImpuesto`).
- [X] T003 Ejecutar el script contra `WC` (solo después de T001 confirmado) y verificar: la constraint se creó sin error (prueba de que las 1.598 filas existentes la cumplen), y `SELECT COUNT(*) FROM Tarjetas_Resumenes_Lineas_Compras` sigue dando 1.598.
- [X] T004 En `backend/src/features/tarjetas_resumenes/repository.py`, implementar `saldo_pendiente_impuesto(id_impuesto, excluir_id_linea) -> float`: `Impuestos.Importe` menos `SUM(ImporteImputado) FROM Tarjetas_Resumenes_Lineas_Compras WHERE IdImpuesto=? AND IdLineaConsumo<>?` (research.md §2, data-model.md). Extraer el `SUM(...)` a una constante SQL de módulo (ej. `_VINCULADO_IMPUESTO_SQL`) reutilizable tal cual por T012 — remediación D1 de `/speckit-analyze`: evita que el filtro de saldo pendiente del buscador (T012) reimplemente el mismo cálculo por separado y diverja con el tiempo.
- [X] T005 [P] En `backend/src/features/tarjetas_resumenes/schemas.py`, extender `DocumentoCandidato`: `idCompra: int | None = None` (deja de ser obligatorio), agregar `origen: str` (`"Compras"` \| `"Impuestos"`), `idImpuesto: int | None = None`, `saldoPendiente: float | None = None` (contracts/api.md).
- [X] T006 [P] Test de repository: `saldo_pendiente_impuesto` con y sin vínculos previos, en `backend/tests/test_tarjetas_resumenes_repository.py`.

**Checkpoint**: esquema listo en `WC`, el cálculo de saldo pendiente existe — recién ahora pueden empezar las historias.

---

## Phase 3: User Story 1 - Encontrar y vincular un pago de impuesto desde la conciliación de tarjeta (Priority: P1) 🎯 MVP

**Goal**: que "Sumar documentos de otro proveedor" encuentre pagos de Impuestos y se puedan vincular, solos o mezclados con Compras, con reparto proporcional y saldo pendiente cuando corresponde.

**Independent Test**: buscar "AFIP" en el buscador de una línea real sin conciliar, encontrar un pago real, vincularlo, y verificar que la línea queda conciliada con ese pago como respaldo (quickstart.md Escenario 1).

### Tests for User Story 1

- [X] T007 [P] [US1] Contract test: `GET /documentos-buscar?q=AFIP` devuelve candidatos con `origen: "Impuestos"` junto a los de Compras, en `backend/tests/contract/test_tarjetas_resumenes_documentos_buscar.py` (o el archivo de contract test existente para este endpoint), mockeando el repository.
- [X] T008 [P] [US1] Contract test: `POST .../compras/lote` con `idsImpuesto` no vacío vincula correctamente y devuelve los vínculos con `origen: "Impuestos"`.
- [X] T009 [P] [US1] Test de repository: `buscar_documentos("ARBA")` devuelve filas de `Impuestos` con `IdOrganismo` asignado, y NINGUNA fila con `IdOrganismo IS NULL` (FR-006), en `backend/tests/test_tarjetas_resumenes_repository.py`.
- [X] T010 [P] [US1] Test de repository: vincular un pago de Impuestos junto con un documento de Compras en el mismo lote reparte proporcionalmente cuando la suma supera la línea (reusa `calcular_imputacion`, sin cambios ahí — research.md §3).
- [X] T011 [P] [US1] Test de repository: vincular un pago de Impuestos con `importeImputado` mayor a su `saldo_pendiente_impuesto` rechaza con `ValueError` (FR-005, 409 en el contrato).
- [X] T011a [P] [US1] Test de repository: un pago de Impuestos cuyo saldo pendiente ya llegó a cero (totalmente vinculado en otra línea) NO aparece en `buscar_documentos` (edge case de spec.md, remediación C2 de `/speckit-analyze`).
- [X] T011b [P] [US1] Test de repository: dos `vincular_compra`/`vincular_compras_lote` sucesivos sobre el mismo pago de Impuestos cuya suma excede su importe real — el segundo falla viendo el saldo pendiente recalculado en ese momento, no el que existía al iniciar el primero (FR-009, remediación C3 de `/speckit-analyze`).

### Implementation for User Story 1

- [X] T012 [US1] En `repository.py`, extender `buscar_documentos(texto)`: `UNION ALL` entre la consulta actual sobre `Compras` y una nueva sobre `dbo.Impuestos i JOIN dbo.Contactos c ON c.IdContacto = i.IdOrganismo WHERE i.IdOrganismo IS NOT NULL AND (c.[Razon Social] LIKE ? OR i.[Numero de documento] LIKE ?) AND i.Importe > (SELECT ISNULL(SUM(v.ImporteImputado), 0) FROM dbo.Tarjetas_Resumenes_Lineas_Compras v WHERE v.IdImpuesto = i.IdImpuesto)` (mismo `_VINCULADO_IMPUESTO_SQL` de T004 — remediación D1) — cada fila del segundo lado con `origen: "Impuestos"`, `idCompra: None`, `idImpuesto: i.IdImpuesto`, `proveedor: c.[Razon Social]` (el nombre del organismo), `moneda: None`, `tipoDeCambio: None` (research.md §3/§4). El filtro `i.Importe > vinculado` excluye los pagos ya cubiertos por completo (edge case de spec.md, remediación C2 de `/speckit-analyze`).
- [X] T013 [US1] En `repository.py`, extender `_documento_dict` (o crear un `_documento_impuesto_dict` paralelo) para incluir `origen`/`idCompra`/`idImpuesto`/`saldoPendiente` en la forma ya usada por Compras — `saldoPendiente` solo poblado cuando `origen == "Impuestos"` (llama a T004).
- [X] T014 [US1] En `repository.py`, extender `get_documentos_por_ids` para aceptar también ids de Impuestos (o agregar `get_documentos_impuestos_por_ids` paralela) — usada al reabrir una línea ya conciliada para mostrar su respaldo completo.
- [X] T015 [US1] En `repository.py`, extender `vincular_compra`: nuevo parámetro `id_impuesto: int | None = None` (junto al ya existente `id_compra: int | None`) — exactamente uno presente; si es Impuestos, valida contra `saldo_pendiente_impuesto` (T004) antes del `INSERT INTO Tarjetas_Resumenes_Lineas_Compras (IdLineaConsumo, IdCompra, IdImpuesto, ImporteImputado)`.
- [X] T016 [US1] En `repository.py`, extender `vincular_compras_lote`: nuevo parámetro `ids_impuesto: list[int] = []` (junto al ya existente `ids_compra`) — combina ambos en la lista de `docs` que arma antes de llamar a `conciliacion_documentos.calcular_imputacion`/`repartir`, validando el saldo pendiente de cada id de Impuestos antes de confirmar.
- [X] T017 [US1] En `router.py`, extender `VincularCompraRequest`/`VincularLoteRequest` (schemas.py) con los campos opcionales del contrato (`idImpuesto`, `idsImpuesto`) y pasarlos a `vincular_compra`/`vincular_compras_lote`; mapear el `ValueError` de saldo pendiente excedido a `409` (mismo patrón `except ValueError` ya usado en el router).
- [X] T018 [US1] En `router.py`, extender `previsualizar_conciliacion` (`GET .../conciliacion`) con `idsImpuesto: list[int] = Query(default=[])`, combinando con `idsCompra` antes de llamar a `repository.calcular_conciliacion`.
- [X] T019 [US1] Actualizar `frontend/src/services/tarjetasResumenesApi.ts`: `DocumentoCandidato` con los campos nuevos (`origen`, `idImpuesto`, `saldoPendiente`), y las funciones de vincular/previsualizar con los parámetros nuevos opcionales.
- [X] T020 [US1] En `frontend/src/components/tarjetas-conciliacion/PanelConciliacion.tsx`, mostrar el `origen` de cada candidato distinguido visualmente (badge o etiqueta — nunca "proveedor" para un organismo, FR-004) y, si `saldoPendiente` está presente, mostrarlo junto al importe.
- [X] T020a [US1] Confirmar que `quitar_vinculo_compra`/`DELETE .../compras/{idVinculo}` (sin cambios de firma, contracts/api.md) desvincula correctamente una fila con `IdImpuesto` poblado — no asumir que "no hace falta tocar nada" sin probarlo (FR-008, remediación C1 de `/speckit-analyze`).
- [X] T020b [P] [US1] Test de repository: vincular un pago de Impuestos, desvincularlo (`quitar_vinculo_compra`), y verificar que `saldo_pendiente_impuesto` vuelve a su valor original y que el pago reaparece en `buscar_documentos` (FR-008, remediación C1).

**Checkpoint**: se puede buscar, vincular, desvincular y repartir pagos de Impuestos de punta a punta, solos o mezclados con Compras.

---

## Phase 4: User Story 2 - No perder lo que ya funciona para Compras (Priority: P1)

**Goal**: cero regresión sobre el mecanismo de conciliación de tarjetas ya en producción.

**Independent Test**: correr toda la suite de tests ya existente de `tarjetas_resumenes` (incluidos los 18 casos de `conciliacion_documentos.py` y los de contrato/repository de 008/009) y confirmar que ningún resultado cambia (quickstart.md Escenario 4).

### Tests for User Story 2

- [X] T021 [P] [US2] Test de repository: `buscar_documentos("Garbarino")` (un proveedor real de Compras) sigue devolviendo exactamente lo mismo que antes de esta feature — mismos campos, mismo orden, sin el campo `origen` faltando (ahora siempre `"Compras"` para estos).
- [X] T022 [P] [US2] Test de repository: `vincular_compras_lote` con solo `ids_compra` (sin `ids_impuesto`, el caso 100% actual) da exactamente el mismo resultado que antes del cambio — mismos `imputados`, misma `diferencia`.
- [X] T023 [P] [US2] Test de integración: correr `test_conciliacion_documentos.py` completo (18 casos, incluido el de reparto proporcional del 2026-09-29) sin ningún cambio en `conciliacion_documentos.py` — confirma research.md §3 (el módulo puro no se tocó).

### Implementation for User Story 2

- [X] T024 [US2] Correr la suite completa de `backend/tests/` (no solo `-k tarjetas`) y confirmar 0 regresiones, igual que se hizo tras 023/024 (encontrar y corregir cualquier test con una firma de función desactualizada, mismo patrón que los 2 hallazgos de la tanda anterior).
- [X] T025 [US2] Verificar manualmente contra `WC` (quickstart.md Escenario 4): reabrir una línea de resumen ya conciliada contra Compras antes de esta feature y confirmar que se sigue viendo exactamente igual (documento, importe, estado).

**Checkpoint**: MVP real completo — US1 + US2 cubren "agregar Impuestos sin romper Compras".

---

## Phase 5: Polish & Cross-Cutting Concerns

- [X] T026 [P] Verificar SC-004 contra `WC` real: buscar por cada uno de los 4 organismos reales (AFIP, ARBA, Municipalidad de Bolivar, UATRE) y confirmar que aparecen resultados para cada uno.
- [X] T027 Ejecutar los 4 escenarios de `quickstart.md` manualmente contra `WC`.
- [X] T028 Correr `pytest` completo en `backend/` y `tsc --noEmit` en `frontend/`.
- [X] T029 Reconstruir (`npm run build`) y reiniciar el frontend de producción, y reiniciar el backend si no recogió los cambios de esquema automáticamente.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Foundational (Phase 2)**: BLOQUEA ambas historias — el esquema y el cálculo de saldo pendiente son prerequisito de todo lo demás.
- **User Story 1 (Phase 3)**: depende de Foundational.
- **User Story 2 (Phase 4)**: depende de Foundational y de que US1 exista (para tener algo que no-regresionar contra el código nuevo) — pero conceptualmente es una validación continua, no secuencial: T021-T023 pueden escribirse en paralelo con Phase 3 y correrse al final.
- **Polish (Phase 5)**: depende de ambas historias.

### Parallel Opportunities

- T004-T006 (Foundational) en paralelo.
- T007-T011 (tests US1) en paralelo entre sí.
- T021-T023 (tests US2) en paralelo entre sí, y en paralelo con la implementación de US1 (son regresión, no dependen del código nuevo para escribirse, solo para correr al final).

## Implementation Strategy

### MVP real

Setup (n/a) → Foundational → US1 → US2. En un feature que extiende un mecanismo ya en producción, US2 (no regresión) es tan parte del MVP como US1 — no es un "extra" de Polish.
