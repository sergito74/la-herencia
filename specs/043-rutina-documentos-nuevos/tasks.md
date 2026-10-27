---
description: "Tareas de 043 — Rutina automática de documentos nuevos"
---

# Tasks: Rutina automática de documentos nuevos

**Input**: `specs/043-rutina-documentos-nuevos/` (spec.md, plan.md, research.md, data-model.md, contracts/api.md, quickstart.md)

**Tests**: pedidos por el plan (unitarias del clasificador y la marca de mails, contrato de API con datos simulados, `tsc --noEmit`). Nunca escriben en `WC`.

**Organización**: por historia de usuario. US1 y US2 son P1 (Sergio las pidió juntas); US3 es P2. Se trabaja sobre `main`, como 042.

## Formato: `[ID] [P?] [Story] Descripción`

---

## Phase 1: Setup

- [X] T001 Crear el paquete `backend/src/features/documentos_nuevos/` con `__init__.py` y `lectores/__init__.py` (patrón de `backend/src/features/boveda/`)
- [X] T002 [P] Crear `backend/tests/documentos_nuevos/__init__.py` con helpers de datos simulados (conexión falsa, sin `WC`) siguiendo `backend/tests/pastaje_039_helpers.py`

---

## Phase 2: Foundational (bloquea todas las historias)

- [X] T003 Escribir `backend/scripts/crear_esquema_rutina_043.py` (patrón `crear_esquema_boveda_042.py`: `--verificar`, aplicar con respaldo verificado previo, `--revertir`) creando en `WC`: `Rutina_Corridas` (IdRutinaCorrida int identity PK; Inicio, Fin datetime2(0), "Fin NULL = en curso"; Origen nvarchar(20) `programada`/`prueba`; Estado nvarchar(20) `en_curso|ok|con_problemas|incompleta`; CuentasCorridas, CuentasConProblemas, MailsLeidos, DocumentosNuevos, CargadosSolos, ParaCargarAMano int; Mensaje nvarchar(400)), `Rutina_Programacion` (fila única: Horarios nvarchar(50) `07:00,14:00`, ProximaCorrida datetime2(0), Activa bit), `Rutina_MarcaMails` (Almacen nvarchar(200) PK, UltimoRecibido datetime2(0)), `DocumentosNuevos` (todas las columnas de data-model.md: Origen nvarchar(10) `portal`/`mail`; IdPortal/IdDocumentoPortal FK NULL; MailEntryId nvarchar(200); MailRemitente, MailAsunto nvarchar(200); MailRecibido; Sha256 char(64) **único junto con Modulo**; Ruta nvarchar(400); Tipo nvarchar(30); Modulo nvarchar(30) `compras|impuestos|ventas|tesoreria|cuentas_corrientes|sin_clasificar`; IdContacto; Fecha date; Numero nvarchar(50); Total decimal(18,2); Estado nvarchar(20) `cargado_solo|para_cargar|ya_estaba`; Motivo nvarchar(300); IdRegistro int; Revisado datetime2(0); RevisadoPor nvarchar(60); ModuloAnterior nvarchar(30) NULL; ModuloCambiado datetime2(0) NULL; ModuloCambiadoPor nvarchar(60) NULL; Creado default SYSDATETIME()), e índice filtrado para pendientes (`Estado IN ('cargado_solo','para_cargar') AND Revisado IS NULL`); elimina `Portales_Documentos.Revisado` (el revertir la restaura)
- [X] T004 Correr `python -m scripts.crear_esquema_rutina_043 --verificar` y luego aplicar en `WC` tras respaldo verificado (nunca `LaHerencia`); la salida del script registra ruta y verificación del respaldo (como en 042) y se copia al traspaso de T041
- [X] T005 Implementar `backend/src/features/documentos_nuevos/repository.py`: `registrar_documento(...)` idempotente por (Sha256, Modulo) que devuelve el existente sin duplicar; `resumen_pendientes()` por módulo; `listar_pendientes(modulo, limite, desde)` más antiguos primero; `marcar_revisado(id, usuario)`; `cambiar_modulo(id, modulo, usuario)` auditado en `ModuloAnterior`/`ModuloCambiado`/`ModuloCambiadoPor`; funciones de `Rutina_Corridas` (abrir con candado de una sola `en_curso`, cerrar, pasar `en_curso` viejas a `incompleta`), `Rutina_Programacion` y `Rutina_MarcaMails`
- [X] T006 [P] Agregar esquemas Pydantic en `backend/src/features/documentos_nuevos/schemas.py` (resumen, ítem con renglones, body de módulo, estado de rutina) según `contracts/api.md`, con nombres camelCase y textos de negocio

