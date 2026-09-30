# Tasks: Backfill de boletas de impuestos faltantes (029)

**Input**: spec.md, plan.md, research.md, data-model.md, contracts/api.md y quickstart.md de esta carpeta.
**Estado**: tareas planificadas, ninguna implementada ni validada todavía.
**Pruebas**: incluidas por Constitución V y por el plan/quickstart; fixtures y conexiones simuladas, nunca inserts de prueba en WC.
**Formato**: `[P]` indica trabajo en archivos distintos que puede hacerse en paralelo cuando sus prerrequisitos estén completos. No autoriza delegación por sí solo.

## Fase 1 — Preparación

- [X] T001 Registrar baseline de rama, cambios locales, versiones instaladas y rutas vigentes en `specs/029-backfill-boletas-impuestos/validation.md`; preservar trabajo anterior y no instalar dependencias.
- [X] T002 Crear paquete `backend/src/features/backfill_impuestos/__init__.py` y fixtures aisladas en `backend/tests/fixtures/backfill_impuestos.py` para seis medios, boletas existentes, documentos y operaciones concurrentes; impedir conexiones reales en los tests de escritura.

## Fase 2 — Fundamentos de lectura

Esta fase no ejecuta DDL ni requiere las tablas 029 para el MVP de diagnóstico.

- [X] T003 Relevar con SELECT columnas, claves, signos y reasignaciones de los seis medios y sus ramas contables; documentar correspondencias exactas y el caso Tapalqué en `specs/029-backfill-boletas-impuestos/research.md`; validar consultas contra WC sin exportar datos personales (FR-001/002/014).
- [X] T004 Definir modelos compartidos en `backend/src/features/backfill_impuestos/schemas.py`: identidad `(medio,idMovimiento)`, organismo efectivo, importes «Decimal a 2 decimales», fechas ISO, estados respaldado/probable/faltante/pendiente/excluido con motivo; conservar contratos de `contracts/api.md`, strings monetarios y pageSize 1..200.
- [X] T005 Implementar lecturas allowlist parametrizadas en `backend/src/features/backfill_impuestos/repository.py`, con cursor de la conexión común que preserve Decimal, recorrido por clave en bloques acotados y totales históricos completos; detectar ausencia de tablas 029 expresamente, sin convertir errores SQL en listas vacías.

## Fase 3 — US1: Diagnóstico por organismo (P1, MVP)

**Objetivo**: identificar faltantes, respaldos y pendientes y explicar el saldo sin crear deudas.
**Prueba independiente**: abrir un organismo y conciliar totales históricos y causas; un pago ya respaldado no aparece como faltante, contacto reconocido no se interpreta como boleta y Tapalqué no genera deuda por su saldo cero.

- [X] T006 [P] [US1] Crear casos del motor en `backend/tests/test_backfill_impuestos_diagnostico.py`: signos por medio, devoluciones/retenciones/traspasos, contacto 0, reasignaciones, duplicación nativo-conciliación, parciales, capacidad compartida y límites 0,10/0,01; comprobar inicialmente fallos por comportamiento ausente (FR-001/002, SC-002).
- [X] T007 [P] [US1] Crear pruebas HTTP GET en `backend/tests/contract/test_backfill_impuestos_api.py`: sesión, Lectura, paginación, vacío, SQL no disponible, totales fuera de página y ausencia de escrituras (FR-001/002/013).
- [X] T008 [US1] Implementar `backend/src/features/backfill_impuestos/diagnostico.py`: normalizar pagos, cruzar vínculos Tesorería/Tarjetas/029 y otros respaldos contables, reservar capacidad una sola vez y dejar colisiones/parciales pendientes; excluir pagos sin representación contable fiable sin perderlos del informe (FR-001, SC-002).
- [X] T009 [US1] Implementar resumen y detalle en `backend/src/features/backfill_impuestos/router.py`, montar en `backend/src/main.py` y devolver saldo actual, faltantes, proyección y diferencia pendiente de explicar; probable/faltante/excluido deben seguir visibles como pendientes con motivo en el resumen funcional de SC-002 (FR-002/013).
- [X] T010 [US1] Implementar cliente TanStack Query en `frontend/src/services/backfillImpuestosApi.ts` y diagnóstico en `frontend/src/components/impuestos/BackfillDiagnostico.tsx` con organismo, estados, medio, concepto, fecha, importe ARS y referencia contable; incluir cargando, vacío y error (FR-001/002).
- [X] T011 [US1] Crear ruta `frontend/src/app/finanzas/impuestos/backfill/page.tsx` y acceso desde `frontend/src/app/finanzas/impuestos/page.tsx`; ejecutar pruebas T006/T007 y comprobar navegación de diagnóstico y TypeScript, registrando evidencia en `specs/029-backfill-boletas-impuestos/validation.md`.

