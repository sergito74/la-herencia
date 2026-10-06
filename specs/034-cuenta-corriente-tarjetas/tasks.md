---

description: "Lista de tareas de 034-cuenta-corriente-tarjetas"
---

# Tasks: Cuentas de tarjetas y de Mercado Pago

**Input**: documentos de diseño en `/specs/034-cuenta-corriente-tarjetas/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/tarjetas-cuenta-api.md, quickstart.md

**Tests**: se incluyen porque la constitución (principio V) exige la verificación útil más acotada en cada cambio y el contrato se prueba antes de la UI. Las pruebas de control y de cruces usan fixtures puros; las que leen `WC` son de solo lectura.

**Organization**: las tareas se agrupan por historia de usuario para poder implementar y probar cada una por separado. Todas las escrituras reales van a `WC`, con backup verificado previo (constitución II).

## Format: `[ID] [P?] [Story] Descripción con ruta`

- **[P]**: se puede hacer en paralelo (archivos distintos, sin dependencia de tareas incompletas)
- **[Story]**: US1 a US6 según el spec (US1 cuenta de la tarjeta, US2 sin duplicación en proveedores, US3 control, US4 devoluciones de débitos, US5 Mercado Pago, US6 navegación al detalle)

## Path Conventions

- Backend: `backend/src/features/tarjetas_cuenta/`, `backend/scripts/`, `backend/tests/`
- Frontend: `frontend/src/app/finanzas/tarjetas/`, `frontend/src/components/tarjetas-cuenta/`, `frontend/src/services/`

---

## Phase 1: Setup

**Purpose**: revisión previa y estructura base

- [X] T001 Consultar al especialista financiero (`.github/agents/`) con `spec.md` y `plan.md`: fecha de la deuda por consumo, regla de conducto de Mercado Pago, apertura de AgroNacion y tratamiento de cargos; registrar observaciones y supuestos confirmados en una sección "Revisión de especialista" de `specs/034-cuenta-corriente-tarjetas/research.md`
- [X] T002 Crear el módulo `backend/src/features/tarjetas_cuenta/` con `__init__.py`, `schemas.py`, `repository.py` y `router.py` (prefijo `/api/tarjetas-cuenta`) y registrar el router en `backend/src/main.py` junto a `tarjetas_router`
- [X] T003 [P] Crear `frontend/src/services/tarjetasCuentaApi.ts` con los tipos del contrato `contracts/tarjetas-cuenta-api.md` (resumen, cuenta, filas, control, sugerencias, cruces) y las funciones de llamada usando `apiClient.ts`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: tablas, ramas de la vista y datos de partida; ninguna historia puede empezar antes

**⚠️ CRITICAL**: sin esta fase la vista no tiene la pata deuda ni los cruces

- [X] T004 Crear `backend/scripts/vista_tarjeta_cuenta_corriente.py` con modo `--verificar` (no escribe), modo `--ensayo` (ejecuta todo dentro de una transacción y hace rollback, sin dejar cambios), modo normal y `--revertir`; usa `backup_verificado` de `src.features.vinculos.backup`, aborta si la base no es `WC` y guarda la definición previa de `vw_MovimientosCuenta_Base` en un archivo `.sql` junto al respaldo y fuera de git; idempotente (marca de ramas ya presentes) con el mismo patrón de `backend/scripts/vista_tarjeta_impuestos.py`
- [X] T005 En `backend/scripts/vista_tarjeta_cuenta_corriente.py` crear `dbo.TarjetasContacto` con exactamente: `IdTarjeta` int PK (referencia a `Tarjetas`); `IdContacto` int, NOT NULL, único (referencia a `Contactos`); `IdContactoAnterior` int, NULL; `Usuario` varchar(60); `Fecha` datetime2; sembrar 1→373, 2→503, 3→372, 4→532, 5→533 verificando antes que cada contacto tenga el nombre de la tarjeta y `Tipo Contacto = 'Tarjeta de Credito'`
- [X] T006 En `backend/scripts/vista_tarjeta_cuenta_corriente.py` crear `dbo.TarjetasCruces` con exactamente: `IdCruce` int identity PK; `Tipo` varchar(30) con CHECK `devolucion-debito` o `consumo-devolucion`; `IdTarjeta` int NOT NULL; `MedioOrigen` varchar(20) NOT NULL; `IdMovimientoOrigen` int NOT NULL; `MedioDestino` varchar(20) NULL; `IdMovimientoDestino` int NULL; `IdLineaConsumo` int NULL; `Importe` money NOT NULL (positivo); `Sugerido` bit; `Usuario` varchar(60); `Fecha` datetime2; `Deshecho` bit default 0; `UsuarioDeshecho` varchar(60) NULL; `FechaDeshecho` datetime2 NULL; restricciones: único por (`MedioOrigen`, `IdMovimientoOrigen`) entre cruces no deshechos, `devolucion-debito` exige `MedioDestino` e `IdMovimientoDestino`, `consumo-devolucion` exige `IdLineaConsumo`
- [X] T007 En `backend/scripts/vista_tarjeta_cuenta_corriente.py` agregar a la vista las ramas `Tarjeta consumo` (una fila por línea de `Tarjetas_Resumenes_Lineas` de resúmenes con `EstadoResumen` distinto de `Cerrado`, `Fecha` = `FechaCompra`, contacto = `TarjetasContacto.IdContacto` de la tarjeta del resumen, importe positivo = Deuda y negativo = Crédito por el valor absoluto, `IdOrigen` = `IdLineaConsumo`) y `Tarjeta cargo` (las 14 columnas de cargos del resumen no nulas y distintas de cero con `CROSS APPLY (VALUES …)`, `Fecha` = `FechaCierre`, `IdOrigen` = `IdResumen * 100 + n` con n de 1 a 14)
- [X] T008 En `backend/scripts/vista_tarjeta_cuenta_corriente.py` agregar las ramas `Tarjeta pago` (pagos de `Tarjetas_Resumenes_Pagos` con `IdMovimientoOrigen` nulo de resúmenes distintos de `Cerrado`, `Fecha` = fecha del pago, Crédito por el importe, `IdOrigen` = `IdPago`), `Tarjeta devolución` (cruces `devolucion-debito` con `Deshecho = 0`, `Fecha` = fecha del movimiento de la devolución, contacto de la tarjeta, Deuda por `Importe`, `IdOrigen` = `IdCruce`) y `Mercado Pago` (movimientos de `Movimientos Mercado Libre` con `IdContacto` asignado, sin conciliación en `ConciliacionesTesoreria` y que no sean conducto; conducto = existe otro movimiento de la misma `IdOperacion`, del mismo día, de descripción que empieza con "Ingreso de dinero" y de importe opuesto con diferencia menor a $0,01; importe negativo = Crédito, positivo = Deuda, `IdOrigen` = `IdMovimiento`)
- [X] T009 En `backend/scripts/vista_tarjeta_cuenta_corriente.py` implementar la instantánea previa a ampliar la vista (saldo por contacto y totales mensuales de ingresos y egresos del flujo de caja de `backend/src/features/flujo_caja/repository.py` de 2024-01 a 2026-09), el modo `--comparar` (diferencias por contacto, total general y totales del flujo de caja contra la instantánea) y la restauración completa de `--revertir`
- [X] T010 [P] Cambiar `get_id_contacto_tarjeta` en `backend/src/features/tarjetas/repository.py` para leer `TarjetasContacto` (y devolver `None` si la tarjeta no tiene fila) y agregar `backend/tests/test_tarjetas_contacto.py` con fixtures que cubran tarjeta con contacto, sin contacto y contacto duplicado
- [X] T011 [P] Extender `backend/src/features/cuentas_corrientes/origen_resolver.py` para resolver los orígenes `Tarjeta consumo`, `Tarjeta cargo`, `Tarjeta devolución` y `Mercado Pago` (referencias `linea-consumo`, `resumen`, `cruce` y `mercado-libre`) y agregar `backend/tests/test_origen_resolver_tarjetas.py`
- [X] T012 Crear `backend/scripts/preparar_tarjetas_cuenta_034.py` con `--verificar` y `--revertir` (la comparación antes/después vive en `vista_tarjeta_cuenta_corriente.py --comparar`): crea el contacto "AgroNacion (administración anterior)", lo guarda en `TarjetasContacto.IdContactoAnterior` de AgroNacion y reasigna con `ReasignacionesContacto` los 22 pagos de la administración anterior de AgroNacion: 21 de `Movimientos BNA` (`Origen` `Banco Nacion`) con concepto "PM/TOT. RES. AGRONACION", fechas del 28/09/2010 al 28/05/2012, sin pago de resumen vinculado y que sumen exactamente $23.575,00, y 1 de `Pagos efectivo` (`Origen` `Pagos efectivo`, `IdPagoEfectivo` 363, 26/06/2012, $1.677,58); aborta si el conjunto no coincide; backup verificado antes de escribir
- [X] T013 Con T027 y T028 ya escritas, ejecutar en `WC` `python -m scripts.vista_tarjeta_cuenta_corriente --verificar`, luego `--ensayo` (transacción con rollback) y recién entonces sin opción; registrar backup, tablas creadas y ramas agregadas en la sección "Resultados de la corrida" de `specs/034-cuenta-corriente-tarjetas/quickstart.md`
- [X] T014 Ejecutar en `WC` `python -m scripts.preparar_tarjetas_cuenta_034 --verificar` y luego sin la opción; registrar los 22 pagos reasignados y el contacto creado en `specs/034-cuenta-corriente-tarjetas/quickstart.md`

**Checkpoint**: la vista tiene las cinco ramas nuevas, el mapeo explícito existe y AgroNacion tiene su cuenta anterior; las historias pueden empezar.

---

## Phase 3: User Story 1 - Saber cuánto se le debe a cada tarjeta (Priority: P1) 🎯 MVP

**Goal**: resumen de las cinco tarjetas y cuenta cronológica de cada una con consumos, cargos, pagos y saldo, con filtro por período, vista por resumen, cuotas a vencer y exportación.

**Independent Test**: en Visa Galicia el saldo final coincide con el pendiente neto del módulo de tarjetas (diferencia menor a $1) y cada fila se rastrea a su resumen o movimiento (quickstart pasos 4).

### Tests for User Story 1

- [X] T015 [P] [US1] Prueba de contrato de `GET /api/tarjetas-cuenta/resumen` y `GET /api/tarjetas-cuenta/{idTarjeta}` (parámetros `desde`, `hasta`, `agrupar=movimientos|resumenes`, `saldoInicial`, `detalleSaldo`, `avisoSaldo`, `cuotasAVencer`, 404 de tarjeta inexistente, `tarjetasSinContacto`) con el repositorio simulado en `backend/tests/contract/test_tarjetas_cuenta_api.py`
- [X] T016 [P] [US1] Prueba con fixtures puros del saldo inicial del período, el saldo final, el orden cronológico y la equivalencia entre `agrupar=movimientos` y `agrupar=resumenes` (suma por resumen igual al total de `calcular_total`) en `backend/tests/test_tarjetas_cuenta_repository.py`

### Implementation for User Story 1

- [X] T017 [US1] Definir en `backend/src/features/tarjetas_cuenta/schemas.py` los modelos de respuesta del contrato: tarjeta del resumen, total, fila de cuenta (`origen` `Consumo`, `Cargo del resumen`, `Pago`, `Devolución`; `estadoVinculo` `vinculado`, `resto-con-proveedor`, `sin-proveedor`, `cruzado-con-devolucion`; `referencia`), cuenta con `saldoInicial`, `saldoFinal`, `cuotasAVencer` y `apertura`
- [X] T018 [US1] Implementar en `backend/src/features/tarjetas_cuenta/repository.py` el resumen de las cinco tarjetas: saldo desde la vista, deuda y crédito totales, `pendienteNeto` con `get_compensaciones`, `diferenciaConModuloTarjetas`, `ultimoMovimiento`, `cuotasAVencer` (cantidad) y `tarjetasSinContacto` (FR-006, FR-009)
- [X] T019 [US1] Implementar en `backend/src/features/tarjetas_cuenta/repository.py` la cuenta de una tarjeta con `desde`, `hasta` y `agrupar`: filas de la vista del contacto, saldo acumulado, saldo inicial del período y `estadoVinculo` de cada consumo; en `agrupar=resumenes` una fila por resumen con su total, el bloque `apertura` con el contacto de la administración anterior cuando existe y `detalleSaldo` con el saldo exigible y el consumo aún no resumido a la fecha `hasta` (FR-023: `exigible + noResumido` igual al saldo con diferencia menor a $1), más el texto `avisoSaldo` (FR-024) (FR-001, FR-004, FR-007, FR-008)
- [X] T020 [US1] Implementar en `backend/src/features/tarjetas_cuenta/repository.py` las cuotas a vencer de la tarjeta (cuotas no cobradas del cronograma `Cuotas Tarjetas de Credito`, vía `backend/src/features/tarjetas_cuotas/repository.py`), informadas aparte y sin sumar al saldo (FR-015)
- [X] T021 [US1] Exponer en `backend/src/features/tarjetas_cuenta/router.py` `GET /resumen` y `GET /{id_tarjeta}` con las validaciones y errores del contrato
- [X] T022 [US1] Crear `backend/src/features/tarjetas_cuenta/exportacion.py` y exponer `GET /{id_tarjeta}/exportar` que genera un `.xlsx` con las mismas filas y saldos que la pantalla (FR-008)
- [X] T023 [P] [US1] Implementar en `frontend/src/services/tarjetasCuentaApi.ts` las llamadas a resumen, cuenta y exportación con TanStack Query
- [X] T024 [US1] Mostrar saldo de cada tarjeta, total y alerta de tarjetas sin contacto en `frontend/src/app/finanzas/tarjetas/page.tsx`
- [X] T025 [US1] Crear `frontend/src/components/tarjetas-cuenta/TarjetaCuentaTabla.tsx` y cambiar `frontend/src/app/finanzas/tarjetas/[idTarjeta]/cuenta-corriente/page.tsx` para usar el nuevo endpoint: filas con saldo cronológico, filtro de período, selector "por movimiento / por resumen", sección de cuotas a vencer, bloque "Apertura de la administración anterior" con enlace a esa cuenta (FR-004), subtotales "Exigible" y "Consumo aún no resumido" (FR-023), el aviso de que el saldo es de gestión (FR-024) y botón de exportación (que repite el detalle y el aviso), con los formatos de moneda del proyecto (`formatMoneda`)
- [X] T026 [US1] Verificar la historia: desde `backend/` ejecutar `python -m pytest tests/contract/test_tarjetas_cuenta_api.py tests/test_tarjetas_cuenta_repository.py -q` y desde `frontend/` `npx tsc --noEmit`, y comprobar en `WC` el saldo de Visa Galicia contra su pendiente neto y medir el tiempo de `GET /api/tarjetas-cuenta/1` (AgroNacion, historia completa) contra el objetivo de menos de 3 segundos (SC-005); registrar el resultado en `specs/034-cuenta-corriente-tarjetas/quickstart.md`

**Checkpoint**: cada tarjeta muestra su cuenta con deuda real; sin los cruces aún pendientes, AgroNacion puede mostrar $966.654,20 de diferencia (se resuelve en US4).

---

## Phase 4: User Story 2 - Que la deuda con las tarjetas no altere los saldos de proveedores (Priority: P1)

**Goal**: probar que ningún saldo de contactos que no son tarjetas cambia (salvo UATRE) y que el flujo de caja real queda idéntico.

**Independent Test**: la comparación antes/después y las invariantes de solo lectura pasan (quickstart pasos 3, 5 y 10).

### Tests for User Story 2

> **Nota de orden**: T027 y T028 se escriben al inicio de la funcionalidad (son archivos de prueba, en paralelo con T004 a T012) porque T013 las exige antes de modificar la vista de `WC`.

- [X] T027 [P] [US2] Escribir en `backend/tests/test_vista_cuenta_tarjetas.py` las invariantes de solo lectura contra `WC`: consumos de tarjeta igual a vinculados más resto acreditado más consumos sin proveedor; ningún pago de resumen asignado a un proveedor; las ramas nuevas no suman filas a contactos que no son tarjetas salvo UATRE (contacto 315)
- [X] T028 [US2] Agregar en `backend/tests/test_vista_cuenta_tarjetas.py` la prueba de flujo de caja (`-k flujo`): `backend/src/features/flujo_caja/` solo lee `Movimientos BNA` y `Movimientos Galicia` y su única consulta a la vista filtra `Origen = 'Compras'`, y los totales de períodos de control son idénticos a los de la instantánea previa (FR-017, SC-007)

### Implementation for User Story 2

- [X] T029 [US2] Ejecutar `python -m scripts.vista_tarjeta_cuenta_corriente --comparar` en `WC` y confirmar: ningún cambio de saldo en contactos que no son tarjetas salvo UATRE (+$17.185,82), tarjetas con saldo real y total general cambiado solo por la deuda vigente incorporada, las devoluciones cruzadas y el pago de UATRE (SC-008), y totales del flujo de caja idénticos a la instantánea; registrar la comparación en `specs/034-cuenta-corriente-tarjetas/quickstart.md`
- [ ] T030 [US2] Si la comparación muestra una diferencia no explicada, corregir la rama correspondiente en `backend/scripts/vista_tarjeta_cuenta_corriente.py`, revertir con `--revertir`, volver a aplicar y repetir T029; dejar constancia de lo corregido en `research.md`

**Checkpoint**: las cuentas de proveedores y el flujo de caja están demostrablemente intactos.

---

## Phase 5: User Story 3 - Detectar pagos duplicados y datos inconsistentes (Priority: P2)

**Goal**: panel de control con las categorías (a) a (j) del spec y exportación.

**Independent Test**: con los datos de partida lista 22 movimientos de AgroNacion sin resumen (y el de Mastercard BNA hasta su registro como gasto bancario), la devolución sin cruzar, el pago con origen "Crédito banco" y los consumos sin proveedor (quickstart paso 6).

### Tests for User Story 3

- [X] T031 [P] [US3] Escribir con fixtures puros una prueba por categoría (`pago-en-proveedor`, `movimiento-sin-resumen`, `pago-sin-origen-o-importe`, `resumen-con-pendiente`, `devolucion-sin-cruzar`, `saldo-inicial-con-pagos`, `tarjeta-sin-contacto`, `consumo-sin-vinculo-con-deuda-abierta`, `consumo-sin-proveedor`, `diferencia-contrapartida`, `continuidad-de-resumenes`, `indicios-de-otra-moneda`) y la tolerancia de $300 de pendiente en `backend/tests/test_tarjetas_cuenta_control.py`; la continuidad no debe señalar meses sin resumen en una tarjeta sin actividad (caso de los 64 meses de AgroNacion) y sí una tarjeta activa con último resumen de más de 92 días
- [X] T032 [US3] Agregar a `backend/tests/contract/test_tarjetas_cuenta_api.py` las pruebas de `GET /control` (filtros `idTarjeta` y `categoria`, `resumenPorCategoria`) y `GET /control/exportar`

### Implementation for User Story 3

- [X] T033 [US3] Crear `backend/src/features/tarjetas_cuenta/control.py` con la función pura `hallazgos(raw)` (categorías (a) a (l); la (k) señala tarjetas activas con último resumen de más de 92 días y resúmenes con pendiente mayor a la tolerancia sin resumen posterior; la (l) busca USD, U$S, dólar o euro en el detalle de los consumos y en las observaciones) sobre un diccionario cargado de solo lectura, siguiendo el patrón de `backend/src/features/vinculos/control.py` y la tolerancia de pendiente de `TOLERANCIA_CONCILIACION` (FR-010, FR-012)
- [X] T034 [US3] Implementar en `backend/src/features/tarjetas_cuenta/repository.py` el cargador de solo lectura del control: movimientos a contactos de tarjeta, `Tarjetas_Resumenes_Pagos`, consumos, vínculos, conciliaciones, cruces y devoluciones sin contacto
- [X] T035 [US3] Exponer `GET /control` y `GET /control/exportar` en `backend/src/features/tarjetas_cuenta/router.py` y generar el `.xlsx` en `backend/src/features/tarjetas_cuenta/exportacion.py` (FR-011)
- [X] T036 [P] [US3] Crear `frontend/src/components/tarjetas-cuenta/PanelControl.tsx` y `frontend/src/app/finanzas/tarjetas/control/page.tsx` con filtros por tarjeta y categoría, totales por categoría, motivo de cada hallazgo y exportación; agregar el acceso en `frontend/src/components/layout/NavHeader.tsx` y en `frontend/src/app/finanzas/tarjetas/page.tsx`
- [X] T037 [US3] Verificar contra `WC` los casos conocidos del contexto en el estado posterior a T014 (SC-003: débito 18093 de AgroNacion, devolución sin contacto y pago con origen "Crédito banco") y la medición de consumos sin proveedor ($249.998,99) y registrar el resultado en `specs/034-cuenta-corriente-tarjetas/quickstart.md`

**Checkpoint**: el control detecta los casos conocidos y puede exportarse.

---

## Phase 6: User Story 4 - Devoluciones de débitos de tarjeta (Priority: P2)

**Goal**: sugerir y aprobar el cruce de una devolución con su débito, con registro de quién y cuándo, y poder deshacerlo.

**Independent Test**: cruzar BNA 9426 (17/09/2025) con BNA 18093 (01/09/2025) deja el neto de AgroNacion sin diferencia y la devolución deja de figurar sin contacto (quickstart paso 7).

### Tests for User Story 4

- [X] T038 [P] [US4] Escribir con fixtures puros en `backend/tests/test_tarjetas_cuenta_cruces.py` las sugerencias `devolucion-debito` (ventana de ±45 días, importes iguales con tolerancia de $0,01, orden por puntaje, exclusión de movimientos ya cruzados) y las validaciones de alta (importe distinto, devolución mayor al débito, duplicado, línea de otra tarjeta)
- [X] T039 [US4] Agregar a `backend/tests/contract/test_tarjetas_cuenta_api.py` las pruebas de `GET /cruces/sugerencias`, `POST /cruces` (201, 409, 422, 403 para rol `Lectura`), `DELETE /cruces/{idCruce}` (204, 404, 409) y `GET /cruces`

### Implementation for User Story 4

- [X] T040 [US4] Crear `backend/src/features/tarjetas_cuenta/cruces.py` con la sugerencia `devolucion-debito`, el alta de un cruce con las validaciones del modelo de datos ("el importe debe igualar el de la devolución y no superar el del débito", un movimiento no puede estar en dos cruces vigentes), la baja lógica con usuario y fecha y el listado (FR-003, FR-022)
- [X] T041 [US4] Exponer en `backend/src/features/tarjetas_cuenta/router.py` `GET /cruces/sugerencias`, `POST /cruces`, `DELETE /cruces/{id_cruce}` y `GET /cruces` con el rol de escritura ya vigente y los códigos de error del contrato
- [X] T042 [US4] Crear `frontend/src/components/tarjetas-cuenta/DialogoCruce.tsx` y agregar la sección de sugerencias con candidatas ordenadas, aprobar, rechazar y deshacer (botones ocultos para el rol `Lectura`, como en el resto de las pantallas), más el historial de cruces, a `frontend/src/app/finanzas/tarjetas/control/page.tsx`
- [X] T043 [US4] Aprobar desde la pantalla el cruce de BNA 9426 con BNA 18093 en `WC` y verificar el neto de AgroNacion, la fila "Devolución" en su cuenta y que dejan de informarse las categorías (b) y (e) para ese caso (SC-006); registrar en `specs/034-cuenta-corriente-tarjetas/quickstart.md`

**Checkpoint**: la devolución de $966.654,20 queda cruzada con trazabilidad.

---

## Phase 7: User Story 5 - Mercado Pago tratado como un banco (Priority: P2)

**Goal**: marcar el conducto en Tesorería, acreditar los pagos con fondos propios de la billetera y cruzar la devolución del kit Starlink con su consumo.

**Independent Test**: UATRE suma el pago del 04/09/2024 y los 30 pares quedan como conducto; el cruce de la línea 505 con el movimiento 20 deja de informar ese consumo como sin proveedor (quickstart pasos 8 y 9).

### Tests for User Story 5

- [ ] T044 [P] [US5] Escribir en `backend/tests/test_mercado_pago_conducto.py` la detección de conducto con fixtures puros (mismo `IdOperacion`, mismo día, "Ingreso de dinero", importe opuesto con diferencia menor a $0,01; el pago de UATRE del 04/09/2024, operación 86673304977, no es conducto; un pago con QR sin ingreso emparejado no es conducto)
- [ ] T045 [US5] Agregar a `backend/tests/test_tarjetas_cuenta_cruces.py` las sugerencias y validaciones de `consumo-devolucion` (ingreso de la billetera "Devolución de dinero…" contra un consumo sin proveedor del mismo importe en ±45 días; la línea debe ser de la tarjeta indicada)

### Implementation for User Story 5

- [ ] T046 [US5] Agregar los campos `esConducto` e `idOperacionPar` a los movimientos de Mercado Libre en `backend/src/features/tesoreria/schemas.py` y `backend/src/features/tesoreria/repository.py` (endpoint `GET /api/tesoreria/mercado-libre/movimientos`), sin modificar ningún otro campo
- [ ] T047 [US5] Extender `backend/src/features/tarjetas_cuenta/cruces.py` y `router.py` con la sugerencia y el alta del cruce `consumo-devolucion` (marca el consumo `cruzado-con-devolucion` y el ingreso de la billetera como devolución de compra; sin fila contable nueva)
- [ ] T048 [US5] Mostrar la marca "Conducto" en la lista de movimientos de Mercado Libre de Tesorería (`frontend/src/components/tesoreria/`) y ofrecer el cruce `consumo-devolucion` (oculto para el rol `Lectura`) en `frontend/src/components/tarjetas-cuenta/DialogoCruce.tsx`
- [ ] T049 [US5] Verificar en `WC`: la cuenta de UATRE muestra el pago del 04/09/2024 y cada otro pago mensual una sola vez, el saldo de la billetera es $0,14, y aprobar el cruce de la línea 505 de Visa Galicia con el movimiento 20 (SC-009, SC-010); registrar en `specs/034-cuenta-corriente-tarjetas/quickstart.md`

**Checkpoint**: Mercado Pago sigue las reglas de un banco y el caso Starlink queda resuelto.

---

## Phase 8: User Story 6 - Navegar de la cuenta al detalle (Priority: P3)

**Goal**: desde cada fila llegar al resumen o al movimiento bancario de origen.

**Independent Test**: un clic en un resumen y en un pago de la cuenta abre el detalle correcto (quickstart paso 4).

- [ ] T050 [US6] Agregar a `backend/tests/contract/test_tarjetas_cuenta_api.py` la prueba de la `referencia` de cada tipo de fila (`linea-consumo`, `resumen`, `movimiento-bancario`, `cruce`)
- [ ] T051 [US6] Completar en `backend/src/features/tarjetas_cuenta/repository.py` la `referencia` de cada fila para llegar al resumen de `backend/src/features/tarjetas_resumenes/` o al movimiento de Tesorería
- [ ] T052 [US6] Hacer clicables las filas en `frontend/src/components/tarjetas-cuenta/TarjetaCuentaTabla.tsx` (enlace al resumen en `frontend/src/app/finanzas/tarjetas/resumenes/` y al movimiento bancario de Tesorería) y verificar ambos recorridos

---

## Phase 9: Polish & Cross-Cutting Concerns

- [X] T053 Destino del pago de Mastercard BNA del 05/06/2024 ($15.180,50, "MASTER XXXX3813"): decidido por Sergio el 2026-10-06 (débito indebido del banco contra una tarjeta dada de baja; pérdida y gasto bancario) y aplicado con `backend/scripts/registrar_debito_indebido_mastercard_bna.py` (reasignación al contacto "Banco Nacion", backup previo), registrado en `specs/034-cuenta-corriente-tarjetas/research.md`; con T043 y T053 aplicados se verifica SC-001 para las cinco tarjetas (diferencia menor a $1)
- [ ] T054 Revisión final con el especialista financiero de los resultados medidos y de las diferencias aceptadas; registrar el cierre en `specs/034-cuenta-corriente-tarjetas/research.md`
- [ ] T055 [P] Crear `frontend/tests/tarjetas-cuenta.e2e.cjs` (patrón de `frontend/tests/tarjetas-navegacion.e2e.cjs`) que recorra resumen de tarjetas, cuenta con filtro y exportación, control y aprobación de un cruce con la API simulada
- [ ] T056 Ejecutar la suite completa de `backend/tests/` (`python -m pytest tests -q`), `npx tsc --noEmit` en `frontend/` y el script `frontend/tests/tarjetas-cuenta.e2e.cjs`; corregir lo que falle
- [ ] T057 Actualizar la documentación: nota de la cuenta de tarjeta vigente en `specs/008-tarjetas/spec.md`, estado "implementado" y fecha en `specs/034-cuenta-corriente-tarjetas/spec.md` y resultados finales en `quickstart.md`
- [ ] T058 Hacer el commit y el push a `main` de `backend/src/features/tarjetas_cuenta/`, `backend/scripts/`, `backend/tests/`, `frontend/src/` y `specs/034-cuenta-corriente-tarjetas/`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias; T001 conviene antes de implementar.
- **Foundational (Phase 2)**: depende de Setup y bloquea todas las historias; dentro de la fase T004 a T009 son secuenciales (mismo archivo), T010, T011 y T012 pueden ir en paralelo después de T006, y T013/T014 se ejecutan al final de la fase, con T027 y T028 ya escritas y después del ensayo con rollback.
- **US1 y US2 (P1)**: empiezan al terminar Phase 2; US2 puede ir en paralelo con US1 salvo T029 que necesita los datos de T014.
- **US3 (P2)**: depende de Phase 2 y reutiliza el repositorio de US1 (T018/T019) para no duplicar lecturas.
- **US4 (P2)**: depende de Phase 2 (tabla de cruces y rama de devolución) y comparte la página de control con US3 (T036 antes de T042).
- **US5 (P2)**: depende de Phase 2 (rama `Mercado Pago`) y de T040 (módulo de cruces) para T047.
- **US6 (P3)**: depende de US1.
- **Polish (Phase 9)**: después de las historias elegidas; T053 requiere la decisión de Sergio.

### User Story Dependencies

- US1 y US2 son independientes entre sí y forman el MVP.
- US3, US4 y US5 pueden avanzar en paralelo después de Phase 2; US3 y US4 comparten `control/page.tsx` (T036 antes de T042) y US4 y US5 comparten `cruces.py`, `DialogoCruce.tsx` y `test_tarjetas_cuenta_cruces.py`, por lo que US4 se termina antes de US5 en esos archivos. Las pruebas de contrato (`test_tarjetas_cuenta_api.py`) se agregan en orden (T015, T032, T039, T050) y por eso no llevan marca [P] salvo la primera.
- US6 extiende la tabla de US1.

### Within Each User Story

- Pruebas primero (deben fallar antes de implementar), luego esquemas y repositorio, endpoints y por último la interfaz.
- Cada historia termina con una tarea de verificación contra `WC` registrada en `quickstart.md`.

### Parallel Opportunities

- T003, T010, T011 (y T012 tras T006).
- Dentro de US1: T015 y T016; T023 en paralelo con el backend.
- US2: T027 y T028.
- US3, US4 y US5: las pruebas de fixtures puros de archivos distintos (T031, T038, T044) pueden escribirse al mismo tiempo, y los componentes de frontend marcados [P] en paralelo con el backend de su historia.

---

## Parallel Example: User Story 1

```text
Task: "T015 [P] [US1] Prueba de contrato de resumen y cuenta en backend/tests/contract/test_tarjetas_cuenta_api.py"
Task: "T016 [P] [US1] Prueba de saldo inicial y agrupación en backend/tests/test_tarjetas_cuenta_repository.py"
Task: "T023 [P] [US1] Llamadas de la API en frontend/src/services/tarjetasCuentaApi.ts"
```

---

## Implementation Strategy

### MVP (US1 + US2)

1. Completar Setup y Foundational (con backup verificado y reversión probada).
2. Completar US1: cuenta de cada tarjeta con deuda real.
3. Completar US2: demostrar que los proveedores y el flujo de caja no cambian.
4. **Detenerse y validar** con Sergio antes de seguir: es el punto donde el total general deja de incluir los créditos sin contrapartida de las tarjetas.

### Entrega incremental

1. MVP (US1 + US2).
2. US3 (control) y US4 (devoluciones): resuelven los $990.229,20 de AgroNacion y dejan el saldo en cero.
3. US5 (Mercado Pago): UATRE y el kit Starlink.
4. US6 (navegación) y Polish.

### Riesgos y salvaguardas

- La vista alimenta a otras pantallas: cada cambio de la vista se hace con `--verificar`, instantánea previa, `--comparar` y reversión disponible.
- Ninguna escritura real sin backup verificado; las pruebas automáticas no escriben en `WC`.
- Antes de modificar la vista de `WC`, se ensaya el script completo con `--ensayo` (transacción con rollback) y se comparan saldos y flujo de caja contra la instantánea.
