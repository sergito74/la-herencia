# Validación del módulo 013 — 2026-09-22

T025 se ejecutó contra `WC` real (Galicia; BNA no se pudo probar con un
archivo `.xls` real porque `xlwt` no está instalado en el entorno — mismo
límite ya documentado en `specs/003-tesoreria/tasks.md` T022 — pero comparte
exactamente el mismo código de deduplicación/persistencia, ya cubierto por
`test_tesoreria_confirmacion_carga.py`).

## Completado

- 384 tests de backend corridos, 383 pasan (la única falla, `test_db_connection.py::test_execute_write_refuses_target_laherencia_case_insensitive`, es preexistente y no relacionada — confirmado con `git stash`).
- `tsc --noEmit` del frontend pasa sin errores.
- Escenario 1 (confirmar carga nueva): 2 movimientos de un Excel de prueba insertados en `Movimientos Galicia`, visibles en `get_movimientos` inmediatamente.
- Escenario 2 (mismo archivo dos veces): segunda confirmación insertó 0 movimientos, ambos correctamente marcados como duplicados.
- Escenario 3 (previsualización vs. confirmación): el conteo de `previsualizar_confirmacion` coincidió exactamente con el resultado real de `confirmar_carga` en las dos corridas.
- Escenario 4 (trazabilidad): `listar_cargas('galicia')` devolvió el historial correcto; `get_movimientos`/`get_movimiento` expusieron `idCarga` correcto en los movimientos importados y `idCarga: null` en movimientos históricos reales.
- Escenario 5 (fila incompleta): un archivo con una fila sin débito/crédito se contó como `omitidosIncompletos: 1` y no se insertó; la fila completa del mismo archivo sí se insertó.
- Escenario 6 (contacto en blanco): confirmado por código — el `INSERT` no incluye `IdContacto`/`Contacto`, quedan `NULL`.
- Todos los datos de prueba (movimientos + cargas) se borraron al terminar — `WC` quedó exactamente como estaba antes de la verificación.

## Bugs reales encontrados y corregidos durante T025

Los primeros tres solo aparecieron corriendo contra `WC` real — los tests unitarios con datos sintéticos (fechas/importes ya como `date`/`float` en ambos lados) no los detectaban, así que se agregaron regresiones específicas después de encontrarlos:

1. **`Decimal` de SQL Server vs. `float` del Excel**: `Movimientos Galicia`/`Movimientos BNA` devuelven `Débitos`/`Créditos`/`Importe` como `Decimal` (columnas `money`); comparar `Decimal == float` en Python nunca lanza error, solo da `False` siempre — ningún duplicado real se detectaba. Corregido normalizando ambos lados a `float` (`confirmacion_carga._norm_monto`).
2. **`datetime` de SQL Server vs. `date` del Excel**: mismo problema con las fechas (`datetime` vs `date`, columnas `datetime`). Corregido con `confirmacion_carga._norm_fecha`.
3. **Comprobante numérico vs. texto**: `Nro# Comprobante`/`Número de Comprobante` son columnas `float` en SQL Server (`999001.0`), mientras el preview de Excel trae el comprobante como texto (`"999001"`) — `str(999001.0) != "999001"`. Corregido con `confirmacion_carga._norm_comprobante`.
4. **Guard de solo-lectura contra el propio nombre de columna**: la columna `CantidadInsertados` (y el alias `AS insertados`) contienen la subcadena `INSERT`, que `_assert_read_only` (`connection.py`) rechaza en cualquier SELECT sin importar el contexto — cualquier consulta a `CargasResumenBancario` quedaba rota. Corregido renombrando la columna real a `CantidadCargados` (con una migración idempotente en `crear_tablas_carga_resumenes.py` para quien ya la haya creado con el nombre viejo) y aliasando `AS cargados` en el SQL, renombrando a `insertados` recién en Python.
5. **`IdMovimiento` ambiguo**: el `LEFT JOIN` a `CargasResumenBancario_Movimientos` (que también tiene una columna `IdMovimiento`) volvió ambiguas las referencias sin calificar a `IdMovimiento` de `Movimientos Galicia` en `ORDER BY`/`SELECT`. Corregido calificando `id_column` y la columna de `idMovimiento` en `repository.py` con el nombre de tabla.

Los 5 se cubrieron con tests de regresión (unitarios para 1-3, y quedan implícitamente cubiertos por los tests de endpoint para 4-5 al usar el código real de `repository.py`).

## Pendiente

- BNA no se verificó con un archivo `.xls` real contra `WC` (limitación de entorno, no del código) — mismo hueco que ya tenía 003. Si aparece un archivo `.xls` real de ejemplo, repetir el Escenario 1-3 con BNA.
- No se probó la concurrencia real (SC-005, dos confirmaciones simultáneas) — de baja prioridad real dado el volumen (una persona, cargas mensuales), documentado como límite conocido en `research.md` §4.
