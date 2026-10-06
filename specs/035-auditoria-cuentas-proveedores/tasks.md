# Tasks: Auditoría de cuentas corrientes de proveedores

**Input**: documentos de diseño en `specs/035-auditoria-cuentas-proveedores/` (plan.md, spec.md, research.md, data-model.md, contracts/auditoria-cuentas-api.md, quickstart.md)

**Prerequisitos**: feature 032 (motor FIFO), feature 034 (tarjetas cerradas), `SaldosReferenciaAccess` cargada al 25/09/2026.

**Tests**: se incluyen (pruebas de funciones puras con fixtures, de contrato y lecturas de solo lectura sobre `WC`), por la constitución (contrato primero y probado).

**Organización**: por historia de usuario; cada una se puede probar por separado. Rutas de aplicación web: `backend/src/`, `frontend/src/`.

## Format: `[ID] [P?] [Story] Descripción con ruta`

- **[P]**: se puede hacer en paralelo (archivos distintos, sin depender de tareas incompletas)
- **[US1]…[US5]**: historia a la que pertenece

---

## Phase 1: Setup

- [X] T001 Crear el paquete `backend/src/features/auditoria_cuentas/` con `__init__.py`, `schemas.py` vacío y `router.py` con `APIRouter(prefix="/api/auditoria-cuentas", tags=["auditoria-cuentas"])`, y registrarlo en `backend/src/main.py` antes de los demás routers de cuentas
- [X] T002 [P] Crear `frontend/src/services/auditoriaCuentasApi.ts` con los tipos y las llamadas del contrato `contracts/auditoria-cuentas-api.md` (resumen, grupos, hallazgos, parámetros, exportar, reglas, correcciones, fifo/estado) usando `apiGet`, `apiPost`, `apiDelete`

---

## Phase 2: Foundational (bloquea todas las historias)

- [X] T003 Escribir `backend/scripts/crear_esquema_auditoria_035.py` (modos `--verificar` sin escritura y aplicar con `backup_verificado`, idempotente) que cree `dbo.AuditoriaParametros` (`Clave` varchar(60) PK, `Valor` varchar(60) NOT NULL, `Usuario` varchar(60), `Fecha` datetime2), `dbo.AuditoriaCorrecciones` (`IdCorreccion` int identity PK, `Regla` varchar(60) NOT NULL, `Estado` varchar(20) con CHECK en `simulada`, `aplicada`, `revertida`, `descartada`, `Parametros` nvarchar(max), `Usuario`, `Fecha`, `UsuarioAplicacion`, `FechaAplicacion` NULL, `Respaldo` varchar(260) NULL, `UsuarioReversion`, `FechaReversion` NULL, `Resumen` nvarchar(max)) y `dbo.AuditoriaCorreccionesCuentas` (`IdCorreccion` FK, `IdContacto`, `Tildada` bit, `SaldoAntes`/`SaldoDespues` money, `IdsAplicacion` nvarchar(max), `Detalle` nvarchar(max), PK `(IdCorreccion, IdContacto)`), con los valores iniciales `plazoMaximoMeses = 24`, `umbralPesos = 300`, `anticipoDias = 60`
- [X] T004 Ejecutar T003 contra `WC` (primero `--verificar`, luego aplicar) y registrar en `specs/035-auditoria-cuentas-proveedores/quickstart.md` ("Resultados de la corrida") el respaldo usado y las tablas creadas
- [X] T005 Implementar en `backend/src/features/auditoria_cuentas/datos.py` la carga de solo lectura: saldo por contacto de `vw_MovimientosCuenta_Base` hasta la fecha de corte, `SaldosReferenciaAccess` (con su `FechaCorte`), las aplicaciones vigentes de `AplicacionesPago` (`Anulada = 0`) con la fecha de la factura (`Compras.Fecha`) y la fecha real del movimiento de pago (BNA, Galicia, efectivo, valores recibidos, tarjetas), los vínculos de `Tarjetas_Resumenes_Lineas_Compras`, `ReasignacionesContacto`, `AjustesCuentaCorriente` y las entidades excluidas de `recalculo_fifo.entrada.EXCLUIDOS`
- [X] T006 Implementar en `backend/src/features/auditoria_cuentas/parametros.py` la lectura y escritura de `AuditoriaParametros` (`obtener()` y `guardar(clave, valor, usuario)`) con validación de entero positivo y exposición de `GET` y `PUT /parametros` en `router.py` (422 si el valor no es un entero positivo)
- [X] T007 [P] Definir en `backend/src/features/auditoria_cuentas/schemas.py` los modelos de respuesta: `ParametrosAuditoria`, `CausaResumen`, `ResumenAuditoria`, `CuentaAuditada`, `GrupoCuentas`, `Hallazgo`, `HallazgosCuenta`, `ReglaCorreccion`, `CuentaCorreccion`, `Correccion`, `FifoEstado`, con las causas del `data-model.md` (`coincide`, `coincide-causa-conocida`, `diferencia-menor-umbral`, `aplicacion-fuera-de-plazo`, `doble-descuento-tarjeta`, `nota-sin-imputar`, `impuesto-sin-boleta`, `movimiento-sin-contacto`, `falta-documento`, `sin-referencia`, `otros`)

