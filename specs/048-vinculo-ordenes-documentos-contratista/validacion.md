# Validación 048: 06/11/2026

## Base de datos (WC)

- Backups verificados (`RESTORE VERIFYONLY`): `WC_vinculos-contratista-048_20261106_143250_889645.bak` (columnas y UNIQUE en `OrdenesContratistaFacturas`) y `WC_vinculos-contratista-048_20261106_145306_283372.bak` (`ImputacionPropuestas.Origen` de varchar(10) a varchar(20)).
- Script re-corrible: `backend/scripts/vinculos_contratista_048.py` + `.sql`.

## Hallazgos durante la implementación (heredados de 017, corregidos)

1. `ImputacionPropuestas.Origen` era varchar(10): "Contratista" no entraba, así que la imputación de contratistas nunca pudo guardarse.
2. `aprobar_corrida` comparaba el IdCorrida distinguiendo mayúsculas (uuid de Python en minúsculas vs uniqueidentifier de SQL en mayúsculas): una corrida recién creada nunca era "vigente".
3. `corrida_vigente` no filtraba por origen: el IdDetalleCompra de un insumo puede coincidir con el IdCompra de una factura de contratista (rangos superpuestos). Ahora filtra por origen.
4. `distribucion_de_orden` sumaba la superficie de cada lote una vez por cada insumo de la orden; ahora toma el máximo por lote.
5. `fijar_vinculos` ahora es todo o nada: si la imputación falla, los vínculos vuelven a como estaban.

## Recorrido de punta a punta (API sobre WC, luego revertido)

Factura 00002-00000735 de Pérez ($ 2.376.000,00) con la orden 162 (198 ha):

| Control | Resultado |
|---------|-----------|
| GET panel de órdenes | 0,06–0,17 s, 37 órdenes de Pérez |
| PUT con usuario de solo lectura | 403 |
| PUT vincular | 0,19 s, 200; reparto en 14 fracciones que suman $ 2.376.000,00 al centavo |
| Orden 162 | muestra la factura con su reparto |
| Resultado | los 5 cultivos de la campaña 2026/2027 suben en total $ 2.376.000,00 |
| Desvincular | 200; todos los cultivos vuelven exactamente al valor previo |

La factura estaba cargada a mano como "General / No Aplica" (fuera de los cultivos); al vincularla, el costo pasa a los cultivos de la orden. No es doble conteo: los renglones repartidos se excluyen de la carga manual (`costos_heredados` y `costo_sin_clasificar`).

## Control contra la foto previa (SC-003 / SC-004)

Foto previa y final (sin vínculos grabados) en el scratchpad: **0 saldos distintos en 527 cuentas** y **0 diferencias en 87 combinaciones de cultivo y campaña**.

## Tests

- `pytest -k "orden or imputacion or compras or contratista or resultado or costos"`: 285 pasan.
- Suite completa: 13 fallas y 18 errores **preexistentes** (peajes, auditoría, impuestos, remuneraciones, revisión de cuentas, vista tarjetas): fallan igual sin los cambios de la 048.
- Frontend: `tsc --noEmit` y `eslint` sobre los archivos tocados, sin errores.

## Pendiente

- Recorrido visual en el navegador (panel en Compras, aviso al guardar sin orden, sección de la orden, listado sin orden).
- NC/ND: ninguna de las 6 NC de contratistas está relacionada con su factura; el caso real se prueba cuando se relacione la primera (cubierto por tests).
- Tarea futura: borrar la tabla vacía `Ordenes_Trabajo_Contratista_Factura` (con backup).
