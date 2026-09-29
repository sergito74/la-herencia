# Tasks: Conciliación de Tesorería con documentos

**Input**: `specs/026-conciliacion-tesoreria-documentos/`: spec.md, plan.md, research.md, data-model.md, contracts/, quickstart.md y review.md.
**Organización**: tres historias, US1 P1, US2 P1, US3 P2; todos los medios en cada incremento.
**Verificaciones**: comprobaciones enfocadas exigidas por Constitución V y plan.md (pytest de contrato/repository y TypeScript). Usar mocks/fixtures para escrituras; WC es producción.
**Formato**: `- [ ] TNNN [P?] [USn?] Descripción con ruta`. `[P]` indica archivos independientes dentro de la etapa indicada, una vez cumplidas sus dependencias. Ninguna casilla representa trabajo ya implementado.

## Phase 1: Setup — cerrar revisión del diseño

**Objetivo**: dejar decisiones coherentes y ejecutables antes del DDL y del código. No crear proyecto ni instalar dependencias: ambos ya existen. Los hallazgos R01–R12 están detallados en review.md.

- [x] T001 Resolver R01, R04–R08 y R11 en `specs/026-conciliacion-tesoreria-documentos/spec.md`, `research.md`, `data-model.md` y `quickstart.md`: continuidad del parcial, revocación auditable, diferencia de ambos signos, saldo compartido con Tarjetas, NC y fixtures; preservar las aclaraciones aprobadas y solicitar únicamente decisiones funcionales que no puedan inferirse. Registrar reglas de saldo/moneda y efecto contable con ejemplos numéricos; no dejar estas decisiones al implementar.
- [x] T002 Completar `specs/026-conciliacion-tesoreria-documentos/contracts/conciliacion-tesoreria-documentos-api.md` tras T001: identidad compuesta en selección/sugerencias/imputados, serialización exacta del preview, GET de estado con auditoría, revocación y errores 400/404/409/422, autenticación/permisos, límites concretos de búsqueda/candidatos/selección y comportamiento sin contacto; resolver R02, R05, R06 y R10 sin alterar el POST manual existente.
- [x] T003 Actualizar `specs/026-conciliacion-tesoreria-documentos/plan.md`, `research.md`, `review.md` y este `tasks.md` tras T001–T002: corregir R03/R12, describir adaptador y transacción de R09, enumerar archivos afectados y desglosar cambios adicionales si R07/R08 los requieren; marcar cada hallazgo resuelto con su decisión. Gate: no iniciar Phase 2 con decisiones bloqueantes abiertas ni declarar el diseño conforme sin evidencia.

## Phase 2: Foundational — esquema y contratos comunes

**Gate**: Phase 1 completa. El núcleo compartido debe estar listo antes de las historias.