**Checkpoint**: tablas creadas, carga de datos y parámetros disponibles.

---

## Phase 2b: User Story 0 - Revisar y corregir una cuenta (Priority: P1) 🎯 NUEVA PRIORIDAD

**Goal**: la pantalla de revisión de una cuenta con todo el detalle, corrección en el lugar, marca de revisada y navegación alfabética de fáciles a complicadas.

**Independent Test**: abrir una cuenta, ver movimientos con saldo acumulado y avisos, corregir un movimiento, marcarla revisada y pasar a la siguiente.

- [X] T044 [US0] Agregar a `backend/scripts/crear_esquema_auditoria_035.py` y crear en `WC` (con respaldo) `dbo.AuditoriaRevisiones` (`IdContacto` int PK, `SaldoEsperado` varchar(20) NULL con CHECK en `cero` o `puede-tener-saldo`, `Estado` varchar(20) con CHECK en `pendiente` o `revisada`, `FechaRevision` datetime2 NULL, `Usuario` varchar(60) NULL, `Nota` varchar(500) NULL, `SaldoAlRevisar` money NULL) y `dbo.AuditoriaRevisionesHistorial` (`IdHistorial` int identity PK, `IdContacto`, `Accion` varchar(40), `Detalle` nvarchar(max), `Usuario`, `Fecha`)
- [X] T045 [P] [US0] Pruebas con fixtures puros en `backend/tests/test_auditoria_revision.py`: orden alfabético de fáciles a complicadas (dificultad 0 sin avisos, 1 con diferencia menor o de causa conocida, 2 con excepciones), salto de las ya revisadas, aviso de revisión vieja cuando cambió el saldo y aviso de saldo esperado cero no cumplido
- [X] T046 [US0] Crear `backend/src/features/auditoria_cuentas/revision.py` con las funciones puras (`dificultad`, `orden_de_revision`, `estado_de_revision`) y la lectura y escritura de `AuditoriaRevisiones` y su historial
- [X] T047 [US0] Exponer en `backend/src/features/auditoria_cuentas/router.py` `GET /cuentas/{idContacto}/revision` (estado, saldo esperado, avisos de la cuenta, anterior y siguiente), `PUT /cuentas/{idContacto}/revision` (marcar revisada o pendiente con nota, y saldo esperado) y `GET /revision/siguiente` (la próxima sin revisar), más pruebas de contrato en `backend/tests/contract/test_auditoria_cuentas_api.py`
- [X] T048 [P] [US0] Agregar a `frontend/src/services/auditoriaCuentasApi.ts` las llamadas de revisión y crear `frontend/src/app/finanzas/auditoria-cuentas/cuenta/[idContacto]/page.tsx` con `frontend/src/components/auditoria-cuentas/RevisionCuenta.tsx`: lista de movimientos con saldo acumulado (reutiliza `fetchMovimientos` y `OrigenMovimiento` de cuentas corrientes), avisos de la cuenta, saldo esperado, "Marcar revisada" con nota, botón "Siguiente cuenta" y enlace desde cada cuenta de los grupos
- [X] T049 [US0] Agregar a cada fila de la revisión el enlace al comprobante original (`Compras.[Documento Original]` por `urlParaAbrirDocumento` o el origen del movimiento) y el cambio de contacto con `ReasignarMovimientoButton`
- [X] T050 [US0] Crear en `backend/src/features/auditoria_cuentas/correcciones.py` `anular_aplicaciones(idContacto, idsAplicacion, motivo, usuario)` y `revertir(idCorreccion)` (baja lógica con `AplicacionesPago.Anulada`, registro en `AuditoriaCorrecciones` y `AuditoriaCorreccionesCuentas`, respaldo verificado, saldo antes y después iguales), con `POST /cuentas/{idContacto}/anular-aplicaciones` y `POST /correcciones/{id}/revertir`, y agregar a los hallazgos de plazo y de doble descuento los `idsAplicacion`
- [X] T051 [US0] Crear en `backend/src/features/auditoria_cuentas/ajustes.py` `cargar_nota_ajuste(idContacto, tipo, fecha, importe, moneda, motivo, usuario)` que cargue una nota de débito o de crédito "SIN DOCUMENTO" con la marca de ajuste (con `compras.repository.create_compra`) y su `POST /cuentas/{idContacto}/nota-ajuste`
- [X] T052 [US0] Agregar a `RevisionCuenta.tsx` los diálogos "Anular imputaciones" (desde un aviso), "Cargar nota de ajuste" y el historial de cambios de la cuenta (ocultos para el rol `Lectura`)
- [ ] T053 [US0] Asignación de contacto a movimientos del banco sin contacto uno a uno, varios a la vez y por regla desde el grupo `movimiento-sin-contacto` (reutiliza `reasignacion_contacto`)
- [X] T054 [US0] Prueba de navegador `frontend/tests/auditoria-cuentas.e2e.cjs`: abrir una cuenta, ver saldo acumulado, marcar revisada y pasar a la siguiente; y registrar en `quickstart.md`