**Checkpoint**: tablas creadas y repositorio listo.

---

## Phase 3: User Story 1 — Ver en cada módulo los documentos nuevos y revisarlos (P1) 🎯 MVP

**Goal**: número por módulo en el menú, vista "Nuevos para revisar" con el documento cargado, "Revisado", retiro del listado de la bóveda. Funciona con lo que ya bajan las cuentas de 042.

**Independent Test**: con la factura de octubre de Allianz cargada sola, ver "Compras 1" en el menú, clic → documento abierto, "Revisado" → el número baja; la bóveda ya no muestra "Cargado solo en Compras — para revisar".

### Tests

- [X] T007 [P] [US1] Pruebas de contrato de `GET /resumen`, `GET /?modulo=`, `POST /{id}/revisado` (404 si no pendiente), `POST /{id}/modulo` y permisos (escritura solo Administrador) en `backend/tests/documentos_nuevos/test_contrato_api.py`
- [X] T008 [P] [US1] Pruebas del repositorio (idempotencia Sha256+Modulo, `ya_estaba` no cuenta, `para_cargar` con IdRegistro sigue pendiente) en `backend/tests/documentos_nuevos/test_repository.py`

### Implementation

- [X] T009 [US1] Implementar `backend/src/features/documentos_nuevos/router.py` con prefijo `/api/documentos-nuevos` (contracts/api.md): `modulo` validado contra lista permitida; `origen` "Portal <nombre>" / "Mail de <remitente>"; `enlace` al registro del módulo; `renglones` (detalle, rubro, centro de costo, importe, IVA) solo para Compras; registrarlo en `backend/src/main.py`
- [X] T010 [US1] En `backend/src/features/boveda/servicio.py`, cada documento de portal que se carga solo o queda sin cargar genera su fila en `DocumentosNuevos` (Origen `portal`, IdPortal, IdDocumentoPortal, módulo `compras`, estado y motivo en palabras simples; `ya_estaba` si ya existía)
- [X] T011 [US1] Backfill único (hecho como paso de `backend/scripts/crear_esquema_rutina_043.py`, antes de quitar la columna): pasa a `DocumentosNuevos` los documentos de portal cargados solos aún no revisados (Allianz, Movistar, peajes) para que el aviso arranque con contenido
- [X] T012 [US1] Retirar de `backend/src/features/boveda/router.py` y `repository.py` `GET /api/boveda/revision` y `POST /api/boveda/documentos/{id}/revisado`; `GET /api/boveda/resumen` deja de contar pendientes de carga
- [X] T013 [P] [US1] Crear `frontend/src/services/documentosNuevosApi.ts` (tipos y hooks TanStack Query: resumen, lista por módulo, revisado, cambiar módulo; invalidar resumen al marcar)
- [X] T014 [US1] En `frontend/src/components/layout/NavHeader.tsx`, mostrar el número junto a Compras (compras + sin clasificar), Ventas y Finanzas, y en el submenú junto a Tesorería, Cuentas corrientes e Impuestos y retenciones (mismo estilo que el contador de peajes); el clic lleva a la pantalla con `?nuevos=1`
- [X] T015 [US1] Crear `frontend/src/components/documentos-nuevos/NuevosParaRevisar.tsx` (prop `modulo`): lista + primero abierto con contacto, fecha, número, total, renglones con rubro y centro de costo, archivo original; botones "Revisado" (oculto para Solo lectura), "Ver/corregir" que abre el registro con las herramientas del módulo, "Cargar a mano" para `para_cargar` con su motivo; para `sin_clasificar` un selector "¿A qué módulo va?"; formato de números con los helpers globales (miles '.', decimales ',', nunca `toLocaleString`); sin términos internos
- [X] T016 [US1] Montar `NuevosParaRevisar` con `?nuevos=1` en `frontend/src/app/compras/page.tsx` (más filtro "Sin clasificar"), `frontend/src/app/ventas/granos/page.tsx`, `frontend/src/app/ventas/hacienda/page.tsx`, `frontend/src/app/finanzas/tesoreria/page.tsx`, `frontend/src/app/finanzas/cuentas-corrientes/page.tsx` (abre la cuenta del contacto) y `frontend/src/app/finanzas/impuestos/page.tsx`
- [X] T017 [US1] Eliminar `frontend/src/components/boveda/RevisionCargas.tsx`, su uso en `frontend/src/app/boveda/page.tsx` y las funciones de revisión en `frontend/src/services/bovedaApi.ts`