**Checkpoint**: diagnóstico utilizable por sí solo, sin migración y sin habilitar confirmaciones.

## Fase 4 — US2: Completar con comprobantes reales (P2)

**Objetivo**: proponer archivos únicos y permitir revisión individual antes de crear boletas.
**Prueba independiente**: con fixtures ARBA, confirmar una selección revisada, abrir el PDF asociado y comprobar que el pago no vuelve a proponerse y que no se duplicó su crédito contable.

- [X] T012 [P] [US2] Crear pruebas de inventario y emparejamiento en `backend/tests/test_backfill_impuestos_propuesta.py`: nombre/fecha/alias, unicidad bidireccional, varios candidatos y resolución manual válida/inválida sin levantar bloqueos financieros, archivo usado/repetido/ilegible, raíces ausentes, enlaces fuera de raíz y límites de recorrido (FR-003/004/006).
- [X] T013 [P] [US2] Crear pruebas transaccionales con conexiones simuladas en `backend/tests/test_backfill_impuestos_repository.py`: rollback entre inserts, UUID repetido/distinto, fuente cambiada, backup rechazado, dos confirmaciones y no modificación de registros previos; agregar casos de reversión de dos boletas en un mismo lote, evidencia/token adulterados, finalidad/usuario incorrectos y respaldo iniciado antes de preparar (FR-008/009/011/012/014).
- [X] T014 [US2] Implementar inventario seguro en `backend/src/features/backfill_impuestos/documentos.py`: raíces Impuestos/Compras configuradas, alias explícitos, fecha válida, ±7 días versionados, deduplicación ruta/hash y exclusión de adjuntos existentes; límite 20.000 archivos/30 segundos, indicador de cobertura incompleta y archivos no reconocidos; identificadores opacos y apertura por raíz canónica (FR-003/004).
- [X] T015 [US2] Implementar propuesta pura en `backend/src/features/backfill_impuestos/propuesta.py`: reserva de archivos global independiente de paginación, sugerencias solo únicas, correcciones y exclusiones individuales, conflictos explícitos, huellas deterministas de fuentes/selección/política y vista previa completa sin persistir borradores (FR-004/006).
- [X] T016 [US2] Definir requests/responses de revisión y confirmación en `backend/src/features/backfill_impuestos/schemas.py`: «1..200 decisiones únicas», UUID, hash, longitudes período/número «nvarchar(255)», fuente comprobante/generada; mantener organismo/fecha/importe autoritativos y usar tipoImpuesto discriminado existente/generico, exclusiones sin tipo/archivo y confirmacionDocumento obligatoria para comprobantes según contrato (FR-005/006/009/013).
- [X] T017 [US2] Preparar migración idempotente en `backend/scripts/crear_tablas_backfill_impuestos.py` para Lotes/Boletas/Vinculos/Eventos según `data-model.md`: «Estado varchar(20) confirmado/revertido», «HuellaPropuesta y HashSolicitud char(64)», «Usuario nvarchar(100)», «BackupId nvarchar(100)», fechas datetime2, «CHECK cantidad positiva, total positivo»; PK/FK, nullable explícitos, una transacción y sin ejecución al arrancar la aplicación (FR-011/012/014).
- [X] T018 [US2] Completar en `backend/scripts/crear_tablas_backfill_impuestos.py` restricciones de Boletas/Vinculos/Eventos: «IdImpuesto int nullable FK Impuestos, con índice UNIQUE filtrado WHERE IdImpuesto IS NOT NULL», «IdImpuestoHistorico int inmutable», «OrigenCreacion varchar(20) comprobante/generada», «TieneComprobante bit», «ArchivoHash char(64) nullable», «SnapshotCreacion nvarchar(max)», «Version rowversion», «Índice UNIQUE `(Medio,IdMovimiento)`», medio varchar(20) allowlist, importe decimal(19,2) positivo y JSON validado; usar para ArchivoHash el filtro WHERE ArchivoHash IS NOT NULL AND IdImpuesto IS NOT NULL, conservar IDs/hash históricos al revertir y probar reversión múltiple antes de ejecutar DDL (FR-008/009/011).
- [X] T019 [US2] Implementar creación y validación de evidencia de backup en `backend/scripts/crear_tablas_backfill_impuestos.py` y `backend/src/features/backfill_impuestos/repository.py`: base WC comprobada, CHECKSUM + VERIFYONLY, evidencia fuera de Git, referencia opaca confiable, archivo existente y verificación posterior a preparación del lote; rechazar booleanos/rutas/SQL del cliente y emitir token firmado de preparación, implementar modo --backup-only y GET /respaldo en `backend/src/features/backfill_impuestos/router.py`, validar evidencia firmada y hash de archivo, ocultar tokens en logs y documentar acceso operativo en `specs/029-backfill-boletas-impuestos/quickstart.md` (FR-012).
- [X] T020 [US2] Agregar GET propuesta/archivo y POST validar al router `backend/src/features/backfill_impuestos/router.py`; revisión no escribe; 404 archivo ausente, 409 archivo cambiado, 422 selección inválida y 503 fuente indisponible; resolver ambiguos documentales solo mediante candidato vigente elegido y confirmado, validar unicidad global y conservar bloqueos financieros según contrato (FR-003/004/006).
- [X] T021 [US2] Implementar confirmación con comprobante en `backend/src/features/backfill_impuestos/repository.py` y `backend/src/features/backfill_impuestos/router.py`: backup antes de transacción, `reconciliation_transaction`, revalidación bajo bloqueo común, idempotencia, inserción Impuestos/procedencia/vínculo/evento/lote atómica y comprobación de filas afectadas; no insertar ConciliacionesTesoreria ni tocar pagos (FR-006/008/009/011/012/013/014).
- [X] T022 [US2] Integrar vínculos 029 en todas las lecturas compartidas de saldo en `backend/src/features/conciliacion_tesoreria/documentos.py`; verificar consumidores de `backend/src/features/tarjetas_resumenes/repository.py` y Tesorería, sin cambiar vista contable ni contar un mismo vínculo dos veces; coordinar activación con T026 (FR-008/009/014).
- [X] T023 [US2] Implementar GET lotes/detalle, prevalidación y reversión en `backend/src/features/backfill_impuestos/router.py` y `backend/src/features/backfill_impuestos/repository.py`: huella, backup, bloqueo, snapshots, identidad y dependencias posteriores; eliminar solo filas propias intactas, preservar auditoría/catálogo y garantizar rollback total ante conflicto (FR-011/014).
- [X] T024 [US2] Extender contratos HTTP en `backend/tests/contract/test_backfill_impuestos_api.py` y regresión en `backend/tests/test_imputacion_documentos.py`: Lectura 403, sesión 401, 201/200 idempotentes, conflictos, preview sin writes, apertura segura y reducción del saldo documental sin segundo crédito; ejecutar T012/T013 y estas pruebas (FR-003/004/006/008/009/011/012/013/014).
- [ ] T025 [US2] Implementar revisión/resultado/lotes en `frontend/src/components/impuestos/BackfillRevision.tsx`, `frontend/src/components/impuestos/BackfillLotes.tsx` y `frontend/src/services/backfillImpuestosApi.ts`; selección por caso, vista previa PDF, exclusiones, correcciones, UUID estable al reintentar, backup visible, confirmación exacta y reversión con motivos de bloqueo; invalidar consultas afectadas (FR-004/006/009/011/012/013).
- [X] T026 [US2] Revisar diff y pruebas, generar respaldo verificado y ejecutar únicamente la migración aditiva preparada de `backend/scripts/crear_tablas_backfill_impuestos.py`; validar esquema por SELECT y registrar evidencia/ruta externa en `specs/029-backfill-boletas-impuestos/validation.md`; activar integración T022 solo con esquema disponible y ninguna carga de boletas implícita (FR-012/014).