- [X] T004 Preparar `backend/scripts/extender_conciliaciones_tesoreria_documentos.py` idempotente con resguardo WC: columnas `TipoOrigenDocumento` «varchar(20), NULL» y `IdOrigenDocumento` «bigint, NULL», catálogo «Compras | Impuestos | Remuneraciones | Alquileres | NULL» y regla «ambos NULL o ambos con valor» en repository; crear tabla de eventos e índices por movimiento y documento según T001, preservando filas manuales existentes.
- [X] T005 Registrar en `specs/026-conciliacion-tesoreria-documentos/quickstart.md` validación de solo lectura del esquema real de los cuatro orígenes, restricciones/índices y vista de cuentas corrientes; obtener y verificar backup de WC antes de aplicar `backend/scripts/extender_conciliaciones_tesoreria_documentos.py`, registrar resultado e idempotencia y procedimiento de reversión sin borrar historial. No ejecutar DDL si falta backup verificado.
- [X] T006 [P] Definir schemas compartidos en `backend/src/features/conciliacion_tesoreria/schemas.py` según T002: documento con origen e ID, importes/moneda, referencia compuesta, conciliación con columnas nullable, cálculo y auditoría. Campos del evento: `IdEstado` «int identity, PK», `Medio` «varchar(20)» con los seis medios, `IdMovimiento` «bigint», `Estado` «varchar(20)», `Motivo` «varchar(30)», `Detalle` «nvarchar(255), NULL», `ImporteDiferencia` «money, NULL», `Usuario` «nvarchar(100)», `Fecha` «datetime, default getdate()»; incorporar explícitamente el mecanismo de revocación definido en T001.
- [X] T007 [P] Implementar adaptador local en `backend/src/features/conciliacion_tesoreria/documentos_adapter.py`: mapear `(origen,idOrigen)` a claves internas únicas para `calcular_imputacion`/`sugerir`, revertir resultados a la identidad pública y usar saldos disponibles en la moneda definida por T001; conservar TC y signos sin colisiones ni duplicar fórmulas de `backend/src/features/tarjetas_resumenes/conciliacion_documentos.py`.
- [X] T008 Implementar en `backend/src/features/conciliacion_tesoreria/repository.py` el mecanismo transaccional definido en T003 usando resguardos de `backend/src/db/connection.py`: lecturas/revalidación bajo la misma conexión y bloqueos hasta commit, orden estable de movimiento/documentos y rollback completo; mantener parametrización y no ampliar permisos SQL generales para sortear los resguardos.

## Phase 3: US1 — buscar y elegir documentos (P1, MVP de consulta)

**Objetivo**: búsqueda principal, candidatos y selección para los seis medios.
**Prueba independiente**: abrir movimiento ML sin contacto, buscar proveedor/número, ver saldo y origen de los cuatro tipos, seleccionar coincidencia; repetir con fixtures de los otros cinco medios. Guardar el lote se entrega en US2.

- [X] T009 [P] [US1] Añadir pruebas de GET búsqueda/candidatos en `backend/tests/contract/test_conciliacion_tesoreria_documentos_api.py`: seis medios, filtros/límites, identidades con IDs coincidentes, respuesta vacía, errores y bloqueo de movimientos resueltos; permitir continuar parcial según T001.
- [X] T010 [P] [US1] Añadir pruebas de consultas/adaptador en `backend/tests/test_conciliacion_tesoreria_documentos_repository.py`: cuatro orígenes, importes y contraparte correctos, saldo según T001, documentos sin contacto, claves repetidas entre tablas, TC, sugerencias exactas y límites combinatorios sin acceso de escritura a WC.
- [X] T011 [US1] Implementar búsqueda parametrizada y acotada de cuatro ramas en `backend/src/features/conciliacion_tesoreria/repository.py`: Compras vía vista de importe bruto, Impuestos por IdOrganismo, Remuneraciones por suma vigente de conceptos y Alquileres por cuota/IdCobroAlquiler; devolver todos los campos de T002 y calcular saldo/vínculos según T001, sin modificar tablas de origen ni Estado de cuota.
- [X] T012 [US1] Implementar candidatos en `backend/src/features/conciliacion_tesoreria/repository.py`: usar importe pendiente/fecha para movimientos sin contacto, ordenar y limitar candidatos antes de sugerir con el adaptador; conservar búsqueda libre y aplicar exclusión por otra vía sin impedir la continuación parcial.
- [X] T013 [US1] Exponer `GET /documentos-buscar` y `GET /{medio}/movimientos/{id}/candidatos` en `backend/src/features/conciliacion_tesoreria/router.py` con modelos T006, trabajo SQL en threadpool, errores de T002 y rutas estáticas sin colisiones con routers existentes.
- [X] T014 [US1] Extender `frontend/src/services/conciliacionTesoreriaApi.ts` con tipos y llamadas de búsqueda/candidatos, identidad compuesta y claves de consulta por medio/movimiento/filtro; conservar las funciones manuales existentes.
- [X] T015 [US1] Extender `frontend/src/components/tesoreria/ConciliarMovimiento.tsx` con pestaña principal de documentos, búsqueda, selección múltiple y sugerencias, mostrando fecha, moneda, importe y saldo; mantener pestaña manual y cubrir carga/vacío/error/acceso de solo lectura. Verificar T009–T010 y registrar evidencia de US1 en `specs/026-conciliacion-tesoreria-documentos/quickstart.md`.

