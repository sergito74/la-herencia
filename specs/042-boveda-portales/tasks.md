# Tasks: Bóveda de portales y sincronización periódica

**Input**: Design documents from `specs/042-boveda-portales/` (spec, plan, research, data-model, contracts/api.md, quickstart)

**Tests**: incluidos solo los mínimos que exige la Constitución (V) y el quickstart §9: cifrado, planificador, permisos y contrato con repositorio simulado. Ninguno escribe en `WC`.

**Format**: `- [ ] [ID] [P?] [Story] Descripción con ruta`

## Phase 1: Setup

- [X] T001 Crear paquete `backend/src/features/boveda/` (`__init__.py`) y `backend/src/features/boveda/conectores/__init__.py`, y carpeta `backend/tests/boveda/` con `conftest.py` que simule `repository` y `keyring` (sin conexión a `WC`)
- [X] T002 [P] Crear `frontend/src/services/bovedaApi.ts` con tipos TypeScript de todas las respuestas de `specs/042-boveda-portales/contracts/api.md` (sin campos de secretos salvo `revelar`)

## Phase 2: Foundational (bloquea todas las historias)

- [X] T003 Escribir `backend/scripts/crear_esquema_boveda_042.py`: respaldo verificado de `WC` antes de cualquier DDL (patrón de `crear_esquema_descarga_peajes_037.py`), `--dry-run`, `--aplicar`, `--revertir`; crea `Boveda_Credenciales`, `Boveda_CredencialDatos`, `Portales`, `Portales_Autorizaciones`, `Portales_Programacion`, `Portales_Corridas`, `Portales_Documentos` (`UNIQUE (IdPortal, Clave)`), `Portales_EstadoCuenta`, `Portales_EstadoCuentaMovimientos`, `Boveda_Auditoria` exactamente como en `data-model.md` (incluye CHECKs: `Titular IN ('empresa','socio')`, `Tipo IN ('organismo','proveedor','cliente','banco','otro')`, `Alcance = 'solo_lectura_descarga'`, `Frecuencia IN ('desactivada','diaria','semanal','mensual')`, `DiaMes BETWEEN 1 AND 28`, `DiaSemana BETWEEN 1 AND 7`, `Moneda IN ('ARS','USD')`)
- [X] T004 Implementar `backend/src/features/boveda/cifrado.py`: clave maestra de 32 B en keyring servicio `LaHerencia-Boveda` cuenta `clave-maestra` (se genera si no existe), `cifrar(valor, aad)`/`descifrar(blob, aad)` AES-256-GCM con nonce de 12 B, AAD `boveda:<IdCredencial>:clave` y `boveda:<IdCredencial>:dato:<Nombre>`, clase `Secreto` cuyo `__repr__`/`__str__` devuelven `***`
- [X] T005 [P] Escribir `backend/scripts/boveda_clave.py` con `generar`, `exportar <archivo.lhkey>` (envuelve la clave con frase de recuperación: scrypt + AES-GCM; rechaza rutas dentro del repo o de Dropbox) e `importar <archivo.lhkey>`
- [X] T006 Implementar `backend/src/features/boveda/repository.py`: CRUD de credenciales/datos (solo blobs cifrados), portales, autorizaciones (vigente = última sin `Revocada`), programación, corridas, documentos, fotos y `auditar(accion, usuario, id_portal, id_credencial, detalle)`; todas las consultas parametrizadas y con límites
- [X] T007 Implementar `backend/src/features/boveda/conectores/__init__.py`: interfaz `Conector` (`codigo`, `nombre`, `ingresar(pw, credencial)`, `listar_documentos(sesion)`, `estado_cuenta(sesion) | None`, `leer_comprobante(pdf) | None`, `mapeo_proveedores` con IdContacto/rubro/centro de costo), excepciones `RequiereIntervencion`, `CredencialesRechazadas`, `PortalCambio`, dataclasses `DocumentoPortal`, `EstadoCuentaPortal`, `DatosCompra`, y registro `CONECTORES`
- [X] T008 Implementar `_exigir_admin` y esqueleto de `backend/src/features/boveda/router.py` (prefijo `/api/boveda`, 403 `"Solo el administrador accede a la bóveda"` si `rol != "Administrador"`), `schemas.py`, e incluirlo en `backend/src/main.py`
- [X] T009 [P] Tests `backend/tests/boveda/test_cifrado.py`: ida y vuelta, AAD distinta falla, `repr(Secreto)` no contiene el valor
- [X] T010 [P] Tests `backend/tests/boveda/test_permisos.py`: todo `/api/boveda/*` devuelve 403 con rol `Lectura` y con cualquier rol distinto de `Administrador`

