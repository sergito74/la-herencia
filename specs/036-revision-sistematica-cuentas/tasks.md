# Tasks: Método sistemático de revisión, conciliación y FIFO de cuentas

**Input**: documentos de diseño en `specs/036-revision-sistematica-cuentas/` (plan.md, spec.md, research.md, data-model.md, contracts/revision-cuentas-api.md, quickstart.md)

**Prerequisitos**: feature 035 (auditoría de cuentas, hallazgos, correcciones registradas, `AuditoriaRevisiones*`), feature 032 (motor FIFO), feature 034 (tarjetas), base `WC` con corte de movimientos al 30/09/2026.

**Tests**: se incluyen (pruebas de funciones puras con fixtures, de contrato y lecturas de solo lectura sobre `WC`), por la Constitución (contrato primero y probado). Las pruebas de cada historia se escriben antes de implementarla y deben fallar primero.

**Organización**: por historia de usuario; cada una se puede probar por separado. Rutas de aplicación web: `backend/src/`, `frontend/src/`.

## Format: `[ID] [P?] [Story] Descripción con ruta`

- **[P]**: se puede hacer en paralelo (archivos distintos, sin depender de tareas incompletas)
- **[US1]…[US7]**: historia a la que pertenece (ver `spec.md`)

---

## Phase 1: Setup

- [X] T001 Crear el paquete `backend/src/features/revision_cuentas/` con `__init__.py`, `schemas.py` vacío y `router.py` con `APIRouter(prefix="/api/revision-cuentas", tags=["revision-cuentas"])`, y registrarlo en `backend/src/main.py` junto a los demás routers de cuentas
- [X] T002 [P] Crear `frontend/src/services/revisionCuentasApi.ts` con los tipos y las llamadas de `contracts/revision-cuentas-api.md` (corte, tablero, fotos, preguntas, colas, reglas, lotes, ficha, inventario, pagos sin factura, saldos externos, archivos incompletos) usando los mismos ayudantes `apiGet`, `apiPost`, `apiPut`, `apiDelete` que `frontend/src/services/auditoriaCuentasApi.ts`

---

## Phase 2: Foundational (bloquea todas las historias)

- [X] T003 Escribir `backend/scripts/crear_esquema_revision_036.py` (modos `--verificar` sin escritura y aplicar con `backup_verificado`, idempotente, mismo patrón que `crear_esquema_auditoria_035.py`) que cree: `dbo.RevisionCortes` (`IdCorte` int identity PK, `Corte` date NOT NULL, `Motivo` varchar(200) NULL, `Usuario` varchar(60) NOT NULL, `Fecha` datetime2 NOT NULL por defecto ahora); `dbo.RevisionFichas` (`IdContacto` int PK, `Estado` varchar(24) NOT NULL con CHECK en `pendiente`, `en-proceso`, `esperando-evidencia`, `esperando-sergio`, `cerrada`, `cerrada-con-excepcion` y por defecto `pendiente`, `InventarioFuentes` nvarchar(max) NULL, `Nota` varchar(500) NULL, `PreguntaBloqueante` varchar(300) NULL, `Corte` date NULL, `SaldoAlCierre` money NULL, `Moneda` varchar(10) NULL, `MotivoExcepcion` varchar(500) NULL, `UsuarioCierre` varchar(60) NULL, `FechaCierre` datetime2 NULL, `UsuarioActualiza` varchar(60) NULL, `FechaActualiza` datetime2 NOT NULL); `dbo.RevisionPagosSinFactura` (`IdMarca` int identity PK, `IdContacto` int NOT NULL, `Medio` varchar(20) NOT NULL, `IdMovimiento` int NOT NULL, `Estado` varchar(24) NOT NULL con CHECK en `pendiente`, `factura-cargada`, `sin-documento`, `anticipo`, `IdCompra` int NULL, `Nota` varchar(500) NULL, `Usuario` varchar(60) NOT NULL, `Fecha` datetime2 NOT NULL, e índice único filtrado por (`IdContacto`, `Medio`, `IdMovimiento`) para la marca vigente); `dbo.RevisionSaldosExternos` (`IdSaldoExterno` int identity PK, `IdContacto` int NOT NULL, `FechaSaldo` date NOT NULL, `Saldo` money NOT NULL, `Moneda` varchar(10) NOT NULL (`Pesos` o `Dolares`), `Fuente` varchar(20) NOT NULL con CHECK en `portal`, `pdf`, `mail`, `banco`, `tarjeta`, `sin-estado`, `Referencia` varchar(400) NULL, `Nota` varchar(500) NULL, `Usuario` varchar(60) NOT NULL, `Fecha` datetime2 NOT NULL, `Anulado` bit NOT NULL por defecto 0); `dbo.RevisionTableroFotos` (`IdFoto` int identity PK, `Semana` date NOT NULL único, `Corte` date NOT NULL, `Datos` nvarchar(max) NOT NULL, `Usuario` varchar(60) NULL, `Fecha` datetime2 NOT NULL); e inserte en `RevisionCortes` el corte `2026-09-30` con motivo "Primer corte: cierre del mes 9" si la tabla está vacía
- [X] T004 Ejecutar T003 contra `WC` (primero `--verificar`, luego aplicar) y registrar en `specs/036-revision-sistematica-cuentas/quickstart.md` ("Resultados de la corrida") el respaldo usado y las tablas creadas
- [X] T005 Implementar en `backend/src/features/revision_cuentas/datos.py` la carga de solo lectura por cuenta desde `vw_MovimientosCuenta_Base`: movimientos con `Fecha`, `Origen`, `IdOrigen`, `Deuda`, `Credito`; la cantidad de movimientos y el volumen en pesos por contacto (misma fuente de volumen que `fifo_plan.py`); el saldo (crédito menos deuda) hasta una fecha de corte; las facturas con su importe de `vw_Compras_ImporteDocumento`; y las retenciones de `Retenciones`. Debe reutilizar `src/db/connection.py` y no escribir. Para clientes y cuentas mixtas debe devolver además, por origen, los documentos de venta que ya generan movimiento en la cuenta (liquidaciones de venta de granos y de hacienda, alquileres) y el sentido de la cuenta (proveedor, cliente o mixta)
- [X] T006 [P] Definir en `backend/src/features/revision_cuentas/schemas.py` los modelos pydantic del contrato: corte, casilla del tablero, tablero, comparación, foto, pregunta, cuenta de cola, cola, regla, lote, criterio, ficha, pago sin factura, consistencia, saldo externo y archivo incompleto, con los nombres de campo de `contracts/revision-cuentas-api.md`
- [X] T007 Implementar `GET /corte` y `PUT /corte` en `backend/src/features/revision_cuentas/router.py` y en un `fichas.py` inicial (funciones `corte_vigente()` y `fijar_corte(corte, motivo, usuario)`): `PUT` crea una fila nueva y no sobrescribe; 422 si la fecha es futura; el usuario sale como en `auditoria_cuentas/router.py` (`_usuario_actual`) y el rol `Lectura` recibe 403
- [X] T008 [P] Escribir `backend/tests/contract/test_revision_cuentas_api.py` con la prueba de `GET /corte` (devuelve 2026-09-30 tras T004), de `PUT /corte` (fila nueva, 422 si es futuro, 403 para `Lectura`) usando una base simulada o una corrida sin escritura

