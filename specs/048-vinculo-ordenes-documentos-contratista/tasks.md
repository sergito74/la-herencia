# Tasks: Vínculo de órdenes de trabajo con documentos del contratista

**Input**: Design documents from `specs/048-vinculo-ordenes-documentos-contratista/` ([plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/api.md](contracts/api.md), [quickstart.md](quickstart.md))

**Tests**: incluidos (Constitución V: cada cambio con su verificación automática más chica útil), con mocks/fixtures y sin escribir en WC.

## Phase 1: Setup

- [ ] T001 Sacar la foto previa: saldos de todas las cuentas corrientes (`cuentas_corrientes.repository.get_saldos_todos`, sin caché) y costo por concepto del Resultado por cultivo de todas las campañas con órdenes (`resultado_cultivo.costos.costo_total` por cultivo/campaña), guardados en JSON en el scratchpad (`foto-previa-048.json`), para SC-004/SC-005.
- [ ] T002 Crear `backend/scripts/vinculos_contratista_048.py` (re-corrible, con backup previo como `backend/scripts/contratos_canje_046.py`): respaldo de `dbo.OrdenesContratistaFacturas` y `dbo.ImputacionPropuestas` en tablas `BAK_..._20261106` con verificación de conteos. Luego, en `dbo.OrdenesContratistaFacturas`: agregar `UsuarioConfirmacion nvarchar(100) NOT NULL` y `FechaConfirmacion datetime2 NOT NULL default SYSUTCDATETIME()`, y `UNIQUE (IdOrdenTrabajo, IdCompra)`. Crear `dbo.OrdenesContratistaDescartes` (`IdDescarte int identity PK`, `IdCompra int NOT NULL UNIQUE`, `Motivo nvarchar(30) NOT NULL` ∈ `propuesta_incorrecta|sin_orden`, `OrdenesPropuestas nvarchar(400) NULL`, `Observacion nvarchar(400) NULL`, `Usuario nvarchar(100) NOT NULL`, `Fecha datetime2 NOT NULL default SYSUTCDATETIME()`). Correrlo en WC y registrar el resultado del backup.

## Phase 2: Foundational (bloquea todas las historias)

- [ ] T003 Crear `backend/src/features/ordenes/documentos_contratista.py` con las constantes `RUBROS_LABOR = ('Fumigacion','Siembra','Cosecha','Fertilizacion','Disqueado','Embolsado Grano')`, `RUBROS_FUERA_REPARTO = ('Semillas','Fertilizantes','Agroquimicos','Hacienda','Trabajos Maq. Propia','Gastos Comercializacion')` (verificar los nombres exactos en `dbo.Rubros`) y `PUESTA_EN_MARCHA` (fecha del deploy), y estas funciones: `documentos_de_labor(id_contacto)` (R1: Factura/NC/ND con al menos un renglón de labor, con hectáreas de los renglones en ha o sin unidad, neto repartible sin los rubros fuera del reparto, pesificado al TC del comprobante), `hectareas_orden(id_orden)` (máximo por lote, sumado, de `Ordenes_Trabajo_Distrib`) y `propuestas(id_contacto)` (R2: ventana desde la factura de labor anterior, máximo 90 días, órdenes ejecutadas no vinculadas; `rotulo` coincide <1% / cerca <10% / no coincide / otra unidad / sin orden). Todo con consultas parametrizadas.
- [ ] T004 En `backend/src/features/imputacion/motor.py`, `evaluar_contratista`: usar como `monto_total` el neto repartible de T003 (sin rubros fuera del reparto) y hacer que la última fracción absorba el redondeo para cerrar al centavo. Para NC/ND con `CompraDocumentosRelacionados` hacia una factura con corrida aprobada, replicar sus proporciones con el signo de la NC/ND (R4). Ajustar `repository.total_neto_compra` si hace falta.
- [ ] T005 En `backend/src/features/ordenes/documentos_contratista.py`, `fijar_vinculos(id_compra, ids_orden, usuario)`: en una transacción, sincronizar `OrdenesContratistaFacturas` (agrega y quita, con usuario y fecha) y borrar el descarte si existe. Después recalcular el documento y sus NC/ND relacionadas: si quedan órdenes, `motor.evaluar_contratista` → `guardar_corrida` → `aprobar_corrida(usuario)`; si no quedan, nueva corrida vacía que retira la imputación. Validar que el documento sea de labor y del contratista de cada orden (si no, ValueError → 422).
- [ ] T006 [P] Tests en `backend/tests/ordenes/test_documentos_contratista.py`: filtro de labor (una factura de hacienda no entra; una factura mixta excluye la semilla del neto), rótulos de propuesta, reparto que cierra al centavo con varias órdenes y cultivos, NC que sigue a su factura con signo negativo, desvincular que retira la imputación.

