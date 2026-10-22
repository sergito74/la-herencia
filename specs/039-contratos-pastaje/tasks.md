# Tasks: Contratos de pastaje

**Input**: specs/039-contratos-pastaje/ (spec.md, plan.md, research.md, data-model.md, contracts/api.md, quickstart.md)
**Tests**: incluidas (práctica del proyecto: contrato/cálculo antes de UI, pyodbc bloqueado en suites).
**Reglas**: escrituras solo en WC con respaldo COPY_ONLY verificado; Decimal sin float; no marcar tareas por mera existencia de archivos; registrar evidencia en quickstart.md.

## Phase 1: Setup

- [x] T001 Crear paquete backend/src/features/pastaje/ (__init__.py, router.py, schemas.py, repository.py, service.py) y registrar router `/api/pastaje` en backend/src/main.py siguiendo el patrón de backend/src/features/cajas_efectivo/router.py (`_usuario`, `_ejecutar`, 403 para SoloLectura en escrituras).
- [x] T002 [P] Crear helper de tests backend/tests/pastaje_039_helpers.py que bloquee pyodbc.connect y simule persistencia (patrón backend/tests/cajas_038_helpers.py).
- [x] T003 [P] Crear frontend/src/services/pastajeApi.ts con tipos de contracts/api.md (importes Decimal como string) y agregar "Pastaje" al menú Ventas en frontend/src/components/layout/NavHeader.tsx (`/ventas/pastaje`).

## Phase 2: Foundational

- [x] T004 Crear backend/scripts/migrar_pastaje_039.py (sin argumentos inspecciona; `--aplicar` hace respaldo con src.features.vinculos.backup.backup_verificado y `_assert_target_is_wc`) que cree en una transacción: dbo.IndiceINMAG (Fecha date PK, Indice decimal(18,3) >0, CabIngresadas int, Origen `auto`/`manual`, Fuente, ObtenidoEn, Nota obligatoria si manual), dbo.IndiceINMAG_Historial, dbo.ContratosPastaje, dbo.PastajeTarifas (único contrato+categoría+VigenteDesde; TipoTarifa `kg_novillo`/`fijo_ars`/`fijo_usd`), dbo.PastajeBitacora (Tipo `ingreso`/`egreso`/`muerte`/`faltante`/`nacimiento`/`destete`/`recuento`, Cabezas >0, Estado `vigente`/`anulado`), dbo.PastajeLiquidaciones (+Tramos, +Indices; única `mensual` no anulada por contrato+período), dbo.PastajeComprobantes (único Tipo+Letra+PuntoVenta+Numero), con columnas de auditoría y Version según data-model.md.
- [x] T005 En el mismo script agregar rama `'Pastaje'` a vw_MovimientosCuenta_Base con CREATE OR ALTER VIEW (factura/ND al debe, NC al haber, solo Estado `vigente`) y ampliar CK_AplicacionesPago_TipoDocumento con `'Pastaje'`; guardar definición anterior de la vista en backups/pastaje-039-schema/ y verificar que el conteo y los totales debe/haber de la vista sean idénticos antes/después (gate; abortar y revertir si difieren).
- [x] T006 Ejecutar migración en modo inspección, luego `--aplicar`; registrar respaldo, evidencia JSON y gate en specs/039-contratos-pastaje/quickstart.md.
- [x] T007 [P] Implementar cálculo puro en backend/src/features/pastaje/calculo.py: cabezas-día por categoría desde bitácora (día de ingreso se cobra, día de egreso/muerte/faltante no; crías cobran desde destete; recuento sin efecto), tarifa vigente por día, precio = round(promedio simple INMAG de días con hacienda y con índice, 2), kg sin redondeo intermedio, neto = round(Σ kg×precio, 2), IVA = round(neto×0,21, 2); precio fijo ARS/USD; bloqueo si no hay índice.
- [x] T008 [P] Tests backend/tests/test_pastaje_calculo_039.py: septiembre 2026 (70 vaquillonas desde 25/09, 5 kg, 4.068,212/4.241,828 → 70 kg, $4.155,02, $290.851,40, $61.078,79, $351.930,19), mes de 31 días, egreso a mitad de mes, muerte, nacimiento/destete, varias categorías, sin índice bloqueado, precio fijo.

