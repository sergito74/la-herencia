# Tasks: Vínculo de órdenes de trabajo con documentos del contratista (revisado 06/11)

**Input**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/api.md](contracts/api.md), [quickstart.md](quickstart.md)

**Tests**: incluidos (Constitución V), con mocks y sin escribir en WC.

## Phase 1: Setup

- [X] T001 Sacar la foto previa: saldos de todas las cuentas (`cuentas_corrientes.repository.get_saldos_todos`, sin caché) y `resultado_cultivo.costos.costo_total` por cultivo/campaña de las campañas con órdenes, en `foto-previa-048.json` en el scratchpad.
- [X] T002 Crear `backend/scripts/vinculos_contratista_048.py`, re-corrible y con el patrón de `backend/scripts/contratos_canje_046.py`: backup de `dbo.OrdenesContratistaFacturas` y `dbo.ImputacionPropuestas` en `BAK_*_20261106` con verificación de conteos. Luego, en `dbo.OrdenesContratistaFacturas`, agregar `UsuarioConfirmacion nvarchar(100) NOT NULL` y `FechaConfirmacion datetime2 NOT NULL default SYSUTCDATETIME()`, y `UNIQUE (IdOrdenTrabajo, IdCompra)`. Correrlo en WC.

## Phase 2: Foundational

- [X] T003 Crear `backend/src/features/ordenes/documentos_contratista.py` con `RUBROS_LABOR = ('Fumigacion','Siembra','Cosecha','Fertilizacion','Disqueado','Embolsado Grano')` y `RUBROS_FUERA_REPARTO = ('Semillas','Fertilizantes','Agroquimicos','Hacienda','Trabajos Maq. Propia','Gastos Comercializacion')` (verificar los nombres en `dbo.Rubros`), y las funciones `es_documento_de_labor(id_compra)`, `es_nota_credito_debito(id_compra)`, `ordenes_del_contratista(id_compra)` (ejecutadas, del contacto de la compra, con fecha, labor, lotes y hectáreas —máximo por lote, sumado—, `vinculada` y `tieneOtraFactura`; primero las que no tienen factura y, dentro de eso, de la más nueva a la más vieja) y `neto_repartible(id_compra)` (sin `RUBROS_FUERA_REPARTO`, pesificado al TC del comprobante).
- [X] T004 En `backend/src/features/imputacion/motor.py` y `backend/src/features/imputacion/repository.py`: `evaluar_contratista` usa `neto_repartible` (cambiar `total_neto_compra`, que hoy suma todos los renglones) y la última fracción absorbe el redondeo. Nueva `evaluar_nota_relacionada(id_nc)`: si la NC/ND tiene en `CompraDocumentosRelacionados` una factura con corrida aprobada vigente, replica sus proporciones sobre el neto repartible de la NC/ND con su signo.
- [X] T005 En `backend/src/features/ordenes/documentos_contratista.py`, `fijar_vinculos(id_compra, ids_orden, usuario)`: valida que sea documento de labor, que no sea NC/ND y que las órdenes sean del contratista (si no, ValueError → 422). Sincroniza `OrdenesContratistaFacturas` (con usuario y fecha) en una transacción. Imputa: con órdenes, `evaluar_contratista` → `guardar_corrida` → `aprobar_corrida(usuario)`; sin órdenes, corrida aprobada vacía que retira. Crear en el mismo archivo `recalcular_nota(id_nc, usuario)`: `motor.evaluar_nota_relacionada` → guardar y aprobar, o corrida aprobada vacía si ya no tiene factura con reparto. `fijar_vinculos` la llama para cada NC/ND relacionada.
- [X] T006 [P] Tests en `backend/tests/ordenes/test_documentos_contratista.py`: la factura de hacienda no es de labor; la factura mixta excluye la semilla del neto; el reparto con varias órdenes y cultivos cierra al centavo; la orden sin cultivo va al centro de costo; la NC replica las proporciones en negativo; destildar todo retira la imputación.

## Phase 3: US1 — Vincular desde Compras (P1) 🎯 MVP

- [X] T007 [US1] En `backend/src/features/compras/router.py`: `GET` y `PUT /api/compras/{idCompra}/ordenes-trabajo` según [contracts/api.md](contracts/api.md), con el usuario de la sesión (016). En `backend/src/features/compras/repository.py`, al agregar o quitar un documento relacionado, llamar a `recalcular_nota` sobre la NC/ND involucrada.
- [X] T008 [P] [US1] Test de contrato en `backend/tests/compras/test_ordenes_trabajo_api.py`: forma del GET; PUT que agrega y quita; 422 si no es de labor, es NC/ND o la orden es de otro contratista; 403 para solo lectura; agregar un relacionado imputa la NC.
- [X] T009 [US1] En `frontend/src/services/comprasApi.ts`: `fetchOrdenesTrabajoCompra` y `fijarOrdenesTrabajoCompra` (TanStack Query, invalidando la compra, la orden y el resultado).
- [X] T010 [US1] Crear `frontend/src/components/compras/OrdenesTrabajoPanel.tsx`: lista tildable (fecha, labor, lotes, hectáreas con los helpers de formato, nunca `toLocaleString`), marca "ya tiene otra factura", botón Guardar dentro de `<SoloLectura>` y, abajo, el reparto por lote/cultivo/campaña. Si es NC/ND: "Se imputa como su factura: relacionala en Documentos relacionados". Si no es de labor: no se muestra.
- [X] T011 [US1] En `frontend/src/components/compras/CompraForm.tsx`: incluir `OrdenesTrabajoPanel` junto a `DocumentosRelacionadosPanel` (en una compra nueva, después del primer guardado, igual que relacionados). Al guardar una factura de labor de un contratista sin órdenes vinculadas, mostrar el aviso "Factura de contratista sin orden de trabajo" con confirmación (FR-009).