**Checkpoint**: US2 utilizable, creación real de boletas pendiente de revisión explícita de la propuesta concreta. T026 prepara esquema, no confirma lotes.

## Fase 5 — US3: Generar desde el pago y mantener procedencia (P3)

**Objetivo**: completar exclusivamente pagos totalmente descubiertos, distinguir generación y permitir adjuntar/corregir después.
**Prueba independiente**: generar en fixtures una boleta por total del pago, repetir sin duplicar, ver marca en Impuestos/cuenta, adjuntar documento y conservar origen histórico.

- [X] T027 [P] [US3] Agregar pruebas en `backend/tests/test_backfill_impuestos_generadas.py`: una boleta por pago multicuota, fecha/importe originales, tipo genérico simbólico sin ID y sin escrituras en preview, exclusiones sin tipo, cobertura documental incompleta, adjunto posterior, filtros, versiones y protección de preexistentes (FR-005/007/010/014/015).
- [X] T028 [US3] Extender `backend/src/features/backfill_impuestos/propuesta.py` con generación solo tras búsqueda completa sin archivo y pago totalmente descubierto; inferir tipo por conceptos explícitos, fallback «Sin identificar (generada desde el pago)», período/número NULL si desconocidos; no generar por parciales o ambigüedades (FR-005/006/015).
- [X] T029 [US3] Extender confirmación en `backend/src/features/backfill_impuestos/repository.py` para tipo genérico único por organismo bajo bloqueo y boleta total con origen generado; resolver referencia al tipo genérico sin escribir durante propuesta; auditar tipo creado y conservarlo al revertir (FR-005/007/008/009/014/015).
- [X] T030 [US3] Implementar PATCH tipo/comprobante en `backend/src/features/backfill_impuestos/router.py` y `backend/src/features/backfill_impuestos/repository.py`: solo boletas 029, tipo del mismo organismo, versión obligatoria, archivo no usado y evento antes/después; retirar marca visible al adjuntar manteniendo OrigenCreacion inmutable (FR-007/010/014/015).
- [X] T031 [US3] Ampliar listado/filtros y modelos de `backend/src/features/impuestos/repository.py`, `backend/src/features/impuestos/schemas.py` y `backend/src/features/impuestos/router.py` con metadatos aditivos, versión, sinIdentificar y generadaDesdePago; conservar filas/importes previos y contratos GET (FR-007/015).
- [X] T032 [US3] Enriquecer por clave única los movimientos Impuestos en `backend/src/features/cuentas_corrientes/repository.py` y `backend/src/features/cuentas_corrientes/schemas.py`, sin alterar vista, número, importes ni multiplicar filas; probar marca actual y ausencia tras adjunto en `backend/tests/test_backfill_impuestos_generadas.py` (FR-007/010).
- [ ] T033 [US3] Extender `frontend/src/components/impuestos/ImpuestosListado.tsx` y `frontend/src/services/impuestosApi.ts` con filtros, marca, cambio de tipo y adjunto posterior; mostrar procedencia en `frontend/src/components/cuentas-corrientes/OrigenMovimiento.tsx` y tipos de `frontend/src/services/cuentasCorrientesApi.ts`; integrar flujo generado en `frontend/src/components/impuestos/BackfillRevision.tsx` (FR-005/007/010/015).
- [X] T034 [US3] Ejecutar pruebas T027 y ampliar `backend/tests/contract/test_backfill_impuestos_api.py` para PATCH, versión obsoleta, tipo ajeno, adjunto ya usado, preexistente protegido y huella cambiada; verificar catálogo genérico y repetir propuesta sin crear nada nuevo (FR-005/007/009/010/014/015, SC-003/004).

