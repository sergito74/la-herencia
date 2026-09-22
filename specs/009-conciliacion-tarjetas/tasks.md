# Tasks: Conciliación manual de consumos de tarjeta

**Nota**: tareas documentadas **retroactivamente** el 2026-09-22 (ver `plan.md`). El código ya existía antes de este documento; cada tarea marcada `[X]` apunta al archivo/función real que la implementa, verificado en vivo contra `WC` (ver `validation.md`). No se generó con `/speckit-tasks` antes de codear.

## Setup

- [X] T001 Tabla nueva `dbo.Tarjetas_Resumenes_Lineas_Estado` en `WC` (`IdLineaConsumo` PK, `Estado`, `Motivo`, `Detalle`, `ImporteDiferencia`) — spec.md "Datos". Confirmada por `repository.py` (`marcar_sin_documento`/`quitar_estado`/consultas de `estadoLinea`).
- [X] T002 Router registrado en `backend/src/main.py` bajo `/api/tarjetas-resumenes` (compartido con 008) — `backend/src/features/tarjetas_resumenes/router.py`.
- [X] T003 Ruta frontend `/finanzas/tarjetas/conciliacion` — `frontend/src/app/finanzas/tarjetas/conciliacion/page.tsx`.

## Foundational (cálculo puro, sin escritura)

- [X] T010 Pesificación de documentos en dólares con su propio tipo de cambio, redondeo a 2 decimales antes de sumar — `backend/src/features/tarjetas_resumenes/conciliacion_documentos.py`.
- [X] T011 Tolerancia de cierre exacto en pesos ±$0,10 — `conciliacion_documentos.py`.
- [X] T012 Detección de combinaciones exactas (Factura + NC/ND, incluso multi-proveedor) — `conciliacion_documentos.py`, `repository.py:361` (`get_documentos_candidatos`).
- [X] T013 Detección de notas `Ajusta Tipo Cambio` del proveedor de la factura en dólares, ordenadas por cercanía de fecha, y cálculo del importe aproximado (tipo de cambio implícito) cuando falta la nota — `conciliacion_documentos.py`; usa `Compras.[Ajusta Tipo Cambio]` vía `repository.py:320,370,514`.
- [X] T014 Tests unitarios de cálculo puro — `backend/tests/test_conciliacion_documentos.py` (16 tests, verde).

## Historia 1 — Bandeja de pendientes (P1)

- [X] T020 `GET /api/tarjetas-resumenes/pendientes` con filtros `idTarjeta`/`proveedor`/`fechaCierreDesde`/`fechaCierreHasta`/`soloConSugerencia`, paginado, orden por sugerencia exacta primero — `router.py:196-222`, `repository.py:553` (`get_pendientes`).
- [X] T021 `BandejaConciliacion.tsx` — filtros y tabla, cada fila abre el panel — `frontend/src/components/tarjetas-conciliacion/BandejaConciliacion.tsx`.
- [X] T022 Verificado en vivo 2026-09-22: 281 líneas pendientes reales, filtros funcionan, orden prioriza `sugerencia.estado === "exacta"` — ver `validation.md`.

## Historia 2 — Panel de conciliación dividido (P1)

- [X] T030 `GET /api/tarjetas-resumenes/lineas/{id}/candidatos` — línea, líneas hermanas del mismo proveedor, documentos candidatos, sugerencias — `router.py:328-335`, `repository.py:484` (`get_candidatos_linea`).
- [X] T031 `GET /api/tarjetas-resumenes/documentos-buscar?q=` — canasta con buscador de documentos de otros proveedores — `router.py:251-256`, `repository.py:506`.
- [X] T032 `PanelConciliacion.tsx` — pantalla dividida (línea + hermanas + PDF a la izquierda; canasta + sugerencias + acciones a la derecha) — `frontend/src/components/tarjetas-conciliacion/PanelConciliacion.tsx` (657 líneas).
- [X] T033 `POST /api/tarjetas-resumenes/lineas/{id}/compras` (vínculo simple) y `DELETE .../compras/{idVinculo}` (quitar vínculo) — `router.py:313-325,365-367`, `repository.py:764` (`vincular_compra`), `repository.py` (`quitar_vinculo_compra`).
- [X] T034 Verificado en vivo: línea real (704, Corredores Viales) vinculada a su factura exacta (HTTP 201), desapareció de pendientes, `DELETE` del vínculo la devolvió a pendientes sin dejar rastro en `WC` — ver `validation.md`.

## Historia 3 — Notas de ajuste de tipo de cambio (P2)

- [X] T040 Al elegir factura en USD, resaltar NC/ND `Ajusta Tipo Cambio` del proveedor ordenadas por cercanía de fecha — `PanelConciliacion.tsx` líneas ~207-208, ~445, ~502 (`hayFacturaUsd`, `ajustesSinTildar`, badge "Ajuste TC").
- [X] T041 Guardar relación factura–nota en `CompraDocumentosRelacionados` al vincular — `repository.py` (vía `vincular_compras_lote`/`conciliar_reparto`).
- [X] T042 Si falta la nota, mostrar importe aproximado (TC implícito) como pista — `conciliacion_documentos.py` + `PanelConciliacion.tsx`.
- [X] T043 Verificado por código: la lógica está presente y ejercitada por los 16 tests de `test_conciliacion_documentos.py`. **No se verificó en vivo contra una línea real con factura en USD** porque, entre las 281 líneas pendientes reales del 2026-09-22, ninguna de las combinaciones exploradas manualmente tenía factura en dólares con nota de ajuste disponible (el propio `spec.md` documenta que `CompraDocumentosRelacionados` tiene 0 filas hoy y que de 6 casos históricos solo 1 se explica con nota del proveedor — es un caso real pero infrecuente). Queda como verificación pendiente la próxima vez que aparezca una línea así en la bandeja.