**Checkpoint**: tablas creadas en `WC`, corte vigente y lectura de datos funcionando.

---

## Phase 3: User Story 1 — Encontrar los documentos que faltan (Priority: P1) 🎯 MVP

**Meta**: el detector lista los pagos sin factura de una cuenta con importe y fecha esperados de la factura faltante, y Sergio los marca; es lo que habría encontrado Jauregui.

**Prueba independiente**: sobre la fixture de Jauregui antes del 09/10/2026, el detector devuelve los 8 pagos esperados y ningún pago con factura.

### Tests de US1

- [X] T009 [US1] Escribir `backend/scripts/exportar_fixture_jauregui_036.py` (solo lectura) que guarde en `backend/tests/fixtures/jauregui_antes.json` los movimientos de `vw_MovimientosCuenta_Base` del contacto 48 sin las compras con `IdOrigen` de 2143522625 a 2143522634 (las 10 facturas cargadas el 09/10/2026), con `Fecha`, `Origen`, `IdOrigen`, `Deuda`, `Credito` y `Nro Documento`; y ejecutarlo
- [X] T009b [US1] Exportar a `backend/tests/fixtures/cliente_mixta.json` (solo lectura, con un script `backend/scripts/exportar_fixture_cliente_036.py`) los movimientos de una cuenta de cliente o mixta (por ejemplo Cargill, contacto 258, o una cuenta de cliente más chica que Sergio elija), con `Fecha`, `Origen`, `IdOrigen`, `Deuda`, `Credito` y `Nro Documento`, para validar la inversión de papeles del detector (research D1, "Cuentas de clientes y mixtas")
- [X] T010 [P] [US1] Escribir `backend/tests/test_revision_detector.py` con pruebas de las funciones puras de `detector.py`: la fixture de Jauregui devuelve exactamente los 8 pagos esperados (20.000,04; 79.114,02; 1.563.484,73 con retención asociada de 18.515,27 y `importeEsperadoFactura` 1.582.000,00; 30.017,03; 33.000,00; 39.011,00; 43.056,90; 46.044,04); el pago de 10.594,55 del 06/01/2025 NO figura (su retención de 14.405,49 está 21 días antes); un pago que cubre más de 4 facturas seguidas se empareja por corrida FIFO con `confianza` `media`; un pago de tarjeta no cuenta como pago sin factura; los pagos anteriores al 01/01/2021 llevan `anteriorA2021` verdadero; `consistencia.cierra` es verdadero cuando pagos sin factura menos facturas sin pago explica el saldo; cada `Origen` de la vista (`Banco Nacion`, `Galicia`, `Pagos efectivo`, `Tarjetas`, `Retenciones`, `Cobros Valores Recibidos`, `Pagos Valores Recibidos`, `Venta Granos`) se traduce al `Medio` del modelo de datos según su tabla de mapeo; en la fixture `cliente_mixta.json` un cobro cubierto por una liquidación de venta de granos no figura como pago sin factura (US1 escenario 6)
- [X] T011 [P] [US1] Agregar a `backend/tests/contract/test_revision_cuentas_api.py` las pruebas de `GET /cuentas/{id}/pagos-sin-factura` (forma de la respuesta y `consistencia`) y `PUT /cuentas/{id}/pagos-sin-factura/{medio}/{idMovimiento}` (422 si `sin-documento` no trae `nota`; la marca se conserva en el siguiente `GET`; 403 para `Lectura`; 404 si el movimiento no existe)