**Checkpoint**: Sergio entra a una cuenta, la revisa, corrige y avanza a la siguiente.

---

## Phase 3: User Story 1 - Ver de una vez el estado de todas las cuentas (Priority: P1) 🎯 MVP

**Goal**: pantalla de control con todas las cuentas comparadas contra el Access al corte y las diferencias agrupadas por causa.

**Independent Test**: con los datos al 25/09/2026, el resumen informa 513 cuentas, 436 que coinciden (incluidas las "coincide con causa conocida") y el resto agrupado; ninguna cuenta queda sin causa (quickstart pasos 2 y 5).

### Tests for User Story 1

- [X] T008 [P] [US1] Escribir con fixtures puros en `backend/tests/test_auditoria_clasificacion.py` las causas `coincide`, `coincide-causa-conocida` (diferencia explicada por fuentes que el Access no contaba, reasignaciones y filas posteriores al congelamiento), `diferencia-menor-umbral` (menor a $300 solo en pesos; en dólares nunca), `sin-referencia`, `otros`, la exclusión de lo posterior al corte, y que una cuenta con varias causas cuente una sola vez en el total con diferencia (FR-001, FR-002, FR-003)
- [X] T009 [P] [US1] Escribir en `backend/tests/contract/test_auditoria_cuentas_api.py` las pruebas de `GET /resumen`, `GET /grupos/{causa}` y `GET /parametros` (suma de cuentas de todos los grupos igual al total, `excepcion` falso en los grupos de coincidencia, 422 para una causa desconocida)

### Implementation for User Story 1