## Phase 3: User Story 1 — Vincular desde la orden con una lista (P1) 🎯 MVP

**Goal**: en la orden, tildar los documentos del contratista sin tipear números.

**Independent Test**: en la orden 162, la factura 00002-00000735 aparece sugerida y se vincula con un tilde.

- [ ] T007 [US1] En `backend/src/features/ordenes/router.py`: `GET /api/ordenes/{idOrden}/documentos-contratista` y `PUT /api/ordenes/{idOrden}/documentos-contratista` (body `{idsCompra: []}`), según [contracts/api.md](contracts/api.md). El usuario sale de la sesión (016). Los endpoints viejos `POST/DELETE .../factura-contratista` pasan a delegar en `fijar_vinculos`, y `repository.vincular_factura_contratista`/`desvincular_factura_contratista` usan esa misma lógica.
- [ ] T008 [P] [US1] Test de contrato en `backend/tests/ordenes/test_documentos_contratista_api.py`: forma de la respuesta del GET (sin ids visibles salvo `idCompra`), PUT que agrega y quita, 422 para un documento de otro contratista o que no es de labor, lista vacía para maquinaria propia.
- [ ] T009 [US1] En `frontend/src/services/ordenesApi.ts`: tipos y funciones `documentosContratista(idOrden)` y `fijarDocumentosContratista(idOrden, idsCompra)`, con TanStack Query e invalidación de la orden y del resultado.
- [ ] T010 [US1] Crear `frontend/src/components/ordenes/DocumentosContratistaPanel.tsx`: lista tildable con tipo, número, fecha, hectáreas y neto (helpers de moneda/números, nunca `toLocaleString`), rótulo "sugerida", aviso "vinculada también a la orden del dd/mm" y botón Guardar dentro de `<SoloLectura>`. Tras guardar, mostrar el reparto por lote/cultivo/campaña. Estado vacío: "No hay documentos de labor de este contratista". El número de documento enlaza a `/compras/{id}/editar`.
- [ ] T011 [US1] En `frontend/src/app/produccion/ordenes/[idOrden]/page.tsx`, reemplazar la sección "Facturas del contratista" (NumberInput de IdCompra, `guardarFactura`, `quitarFactura`) por `DocumentosContratistaPanel`.

## Phase 4: User Story 2 — Imputación automática en el Resultado (P1)

**Goal**: el Resultado por cultivo toma el reparto de los vínculos confirmados, sin doble conteo.

**Independent Test**: tras vincular la orden 162, el cultivo/campaña muestra el costo de contratista desde la orden y la factura ya no figura como costo heredado; al desvincular, vuelve la carga manual.

- [ ] T012 [US2] En `backend/src/features/resultado_cultivo/costos.py`: `costos_heredados` excluye los renglones de rubros de labor de las compras con corrida `Contratista` aprobada vigente (los renglones fuera del reparto siguen). `costos_contratista` suma las fracciones aprobadas vigentes de `ImputacionPropuestas` (`Origen='Contratista'`, `IdCultivo`, `IdCampania`), con las mismas claves de hoy. Pesos y dólares al TC del comprobante. Dejar de leer `Ordenes_Trabajo_Contratista_Factura`.
- [ ] T013 [US2] En `backend/src/features/resultado_cultivo/resultado.py` (y `backend/src/features/ordenes/resultado.py` si corresponde): reemplazar las lecturas de `Ordenes_Trabajo_Contratista_Factura` por la existencia de fracciones aprobadas de contratista del cultivo y campaña.
- [ ] T014 [US2] En `backend/src/features/ordenes/repository.py`: `anular_orden` borra los vínculos de la orden y recalcula los documentos afectados con `fijar_vinculos`; `corregir_hectareas` recalcula los documentos vinculados a la orden.
- [ ] T015 [P] [US2] Tests en `backend/tests/resultado_cultivo/test_costos_contratista.py`: sin vínculo cuenta la carga manual; con vínculo cuenta el reparto y no la carga manual (total igual si el cultivo/campaña coincide); la semilla de una factura mixta sigue por la vista heredada; anular la orden restituye la carga manual.

## Phase 5: User Story 3 — Revisión en bloque del histórico (P2)