## Phase 4: US2 — La orden muestra y el Resultado imputa (P1)

- [X] T012 [US2] En `backend/src/features/ordenes/repository.py` (`obtener_orden`): `facturasContratista` con fecha, neto, moneda, `notasRelacionadas` y el reparto de la orden (desde `ImputacionPropuestas` aprobadas vigentes con ese `IdOrdenTrabajo`). Quitar `vincular_factura_contratista`/`desvincular_factura_contratista` y sus endpoints en `backend/src/features/ordenes/router.py`, y `facturaContratista` (singular). `anular_orden` y `corregir_hectareas` reciben el usuario de la sesión (pasarlo desde `ordenes/router.py`) y recalculan las facturas vinculadas con `fijar_vinculos` (al anular, sin esa orden). Reemplazar `backend/tests/test_ordenes_contratista_factura.py`, que usa las funciones eliminadas, por tests de la vista de solo lectura, y quitar `facturaContratista` (singular), `vincularFacturaContratista` y `desvincularFacturaContratista` de `frontend/src/services/ordenesApi.ts`.
- [X] T013 [US2] En `frontend/src/app/produccion/ordenes/[idOrden]/page.tsx` y `frontend/src/services/ordenesApi.ts`: reemplazar la sección "Facturas del contratista" (NumberInput, `guardarFactura`, `quitarFactura`, `vincular/desvincularFacturaContratista`) por una tabla de solo lectura: documento (enlace a `/compras/{id}/editar`), fecha, neto, NC/ND relacionadas y reparto. Sin documentos: "Todavía no hay facturas vinculadas a esta orden (se vinculan desde la factura, en Compras)".
- [X] T014 [US2] En `backend/src/features/resultado_cultivo/costos.py`: "Reparto vigente" = la ÚLTIMA corrida APROBADA de `Origen='Contratista'` del documento (no la última corrida: una corrida Pendiente creada por `/api/imputacion/recalcular` no debe hacer desaparecer el costo); una corrida aprobada sin fracciones (retiro) = sin reparto. `costos_heredados` excluye, de las compras con reparto vigente, todos los renglones fuera de `RUBROS_FUERA_REPARTO`; `costos_contratista` suma las fracciones del reparto vigente por `IdCultivo`/`IdCampania` con las mismas claves. En `backend/src/features/resultado_cultivo/resultado.py`, reemplazar la lectura de `Ordenes_Trabajo_Contratista_Factura` por la existencia de fracciones aprobadas.
- [X] T015 [P] [US2] Tests en `backend/tests/resultado_cultivo/test_costos_contratista.py`: sin vínculo cuenta la carga manual; con vínculo, el reparto, y la carga manual de lo repartido (incluido un renglón de Movilidad) no; la semilla de una factura mixta sigue por la vista heredada; anular la orden restituye la carga manual; una corrida Pendiente posterior a la aprobada no cambia el costo.

## Phase 5: US3 — Listado sin orden (P2)

- [X] T016 [US3] En `backend/src/features/ordenes/documentos_contratista.py` y `backend/src/features/ordenes/router.py`: `GET /api/ordenes/contratistas/sin-orden` y `/exportar` (.xlsx con openpyxl; columnas como `facturas-sin-orden-20261106-v2.xlsx`).
- [X] T017 [US3] Crear `frontend/src/app/produccion/contratistas/sin-orden/page.tsx`: filtro por contratista, tabla con enlace a `/compras/{id}/editar` y botón para exportar a Excel; agregar el enlace en el menú de Producción.

## Phase 6: Polish

- [X] T018 Correr `python -m pytest tests/ordenes tests/compras tests/imputacion tests/resultado_cultivo -q`, y `npm run lint` y `npx tsc --noEmit` en `frontend`.
- [X] T019 Reiniciar y recorrer los escenarios de [quickstart.md](quickstart.md) en WC, midiendo SC-001 (menos de 30 s) y la carga del panel (menos de 2 s), y verificando el aviso "sin orden" (escenario 7, FR-009).
- [X] T020 Control contra la foto de T001 (saldos al centavo; costo por campaña igual salvo repartos, que se listan) en `specs/048-vinculo-ordenes-documentos-contratista/validacion.md`; actualizar la memoria y dejar como tarea futura borrar la tabla vacía `Ordenes_Trabajo_Contratista_Factura` (con backup).

## Dependencies

Setup → Foundational → US1 y US2 (en paralelo; T012 usa `fijar_vinculos`) → US3 → Polish. MVP = Setup, Foundational, US1 y US2.