- [X] T010 [US1] Implementar en `backend/src/features/auditoria_cuentas/clasificacion.py` la función pura `clasificar_cuentas(datos, parametros)` que calcule `diferencia = saldo WC al corte − saldo Access` y la descomponga en fuentes no contadas por el Access, reasignaciones y filas posteriores al congelamiento (research D4), dejando `sinExplicar`, y asigne la causa principal con el umbral solo en pesos
- [X] T011 [US1] Validar contra `WC` que `clasificar_cuentas` reproduce la clasificación del 01/10/2026 (325 coinciden tal cual, 137 al quitar fuentes que el Access no contaba, 26 al quitar filas nuevas, 25 correcciones deliberadas; 436 cuentas cierran); si no la reproduce, ajustar la lista de fuentes en `clasificacion.py` y registrar el resultado y los ajustes en `specs/035-auditoria-cuentas-proveedores/research.md`
- [X] T012 [US1] Exponer en `backend/src/features/auditoria_cuentas/router.py` `GET /resumen`, `GET /grupos/{causa}` y `GET /cuentas/{idContacto}/hallazgos` según el contrato (los hallazgos de plazo y de doble descuento los completan US2)
- [X] T013 [P] [US1] Crear `frontend/src/components/auditoria-cuentas/ResumenCausas.tsx` (total, cuántas coinciden, causas con cantidad e importe, aviso de corte, y los grupos que no son excepción en un bloque aparte) y `frontend/src/components/auditoria-cuentas/GrupoExcepciones.tsx` (cuentas del grupo con saldo del sistema, del Access, diferencia y enlace a su cuenta corriente)
- [X] T014 [US1] Crear `frontend/src/app/finanzas/auditoria-cuentas/page.tsx` con el resumen, el acceso a cada grupo y el panel de parámetros (`ParametrosAuditoria.tsx`), y agregar el acceso en `frontend/src/components/layout/NavHeader.tsx`
- [X] T015 [US1] Verificar la historia: `python -m pytest tests/test_auditoria_clasificacion.py tests/contract/test_auditoria_cuentas_api.py -q`, `npx tsc --noEmit` y medir que el resumen responde en menos de 10 segundos (SC-001); registrar en `quickstart.md`

**Checkpoint**: Sergio ve el estado de todas las cuentas por causa.

---

## Phase 4: User Story 2 - Detectar pagos aplicados fuera de plazo y doble descuento (Priority: P1)

**Goal**: el control marca las aplicaciones de pagos a facturas con más de 24 meses entre factura y movimiento de pago, y las que duplican lo ya pagado con tarjeta.

**Independent Test**: sin señalarlos aparecen Cargill (movimiento Galicia 3240, contacto 258), Cooperativa y Lartirigoyen (doble descuento) y Nidera (nota sin imputar); con plazo 12 aumentan los hallazgos y con 24 vuelven al valor anterior (quickstart pasos 3, 4 y 6).

### Tests for User Story 2

- [X] T016 [P] [US2] Agregar a `backend/tests/test_auditoria_clasificacion.py` las pruebas del plazo (medido entre `Compras.Fecha` y la fecha del movimiento de pago y no la de creación de la aplicación; anticipos de hasta 60 días normales y mayores marcados; agrupación por movimiento de pago; solo origen `automatica-exacta` y `automatica-mejor-esfuerzo`, con `fifo-032` y `manual` informados aparte), del doble descuento con tarjeta (aplicación automática sobre una factura con vínculo de tarjeta por el mismo importe o más) y de la nota sin imputar (FR-004, FR-005, FR-006, FR-007)
- [X] T017 [US2] Agregar a `backend/tests/contract/test_auditoria_cuentas_api.py` la prueba de `GET /cuentas/{idContacto}/hallazgos` para el contacto 258 (movimiento 3240 de Galicia con `cantidadFacturas`, `facturaMasVieja` y `diasMaximos`) y la de cambio de plazo con `PUT /parametros`

### Implementation for User Story 2

- [X] T018 [US2] Implementar en `backend/src/features/auditoria_cuentas/clasificacion.py` las funciones puras `hallazgos_plazo`, `hallazgos_doble_descuento` y `hallazgos_nota_sin_imputar` según research D1, D2 y D3, y que `clasificar_cuentas` asigne las causas `aplicacion-fuera-de-plazo`, `doble-descuento-tarjeta` y `nota-sin-imputar`
- [X] T019 [US2] Implementar en `backend/src/features/auditoria_cuentas/clasificacion.py` las causas restantes de FR-002 y FR-018: `impuesto-sin-boleta` (los organismos pasan a ser cuentas auditables; un saldo a nuestro favor por encima del umbral es un pago sin boleta; solo se clasifica, el relleno de boletas queda fuera de alcance), `movimiento-sin-contacto` (solo movimientos de $100.000 o más, sin conciliación ni cruce, que no sean impuestos o comisiones del banco ni movimientos propios), `sobrepago` (pago aplicado de más que no es anticipo), `contacto-duplicado` (mismo CUIT, o misma descripción si no hay CUIT; solo se informa agrupado, no se unifica) y `fuera-de-plazo-decidido` (aplicaciones `manual` o `fifo-032` que superan el plazo: grupo aparte que no cuenta como excepción), con la medición de Cargill y demás acopiadores en dólares y sin tratar la compensación como error por sí sola; agregar sus pruebas a `backend/tests/test_auditoria_clasificacion.py`
- [X] T020 [US2] Completar en `router.py` `GET /cuentas/{idContacto}/hallazgos` con los hallazgos de plazo, doble descuento y nota sin imputar, cada uno con `medio` e `idMovimiento` para abrir el movimiento en Tesorería y con el motivo en español simple (FR-016)
- [X] T021 [P] [US2] Mostrar en `frontend/src/components/auditoria-cuentas/GrupoExcepciones.tsx` el detalle de cada hallazgo (pago, factura más vieja, días, importe, motivo) con el enlace a Tesorería y a la cuenta corriente
- [X] T022 [US2] Verificar contra `WC` los casos conocidos (SC-002) y la medición del plazo (2.194 aplicaciones `automatica-exacta`, Banco Nación 1.477 y Galicia 717, en unos 110 contactos, agrupadas por movimiento); registrar en `quickstart.md` y anotar en `research.md` cualquier diferencia con la medición previa

