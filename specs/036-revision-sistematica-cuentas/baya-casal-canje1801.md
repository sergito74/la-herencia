# Canje 1801 kg — alta reconstruida autorizada

## Desglose vigente — instrucción posterior de Sergio

El20/10/2026 Sergio aprobó reemplazar la comisión global por la misma estructura proporcional de la liquidación mayor, con residual$32,27 como otros gastos de comercialización. Aplicado en venta1230, conservando cabecera y neto$187.546,31:

| Deducción | Base pesos | IVA |
|---|---:|---:|
| Comisión | 3.602,00 | 10,5% ($378,21) |
| Sellado de contrato | 1.801,00 | 0 |
| Ingresos brutos | 1.148,14 | 0 |
| A cobrar en Final (RCC) | 4.502,50 | 0 |
| Ajuste PE | 0,07 | 0 |
| Otros gastos de comercializacion | 32,27 | 0 |

Total descontado incluido IVA de comisión$11.464,19. Se reemplazó deducción1364 por seis filas, sin duplicar. Los$32,27 se verificaron en `vw_ResultadosCultivo_Deducciones` para IdCultivo3/Soja y campaña2022/2023, fuente que el resumen de resultado resta de ventas para formar venta neta. No se agregó un costo de producción paralelo: eso duplicaría su efecto en margen. La interfaz actual lo refleja en venta neta, no en un nuevo rubro de costos de producción. Comisión/IVA y restantes conceptos son reconstrucción autorizada, no lectura de un original inexistente.

La reservaRCC es recuperable; su final$4.502,50 está identificada pero aún no cargada. La vista heredada resta todas las deducciones, incluidas RCC e IIBB; el alta de las finales y el análisis de clasificación económica/impositiva siguen pendientes. No confundir retención/reserva con costo definitivo ni afirmar resultado integral del canje cerrado.

Respaldo verificado `WC_baya-canje1801-desglose-036_20261020_082951_166346.bak`; script `backend/scripts/baya_casal_canje1801_desglose_036.py`, auditoría local `canje1801-desglose-*.json`. Comprobados neto en cálculo y vista de cuenta, presencia del gasto en la fuente del resultado, cabecera1230 intacta y deducciones177 intactas, lectura posterior a commit. Este desglose sustituye la clasificación global de la sección siguiente.

## Clasificación vigente — decisión posterior de Sergio

El20/10/2026 Sergio indicó sustituir el detalle reconstruido por **comisiones**. Aplicado a deducción1364 de venta1230: IdConcepto1 (`Comision o Gastos Administrativos`), Detalle `Comision`, importe$11.464,19, porcentaje100 y alícuota0 conservados. El resultado de Soja2022/2023 la agrupa ahora con las demás líneas `Comision`; no se agrega otro gasto. Neto de liquidación$187.546,31 verificado sin cambio. La reconstrucción y ausencia de original permanecen como antecedente de auditoría, no como etiqueta de gasto. Esta decisión sustituye la clasificación inicial como otras deducciones descrita abajo.

Respaldo verificado `WC_baya-canje1801-comision-036_20261020_081507_816811.bak`; auditoría local `canje1801-comision-*.json` con antes/después y verificación de neto.

Sergio autorizó el 20/10/2026 cargar la liquidación sin su PDF original, que no está disponible ni puede obtener, tomando el precio de la liquidación de 30.091 kg. Alta aplicada en WC: **IdVenta1230**, COE330223253039, fecha03/05/2023, Bayá226, soja campaña2022/2023. Documento Original NULL: no se atribuye un PDF inexistente.

## Fuentes y reconstrucción

- CA0006-00078182 confirma 1801 kg, neto$187.546,31 y TC224,65; PDF en la carpeta documental de auditoría de Bayá del19/10/2026.
- Venta177/COE330223253060 y su PDF respaldan el precio de referencia $100.000/t ($100/kg). IVA10,5%, factor100 y flete0 se toman de esa referencia, no de un original de la nueva liquidación. Grados y depósito quedan NULL por no estar documentados para estos1801kg.
- Neto comercial reconstruido$180.100,00 + IVA$18.910,50 = bruto$199.010,50.
- Diferencia hasta el neto confirmado$11.464,19: una línea de **otras deducciones sin desglose**, con detalle visible `Reconstruido sin original; sin desglose`. Se conserva el importe agregado sin presumir comisión, retenciones ni crédito fiscal sobre esas deducciones; alícuota de la línea0. No es desglose fiscal comprobado.
- Resultado neto verificado por cálculo de Ventas y por vista de movimientos: **$187.546,31**. Venta177 intacta. No se creó cobro bancario, pago ni aplicación adicional.

## Valuación pendiente

TC224,65 viene del CA. La conversión genérica del neto completo da USD834,84; el proveedor separa $3.737,68 en pesos para ND90696 y reconoce USD818,20 sobre el resto. El alta completa el documento de venta; no resuelve por sí sola esa separación monetaria ni autoriza alterar el neto para forzar dólares. Revisar la aplicación/valuación en la etapa correspondiente.

## Respaldo y verificación

Respaldo verificado `WC_baya-canje1801-036_20261020_081055_777714.bak`. Script `backend/scripts/baya_casal_canje1801_036.py`, transacción de conciliación con bloqueo, guarda de COE para no duplicar, validación de neto en cálculo y vista y comparación de venta177 antes/después. Auditoría local `backups/baya-conciliacion-20261019/canje1801-alta-20261020_081056_704167.json` conserva datos, autorización y resultados.

Primer intento revertido íntegramente por longitud del detalle de deducción; acortado a37 caracteres y alta posterior confirmada con lectura independiente. No se ejecutaron pruebas que insertaran datos ficticios.