**Checkpoint**: aviso + revisión funcionando con documentos de portal; bóveda sin listado de revisión.

---

## Phase 4: User Story 2 — Rutina programada que trae y carga lo nuevo (P1)

**Goal**: a las 07:00 y 14:00, sin botón, sincroniza todas las cuentas, lee los mails nuevos, guarda, carga lo que sabe leer y deja el resto "para cargar a mano".

**Independent Test**: adelantar `Rutina_Programacion.ProximaCorrida`; verificar fila `ok`/`con_problemas` en `Rutina_Corridas`, una corrida por cuenta sincronizable, marca de mails adelantada; repetir y comprobar que no hay mails reprocesados ni avisos duplicados.

### Tests

- [X] T018 [P] [US2] Pruebas unitarias de la marca de mails (solo `ReceivedTime` > marca; marca se adelanta solo al cerrar bien; primera corrida fija la marca sin barrer historia; la marca del almacén avanza aunque una cuenta de portal falle; dedup por EntryID+SHA-256) en `backend/tests/documentos_nuevos/test_mails.py`
- [X] T019 [P] [US2] Pruebas unitarias del clasificador con textos de PDF de ejemplo (tipo, emisor por CUIT, receptor Giamigli 30-71211460-2 o Sucesión aceptado, San Justo ignorado, módulo, carpeta; no-comprobante ignorado; emisor nuevo → `para_cargar` "Emisor nuevo"; Galicia Visa vs Galicia Rural por contenido) en `backend/tests/documentos_nuevos/test_clasificador.py`
- [X] T020 [P] [US2] Pruebas de la corrida con conectores y Outlook simulados (cuenta que falla no corta la rutina; Outlook caído → cuentas corren y mails quedan para la próxima; no se lanza otra corrida en curso; recuperación única tras apagado) en `backend/tests/documentos_nuevos/test_rutina.py`

### Implementation

