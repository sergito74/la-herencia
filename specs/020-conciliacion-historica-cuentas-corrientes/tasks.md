---

description: "Task list for 020-conciliacion-historica-cuentas-corrientes"
---

# Tasks: Conciliación histórica de cuentas corrientes de proveedores y ventas

**Input**: Design documents from `/specs/020-conciliacion-historica-cuentas-corrientes/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/cli-script.md, contracts/api.md, quickstart.md

**Tests**: incluidos (Constitución, Principio V exige el chequeo automatizado más acotado; mismo criterio que 004/019).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Puede ejecutarse en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: US1 (aplicar histórico), US2 (revisar mejor esfuerzo/excepciones), US3 (verificar saldo vs Access)

## Phase 1: Setup

**Purpose**: esquema y estructura de módulo compartidos por todas las historias.

- [X] T001 Crear script de migración de esquema `backend/scripts/migrar_conciliacion_historico_esquema.py` — **desviación**: sin flag `--apply` (no hace falta: es DDL idempotente vía `IF NOT EXISTS`/`IF OBJECT_ID IS NULL`, mismo patrón real de `crear_tabla_aplicaciones_pago.py`, que tampoco tiene dry-run)
- [X] T002 Ejecutar `migrar_conciliacion_historico_esquema.py` contra `WC` y verificar con `INFORMATION_SCHEMA.COLUMNS`/`INFORMATION_SCHEMA.TABLES` — hecho 2026-09-25, tras backup verificado (`backups/WC_pre_conciliacion_historico_20260925.bak`, 79 MB, `BACKUP DATABASE` vía `pyodbc`, sin `COMPRESSION` — no soportada en esta instancia Express)
- [X] T003 [P] Crear estructura del módulo `backend/src/features/conciliacion_historico/` — **desviación**: solo `__init__.py` + `repository.py` por ahora; `router.py`/`schemas.py` se crean recién en US2, cuando existan endpoints reales que definir (evita archivos vacíos sin contenido)
- [ ] T004 [P] Registrar `conciliacion_historico.router` en el router principal — **diferida a US2** (no hay router todavía, ver T003)

**Checkpoint**: esquema listo, módulo montado — puede arrancar cualquier historia.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: utilidades compartidas por US1/US2 que no pertenecen a ninguna historia individual.

- [X] T005 Implementar `movimientos_sin_aplicar(fecha_desde, fecha_hasta)` en `backend/src/features/conciliacion_historico/repository.py` — **desviación de alcance**: recorre `bna`, `galicia`, `efectivo`, `valores-recibidos`, `tarjetas` (no `valores-propios`: confirmado en `tesoreria/matching.py` que ese medio no tiene columna de contacto y siempre es `sin_coincidencia`, por lo tanto siempre terminaría en excepción "sin contacto identificable" — se excluye de la enumeración en vez de generar esa excepción para el 100% de sus filas)
- [X] T006 Implementar `clasificar_movimiento(origen_movimiento, id_movimiento_origen)` en el mismo `repository.py` — **renombrada/refactorizada respecto al plan**: en vez de una función `buscar_mejor_combinacion` que reimplementa el matching, llama directamente a `sugerencia.sugerir` (019) y clasifica su resultado ya calculado (exacta si `saldoSinAsignar <= TOLERANCIA_REDONDEO_APLICACION`, mejor esfuerzo si `<= 2%` del importe, excepción en otro caso) — más DRY que la firma original prevista en tasks.md/data-model.md, sin reimplementar el FIFO

**Checkpoint**: utilidades de matching listas — US1 puede implementarse.

---

## Phase 3: User Story 1 - Aplicar retroactivamente el backlog histórico de movimientos (Priority: P1) 🎯 MVP

**Goal**: generar aplicaciones automáticas (exactas o de mejor esfuerzo) para los movimientos históricos sin aplicar, dejando en un listado de excepciones los que no tienen ningún candidato.

**Independent Test**: correr el script en modo dry-run y luego con `--apply` sobre datos reales de `WC`, y verificar que la cantidad de movimientos "sin aplicar" en 2015-2026 se reduce, con filas nuevas en `AplicacionesPago` marcadas `Origen IN ('automatica-exacta','automatica-mejor-esfuerzo')`.

### Tests for User Story 1

- [X] T007 [P] [US1] Test en `backend/tests/test_conciliacion_historico_script.py`: `clasificar_movimiento` con coincidencia exacta → `automatica-exacta`
- [X] T008 [P] [US1] Test: `aplicar_clasificacion` inserta una fila por sugerencia con los parámetros correctos (`Origen`, `Usuario='sistema-conciliacion-020'`, importe) — verificado con `execute_insert_returning_id` monkeypatcheado, no contra `WC` real (mismo criterio que los tests existentes de 019)
- [X] T009 [P] [US1] Test: diferencia del 1.5% (dentro del 2%) → `automatica-mejor-esfuerzo` con `notaConciliacion` describiendo la diferencia y el documento
- [X] T010 [P] [US1] Test: diferencia del 50% (excede el 2%) → `excepcion` con motivo `'sin documentos candidatos'`; test adicional para el caso sin ninguna sugerencia FIFO
- [X] T011 [P] [US1] Test: contacto no identificable → `excepcion` con motivo `'sin contacto identificable'`, sin excepción de Python
- [X] T012 [P] [US1] Test: `movimientos_sin_aplicar` no vuelve a listar un movimiento que ya quedó con aplicación vigente (simula la segunda corrida) → re-ejecutar el script no duplica
- [X] T013 [P] [US1] Test: un movimiento con aplicación vigente preexistente (manual o no) queda excluido de `movimientos_sin_aplicar`, sin distinguir el `Origen` de esa aplicación (el chequeo es "¿tiene algo vigente?", no "¿es manual?")

**Nota de alcance**: los 7 tests anteriores validan la lógica de clasificación y filtrado contra fixtures en memoria (monkeypatch), igual que la suite existente de 019 (`test_aplicaciones_pago_endpoints.py`) — ningún test automatizado escribe contra `WC` real; la validación end-to-end contra datos reales queda para la corrida manual del dry-run (T002/quickstart Escenario 1) antes de `--apply`.

### Implementation for User Story 1

- [X] T014 [US1] Crear `backend/scripts/conciliar_historico_cuentas_corrientes.py` (contrato: `contracts/cli-script.md`) con `argparse` para `--apply` y `--contacto <id>`, dry-run por defecto, usando `movimientos_sin_aplicar` y `clasificar_movimiento` (T005/T006)
- [X] T015 [US1] Implementado en el script (`_imprimir_resumen`): clasifica cada movimiento e imprime totales por categoría
- [X] T016 [US1] Implementado (`aplicar_clasificacion`, llamado desde `main` solo si `--apply`): `INSERT` en `AplicacionesPago` vía `execute_insert_returning_id` — **desviación**: se usa esta función (ya existente en `src/db/connection.py` para inserts con `OUTPUT`) en vez de `execute_write`/`execute_write_transaction`, porque cada aplicación necesita su `IdAplicacion` para el log/CSV, igual que ya hace `aplicaciones_pago.router` al confirmar una aplicación manual
- [X] T017 [US1] Implementado (`_escribir_csv`): `conciliacion_historico_<timestamp>.csv` con una fila por movimiento procesado
- [X] T018 [US1] Verificado: el script llama a `_assert_target_is_wc()` al inicio de `main()`, antes de cualquier lectura/escritura (mismo guard que `migrar_ordenes.py`)

**Checkpoint**: el histórico puede aplicarse de punta a punta desde línea de comandos, de forma segura y re-ejecutable. **Aplicado contra datos reales de `WC` (2026-09-25)**, tras backup verificado (`backups/WC_pre_conciliacion_historico_20260925.bak`):

- Dry-run inicial: 12.762 movimientos sin aplicar → 5.010 exactos, 3 mejor esfuerzo, 7.749 excepciones (mayormente impuestos/transferencias/retenciones sin documento de compra/venta asociable — ver memoria `project_impuestos_boletas_faltantes`, hallazgo real: faltan boletas de impuestos cargadas, no es "fuera de alcance").
- **Bug real encontrado y corregido en la primera corrida de `--apply`**: el script reclasificaba cada movimiento dos veces (una para el resumen, otra al aplicar); entre medio, aplicar un movimiento consumía saldo de un documento compartido con otro movimiento del mismo contacto, y la reclasificación tardía de ese segundo movimiento ya no encontraba el mismo resultado → `KeyError: 'sugerencias'`. Solo 7 filas habían quedado insertadas (todas `automatica-exacta`, consistentes) antes del crash — sin necesidad de rollback, por el diseño idempotente. Corregido: clasificar y aplicar en una sola pasada por movimiento (`_procesar` en `conciliar_historico_cuentas_corrientes.py`).
- **Segundo bug real encontrado en la misma corrida**: columna `Origen` era `varchar(20)`, pero `'automatica-mejor-esfuerzo'` tiene 25 caracteres → truncamiento. Corregido: `ALTER COLUMN Origen varchar(30)` (`data-model.md` actualizado).
- Corrida final exitosa: 12.700 movimientos (62 menos que el dry-run porque ya no vuelve a contar los 7 aplicados en el intento fallido) → **3.719 exactos, 5 mejor esfuerzo, 8.976 excepciones**; total insertado en `AplicacionesPago`: **8.379 filas `automatica-exacta`** + **11 filas `automatica-mejor-esfuerzo`** (un movimiento puede generar más de una fila si se combina con varios documentos). Los conteos de movimientos bajaron respecto al dry-run porque este SÍ descuenta saldo real entre movimientos del mismo run (el dry-run, al no escribir nada, podía "ver" el mismo documento como disponible para más de un movimiento a la vez — la corrida real es la que refleja el reparto FIFO correcto).
- **Idempotencia confirmada (T012) contra datos reales**: segundo dry-run tras el `--apply` → 8.976 movimientos restantes (exactamente los que quedaron como excepción), 0 exactos, 0 mejor esfuerzo. Correr el script de nuevo no reprocesa ni duplica nada de lo ya aplicado.

---

## Phase 4: User Story 2 - Revisar las aplicaciones de mejor esfuerzo y las excepciones (Priority: P1)

**Goal**: exponer, por contacto, el resultado de la conciliación histórica (exactas / mejor esfuerzo / excepciones) para que el usuario decida qué revisar y corregir.

**Independent Test**: con datos ya conciliados por US1, consultar `GET /api/conciliacion-historico/resumen` y `GET /api/conciliacion-historico/{idContacto}/detalle` y verificar que reflejan correctamente las categorías, y que anular una aplicación de mejor esfuerzo (endpoint existente de 019) se refleja en una consulta posterior al detalle.

### Tests for User Story 2

- [X] T019 [P] [US2] Test en `backend/tests/test_conciliacion_historico_endpoints.py`: `GET /api/conciliacion-historico/resumen` devuelve los conteos correctos por contacto (mockeado, mismo criterio que 019)
- [X] T020 [P] [US2] Test: `GET /api/conciliacion-historico/resumen?soloConDudas=true` pasa el filtro correctamente a `repository.resumen_por_contacto`
- [X] T021 [P] [US2] Test: `GET /api/conciliacion-historico/{idContacto}/detalle` lista aplicaciones con `origen`/`notaConciliacion` y excepciones con `subcategoria`/`motivo`
- [ ] T022 [P] [US2] Test de integración real (anular mejor esfuerzo → detalle refleja el cambio) — **diferido**: no bloquea el uso de la pantalla, se valida a mano cuando exista el frontend de revisión

### Implementation for User Story 2

- [X] T023 [US2] Implementado `resumen_por_contacto(solo_con_dudas)` — **desviación de diseño real, encontrada corriendo contra `WC`**: en vez de recalcular `movimientos_sin_aplicar` en cada consulta (~10 minutos medido), lee de `dbo.ConciliacionHistoricoLog`, una tabla nueva que el script llena en cada corrida (`registrar_en_log`). Categorías devueltas: `aplicadosExactos`, `aplicadosMejorEsfuerzo`, `revisionManual` (excepción con documento comercial existente — candidato real a revisar), `fueraDeAlcance` (excepción sin contacto o sin ningún documento comercial jamás) — más útil que el "sinAplicar" único que preveía el plan original, ver research.md §6
- [X] T024 [US2] Implementado `detalle_contacto(id_contacto)` — lee `AplicacionesPago` (join con el log para filtrar por contacto) + `ConciliacionHistoricoLog` para las excepciones
- [X] T025 [US2] Schemas Pydantic en `schemas.py` (`ResumenResponse`, `DetalleContactoResponse`)
- [X] T026 [US2] Endpoints implementados y registrados en `src/main.py`
- [X] T027 [US2] Pantalla de revisión en `frontend/src/app/finanzas/conciliacion-historico/page.tsx` + `frontend/src/components/conciliacion-historico/ConciliacionHistorica.tsx`: tabla de resumen por contacto (filtro "solo con dudas"), detalle expandible con aplicaciones automáticas (marcando mejor esfuerzo) y excepciones (con subcategoría en texto legible). Link agregado desde `/finanzas/cuentas-corrientes`. `tsc --noEmit` y `eslint` sin errores; probado end-to-end levantando el backend real y consultando ambos endpoints con curl (datos reales de `WC`)

**Validado contra datos reales de `WC` (2026-09-25)**, tras backfillear en `ConciliacionHistoricoLog` los 3.786 movimientos aplicados por US1 (que la corrida de log no había capturado por no haber sido reprocesados — bug de diseño real, corregido: `registrar_en_log` ya no vacía la tabla entera, solo las claves que va a reescribir):

- Log consistente: 3.781 exactos + 5 mejor esfuerzo + 8.976 excepciones = 12.762 (coincide exactamente con el total procesado desde el inicio).
- `resumen_por_contacto(solo_con_dudas=True)`: **190 contactos** con algo para revisar. Los primeros: Banco Nacion (828 casos "revisión manual" — en rigor un banco propio, pero tiene 2 `Compras` cargadas por error de datos, así que la heurística binaria lo marca revisable; queda para que el usuario lo descarte a mano), Cargill (291), XXXXXXXXX (138), Irma Miranda (118), CV1 (106), Sancor Seguros (72), Municipalidad de Bolívar (69), Jauregui y Morales (65).
- `detalle_contacto(258)` (Cargill): 285 aplicaciones automáticas + 291 excepciones, todas con motivo/subcategoría — verificado que responde correctamente.
- **Caveat conocido**: la subcategoría `revisionManual` es una heurística binaria ("¿tuvo algún documento comercial alguna vez?"), no garantiza que el caso sea realmente accionable (ver Banco Nacion arriba) — el propósito de US2 es justamente que el usuario filtre esos falsos positivos con criterio humano, no que el sistema los resuelva solo.

**Checkpoint**: US1 y US2 funcionan juntas a nivel backend — el histórico se aplica y se puede auditar por API. Falta la pantalla de frontend (T027) para que el usuario no dependa de llamar a la API a mano.

---

## Phase 5: User Story 3 - Verificar el saldo de cuenta corriente contra el sistema anterior (Priority: P2)

**Goal**: comparar, por contacto, el saldo actual (004) contra el saldo de referencia cargado desde Access, marcando cada contacto como conciliado o con diferencia.

**Independent Test**: cargar un archivo de referencia de prueba con `cargar_saldos_referencia_access.py`, y verificar que `GET /api/conciliacion-historico/saldos` calcula correctamente la diferencia y el estado para cada contacto cargado.

### Tests for User Story 3

- [ ] T028 [P] [US3] Test en `backend/tests/test_conciliacion_historico_saldos.py`: `cargar_saldos_referencia_access.py` hace upsert por `IdContacto` (una segunda carga con el mismo contacto reemplaza el `SaldoAccess`/`FechaCorte` anterior, no acumula filas)
- [ ] T029 [P] [US3] Test: para un contacto con `SaldoAccess` igual (dentro de `TOLERANCIA_SALDO`) al saldo actual de 004, `GET /api/conciliacion-historico/saldos` lo marca `estado='conciliado'`
- [ ] T030 [P] [US3] Test: para un contacto con diferencia mayor a `TOLERANCIA_SALDO`, se marca `estado='con-diferencia'` mostrando el monto exacto de la diferencia
- [ ] T031 [P] [US3] Test: un contacto sin fila en `SaldosReferenciaAccess` no aparece en la respuesta de `/saldos`
- [ ] T032 [P] [US3] Test: el filtro `?estado=con-diferencia` devuelve únicamente los contactos en ese estado

### Implementation for User Story 3

- [ ] T033 [US3] Crear `backend/scripts/cargar_saldos_referencia_access.py`: lee un CSV/Excel (`IdContacto`, `SaldoAccess`, `FechaCorte`) y hace upsert en `SaldosReferenciaAccess`, mismo patrón dry-run/`--apply` que el resto de los scripts de la feature
- [ ] T034 [US3] Implementar `comparar_saldos(estado: str | None)` en `backend/src/features/conciliacion_historico/repository.py`: para cada `IdContacto` en `SaldosReferenciaAccess`, obtiene `saldoActual` reutilizando el repository existente de `cuentas_corrientes` (004) sin modificarlo, calcula `diferencia` y `estado` con `TOLERANCIA_SALDO = 1.0` (valor inicial, documentado como configurable en el propio código)
- [ ] T035 [US3] Implementar `GET /api/conciliacion-historico/saldos` en `router.py`, con el filtro `estado` (según `contracts/api.md`)
- [ ] T036 [US3] Agregar a la pantalla de revisión del frontend (T027) una vista de "Verificación de saldos" que liste el resultado de `/saldos`, permita filtrar por estado, y enlace cada contacto "con diferencia" al detalle de conciliación de US2 para correlacionar la causa

**Checkpoint**: las 3 historias funcionan de forma independiente y en conjunto — histórico aplicado, revisable, y verificado contra Access.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T037 [P] Ejecutar los 6 escenarios de `quickstart.md` contra datos reales de `WC` (con backup verificado antes de cualquier `--apply`) y documentar resultado
- [ ] T038 Ejecutar `pytest backend/tests/test_conciliacion_historico_*.py` y confirmar 100% en verde
- [ ] T039 [P] Revisar formato de números y convenciones de UX (memoria `feedback_formato_numeros`) en las pantallas de revisión y verificación de saldos
- [ ] T040 Actualizar `specs/020-conciliacion-historica-cuentas-corrientes/data-model.md` si la corrida real contra `WC` revela ajustes necesarios en `TOLERANCIA_SALDO` o en el criterio de "mejor esfuerzo" (documentar el valor final calibrado, igual que se hizo con la tolerancia 2% de conciliación de documentos USD)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias.
- **Foundational (Phase 2)**: depende de Setup — BLOQUEA US1 (el matching de mejor esfuerzo no existe sin T005/T006).
- **User Stories (Phase 3-5)**: todas dependen de Foundational. US1 es prerrequisito real de US2 (no hay nada que revisar sin aplicaciones generadas) y de US3 (verificar saldo sin haber aplicado el histórico da diferencias que en realidad son "falta de aplicar", no errores de datos) — se implementan y prueban en ese orden, aunque los endpoints de US2/US3 en sí son código independiente.
- **Polish (Phase 6)**: depende de que las tres historias estén completas.

### Parallel Opportunities

- T003/T004 (Setup) en paralelo con T001/T002 una vez decidido el esquema.
- Todos los tests marcados [P] de una misma historia en paralelo entre sí, antes de su implementación.
- T028-T032 (tests de US3) pueden escribirse en paralelo con la implementación de US1/US2, ya que dependen de datos que van a existir pero no del código de esas historias.

---

## Implementation Strategy

### MVP First (User Story 1)

1. Setup + Foundational.
2. US1 — ya es demostrable: correr el script sobre datos reales y ver el histórico aplicado.
3. **Parar y validar** con el usuario el resultado del dry-run antes de correr `--apply` sobre todo el histórico (mismo criterio de precaución que 011/`migrar_ordenes.py`).

### Incremental Delivery

1. Setup + Foundational → esquema y utilidades listas.
2. US1 → histórico aplicado (con mejor esfuerzo marcado y excepciones listadas).
3. US2 → auditoría y corrección manual de lo dudoso.
4. US3 → verificación final del saldo contra Access.
5. Polish → validación contra `quickstart.md` y calibración de tolerancias con datos reales.