## Phase 4: US2 — preview y reparto automático (P1)

**Objetivo**: confirmar uno o varios documentos con reparto y continuar conciliaciones parciales.
**Prueba independiente**: fixture de $3.717,61 y tres documentos de US2; suma imputada exacta a centavos, reparto proporcional, saldo documental reducido; con menos documentos que importe, agregar un segundo lote sobre el residual. No mezclar fixture con cifras reales del quickstart.

- [X] T016 [P] [US2] Añadir pruebas de preview/lote en `backend/tests/contract/test_conciliacion_tesoreria_documentos_api.py`: identidades compuestas, selección vacía/duplicada/excesiva, 201, documento inexistente 404, conflicto 409 y POST manual compatible, para los seis medios.
- [X] T017 [P] [US2] Añadir pruebas de reparto y concurrencia en `backend/tests/test_conciliacion_tesoreria_documentos_repository.py`: exacto, proporcional, redondeo, TC, saldo ya consumido, signos según T001, continuación parcial, rollback y dos confirmaciones competidoras por movimiento y documento; probar lectura/revalidación dentro de la transacción, no solo recalcular antes del INSERT.
- [X] T018 [US2] Implementar preview en `backend/src/features/conciliacion_tesoreria/repository.py` sobre el saldo restante real y documentos vigentes con el adaptador; validar duplicados, orígenes e IDs y devolver imputados con referencia compuesta, diferencia y pistas de TC según T002, sin escrituras.
- [X] T019 [US2] Implementar lote atómico en `backend/src/features/conciliacion_tesoreria/repository.py`: recargar movimiento/documentos bajo T008, obtener contacto desde cada origen, recalcular reparto y disponibilidad, insertar metadata de documento y usuario autenticado; conservar suma e integración existente en cuentas corrientes y rechazar conflictos sin guardar partes del lote.
- [X] T020 [US2] Coordinar guardas/transacciones de la vía manual en `backend/src/features/conciliacion_tesoreria/repository.py` y traspasos en `backend/src/features/traspasos_internos_tesoreria/repository.py` con el lote según T003, evitando carreras entre vías; mantener manual con ambas columnas NULL, parcial continuable y ausencia de importaciones circulares.
- [X] T021 [US2] Exponer preview y POST lote en `backend/src/features/conciliacion_tesoreria/router.py` según T002, extender GET conciliación con metadata nullable y preservar entrada/salida compatible del POST manual; pasar usuario del servidor, nunca del body.
- [X] T022 [US2] Añadir llamadas/tipos preview y lote en `frontend/src/services/conciliacionTesoreriaApi.ts` e integrar en `frontend/src/components/tesoreria/ConciliarMovimiento.tsx`: preview antes de confirmar, montos automáticos, estado parcial persistente, errores de concurrencia y actualización de búsqueda/saldos/listado/cuentas corrientes. Ejecutar T016–T017 y registrar resultado en `specs/026-conciliacion-tesoreria-documentos/quickstart.md`.

## Phase 5: US3 — diferencia con motivo y sin documento (P2)

**Objetivo**: cerrar excepciones explícitamente y conservar su auditoría.
**Prueba independiente**: diferencia pequeña aceptada como Impuesto cierra y muestra motivo/detalle/usuario/fecha; Otro sin detalle falla; SinDocumento sale de pendientes; quitar estado recalcula desde vínculos conservados.