### Implementación de US1

- [X] T012 [US1] Implementar en `backend/src/features/revision_cuentas/detector.py` las funciones puras del detector (research D1): pasada 1 (un pago contra una factura o contra 2 a 4 facturas, diferencia de hasta $1, facturas hasta 600 días antes y hasta 7 días después, probando las 14 facturas libres más cercanas en fecha), pasada 2 (pago más retención cercana, ventana de 45 días), pasada 3 (corrida FIFO contra las facturas libres más viejas para pagos de más de 4 facturas), control de consistencia (pagos sin factura menos facturas sin pago contra el saldo) y `confianza` `alta`/`media`; el débito bancario que cancela una tarjeta no entra (FR-016); en cuentas de clientes y mixtas invierte los papeles (el cobro es el "pago" y el documento de venta es la "factura") y toma como respaldo las liquidaciones de venta de granos y de hacienda y los alquileres (research D1); el saldo inicial del Access queda fuera de esta entrega y el control de consistencia informa "sin apertura" en las cuentas que arrancan antes de 2011 sin contarlo como detector sin cerrar (research D8)
- [X] T013 [US1] Agregar en `detector.py` el cálculo de `importeEsperadoFactura` (pago más retención asociada) y del rango `fechaEsperadaDesde` y `fechaEsperadaHasta` (research D2): fecha del pago menos la mediana de días factura→pago de las parejas emparejadas de la cuenta en los últimos 24 meses, 7 días si no hay parejas, con rango de ±4 días
- [X] T014 [US1] Implementar en `backend/src/features/revision_cuentas/evidencia.py` la lectura y escritura de `RevisionPagosSinFactura`: `estado` en `pendiente`, `factura-cargada`, `sin-documento`, `anticipo`; `Nota` varchar(500) obligatoria si `sin-documento`; una sola marca vigente por (`IdContacto`, `Medio`, `IdMovimiento`) y cada cambio registrado en `AuditoriaRevisionesHistorial` con `Accion` `pago-sin-factura`, quién, cuándo y el detalle anterior
- [X] T014a [US1] Agregar en `evidencia.py` el campo `FuenteRespaldo` de `RevisionPagosSinFactura` (varchar(20) NULL, CHECK en `portal`, `estado-de-cuenta`, `pdf`; obligatorio cuando `Estado = factura-cargada` y la compra no tiene archivo, 422 si falta; FR-020) y dejar en `Compras.[Documento Original]` de esa factura el texto "Sin archivo, respaldo: [fuente] [fecha]"; el alta de la factura sigue haciéndose con el alta de compras existente
- [X] T015 [US1] Exponer en `router.py` `GET /cuentas/{idContacto}/pagos-sin-factura` (parámetros `desde` e `incluirMarcados`) y `PUT /cuentas/{idContacto}/pagos-sin-factura/{medio}/{idMovimiento}` con los códigos de error del contrato; los pagos con marca `sin-documento` o `anticipo` no se cuentan como pendientes
- [X] T016 [P] [US1] Crear `frontend/src/components/revision-cuentas/PagosSinFactura.tsx` con la lista del detector (importe, fecha, retención asociada, importe y fecha esperados de la factura, confianza), los pagos anteriores a 2021 en una sección aparte, el aviso "detector sin cerrar" si `consistencia.cierra` es falso, y las acciones de marca (botones ocultos para el rol `Lectura` con `SoloLectura`)
- [X] T017 [US1] Validar el detector contra el caso testigo con la fixture de T009: confirmar que los falsos positivos del prototipo (pago de 10.594,55 y pago de 2021) quedaron resueltos, ajustar las pasadas si no, y registrar el resultado (pagos hallados, falsos positivos, tiempo) en `specs/036-revision-sistematica-cuentas/research.md` (D1) y en `quickstart.md`

**Checkpoint**: el detector funciona sobre una cuenta y las marcas se guardan; US1 es el MVP.

---

## Phase 4: User Story 2 — Ver cada cuenta por etapas y cerrarla con criterios claros (Priority: P1)

**Meta**: ficha por cuenta con etapa calculada, los 7 criterios medidos, cierre al corte (con excepción documentada), y reapertura cuando cambia el saldo al corte.

**Prueba independiente**: la ficha de Jauregui muestra los 7 criterios con los números del 09/10/2026 y se puede cerrar al corte del 30/09/2026.

### Tests de US2