## Fase 6 — Validación transversal y entrega

- [ ] T035 Ejecutar suite focalizada 029, regresiones de Tesorería/Tarjetas, TypeScript y navegación autenticada de los tres recorridos; registrar resultados reales, vacíos/errores y comandos en `specs/029-backfill-boletas-impuestos/validation.md`, sin pruebas de escritura en datos reales (SC-002/003/004/006).
- [ ] T036 Medir revisión y confirmación simulada de un organismo representativo, incluyendo paginación, ambiguos y varios lotes cuando exceda 200 pagos; registrar tamaño del caso, tiempo efectivo y tratamiento del tiempo de backup en `specs/029-backfill-boletas-impuestos/validation.md`; contrastar SC-005 sin declarar cumplimiento por mera existencia de UI.
- [X] T037 Producir diagnóstico real y propuesta de solo lectura con el módulo `backend/src/features/backfill_impuestos/` para los seis organismos, exponer filas revisables por UI, registrar solo resumen no sensible en `specs/029-backfill-boletas-impuestos/validation.md` y presentar a Sergio las selecciones y diferencias concretas antes de cargar (FR-001/002/006, SC-001/002).
- [ ] T038 Solo tras revisión explícita de la propuesta concreta, confirmar los lotes seleccionados mediante `backend/src/features/backfill_impuestos/router.py` con respaldo verificado; hacer SELECT posterior para contrastar deuda agregada/crédito intacto, repetir diagnóstico y documentar pendientes/reversión disponible en `specs/029-backfill-boletas-impuestos/validation.md`; dejar abierta si falta revisión, nunca inferirla de la aprobación del desarrollo (FR-006/009/011/012/014, SC-001/004).
- [ ] T039 Actualizar instrucciones operativas y estado real en `specs/029-backfill-boletas-impuestos/quickstart.md`, revisar diff sin secretos/binarios/backups y marcar únicamente tareas cuya implementación y verificaciones estén completas en `specs/029-backfill-boletas-impuestos/tasks.md`; no publicar ni hacer push implícitos.

