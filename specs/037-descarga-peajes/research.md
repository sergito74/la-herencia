# Research: 037 — Descarga y carga automática de comprobantes de peajes

Relevamiento hecho el 2026-10-16 sobre los portales reales (con autorización de Sergio), la carpeta de Compras y las compras ya cargadas en `WC`.

## R1. Dónde vive la lógica (app + tarea semanal)

- **Decision**: Mover la lógica del script a un módulo del backend, `backend/src/features/descarga_peajes/`, que contiene la descarga, la lectura y la carga. `backend/scripts/descargar_peajes.py` queda como un punto de entrada fino (`--origen semanal`) que llama al mismo servicio. La tarea programada lo ejecuta con el Python de `backend/.venv`.
- **Rationale**: Un solo proceso, un solo registro (FR-009). La tarea semanal no depende de que la aplicación esté abierta: el launcher apaga el backend cuando se cierran las pestañas.
- **Alternatives considered**: (a) que la tarea semanal llame a la API: falla si el backend está apagado, que es lo normal un lunes a las 9. (b) Dos implementaciones separadas: el resultado divergiría.

## R2. Ejecución en segundo plano desde la API

- **Decision**: `POST /api/descarga-peajes/ejecuciones` crea la fila de ejecución, lanza un `threading.Thread(daemon=True)` y responde 202 con el id. El avance por portal se guarda en `WC` y el frontend lo consulta cada 2 s con TanStack Query (`refetchInterval` mientras el estado sea `en_curso`).
- **Rationale**: Es el patrón que ya existe (`main.py`, precalentado de la auditoría). Playwright sincrónico corre bien en un hilo propio. No suma una cola de tareas ni WebSockets.
- **Alternatives considered**: Celery/RQ (agrega infraestructura sin necesidad, un solo usuario); `BackgroundTasks` de FastAPI (corre en el mismo worker, no es más simple y es igual de frágil ante cortes); SSE (mejora menor frente al polling).

## R3. Evitar ejecuciones simultáneas entre procesos (FR-005)

- **Decision**: Usar un lock de aplicación de SQL Server, `sp_getapplock @Resource='DescargaPeajes', @LockOwner='Session', @LockTimeout=0`, sobre una conexión dedicada que dura toda la ejecución. Si no se obtiene, la ejecución se registra como `salteada` y la API devuelve 409 con el id de la que está en curso.
- **Rationale**: Sirve entre la API y la tarea programada (procesos distintos) y se libera solo si el proceso muere, así no quedan bloqueos colgados. Una ejecución que quedó `en_curso` sin lock vivo se marca `incompleta` al iniciar la siguiente. En "Descargar ahora" el lock se toma dentro de la misma petición HTTP antes de responder (202 o 409) y la conexión se pasa al hilo, que la libera al terminar: no hay carrera entre dos clics. El dry-run no toma el lock ni escribe nada.
- **Alternatives considered**: Un archivo de lock (queda colgado si el proceso muere); una fila "en curso" sin lock (carrera entre dos procesos y limpieza manual).

## R4. Lectura de los PDF (carga automática, FR-017/018)

- **Decision**: Un lector por formato en `lectores.py` (pdfplumber, ya está en requirements). Cada uno devuelve `{numero, fecha, tipo, renglones[(descripcion, cantidad, precio_unitario, iva)], percepcion_iibb, conceptos_no_gravados, sellos, total_impreso}`. La regla de cierre usa `compras.repository.calcular_totales` (la misma fórmula del alta) y exige `|calculado − total_impreso| ≤ 0,05`.
- **Formatos** (todos relevados sobre PDFs reales de la carpeta, todos con texto, sin escaneos):

| Formato | Origen | Proveedor (IdContacto) | Particularidades |
| --- | --- | --- | --- |
| Resumen Telepeaje | TelepeajePlus | Telepeaje (328) | Se carga como hoy: 1 renglón "Resumen peajes" en $0 y el impuesto de sellos en Ley de Sellos; si trae intereses financieros, el renglón es "Intereses financieros" con neto = interés/1,21 e IVA 21 (verificado en WC: 27/04/2026 $0,12 → $0,10; 27/05/2026 $0,14 → $0,12); Nº `0002-<resumen>`; fecha = cierre |
| Autopistas del Sol | TelePASE (ausol) | 276 | Renglones "X PASADAS [HP] - CAT n" con cantidad × precio neto, IVA 21; percepción IIBB en `Ingresos Brutos` |
| GCO | TelePASE (gco) | 306 | Como AUSOL; sin percepción en los casos vistos |
| AUSA | TelePASE (factura) | 380 | Renglones por circuito, IVA 21; conceptos no gravados (contribución ferroviaria) y percepción IIBB |
| Corredores Viales | TelepeajePlus / TelePASE (cvsa) | 436 | "PASOS ... KM", IVA 21 |
| Corresur | TelepeajePlus | 2657 | Ídem; el IVA viene en un renglón aparte: se recalcula sobre el neto |
| CV5 / Pentavia | TelepeajePlus | 2658 | Ídem Corresur |
| CEAMSE | Oficina virtual | 314 | 1 renglón "TRANSACCIONES TELEPASE - CAT n"; percepción IIBB o no gravados según la factura |
| AUBASA | Oficina virtual | 316 | Varios renglones por estación y "Gastos Administrativos"; percepción IIBB |