- [X] T018 [P] [US2] Escribir `backend/tests/test_revision_criterios.py` con pruebas de las funciones puras de `criterios.py`: C1 a C7 con su `cumple`, número medido y texto; la etapa es E0 si no hay inventario confirmado, luego la primera de E1 a E5 con un criterio sin cumplir, y E6 si todo cumple; una cuenta con saldo cero y sin hallazgos queda en E6; una cuenta con pagos sin factura sin decisión queda en E1
- [X] T019 [P] [US2] Escribir `backend/tests/test_revision_fichas.py` con pruebas de `fichas.py` sobre datos simulados: cerrar con los 7 criterios cumplidos guarda `Corte`, `SaldoAlCierre`, `Moneda`, usuario y fecha; cerrar con un criterio sin cumplir devuelve 409 con la lista; `cerrada-con-excepcion` sin `MotivoExcepcion` devuelve 422; `esperando-sergio` sin `PreguntaBloqueante` devuelve 422; una cuenta cerrada se calcula como `reabierta` cuando el saldo al corte cambia en más de la tolerancia y NO cuando solo hay movimientos posteriores al corte
- [X] T020 [P] [US2] Agregar a `backend/tests/contract/test_revision_cuentas_api.py` las pruebas de `GET /cuentas/{id}/ficha`, `PUT /cuentas/{id}/ficha` (409, 422, 403 para `Lectura`) y `PUT /cuentas/{id}/ficha/inventario` (422 si la lista de fuentes está vacía)

### Implementación de US2

- [X] T021 [US2] Implementar en `backend/src/features/revision_cuentas/criterios.py` las funciones puras de los 7 criterios (data-model): C1 documentos completos (pagos sin factura desde el 01/01/2021 sin decisión = 0; los anteriores a 2021 no bloquean si el saldo cierra contra la evidencia y se registran como excepción documentada con motivo, FR-013b), C2 movimientos y contactos (hallazgos `contacto-duplicado` y `movimiento-sin-contacto` = 0), C3 saldo explicado por evidencia (diferencia contra el saldo externo menor al umbral de $300 en pesos o tolerancia relativa en dólares, o `sin-estado` con motivo), C4 tarjeta sin doble conteo (`doble-descuento-tarjeta` = 0), C5 imputaciones sanas (`aplicacion-fuera-de-plazo` y `sobrepago` en 0 o decididos, FIFO aplicado con saldo idéntico), C6 pendientes tipificados (`nota-sin-imputar`, `impuesto-sin-boleta` y retenciones con certificado, entendiendo por retención sin certificado la del contacto sin documento de certificado asociado), C7 trazabilidad (sin cambios de saldo al corte desde el cierre); y la función que devuelve la etapa de la cuenta (research D3). Debe reutilizar los hallazgos de `auditoria_cuentas/hallazgos.py` sin copiarlos. C3 informa además si el Access discrepa del saldo externo (gana el proveedor con documento; el Access solo es referencia, FR-018); para las cuentas de la cola A, C3 se cumple también cuando el saldo coincide con la referencia del Access al corte (`SaldosReferenciaAccess`) y la cuenta no tiene hallazgos ni pagos sin factura, devolviendo la fuente `access` como evidencia (FR-017b)
- [X] T022 [US2] Implementar en `backend/src/features/revision_cuentas/fichas.py` la ficha: lectura (crea la fila `pendiente` al primer acceso), cambio de estado con las reglas de T019 y las restricciones de `RevisionFichas` (`Estado` varchar(24) NOT NULL con CHECK en `pendiente`, `en-proceso`, `esperando-evidencia`, `esperando-sergio`, `cerrada`, `cerrada-con-excepcion`; `Nota` varchar(500); `PreguntaBloqueante` varchar(300); `MotivoExcepcion` varchar(500) obligatorio si `cerrada-con-excepcion`), cálculo de `estadoEfectivo` `reabierta` comparando el saldo recalculado al corte de la ficha con `SaldoAlCierre` (research D7), y registro de cada cambio en `AuditoriaRevisionesHistorial` con `Accion` `ficha-estado`, `ficha-inventario`, `ficha-cierre` y `ficha-reapertura`; al cerrar con una diferencia menor a $300 guarda esa diferencia en el detalle de `ficha-cierre` (FR-009)
- [X] T023 [US2] Exponer en `router.py` `GET /cuentas/{idContacto}/ficha`, `PUT /cuentas/{idContacto}/ficha` y `PUT /cuentas/{idContacto}/ficha/inventario` con los campos del contrato, incluyendo `antecedente035` (estado y nota de `AuditoriaRevisiones`) y `fifoAplicadoAntes` (el contacto figura como aplicado en `RecalculoFifoEjecucion`), sin tomar como cerradas las cuentas "revisadas" de la 035
- [X] T023a [US2] Implementar en `fichas.py` y exponer en `router.py` `GET` y `POST /cuentas/{idContacto}/decisiones` (contrato "Decisiones"): `tipo` en `descartar-access`, `cierre-con-excepcion`, `otro`; `texto` obligatorio (422 si falta); `descartar-access` exige `evidencia` con el análisis; se guardan en `AuditoriaRevisionesHistorial` con `Accion` `decision`, quién, cuándo y por qué
- [X] T024 [P] [US2] Crear `frontend/src/components/revision-cuentas/FichaCuenta.tsx` con las siete etapas, los 7 criterios (cumple o no, número medido y texto), el cierre al corte con confirmación en español simple, el cierre con excepción (motivo obligatorio), la pregunta para Sergio, el bloque "Qué evidencia manda" (el proveedor con documento primero, luego banco y tarjeta; el Access solo como referencia), las decisiones registradas y el historial, e incorporarlo como panel en `frontend/src/components/auditoria-cuentas/RevisionCuenta.tsx` (botones ocultos para `Lectura` con `SoloLectura`)
- [X] T025 [US2] Validar con Jauregui y Morales (contacto 48): leer su ficha y comprobar que C1, C2, C4, C5, C6 y C7 cumplen con los números del 09/10/2026; C3 queda pendiente hasta T038; registrar en `quickstart.md` los criterios medidos (el cierre se hace en T038a)