**Checkpoint**: Cargill, Cooperativa, Lartirigoyen y Nidera aparecen solos con su causa.

---

## Phase 5: User Story 3 - Completar el recálculo FIFO para todos los contactos (Priority: P2)

**Goal**: FIFO aplicado a todos los contactos, sin cambiar ningún saldo, con aprobación de Sergio, respaldo y reversión.

**Independent Test**: la simulación con todos los contactos deja el saldo idéntico antes y después, las que no cierran quedan en `CuentasARevisar` y aplicar y revertir deja los datos exactamente como estaban (quickstart paso 8).

### Tests for User Story 3

- [ ] T023 [P] [US3] Agregar a `backend/tests/contract/test_auditoria_cuentas_api.py` la prueba de `GET /fifo/estado` (contactos aplicados, pendientes, cuentas a revisar y última simulación) y escribir en `backend/tests/test_auditoria_fifo_alcance.py` la prueba pura del cálculo del alcance (todos los contactos menos las entidades de `EXCLUIDOS`, las cuentas de `CuentasARevisar` abiertas y la caja sin contacto)

### Implementation for User Story 3

- [ ] T024 [US3] Implementar `GET /fifo/estado` en `backend/src/features/auditoria_cuentas/router.py` leyendo `RecalculoFifoEjecucion`, `RecalculoFifoAplicacion`, `RecalculoFifoContacto` y `CuentasARevisar`, sin escribir
- [ ] T025 [US3] Escribir `backend/scripts/fifo_completo_035.py` que calcule el alcance (todos los contactos menos exclusiones), cree la simulación con `recalculo_fifo.ejecuciones.simular` por tandas ordenadas por volumen, imprima por tanda cuántas cierran, mejoran o empeoran y la lista de excepciones, y NO aplique nada (solo simula)
- [ ] T026 [US3] Correr T025 contra `WC`, revisar con Sergio la simulación (cuentas que empeoran o no cierran) y registrar el resumen en `quickstart.md` (SC-004: saldo antes y después idéntico en todas)
- [ ] T027 [US3] Con la aprobación explícita de Sergio de cada tanda, aplicar desde Finanzas → Recálculo FIFO (respaldo verificado previo) y verificar que el saldo de todas las cuentas es idéntico y que revertir deja todo como estaba; cerrar o dejar en `CuentasARevisar` cada excepción con su motivo (FR-009, FR-011)
- [ ] T028 [P] [US3] Mostrar en `frontend/src/app/finanzas/auditoria-cuentas/page.tsx` el estado del FIFO (contactos aplicados y pendientes, cuentas a revisar con su motivo, enlace a Recálculo FIFO) y el historial de cambios de imputación sin informarlos como diferencia (FR-017)

**Checkpoint**: FIFO completo aplicado, saldos intactos.

---

## Phase 6: User Story 4 - Corregir por causa, con respaldo y reversible (Priority: P2)

**Goal**: una regla de corrección por grupo, con las cuentas tildadas una a una, respaldo verificado y reversión exacta.

**Independent Test**: simular la regla del doble descuento, tildar una cuenta, aplicar, verificar saldo antes igual al saldo después y que la cuenta sale del grupo; revertir la devuelve y deja las aplicaciones como estaban (quickstart paso 7).