## Phase 3: US3 — Índice INMAG diario automático (P1)

**Goal**: INMAG registrado cada día sin intervención. **Independent test**: actualizar 25–30/09/2026 → filas 25 y 29, sin fila 30, reintento sin duplicados.

- [x] T009 [US3] Implementar backend/src/features/pastaje/inmag.py: POST a haciinfo000011 (txtFechaIni/txtFechaFin dd/mm/aaaa, USUARIO=SIN+IDENTIFICAR), parseo de "TOTALES POR DIA … I.N.M.A.G." con '.' como separador de miles en cabezas, días con "-" omitidos; upsert idempotente; correcciones manuales con historial y nota obligatoria.
- [x] T010 [P] [US3] Tests backend/tests/test_pastaje_inmag_039.py con HTML de fixture (guardar muestra de la respuesta real en backend/tests/fixtures/inmag_20260925_30.html).
- [x] T011 [US3] CLI backend/scripts/indice_inmag.py (`--desde`, por defecto recupera los últimos 10 días faltantes) y carga histórica desde 2020-03-01; ejecutar y registrar cantidad de filas y verificación 25/09 y 29/09 en quickstart.md.
- [x] T012 [US3] Instalador backend/scripts/instalar_indice_inmag.ps1 (Register-ScheduledTask "LaHerencia - Indice INMAG" -Daily, -StartWhenAvailable -RunOnlyIfNetworkAvailable, pythonw -m scripts.indice_inmag; el día 1 además llama generar-mes) siguiendo backend/scripts/instalar_descarga_peajes.ps1.
- [x] T013 [US3] Endpoints GET /indice-inmag, POST /indice-inmag/actualizar, PUT /indice-inmag/{fecha} en backend/src/features/pastaje/router.py.

## Phase 4: US1 — Condiciones del contrato (P1)

**Goal**: alta y consulta de contratos. **Independent test**: contrato San Justo visible con 70 vaquillonas, 5 kg, INMAG, mes vencido, IVA 21%, contado y cláusulas.

- [x] T014 [US1] Repositorio/servicio de contratos y tarifas en backend/src/features/pastaje/repository.py y service.py (Modalidad `mes_vencido`, CondicionVenta `contado`, AlicuotaIva 21.00, IdEstablecimiento 1, empresa contacto 386; editar sin afectar meses liquidados; transiciones de Estado `vigente` → `finalizado` (con FechaFin) y `anulado` (solo sin liquidaciones confirmadas), con motivo; adjunto opcional guardado con el almacenamiento de archivos existente (componente frontend/src/components/ui/ArchivoVinculado.tsx y su backend)).
- [x] T015 [P] [US1] Tests de contrato API backend/tests/test_pastaje_contrato_039.py (alta, edición, listado con tarjetas, 403 Lectura, concurrencia por Version).
- [x] T016 [US1] Endpoints de contratos (GET/POST/PUT /contratos, GET /contratos/{id}, POST archivo-contrato, POST /contratos/{id}/finalizar y /anular) con resumen de tarjetas (cabezas actuales, último INMAG, promedio y estimado del mes en curso, próximo paso, alertas).
- [x] T016a [US1] Consultar a los agentes .github/agents/08-agro-erp-frontend-specialist.agent.md y 09-agroux-lead-product-architect.agent.md (subagentes) sobre la propuesta de pantallas de spec.md antes de construir la UI; registrar decisiones en specs/039-contratos-pastaje/research.md.
- [x] T017 [US1] Frontend: frontend/src/app/ventas/pastaje/page.tsx (tarjetas por contrato) y frontend/src/app/ventas/pastaje/[id]/page.tsx con componente frontend/src/components/pastaje/FichaContrato.tsx (pestaña Condiciones: parámetros, tarifas, cláusulas, contrato adjunto; formulario de alta/edición con MoneyInput y helpers de formato global; SoloLectura).