**Checkpoint**: se puede revisar y cerrar una cuenta con criterios medibles.

---

## Phase 5: User Story 3 — Trabajar en colas por tipo de problema (Priority: P1)

**Meta**: cada cuenta cae en una sola cola A a I, ordenada de las más fáciles a las más complejas, y se resuelve en lote con una regla reversible.

**Prueba independiente**: todas las cuentas con movimientos quedan en exactamente una cola; la suma del tablero coincide con el total; el lote de una cola se aplica y se revierte dejando el saldo idéntico.

### Tests de US3

- [X] T026 [P] [US3] Escribir `backend/tests/test_revision_colas.py` con pruebas de `colas.py`: la precedencia H, D, E, C, G, F, I, B, A (research D5) con una cuenta con pago sin factura y doble descuento que va a la D y lista el doble descuento en `otrosProblemas`; una entidad de `EXCLUIDOS` (Condominio LSC) va siempre a la H; una cuenta sin pendientes va a la A; el orden dentro de la cola es por cantidad de movimientos (menos primero) y, a igual cantidad, por volumen (menor primero)
- [X] T027 [P] [US3] Escribir `backend/tests/test_revision_lotes.py` con pruebas de `lotes.py` sobre datos simulados: `simular` crea la corrección `simulada` con una fila por cuenta y `Tildada = 0`; tildar con `tildarTodas` marca solo las cuentas que cumplen la regla y se pueden desmarcar cuentas sueltas; `aplicar` rechaza un lote sin cuentas tildadas (409), uno ya aplicado (409) y uno cuyo saldo cambió desde la simulación (409); aplicar deja el saldo de cada cuenta idéntico antes y después; `revertir` devuelve las imputaciones al estado anterior y rechaza un lote no aplicado (409); `DELETE` solo descarta lotes simulados
- [X] T028 [P] [US3] Agregar a `backend/tests/contract/test_revision_cuentas_api.py` las pruebas de `GET /colas/{cola}` (orden y paginación de hasta 100), `GET /reglas`, `POST /lotes/simular` (201, 422 si la regla no corresponde a la cola), `PUT /lotes/{id}/cuentas`, `POST /lotes/{id}/aplicar` (409 sin cuentas tildadas, 403 para `Lectura`), `POST /lotes/{id}/revertir` y `DELETE /lotes/{id}`

### Implementación de US3

- [X] T029 [US3] Implementar en `backend/src/features/revision_cuentas/colas.py` las funciones puras `asignar_cola` (precedencia de research D5, devolviendo la cola y `otrosProblemas`) y `orden_de_dificultad` (cantidad de movimientos y, a igual cantidad, volumen en pesos; research D6), reutilizando `auditoria_cuentas.clasificacion` y `hallazgos` para las causas; las compras particulares llegan a la cola H por las cajas `Particular L` y `Particular S` ya existentes (`backend/src/features/compras/particular.py`)
- [X] T030 [US3] Implementar en `backend/src/features/revision_cuentas/lotes.py` los lotes sobre `AuditoriaCorrecciones` y `AuditoriaCorreccionesCuentas` (research D10): `simular`, `tildar`, `aplicar` (respaldo con `backup_verificado`, una sola transacción, guarda lo necesario para revertir), `revertir` y `descartar`, sin borrar filas y sin escribir en `LaHerencia`; con las reglas `aprobar-cierre` (cola A, cierra las cuentas tildadas al corte con la aprobación de Sergio, registra la fuente `access` en el detalle de `ficha-cierre` y muestra en el lote los movimientos del 26 al 30/09/2026, posteriores a la referencia del Access, para que Sergio los revise antes de aprobar; FR-017b), `fifo-tandas` (cola B, delega en `auditoria_cuentas/fifo_plan.py` y `recalculo_fifo/ejecuciones.py` y resuelve también los hallazgos `aplicacion-fuera-de-plazo`, anulando y reimputando, con una lista previa que Sergio tilda; FR-025) y `anular-doble-descuento` (cola C: anula las imputaciones bancarias de `AplicacionesPago` que duplican lo que cubrió la tarjeta, `Anulada = 1` con motivo, usuario y fecha, saldo antes igual a saldo después, reemplazando las tareas T029 a T033 de la 035)
- [X] T031 [US3] Exponer en `router.py` `GET /colas/{cola}`, `GET /reglas`, `POST /lotes/simular`, `PUT /lotes/{idCorreccion}/cuentas`, `POST /lotes/{idCorreccion}/aplicar`, `POST /lotes/{idCorreccion}/revertir` y `DELETE /lotes/{idCorreccion}` con los códigos de error del contrato y el usuario actual; cada cuenta del lote queda con una entrada de historial
- [X] T032 [P] [US3] Crear `frontend/src/components/revision-cuentas/ColaCuentas.tsx` y `frontend/src/components/revision-cuentas/LoteCola.tsx` y la ruta `frontend/src/app/finanzas/revision-cuentas/cola/[cola]/page.tsx`: lista de cuentas de la más fácil a la más compleja, regla a aplicar, casillas sin tildar de antemano, el botón explícito "tildar todas las que cumplen" (usa `tildarTodas` del contrato) con posibilidad de desmarcar cuentas sueltas, "Aplicar" con confirmación en español simple, historial de lotes y "Revertir" (ocultos para `Lectura`)
- [X] T033 [US3] Calcular las colas de las 518 cuentas con movimientos, comprobar que ninguna queda sin cola y que la cola I es menos del 10 % del total (SC-007), y registrar la distribución por cola en `quickstart.md`

