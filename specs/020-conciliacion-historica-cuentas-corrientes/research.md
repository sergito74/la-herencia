# Research: Conciliación histórica de cuentas corrientes

## 1. Cómo distinguir aplicaciones automáticas de manuales

**Decision**: agregar dos columnas nuevas a `AplicacionesPago` (creada en 019): `Origen varchar(20) NOT NULL DEFAULT 'manual'` (`'manual'`|`'automatica-exacta'`|`'automatica-mejor-esfuerzo'`) y `NotaConciliacion nvarchar(255) NULL` (detalle de qué candidatos se combinaron, para revisión humana).

**Rationale**: la 019 ya documenta la tabla como inmutable (insertar/anular, nunca editar) e indexada por `(OrigenMovimiento, IdMovimientoOrigen)` y `(TipoDocumento, IdDocumentoAplicado)`. Agregar columnas con `DEFAULT` no rompe filas existentes ni el contrato de la 019 (`Usuario` para automáticas puede ser un valor fijo, ej. `'sistema-conciliacion-020'`, reusando la misma columna en vez de crear una nueva).

**Alternatives considered**: tabla separada `AplicacionesPagoHistoricas` — rechazada porque duplicaría lógica de estado/anulación y rompería la premisa de la 019 de que el estado de un documento/movimiento sale de una sola fuente (`AplicacionesPago`).

## 2. Cómo obtener el "saldo de referencia" para comparar (actualizado 2026-09-25)

**Decision** (revisada tras respuesta del usuario, ver tasks.md): no existe todavía una exportación de Access con la que comparar, ni el usuario va a armarla en el corto plazo. El "saldo actual reconstruido desde el arrastre de movimientos" que pedía US3 **ya existe**: es exactamente `dbo.vw_MovimientosCuenta_Saldo` (columna `SaldoParcial`), la vista que 004 ya consume vía `cuentas_corrientes.repository.get_saldo`/`get_saldos_todos` — confirmada contra el formulario Access real `SbfrmMovCuenta` (memoria `project_access_forms_analysis`, mismo bug de `ORDER BY` ya corregido en 2026-09-17). No hay nada nuevo que "armar desde el inicio": la reconstrucción del arrastre ya está hecha en esa vista, y es la misma fuente para todo el sistema (018/019/004).

Lo que sí falta, y que el usuario aclaró explícitamente que se resuelve después ("habrá que analizarlos contra los saldos reales de cada cuenta"), es un **dato de verdad externo** (el saldo real de cada cuenta, fuera del sistema) contra el cual validar que `SaldoParcial` es correcto. Sin ese dato, US3 tal como estaba especificada (comparar `SaldoParcial` contra un `SaldoAccess` cargado) no tiene con qué compararse todavía.

**Se pospone la Tabla `SaldosReferenciaAccess` y el script de carga** hasta que exista esa fuente externa real. Mientras tanto, el valor que aporta esta feature en el frente de "saldo" es indirecto: al aplicar el histórico (US1), más movimientos pasan a tener Rubro/Centro de Costos real en 018, pero `SaldoParcial` en sí **no cambia** — es un cálculo sobre `vw_MovimientosCuenta_Saldo`/`vw_MovimientosCuenta_Base`, independiente de `AplicacionesPago`. Aplicar el histórico no mueve el saldo de ningún contacto; solo le da significado (a qué documento corresponde cada movimiento) a movimientos que ya estaban sumados en ese saldo.

**Alternatives considered**: conectar el backend directamente a los `.accdb` vía ODBC — rechazado (Principio I: preservar Access sin tocarlo, y sin ser fuente de la app nueva). Inventar un saldo de referencia derivándolo de los mismos datos de `WC` — rechazado explícitamente por el usuario: compararía el sistema contra sí mismo, no aportaría ninguna validación real.

## 3. Patrón de ejecución del proceso de aplicación histórica

**Decision**: script en `backend/scripts/conciliar_historico_cuentas_corrientes.py`, mismo patrón que `migrar_ordenes.py`: dry-run por defecto (imprime plan: cuántos movimientos, cuántos exactos, cuántos mejor esfuerzo, cuántas excepciones), requiere `--apply` para escribir, idempotente (salta movimientos que ya tienen aplicaciones vigentes — chequeo directo sobre `AplicacionesPago`, no requiere marcador adicional).

**Rationale**: reutiliza un patrón ya validado y aprobado por el usuario en 3 migraciones previas (`migrar_ordenes.py`, `migrar_remitos.py`, `migrar_vinculo_contratista.py`); cumple Constitución Principio II (no escribe sin `--apply` explícito) y VII (reversible: cada aplicación se anula individualmente si hace falta, sin rollback de script).

**Alternatives considered**: endpoint HTTP que dispare el proceso desde el frontend — rechazado para la primera pasada: es un proceso de corrida única (o pocas), sobre todo el histórico 2015-2026, mejor controlado desde línea de comandos con revisión de la salida antes de confirmar `--apply`; no impide agregar un endpoint de re-ejecución más adelante si se necesita.

## 4. Definición operativa de "mejor esfuerzo" (FIFO aproximado)

**Decision**: dado un movimiento histórico de importe `M` para un contacto, se buscan documentos pendientes del contacto ordenados por fecha (FIFO, igual que `sugerencia.sugerir` de 019). Se prueba primero la combinación exacta (documento único o suma de N documentos consecutivos que cierra contra `M` dentro de `TOLERANCIA_REDONDEO_APLICACION`). Si no cierra exacto, se toma la combinación FIFO que más se acerca a `M` sin excederlo por más de una tolerancia relativa configurable (ej. 2%, ya usada y calibrada en conciliación de documentos USD — memoria `project_conciliacion_documentos_usd`) y se marca `'automatica-mejor-esfuerzo'` con la diferencia en `NotaConciliacion`.

**Rationale**: reutiliza la función de sugerencia FIFO existente (`sugerencia.sugerir`) en vez de reimplementar matching; la tolerancia del 2% ya fue validada con datos reales en un contexto similar (conciliación de documentos en USD), evitando inventar un nuevo umbral sin respaldo.

**Alternatives considered**: aplicar siempre el primer documento pendiente sin verificar cierre de importe — rechazado, generaría "mejor esfuerzo" en casos que en realidad podrían cerrar exacto con otra combinación, perdiendo precisión sin necesidad.

## 5. Alcance de "documentos" para ventas

**Decision**: igual que 019 US2, "documentos de venta" incluye tanto `VentaHacienda` como `VentaGranos`, combinadas y ordenadas por fecha para la búsqueda FIFO del lado de cobros.

**Rationale**: consistencia directa con el `TipoDocumento` ya soportado por `AplicacionesPago`; no hay un tercer tipo de documento de venta en el sistema migrado.