- [X] T021 [P] [US2] Implementar `backend/src/features/documentos_nuevos/mails.py`: Outlook COM solo lectura reusando `backend/src/features/boveda/mails.py`; recorre las bandejas de entrada de todos los almacenes; toma mails con `ReceivedTime` posterior a `Rutina_MarcaMails`; adjuntos PDF (y XML de comprobante); nunca marca, mueve, responde ni borra
- [X] T022 [P] [US2] Implementar `backend/src/features/documentos_nuevos/clasificador.py` (pdfplumber): tipo (factura/NC/ND, boleta, retención, liquidación, recibo, resumen_banco, resumen_tarjeta, resumen_proveedor, contrato), emisor por CUIT → `Contactos` (nunca crea contactos), receptor (Giamigli o Sucesión —etapa previa de Giamigli—; San Justo, socios y Alquileres se ignoran, research P1), módulo y carpeta según la tabla de research R3 y las Clarifications (Bancos `<Banco>\<Producto>\<Año>` con `Extracto AAAA MM`/`AAAA MM`; Resumenes de Cuenta `<Proveedor>\` nombre original; `Agricultura\Contratos\Contrato <Comprador> <número>.pdf` con variante `(AF Soja)`/`(Carta Fijacion)`/`(CF)` y `Fijacion cto. <número>.pdf`); no se decide → `sin_clasificar` guardado en Compras del ejercicio
- [X] T023 [US2] Implementar el registro de lectores en `backend/src/features/documentos_nuevos/lectores/__init__.py` por (tipo, emisor), registrando los ya probados de 042/037 (peajes, Allianz, Movistar, reusando `backend/src/features/boveda/carga.py`); carga solo si cierra al centavo contra el total impreso, si no `para_cargar` con motivo "No cierra al centavo…"; documento ya existente → `ya_estaba`
- [X] T024 [US2] Implementar `backend/src/features/documentos_nuevos/rutina.py`: abre corrida (candado, una sola `en_curso`), sincroniza de a una las cuentas con autorización vigente y contraseña (vía `boveda/servicio.py`); si una cuenta está ocupada por su propia programación de 042, la saltea, la informa y sigue, procesa mails → clasificador → guardar archivo sin duplicar → lector → `DocumentosNuevos` (mismo archivo por portal y mail = un solo aviso); cuenta con verificación humana o contraseña rechazada queda informada en palabras simples y sigue; cierra con totales; adelanta `Rutina_MarcaMails` de cada almacén cuya lectura terminó bien, aunque la corrida quede `con_problemas` por portales
- [X] T025 [US2] En `backend/src/features/boveda/planificador.py`, agregar el tick de la rutina: horarios 07:00 y 14:00 desde `Rutina_Programacion`, recuperación única si el backend estuvo apagado, al arrancar pasa `en_curso` viejas a `incompleta`; sin botón ni endpoint para disparar (FR-001); la programación por cuenta de 042 se mantiene
- [X] T026 [US2] Agregar `GET /api/documentos-nuevos/rutina` (solo Administrador: próxima corrida, última corrida con estado, mails leídos, documentos nuevos, cargados solos, para cargar a mano, mensaje) en `backend/src/features/documentos_nuevos/router.py`
- [X] T027 [US2] Mostrar en `frontend/src/app/boveda/page.tsx` un panel "Rutina diaria" (componente nuevo `frontend/src/components/boveda/RutinaPanel.tsx`) con próxima corrida y resultado de la última en palabras simples; sin botón de disparo

**Checkpoint**: rutina corriendo sola dos veces por día y alimentando los avisos de US1.

---

## Phase 5: User Story 3 — De Campo a Campo automatizada (P2)

**Goal**: la cuenta 21 baja sola liquidaciones y certificados de retención de Giamigli, sin operar en el portal y sin nada de Ganadera San Justo.

**Independent Test**: sincronizar la cuenta: solo aparecen liquidaciones/retenciones de Giamigli (30-71211460-2); ninguna operación de San Justo se lista ni se baja; un documento ya cargado a mano se vincula sin duplicar.

- [ ] T028 [US3] Implementar `backend/src/features/boveda/conectores/decampoacampo.py` (Chromium sin cabeza): login en `https://www.decampoacampo.com/__dcac/login` (`#btn_login` → `#maillog`, `#password`, `#ingresar_login`); Operaciones › Ventas/Compras en `react.alb.decampoacampo.com/operacion/invernada/{venta|compra}` y Perfil › Mi Historial de Retenciones; **filtra por sociedad Giamigli (CUIT 30-71211460-2) antes de abrir o bajar nada**; baja solo Liquidación y certificados de retención; nunca usa Programar pago, Ofertar, Comprar, Cotizar ni Consultas; registrarlo en `backend/src/features/boveda/conectores/__init__.py`
- [ ] T029 [P] [US3] Pruebas del filtro de sociedad y de las acciones prohibidas con páginas simuladas en `backend/tests/documentos_nuevos/test_decampoacampo.py`
- [ ] T030 [US3] Destino de sus documentos: liquidaciones → Ventas (hacienda), certificados → Impuestos, vía el clasificador/`DocumentosNuevos`; vínculo con lo ya cargado a mano como `ya_estaba` en `backend/src/features/boveda/servicio.py`
- [ ] T031 [US3] Probar contra el portal real (solo lectura) y recién entonces poner `Portales.CodigoConector = 'decampoacampo'` para el portal 21 en `WC` con `backend/scripts/activar_decampoacampo_043.py`

**Checkpoint**: De Campo a Campo incluida en la rutina.

---

## Phase 6: Lectores adicionales (uno por tarea, contra cargas reales; amplía US2)

Cada lector se valida contra documentos ya cargados a mano: la carga automática tiene que coincidir al centavo e imputar igual; si no, no se registra.

- [ ] T032 [US2] Lector de certificados de retención (desde `backend/scripts/cargar_retenciones_certificados.py`) en `backend/src/features/documentos_nuevos/lectores/retenciones.py`
- [ ] T033 [US2] Lector de liquidaciones Cargill (desde `backend/scripts/cargill_liquidaciones_pdf_036.py`) en `backend/src/features/documentos_nuevos/lectores/cargill.py`
- [ ] T034 [US2] Lector de resúmenes Visa Galicia (desde `backend/scripts/cargar_resumen_visa_galicia_pdf.py`) en `backend/src/features/documentos_nuevos/lectores/visa_galicia.py`
- [ ] T035 [US2] Lector de resúmenes Mercado Libre (desde `backend/scripts/cargar_resumenes_mercado_libre_pdf.py`) en `backend/src/features/documentos_nuevos/lectores/mercado_libre.py`
- [X] T036 [US2] Extractos bancarios: guardar + avisar en Tesorería con enlace a la importación existente (sin importar solos) en `backend/src/features/documentos_nuevos/clasificador.py` y `NuevosParaRevisar.tsx`; el lector automático desde `importar_extractos.py` queda fuera de esta entrega

---

## Phase 7: Polish & Cross-Cutting

- [X] T037 [P] `npx tsc --noEmit` en `frontend/` y `pytest backend/tests/documentos_nuevos` en verde
- [X] T038 [P] Revisar textos de pantallas (`NuevosParaRevisar.tsx`, `RutinaPanel.tsx`, `NavHeader.tsx`) sin términos internos (conector, ids, códigos) — FR-016
- [ ] T039 Validación completa según `specs/043-rutina-documentos-nuevos/quickstart.md` (secciones 1–5), incluida la corrida de prueba adelantando `ProximaCorrida`; verificar con Inicio/Fin de `Rutina_Corridas` que dure menos de 15 minutos
- [ ] T040 Consultar a los agentes especialistas de `.github/agents/` sobre la entrega (checkpoint de módulo) y aplicar correcciones
- [X] T041 Dejar traspaso "DÓNDE QUEDAMOS" en `specs/043-rutina-documentos-nuevos/` y commit + push a `main`

---

## Dependencies & Execution Order

- Setup (T001–T002) → Foundational (T003–T006) → historias.
- **US1** (T007–T017): solo depende de Foundational. Es el MVP: cumple la regla de Sergio desde el primer día con lo que ya bajan las cuentas.
- **US2** (T018–T027): depende de Foundational; usa `DocumentosNuevos` y se ve a través de los avisos de US1 (se puede construir en paralelo, se valida mejor con US1 hecha).
- **US3** (T028–T031): depende de US2 para entrar en la rutina (T030 usa el clasificador T022); el conector en sí (T028) es independiente.
- **Lectores** (T032–T036): después de T023; independientes entre sí, de a uno.
- Polish: al final.

Dentro de cada historia: pruebas → repositorio/servicios → endpoints → frontend.

## Parallel Example

```text
# Foundational
T006 schemas.py  ||  T005 repository.py (archivos distintos)

# US1
T007 test_contrato_api.py || T008 test_repository.py || T013 documentosNuevosApi.ts

# US2
T018 test_mails.py || T019 test_clasificador.py || T020 test_rutina.py
T021 mails.py || T022 clasificador.py
```

## Implementation Strategy

1. **MVP**: Setup + Foundational + US1 → validar con Allianz/Movistar/peajes ya cargados → commit.
2. US2: rutina + mails + clasificador → validar con corrida de prueba → commit.
3. US3: De Campo a Campo (solo Giamigli) → commit.
4. Lectores adicionales, uno por commit, cada uno contra cargas reales.
