# Research: Conciliación histórica de cuentas corrientes

## 1. Cómo distinguir aplicaciones automáticas de manuales

**Decision**: agregar dos columnas nuevas a `AplicacionesPago` (creada en 019): `Origen varchar(20) NOT NULL DEFAULT 'manual'` (`'manual'`|`'automatica-exacta'`|`'automatica-mejor-esfuerzo'`) y `NotaConciliacion nvarchar(255) NULL` (detalle de qué candidatos se combinaron, para revisión humana).

**Rationale**: la 019 ya documenta la tabla como inmutable (insertar/anular, nunca editar) e indexada por `(OrigenMovimiento, IdMovimientoOrigen)` y `(TipoDocumento, IdDocumentoAplicado)`. Agregar columnas con `DEFAULT` no rompe filas existentes ni el contrato de la 019 (`Usuario` para automáticas puede ser un valor fijo, ej. `'sistema-conciliacion-020'`, reusando la misma columna en vez de crear una nueva).

**Alternatives considered**: tabla separada `AplicacionesPagoHistoricas` — rechazada porque duplicaría lógica de estado/anulación y rompería la premisa de la 019 de que el estado de un documento/movimiento sale de una sola fuente (`AplicacionesPago`).

## 2. Cómo obtener el "saldo de referencia" para comparar (resuelto 2026-09-25)

**Decision final**: el usuario pidió explícitamente calcular el saldo "desde Access" y compararlo contra la conciliación del sistema nuevo. Investigando los archivos `La Herencia/*.accdb` con el driver ODBC de Access (`cur.tables()`), se confirmó que **`AdmLaHerenciaVer3.accdb` no tiene datos propios**: sus tablas son `SYNONYM` (enlaces ODBC) al mismo DSN `SQL_LaHerencia` que usa el backend, pero apuntando a la base **`LaHerencia`** (la oficial protegida) en vez de `WC`. Es decir: **Access hoy es un front-end sobre `LaHerencia`**, no una base de datos independiente. El "saldo real de Access" que pedía el usuario es, en los hechos, `vw_MovimientosCuenta_Saldo` calculado sobre `LaHerencia`.

Se confirmó además que `LaHerencia` sigue viva y recibiendo carga real desde Access, independiente de `WC`: al comparar (2026-09-25), `LaHerencia` tenía 6.436 `Compras` contra 6.435 de `WC` (llevan meses divergiendo desde el snapshot del 2026-09-17), y `AplicacionesPago` no existe en `LaHerencia` — aislamiento de escritura intacto, nunca se tocó la base protegida.

**Implementación**: `backend/scripts/comparar_saldo_laherencia.py` abre una conexión de solo lectura dedicada a `LaHerencia` (reutilizando el guard `_assert_read_only` de `src/db/connection.py`, nunca las funciones de escritura), lee `vw_MovimientosCuenta_Saldo` con la misma fórmula que ya usa 004, y compara contra `cuentas_corrientes.get_saldos_todos()` de `WC`. El resultado se persiste en `SaldosReferenciaAccess` (`--apply`) para que el endpoint de revisión no tenga que releer `LaHerencia` en cada consulta.

**Resultado real de la primera corrida (2026-09-25)**: 512 de 513 contactos coinciden dentro de la tolerancia (0.5% relativo, mínimo $1) — confirma que la conciliación histórica (US1) no alteró ningún saldo (`AplicacionesPago` no interviene en el cálculo de `SaldoParcial`, es independiente). El único caso con diferencia (contacto #5, Agrovet Integral SRL, diferencia $439.913,82) se investigó puntualmente: una `Compra` (factura 0003-00068465) existe en `WC` pero no en `LaHerencia` — se cargó directo en `WC` el 2026-09-16 y nunca se registró en el sistema Access real. Es un hallazgo real (documento no ingresado en producción), no un efecto de esta feature.

**Alternatives considered**: pedirle al usuario una exportación manual (CSV/Excel) — descartado una vez confirmado que `LaHerencia` es accesible en vivo y de solo lectura, es más preciso y no depende de que alguien genere y mantenga un archivo. Inventar un saldo de referencia derivándolo de los mismos datos de `WC` — rechazado (compararía el sistema contra sí mismo).

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