**Checkpoint**: base lista; ejecutar `crear_esquema_boveda_042.py --dry-run`, pedir respaldo verificado y `--aplicar` (DDL solamente).

## Phase 3: User Story 1 — Registrar un portal en la bóveda (P1) 🎯 MVP

**Goal**: guardar enlaces y credenciales cifradas, editar, reemplazar clave, revelar/copiar con auditoría.
**Independent Test**: quickstart §2 y §3.

- [X] T011 [US1] Endpoints de credenciales en `backend/src/features/boveda/router.py`: `GET/POST /credenciales`, `PATCH /credenciales/{id}`, `PUT /credenciales/{id}/clave` (204), `POST /credenciales/{id}/revelar` (`Cache-Control: no-store`, audita `revelar`); `GET` devuelve `valor: null` en datos secretos
- [X] T012 [US1] Endpoints de portales: `GET/POST /portales`, `PATCH /portales/{id}` (400 si URL no es http/https, nombre repetido o `codigoConector` desconocido), `GET /conectores`; alta con `credencialNueva` en una transacción; auditar `alta_portal`/`edicion_portal`/`alta_credencial`/`cambio_clave`
- [X] T013 [P] [US1] Test de contrato `backend/tests/boveda/test_api_portales.py` con repositorio simulado: ninguna respuesta salvo `revelar` contiene la clave cargada
- [X] T014 [P] [US1] `frontend/src/app/boveda/page.tsx`: lista de portales (nombre, tipo, contacto, usuario, clave enmascarada, conector disponible / "solo bóveda", botón "Abrir portal" en pestaña nueva con `rel="noopener noreferrer"`)
- [X] T015 [P] [US1] `frontend/src/components/boveda/PortalForm.tsx` y `CredencialForm.tsx` (alta/edición, credencial existente o nueva, titular empresa/socio, datos adicionales con marca secreto); inputs de clave `type="password"` `autoComplete="new-password"`
- [X] T016 [US1] `frontend/src/components/boveda/Revelar.tsx`: muestra 30 s o copia al portapapeles y limpia el estado; no guarda en caché de TanStack Query (`gcTime: 0`, mutación)
- [X] T017 [US1] Entrada "Bóveda" en `frontend/src/components/layout/NavHeader.tsx` visible solo para rol Administrador

**Checkpoint**: bóveda usable como guardado seguro de accesos.

## Phase 4: User Story 4 — Autorización y control de cada portal (P1)

**Goal**: sin autorización vigente no se entra; revocación inmediata.
**Independent Test**: quickstart §4.

- [X] T018 [US4] Endpoints `POST/DELETE /portales/{id}/autorizacion` (alcance fijo `solo_lectura_descarga`; auditar `autorizar`/`revocar`)
- [X] T019 [US4] Verificación de autorización vigente en `backend/src/features/boveda/servicio.py` antes de ingresar y otra vez antes de cada descarga (la revocación detiene la corrida en curso); sin vigente ⇒ corrida `sin_autorizacion`
- [X] T020 [P] [US4] Bloque de autorización (vigente, fecha, quién, fuente, revocar) en `frontend/src/app/boveda/[id]/page.tsx`

## Phase 5: User Story 2 — Programar la periodicidad de cada portal (P1)

**Goal**: frecuencia por portal ejecutada solo con la app abierta, con recuperación única.
**Independent Test**: quickstart §5.

- [X] T021 [US2] `backend/src/features/boveda/planificador.py`: `proxima_corrida(prog, desde)` para `diaria`/`semanal`/`mensual`/`desactivada`; hilo con tick de 60 s iniciado en `@app.on_event("startup")` de `backend/src/main.py`; selecciona portales activos, autorizados, con conector, no suspendidos y `ProximaCorrida <= ahora`; los corre en serie; al terminar recalcula desde *ahora* (recuperación única)
- [X] T022 [US2] Lock por portal con `sp_getapplock` (`boveda-portal-<id>`) en `servicio.py`; al arrancar marcar `incompleta` las corridas `en_curso` sin lock vivo
- [X] T023 [US2] Endpoint `PUT /portales/{id}/programacion` (400 si sin conector; audita `programar`) y `POST /portales/{id}/corridas`, `POST /corridas` (202 / 409 en curso / 409 falta autorización / 400 solo bóveda)
- [X] T024 [P] [US2] Tests `backend/tests/boveda/test_planificador.py`: cálculo de próxima corrida (cambio de mes, día 28, semana), recuperación única tras varios períodos perdidos, no dispara suspendidos ni sin autorización
- [X] T025 [P] [US2] `frontend/src/components/boveda/Programacion.tsx` (frecuencia, día, hora, próxima corrida, "Correr ahora", estado en curso con polling 2 s)