## Phase 5: US2 — Bitácora de hacienda (P1)

**Goal**: movimientos fechados. **Independent test**: ingreso 70 el 25/09 con DTe → 420 cabezas-día en septiembre.

- [x] T018 [US2] Bitácora en repository/service: alta, validación de no negativos por categoría y fecha, recuento devuelve diferencia (positiva o negativa) sin modificar cabezas, anulación con motivo.
- [x] T019 [US2] Endpoints GET/POST /contratos/{id}/bitacora y POST /bitacora/{id}/anular; ampliar tests en backend/tests/test_pastaje_contrato_039.py (incluye recuento con más cabezas que las registradas y con menos).
- [x] T020 [US2] Frontend frontend/src/components/pastaje/BitacoraHacienda.tsx (línea de tiempo, cabezas vigentes por categoría, formulario de movimiento, alerta de recuento).

## Phase 6: US4 — Liquidación mensual (P1)

**Goal**: liquidación del mes vencido con PDF. **Independent test**: septiembre 2026 reproduce la liquidación real y genera PDF en la carpeta del contrato.

- [x] T021 [US4] Servicio de liquidaciones: preview, borrador, generar-mes, confirmar (fija tramos e índices copiados), anular (solo sin comprobante vigente), ajuste (original vs recalculado).
- [x] T022 [US4] PDF backend/src/features/pastaje/liquidacion_pdf.py con reportlab replicando "Liquidación de Pastaje - Septiembre.pdf" (C:\Users\Sergio\Documents\La Herencia\Ganaderia\Pastaje - La Herencia); guardar como `Liquidación de Pastaje - {Mes} {Año} - {Cliente}.pdf` en CarpetaDocumentos; variante de ajuste.
- [x] T023 [US4] Endpoints de liquidaciones (preview, crear, generar-mes, confirmar, ajuste, pdf, texto-factura) y tests en backend/tests/test_pastaje_liquidacion_039.py (bloqueo sin índice, unicidad mensual, fijación tras confirmar).
- [x] T024 [US4] Frontend frontend/src/components/pastaje/Liquidaciones.tsx (preview por tramos e índices usados, confirmar, abrir PDF, texto sugerido para ARCA con copiar).

- [x] T024a [US4] Revisión de los agentes 06-livestock-health-specialist y 07-financial-direction-specialist (subagentes) sobre cálculo, PDF de liquidación y caso septiembre; registrar hallazgos en quickstart.md y corregir antes de US5.

## Phase 7: US5 — Facturas emitidas (P2)

**Goal**: factura ARCA desde PDF a cuenta corriente. **Independent test**: factura A 0002-00000008 vinculada a septiembre sin diferencias; saldo cliente $351.930,19.

- [x] T025 [US5] Lector backend/src/features/pastaje/lector_factura.py (pdfplumber, patrón descarga_peajes/lectores.py): tipo/código, letra, punto de venta, número, fecha, vto pago, CUIT emisor (debe ser 30712114602), CUIT cliente, período, detalle, neto, IVA 21%, total, CAE, vto CAE.
- [x] T026 [P] [US5] Tests backend/tests/test_pastaje_factura_039.py con texto de fixture de 20261006_Giamigli.pdf (sin copiar el PDF al repo): lectura exacta, advertencias de emisor/cliente/importes, duplicado 409, ND/NC vinculada.
- [x] T027 [US5] Endpoints POST /comprobantes/leer, POST /comprobantes, GET /contratos/{id}/comprobantes, POST /comprobantes/{id}/anular (bloqueado con cobros aplicados); el PDF subido se guarda con el almacenamiento de archivos existente (ArchivoVinculado) y el comprobante guarda su referencia en ArchivoPdf; IdCampaña por período julio–junio (dbo.Campañas "YYYY/YYYY+1").
- [x] T028 [US5] Integración de cobros: tipo `'Pastaje'` en backend/src/features/aplicaciones_pago/documentos.py, mapeo de origen en backend/src/features/recalculo_fifo/ejecuciones.py; revisar backend/src/features/auditoria_cuentas/datos.py, bimonetaria.py y backend/src/features/cajas_efectivo/operaciones.py/service.py para que reconozcan el origen; retenciones sufridas en dbo.[Retenciones Ventas Hacienda] vinculadas al comprobante mediante AplicacionesPago (OrigenMovimiento `ret-ventas-hacienda`, TipoDocumento `Pastaje`, IdDocumentoAplicado = IdComprobante), con test de trazabilidad retención → comprobante; tests de regresión de aplicaciones/cajas.
- [x] T029 [US5] Frontend frontend/src/components/pastaje/Facturas.tsx (subir PDF, confirmar datos leídos, comparación con liquidación, grilla por mes con cobrado/saldo, ND/NC).

