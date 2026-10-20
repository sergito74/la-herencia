# Hallazgo: liquidaciones finales del canje de soja 2022/2023

Revisión20/10/2026, posterior al alta de venta1230. Sin cambios SQL.

## Análisis conjunto ampliado por pedido de Sergio

La relación está explícita en el proveedor, no se deduce solo de kilos coincidentes: ambas iniciales del03/05/2023 se aplican bajo contrato AF0001-00210745 (CA78185 para30091kg y CA78182 para1801kg); las finales citan individualmente AF3302-23253060 y AF3302-23253039. El PDF de la inicial30091kg dice `Liq, Parcial 97,5%` y deduce `A cobrar en Final(RCC)`$75.227,50. Por tanto son dos ventas con una instancia parcial y otra final, no cuatro ventas físicas.

Con precio$100/kg, bases$3.009.100 y$180.100: el2,5% retenido da exactamente$75.227,50 y$4.502,50; el segundo desglose original sigue sin documento y se reconstruye por la relación expresa de su final. Iniciales netas$3.134.051,64+$187.546,31=$3.321.597,95; finales$79.730; total acreditado de las dos operaciones$3.401.327,95. Kilos únicos31892.

La deducción global1230$11.464,19 incluye aritméticamente un componente$4.502,50 que se recupera en la final; diferencia no recuperada$6.961,69, cuya composición fiscal sigue desconocida. Haber llamado comisión a toda la deducción fue una clasificación global autorizada para la etapa parcial; no debe interpretarse como prueba de comisión definitiva por ese importe. El tratamiento conjunto propuesto es reconocer las finales como recuperación de importes retenidos de las mismas operaciones, sin nuevos kilos y con trazabilidad, y evitar que permanezcan como gasto definitivo. No se modificó la clasificación autorizada ni se cargaron finales durante este análisis.

**Diferencia$2.828,14 localizada:** en09/01/2025 CA115924/CD115924 utiliza$8.140.515,34, frente al eCheq RI52670 de$8.137.687,20. Diferencia$2.828,14 aplicada del crédito previo$79.730. Luego de los movimientos de cambio de NC116557, el crédito queda$76.901,86. En22/05/2025 CA/CD123088 consume ese remanente: USD83,17 alTC958,50 equivalen$79.722,45, menos componente pesos$2.820,71 = $76.901,74 (diferencia$0,12 por redondeo del USD mostrado). La NC120722 cancela el componente pesos$2.820,71. No sumar este importe como nueva comisión ni confundirlo con$2.828,14 de enero. Reconstrucción a partir de filas del libro, pendiente cotejo de PDFsCA115924/123088; ya no hay diferencia monetaria$2.828,14 sin localizar.

El historial externo conserva dos créditos del04/09/2024 (vencimiento11/09/2024):

| Liquidación | Referencia del proveedor | Crédito pesos |
|---|---|---:|
| LC3302-26576206 | AF3302-23253060, soja2223,30091kg | 75.227,50 |
| LC3302-26576221 | AF3302-23253039, soja2223,1801kg | 4.502,50 |
| Total | | 79.730,00 |

En WC no existen ventas con ninguno de los dos números. Venta177 contiene deducción305 por$75.227,50, detalle histórico `Ajuste por diferencia de calculo`; su PDF original la identifica como **A cobrar en Final (RCC)**. El crédito posterior coincide exactamente con ese importe retenido. Además$75.227,50 equivale al2,5% de$3.009.100 y$4.502,50 al2,5% de$180.100. Esto sustenta que se trata de liquidaciones finales de importes pendientes de las mismas ventas, no de nuevas cantidades de soja; no equivale a contar con sus originales fiscales.

Venta1230 conserva, por decisión posterior explícita de Sergio, deducción global$11.464,19 clasificada como comisión. La nueva evidencia del crédito final$4.502,50 obliga a separar el reconocimiento de ese crédito del juicio sobre la composición de la deducción global. No se cambió la comisión ni se sumaron nuevamente1801kg. Para resultados de cultivo debe evitarse presentar un importe recuperable como gasto definitivo, pero también respetarse la clasificación autorizada mientras se decide el tratamiento completo.

CA123088 del22/05/2025 aplica remanente$76.901,86 y registraUSD83,17 junto a componente$2.820,71 mantenido en pesos. Diferencia respecto al crédito original$79.730: $2.828,14. Falta recuperar el CA para explicar esa utilización previa y la separación monetaria: no convertir simplemente$79.730 al TC958,50 ni equiparar crédito original y remanente. No afirmar que todo$79.730 sigue disponible al momento de la aplicación.

Fuentes: `backups/baya-conciliacion-20261019/portal-filas-links.json` (filas LC26576206/221 y CA123088); PDF original Ventas/04 2023 - 03 2024/20230503_BayaCasal.pdf; lectura actual de Venta Granos/Deducciones/Ajustes para177/1230. La búsqueda completa de Ventas de esta sesión no encontró los originales de las liquidaciones finales. Los enlaces externos de ambas LC están preservados en el inventario, pendientes de recuperación si el portal los entrega.