**Goal**: confirmar, corregir o descartar las propuestas por contratista, y ver el detalle "sin orden".

**Independent Test**: en la revisión de Pérez, confirmar la factura 00002-00000691 con la orden 141 la vincula e imputa; descartar otra como "sin orden" la pasa al detalle.

- [ ] T016 [US3] En `backend/src/features/ordenes/documentos_contratista.py`: `revision(id_contacto, estado)` (estados calculados según [data-model.md](data-model.md); `pendientes` por contratista; un descarte cuyo `OrdenesPropuestas` ya no coincide con la propuesta actual vuelve a `sin_revisar`), `descartar(id_compra, motivo, observacion, usuario)` con `Motivo` ∈ `propuesta_incorrecta|sin_orden`, `reabrir(id_compra)` y `sin_orden_detalle()` (renglones con rubro, concepto, cantidad, unidad, neto, cultivo/destino y campaña cargados a mano).
- [ ] T017 [US3] En `backend/src/features/ordenes/router.py`: `GET /api/ordenes/contratistas/revision`, `POST .../revision/{idCompra}/confirmar`, `POST .../revision/{idCompra}/descartar`, `DELETE .../revision/{idCompra}/descarte`, `GET /api/ordenes/contratistas/sin-orden` y `GET .../sin-orden/exportar` (.xlsx con openpyxl, columnas como `facturas-sin-orden-20261106-v2.xlsx`).
- [ ] T018 [P] [US3] Tests en `backend/tests/ordenes/test_revision_contratistas.py`: estados, confirmar con una corrección de órdenes, descartar y reabrir, descarte invalidado al cambiar las órdenes candidatas, export con las columnas esperadas.
- [ ] T019 [US3] Crear `frontend/src/app/produccion/contratistas/revision/page.tsx`: selector de contratista con el conteo de pendientes, filtro de estado, tabla de facturas con las órdenes propuestas (fecha, labor, hectáreas), diferencia de hectáreas y rótulo, y acciones Confirmar (con tildes para corregir las órdenes), Descartar (motivo) y Reabrir dentro de `<SoloLectura>`. Pestaña "Sin orden" con el detalle y un botón para exportar a Excel. Agregar el enlace en el menú de Producción.
- [ ] T020 [US3] FR-008b: facturas de labor con fecha ≥ `PUESTA_EN_MARCHA` sin vínculo ni descarte. En `backend/src/features/documentos_nuevos` (listado de revisión de la rutina 043), agregar el aviso "Factura de contratista sin orden de trabajo" con enlace a la revisión del contratista; mostrar también el conteo en el menú si existe el mecanismo de avisos de la bóveda.

## Phase 6: Polish & Cross-Cutting

- [ ] T021 Correr `python -m pytest tests/ordenes tests/imputacion tests/resultado_cultivo tests/documentos_nuevos -q` en `backend`, y `npm run lint` y `npx tsc --noEmit` en `frontend`.
- [ ] T022 Reiniciar con `LaHerencia.ps1 -Reiniciar -NoBrowser` y recorrer los escenarios 1 a 7 de [quickstart.md](quickstart.md) contra WC.
- [ ] T023 Control final contra la foto de T001: saldos de cuentas iguales al centavo (SC-005); costo de contratista por campaña igual, salvo repartos entre cultivos, que se listan para Sergio (SC-004). Registrar el resultado en `specs/048-vinculo-ordenes-documentos-contratista/validacion.md`.
- [ ] T024 Actualizar la memoria del proyecto y el traspaso (decisiones D1–D4, rubros de labor, puesta en marcha) y marcar como tarea futura la eliminación de la tabla vacía `Ordenes_Trabajo_Contratista_Factura` (con backup).

## Dependencies & Execution Order

- Setup (T001–T002) → Foundational (T003–T006) → US1 (T007–T011) y US2 (T012–T015), que pueden ir en paralelo → US3 (T016–T020, usa `fijar_vinculos` y el Resultado ya corregido) → Polish.
- Dentro de US1, el backend (T007) va antes del frontend (T009–T011).

## Parallel Opportunities

- T006, T008, T015 y T018 (tests en archivos distintos) en paralelo con la implementación de su fase.
- Las fases US1 (orden + frontend) y US2 (resultado_cultivo) tocan archivos distintos.

## Implementation Strategy

- **MVP** = Setup + Foundational + US1 + US2: se puede vincular desde la orden y el Resultado lo refleja.
- Después, US3 para revisar el histórico (91 facturas) con Sergio, y el aviso de facturas nuevas sin orden.
