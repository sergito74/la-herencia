# Tasks: Descarga y carga automática de comprobantes de peajes

**Input**: Design documents from `specs/037-descarga-peajes/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/api.md](contracts/api.md), [quickstart.md](quickstart.md)

**Tests**: Se incluyen. La Constitución (Principio V) exige el chequeo automático más acotado que sirva y el [quickstart](quickstart.md) los define. Ningún test escribe en `WC` ni entra a los portales.

**Organization**: Tareas agrupadas por historia de usuario. US1 y US2 son ambas P1 (descargar y cargar solo); US3 P2; US4 P3.

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Setup

- [X] T001 Agregar `playwright>=1.47` y `keyring>=25` a `backend/requirements.txt` e instalarlos en `backend/.venv` (pedir autorización a Sergio antes de instalar; Playwright usa `channel="chrome"`, sin `playwright install`)
- [X] T002 [P] Crear el paquete `backend/src/features/descarga_peajes/__init__.py` y la carpeta `backend/tests/fixtures/peajes/`
- [X] T003 [P] Crear `backend/tests/fixtures/peajes/casos.json` (versionado) con los casos de prueba: archivo de Dropbox (`Compras/04 2026 - 03 2027`: Telepeaje 20260427 —con intereses— y 20261012, AutopistasDelSol 20261001, GrupoConcesionarioDelOeste 20260901, AUSA 20260531, CorredoresViales 20260528 y 20260529, Corresur 20260914 001, CV5 20260729, Ceamse 20260831; `04 2025 - 03 2026`: AUBASA 20251215) y valores esperados (número, fecha, total, IdDeuda existente). Los PDFs NO se copian al repo: tienen datos personales (domicilio particular, CUIT) y la Constitución prohíbe versionarlos; los tests los leen de Dropbox y hacen `pytest.skip` si no están. Agregar `backend/tests/fixtures/peajes/*.pdf` a `.gitignore`

---

## Phase 2: Foundational (bloquea todas las historias)

- [X] T004 Crear `backend/scripts/crear_esquema_descarga_peajes_037.py` siguiendo el patrón de `crear_esquema_auditoria_035.py` (`--verificar`, respaldo con `backup_verificado`, creación idempotente, `--revertir` solo si vacías) con: `dbo.DescargaPeajes_Ejecuciones` (IdEjecucion int IDENTITY PK; Origen varchar(10) NOT NULL `manual`|`semanal`; Usuario varchar(60) NULL; Inicio datetime2 NOT NULL default SYSDATETIME(); Fin datetime2 NULL; Estado varchar(15) NOT NULL `en_curso`|`completa`|`con_errores`|`incompleta`|`salteada`; Mensaje nvarchar(400) NULL), `dbo.DescargaPeajes_EjecucionPortales` (PK (IdEjecucion, Portal); Portal varchar(20) `TelepeajePlus`|`TelePASE`|`CEAMSE`|`AUBASA`; Estado varchar(15) `pendiente`|`en_curso`|`ok`|`error`|`sin_credenciales`; Nuevos/Existentes/Cargados/Pendientes int default 0; Error nvarchar(400) NULL) y `dbo.DescargaPeajes_Documentos` (IdDocumento int IDENTITY PK; Clave varchar(120) NOT NULL UNIQUE; Portal varchar(20) NOT NULL; Proveedor varchar(40) NOT NULL; IdContacto int NULL; FechaDocumento date NOT NULL; NumeroDocumento varchar(30) NULL; TotalImpreso decimal(18,2) NULL; Ruta nvarchar(400) NULL; IdEjecucion int NULL FK; EstadoCarga varchar(20) NOT NULL `cargado_auto`|`ya_cargado`|`pendiente`|`historico`; Motivo nvarchar(300) NULL; IdCompra int NULL; Creado datetime2 NOT NULL default SYSDATETIME()), con CHECK constraints para los enumerados
- [X] T005 Agregar a `backend/scripts/crear_esquema_descarga_peajes_037.py` la opción `--importar-manifiesto` que inserta las claves de `Dropbox/.../Compras/_descargas_portales.json` (98) como documentos `EstadoCarga='historico'`, idempotente (salta claves existentes)
- [X] T006 Ejecutar T004 y T005 contra `WC` (respaldo verificado; anotar ruta del .bak en la salida) y verificar 3 tablas y 98 filas `historico`
- [X] T007 [P] Implementar `backend/src/features/descarga_peajes/repository.py`: crear ejecución, actualizar estado de portal/ejecución, insertar documento, `existe_clave`, listar ejecuciones paginado (limite≤100), detalle de ejecución con documentos, listar documentos por estado, `revalidar_pendientes()` (marca `ya_cargado` + IdCompra si existe compra con `[Documento Original]=Ruta` o mismo IdContacto y `[Nro Documento]`), `resumen()` (pendientes y portales con error en la última ejecución de cada portal) — solo SQL parametrizado
- [X] T008 [P] Implementar `backend/src/features/descarga_peajes/configuracion.py`: `credenciales_configuradas(portal) -> bool` con keyring servicio `LaHerencia-Peajes` (entradas `<cuenta>` y `<cuenta>-usuario`, nunca devuelve valores) y `estado_tarea()` leyendo `schtasks /Query /TN "LaHerencia - Descarga peajes" /FO CSV /V` (instalada, próxima corrida, último resultado; tolerante a tarea inexistente)
- [X] T009 Mover a `backend/src/features/descarga_peajes/portales.py` la lógica de login y listado de `backend/scripts/descargar_peajes.py` (TelepeajePlus, TelePASE, oficinas virtuales CEAMSE/AUBASA, `carpeta_ejercicio`, `destino_libre`, `credencial`) más el mapeo proveedor→IdContacto de data-model.md (Telepeaje 328, CorredoresViales 436, Corresur 2657, CV5 2658, AutopistasDelSol 276, GrupoConcesionarioDelOeste 306, AUSA 380, Ceamse 314, AUBASA 316); cada fuente devuelve documentos con clave, fecha, proveedor, idContacto, detalle y forma de bajar el PDF. Si después del login no se llega a la página esperada dentro del timeout (captcha, código adicional, cambio de página), el portal falla con el mensaje "El portal requiere ingreso manual o cambió su página"

**Checkpoint**: esquema creado, repositorio y portales listos.

---

## Phase 3: User Story 1 - Descargar ahora desde la aplicación (P1) 🎯 MVP

**Goal**: botón que baja los documentos nuevos en segundo plano, con avance por portal y sin ejecuciones simultáneas.

**Independent Test**: con credenciales, apretar "Descargar ahora" y ver el avance y el resultado por portal; un segundo clic durante la corrida avisa que hay otra en curso.

- [X] T010 [P] [US1] Test de contrato en `backend/tests/contract/test_descarga_peajes_api.py`: `POST /api/descarga-peajes/ejecuciones` → 202 con idEjecucion; 409 con idEjecucion si hay una en curso; 403 con rol `Lectura`; `GET /ejecuciones/{id}` con portales y documentos; 404 si no existe (servicio y repositorio simulados)
- [X] T011 [US1] Implementar `backend/src/features/descarga_peajes/servicio.py` `tomar_lock() -> conexión | None` (conexión dedicada autocommit con `sp_getapplock @Resource='DescargaPeajes', @LockOwner='Session', @LockTimeout=0`; `None` si está tomado) y `ejecutar(origen, usuario, dry_run=False, conexion_lock=None)`: si no recibe la conexión del lock la toma él (si falla: ejecución `salteada`); libera el lock al terminar cerrando la conexión, aun ante excepción; marcar `incompleta` las `en_curso` previas, verificar carpeta Dropbox (si no está: error general), procesar cada portal independiente (sin credenciales → `sin_credenciales`), guardar solo PDF válidos (`%PDF`) y, si la descarga falla o no es PDF, NO insertar el documento (así se reintenta la próxima vez) y contar el error en el portal; nunca pisar archivos; registrar el documento por clave solo después de guardar el archivo; actualizar contadores por portal y estado final `completa`/`con_errores`; nunca loguear credenciales. Con `dry_run=True` NO escribe nada en la base (ni ejecución, ni portales, ni documentos) ni en disco, no toma el lock y devuelve un informe en memoria de lo que bajaría y cargaría
- [X] T012 [US1] Agregar en `servicio.py` `iniciar_en_segundo_plano(usuario) -> (idEjecucion | None, idEnCurso | None)`: llama `tomar_lock()` dentro de la misma petición HTTP; si devuelve `None`, no crea nada y devuelve el id de la ejecución `en_curso` para el 409 (sin carrera: el lock se decide antes de responder); si lo obtiene, crea la ejecución, lanza `threading.Thread(daemon=True)` pasándole la conexión del lock (el hilo la libera al terminar) y responde 202
- [X] T013 [P] [US1] Definir modelos Pydantic en `backend/src/features/descarga_peajes/schemas.py` según [contracts/api.md](contracts/api.md) (EjecucionResumen, PortalResultado, Documento, Estado, ResumenContador)
- [X] T014 [US1] Implementar `backend/src/features/descarga_peajes/router.py` (prefix `/api/descarga-peajes`): `POST /ejecuciones`, `GET /ejecuciones/{id}`, `GET /estado`; registrar en `backend/src/main.py` con `app.include_router`
- [X] T015 [US1] Reemplazar `backend/scripts/descargar_peajes.py` por una entrada fina que llama a `servicio.ejecutar(origen=args.origen, usuario=None, dry_run=args.dry_run)` con `--origen manual|semanal` (default `semanal`) y `--dry-run` (imprime el informe en memoria, sin escribir nada); códigos de salida 0/2/1 según contrato
- [X] T016 [P] [US1] Crear `frontend/src/services/descargaPeajesApi.ts` (tipos y funciones de todos los endpoints de contracts/api.md, con `apiClient`)
- [X] T017 [US1] Crear `frontend/src/components/descarga-peajes/EjecucionEnCurso.tsx`: botón "Descargar ahora" envuelto en `SoloLectura`, mutación POST, manejo de 409 mostrando la ejecución en curso, y polling con TanStack Query `refetchInterval: 2000` mientras `estado === "en_curso"`; tabla por portal (estado, nuevos, existentes, cargados, pendientes, error) y lista de documentos nuevos (fecha `dd/mm/aaaa`, proveedor, archivo, carpeta)
- [X] T018 [US1] Crear `frontend/src/app/compras/descarga-peajes/page.tsx` con el componente de US1 y agregar a `frontend/src/components/layout/NavHeader.tsx` el submenú de Compras: "Compras" (`/compras`) y "Descarga de peajes" (`/compras/descarga-peajes`)

**Checkpoint**: la descarga se dispara desde la app y queda registrada.

---

## Phase 4: User Story 2 - Carga automática en Compras (P1)

**Goal**: cada documento nuevo de formato reconocido se carga solo en Compras si cierra exacto y no está duplicado; lo demás queda pendiente con motivo.

**Independent Test**: con un PDF de cada formato, el lector devuelve datos cuyo total cierra con el impreso; procesar un documento ya cargado lo marca `ya_cargado` sin duplicar.

- [X] T019 [P] [US2] Tests en `backend/tests/test_descarga_peajes_lectores.py`: para cada caso de `casos.json` (T003; `pytest.skip` si el PDF no está en Dropbox), el lector correcto devuelve número, fecha, renglones y total impreso, y `calcular_totales` cierra con ±0,05; números esperados iguales a las compras existentes en `WC` (ej. AUSOL `0840-00787789`, CEAMSE `00126-00787798`, AUBASA `00050-04824898`); un caso con un importe alterado devuelve "no cierra"
- [X] T020 [P] [US2] Tests en `backend/tests/test_descarga_peajes_carga.py` con `create_compra` y búsqueda de duplicados simulados: cierra → crea compra con IdContacto, rubro 2047893477, centro de costo 3, destino 1, campaña "No Aplica", moneda Pesos, tipo A, documento original = ruta; duplicado (mismo IdContacto y número) → `ya_cargado` sin crear; no cierra / formato desconocido / proveedor sin IdContacto → `pendiente` con motivo legible
- [X] T021 [US2] Implementar `backend/src/features/descarga_peajes/lectores.py`: un lector por formato (Telepeaje resumen → 1 renglón "Resumen peajes" $0 unidad RESUMEN + sellos en `leyDeSellos`; si el resumen trae "Intereses Financieros", en lugar del renglón $0 va un renglón "Intereses financieros" con precio = interés / 1,21 redondeado a 2 decimales e IVA 21, como se cargó a mano (27/04/2026: $0,12 → $0,10; 27/05/2026: $0,14 → $0,12); AutopistasDelSol; GCO; AUSA con no gravados y percepción IIBB; CorredoresViales; Corresur y CV5 recalculando IVA sobre neto; CEAMSE; AUBASA con "Gastos Administrativos"), seleccionados por proveedor; devuelven `{numero, fecha, tipo, renglones, ingresosBrutos, conceptosNoGravados, leyDeSellos, totalImpreso}` o un motivo de no reconocimiento; números con el mismo formato que las cargas históricas (`0840-00787789`, `0002-365398211`, `00126-00787798`, `00050-04824898`)
- [X] T022 [US2] Implementar `backend/src/features/descarga_peajes/carga.py` `cargar(documento)`: ejecutar lector, validar cierre con `compras.repository.calcular_totales` (|dif| ≤ 0,05), chequear `buscar_documento_duplicado(IdContacto, numero)` y documento original existente, y crear con `compras.repository.create_compra` (cabecera + líneas; sin vencimientos salvo que el lector los informe); devolver estado `cargado_auto`/`ya_cargado`/`pendiente`, motivo e IdCompra
- [X] T023 [US2] Integrar `carga.cargar` en `servicio.ejecutar` después de guardar cada PDF (no en `dry_run`, donde solo informa qué cargaría); actualizar `Cargados`/`Pendientes` del portal y `EstadoCarga`/`Motivo`/`IdCompra` del documento; un error de carga no corta la ejecución
- [X] T024 [US2] Agregar `GET /api/descarga-peajes/documentos` (filtro por estado, paginado, llama `revalidar_pendientes` antes de responder) en `router.py`
- [X] T025 [P] [US2] Aceptar `?documentoOriginal=` en `frontend/src/app/compras/nueva/page.tsx` y pasarlo al prefill de `frontend/src/components/compras/CompraForm.tsx` (estado inicial de `documentoOriginalLink`)
- [X] T026 [US2] Crear `frontend/src/components/descarga-peajes/DocumentosLista.tsx`: documentos con estado (cargado automáticamente / ya cargado / pendiente con motivo), importes con los helpers de `lib/format.ts`, "Ver PDF" con `urlDocumentoLocal` de `lib/documentoLocal.ts` (aviso legible si el archivo no está), link a la compra si hay IdCompra y "Cargar en Compras" → `/compras/nueva?idContacto=&proveedor=&fecha=&numeroDocumento=&documentoOriginal=`; integrarlo en `page.tsx`

**Checkpoint**: sincronización completa: baja y carga sola.

---

## Phase 5: User Story 3 - Historial de ejecuciones (P2)

**Goal**: ver todas las ejecuciones, manuales y semanales, con su detalle.

**Independent Test**: una ejecución manual y una por script `--origen semanal` aparecen en el historial con origen, usuario, duración y resultado por portal.

- [X] T027 [P] [US3] Ampliar `backend/tests/contract/test_descarga_peajes_api.py` con `GET /ejecuciones?limite=&desde=` (orden descendente, total, portales por ítem)
- [X] T028 [US3] Agregar `GET /api/descarga-peajes/ejecuciones` paginado en `router.py`
- [X] T029 [US3] Crear `frontend/src/components/descarga-peajes/Historial.tsx` (fecha/hora, origen, usuario, duración, estado, resultado por portal y errores; al abrir una ejecución muestra sus documentos) e integrarlo en `page.tsx`

---

## Phase 6: User Story 4 - Estado de la configuración y contador (P3)

**Goal**: ver credenciales por portal y tarea semanal; contador de pendientes/errores en el menú.

**Independent Test**: antes del instalador figuran 4 portales "sin configurar" y tarea "no instalada"; después, configurados con próxima corrida; el contador refleja pendientes + portales con error.

- [X] T030 [P] [US4] Ampliar `backend/tests/contract/test_descarga_peajes_api.py`: `GET /estado` solo devuelve booleanos (ningún usuario/contraseña en la respuesta) y `GET /resumen` devuelve `{pendientes, portalesConError}`
- [X] T031 [US4] Agregar `GET /api/descarga-peajes/resumen` en `router.py` y completar `GET /estado` con `configuracion.py`
- [X] T032 [US4] Crear `frontend/src/components/descarga-peajes/EstadoConfiguracion.tsx` (portal: configurado/sin configurar; tarea: instalada con próxima corrida o "no instalada" con la instrucción del instalador; aviso de portales que se saltearán) e integrarlo arriba en `page.tsx`
- [X] T033 [US4] En `frontend/src/components/layout/NavHeader.tsx` mostrar el contador junto a "Descarga de peajes" (y sobre "Compras") consultando `/resumen` cada 5 min y al volver a la pestaña; oculto si es 0
- [X] T034 [US4] Actualizar `backend/scripts/instalar_descarga_peajes.ps1`: usar `C:\dev\LaHerencia\backend\.venv\Scripts\python.exe`, argumentos `-m scripts.descargar_peajes --origen semanal`, mantener la carga de las 4 credenciales

---

## Phase 7: Polish & Cross-Cutting

- [X] T035 Correr `pytest backend/tests/test_descarga_peajes_lectores.py backend/tests/test_descarga_peajes_carga.py backend/tests/contract/test_descarga_peajes_api.py` y `npx tsc --noEmit` + `npm run build` en `frontend/`
- [ ] T036 Ejecutar `python -m scripts.descargar_peajes --origen manual --dry-run` desde `backend/` con el .venv y verificar que no propone documentos nuevos (todo `historico`)
- [ ] T037 Validación manual de [quickstart.md](quickstart.md) pasos 1–8 con la app levantada por el launcher; registrar resultados en `specs/037-descarga-peajes/quickstart.md`
- [X] T038 [P] Revisión de checkpoint con el agente de dirección financiera (`.github/agents/`) sobre los criterios de carga automática (rubro, IIBB, no gravados, resumen Telepeaje $0) y registrar hallazgos
  - Hecha 2026-10-16 (agente 07, dirección financiera). Corregidos: (6) los lectores rechazan notas de crédito/débito → pendiente; (7) "ya cargado" por documento original compara ruta exacta (o formato heredado `ruta#`), no prefijo. (3) Sergio decidió (A): percepción de IVA → `PercepcionIVA` desde el módulo; aplicado en lectores y carga. Seguimiento: (1) el débito del resumen Telepeaje se imputa a las facturas de las concesionarias, no a Telepeaje (328); (2) aceptación con cuenta corriente 276/380/328 en cero tras imputar débitos reales; (5) informe de cargas automáticas y anulación por ejecución.
- [X] T039 [P] Actualizar `memory.md` y la memoria de proyecto (descarga de peajes) con el módulo, tablas y la ubicación del instalador; revisar diff (sin credenciales, sin PDFs fuera de fixtures, sin .bak)

---

## Dependencies & Execution Order

- Setup (T001–T003) → Foundational (T004–T009) → historias.
- US1 (T010–T018) es el MVP; US2 depende de US1 (se integra en `servicio.ejecutar`, T023).
- US3 y US4 dependen solo de Foundational + `router.py` de US1; pueden ir en paralelo entre sí.
- Polish al final.

## Parallel Examples

- Foundational: T007, T008 en paralelo (archivos distintos); T009 después de T001.
- US1: T010, T013, T016 en paralelo; luego T011 → T012 → T014; T017 → T018.
- US2: T019, T020, T025 en paralelo; T021 → T022 → T023 → T024 → T026.
- US3 y US4 en paralelo una vez cerrada US1.

## Implementation Strategy

1. **MVP**: Setup + Foundational + US1 → descarga desde la app con registro (equivalente al script, visible en la app).
2. **Sincronización**: US2 → carga automática; validar con PDFs reales antes de habilitarla en la tarea semanal.
3. US3 + US4 → historial, estado y contador.
4. Polish → tests, validación manual, revisión de especialista; recién entonces Sergio corre el instalador actualizado.