- [X] T023 [P] [US3] Añadir pruebas de contrato de aceptarDiferencia, sin-documento, GET auditoría y DELETE estado en `backend/tests/contract/test_conciliacion_tesoreria_documentos_api.py`: motivos, límites de strings, detalle requerido, usuario del servidor, permisos y errores definidos en T002.
- [X] T024 [P] [US3] Añadir pruebas de eventos/resolución en `backend/tests/test_conciliacion_tesoreria_documentos_repository.py`: última fila por IdEstado, cierre de parcial por diferencia, revocación sin borrar historia, ambos signos, bloqueo simétrico con manual/lote/traspaso y saldo derivado después de revocar según T001.
- [X] T025 [US3] Implementar validaciones y eventos en `backend/src/features/conciliacion_tesoreria/repository.py`: Estado «SinDocumento | DiferenciaAceptada» más revocación según T001; motivos SinDocumento «Impuesto|Interes|CompraNoCargada|Otro» y DiferenciaAceptada «AjusteTipoCambioSinNota|Redondeo|Impuesto|Otro»; Detalle «obligatorio cuando Motivo = 'Otro'» y máximo 255, ImporteDiferencia «solo para DiferenciaAceptada»; usuario máximo 100 obtenido del servidor y fecha registrada por SQL. Guardar diferencia y lote en la misma transacción.
- [X] T026 [US3] Integrar eventos vigentes en `backend/src/features/conciliacion_tesoreria/repository.py` y `backend/src/features/tesoreria/estado_resolucion.py`: diferencia aceptada cierra incluso con imputación parcial; SinDocumento devuelve `sin_documento`; revocación recalcula sin borrar vínculos; conservar seis estados públicos y prioridad definida en T001, sin ciclo de imports.
- [X] T027 [US3] Implementar POST sin-documento y DELETE estado en `backend/src/features/conciliacion_tesoreria/router.py`, ampliar GET con auditoría y aceptarDiferencia en lote según T002; revocar mediante el mecanismo insert-only acordado, responder 204 y mantener guardas sobre las otras vías.
- [X] T028 [US3] Propagar `sin_documento` y auditoría en `backend/src/features/tesoreria/schemas.py`, `backend/src/features/tesoreria/repository.py`, `frontend/src/services/tesoreriaApi.ts` y `frontend/src/services/conciliacionTesoreriaApi.ts`; verificar que listados, filtros y acción de traspasos interpreten el mismo estado y no ofrezcan resolver dos veces.
- [X] T029 [US3] Añadir acciones y auditoría en `frontend/src/components/tesoreria/ConciliarMovimiento.tsx`: elegir explícitamente continuar parcial o aceptar diferencia, motivo/detalle, marcar sin documento y quitar estado; actualizar `frontend/src/components/tesoreria/VincularTraspasoInterno.tsx` si su guarda enumera estados y refrescar caches afectadas. Ejecutar T023–T024 y registrar resultado en `specs/026-conciliacion-tesoreria-documentos/quickstart.md`.

## Phase 6: Polish — integración y evidencia

- [X] T030 Verificar regresión con `backend/tests/contract/test_conciliacion_tesoreria_api.py`, `backend/tests/test_conciliacion_tesoreria_repository.py`, `backend/tests/contract/test_traspasos_internos_tesoreria_api.py`, `backend/tests/test_traspasos_internos_tesoreria_repository.py` y `backend/tests/test_conciliacion_documentos.py`, además de los dos archivos nuevos de 026; inspeccionar fixtures antes de ejecutar para evitar escrituras en producción y registrar comandos/resultados en `specs/026-conciliacion-tesoreria-documentos/quickstart.md`.
- [X] T031 [P] Ejecutar `tsc --noEmit` desde `frontend/` y verificar UI de los seis medios con estados vacío/error/parcial/resuelto y permisos, según `frontend/src/components/tesoreria/ConciliarMovimiento.tsx` y `frontend/src/components/tesoreria/MovimientosPorMedio.tsx`; registrar resultados en `specs/026-conciliacion-tesoreria-documentos/validation.md`.
- [X] T032 Verificar FR-007 mediante lectura acotada de la definición vigente de `vw_MovimientosCuenta_Base` y fixtures de integración en `backend/tests/test_conciliacion_tesoreria_documentos_repository.py`: importe/contacto/signo, metadata documental sin duplicar asientos y conciliación manual intacta; documentar la evidencia en `specs/026-conciliacion-tesoreria-documentos/quickstart.md`.
- [X] T033 Medir SC-002 sobre el corpus definido en T002 y completar SC-001/003/004 en `specs/026-conciliacion-tesoreria-documentos/quickstart.md`: denominador, coincidencias y porcentaje, escenarios de Tarjetas+ML y limitaciones verificadas; no declarar ≥90% sin medición ni escribir sobre registros reales para simular pruebas.
- [X] T034 Revisar diff, conservar sin cambios el checklist de calidad y actualizar `review.md`, `plan.md` y `tasks.md` con decisiones/evidencias finales; cerrar solo tareas verificadas y confirmar ausencia de secretos, backups, bases y artefactos generados en los cambios. Preservar trabajo local de otras features.

