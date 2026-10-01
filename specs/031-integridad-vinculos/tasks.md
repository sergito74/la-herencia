# Tasks: Integridad de vínculos entre pagos y documentos

**Input**: Design documents from `/specs/031-integridad-vinculos/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md, quickstart.md

**Tests**: se incluyen. La constitución (V) exige tests de las reglas antes de cualquier escritura sobre datos reales.

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Setup

- [X] T001 Crear el paquete `backend/src/features/vinculos/__init__.py` y registrar el router (vacío) en `backend/src/main.py` con el prefijo `/api/integridad-vinculos`.
- [X] T002 [P] Crear `frontend/src/services/integridadVinculosApi.ts` con los tipos `Vinculo`, `HallazgoIntegridad`, `Lote` e `ItemLote`, según [contracts/api.md](contracts/api.md).

---

## Phase 2: Foundational (fuente unificada, solo lectura)

**⚠️ CRITICAL**: US1, US2 y US3 dependen de esta fase.

- [X] T003 [P] Tests puros en `backend/tests/test_vinculos_fuente_cadenas.py`:
  - Un débito de resumen hereda los consumos × (pago / total del resumen), y lo no imputado queda como pendiente.
  - Cheque ↔ débito: empareja por número de cheque contenido en el concepto ("48HS. BANCOS 003620071", "Echeq Galicia Nro: 120"), importe ±0,01 y débito ≥ emisión. Con dos candidatos elige el de fecha más cercana.
  - Una aplicación directa desde un débito de la cadena del mismo documento se excluye y se marca.
  - Un documento en us$ se pesifica con `[Tipo de Cambio]` de la factura.
  - Las aplicaciones anuladas nunca cuentan.
  - Una factura con un consumo imputado cuyo resumen todavía no se pagó figura pagada a nivel documento, pero no aparece en ningún movimiento.
- [X] T004 Implementar `backend/src/features/vinculos/fuente.py`: carga en bloque de las 5 vías → lista de `Vinculo`. Campos: `via`, `origenMovimiento`, `idMovimiento`, `tipoDocumento`, `idDocumento`, `importeArs`, `fechaPago`, `idRegistro`, `cadena`. Las vías son:
  - `AplicacionesPago` con `Anulada=0`;
  - `Tarjetas_Resumenes_Pagos` + `Tarjetas_Resumenes_Lineas` + `Tarjetas_Resumenes_Lineas_Compras`;
  - `ConciliacionesTesoreria`;
  - `BackfillImpuestosVinculos`.

  Son 5 consultas como máximo, sin consultas por fila.

  Cada vínculo lleva su `nivel` (FR-017):
  - Los consumos imputados y las conciliaciones de cheques son de nivel `documento`, aunque no haya débito.
  - Los pagos de resumen y los débitos de cheque emparejados producen los vínculos de nivel `movimiento`.

  `ConciliacionesTesoreria` con `Medio='valores-propios'` es vía `valor-propio`; el resto de los medios es vía `tesoreria`.
- [X] T005 Implementar `backend/src/features/vinculos/cadenas.py`:
  - `emparejar_cheques(debitos, valores)`;
  - `repartir_resumen(pago, consumos_imputados, total_resumen)`;
  - `excluir_redundantes(vinculos)`, que devuelve `(vigentes, redundantes)`;
  - `pagado_por_documento(vinculos)`, que usa solo el nivel `documento`;
  - `documentos_de_movimiento(vinculos)`, que usa solo el nivel `movimiento`.

  La `fechaPago` de tarjeta y de cheque es la fecha del débito (FR-015). Deja pasar T003.
- [X] T006 Agregar en `backend/src/features/vinculos/fuente.py` la función `total_documento_ars(tipo, id)` en bloque: `vw_Cns_Total_Compra.GranTotal` × TC si `Moneda='Dolares'`, más los totales de ventas con `calcular_totales` (hacienda) y granos, los importes de las boletas de impuesto y el neto de las liquidaciones de sueldo. Un documento sin total calculable queda fuera de `documento-excedido` y se informa aparte.

**Checkpoint**: se puede consultar "cuánto está pagado cada documento" y "qué documentos paga cada movimiento", contando todas las vías.

---

## Phase 3: User Story 1 - Cada pago con todos sus vínculos, una sola vez (P1) 🎯 MVP

**Goal**: el flujo 030 y el saldo por factura leen de la fuente unificada.

**Independent Test**: un "Pago Visa" vinculado a su resumen aparece repartido por los rubros de las facturas del resumen, con vía `tarjeta`, y no en "Pendiente de aplicar".

- [X] T007 [P] [US1] Tests en `backend/tests/test_flujo_caja_rubro_partes.py`:
  - Un débito de resumen se reparte por los rubros de las compras de sus consumos.
  - Un débito de cheque hereda la compra del cheque.
  - Un vínculo de `ConciliacionesTesoreria` a un impuesto o a un sueldo cae en su rubro.
  - La suma de las partes sigue siendo igual al movimiento.
- [X] T008 [US1] En `backend/src/features/flujo_caja/repository.py` (`atribuir_movimientos`), reemplazar `aplicaciones_vigentes_por_movimiento()` por `vinculos.documentos_de_movimiento(...)`. Adaptar `atribucion.partes_desde_aplicaciones` para aceptar los tipos `Impuesto` y `Remuneracion` (rubro del tipo de impuesto y "Sueldos", respectivamente) y agregar `via` en cada parte.
- [X] T009 [US1] En `backend/src/features/aplicaciones_pago/documentos.py`, calcular `saldoPendiente` con `vinculos.pagado_por_documento` en lugar de sumar solo `AplicacionesPago`. El saldo de documentos en us$ se expresa en pesos.
- [X] T010 [US1] En `backend/src/features/aplicaciones_pago/sugerencia.py`, agregar dos filtros a `sugerir`:
  - solo candidatos con fecha de documento ≤ fecha del movimiento + 60 días;
  - comparar en pesos.

  Test nuevo en `backend/tests/test_aplicaciones_pago_sugerencia.py`: un movimiento de 2019 no sugiere una factura de 2023.
- [X] T011 [US1] Mostrar `via` en el detalle de `frontend/src/components/flujo-caja/FlujoCajaRubro.tsx` (columna "Vía": Aplicación / Tarjeta / Cheque / Tesorería / Impuesto).
- [X] T012 [US1] Validar sobre WC: los pagos de resumen con consumos imputados (≈ $31 M) dejan "Pendiente de aplicar" (SC-002), y SC-002 de 030 (el neto total) sigue igual.

**Checkpoint**: el flujo refleja todos los vínculos. El sugeridor ya no produce aplicaciones incoherentes.

---

## Phase 4: User Story 3 - Control de integridad (P2)

Va antes que US2 porque es solo lectura y da la línea de base que US2 corrige.

**Goal**: listar los hallazgos por categoría.

**Independent Test**: una doble imputación simulada aparece en el control con total, imputado por vía y exceso.

- [X] T013 [P] [US3] Tests en `backend/tests/test_vinculos_control_correccion.py` para `control.hallazgos(vinculos, totales, movimientos)`. Categorías:
  - `documento-excedido` (> 2%);
  - `movimiento-excedido`;
  - `doble-imputacion`;
  - `fecha-incoherente` (> 60 días antes, sin contar las manuales);
  - `moneda-mezclada` (documento en us$, movimiento en pesos, importe aplicado ≈ saldo en us$).
- [X] T014 [US3] Implementar `backend/src/features/vinculos/control.py` y `GET /api/integridad-vinculos/control` en `backend/src/features/vinculos/router.py` + `schemas.py`. El filtro `categoria` es opcional y los totales vienen siempre.
- [X] T015 [P] [US3] Contract test `backend/tests/contract/test_integridad_vinculos_api.py::test_control` con monkeypatch de la fuente.
- [X] T016 [US3] Pantalla `frontend/src/app/finanzas/integridad-vinculos/page.tsx` + `frontend/src/components/integridad/ControlIntegridad.tsx`:
  - tarjetas con los totales por categoría;
  - tabla de hallazgos con importes en formato de moneda del sistema y enlace al documento.

  Agregar la entrada "Integridad de vínculos" en Finanzas, en `frontend/src/components/layout/NavHeader.tsx`.
- [X] T017 [US3] Medir sobre WC y registrar la línea de base en `specs/031-integridad-vinculos/quickstart.md`. El tiempo debe ser menor a 10 s (SC-005).

---

## Phase 5: User Story 2 - Revisar y corregir las aplicaciones erróneas (P1)

**Goal**: lotes revisables con backup, anulación sin borrar, reemplazos y reversión.

**Independent Test**: se aplica un lote y queda anulado con motivo y backup; después se revierte y todo vuelve al estado anterior.

- [X] T018 [US2] Script `backend/scripts/crear_tablas_031.py`:
  - Backup `COPY_ONLY, CHECKSUM` + `RESTORE VERIFYONLY` de WC; si falla, abortar.
  - Crear `CorreccionVinculosLote` con: `IdLote` int identity PK, `Estado` varchar(20) (`propuesto|aplicado|revertido|descartado`), `FechaPropuesta` datetime2, `FechaAplicado`/`FechaRevertido` datetime2 null, `Usuario` varchar(100), `BackupArchivo` varchar(400) null, `Resumen` nvarchar(max).
  - Crear `CorreccionVinculosItem` con: `IdItem` int identity PK, `IdLote` FK, `Grupo` varchar(40), `Accion` varchar(20) (`anular|pesificar|reemplazo`), `IdAplicacion` int null, `OrigenMovimiento`, `IdMovimientoOrigen`, `TipoDocumento`, `IdDocumento`, `Importe`, `Motivo` nvarchar(400), `Candidatos` nvarchar(max) null, `Incluido` bit default 1, `Elegido` bit, `IdAplicacionCreada` int null.
  - Ejecutarlo solo contra WC.
- [X] T019 [P] [US2] Tests en `backend/tests/test_vinculos_control_correccion.py` para `correccion.proponer(hallazgos, vinculos)`:
  - Nunca incluye `Origen='manual'`.
  - Moneda mezclada → `pesificar`.
  - Doble imputación → `anular`, y el movimiento liberado busca una factura.
  - Fecha incoherente → `anular` + reemplazo, en ambos sentidos (FR-016).
  - El reemplazo exige: mismo contacto, fecha dentro del margen y saldo libre del candidato ≥ importe (±2%).
  - Dentro del lote, cada candidato se reserva para un único reemplazo.
  - Con más de un candidato el reemplazo es ambiguo.
  - Certeza: alta para doble imputación, moneda y fecha > 365 días; media para fecha entre 61 y 365 días.
- [X] T020 [US2] Implementar `backend/src/features/vinculos/correccion.py` (deja pasar T019).
- [X] T021 [P] [US2] Tests en `backend/tests/test_vinculos_lotes.py`:
  - Aplicar sin backup verificado no escribe.
  - Aplicar con ambiguos incluidos sin elegir devuelve 409.
  - Aplicar anula con `MotivoAnulacion` con formato `031:<IdLote>: <motivo>` y crea las aplicaciones con `Origen='correccion-031'`.
  - Revertir des-anula solo las de ese lote y anula las creadas.
  - Todo transaccional.
- [X] T022 [US2] Implementar `backend/src/features/vinculos/lotes.py`: `crear_lote`, `obtener`, `actualizar_items`, `aplicar` (reusa el backup de `backfill_impuestos`) y `revertir`.
- [X] T023 [US2] Endpoints en `backend/src/features/vinculos/router.py`:
  - `POST /lotes`
  - `GET /lotes/{id}`
  - `PATCH /lotes/{id}/items`
  - `POST /lotes/{id}/aplicar`
  - `POST /lotes/{id}/revertir`

  Los de escritura son solo para el rol Administrador. Contract tests en `backend/tests/contract/test_integridad_vinculos_api.py`.
- [X] T024 [US2] UI `frontend/src/components/integridad/RevisionLote.tsx`:
  - grupos por motivo y certeza, con cantidad e importe;
  - confirmar el grupo en bloque y destildar ítems;
  - elegir de a uno en los reemplazos ambiguos;
  - botones Aplicar y Revertir con confirmación.

  Integrarla en la página de T016.
- [X] T025 [US2] Revisión con el especialista contable (`.github/agents`) sobre una muestra de la propuesta real. Registrar las conclusiones en `specs/031-integridad-vinculos/quickstart.md`.
- [X] T026 [US2] Generar el primer lote real en WC y dejarlo en estado `propuesto`. **No aplicarlo**: lo revisa y confirma Sergio desde la UI.
- [ ] T026b [US2] Después de que Sergio aplique el lote, verificar sobre WC:
  - el control da 0 en `documento-excedido` y en `doble-imputacion` (SC-001);
  - ninguna aplicación con `Origen='manual'` cambió (SC-006);
  - revertir en una copia restaurada del backup deja los conteos iguales a la línea de base (SC-004).

  Registrar los resultados en `specs/031-integridad-vinculos/quickstart.md`.

---

## Phase 6: User Story 3 (cont.) - Bloqueo al guardar (FR-012)

- [X] T027 [P] [US3] Tests en `backend/tests/test_vinculos_validacion.py` para `verificar_exceso`:
  - exceso > 2% → error;
  - exceso ≤ 2% → advertencia;
  - las vías se suman sin duplicar.
- [X] T028 [US3] Implementar `backend/src/features/vinculos/validacion.py` e invocarlo al crear en:
  - `aplicaciones_pago/repository.py`;
  - la imputación de consumos en `tarjetas_resumenes/repository.py`;
  - `conciliacion_tesoreria/repository.py`.

  Si el exceso supera el 2%, devolver 422. Si no, incluir `advertencia` en la respuesta.
- [X] T029 (parcial: advertencia y error visibles en Aplicaciones de pago; en tarjetas y tesorería se ve el mensaje de error existente) [US3] Mostrar la advertencia y el error en los paneles de vinculación del frontend (`AplicarPagoPanel` y las pantallas de conciliación de tarjetas y de tesorería).

---

## Phase 7: Polish

- [X] T030 Suite completa del backend + `tsc` + `eslint` del frontend.
- [X] T031 Actualizar la memoria del proyecto con las reglas de cadena y la causa raíz del FIFO. Commit y push.

## Dependencies

- Setup → Foundational → US1 → US3 (control) → US2 (corrección) → Phase 6 → Polish.
- US2 depende del control (T014), porque la propuesta se construye a partir de los hallazgos.
- Phase 6 depende solo de Foundational y podría ir en paralelo con US2.

## Parallel Examples

- T003 ∥ T002.
- T007 ∥ T013.
- T019 ∥ T021.
- T027 en paralelo con toda US2.

## Implementation Strategy

- **MVP**: Phases 1–3. El flujo pasa a ver todos los vínculos y el sugeridor deja de producir errores nuevos.
- **Línea de base**: Phase 4, antes de tocar datos.
- **Corrección**: Phase 5, que termina en un lote real `propuesto` y nunca aplicado sin Sergio.
- **Prevención**: Phase 6.