## Dependencias y orden

`T001 → T002 → T003 → T004 → T005 → US1 (T006–T011) → US2 (T012–T026) → US3 (T027–T034) → cierre (T035–T039)`.

Dentro de cada historia: fixtures/pruebas → lógica → API → integración → UI validada. T006/T007 y T012/T013 son independientes entre sí. T014 y T017 pueden desarrollarse en ramas de trabajo separadas tras sus prerrequisitos, pero no se marca T017 [P] porque comparte el script con T018/T019. T022 se prueba con mocks antes de T026, y no debe desplegarse contra tablas ausentes. T023 depende de T018/T021; T025 depende de contratos backend verificados en T024. T027 puede elaborarse sobre fixtures existentes mientras se prepara US3, pero su suite debe pasar tras T028–T033. T038 depende de revisión de lote y respaldo, no solo de tareas técnicas completas.

## Ejemplos de trabajo paralelo

- US1: T006 (motor de diagnóstico) y T007 (contrato GET), tras T005; archivos distintos.
- US2: T012 (archivos/propuesta) y T013 (transacciones), tras US1; archivos distintos.
- US3: preparación de T027 puede acompañar revisión manual del contrato de T028; no editar simultáneamente repository/router compartidos. No hay dos tareas de implementación US3 marcadas [P] porque comparten archivos y dependencias.

## Estrategia incremental

MVP = T001–T011: diagnóstico de solo lectura. Validarlo antes de habilitar creación. US2 incorpora infraestructura de carga y reversión reutilizada por US3. US3 amplía con generación, procedencia y mantenimiento. Validar cada historia con fixtures; presentar propuesta concreta al terminar el código. La revisión final del lote es independiente de autorizar implementación.

## Cobertura prevista

| Requisito | Tareas principales |
|---|---|
| FR-001 | T003, T005–T011, T037 |
| FR-002 | T008–T011, T037 |
| FR-003 | T012, T014, T020, T024 |
| FR-004 | T012, T014–T015, T020, T025 |
| FR-005 | T027–T029, T033–T034 |
| FR-006 | T015–T016, T020–T021, T025, T037–T038 |
| FR-007 | T027, T029–T034 |
| FR-008 | T013, T018, T021–T022, T029 |
| FR-009 | T013, T016, T018, T021–T022, T034, T038 |
| FR-010 | T027, T030, T032–T034 |
| FR-011 | T013, T017–T018, T021, T023, T025 |
| FR-012 | T017, T019, T021, T026, T038 |
| FR-013 | T007, T009, T016, T024–T025 |
| FR-014 | T003, T013, T021–T026, T030, T038 |
| FR-015 | T027–T031, T033–T034 |
| SC-001 | T037–T038 (resultado posterior a revisión, no logrado aún) |
| SC-002 | T006, T008–T009, T035, T037 |
| SC-003 | T027, T031–T035 |
| SC-004 | T013, T034–T035, T038 |
| SC-005 | T025, T033, T036 (medición, no garantía previa) |
| SC-006 | T012, T014–T015, T020, T024–T025, T035 |