## Dependencies & Execution Order

```text
T001 → T002 → T003 → T004 → T005
                         ├→ T006 ─┐
                         ├→ T007 ─┼→ T008 → US1 → US2 → US3 → Phase 6
                         └────────┘
```

T008 requiere T005–T007. T006/T007 pueden prepararse mientras se verifica el esquema T005, pero ninguna historia comienza antes de cerrar Phase 2. Dentro de cada historia, pruebas primero, repository antes de endpoints y endpoints antes de integración UI. Ejecutar las pruebas enfocadas al terminar cada historia. Las historias comparten archivos y dependen funcionalmente entre sí: no implementarlas en paralelo sobre el mismo repository o componente.

US1 se verifica como consulta/selección independiente tras fundamentos. US2 usa US1 y se verifica con fixtures propias de reparto. US3 usa US2 para diferencias y se verifica con fixtures de eventos. Phase 6 comienza tras las tres historias. T030 y T031 pueden correr en paralelo porque sus verificaciones y archivos de evidencia son distintos; T032–T034 son secuenciales después.

## Parallel examples

- **US1**: T009 (contrato API) y T010 (repository/adaptador), ambos tras Phase 2, en archivos distintos.
- **US2**: T016 (contrato preview/lote) y T017 (reparto/concurrencia), ambos tras US1.
- **US3**: T023 (contrato estados) y T024 (eventos/resolución), ambos tras US2.
- **Fundamentos**: T006 (schemas) y T007 (adaptador) después de T003; no modificar ambos el mismo archivo.

## Implementation strategy

1. Cerrar primero las inconsistencias de diseño; T003 debe actualizar esta lista si una decisión necesita más archivos o tareas. No disimular una decisión pendiente como un detalle de implementación.
2. Completar fundamentos y US1 como MVP de búsqueda/selección en los seis medios. Una conciliación documental completa requiere US1 + US2.
3. Entregar reparto/continuación en US2 y excepciones auditadas en US3, verificando cada incremento antes de seguir.
4. Completar regresión, medición y revisión final. La generación de esta lista no ejecuta migraciones ni acredita implementación.

## Cobertura y recuento

34 tareas: Setup 3, Foundational 5, US1 7, US2 7, US3 7, Polish 5. FR-001/002 → US1; FR-003/007/008/009 → US2 y verificaciones finales; FR-004/005 → US3; FR-006 → las tres historias y T020/T026/T028. SC-001/003/004 → pruebas independientes; SC-002 → T002/T033.

## Ampliación necesaria confirmada en T003

T004 incluye la restricción de importes negativos de Compras; T011 usa documentos.py para consulta y saldo compartido. T008/T020 incluyen contexto transaccional en db/connection.py y coordinación con todas las vías de vinculación/reparto de tarjetas_resumenes/repository.py; T019 incluye guardas de saldo común también del lado Tarjetas. No se cambia conciliacion_documentos.py. T030 agrega pruebas de saldo cruzado y transacciones. T033 informa por separado corpus de fixtures y ausencia de corpus real etiquetado, sin afirmar rendimiento real no medido.