### Tests for User Story 4

- [ ] T029 [P] [US4] Escribir en `backend/tests/test_auditoria_correcciones.py` las pruebas de la regla `anular-doble-descuento-tarjeta` (qué aplicaciones anula, saldo antes igual a saldo después, ninguna cuenta tildada de antemano) y las validaciones: solo se aplica si está simulada, tiene al menos una cuenta tildada y no está aplicada; si el saldo de una cuenta cambió desde la simulación se rechaza; revertir devuelve `Anulada = 0` en exactamente las aplicaciones de `IdsAplicacion` (FR-012, FR-013)
- [ ] T030 [US4] Agregar a `backend/tests/contract/test_auditoria_cuentas_api.py` las pruebas de `GET /reglas`, `POST /correcciones/simular` (201, 422), `PUT /correcciones/{id}/cuentas`, `POST /aplicar` (409 sin cuentas tildadas, 409 si cambió el saldo, 403 para el rol `Lectura`), `POST /revertir` (409 si no estaba aplicada), `DELETE /correcciones/{id}` y `GET /correcciones`, usando una regla con simulación sin escritura

### Implementation for User Story 4

- [ ] T031 [US4] Implementar en `backend/src/features/auditoria_cuentas/correcciones.py` el registro de reglas con `simular` (crea `AuditoriaCorrecciones` en estado `simulada` y una fila por cuenta en `AuditoriaCorreccionesCuentas` con `Tildada = 0`, saldo antes y después y el detalle en texto simple), `tildar`, `aplicar` (valida el estado y el saldo, crea `backup_verificado`, anula en una sola transacción las aplicaciones de las cuentas tildadas con `Anulada = 1`, `MotivoAnulacion` de la regla, `UsuarioAnulacion`, `FechaAnulacion`, y guarda `IdsAplicacion` para revertir), `revertir` y `descartar`; primera regla `anular-doble-descuento-tarjeta` (research D3); nunca borra filas y nunca escribe en `LaHerencia`
- [ ] T032 [US4] Exponer en `router.py` los endpoints de reglas y correcciones del contrato, con el usuario actual tomado como en `tarjetas_cuenta/router.py` (`_usuario_actual`) y los códigos de error del contrato
- [ ] T033 [P] [US4] Crear `frontend/src/components/auditoria-cuentas/DialogoCorreccion.tsx` con la regla elegida, la lista de cuentas con el efecto previsto por cuenta (importes y saldo antes y después), casillas sin tildar de antemano, "Aplicar" con confirmación en español simple, historial y "Revertir" (botones ocultos para el rol `Lectura` con `SoloLectura`), y conectarlo al grupo `doble-descuento-tarjeta` en `GrupoExcepciones.tsx`
- [ ] T034 [US4] Aplicar con Sergio la regla de doble descuento sobre Cooperativa y Lartirigoyen desde la pantalla (cuentas tildadas por él), verificar saldo antes igual a saldo después y que salen del grupo, y registrar en `quickstart.md` (SC-007)
- [ ] T035 [US4] Para las excepciones que necesitan un dato externo (recibo de la retención del certificado 32 de Lartirigoyen, nota 7028-00011189 de Nidera) mostrar la causa `falta-documento` o `nota-sin-imputar` con lo que hay que conseguir, sin inventar datos, y dejar anotado cada caso en `research.md`

**Checkpoint**: Sergio corrige por causa y puede revertir.

---

## Phase 7: User Story 5 - Exportar la lista de excepciones (Priority: P3)

**Goal**: exportar a Excel cada grupo, o todas las excepciones.

**Independent Test**: el archivo exportado trae las mismas cuentas e importes que la pantalla, más fecha de corte y parámetros (quickstart paso 9).

- [ ] T036 [P] [US5] Escribir en `backend/tests/contract/test_auditoria_cuentas_api.py` la prueba de `GET /exportar` y `GET /exportar?causa=` (archivo `.xlsx`, mismas cuentas e importes que `GET /grupos/{causa}`, hoja con fecha de corte y parámetros)
- [ ] T037 [US5] Crear `backend/src/features/auditoria_cuentas/exportacion.py` con el Excel (reutilizar los ayudantes `_hoja`, `_cerrar`, `_bytes` y los formatos de `cuentas_corrientes/exportacion.py`) y exponer `GET /exportar` en `router.py`
- [ ] T038 [P] [US5] Agregar el enlace "Exportar a Excel" a `ResumenCausas.tsx` y a `GrupoExcepciones.tsx`