## Phase 6: User Story 3 — Bajar documentación y estado de cuenta (P1)

**Goal**: documentos sin duplicar en la carpeta de Compras del ejercicio, carga automática con cierre exacto, fotos de saldo al centavo.
**Independent Test**: quickstart §6 y §7.

- [X] T026 [US3] `servicio.correr_portal()` en `backend/src/features/boveda/servicio.py`: abre Playwright, descifra credencial como `Secreto`, `ingresar`, `listar_documentos`, salta claves existentes `(IdPortal, Clave)`, baja, guarda con `AAAAMMDD_Proveedor.pdf` en la carpeta de Compras del ejercicio (reusar `carpeta_ejercicio`/`destino_libre` de `descarga_peajes/portales.py`), calcula `Sha256` y evita duplicar archivos iguales; mapea excepciones a `requiere_intervencion`/`credenciales_rechazadas` (sin reintento, suspende programación con motivo y marca la credencial `rechazada` para que `GET /portales` devuelva `credencial.estado = "rechazada"` hasta el `PUT …/clave`)/`portal_cambio`; un fallo no corta la tanda
- [X] T027 [US3] `backend/src/features/boveda/carga.py`: generalizar `descarga_peajes/carga.py`; cargar con `compras.repository.create_compra` solo si formato reconocido, cierre exacto al centavo contra total impreso (sin tolerancia; si no cierra, `pendiente` con la diferencia en el motivo), proveedor mapeado con rubro y centro de costo, sin duplicado `(IdContacto, Nro Documento)`; si no, `pendiente` con motivo; documentos no comprobantes ⇒ `no_aplica`; nunca pagos ni asientos
- [X] T028 [US3] `backend/src/features/boveda/estado_cuenta.py` (primero verificar que la vista de saldos de `features/cuentas_corrientes` admite saldo a una fecha y por moneda; si no, consulta parametrizada propia sobre los mismos movimientos, documentada en research.md): guardar foto por moneda con movimientos; si `Completa` y hay `IdContacto`, obtener saldo del sistema al `FechaCorte` en la misma moneda con la vista de saldos existente (`features/cuentas_corrientes`), `Diferencia` al centavo **sin umbral**
- [X] T029 [US3] Endpoints `GET /documentos` (revalida pendientes como 037 R8), `GET /estado-cuenta`, `GET /estado-cuenta/{idFoto}`, `PATCH /estado-cuenta/{idFoto}` (`revisada`, sin efectos contables), `GET /corridas`, `GET /corridas/{id}`
- [X] T030 [US3] `backend/src/features/boveda/conectores/peajes.py`: 4 conectores (`telepeajeplus`, `telepase`, `ceamse`, `aubasa`) que envuelven `descarga_peajes/portales.py` y `lectores.py` sin reescribirlos
- [X] T031 [US3] Migración en `crear_esquema_boveda_042.py --migrar-037`: alta de los 4 portales de peaje (autorización 16/10/2026, programación semanal leída de `schtasks` o lunes 07:00), copia de credenciales de keyring `LaHerencia-Peajes` cifradas (sin borrarlas), copia de `DescargaPeajes_*` a `Portales_Corridas` (`Origen='migrada037'`, `IdEjecucion037`) y `Portales_Documentos`; informe de totales iguales; respaldo verificado antes
- [X] T032 [US3] Compatibilidad `backend/src/features/descarga_peajes/router.py`: `estado`, `ejecuciones`, `documentos`, `resumen` leen de tablas nuevas filtrando peajes; `POST ejecuciones` dispara las 4 corridas vía `boveda.servicio`; conservan el permiso de 037 (no exigen Administrador) y nunca devuelven credenciales
- [X] T033 [P] [US3] `frontend/src/components/boveda/Documentos.tsx` (ver PDF con el visor de Compras, ir a la compra, "Cargar en Compras" con archivo precargado) y `EstadoCuenta.tsx` (saldo portal / sistema / diferencia por moneda, movimientos, marcar revisada) en `frontend/src/app/boveda/[id]/page.tsx`
- [X] T034 [US3] `frontend/src/app/compras/descarga-peajes/page.tsx` se mantiene para usuarios de Compras (corridas, documentos, "Descargar ahora" de los peajes) leyendo de `/api/descarga-peajes/*`; quitar el estado de credenciales/tarea; enlace "Configurar en la bóveda" visible solo para Administrador
- [ ] T035 [US3] Verificación quickstart §6 con peajes reales; después `backend/scripts/instalar_descarga_peajes.ps1 -Desinstalar` (agregar el parámetro) para retirar la tarea semanal, solo tras una corrida programada exitosa desde la bóveda
  - Avance 27/10/2026: corrida real manual por la bóveda de los 4 peajes OK (login con credenciales de la bóveda; 0 nuevos, 96 ya registrados, sin duplicados). `-Desinstalar` agregado al script. La tarea de Windows quedó **deshabilitada** (reversible, `Enable-ScheduledTask`) para que no corra en paralelo con la bóveda; falta eliminarla con `-Desinstalar` después de la primera corrida **programada** exitosa desde la app (lunes 02/11 09:00 o al abrirla).