## Phase 8: US6 — Devengado vs facturado (P2)

**Independent test**: septiembre "Facturado — pendiente de cobro", octubre "En curso" con estimado.

- [x] T030 [US6] Resumen mensual por contrato (devengado, liquidado, facturado, cobrado, saldo, estado, diferencia) y alertas en service.py; tests.
- [x] T031 [US6] Sección "Otros ingresos — Pastaje" (neto, por campaña y establecimiento) en backend/src/features/resultado_cultivo/ (consolidado de campaña) y frontend/src/components/resultado-cultivo/ConsolidadoCampaniaView.tsx, sin repartir a cultivos.
- [x] T032 [US6] Frontend: panel de meses y alertas en FichaContrato.tsx; pestaña Índice con valores del período y días usados.

## Phase 9: US7 — Unificación del índice INMAG (P3, FR-019)

**Goal**: INMAG único índice del sistema. **Independent test**: comparación por socio aprobada por Sergio antes del cambio.

- [x] T033 [US7] Script de solo lectura backend/scripts/comparar_indice_socios_039.py: valuación de cuentas de socios con IndiceNovillo vs IndiceINMAG (kg y pesos por socio y total); informe en backups/pastaje-039-schema/ y resumen en quickstart.md. PRESENTAR A SERGIO Y ESPERAR APROBACIÓN.
- [ ] T034 [US7] Tras aprobación: cambiar backend/src/features/cuentas_socios/valuacion.py y backend/src/features/cuentas_socios/repository.py (línea ~178) para leer dbo.IndiceINMAG; tests de valuación actualizados; IndiceNovillo queda como histórico (dejar de cargarlo en backend/scripts/cotizaciones_dolar_novillo.py, mantener carga de Dólar BNA).

## Phase 10: Polish

- [ ] T035 Alta del contacto Ganadera San Justo S.S. (CUIT 30715943278) y del contrato real desde la UI con Sergio; liquidación de septiembre confirmada y factura cargada; verificar cuenta corriente (escenarios 1, 10, 12 de quickstart.md).
- [ ] T036 Recorrido UI de las historias, medición de SC-002 (tiempo de preparar y confirmar la liquidación de un contrato < 5 min) e informe de cobertura INMAG (días con remate vs días cargados automáticamente, meta SC-003 ≥ 95%) al cumplirse 30 días de la tarea programada; además recorrido UI de las historias (vacío/error/Lectura), `python -m pytest tests -q -k 039`, `npx tsc --noEmit`, regresiones de aplicaciones/cajas/cuentas corrientes; revisión de diff, secretos y binarios; actualizar spec/plan/quickstart/tasks con evidencia.

## Dependencies

Setup → Foundational (T004–T008) → US3 (índice) → US1 → US2 → US4 → US5 → US6. US7 depende de US3 (histórico INMAG) y es independiente del resto. Estados: T034 requiere aprobación explícita de T033.

## Parallel examples

- T002, T003, T007/T008 en paralelo tras T001.
- T010 con T009; T015 con T014; T026 con T025.
- US7 (T033) puede correr en paralelo con US1–US2 una vez cargado el histórico INMAG (T011).

## Implementation strategy

MVP = Foundational + US3 + US1 + US2 + US4: permite emitir la liquidación de octubre a comienzos de noviembre 2026. Luego US5 (factura y cobro), US6 (control y resultado) y US7 (unificación, con aprobación).
