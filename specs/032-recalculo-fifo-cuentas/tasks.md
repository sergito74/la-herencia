# Tasks: Recálculo FIFO de cuentas corrientes

**Input**: Design documents from `specs/032-recalculo-fifo-cuentas/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md, quickstart.md

**Tests**: los tests del motor están pedidos en quickstart.md §1. Se escriben antes de implementar el motor.

**Regla de oro**: solo `WC`. Antes de cualquier DDL o escritura masiva hay que llamar a `vinculos.backup.backup_verificado()`.

## Phase 1: Setup

- [X] T001 Crear el paquete `backend/src/features/recalculo_fifo/__init__.py` y la carpeta `backend/tests/recalculo_fifo/__init__.py`.
- [X] T002 Crear `backend/scripts/crear_esquema_recalculo_fifo.py`. Es DDL idempotente, con `IF NOT EXISTS` y llamada previa a `backup_verificado("032-esquema")`. Crea las tablas de data-model.md:
  - `RecalculoFifoEjecucion`: `Tipo` en ('simulacion','aplicacion','continua') y `Estado` en ('simulada','aplicada','revertida','descartada').
  - `RecalculoFifoContacto`: PK (IdEjecucion, IdContacto), `Huella char(64)` y `EstadoExcepcion` en ('ninguna','pendiente','resuelta').
  - `RecalculoFifoAplicacion`: `Regla` en ('cadena','eleccion','nota-origen','ajuste-tc','compensacion','fifo','anticipo','diferencia-cambio').
  - `RecalculoFifoSaldoInicial`: `Estado` en ('estimado','confirmado','rechazado').
  - `RecalculoFifoCola` y `ContactoDuplicado`: `Criterio` en ('cuit','nombre') y `Estado` en ('propuesto','confirmado','descartado').
  - `Compras.Suspendida bit NOT NULL DEFAULT 0`.
  - Índices: `RecalculoFifoAplicacion(IdEjecucion, IdContacto)`.
- [X] T003 Ejecutar T002 contra `WC` y registrar en la salida la ruta del respaldo verificado.
- [X] T004 [P] Verificar la cobertura de `dbo.[Dolar BNA]` (`Vend_Divisa`) desde el 19/04/2010 hasta la fecha del último pago, y listar los huecos en `specs/032-recalculo-fifo-cuentas/checklists/etapa1.md`. Antes de simular, correr `backend/scripts/actualizar_dolar_bna.py` para completar hasta ayer (research R2).

## Phase 2: Foundational (bloquea todas las historias)

- [X] T005 Verificar que el total de `Compras` incluye percepciones y recargos (FR-018). Relevar en `Compras` los códigos de tipo de comprobante de nota de crédito y nota de débito, y las columnas de número de comprobante y moneda. Documentar el hallazgo en `specs/032-recalculo-fifo-cuentas/research.md` §R5. Es solo lectura.
- [X] T006 [P] Implementar `backend/src/features/recalculo_fifo/cambio.py`:
  - `tc_dia_anterior(fecha) -> (valor, implicito: bool)`: reutiliza `flujo_caja/cotizacion.py` (`cargar_serie`, `cotizacion_del_dia`) sobre `dbo.[Dolar BNA].Vend_Divisa`, con el último día hábil anterior a `fecha`. Si la fecha es posterior a la serie, devuelve None.
  - `tc_implicito(importe_ars, importe_usd)`.
  - Ajustes de las filas con `Ajusta Tipo Cambio = 1` asociados a su documento USD.
- [X] T007 Implementar `backend/src/features/recalculo_fifo/entrada.py`: `armar(id_contactos) -> dict[idContacto, {debitos, creditos}]`, con las estructuras de data-model.md "Entradas del motor". Reutiliza `vinculos.fuente.cargar()` y `vinculos.cadenas`.
  - **Débitos**:
    - Cuotas de `[Vencimiento Compras]`, con `IdCompra = Compras.IdDeuda` y el importe repartido en partes iguales y el redondeo en la última cuota. Una compra sin cuotas o de contado vence en su `Fecha`.
    - Liquidaciones `Venta Granos` y `Venta Hacienda`, con vencimiento igual a su `Fecha` (FR-033).
    - Notas de débito.
    - Saldo inicial confirmado de `RecalculoFifoSaldoInicial`.
    - Marca `suspendido` desde `Compras.Suspendida`.
  - **Créditos**:
    - Movimientos bna, galicia, efectivo, tarjetas, valores-recibidos y mercado-libre, con fecha real de erogación según R4: débito del resumen, débito del cheque, `Fecha Endoso`.
    - Retenciones de `Retenciones`, `Retenciones IVA Granos` y `Retenciones Ventas Hacienda` (R7).
    - Notas de crédito, con `origenNC` desde `CompraDocumentosRelacionados`.
  - **Asignaciones fijas**:
    - Las cadenas reales de tarjeta y cheque van como `cadena`.
    - Las aplicaciones vigentes con `Origen='manual'` van como `eleccion` (FR-024). Las `automatica-*` y `fifo-032` no son elecciones.
  - **Fecha de inicio**: se excluyen los documentos y movimientos anteriores al 19/04/2010 (FR-027). Las 2 compras sin fecha van como excepción de datos.
  - Contactos unificados por `ContactoDuplicado` con estado 'confirmado'.
  - Excluye movimientos de caja sin contacto (FR-036).
- [X] T008 [P] Escribir tests del motor en `backend/tests/recalculo_fifo/test_motor.py`, con datos sintéticos y sin base de datos:
  - anticipo
  - anticipo de más de 60 días marcado
  - desempate por número de comprobante
  - cuotas en orden
  - cadena parcial más FIFO del resto
  - elección explícita
  - elección manual que sobreaplica, con el exceso reasignado y la marca 'manual-ajustado'
  - diferencia de cambio en documento USD, con el cierre medido en dólares
  - factura suspendida salteada
  - nota de crédito con origen
  - documento USD pagado en pesos con TC del día anterior
  - compensación cruzada en USD
  - pago de más sin débito posterior que da excepción
  - huella idéntica en dos corridas
- [X] T009 Implementar `backend/src/features/recalculo_fifo/motor.py`: `recalcular(entrada_contacto, tc) -> {aplicaciones, anticipos_abiertos, marcas}`. Es puro y determinista. El orden es el siguiente:
  1. Fijos: `cadena` y `eleccion`. Si una `eleccion` sobreaplica una factura o un pago, el exceso vuelve al reparto FIFO y el contacto queda marcado 'manual-ajustado' (FR-024).
  2. Notas de crédito a su factura de origen (`nota-origen`).
  3. Ajustes de TC a su documento (`ajuste-tc`).
  4. Compensación ventas↔compras en la moneda del documento (`compensacion`, FR-007).
  5. Reparto FIFO de los créditos restantes ordenados por (fecha, medio, id) sobre los débitos no suspendidos ordenados por (vencimiento, nroComprobante, id) (`fifo`).
  6. Excedentes como anticipo que cubre el siguiente débito (`anticipo`). Si la distancia es mayor a 60 días, marca 'anticipo-largo'.
  - En documentos USD, el cierre se mide en dólares. La diferencia en pesos entre el TC de la factura y el del pago genera un renglón `diferencia-cambio` (FR-006).
  - Redondeo a 2 decimales y `huella()` SHA-256 de las aplicaciones ordenadas.
  - T008 debe pasar.
- [X] T010 Implementar `backend/src/features/recalculo_fifo/controles.py`: `evaluar(contacto, antes, despues) -> {cierra, controles_fallidos, tendencia}`, con una tolerancia de 0,5%. Controles:
  - FR-010: débito sobreaplicado, crédito sobreaplicado, aplicado distinto de min(pagado, facturado).
  - FR-011: cerraba antes y ya no cierra.
  - FR-034: saldo distinto de 0 al 29/06/2012 en contactos sin continuidad.
  - FR-037: pago de más no imputable.
  - Marcas: saldo estimado, cheque provisorio, TC implícito y 'endoso-sin-registro' (R6).
  - Agregar casos en `backend/tests/recalculo_fifo/test_controles.py`.

**Checkpoint**: el especialista financiero (`.github/agents/07-financial-direction-specialist.agent.md`) revisa motor.py y controles.py contra spec.md antes de seguir.

## Phase 3: User Story 1 - Simular y ver el impacto por contacto (P1) 🎯 MVP

**Goal**: simulación sin escrituras en `AplicacionesPago`, con una lista y un detalle por contacto.

**Independent Test**: quickstart §2. Simular los 9 contactos de la primera etapa. `AplicacionesPago` queda igual, y 47, 384 y 340 siguen cerrando.

- [X] T011 [US1] Implementar `simular(alcance, usuario)` en `backend/src/features/recalculo_fifo/ejecuciones.py`. Crea `RecalculoFifoEjecucion` con Tipo 'simulacion' y Estado 'simulada'. Guarda por contacto en `RecalculoFifoContacto` los valores antes y después, la huella y los controles, y las aplicaciones propuestas en `RecalculoFifoAplicacion`. No escribe en `AplicacionesPago`. "Antes" se calcula con `vinculos.fuente`.
- [X] T012 [US1] Implementar las lecturas de lista, con filtros todos, cierra, no-cierra, mejora, empeora y excepcion, orden por volumen y paginación, y el detalle de contacto: débitos, créditos, aplicaciones con su regla y línea de saldo. Van en `backend/src/features/recalculo_fifo/ejecuciones.py`.
- [X] T013 [US1] Crear `backend/src/features/recalculo_fifo/router.py` con `POST /ejecuciones`, `GET /ejecuciones`, `GET /ejecuciones/{id}`, `GET /ejecuciones/{id}/contactos`, `GET /ejecuciones/{id}/contactos/{idContacto}` y `PATCH .../excepcion` según contracts/api.md. Registrarlo en `backend/src/main.py` bajo `/api/recalculo-fifo`.
- [X] T014 [P] [US1] Agregar en `frontend/src/services/recalculoFifoApi.ts` los tipos y fetchers de los endpoints de T013.
- [X] T015 [US1] Crear la página `frontend/src/app/finanzas/recalculo-fifo/page.tsx` y estos componentes:
  - `frontend/src/components/recalculo-fifo/RecalculoFifo.tsx`, que contiene la barra de ejecución (simular la primera etapa o todos), la lista con filtros y el detalle en panel lateral.
  - Usar TanStack Query y agregar el enlace en `frontend/src/components/layout/NavHeader.tsx` bajo Finanzas.
- [X] T016 [US1] Ejecutar la simulación de los 9 contactos (258, 47, 48, 23, 384, 340, 249, 276, 220). Verificar que el conteo y la suma de `AplicacionesPago` no cambien. Volcar el resultado en `specs/032-recalculo-fifo-cuentas/checklists/etapa1.md` y revisarlo con el especialista financiero.

**Checkpoint**: Sergio revisa la simulación de la primera etapa en pantalla.

## Phase 4: User Story 2 - Aplicar con respaldo y reversión (P1)

**Goal**: aplicar por contacto, de forma idempotente y reversible.

**Independent Test**: quickstart §3. Aplicar, re-simular sin cambios y revertir hasta volver al estado idéntico.

- [X] T017 [US2] Implementar `aplicar(id, contactos, confirmar_empeoran, usuario)` en `backend/src/features/recalculo_fifo/ejecuciones.py`:
  - Exige el rol admin (FR-017), o devuelve 403.
  - Responde 409 si el estado no es 'simulada' o si cambió la huella "antes".
  - Responde 422 si hay contactos que empeoran sin confirmación.
  - Hace `backup_verificado("032-aplicar-N")`.
  - Por contacto, en una transacción: anula las vigentes que no son cadena con el motivo "Reemplazada por FIFO ejecución N" y, si la huella es igual, las cuenta como sinCambios.
  - Inserta con `Origen='fifo-032'` y `NotaConciliacion='ejecucion:N regla:X'`.
  - Pone Estado 'aplicada'.
- [X] T018 [US2] Implementar `revertir(id, usuario)` y `descartar(id)` en `backend/src/features/recalculo_fifo/ejecuciones.py`. Revertir des-anula las aplicaciones anuladas por esa ejecución, anula las `fifo-032` que insertó y pone Estado 'revertida'.
- [X] T019 [US2] Agregar `POST /ejecuciones/{id}/aplicar`, `/revertir` y `/descartar` en `backend/src/features/recalculo_fifo/router.py`.
- [X] T020 [US2] Agregar en `frontend/src/components/recalculo-fifo/RecalculoFifo.tsx` (barra de ejecución) los botones Aplicar, con selección de contactos y confirmación de los que empeoran, Revertir y Descartar, envueltos en `SoloLectura`.
- [X] T021 [US2] Desactivar la generación de lotes de 031: `POST /api/integridad-vinculos/lotes` responde 410 con un mensaje que remite a 032. Además, descartar el lote 4 en `backend/src/features/vinculos/router.py` (FR-016), con confirmación previa de Sergio.
- [X] T022 [US2] Validar quickstart §3 con los contactos simples: aplicar, re-simular para comprobar la huella igual y sinCambios, revertir y comparar `AplicacionesPago` entre antes y después con la misma suma, los mismos conteos y los mismos ids vigentes.

## Phase 5: User Story 3 - Cuentas mixtas, saldo inicial y duplicados (P2)

**Goal**: que Cargill y las cuentas con arrastre cierren, o queden explicadas.

**Independent Test**: simular el contacto 258. La compensación en USD queda reflejada y el saldo neto coincide con la cuenta corriente.

- [ ] T023 [P] [US3] Implementar `backend/src/features/recalculo_fifo/duplicados.py`: detecta por CUIT igual y, sin CUIT, por similitud de `Razon Social` normalizada. Guarda en `ContactoDuplicado` con Estado 'propuesto'. Incluye confirmar y descartar.
- [ ] T024 [US3] Implementar la estimación de saldo inicial (research R10) en `backend/src/features/recalculo_fifo/entrada.py`. Escribe en `RecalculoFifoSaldoInicial` con Estado 'estimado'. Un saldo no confirmado no entra en el motor y deja la marca 'saldo-estimado'.
- [ ] T025 [US3] Agregar los endpoints `/saldos-iniciales` y `/duplicados` (GET y POST, solo admin) en `backend/src/features/recalculo_fifo/router.py`.
- [ ] T026 [P] [US3] Crear `frontend/src/components/recalculo-fifo/SaldosIniciales.tsx` y `Duplicados.tsx` como pestañas de la página de recalculo-fifo.
- [ ] T027 [US3] Simular el contacto 258 (Cargill) y documentar en `checklists/etapa1.md` las compensaciones, el saldo en USD y las excepciones restantes. Revisión del especialista financiero.

## Phase 6: User Story 5 - Operatoria continua y saldo por vencimiento (P2)

**Goal**: mantener las cuentas aplicadas y mostrar los vencimientos.

**Independent Test**: quickstart §5.

- [ ] T028 [US5] Encolar el contacto en `RecalculoFifoCola` al asignar contacto a un movimiento (`backend/src/features/conciliacion_tesoreria/`) y al guardar una compra o venta (`backend/src/features/compras/`, `backend/src/features/ventas_granos/` y `backend/src/features/ventas_hacienda/`). Es una inserción idempotente.
- [ ] T029 [US5] Implementar `procesar_cola()` en `backend/src/features/recalculo_fifo/ejecuciones.py`: crea una ejecución 'continua', aplica a los contactos que pasan los controles y deja el resto en propuestas. Agregar `POST /cola/procesar` y `GET /propuestas`.
- [ ] T030 [US5] Agregar `PATCH /compras/{idDeuda}/suspension` (FR-025) y el interruptor "Suspendida / en reclamo" en el detalle de la compra, en `frontend/src/components/compras/`.
- [ ] T031 [P] [US5] Implementar `backend/src/features/recalculo_fifo/saldos.py`:
  - `saldo_por_vencimiento(idContacto)`: vencido, tramos por fecha de cuota y anticipo, en la moneda de la cuenta.
  - `aviso_vencimientos(usuario, hoy)`: es true el primer ingreso de un lunes y cubre los próximos 15 días.
  - Agregar los endpoints de contracts/api.md.
- [ ] T032 [P] [US5] Crear `frontend/src/components/cuentas-corrientes/SaldoPorVencimiento.tsx` en la pantalla de cuenta corriente, y `frontend/src/components/layout/AvisoVencimientos.tsx` como modal al entrar los lunes. El componente de layout también llama a `cola/procesar` al entrar y cada hora.

## Phase 7: User Story 4 - Flujo por rubro (P2)

**Goal**: el flujo de 030 refleja las aplicaciones nuevas.

**Independent Test**: quickstart §6 (SC-008).

- [ ] T033 [US4] Verificar que `backend/src/features/flujo_caja/` (rubro, 030) lea los `fifo-032` a través de `vinculos.fuente` y reparta cada aplicación por las líneas de su factura (FR-015). Si hoy reparte de otra forma, cambiarlo. Agregar el rubro "Anticipos a proveedores / de clientes" para anticipos abiertos.
- [ ] T034 [US4] Validar SC-008 en un trimestre después de aplicar la primera etapa. Documentarlo en `checklists/etapa1.md`.

## Phase 8: Polish

- [ ] T035 Correr la simulación de todos los contactos, medir que tarde menos de 5 minutos (SC-007) y que pase al menos el 90% (SC-003). Registrarlo en `checklists/etapa1.md`.
- [ ] T036 [P] Actualizar `memory.md` y la memoria del proyecto con el estado de 032 y el fin de los lotes de 031.
- [ ] T037 Revisar el diff final: no deben quedar credenciales ni respaldos versionados, y no debe haber escrituras a `LaHerencia`.

## Dependencies

- Setup (T001-T004) va antes de Foundational (T005-T010) y del checkpoint financiero.
- US1 (T011-T016) es el MVP.
- US2 (T017-T022) requiere US1.
- US3 (T023-T027) puede empezar en paralelo con US1 después de Foundational. Para aplicar Cargill se necesita US2.
- US5 (T028-T032) requiere US2.
- US4 (T033-T034) requiere US2 aplicado.
- Polish va al final.

## Parallel Examples

- **Foundational**: T006 (cambio.py) y T008 (tests) en paralelo. Después T009 y T010.
- **US1**: T014 (fetchers del frontend) mientras se hace T013.
- **US3**: T023 (duplicados) y T026 (frontend) en paralelo.
- **US5**: T031 (saldos) y T032 (componentes) en paralelo.

## Implementation Strategy

1. **MVP**: Setup, Foundational y US1. Sergio ve la simulación de los 9 contactos sin ningún riesgo, porque no se escribe nada en las aplicaciones.
2. **Primera aplicación**: US2 con los 4 contactos simples, después los 5 complejos.
3. **Resto de los contactos**: se aplica por etapas por volumen. Las excepciones quedan pendientes para revisarlas una a una.
4. **Operatoria continua y rubro**: US5 y US4.