## Phase 7: User Story 5 — Agregar servicios nuevos (P2)

**Goal**: alta de portal sin conector como "solo bóveda"; vincular conector luego.
**Independent Test**: quickstart §3.

- [X] T036 [US5] En `PortalForm.tsx` y `PATCH /portales/{id}`: selector de conector (de `GET /conectores`) opcional; sin conector se ocultan programación y "Correr ahora"; al vincular conserva credenciales
- [X] T037 [US5] Alta en `crear_esquema_boveda_042.py --registrar-portales` de Bayá Casal (autorización 19/10/2026), Cargill (20/10/2026) y ARCA, Municipalidad de Bolívar, ARBA, Sancor Seguros, Allianz, Jáuregui y Morales, Lartirigoyen (27/10/2026, fuente "spec 042 Clarifications"), con URL e `IdContacto` verificado en `Contactos` antes de insertar (candidatos según fichas 036: ARBA 12, Bayá 226, Cargill 258, ARCA 119, Municipalidad 72; los demás buscarlos por nombre), sin credenciales (las carga Sergio desde la UI)

## Phase 8: User Story 6 — Seguimiento de corridas y alertas (P2)

**Goal**: historial por portal y contador en el menú.
**Independent Test**: quickstart §8.

- [X] T038 [US6] Endpoint `GET /resumen` (`pendientesCarga`, `conError`, `requiereIntervencion`, `diferenciasSaldo` = fotos completas con `Diferencia <> 0` y `Revisada = 0`, `total`)
- [X] T039 [P] [US6] `frontend/src/components/boveda/Corridas.tsx` (historial paginado con mensaje legible) y contador en `NavHeader.tsx` junto a "Bóveda" (solo Administrador); el contador de "Descarga de peajes" de Compras se mantiene con `/api/descarga-peajes/resumen`

## Phase 9: Conectores nuevos (US3, entrega incremental, orden FR-023)

Cada conector: relevar el portal en solo lectura con Chromium (vía `.specify/memory/local-access.md`, autorización registrada en la bóveda), registrar el relevamiento en `specs/042-boveda-portales/relevamientos/<portal>.md` (URLs, pasos de ingreso, documentos, estado de cuenta, captcha/2FA; **nunca credenciales**), implementar, verificar con una corrida manual y programar. Si exige captcha/2FA en cada ingreso: dejar "solo bóveda" y documentarlo. Criterio de revisión obligatorio de cada conector: el código solo navega, lee y descarga; no hace clic en botones de pagar, presentar, confirmar, aceptar, firmar ni enviar, ni envía formularios distintos del de ingreso y filtros de consulta; dejar constancia en el relevamiento.

- [ ] T040 [US3] `backend/src/features/boveda/conectores/baya_casal.py`: extranet `ctacteA/` (filtro FC desde 2010, aplicaciones SI), PDF embebido en `data:application/pdf;base64`, estado de cuenta ARS/USD, lector de factura (base: `specs/036-revision-sistematica-cuentas/baya-casal-relevamiento-20261019.md`)
- [ ] T041 [US3] `backend/src/features/boveda/conectores/cargill.py`: API del libro financiero por trimestre (customerId 35192801), estado de cuenta en US$, liquidaciones y facturas (memoria reference_portal_cargill)
- [ ] T042 [US3] `backend/src/features/boveda/conectores/arca.py`: relevamiento + conector (cuenta corriente/SCT, comprobantes en línea, retenciones/percepciones; solo consulta)
- [ ] T043 [US3] `backend/src/features/boveda/conectores/arba.py`: relevamiento + conector (boletas, estado de deuda, percepciones/retenciones)
- [ ] T044 [US3] `backend/src/features/boveda/conectores/municipalidad_bolivar.py`: relevamiento + conector (tasas, estado de deuda)
- [ ] T045 [US3] `backend/src/features/boveda/conectores/sancor.py`: relevamiento + conector (pólizas, facturas, estado de cuenta)
- [ ] T046 [US3] `backend/src/features/boveda/conectores/allianz.py`: relevamiento + conector
- [ ] T047 [US3] `backend/src/features/boveda/conectores/jauregui_morales.py`: relevamiento + conector
- [ ] T048 [US3] `backend/src/features/boveda/conectores/lartirigoyen.py`: relevamiento + conector