---

## Phase 8: Polish & Cross-Cutting

- [ ] T039 Revisión final con el especialista financiero de las reglas (plazo, doble descuento, descomposición de la diferencia) y de los resultados medidos; registrar el cierre y las diferencias aceptadas en `specs/035-auditoria-cuentas-proveedores/research.md`
- [ ] T040 [P] Crear `frontend/tests/auditoria-cuentas.e2e.cjs` (patrón de `frontend/tests/tarjetas-cuenta.e2e.cjs`) que recorra el resumen por causa, un grupo, el cambio de plazo, la simulación y aplicación de una corrección y la exportación con la API simulada
- [ ] T041 Ejecutar la suite completa `python -m pytest tests -q`, `npx tsc --noEmit` en `frontend/` y `node tests/auditoria-cuentas.e2e.cjs` con el servidor en el puerto 3100; corregir lo que falle
- [ ] T042 Medir SC-005 (las 436 cuentas que hoy coinciden siguen coincidiendo después de las correcciones) y SC-006 (menos de 30 cuentas en "otros") y registrar los resultados finales en `quickstart.md`
- [ ] T043 Actualizar el estado de `specs/035-auditoria-cuentas-proveedores/spec.md` a "Implementado" con la fecha, y hacer el commit y el push a `main` de `backend/src/features/auditoria_cuentas/`, `backend/scripts/`, `backend/tests/`, `frontend/src/`, `frontend/tests/` y `specs/035-auditoria-cuentas-proveedores/`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias.
- **Foundational (Phase 2)**: depende de Setup y bloquea todas las historias.
- **US1 (P1)**: depende de Phase 2. Es el MVP.
- **US2 (P1)**: depende de Phase 2 y completa los hallazgos que consume el router de US1 (T012/T020); se puede hacer después de US1 o en paralelo con T018 antes que T020.
- **US3 (P2)**: depende de Phase 2; es independiente de US1/US2 salvo la pantalla (T028 después de T014).
- **US4 (P2)**: depende de US2 (sus hallazgos de doble descuento definen qué aplicaciones se anulan).
- **US5 (P3)**: depende de US1.
- **Polish**: al final.

### Within Each User Story

- Las pruebas se escriben antes de la implementación y deben fallar primero.
- Funciones puras antes que el router; el router antes que la interfaz.
- Toda escritura en `WC` va con respaldo verificado previo y la aprobación de Sergio.

### Parallel Opportunities

- T002 y T007 en paralelo con el resto de Phase 2.
- T008 y T009 (US1); T016 (US2); T023 (US3); T029 (US4); T036 (US5): pruebas de archivos distintos.
- Los componentes de frontend marcados [P] en paralelo con el backend de su historia.

---

## Parallel Example: User Story 1

```text
Task: "T008 [P] [US1] Pruebas de clasificación en backend/tests/test_auditoria_clasificacion.py"
Task: "T009 [P] [US1] Pruebas de contrato en backend/tests/contract/test_auditoria_cuentas_api.py"
Task: "T013 [P] [US1] Componentes ResumenCausas.tsx y GrupoExcepciones.tsx"
```

---

## Implementation Strategy

### MVP primero (US1)

1. Phase 1 y 2 (esquema, datos, parámetros).
2. US1: el control por causa. **Parar y validar**: reproducir la clasificación del 01/10 (T011) antes de seguir; es el riesgo principal.
3. US2: plazo y doble descuento: los cuatro casos conocidos aparecen solos.

### Entrega incremental

4. US3: FIFO completo (simular, revisar con Sergio, aplicar por tandas).
5. US4: correcciones por regla (primero Cooperativa y Lartirigoyen).
6. US5: exportación. Luego Polish y cierre.

### Reglas de trabajo

- Un frente a la vez; no reabrir lo cerrado (tarjetas y Mercado Pago, 034).
- Impuestos sin boleta y residuos menores quedan fuera de alcance.
- Nada se escribe en `LaHerencia`; toda aplicación es reversible y con respaldo.