**Checkpoint**: las cuentas están en colas ordenadas y se resuelven por lote reversible.

---

## Phase 6: User Story 4 — Comparar el saldo contra el estado de cuenta del proveedor (Priority: P2)

**Meta**: registrar saldos externos con fecha y fuente, y compararlos con el saldo de la cuenta a esa fecha.

**Prueba independiente**: el saldo de Jauregui de −$0,01 del portal se registra y el sistema lo clasifica como menor al umbral contra el saldo de la cuenta al corte.

- [X] T034 [P] [US4] Agregar a `backend/tests/contract/test_revision_cuentas_api.py` las pruebas de `GET`, `POST` y `DELETE` de `/cuentas/{id}/saldos-externos`: 422 si `fuente = sin-estado` no trae `nota`, 422 si `fechaSaldo` es futura, la diferencia se calcula contra el saldo de la cuenta a esa fecha, la clasificación es `cierra`, `menor-al-umbral` o `con-diferencia`, `DELETE` es baja lógica (`Anulado = 1`) y devuelve 204, y el rol `Lectura` recibe 403
- [X] T035 [US4] Implementar en `backend/src/features/revision_cuentas/evidencia.py` los saldos externos sobre `RevisionSaldosExternos`: `Moneda` varchar(10) (`Pesos` o `Dolares`), `Fuente` varchar(20) con CHECK en `portal`, `pdf`, `mail`, `banco`, `tarjeta`, `sin-estado`, `Referencia` varchar(400), `Nota` varchar(500) obligatoria si `sin-estado`, comparación contra el saldo a la fecha con umbral de $300 en pesos y tolerancia relativa en dólares (nunca monto fijo), y registro en `AuditoriaRevisionesHistorial` con `Accion` `saldo-externo`. El sistema no se conecta a ningún portal ni cuenta externa (research D12)
- [X] T036 [US4] Exponer en `router.py` `GET`, `POST` y `DELETE` de `/cuentas/{idContacto}/saldos-externos` con los códigos del contrato, y conectar el resultado al criterio C3 de `criterios.py`
- [X] T037 [P] [US4] Crear `frontend/src/components/revision-cuentas/SaldosExternos.tsx` con el formulario (fecha, saldo, moneda, fuente, referencia, nota), la lista con la diferencia y su clasificación, y la opción "no se pide estado de cuenta" con motivo
- [X] T034a [US4] Mostrar en `FichaCuenta.tsx` para las cuentas en dólares el aviso `diferencia-de-cambio` y su sugerencia de nota (ya existen en `auditoria_cuentas/revision.py`, `avisos_de_cuenta`), con acceso al `nota-ajuste` existente de `/api/auditoria-cuentas/cuentas/{id}/nota-ajuste`, para que Sergio apruebe la nota (FR-027)
- [X] T038 [US4] Con la aprobación de Sergio (otorgada el 09/10/2026), registrar el estado de cuenta de Jauregui y Morales (saldo −0,01 a su último movimiento del 20/08/2026, fuente `portal`, referencia al comprobante consultado el 09/10/2026) y comprobar que C3 queda cumplido; registrar en `quickstart.md`
- [X] T038a [US4] Con la aprobación de Sergio (otorgada el 09/10/2026), cerrar Jauregui y Morales al corte del 30/09/2026 una vez cumplidos los 7 criterios (T025 y T038), y registrar en `quickstart.md` el saldo al cierre

---

## Phase 7: User Story 5 — Aplicar el FIFO solo cuando la cuenta está lista (Priority: P2)

**Meta**: el FIFO de una cuenta solo se simula y se aplica si completó E1 a E4.

**Prueba independiente**: una cuenta con un pago sin factura sin decisión recibe 409 al simular el FIFO; con documentos completos simula normalmente.

- [X] T039 [P] [US5] Escribir `backend/tests/test_revision_puerta_fifo.py` con pruebas de la puerta: una cuenta con pagos sin factura sin decisión recibe 409 con `etapaPendiente` `E1` y la lista de criterios; una cuenta que cumple E1 a E4 simula normalmente; `revertir` no tiene puerta; las tandas omiten, informándolas, las cuentas que no cumplen
- [X] T040 [US5] Agregar en `backend/src/features/revision_cuentas/criterios.py` la función `puede_simular_fifo(id_contacto)` y usarla en `backend/src/features/auditoria_cuentas/router.py` en `POST /cuentas/{id}/fifo/simular` y `.../aplicar` (409 con `detail`, `etapaPendiente` y `criterios`) y en `POST /fifo/tandas/simular` (omite e informa las cuentas que no cumplen), sin cambiar el resto del contrato de la 035
- [X] T041 [P] [US5] Mostrar en `frontend/src/components/auditoria-cuentas/FifoCuenta.tsx` y `FifoTandas.tsx` el motivo de la puerta (etapa pendiente y qué falta) en español simple, y en la ficha (`FichaCuenta.tsx`) la leyenda "FIFO aplicado antes del método" cuando `fifoAplicadoAntes` sea verdadero
- [X] T042 [US5] En `criterios.py` y `lotes.py` listar como pendientes de la etapa las imputaciones de origen `tarjetas` duplicadas que el FIFO no reemplaza (caso Jauregui, corrección 42 del 09/10/2026) para anularlas con la corrección registrada, y agregarlas al detalle de la regla `anular-doble-descuento`