- **Percepción de IVA (decisión de Sergio 2026-10-16, tras la revisión de dirección financiera)**: la RG 3337 / 3 % va a `percepcionIva` (AUSOL 138,03 = 3 % de 4.601,05; CEAMSE 74,38; AUBASA 833,60; AUSA RG 3337). Las cargas manuales anteriores la tenían en `Ingresos Brutos` y no se tocan. IIBB → `ingresosBrutos`; IVA no inscripto, RAE, no gravado y contribución ferroviaria → `conceptosNoGravados`. Cada lector exige la cantidad exacta de columnas de totales; si cambia, queda pendiente.
- **Común a todos**: rubro Viáticos (2047893477), centro de costo 3, destino 1, campaña "No Aplica", moneda Pesos, tipo A (Factura), unidad "PASADA" (o "RESUMEN"/"PEAJE" como en lo histórico).
- **Rationale**: Reproduce exactamente las cargas manuales recientes (consultadas en `WC`, IdDeuda 2143519506–2143522636). La regla de cierre es la misma que se usó a mano el 2026-10-16.
- **Alternatives considered**: OCR o IA genérica (innecesario, porque los PDF tienen texto, y menos verificable); cargar un solo renglón con el neto total (pierde el detalle de pasadas que hoy se registra).
- **Riesgo**: si un proveedor cambia el formato, el lector no reconoce el comprobante o no cierra, y el documento queda pendiente. No hay riesgo de cargar mal en silencio.

## R5. Dependencias nuevas

- **Decision**: Agregar `playwright>=1.47` y `keyring>=25` a `backend/requirements.txt` e instalarlos en `backend/.venv` (con autorización de Sergio, en la implementación). Playwright usa `channel="chrome"` (el Chrome instalado), así que no hay que bajar navegadores.
- **Rationale**: El backend corre con `.venv`, que hoy no tiene estas librerías; el script de prueba usó el Python del sistema.

## R5b. PDFs de prueba y datos personales

- **Decision**: Los PDFs reales no se versionan: tienen el domicilio particular de Sergio, CUIT y número de cliente (Constitución, Data and Security Constraints). En el repo queda `tests/fixtures/peajes/casos.json` con rutas de Dropbox y valores esperados; los tests leen los PDFs de Dropbox y hacen `skip` si no están.
- **Alternatives considered**: copiar PDFs al repo (viola la Constitución); anonimizar los PDFs (costoso y altera el texto que hay que leer).

## R6. Credenciales y tarea programada

- **Decision**: Las credenciales siguen en el Administrador de credenciales de Windows (servicio `LaHerencia-Peajes`) y las carga el instalador. La API solo consulta si existen (`keyring.get_password(...) is not None`) y nunca devuelve el valor. El estado y la próxima corrida de la tarea se leen con `schtasks /Query /TN "LaHerencia - Descarga peajes" /FO CSV /V`, en solo lectura. El instalador pasa a usar el `.venv` y `-m scripts.descargar_peajes --origen semanal`.
- **Rationale**: FR-013/014/015. La aplicación no puede crear credenciales ni tareas: esa operación queda en manos de Sergio.

## R7. Registro y migración de lo ya descargado

- **Decision**: Tres tablas nuevas en `WC` con prefijo `DescargaPeajes_` (nombres que no existen hoy; ver [[project-wc-tablas-ajenas]]). El manifiesto `_descargas_portales.json` (98 claves) se importa como documentos con estado `historico` (ya bajados antes del módulo, sin ejecución), así no se repiten. El archivo `.log` deja de escribirse.
- **Rationale**: `WC` es el sistema de registro (Principio I) y da trazabilidad entre el documento y la compra (Principio IV).

## R8. Contador del menú (FR-020)

- **Decision**: `GET /api/descarga-peajes/resumen` devuelve `{pendientes, portalesConError}`. El ítem del menú lo consulta cada 5 minutos y al volver a la pestaña. "Pendiente" se recalcula: un documento pendiente deja de contar si ya existe una compra con ese archivo como documento original o con el mismo proveedor y número.
- **Rationale**: No hace falta marcar a mano: si Sergio carga el comprobante por la pantalla de Compras, el contador baja solo.
