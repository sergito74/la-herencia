---

description: "Task list for Órdenes de Trabajo (011)"
---

# Tasks: Órdenes de Trabajo

**Input**: Design documents from `/specs/011-ordenes-trabajo/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api-ordenes.md, quickstart.md

**Tests**: No se pidieron tests exhaustivos en la spec; se incluyen únicamente los tests focalizados que ya son el estándar del proyecto (constitución, Principio V): validación de FIFO/cierre exacto y de la API, replicando el patrón de `backend/tests/test_remitos_api.py` y `test_stock_fifo.py` de 010-remitos.

**Organization**: Tareas agrupadas por historia de usuario (spec.md). US1 es la base funcional (crear/planificar una orden) de la que dependen operativamente US2-US6, tal como ya ocurre en el dominio real (no se puede devolver, costear maquinaria/contratista o sumar al resultado de una campaña sin que la orden exista primero); aun así cada fase agrega una capacidad demostrable e independientemente verificable sobre esa base.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Puede ejecutarse en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: US1–US7, mapeadas 1:1 a las historias de `spec.md`
- Rutas de archivo según `plan.md` → Project Structure

## Path Conventions

Web app existente: `backend/src/features/ordenes/`, `backend/scripts/`, `backend/tests/`, `frontend/src/app/produccion/ordenes/`, `frontend/src/components/ordenes/`, `frontend/src/services/`.

---

## Phase 1: Setup

**Purpose**: Estructura base del módulo, sin lógica de negocio todavía.

- [X] T001 Crear el paquete `backend/src/features/ordenes/` con `__init__.py` vacío, siguiendo la estructura de `backend/src/features/remitos/`
- [X] T002 [P] Crear `frontend/src/app/produccion/ordenes/` (carpeta vacía con `page.tsx` placeholder) y `frontend/src/components/ordenes/` per `plan.md` → Project Structure
- [X] T003 [P] Crear `frontend/src/services/ordenesApi.ts` con el cliente base (fetch/TanStack Query wrapper), siguiendo el patrón de `frontend/src/services/remitosApi.ts`

**Checkpoint**: estructura de carpetas lista, sin funcionalidad.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Esquema de datos en `WC` y el andamiaje del que dependen todas las historias. Ninguna historia puede implementarse hasta que esta fase esté completa.

**⚠️ CRITICAL**: Solo lectura contra `WC` hasta backup verificado y autorización explícita (Constitución, Principio II); los scripts de creación de tablas son idempotentes y no tocan tablas heredadas.

- [X] T004 Crear `backend/scripts/crear_tablas_ordenes.py` (idempotente, mismo patrón que `crear_tablas_remitos.py`) con las 7 tablas nuevas de `data-model.md`: `Ordenes_Trabajo`, `Ordenes_Trabajo_Insumos`, `Ordenes_Trabajo_Distrib`, `Ordenes_Trabajo_Devoluciones`, `Ordenes_Trabajo_Maquinaria`, `Ordenes_Trabajo_Contratista_Factura`, `Formularios_Retiro`, con las columnas y tipos exactos de `data-model.md` (ej. `Ordenes_Trabajo.Estado` como `varchar` con valores permitidos `Planificada | Ejecutada | Anulada`; `Ordenes_Trabajo_Distrib.DosisHa`/`Superficie`/`CantidadAsignada` como `decimal(18,4)`)
- [X] T005 [P] Crear `backend/scripts/indices_ordenes.py` (idempotente, como `indices_remitos.py`): PK identity en las 7 tablas nuevas, índice único `(IdOrdenTrabajo)` en `Formularios_Retiro` (relación 1 a 1, ver `data-model.md`), e índices de soporte en `Ordenes_Trabajo_Insumos.IdOrdenTrabajo` y `Ordenes_Trabajo_Distrib.IdOrdenInsumo`
- [X] T006 Crear `backend/src/features/ordenes/schemas.py` con los modelos Pydantic: `DistribIn` (idLote, idCultivo, idCampania, dosisHa, superficie, aplicar), `RenglonInsumoIn` (idProducto, unidad, distribuciones: list[DistribIn] con `min_length=1`), `OrdenIn` (fecha, idTipoLabor, idContratistaContacto opcional, renglones: list[RenglonInsumoIn] con `min_length=1`, confirmar: bool=False), `DevolucionIn` (fecha, cantidad, observaciones opcional), `MaquinariaIn` (descripcion, costoPorHectarea, tipoCambioBna opcional), `FacturaContratistaIn` (idCompra), `AnularIn` (motivo), `TipoLaborIn` (nombre) — siguiendo el estilo de `backend/src/features/remitos/schemas.py`
- [X] T007 Crear `backend/src/features/ordenes/repository.py` con la conexión a `WC` reutilizando `backend/src/db/connection.py` (misma conexión que Remitos, nunca `LaHerencia`) y las funciones base de lectura de catálogos: `listar_lotes()`, `listar_cultivos()`, `listar_campanias()`, `listar_tipos_labor()`, `listar_contratistas()` (Contactos con `EsContratistaLabores = 1`)
- [X] T008 [P] Crear `backend/src/features/ordenes/router.py` con el `APIRouter(prefix="/api/ordenes", tags=["ordenes"])` vacío y el helper `_ejecutar` (errores de negocio → 400, `RequiereConfirmacion` → 409), copiando el patrón de `backend/src/features/remitos/router.py`
- [X] T009 Registrar `ordenes_router` en `backend/src/main.py` (import + `app.include_router(ordenes_router)`, junto a `remitos_router`)
- [X] T010 [P] Agregar "Órdenes de Trabajo" como cuarto ítem del submenú Producción en `frontend/src/components/layout/NavHeader.tsx` (junto a Remitos y Stock)

**Checkpoint**: esquema de `WC` creado, backend arrancando con el router vacío registrado, nav actualizado. Las historias de usuario pueden empezar.

---

## Phase 3: User Story 1 - Planificar y registrar una Orden de Trabajo (Priority: P1) 🎯 MVP

**Goal**: Un usuario planifica una orden con lotes de distintos cultivos/campañas, dosis/ha por lote, el sistema calcula el total a retirar por insumo, descuenta stock por FIFO y emite el Formulario de Retiro.

**Independent Test**: Ejecutar el Escenario 1 de `quickstart.md` — crear una orden multi-lote/multi-campaña y verificar que `CantidadTotal` cierra contra la suma de distribuciones, que el stock bajó lo esperado, y que se generó un Formulario de Retiro con numeración propia.

### Implementation for User Story 1

- [X] T011 [P] [US1] Crear `backend/src/features/ordenes/distribucion.py` con `calcular_cantidad_total(distribuciones: list[DistribIn]) -> float`, que suma `dosisHa * superficie` de cada distribución con `aplicar=True` (regla FR-003), y `validar_cierre(cantidad_total, distribuciones, devoluciones=[])`, que implementa la regla de integridad FR-004 de `data-model.md` (`sum(CantidadAsignada donde Aplicar=1) + sum(Devoluciones.Cantidad) == CantidadTotal`), lanzando `ValueError` con mensaje de negocio claro si no cierra
- [X] T012 [US1] Implementar `backend/src/features/ordenes/repository.py::crear_orden(datos: OrdenIn)` que: valida el cierre de cada renglón con `distribucion.validar_cierre`, descuenta stock por FIFO reutilizando `backend/src/features/remitos/stock_fifo.py` y `stock_datos.py` (importados, no duplicados — decisión de `research.md` §1), lanza `RequiereConfirmacion` si el consumo supera el stock disponible y `datos.confirmar` es `False` (mismo patrón que `remitos.repository`), inserta la cabecera en `Ordenes_Trabajo` con `Estado='Planificada'`, los renglones en `Ordenes_Trabajo_Insumos` y las distribuciones en `Ordenes_Trabajo_Distrib`
- [X] T013 [US1] Implementar `backend/src/features/ordenes/formulario_retiro.py::generar(idOrden: int) -> dict` que inserta una fila en `Formularios_Retiro` (numeración identity secuencial propia, FR-008) y devuelve el listado de insumos a preparar de esa orden
- [X] T014 [US1] Extender `crear_orden` en `repository.py` para invocar `formulario_retiro.generar()` al confirmar la orden y devolver su número en la respuesta
- [X] T015 [US1] Implementar `backend/src/features/ordenes/repository.py::listar_ordenes(idContratista, idLote, idCultivo, idCampania, fechaDesde, fechaHasta, estado, page, pageSize)` y `obtener_orden(idOrden)` con el detalle completo (cabecera + renglones + distribuciones), siguiendo el estilo de `remitos.repository.listar_remitos`
- [X] T016 [US1] Implementar `backend/src/features/ordenes/repository.py::editar_orden(idOrden, datos: OrdenIn)` — edición libre solo si `Estado='Planificada'` y sin devoluciones ni factura de contratista vinculada (FR-007); si no cumple, `ValueError` con mensaje claro
- [X] T017 [US1] Implementar `backend/src/features/ordenes/repository.py::ejecutar_orden(idOrden, fechaEjecucion)` — transición `Planificada → Ejecutada` (data-model.md → Estados y transiciones)
- [X] T018 [US1] Implementar `backend/src/features/ordenes/repository.py::anular_orden(idOrden, motivo)` — transición a `Anulada`, devuelve al stock las capas FIFO consumidas por la orden (reutilizando la lógica de anulación ya validada en `remitos.repository`, recalcula en vez de bloquear)
- [X] T019 [US1] Agregar a `backend/src/features/ordenes/router.py` los endpoints `POST /api/ordenes`, `GET /api/ordenes`, `GET /api/ordenes/{idOrden}`, `PATCH /api/ordenes/{idOrden}`, `POST /api/ordenes/{idOrden}/ejecutar`, `POST /api/ordenes/{idOrden}/anular`, según `contracts/api-ordenes.md` → "Cabecera de orden"
- [X] T020 [P] [US1] Test `backend/tests/test_ordenes_distribucion.py`: casos de `validar_cierre` (cierra exacto, no cierra sin devolución, cierra con devolución, lote con `aplicar=False` no suma), siguiendo el estilo de `test_stock_fifo.py`
- [X] T021 [P] [US1] Test `backend/tests/test_ordenes_api.py`: crear orden multi-lote/multi-campaña, verificar 409 por stock insuficiente sin confirmar y 201 al confirmar, siguiendo el estilo de `test_remitos_api.py`
- [X] T067 [P] [US1] Test `backend/tests/test_ordenes_api.py`: anular una orden `Planificada` devuelve exactamente las capas FIFO que había consumido, verificado comparando el saldo de existencias antes de crear la orden, después de crearla, y después de anularla (cubre SC-004; hallazgo G1 de `/speckit-analyze`)
- [X] T022 [P] [US1] Crear `frontend/src/components/ordenes/DistribucionLotesPanel.tsx`: selección de lotes (con su cultivo/campaña), carga de dosis/ha por lote, cálculo en vivo de la cantidad total del insumo
- [X] T023 [US1] Crear `frontend/src/components/ordenes/OrdenForm.tsx`: cabecera (fecha, tipo de labor, contratista opcional), renglones de insumo con `DistribucionLotesPanel` embebido por renglón, envío a `POST /api/ordenes` (depende de T022)
- [X] T024 [P] [US1] Crear `frontend/src/components/ordenes/EstadosOrden.tsx`: badge de estado (Planificada/Ejecutada/Anulada), siguiendo el patrón de `frontend/src/components/remitos/EstadosRemito.tsx`
- [X] T025 [P] [US1] Crear `frontend/src/components/ordenes/OrdenesListado.tsx`: listado con filtros (contratista, lote, cultivo, campaña, fecha, estado) y paginación
- [X] T026 [P] [US1] Crear `frontend/src/components/ordenes/FormularioRetiroView.tsx`: vista del Formulario de Retiro con su número secuencial y el listado de insumos a preparar
- [X] T027 [US1] Crear páginas `frontend/src/app/produccion/ordenes/page.tsx` (listado), `frontend/src/app/produccion/ordenes/nuevo/page.tsx` (alta), `frontend/src/app/produccion/ordenes/[idOrden]/page.tsx` (detalle + Formulario de Retiro), `frontend/src/app/produccion/ordenes/[idOrden]/editar/page.tsx` (edición), consumiendo `ordenesApi.ts`
- [X] T028 [US1] Extender `frontend/src/services/ordenesApi.ts` con `crearOrden`, `listarOrdenes`, `obtenerOrden`, `editarOrden`, `ejecutarOrden`, `anularOrden`, tipados según `contracts/api-ordenes.md`

**Checkpoint**: US1 funcional de punta a punta — se puede planificar, listar, editar, ejecutar y anular una orden, con Formulario de Retiro y descuento de stock FIFO. MVP demostrable.

---

## Phase 4: User Story 2 - Devoluciones de insumo (Priority: P1)

**Goal**: Registrar la devolución de insumo no utilizado, reingresarlo al stock y mantener el cierre exacto del renglón.

**Independent Test**: Escenario 2 de `quickstart.md` — devolución parcial sobre una orden de US1, rechazo de una devolución mayor a lo retirado, verificación de que el cierre sigue exacto.

### Implementation for User Story 2

- [X] T029 [US2] Implementar `backend/src/features/ordenes/repository.py::registrar_devolucion(idOrdenInsumo, datos: DevolucionIn)`: valida que `cantidad` no supere lo retirado y no devuelto de ese renglón (regla de `data-model.md` → `Ordenes_Trabajo_Devoluciones`), inserta en `Ordenes_Trabajo_Devoluciones`, reingresa esa cantidad al stock como nueva capa FIFO (reutilizando `remitos.stock_fifo`, mismo mecanismo que una entrada de remito) y re-ejecuta `distribucion.validar_cierre` sobre el renglón
- [X] T030 [US2] Agregar a `router.py` el endpoint `POST /api/ordenes/{idOrden}/insumos/{idOrdenInsumo}/devoluciones` según `contracts/api-ordenes.md`
- [X] T031 [P] [US2] Test en `backend/tests/test_ordenes_api.py`: devolución válida reingresa stock, devolución mayor a lo retirado se rechaza
- [X] T032 [US2] Crear `frontend/src/components/ordenes/DevolucionPanel.tsx`: formulario de devolución por renglón de insumo, integrado en la vista de detalle de la orden (`[idOrden]/page.tsx`)
- [X] T033 [US2] Extender `ordenesApi.ts` con `registrarDevolucion`

**Checkpoint**: US1 + US2 funcionan juntas — una orden puede tener devoluciones que ajustan su cierre y el stock.

---

## Phase 5: User Story 3 - Costeo de maquinaria propia (Priority: P1)

**Goal**: Registrar el uso de maquinaria propia en una orden con su costo por hectárea cargado a mano, prorrateado entre los lotes de la orden.

**Independent Test**: Escenario 3 (parte 1) de `quickstart.md` — agregar un renglón de maquinaria propia a una orden de US1 y verificar el prorrateo por superficie entre sus lotes.

### Implementation for User Story 3

- [X] T034 [P] [US3] Crear `backend/src/features/ordenes/costeo.py` con `costo_maquinaria(idOrden, descripcion, costoPorHectarea, tipoCambioBna=None) -> dict`: prorratea `costoPorHectarea` entre los lotes de la orden por superficie (mismo criterio de prorrateo que un insumo, `data-model.md` → `Ordenes_Trabajo_Maquinaria`), sin tabla de tarifas persistente (decisión de `research.md` §4)
- [X] T035 [US3] Implementar `backend/src/features/ordenes/repository.py::agregar_maquinaria(idOrden, datos: MaquinariaIn)`: inserta en `Ordenes_Trabajo_Maquinaria` y aplica `costeo.costo_maquinaria`
- [X] T036 [US3] Agregar a `router.py` el endpoint `POST /api/ordenes/{idOrden}/maquinaria` según `contracts/api-ordenes.md`
- [X] T037 [P] [US3] Test en `backend/tests/test_ordenes_api.py`: costo de maquinaria se prorratea correctamente entre 2+ lotes de superficies distintas
- [X] T038 [US3] Agregar el bloque de maquinaria propia a la vista de detalle `frontend/src/app/produccion/ordenes/[idOrden]/page.tsx` (no a `OrdenForm.tsx`: maquinaria y factura de contratista se cargan después de crear la orden, igual que la factura de US4): campo de descripción, costo por hectárea y TC opcional
- [X] T039 [US3] Extender `ordenesApi.ts` con `agregarMaquinaria`

**Checkpoint**: una orden puede tener maquinaria propia costeada y prorrateada, independiente de si tiene o no contratista.

---

## Phase 6: User Story 4 - Contratistas y su factura (Priority: P1)

**Goal**: Vincular la factura de Compras de un contratista a la orden, con su costo imputado y dolarizado al TC de esa factura.

**Independent Test**: Escenario 3 (parte 2) de `quickstart.md` — vincular una factura de contratista a una orden y verificar que el costo se prorratea entre lotes y se expresa en pesos y dólares.

### Implementation for User Story 4

- [X] T040 [US4] Implementar `backend/src/features/ordenes/costeo.py::costo_contratista(idOrden, idCompra) -> dict`: lee `Compras.tipoDeCambio` de la factura vinculada (mismo mecanismo ya usado en `remitos/costeo.py` líneas 62-73 para facturas en dólares, confirmado en `research.md` §5) y prorratea el importe entre los lotes de la orden por superficie
- [X] T041 [US4] Implementar `backend/src/features/ordenes/repository.py::vincular_factura_contratista(idOrden, datos: FacturaContratistaIn)`: inserta en `Ordenes_Trabajo_Contratista_Factura` (FK única por orden, `data-model.md`)
- [X] T042 [US4] Agregar a `router.py` el endpoint `POST /api/ordenes/{idOrden}/factura` según `contracts/api-ordenes.md`
- [X] T043 [P] [US4] Test en `backend/tests/test_ordenes_api.py`: costo de contratista se dolariza con el TC de la factura vinculada y se prorratea por superficie
- [X] T044 [US4] Agregar selector de factura de contratista (buscador de compras del proveedor/contratista, reutilizando el patrón de `VinculacionPanel.tsx` de Remitos) a la vista de detalle de la orden
- [X] T045 [US4] Extender `ordenesApi.ts` con `vincularFacturaContratista`

**Checkpoint**: una orden puede tener insumo + maquinaria + contratista simultáneamente, cada costo visible en pesos y dólares (Escenario 3 completo).

---

## Phase 7: User Story 6 - Costo y resultado por Cultivo/Campaña (Priority: P1)

**Goal**: Consultar el costo total acumulado (insumos + maquinaria + contratistas) de un Cultivo/Campaña, conectado con el motor de costeo heredado, sin fecha de cierre.

**Independent Test**: Escenario 5 de `quickstart.md` — consultar el costo de una campaña ya cosechada, agregar una orden nueva de esa campaña y verificar que el costo se actualiza sin ningún paso de reapertura.

### Implementation for User Story 6

- [X] T046 [US6] Crear `backend/src/features/ordenes/resultado.py::costo_por_cultivo_campania(idCultivo=None, idCampania=None, idLote=None) -> list[dict]`: suma el costo de insumos (FIFO), maquinaria y contratistas de `Ordenes_Trabajo_*` agrupado por Cultivo/Campaña/Lote, y lo combina con las vistas heredadas `vw_ResultadoCultivo_Campaña`, `vw_Costos_BaseLineas`, `vw_ResultadosCultivo_CostosBase/CostosAgrupados` (solo lectura, sin modificarlas — `research.md` §2), sin ningún filtro de fecha de cierre (FR-015)
- [X] T047 [US6] Antes de usar `vw_Cns_TotalesOrdenesPorProducto`, verificar con una consulta de solo lectura su convención de signo (riesgo identificado en `research.md` §2); si no es confiable, calcular el consumo directamente desde `Ordenes_Trabajo_Insumos` en vez de esa vista
- [X] T048 [US6] Agregar a `router.py` los endpoints `GET /api/ordenes/resultado-cultivo` y `GET /api/ordenes/resultado-cultivo/exportar` según `contracts/api-ordenes.md`
- [X] T049 [P] [US6] Crear `backend/src/features/ordenes/exportacion.py::exportar_resultado_cultivo(filtros) -> bytes` (Excel), siguiendo el patrón de `backend/src/features/remitos/exportacion.py`
- [X] T050 [P] [US6] Test en `backend/tests/test_ordenes_api.py`: el costo de una campaña con fecha de cosecha pasada se sigue actualizando al agregar una orden nueva de esa campaña, sin ningún endpoint de "reapertura"
- [X] T051 [US6] Crear `frontend/src/components/ordenes/ResultadoCultivoListado.tsx`: tabla filtrable por Cultivo/Campaña/Lote con el costo total en pesos y dólares, y botón de exportar a Excel
- [X] T052 [US6] Crear `frontend/src/app/produccion/ordenes/resultado-cultivo/page.tsx`
- [X] T053 [US6] Extender `ordenesApi.ts` con `obtenerResultadoCultivo` y `exportarResultadoCultivo`

**Checkpoint**: el objetivo central del módulo (costo por Cultivo/Campaña) es consultable end-to-end.

---

## Phase 8: User Story 5 - Órdenes sin cultivo específico (Priority: P2)

**Goal**: Registrar una orden de mantenimiento general (sin cultivo) imputada a Rubro y Centro de Costos.

**Independent Test**: Crear una orden con `idRubro`/`idCentroCostos` y sin ningún renglón de distribución a Cultivo/Campaña; verificar que no aparece en `resultado-cultivo` (US6) pero sí en el listado general de órdenes (US1).

### Implementation for User Story 5

- [X] T054 [US5] Extender `schemas.py::OrdenIn` con `idRubro: int | None` e `idCentroCostos: int | None`, mutuamente excluyentes con tener renglones de insumo con distribución a Cultivo/Campaña (según FR-016: una orden es o de Cultivo/Campaña o de Rubro/Centro de Costos)
- [X] T055 [US5] Extender `repository.py::crear_orden` para aceptar y persistir `idRubro`/`idCentroCostos` en `Ordenes_Trabajo` cuando la orden no tiene distribución a Cultivo/Campaña
- [X] T056 [P] [US5] Test en `backend/tests/test_ordenes_api.py`: orden sin cultivo con Rubro/Centro de Costos se crea correctamente y queda excluida de `resultado-cultivo`
- [X] T057 [US5] Agregar el selector de Rubro/Centro de Costos a `OrdenForm.tsx`, visible cuando la orden no tiene lotes/cultivo asignado

**Checkpoint**: el sistema cubre tanto labores agrícolas como de mantenimiento general.

---

## Phase 9: User Story 7 - Administración de catálogos abiertos (Priority: P2)

**Goal**: Un administrador agrega un nuevo Tipo de Labor sin tocar código.

**Independent Test**: Dar de alta un Tipo de Labor nuevo (ej. "Cosecha") y verificar que aparece disponible al crear una orden nueva (US1).

### Implementation for User Story 7

- [X] T058 [US7] Implementar `backend/src/features/ordenes/repository.py::crear_tipo_labor(nombre: str)` — `INSERT` de una fila nueva directamente en la tabla heredada `Tipo Labores` (nunca `ALTER` de su estructura), mismo criterio que el alta del rubro "Pérdidas y bajas de insumos" en 010-remitos (ver `data-model.md` → "Alta de nuevos Tipos de Labor")
- [X] T059 [US7] Agregar a `router.py` los endpoints `GET /api/ordenes/tipos-labor` y `POST /api/ordenes/tipos-labor` según `contracts/api-ordenes.md`
- [X] T060 [P] [US7] Crear `frontend/src/components/ordenes/TipoLaborAdmin.tsx`: listado + alta de tipos de labor
- [X] T061 [US7] Extender `ordenesApi.ts` con `listarTiposLabor` y `crearTipoLabor`; usar el listado en el selector de tipo de labor de `OrdenForm.tsx`

**Checkpoint**: el catálogo de labores queda abierto a expansión sin deploy de código.

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Migración de datos heredados y verificación final, después de que el módulo funciona de punta a punta.

- [X] T062 [P] Crear `backend/scripts/migrar_ordenes.py` (idempotente, con modo dry-run como `migrar_remitos.py`): migra las 153 filas de `Ordenes` → `Ordenes_Trabajo` (`Estado='Ejecutada'` si `FechaEjecucion` no es NULL, si no `'Planificada'`), 820 de `Ordenes_Detalles` → `Ordenes_Trabajo_Insumos`, 4.319 de `Ordenes_Detalles_Distrib` → `Ordenes_Trabajo_Distrib` unificando unidades contra `Unidades_Medida`/`Producto_Unidad` (`LTS`/`LITROS`→`LTS`, `KGS`/`KILOS`→`KGS`), usa `IdContratistaContacto` (descarta la columna `Contratista`), excluye el lote `PRUE`, y marca `RevisarMigracion=1` en los 13 renglones donde `Total Aplicado` no cierra contra lo distribuido, según `data-model.md` → "Migración de datos heredados"
- [X] T063 Ejecutar `migrar_ordenes.py` en modo dry-run (solo lectura) y verificar los conteos contra `spec.md` → "Hallazgos de datos reales" (153/820/4.319/879); no ejecutar la migración real sin backup verificado y autorización explícita del usuario
- [X] T064 [P] Aplicar formato numérico y monetario del sistema (miles `.`, decimales `,`, `$`/`us$`, FR-018) en todos los componentes nuevos de `frontend/src/components/ordenes/`, usando los helpers ya existentes (nunca `type=number` ni `toLocaleString`, por la regla de memoria del proyecto)
- [X] T065 [P] Agregar exportación a Excel del listado de órdenes y del Formulario de Retiro en `backend/src/features/ordenes/exportacion.py` (FR-019), completando lo ya creado en T049 para resultado por cultivo
- [X] T066 Ejecutar los 6 escenarios de `quickstart.md` de punta a punta sobre el sistema integrado y confirmar los 4 criterios de éxito de `spec.md` (SC-001 a SC-004)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias
- **Foundational (Phase 2)**: depende de Setup — bloquea todas las historias
- **US1 (Phase 3)**: depende de Foundational; es la base operativa de la que dependen US2-US6 (una orden debe existir antes de devolver, costear maquinaria, vincular factura o sumar al resultado de campaña)
- **US2 (Phase 4)**: depende de US1 (necesita una orden con renglones de insumo)
- **US3 (Phase 5)**: depende de US1; independiente de US2
- **US4 (Phase 6)**: depende de US1; independiente de US2 y US3
- **US6 (Phase 7)**: depende de US1, y se beneficia de US3/US4 completas para un cálculo de costo total completo, pero es consultable con datos parciales (solo insumos) desde que US1 existe
- **US5 (Phase 8)**: depende de Foundational y de T054 en `schemas.py`; independiente de US2-US4/US6
- **US7 (Phase 9)**: depende de Foundational; independiente del resto (el catálogo de labores se usa desde US1, pero puede implementarse en paralelo y mockearse mientras tanto)
- **Polish (Phase 10)**: depende de todas las historias que se quieran migrar/verificar

### Parallel Opportunities

- Dentro de Foundational: T005, T008, T010 en paralelo entre sí (T004 primero, bloquea T005)
- Dentro de US1: T020, T021, T067, T022, T024, T025, T026 en paralelo (distintos archivos)
- US3, US4 y US7 pueden implementarse en paralelo por distintas personas una vez terminada US1
- US5 puede implementarse en paralelo con US2/US3/US4/US6 (toca `schemas.py`/`repository.py` en puntos distintos, pero requiere coordinar el merge de `crear_orden`)

---

## Implementation Strategy

### MVP First (User Story 1)

1. Completar Phase 1 (Setup) y Phase 2 (Foundational)
2. Completar Phase 3 (US1): planificar, listar, editar, ejecutar y anular una orden con Formulario de Retiro y descuento FIFO
3. **VALIDAR** con el Escenario 1 de `quickstart.md`
4. Demo: reemplaza el registro básico de `FrmOrdenTrabajo` de Access

### Incremental Delivery

1. Setup + Foundational → base lista
2. US1 → MVP demostrable (reemplaza la carga básica de Access)
3. US2 (devoluciones) → cierra el ciclo de stock de una orden
4. US3 + US4 (maquinaria + contratista) → costo completo de una orden
5. US6 (resultado por cultivo) → objetivo central del módulo alcanzado
6. US5 + US7 → cobertura de casos de borde y administración
7. Polish → migración de los 153 registros heredados y verificación final contra `quickstart.md`