---

## Phase 8: User Story 6 — Detectar archivos incompletos en las carpetas de comprobantes (Priority: P2)

**Meta**: revisar en solo lectura las carpetas de compras e informar archivos incompletos o ilegibles.

**Prueba independiente**: en la carpeta del período `04 2025 - 03 2026` aparecen los `.crdownload` de Jauregui con su estado y si están cargados; los archivos no se modifican.

- [X] T043 [P] [US6] Escribir `backend/tests/test_revision_archivos.py` con carpetas temporales (nunca la real de Dropbox): un `.crdownload` con contenido PDF legible se informa como `comprobante-legible-extension-incorrecta` con número e importe; un archivo vacío como `vacio`; uno ilegible como `no-legible`; una imagen como `imagen-revisar`; `cargado` verdadero si el número de documento (sin ceros a la izquierda) existe en `Compras`; la revisión no modifica, renombra ni borra ningún archivo (misma fecha y tamaño antes y después)
- [X] T044 [US6] Implementar en `backend/src/features/revision_cuentas/archivos.py` la revisión de solo lectura de las carpetas de compras por período fiscal (`04 AAAA - 03 AAAA+1`) con `pdfplumber` (research D9), con la raíz de Dropbox como parámetro de configuración del backend (no recibida del cliente), y la búsqueda del número de documento en `Compras` de cualquier contacto y del campo "documento original"
- [X] T045 [US6] Exponer en `router.py` `GET /archivos/incompletos` (parámetros `periodo`, `estado`, `pagina`; 422 si el período no tiene el formato esperado) con los campos del contrato y sin recibir rutas del cliente
- [X] T046 [P] [US6] Crear `frontend/src/components/revision-cuentas/ArchivosIncompletos.tsx` y la ruta `frontend/src/app/finanzas/revision-cuentas/archivos/page.tsx` con el filtro por período y estado, la indicación de si está cargado y el enlace para abrir el archivo con `/api/compras/documento-local`

---

## Phase 9: User Story 7 — Ver el avance en un tablero semanal (Priority: P3)

**Meta**: tablero de colas por etapas con foto semanal y lista de preguntas que bloquean.

**Prueba independiente**: la suma de las casillas del tablero es igual al total de cuentas, y la comparación contra la foto anterior informa las cuentas cerradas de la semana.

- [X] T047 [P] [US7] Escribir `backend/tests/test_revision_tablero.py` con pruebas de `tablero.py`: cada cuenta cae en una sola casilla y la suma es el total; el recuento por estado suma el total; `comparacion` es `null` sin foto anterior; con una foto anterior informa las cuentas cerradas de la semana y la variación de la cola I; la foto de la semana se crea una sola vez
- [X] T048 [P] [US7] Agregar a `backend/tests/contract/test_revision_cuentas_api.py` las pruebas de `GET /tablero`, `GET /tablero/fotos`, `POST /tablero/fotos` (409 si ya existe la de la semana) y `GET /preguntas`
- [X] T049 [US7] Implementar en `backend/src/features/revision_cuentas/tablero.py` los agregados por cola, etapa y estado con el importe en juego, la comparación contra la foto anterior, la foto semanal sobre `RevisionTableroFotos` (`Semana` date NOT NULL único, `Datos` nvarchar(max) NOT NULL; se crea al abrir el tablero si no existe la de la semana que empieza el lunes, y con el botón; research D13) y la lista de preguntas bloqueantes desde `RevisionFichas.PreguntaBloqueante`
- [X] T050 [US7] Exponer en `router.py` `GET /tablero`, `GET /tablero/fotos`, `POST /tablero/fotos` y `GET /preguntas` con los campos del contrato
- [X] T051 [P] [US7] Crear `frontend/src/components/revision-cuentas/TableroColas.tsx`, `ListaPreguntas.tsx` y la ruta `frontend/src/app/finanzas/revision-cuentas/page.tsx`: grilla de colas por etapas con cuentas e importe por casilla, totales por estado, comparación con la semana anterior, tamaño de la cola I y lista de preguntas con enlace a la cuenta
- [X] T052 [US7] Agregar la entrada "Revisión de cuentas" al menú de Finanzas, junto a la de Auditoría de cuentas (buscar `auditoria-cuentas` en `frontend/src` para ubicar el menú)

---

## Phase 10: Polish y cierre

