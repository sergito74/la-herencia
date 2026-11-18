# Reglas de superficie para costos y resultados (todos los cultivos agrícolas)

Decididas el 18/11/2026 por Sergio, con el criterio de los especialistas en producción agrícola (05) y en dirección financiera y costos (07). Siguen la práctica habitual de la industria: margen bruto de CREA/AACREA, INTA, Márgenes Agropecuarios. Rigen para todos los cultivos y todas las campañas. Se implementan en `backend/src/features/resultado_cultivo/superficies.py`.

## Superficies que lleva el sistema

| Superficie | De dónde sale | Para qué se usa |
|---|---|---|
| **De los lotes** (bruta, "afectada") | Suma de los lotes del plan agrícola, sin los marcados "no sembrado" | Planificación, alquiler por ha bruta, aprovechamiento. **Nunca como denominador del cultivo.** |
| **Aplicada en cada orden** | Superficie de cada lote en la orden de trabajo | Dosis por ha, consumo de stock y pago al contratista. No cambia el denominador. |
| **Sembrada** | Facturas de siembra y siembra con maquinaria propia (reglas del 12/11: la mayor factura por contratista, sin resiembras ni ajustes). Si se cosechó más, manda la cosechada. | **Denominador del costo por ha y del margen bruto por ha.** Superficie que se asegura. |
| **Cosechada** | Cierre del cultivo | **Denominador del rinde (kg/ha)** y del costo de cosecha por ha |
| **Aprovechamiento** | Sembrada / de los lotes | Dato informativo: cuánto del lote no se siembra (cabeceras, bajos, caminos, alambrados) |

## Reglas

1. **El costo total del cultivo no depende de la superficie.** Los insumos entran por lo aplicado en las órdenes y las labores por factura. La superficie solo cambia el valor por hectárea.
2. **Costo por ha y margen bruto por ha = total / ha sembradas.**
3. **Rinde y costo de cosecha por ha = total / ha cosechadas.** Si se perdió parte de lo sembrado (granizo, anegamiento), la diferencia entre sembrada y cosechada se informa aparte.
4. **Lo aplicado sobre las ha no sembradas de un lote que sí se sembró es costo del cultivo.** Cabeceras, bajos y bordes no forman un rubro aparte: son una ineficiencia del lote y suben el costo por ha sembrada.
5. **Barbecho de un lote que terminó con otro cultivo:** va a ese otro cultivo.
6. **Barbecho de un lote que no se sembró** (marcado "no sembrado" en el plan): es costo hundido de la campaña. No tiene costo por ha y no entra en el margen bruto por ha de ningún cultivo, pero sí en el resultado de la campaña (decisión del 17/11/2026).
7. **Si todavía no hay siembra registrada**, se usa la superficie de los lotes y se marca "teórica". Pasa a la real cuando llega la factura de siembra.
8. **Seguro agrícola:** se asegura la superficie sembrada. La suma por ha se compara contra el costo de implantación por ha sembrada.
9. **Factura de siembra en un solo total:** si hace falta el dato por lote, se reparte en proporción a la superficie de cada lote en la orden de siembra.

## Ejemplos

| Cultivo | De los lotes | Sembrada | Aprovechamiento | Implantación | US$/ha antes | US$/ha ahora |
|---|---|---|---|---|---|---|
| Girasol 2025/26 | 116,4 ha | 104 ha | 89% | US$ 35.367 | 303,8 | **340** |
| Girasol 2026/27 (realizado al 18/11) | 78,3 ha | 70 ha | 89% | US$ 23.207 | 296,3 | **332** |
| Trigo 2025/26 (no sembrado) | 76,4 ha no sembradas | 0 | — | US$ 3.048 costo hundido | 40 | sin valor por ha |
