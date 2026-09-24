---

description: "Task list for Motor de auto-clasificación de Rubro/Centro de Costos/Cultivo/Campaña"
---

# Tasks: Motor de auto-clasificación de Rubro/Centro de Costos/Cultivo/Campaña

**Input**: Design documents from `specs/017-imputacion-automatica-costos/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api-imputacion.md, quickstart.md

## Phase 1: Setup

- [X] T001 Crear la estructura del feature: `backend/src/features/imputacion/{__init__.py,schemas.py,motor.py,repository.py,router.py}`, `frontend/src/app/imputacion/{page.tsx,comparacion/page.tsx}`, `frontend/src/components/imputacion/{PropuestaCard.tsx,ComparacionCultivoCampania.tsx}`, `frontend/src/services/imputacionApi.ts` (archivos vacíos/esqueleto, sin lógica todavía)
- [X] T002 [P] Implementar `backend/scripts/crear_tablas_imputacion.py` (idempotente, sigue el patrón de `crear_tablas_auth.py`): `dbo.ImputacionPropuestas` (IdPropuesta int identity PK, IdCorrida uniqueidentifier, Origen varchar(10), IdDetalleCompra int, IdOrdenTrabajo int NULL, IdLote int NULL, IdCultivo int NULL, IdCampania int NULL, IdCentroCosto int NULL, EsGanaderia bit NULL, Importe money, Estado varchar(20), FechaCalculo datetime2, FechaAprobacion datetime2 NULL); `dbo.OrdenesContratistaFacturas` (IdVinculo int identity PK, IdOrdenTrabajo int, IdCompra int, sin restricción de unicidad por IdOrdenTrabajo — a diferencia de la tabla vieja); `dbo.ImputacionReferencias` (IdProducto int, EsGanaderia bit, IdCultivo int NULL, IdCampania int NULL, FechaActualizacion datetime2, PK compuesta IdProducto+EsGanaderia)
- [X] T003 Ejecutar `crear_tablas_imputacion.py` contra `WC` y verificar las 3 tablas creadas

## Phase 2: Foundational (bloqueante para todas las historias)

- [X] T004 Implementar `backend/scripts/migrar_vinculo_contratista.py` (idempotente): copia 1:1 todas las filas de `dbo.Ordenes_Trabajo_Contratista_Factura` a `dbo.OrdenesContratistaFacturas` (mismo IdOrdenTrabajo/IdCompra), sin borrar la tabla vieja (queda de referencia histórica, no se vuelve a escribir); ejecutarlo contra `WC` y verificar que el conteo de filas coincide
- [X] T005 [P] Implementar `backend/src/features/imputacion/schemas.py`: Pydantic models `PropuestaFraccion` (todas las columnas de `ImputacionPropuestas` per data-model.md, `Estado` como Literal["Pendiente","Aprobada","RequiereIntervencion"], `Origen` como Literal["Insumo","Contratista"]), `AprobarPropuestaIn` (correcciones opcionales), `ComparacionCampaniaOut`
- [X] T006 [P] Implementar `backend/src/features/imputacion/repository.py` con las funciones base reutilizadas por todas las historias: `guardar_corrida(origen, id_detalle_compra, fracciones: list[dict]) -> IdCorrida` (INSERT de todas las fracciones con un `IdCorrida` nuevo, `Estado` default `'Pendiente'` salvo lo que el caller marque distinto — no borra corridas anteriores, solo la última por `IdDetalleCompra` cuenta como vigente), `corrida_vigente(id_detalle_compra) -> IdCorrida | None`, `listar_propuestas(estado?, origen?, idDetalleCompra?, page, pageSize)`
- [X] T007 [P] Implementar `backend/src/features/imputacion/repository.py::obtener_referencia(id_producto, es_ganaderia) -> dict | None`: lee `ImputacionReferencias` por `(IdProducto, EsGanaderia)` y devuelve la última clasificación aprobada/corregida para ese contexto, o `None` si no hay ninguna todavía (soporte de lectura para el "aprendizaje simple" de FR-008 — el lado de escritura es `actualizar_referencia`, historia US2)
- [X] T008 Registrar `imputacion_router` (vacío, sin endpoints todavía) en `backend/src/main.py`, mismo patrón que los demás routers de `src/features/*`
- [X] T009 [P] Implementar `frontend/src/services/imputacionApi.ts` con los tipos TypeScript espejo de `PropuestaFraccion`/`AprobarPropuestaIn`/`ComparacionCampaniaOut` (sin funciones de fetch todavía, solo los tipos)

**Checkpoint**: tablas creadas, migración de datos corrida, esqueleto de repository/schemas listo (incluida la lectura de referencias para el aprendizaje simple) — las historias de usuario pueden implementarse.

---

## Phase 3: User Story 1 - Ver la propuesta de reclasificación de una factura de insumo (Priority: P1) 🎯 MVP

**Goal**: calcular y mostrar, para una factura de insumo, el reparto propuesto entre Agricultura/Ganadería y Cultivo/Campaña según el consumo real, con su trazabilidad.

**Independent Test**: abrir una factura de insumo con consumo real en Órdenes de Trabajo y ver el reparto propuesto con el desglose de origen (quickstart.md Escenarios 1-2).

### Tests for User Story 1

- [X] T010 [P] [US1] Test `backend/tests/test_imputacion_motor.py::test_consumo_integro_una_sola_orden`: una factura de insumo vinculada a un remito consumido 100% por una sola Orden de un Cultivo/Campaña (con `Ordenes_Trabajo.IdRubro IS NULL`) → una única fracción con el importe total (quickstart Escenario 1)
- [X] T011 [P] [US1] Test `backend/tests/test_imputacion_motor.py::test_consumo_parcial_multi_campania_y_stock`: consumo repartido entre dos Órdenes de distinto Cultivo/Campaña más saldo en stock → tres fracciones que suman el importe total del renglón, la de stock en `Estado='Aprobada'` automáticamente (quickstart Escenario 2)
- [X] T012 [P] [US1] Test `backend/tests/test_imputacion_motor.py::test_reparto_agricultura_ganaderia`: producto consumido por una Orden de Trabajo (agrícola, `IdRubro IS NULL`) y por una baja de stock (`dbo.Stock_Bajas_Detalle`/`dbo.Stock_Bajas`, salida tipo `B{id}` ya expuesta por `stock_datos.calcular_stock`) cuyo `IdCentro` resuelve a un Centro de Costos de Ganadería → dos fracciones, una con `EsGanaderia=0` y otra `EsGanaderia=1` (mecanismo documentado en research.md — confirmar con el usuario antes de implementar si no coincide con la realidad)
- [X] T013 [P] [US1] Test `backend/tests/test_imputacion_motor.py::test_orden_sin_cultivo_imputa_adm_general`: consumo de insumo por una Orden de Trabajo con `IdRubro IS NOT NULL` (mantenimiento/infraestructura, sin distribución de cultivo) → una fracción con `IdCentroCosto` = "Adm. General", `IdLote/IdCultivo/IdCampania/EsGanaderia = NULL` (FR-005)
- [X] T014 [P] [US1] Test `backend/tests/test_imputacion_motor.py::test_compra_fuera_de_alcance_no_genera_propuesta`: una compra sin vínculo `tblRemitoCompra`/remito (repuestos, combustible, administrativas) no genera ninguna propuesta al consultarla en este módulo (FR-014, User Story 1 Acceptance Scenario 4)

### Implementation for User Story 1

- [X] T015 [US1] Implementar `backend/src/features/imputacion/motor.py::calcular_propuesta_insumo(id_detalle_compra)`: reutiliza `remitos.stock_datos.calcular_stock()` para obtener, por producto, las capas y consumos ya resueltos por FIFO; filtra las capas `R{IdDetalleRemito}` que remontan (vía `tblRemitoCompra`) al `id_detalle_compra` dado; para cada consumo que tomó de esas capas — `items[].capa` — determina el destino: (a) si el consumo es `OT{idOrdenInsumo}` de una Orden con `Ordenes_Trabajo.IdRubro IS NULL` (con cultivo), busca su reparto en `Ordenes_Trabajo_Distrib` (Lote/Cultivo/Campania, proporcional a `CantidadAsignada`); (b) si es `OT{idOrdenInsumo}` de una Orden con `IdRubro IS NOT NULL` (sin cultivo, mantenimiento), imputa a Centro de Costos "Adm. General" con ese Rubro, sin Cultivo/Campaña (FR-005); (c) si es `B{idBajaDetalle}` (`Stock_Bajas_Detalle`/`Stock_Bajas`), usa el `IdRubro`/`IdCentro` de la baja como destino, con `EsGanaderia=1` si ese Centro resuelve a Ganadería (research.md); lo que quedó en capas sin consumir es la fracción "en stock sin consumir". Antes de fijar Cultivo/Campaña por consumo puro, consulta `repository.obtener_referencia(idProducto, esGanaderia)` (T007) y, si existe una referencia más reciente que el cálculo por consumo para ese contexto, la usa como prioridad (FR-008). Devuelve la lista de fracciones (dict con `origen='Insumo'`, `idOrdenTrabajo`, `idLote/idCultivo/idCampania`, `idCentroCosto`, `esGanaderia`, `importe`)
- [X] T016 [US1] Implementar `backend/src/features/imputacion/repository.py::marcar_stock_sin_consumir_aprobada(fracciones)`: la fracción "en stock sin consumir" (sin `idOrdenTrabajo`/`idCultivo`/`idCampania`/`esGanaderia`/`idCentroCosto`) se guarda directo con `Estado='Aprobada'`, `FechaAprobacion=now()` — no requiere aprobación del usuario (FR-002)
- [X] T017 [US1] Implementar endpoint `GET /api/imputacion/propuestas` en `backend/src/features/imputacion/router.py` (query params `idDetalleCompra?`, `estado?`, `origen?`, `page`, `pageSize`, per contracts/api-imputacion.md) — llama a `motor.calcular_propuesta_insumo` si no hay corrida vigente todavía para ese renglón (y el renglón está dentro de alcance, FR-014), o lista la corrida vigente ya guardada
- [X] T018 [US1] Implementar endpoint `GET /api/imputacion/propuestas/{idDetalleCompra}/trazabilidad` en `router.py`: remonta on-demand (sin persistir) capa FIFO → `tblRemitoCompra` → remito, y Orden → `Ordenes_Trabajo_Distrib` (o baja → `Stock_Bajas`), para explicar cada fracción de la propuesta vigente (FR-013)
- [X] T019 [US1] Implementar `frontend/src/app/imputacion/page.tsx`: listado de propuestas (usa `GET /api/imputacion/propuestas`), agrupado por factura, con badge de `Estado`
- [X] T020 [US1] Implementar `frontend/src/components/imputacion/PropuestaCard.tsx`: muestra el reparto de una factura (fracciones con Cultivo/Campaña/importe) y su trazabilidad (remito, orden, distribución) vía `GET .../trazabilidad`

**Checkpoint**: se puede ver, para cualquier factura de insumo con consumo real, el reparto propuesto con su origen — MVP funcional aunque todavía nada se pueda aprobar.

---

## Phase 4: User Story 2 - Aprobar o corregir una propuesta de reclasificación (Priority: P1)

**Goal**: que el usuario apruebe una propuesta (con o sin corrección) para que pase a ser el reparto vigente, y que un cambio posterior dispare una propuesta nueva sin pisar en silencio lo ya aprobado.

**Independent Test**: aprobar una propuesta y verificar que deja de listarse como pendiente; anular la Orden que la consumía y verificar que aparece una propuesta nueva pendiente con el reparto corregido (quickstart Escenarios 3-4).

### Tests for User Story 2

- [X] T021 [P] [US2] Test `backend/tests/test_imputacion_endpoints.py::test_aprobar_sin_cambios`: aprobar una corrida marca todas sus fracciones `Estado='Aprobada'`, `FechaAprobacion` seteada, y deja de aparecer en `GET /api/imputacion/propuestas?estado=pendiente`
- [X] T022 [P] [US2] Test `backend/tests/test_imputacion_endpoints.py::test_aprobar_con_correccion_actualiza_referencia`: aprobar con `correcciones` reasignando una fracción a otro Cultivo/Campaña guarda esa clasificación en `ImputacionReferencias` para ese producto (verificar con `repository.obtener_referencia`, T007)
- [X] T023 [P] [US2] Test `backend/tests/test_imputacion_endpoints.py::test_cambio_fuente_genera_corrida_nueva_sin_pisar_aprobada`: con una corrida ya `Aprobada`, anular la Orden que la consumía y recalcular → nueva `IdCorrida` en `Estado='Pendiente'` con el reparto completo corregido; la corrida `Aprobada` original sigue intacta hasta que la nueva se apruebe (quickstart Escenario 4)

### Implementation for User Story 2

- [X] T024 [US2] Implementar `backend/src/features/imputacion/repository.py::aprobar_corrida(id_corrida, correcciones=None)`: marca todas las fracciones de esa `IdCorrida` como `Estado='Aprobada'`/`FechaAprobacion=now()`; si `correcciones` trae cambios de `idLote/idCultivo/idCampania/importe` para alguna `idPropuesta`, los aplica antes de marcar aprobada; devuelve 409 (vía excepción de negocio) si `id_corrida` ya no es la vigente para su renglón
- [X] T025 [US2] Implementar `backend/src/features/imputacion/repository.py::actualizar_referencia(id_producto, es_ganaderia, id_cultivo, id_campania)`: UPSERT en `ImputacionReferencias` (lado de escritura del aprendizaje simple, FR-008 — el lado de lectura es T007), llamada desde `aprobar_corrida` cuando hubo corrección manual
- [X] T026 [US2] Implementar endpoint `POST /api/imputacion/propuestas/{idCorrida}/aprobar` en `router.py` (body `AprobarPropuestaIn`, per contracts/api-imputacion.md)
- [X] T027 [US2] Implementar `backend/src/features/imputacion/motor.py::recalcular_si_corresponde(id_detalle_compra)`: vuelve a correr `calcular_propuesta_insumo`/`calcular_propuesta_contratista` (según `Origen` de la última corrida) y guarda una corrida nueva (`guardar_corrida`) en `Estado='Pendiente'` sin tocar la corrida `Aprobada` anterior (función pura, sin tocar otros módulos — FR-011/FR-012)
- [X] T028 [US2] Integrar la llamada a `recalcular_si_corresponde` en `backend/src/features/ordenes/repository.py::anular_orden` (o el nombre real de la función que marca `Estado='Anulada'`): tras anular, recorre los `IdDetalleCompra` cuyas propuestas vigentes dependían de esa Orden (insumo vía `Ordenes_Trabajo_Distrib`/consumo FIFO, o contratista vía `OrdenesContratistaFacturas`) y dispara el recálculo para cada uno
- [X] T029 [US2] Integrar la llamada a `recalcular_si_corresponde` en `backend/src/features/remitos/repository.py` (en `vincular_renglones`/donde se recarga o revincula un remito contra `tblRemitoCompra`): tras el cambio, dispara el recálculo para los `IdDetalleCompra` afectados
- [X] T030 [US2] Integrar la llamada a `recalcular_si_corresponde` en `backend/src/features/ordenes/repository.py` (donde se guarda/corrige `Ordenes_Trabajo_Distrib`, ej. al editar una Orden `Planificada`): tras el cambio, dispara el recálculo para los `IdDetalleCompra` cuyo consumo pasa por esa distribución
- [X] T031 [US2] Implementar endpoint `POST /api/imputacion/recalcular` en `router.py` (body `{idDetalleCompra?, idOrdenTrabajo?}`) para disparar manualmente `recalcular_si_corresponde`, uso principal: resolver un caso `RequiereIntervencion` después de corregir su causa
- [X] T032 [US2] Agregar en `frontend/src/components/imputacion/PropuestaCard.tsx` el botón "Aprobar" (sin cambios) y el modo de edición inline para corregir una fracción antes de aprobar (`POST .../aprobar` con `correcciones`)

**Checkpoint**: el flujo completo de insumos (Historias 1 y 2) funciona de punta a punta — es el MVP entregable.

---

## Phase 5: User Story 3 - Resolver una inconsistencia grande (Priority: P2)

**Goal**: señalar como "requiere intervención manual" los casos donde el motor no puede proponer un reparto confiable, en vez de proponer algo silenciosamente incorrecto.

**Independent Test**: una factura de contratista sin ninguna Orden vinculada queda marcada `RequiereIntervencion` en vez de generar una propuesta (quickstart Escenario 5).

### Tests for User Story 3

- [X] T033 [P] [US3] Test `backend/tests/test_imputacion_motor.py::test_contratista_sin_orden_requiere_intervencion`: factura de contratista sin filas en `OrdenesContratistaFacturas` → `Estado='RequiereIntervencion'`, sin fracciones de reparto calculadas
- [X] T034 [P] [US3] Test `backend/tests/test_imputacion_motor.py::test_diferencia_grande_requiere_intervencion`: suma repartida entre Órdenes vs. total de la factura con diferencia mayor al umbral (`UMBRAL_INCONSISTENCIA_PORCENTAJE=0.05` o `UMBRAL_INCONSISTENCIA_MONTO_MINIMO=$10.000`, research.md) → `Estado='RequiereIntervencion'`; con diferencia menor al umbral → se tolera y genera la propuesta normal

### Implementation for User Story 3

- [X] T035 [US3] En `backend/src/features/imputacion/motor.py`, agregar las constantes `UMBRAL_INCONSISTENCIA_PORCENTAJE = 0.05` y `UMBRAL_INCONSISTENCIA_MONTO_MINIMO = 10_000` (research.md) y la función `evaluar_inconsistencia(total_factura, total_repartido) -> bool` (compara contra ambos umbrales)
- [X] T036 [US3] Implementar `backend/src/features/imputacion/repository.py::guardar_requiere_intervencion(origen, id_detalle_compra, motivo)`: guarda una corrida de una sola fila especial `Estado='RequiereIntervencion'` con el motivo (`sinOrdenVinculada` | `repartoNoCierra`) — sin fracciones de reparto
- [X] T037 [US3] Implementar endpoint `GET /api/imputacion/pendientes-intervencion` en `router.py` (query `page`, `pageSize`) — lista las corridas vigentes en `Estado='RequiereIntervencion'` con su motivo y el detalle de la factura
- [X] T038 [P] [US3] Implementar `frontend/src/app/imputacion/page.tsx`: sección/filtro "Requiere intervención" que lista estos casos con el motivo visible

**Checkpoint**: los casos límite quedan visibles en vez de generar reclasificaciones silenciosamente incorrectas.

---

## Phase 6: User Story 4 - Vincular una factura de contratista a varias Órdenes de Trabajo (Priority: P2)

**Goal**: generalizar el vínculo factura de contratista↔Orden, hoy 1 a 1, a N a N, y calcular la propuesta de reparto de facturas de contratista.

**Independent Test**: vincular una misma factura a dos Órdenes distintas sin el bloqueo actual, y ver el costo repartido entre los Cultivo/Campaña de ambas (quickstart Escenario 6).

### Tests for User Story 4

- [X] T039 [P] [US4] Test `backend/tests/test_ordenes_contratista_factura.py::test_vincular_misma_factura_a_dos_ordenes`: `vincular_factura_contratista` ya no lanza error si la Orden (u otra Orden) ya tiene esa u otra factura vinculada — ambos vínculos quedan en `OrdenesContratistaFacturas`
- [X] T040 [P] [US4] Test `backend/tests/test_ordenes_contratista_factura.py::test_desvincular_factura_puntual`: `DELETE /api/ordenes/{idOrden}/factura-contratista/{idCompra}` quita solo ese vínculo, sin afectar otros
- [X] T041 [P] [US4] Test `backend/tests/test_imputacion_motor.py::test_propuesta_contratista_prorratea_entre_ordenes`: factura de contratista vinculada a dos Órdenes de distinto Cultivo/Campaña → fracciones prorrateadas por superficie de cada Orden (reusando `ordenes.costeo.prorratear_por_superficie`)
- [X] T042 [P] [US4] Test `backend/tests/test_imputacion_motor.py::test_propuesta_contratista_orden_sin_cultivo`: factura de contratista vinculada a una Orden con `IdRubro IS NOT NULL` (sin cultivo) → fracción imputada a Centro de Costos "Adm. General" con ese Rubro (FR-005, mismo criterio que insumos)

### Implementation for User Story 4

- [X] T043 [US4] Modificar `backend/src/features/ordenes/repository.py::vincular_factura_contratista(id_orden, id_compra)`: quitar el chequeo que bloquea si `orden["facturaContratista"] is not None`; INSERT en `dbo.OrdenesContratistaFacturas` en vez de `dbo.Ordenes_Trabajo_Contratista_Factura`
- [X] T044 [US4] Implementar `backend/src/features/ordenes/repository.py::desvincular_factura_contratista(id_orden, id_compra)` — DELETE de la fila puntual en `OrdenesContratistaFacturas`
- [X] T045 [US4] Agregar endpoint `DELETE /api/ordenes/{idOrden}/factura-contratista/{idCompra}` en `backend/src/features/ordenes/router.py`; mantener `POST /api/ordenes/{idOrden}/factura-contratista` para que acepte múltiples llamadas sin bloquear
- [X] T046 [US4] Actualizar `backend/src/features/ordenes/costeo.py::costo_contratista` y `backend/src/features/ordenes/resultado.py::_filas_maquinaria_y_contratista` para leer de `dbo.OrdenesContratistaFacturas` en vez de `dbo.Ordenes_Trabajo_Contratista_Factura` (mismas columnas, sin cambio de forma de los datos que consumen)
- [X] T047 [US4] Implementar `backend/src/features/imputacion/motor.py::calcular_propuesta_contratista(id_compra)`: lee todas las Órdenes vinculadas en `OrdenesContratistaFacturas`; si no hay ninguna → `evaluar_inconsistencia` dispara `RequiereIntervencion` (motivo `sinOrdenVinculada`, US3); si hay, separa las Órdenes con `IdRubro IS NULL` (con cultivo, prorratea por superficie entre sus Cultivo/Campaña, reutilizando `ordenes.costeo.prorratear_por_superficie`) de las con `IdRubro IS NOT NULL` (imputa a Centro de Costos "Adm. General" con ese Rubro, FR-005); evalúa `evaluar_inconsistencia` contra la suma repartida total (motivo `repartoNoCierra` si no cierra)
- [X] T048 [US4] Extender `GET /api/imputacion/propuestas` (`router.py`) para incluir `origen=Contratista`, llamando a `motor.calcular_propuesta_contratista` cuando corresponda
- [X] T049 [P] [US4] Actualizar `frontend/src/app/produccion/ordenes/[idOrden]` (o el componente que ya vincula factura de contratista, spec 011) para permitir vincular/desvincular varias facturas por Orden, en vez de una sola

**Checkpoint**: el flujo completo de contratistas (Historias 3 y 4) funciona de punta a punta, junto con el de insumos (Historias 1-2).

---

## Phase 7: User Story 5 - Comparar el motor nuevo contra el motor de costeo heredado (Priority: P2)

**Goal**: mostrar, para un Cultivo/Campaña, el costo total según el motor heredado (012) junto al costo total de las propuestas aprobadas del motor nuevo, con su diferencia.

**Independent Test**: pedir la comparación de una Cultivo/Campaña histórica y ver ambos totales con la diferencia, sin que el motor heredado cambie de valor (quickstart Escenario 7).

### Tests for User Story 5

- [X] T050 [P] [US5] Test `backend/tests/test_imputacion_comparacion.py::test_comparacion_completa`: Cultivo/Campaña con todas sus propuestas `Aprobada` → `comparacionParcial=false`, `costoNuevo.totalAprobado` = suma de esas fracciones
- [X] T051 [P] [US5] Test `backend/tests/test_imputacion_comparacion.py::test_comparacion_parcial`: Cultivo/Campaña con alguna propuesta `Pendiente`/`RequiereIntervencion` → `comparacionParcial=true`
- [X] T052 [P] [US5] Test `backend/tests/test_imputacion_comparacion.py::test_no_altera_motor_heredado`: correr la comparación no modifica ningún valor de `vw_ResultadoCultivo_Campaña` ni el resultado de `ordenes.resultado.costo_por_cultivo_campania` (SC-005) — se verifica comparando el resultado de esa función antes y después de correr el motor nuevo

### Implementation for User Story 5

- [X] T053 [US5] Implementar `backend/src/features/imputacion/repository.py::costo_aprobado_por_campania(id_campania)`: suma `Importe` de fracciones `Estado='Aprobada'` en `ImputacionPropuestas` agrupadas por `IdCampania`, y cuenta cuántas fracciones de esa campaña siguen `Pendiente`/`RequiereIntervencion`
- [X] T054 [US5] Implementar endpoint `GET /api/imputacion/comparacion` en `router.py` (query `idCampania` requerido): junta `ordenes.resultado.resumen_campania_heredado(id_campania)` (012, sin modificar) con `costo_aprobado_por_campania`, calcula `diferenciaPesos`/`diferenciaPorcentual`/`comparacionParcial`
- [X] T055 [P] [US5] Implementar `frontend/src/app/imputacion/comparacion/page.tsx` y `frontend/src/components/imputacion/ComparacionCultivoCampania.tsx`: selector de Cultivo/Campaña + tabla lado a lado (costo heredado vs. nuevo) con la diferencia

**Checkpoint**: las 5 historias de usuario funcionan de punta a punta.

---

## Phase 8: Polish

- [X] T056 [P] Ejecutar los 7 escenarios de `quickstart.md` de punta a punta contra `WC` — probado con datos reales (factura 2141365940/orden 14/campaña 3: propuesta calculada, trazabilidad, aprobación); pendientes-intervencion y comparación probados sin datos suficientes para los otros escenarios (WC no tiene facturas de contratista vinculadas todavía) — bug real encontrado y corregido: `comparacionParcial` no detectaba `totalPendiente` negativo (notas de crédito)
- [X] T057 Ejecutar la suite completa de backend y `tsc --noEmit`; confirmar que ningún test ni endpoint existente de Compras/Remitos/Órdenes/Resultado (006/010/011/012) cambió de comportamiento
- [X] T058 Confirmar SC-005: comparar `vw_ResultadoCultivo_Campaña` y `ordenes.resultado.costo_por_cultivo_campania()` antes/después de tener este módulo activo — deben devolver exactamente los mismos valores

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Fase 1)**: sin dependencias.
- **Foundational (Fase 2)**: depende de Setup — bloquea todas las historias. Incluye tanto el lado de escritura como el de lectura de `ImputacionReferencias` (T007), porque ambos motores (US1 y US4) lo consultan desde su primera versión.
- **User Story 1 (Fase 3, P1)**: depende de Foundational. Es la base del MVP.
- **User Story 2 (Fase 4, P1)**: depende de Foundational y de que User Story 1 exista (aprueba propuestas que US1 genera) — juntas forman el MVP (insumos de punta a punta).
- **User Story 3 (Fase 5, P2)**: depende de Foundational; usa las mismas primitivas de `repository.py` que US1/US2 pero es independiente de ellas en su propio flujo (contratistas).
- **User Story 4 (Fase 6, P2)**: depende de Foundational (tabla `OrdenesContratistaFacturas` ya migrada); usa `evaluar_inconsistencia` de US3.
- **User Story 5 (Fase 7, P2)**: depende de que existan propuestas `Aprobada` (US2) para tener algo que comparar — funcionalmente independiente en su propio endpoint, pero sin datos de US1/US2 no hay nada que mostrar.
- **Polish (Fase 8)**: depende de todas las historias que se quieran entregar.

### Oportunidades de paralelismo

- Todas las tareas `[P]` dentro de una misma fase pueden correr en paralelo (archivos distintos, sin dependencias entre sí).
- Los tests de una historia (`[P]`) pueden escribirse en paralelo entre sí, antes de la implementación.
- User Story 3 y User Story 4 pueden desarrollarse en paralelo por personas distintas una vez completa la Fase 2 (ambas dependen de Foundational, no una de la otra, salvo por la constante `evaluar_inconsistencia` que puede definirse primero en US3 y reusarse).
- T028, T029 y T030 (integración de `recalcular_si_corresponde` en tres archivos distintos) pueden hacerse en paralelo entre sí una vez que T027 (la función pura) está lista.

## Implementation Strategy

### MVP primero (User Stories 1 + 2)

1. Fase 1: Setup
2. Fase 2: Foundational (bloqueante)
3. Fase 3: User Story 1 (ver propuesta de insumo)
4. Fase 4: User Story 2 (aprobar/corregir)
5. **Parar y validar**: correr los Escenarios 1-4 de quickstart.md contra datos reales de `WC`
6. Este es el MVP entregable: flujo completo de insumos, sin contratistas ni comparación todavía

### Entrega incremental

1. Setup + Foundational → base lista
2. US1 + US2 → MVP de insumos, demostrable
3. US3 + US4 → completa el flujo de contratistas (pueden ir en paralelo)
4. US5 → habilita la validación/benchmark contra el motor heredado, cierre de esta iteración
5. Cada historia agrega valor sin romper las anteriores (ninguna toca `Det_Compras`, `Remitos_*`, `Ordenes_Trabajo_*` fuera de lo explícito en US4, ni las vistas heredadas de 012)

## Notas de la revisión `/speckit-analyze` (2026-09-23)

Antes de implementar T015/T047 (motor.py), confirmar con el usuario el mecanismo de "consumo ganadero" documentado en research.md (Decisión: reutiliza `Stock_Bajas`) — no fue verificado explícitamente en la sesión de clarificación original, solo el resultado esperado (reparto Agricultura/Ganadería).

## Corrección de rendimiento — 2026-09-24

- [X] PERF01 Liberar el event loop de las llamadas síncronas de imputación, preservar el lock de corridas y validar concurrencia (25 pruebas focalizadas exitosas).
- [X] PERF02 Preparar arranque compilado, conservar modo Dev y evitar cierre forzado por sondeos fallidos; build, lint y TypeScript exitosos.
- [X] PERF03 Escuchar localhost IPv4/IPv6 y medir arranque, entrega de páginas y lectura de documentos WC; evidencia en docs/auditoria-rendimiento-2026-09-24.md.