- [X] T053 [P] Crear `frontend/tests/revision-cuentas.e2e.cjs` (patrón de `frontend/tests/auditoria-cuentas.e2e.cjs`) que recorra el tablero, una cola, la ficha de una cuenta con sus pagos sin factura, el alta de un saldo externo, un lote simulado y el control de archivos con la API simulada
- [X] T054 Ejecutar la suite completa `python -m pytest tests -q`, `npx tsc --noEmit` en `frontend/` y `node tests/revision-cuentas.e2e.cjs` con el servidor en el puerto 3100; corregir lo que falle
- [X] T055 Medir con las 518 cuentas los criterios de éxito SC-001 a SC-011 y los tiempos (detector por cuenta menos de 2 segundos con Cargill, tablero menos de 10 segundos, revisión de archivos de un período menos de 15 segundos), y registrar los resultados en `quickstart.md`
- [X] T056 Revisión final con el agente financiero (`.github/agents/07-financial-direction-specialist.agent.md`) de los criterios de cierre, la precedencia de colas, el tratamiento de lo anterior a 2021 y los resultados medidos; registrar el cierre y las diferencias aceptadas en `specs/036-revision-sistematica-cuentas/research.md`
- [X] T057 (aprobada por Sergio y aplicada el 09/10/2026; ver `research.md` D17) Proponer a Sergio el cambio de `.specify/memory/agent-guidance.md` para alinearlo con la Constitución v1.4.0 (`WC` es producción, `LaHerencia` está congelada) y aplicarlo solo con su aprobación (research D14)
- [ ] T058 Actualizar el estado de `specs/036-revision-sistematica-cuentas/spec.md` a "Implementado" con la fecha, y con la autorización de Sergio (otorgada el 09/10/2026) hacer el commit y el push de `backend/src/features/revision_cuentas/`, `backend/scripts/`, `backend/tests/`, `frontend/src/`, `frontend/tests/` y `specs/036-revision-sistematica-cuentas/`

---

## Dependencies & Execution Order

### Orden de fases

- **Setup (Phase 1)**: sin dependencias.
- **Foundational (Phase 2)**: depende de Setup; bloquea todas las historias (tablas y lectura de datos).
- **US1 (Phase 3, MVP)**: depende de la Fase 2. Es lo más valioso y lo de mayor riesgo técnico; se valida contra el caso testigo antes de seguir.
- **US2 (Phase 4)**: depende de la Fase 2 y usa el detector de US1 para C1.
- **US3 (Phase 5)**: depende de US1 y US2 (la cola D sale del detector; las etapas y criterios definen la precedencia).
- **US4 (Phase 6)**: depende de US2 (alimenta C3 de la ficha). El cierre de Jauregui (T038a) va después de T038 porque C3 necesita el saldo externo.
- **US5 (Phase 7)**: depende de US2 (la puerta usa los criterios).
- **US6 (Phase 8)**: depende solo de la Fase 2; se puede hacer en paralelo con US2 a US5.
- **US7 (Phase 9)**: depende de US2 y US3 (colas y estados para el tablero).
- **Polish (Phase 10)**: depende de todas las historias que se quieran entregar.

### Dentro de cada historia

- Las pruebas se escriben primero y deben fallar antes de implementar.
- Orden: funciones puras → acceso a datos → endpoints → pantallas → validación con datos reales.
- Nada se aplica sobre `WC` fuera de las tareas marcadas con la aprobación de Sergio (T038, T038a, T058) y sin respaldo verificado.

### Oportunidades de paralelismo

- T002 y T006 en paralelo con T005; T008 con T007.
- T010 y T011 (US1); T018, T019 y T020 (US2); T026, T027 y T028 (US3); T043 (US6); T047 y T048 (US7): pruebas de archivos distintos.
- Los componentes de frontend marcados [P] en paralelo con el backend de su historia.
- US6 completa en paralelo con US2 a US5.

### Ejemplo de paralelismo: User Story 1

```text
Task: "T010 [P] [US1] Pruebas del detector en backend/tests/test_revision_detector.py"
Task: "T011 [P] [US1] Pruebas de contrato de pagos sin factura en backend/tests/contract/test_revision_cuentas_api.py"
Task: "T016 [P] [US1] Componente PagosSinFactura.tsx en frontend/src/components/revision-cuentas/"
```

---

## Implementation Strategy

### MVP primero (US1)

1. Fase 1 y 2: paquete, tablas con respaldo, corte y lectura de datos.
2. US1: el detector. **Parar y validar**: reproducir los 8 pagos de Jauregui y resolver los falsos positivos (T017) es el riesgo principal.
3. US2: la ficha y el cierre con criterios medibles; cerrar Jauregui como caso testigo.

### Entrega incremental

4. US3: colas y lotes (la cola A y la B permiten avanzar rápido con las cuentas ya sanas y las de solo imputación).
5. US4 y US5: saldos externos y la puerta del FIFO.
6. US6: archivos incompletos (se puede adelantar en paralelo).
7. US7: tablero y foto semanal. Luego Polish y cierre.

### Reglas de trabajo

- Un frente a la vez; no reabrir lo cerrado (Jauregui, tarjetas, Mercado Pago).
- Primero lo que cambia el saldo (documentos, movimientos), al final las imputaciones (FIFO).
- Nada se escribe en `LaHerencia` ni en los Access; toda aplicación es reversible y con respaldo; el sistema no entra a portales (regla de oro).
- Solo Sergio audita y aprueba cierres y excepciones.