## Phase 10: Polish

- [X] T049 Búsqueda de secretos (quickstart §2): logs del backend, `git grep` y respuestas de API sin contraseñas; resultado en `specs/042-boveda-portales/validacion.md`
- [X] T050 [P] Documentar en `specs/042-boveda-portales/quickstart.md` el respaldo de la clave maestra (`boveda_clave.py exportar`) y pedir a Sergio que guarde el `.lhkey`
- [X] T051 [P] Actualizar `.specify/memory/local-access.md` (autorizaciones de los 7 portales del 27/10 y que las credenciales viven en la bóveda) y la memoria del proyecto
- [ ] T052 Revisión de checkpoint con agentes de seguridad/Python y dirección financiera (Constitución VI); `npm run build`; `pytest backend/tests/boveda -q`
  - Avance 27/10/2026: revisión Python/seguridad hecha y sus 9 defectos corregidos (ver validacion.md); `npm run build` y pytest OK. Falta la revisión de dirección financiera con el primer conector con estado de cuenta.

## Phase 11: Claridad de la sincronización (pedido de Sergio 27/10/2026, tarde)

- [X] T053 [US6] Columnas `Paso`, `AvanceHecho`, `AvanceTotal` en `Portales_Corridas` (DDL idempotente en `crear_esquema_boveda_042.py`, respaldo verificado) y `repository.avance()`; `servicio._procesar` informa cada paso
- [X] T054 [US2] Cola en memoria de la tanda manual (`servicio.en_cola`), sin encolar dos veces; "Sincronizar ahora" de una cuenta pasa por la misma cola; `POST /api/boveda/corridas` acepta `idsPortales` y devuelve `encolados` y `omitidos` con motivo
- [X] T055 [US6] `GET /portales` agrega `enCola`, `progreso` y `motivoNoSincroniza`; la vista de peajes cuenta la cola como "en curso"
- [X] T056 [US6] Pantalla `/boveda`: casillas y "Sincronizar seleccionadas", "Sincronizar todas las automáticas", barra general de la tanda, mensaje final y motivos; columnas "Acceso", "Sincronización automática" (reemplaza "Descarga") y "Estado" con barra y paso (`components/boveda/EstadoSincronizacion.tsx`)
- [X] T057 [US5] Alta de Movistar (contacto 71) en `--registrar-portales`; el registro reconoce portales renombrados por contacto (se borraron los duplicados 17 ARCA y 18 ARBA creados por error al registrar Movistar)

## Dependencies & Execution Order

- Setup → Foundational (T003–T010) bloquea todo.
- US1 → US4 → US2 → US3 (US2 y US3 necesitan autorización; US3 necesita corridas de US2 para la tarea semanal, pero `correr_portal` puede probarse con "Correr ahora").
- US5 depende de US1; US6 depende de US3.
- Phase 9: cada conector depende de US3 y es independiente de los demás (se pueden hacer en cualquier orden, sugerido el de FR-023).
- T035 (retirar tarea semanal) solo después de una corrida programada exitosa.

## Parallel Examples

- Foundational: T005, T009, T010 en paralelo tras T004.
- US1: T013, T014, T015 en paralelo tras T011–T012.
- US2: T024 y T025 en paralelo tras T021–T023.
- Phase 9: T040–T048 en paralelo entre sí (archivos distintos).

## Implementation Strategy

1. **MVP**: Setup + Foundational + US1 (bóveda segura de accesos) → validar con Sergio.
2. US4 + US2 + US3 con peajes migrados → retirar tarea semanal (primera entrega del plan).
3. US5 + US6 + Bayá Casal y Cargill (segunda entrega).
4. Conectores T042–T048 uno por uno (tercera entrega).
