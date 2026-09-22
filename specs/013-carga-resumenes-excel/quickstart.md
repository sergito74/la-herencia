# Quickstart: validar la carga de resúmenes bancarios (013)

## Prerrequisitos

- Backend y frontend corriendo igual que en 003/012.
- Un Excel real de BNA (`.xls`) o Galicia (`.xlsx`), o los fixtures usados en 003.
- Conexión de escritura a `WC` — este módulo SÍ escribe (a diferencia de 003), nunca contra `LaHerencia`.

## Escenario 1 — Confirmar una carga nueva

1. Ir a Tesorería → subir un Excel de BNA o Galicia.
2. Verificar la vista previa con el conteo "N nuevos / M omitidos por duplicado" (debería ser N=total, M=0 la primera vez).
3. Confirmar. Verificar que los movimientos aparecen en el listado de tesorería de ese banco (003 US1), con los mismos valores de la vista previa.

**Resultado esperado**: SC-001, FR-001, FR-004.

## Escenario 2 — Subir el mismo archivo dos veces

1. Repetir la carga del mismo archivo del Escenario 1.
2. Verificar que la vista previa muestra 0 nuevos / N omitidos por duplicado.
3. Confirmar de todas formas y verificar que no se insertó ningún movimiento nuevo (mismo total en el listado antes y después).

**Resultado esperado**: SC-002, FR-003, FR-005.

## Escenario 3 — Superposición parcial

1. Con datos reales o de prueba, armar (o encontrar) un archivo con algunas fechas ya cargadas y otras nuevas.
2. Verificar que la vista previa distingue correctamente cuáles son nuevos y cuáles se omiten.
3. Confirmar y verificar que el total insertado coincide con lo anunciado.

**Resultado esperado**: FR-003, FR-004.

## Escenario 4 — Trazabilidad

1. Sobre una carga confirmada, consultar `GET /api/tesoreria/{banco}/cargas` y verificar que aparece con nombre de archivo, fecha/hora e insertados/omitidos correctos.
2. Tomar un movimiento insertado por esta vía desde el listado de tesorería y verificar que trae `idCarga` no nulo, coincidente con la carga del paso 1.
3. Tomar un movimiento cargado antes de esta feature (histórico) y verificar que `idCarga` es `null`.

**Resultado esperado**: SC-004, FR-007, FR-008, FR-009.

## Escenario 5 — Archivo con filas incompletas

1. Usar (o simular) un archivo con alguna fila sin fecha o sin importe en el medio.
2. Verificar que esa fila no se inserta, se cuenta en `omitidosIncompletos`, y el resto del archivo se procesa normalmente (no se rechaza todo el archivo).

**Resultado esperado**: Edge Cases de spec.md.

## Escenario 6 — Contacto en blanco

1. Confirmar cualquier carga y verificar que los movimientos nuevos tienen `Contacto`/`IdContacto` vacíos en el listado de tesorería.
2. Verificar en 003 US2 (referencia de origen) que esos movimientos muestran "sin coincidencia", sin error.

**Resultado esperado**: FR-006, Clarifications Q1.

## Revertir después de probar

Los movimientos insertados durante esta verificación son reales en `WC`. Si se usó un archivo de prueba (no un resumen real que corresponda dejar cargado), borrar manualmente las filas insertadas de `Movimientos BNA`/`Movimientos Galicia` y sus filas en `CargasResumenBancario`/`CargasResumenBancario_Movimientos` por `IdCarga`, para no dejar datos de prueba mezclados con la operación real.