## Historia 4 — Muchas líneas contra muchos documentos (P2)

- [X] T050 `POST /api/tarjetas-resumenes/lineas/reparto-propuesta` — reparto editable propuesto por importe — `router.py:259-265`, `repository.py:703` (`proponer_reparto`).
- [X] T051 `POST /api/tarjetas-resumenes/lineas/conciliar-reparto` — guarda de una vez, con `aceptarDiferencia` opcional por residuo fuera de tolerancia — `router.py:268-278`, `repository.py:721` (`conciliar_reparto`).
- [X] T052 UI de tildar varias líneas + varios documentos y editar el reparto propuesto — `PanelConciliacion.tsx` líneas ~169-287 (`repartoEdit`, `diferenciasReparto`).
- [X] T053 Verificado en vivo: 2 líneas (704 + 710, Corredores Viales, $1.258,38 + $2.013,40) contra 2 documentos de otros números de factura — la propuesta calzó 1:1 por importe, con diferencia de $0,01 en la segunda (dentro de la tolerancia ±$0,10, por lo que correctamente **no** quedó como "diferencia aceptada"). `POST conciliar-reparto` devolvió `{"lineas":2,"vinculos":2}` (HTTP 201). Se revirtieron ambos vínculos con `DELETE` y la bandeja volvió a su total original (281) — ver `validation.md`.

## Historia 5 — Aceptar sugerencias exactas con vista previa (P2)

- [X] T060 `GET /api/tarjetas-resumenes/pendientes/exactas` — vista previa, solo combinaciones únicas en pesos — `router.py:225-242`, `repository.py:612` (`get_exactas_propuestas`).
- [X] T061 `POST /api/tarjetas-resumenes/pendientes/aceptar-exactas` — confirma, nunca aplica sin ese paso previo — `router.py:245-248`, `repository.py:629` (`aceptar_exactas`).
- [X] T062 Modal de vista previa en la bandeja — `BandejaConciliacion.tsx`.
- [X] T063 Verificado en vivo: 35 propuestas reales en la vista previa el 2026-09-22. Se confirmaron 2 líneas (706, 707); el sistema aplicó 1 y omitió la otra (706) porque su combinación dejó de ser única/exacta en el momento de confirmar (comportamiento correcto: revalida antes de aplicar). Se revirtió el vínculo aplicado (línea 707) — ver `validation.md`.

## Historia 6 — Sin documento / no aplica (P2)

- [X] T070 `POST /api/tarjetas-resumenes/lineas/{id}/sin-documento` (motivo + detalle) y `DELETE .../estado` (quitar) — `router.py:281-291`, `repository.py:693,699` (`marcar_sin_documento`, `quitar_estado`).
- [X] T071 Link precargado a `/compras/nueva` con proveedor/fecha/importe — `PanelConciliacion.tsx` línea ~638 (`compraParams`, existe alta de Compras ya implementada fuera de esta feature).
- [X] T072 Verificado en vivo: línea real 2699 ("Mercado Lobre", $100.000, sin sugerencia) marcada "sin documento" con motivo `Otro` (HTTP 204), desapareció de pendientes (281→280), `DELETE` del estado la devolvió (280→281) — ver `validation.md`. **No se hizo clic real en el link a `/compras/nueva`** (no se abrió navegador); se verificó por código que arma los query params correctos.

## Transversal / Polish

- [X] T080 Exportar a Excel — `GET /api/tarjetas-resumenes/reporte-conciliacion`, `backend/src/features/tarjetas_resumenes/reporte_conciliacion.py`, botón `BotonExportarConciliacion.tsx`. Verificado en vivo: HTTP 200, `.xlsx` válido con 5 hojas (Resúmenes, Conciliación, Pagos, Proveedores sin CUIT, Ayuda), 295 filas en la primera hoja.
- [X] T081 Recrear líneas en `PUT`/`DELETE` de resumen (008) borra también las filas de estado de esta feature, no solo los vínculos — confirmado por código en `repository.py` (mismo bloque que borra `Tarjetas_Resumenes_Lineas_Compras`). No re-ejecutado en vivo en esta verificación (fuera del alcance de las 6 historias; ya cubierto por los tests de 008).
- [X] T082 Tests backend — `backend/tests/test_conciliacion_documentos.py` (16) + `backend/tests/test_conciliacion_endpoints.py` (5) = 21 tests, verdes el 2026-09-22 (`python -m pytest ... -q` → `21 passed`).

## No cubierto en esta verificación (pendiente de decisión o de una próxima corrida)

- [ ] T090 Verificación en navegador real (Playwright/Chromium) de las 6 historias, clic a clic. Esta verificación se hizo **a nivel de API** (misma lógica de backend que consume la UI, con datos reales de `WC`, incluyendo escritura+reversión de cada acción) porque el entorno de este agente no tuvo una herramienta de automatización de navegador disponible. El código de `PanelConciliacion.tsx`/`BandejaConciliacion.tsx` fue revisado y coincide con lo verificado por API, pero no hubo clic real en el navegador. Recomendado antes de dar la feature por cerrada del todo.
- [ ] T091 Caso real de Historia 3 (factura USD + nota de ajuste) de punta a punta en la UI — ver T043. No se encontró una línea pendiente real con ese perfil el 2026-09-22.
