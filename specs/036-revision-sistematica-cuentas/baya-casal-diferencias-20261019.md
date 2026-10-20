# Bayá Casal: diferencias entre el sistema y el proveedor

## Alta aplicada: FC0020-00251611

Por autorización expresa de Sergio se creó enWC la compra **2143523736**, FC0020-00251611 del15/06/2021:5litrosIMIDACLOPRID35%X5L,USD23,76/litro,IVA21%,TC95,50 y vencimiento11/04/2022. Totalvisible **USD143,75** (cálculo interno143,748 por precio original, sin ajuste artificial). PDFarchivadoyvinculado:`C:\Users\Sergio\Dropbox\Giamigli de Bolivar SA\Compras\04 2021 - 03 2022\20210615_BayaCasal_FC0020-00251611.pdf`.

Clasificación conservada de laNC78448 del mismo producto:centro1,destino6,rubro2047893469,campaña15/2021–2022; esaNC no se modificó ni se volvió a cargar. No se imputó un pago ni se ejecutóFIFO/cierre; el alta documental no significa deuda vencida nueva, según confirmación de Sergio.

Respaldoverificado:`C:\Program Files\Microsoft SQL Server\MSSQL17.SQLEXPRESS\MSSQL\Backup\WC_baya-fc251611-036_20261019_232023_299245.bak`. Auditoría:`backups/baya-conciliacion-20261019/fc251611-alta-20261019_232024_196245.json`. Script:`backend/scripts/baya_casal_factura_251611_036.py`. Verificadospersistencia,total,datosoriginales,ausenciadeduplicados,NCintactayvariacióndeudaporimporteexacto. Loshallazgosanterioresquedanhistóricosrespectoaestafactura.


## Corrección aplicada por autorización de Sergio

FC0020-00316792/IdDeuda2143513785 corregida enWC el19/10/2026: precios de los13productos restituidos alPDF en73repartos, sin cambios en cantidades, lotes, destinos ni campañas. TC128,25→230 y vencimiento30/05/2023 según comprobante. Total confirmado por relectura independiente: **USD29.613,30** frenteUSD30.994,8302 anterior; reducciónUSD1.381,5302.

Se agregó una línea financiera explícita `Redondeo IVA segun comprobante FC 0020-00316792`, IVA0 y cantidad1, porUSD0.0097, aproximadamente1centavo, para reproducir el total fiscal sin alterar precios originales de cuatro decimales. El detalle de productos sigue intacto. Respaldo verificado:`C:\Program Files\Microsoft SQL Server\MSSQL17.SQLEXPRESS\MSSQL\Backup\WC_baya-fc316792-036_20261019_230129_907858.bak`. Auditoría antes/después:`backups/baya-conciliacion-20261019/fc316792-correccion-20261019_230129_907369.json`. Script:`backend/scripts/baya_casal_factura_316792_036.py`. Las dos primeras ejecuciones fallidas se revirtieron transaccionalmente; la ejecución final y su persistencia fueron verificadas. No se corrigieron otras facturas, pagos ni cierres.

Las tablas del diagnóstico siguiente son la foto **anterior** a esta corrección; no representan el saldo actualizado. Sergio informó además que corrigió por su cuenta una línea a la que le faltaba precio (la identificó como trigo); no asumir que eso equivale a verificar otra factura sin relectura.


Contacto 226, cuenta externa 13338. Corte 30/09/2026; evidencia consultada 19/10/2026. Diagnóstico solicitado por Sergio: **sin escrituras en WC, ajustes, FIFO ni cierre**. Complementa [el relevamiento](baya-casal-relevamiento-20261019.md), que contiene pedidos, imágenes, precios e instrucciones de Sergio.

## Dato de negocio confirmado posteriormente por Sergio

Sergio confirma: «los documentos vencidos están todos cancelados. No se le debe nada a Baya Casal». Se toma como confirmado **sin deuda vencida**. Las diferencias históricas del sistema son problemas de representación, documentos, pagos, imputación o valuación a reconstruir; no tratarlas como obligaciones vencidas pendientes de pago ni proponer nuevos pagos para cancelarlas.

Distinguir ese dato de los compromisos futuros: el portal muestra FC465204 con vencimiento30/06/2027 y Sergio confirmó previamente que los PENDIENTE son compras firmes exigibles aunque no facturadas. No se ha confirmado que esas compras futuras estén pagadas o anuladas. Conservarlas separadas, sin eliminarlas ni forzar todo el saldo a cero. La cifra2.055,85 corresponde a saldo facturado a vencer; el escenario integral41.982,04 incluye compromisos futuros, no deuda vencida. Verificar fechas de vencimiento de los pedidos y reconstruir cancelaciones históricas contra el hecho confirmado por Sergio.

La declaración no identifica todavía el emisor del cheque8092 ni la documentación faltante y no autoriza inventar su origen. No se modificóSQL ni se registró un ajuste de apertura/cierre.

## Método y alcance

Se contrastaron 169 movimientos del sistema,107 cabeceras de Compras, líneas por producto y 239 filas útiles del portal, además de originales, recibos y correo. Las 107 cabeceras producen 106 movimientos de Compras: una cabecera adicional de 2018 repite número 168812 y no tiene efecto en la vista. No se la contó como una segunda deuda.

Se normalizaron números y se verificó contexto/tipo; SD son saldos migrados, no nuevas facturas. Se sumaron efectosUSD sin duplicar filas de aplicación, pesos, IVA o reprogramaciones. La matriz de pagos asigna cada movimiento posterior a 2020 una sola vez. Para los importes del sistema se reprodujeron las reglas vigentes a cuatro decimales: BNA, fecha de entrega, TC de granos y marcas de ajuste. No hay valuaciones específicas del contacto.

**Convención: deuda positiva; crédito a favor negativo**, al revés del signo de la aplicación. Gobiernan dólares por instrucción de Sergio. Los PENDIENTE son compras firmes exigibles; las cantidades redondeadas por envases están justificadas.

## 1. Qué se está comparando

- Sistema: deudaUSD 6.776,89, incluyendo PENDIENTE porUSD 21.392,26.
- Sistema sin esos pedidos: **créditoUSD 14.615,37**.
- Proveedor, parte facturada: **deudaUSD 2.055,85**. Factura 465204 porUSD 2.143,26 menos créditoUSD 87,41; vence 30/06/2027.
- Diferencia comparable de lo facturado: **USD 16.671,22**. La diferencia anteriorUSD 4.721,04 mezclaba alcances.

El puente que se adjunta al final descompone íntegramente esa diferencia. No es una autorización para ajustar importes globales: parte está explicada documentalmente y parte solo localizada.

## 2. Errores de facturas con originales confirmados

### Urea FC 0020-00320049

IdDeuda 2143514033. SistemaUSD 12.856,80798; originalUSD 19.375,91. **Falta deudaUSD 6.519,10202**.

El original factura 28.200 kg aUSD 0,6218 conIVA 10,5%. La línea 2141378458 tiene **9.488 kg con precioNULL e IVANULL**. Valuada al precio/IVA del original agregaUSD 6.519,10043: explica prácticamente toda la diferencia, con milésimas por distribución de cantidades.

Propuesta: completar precio e IVA de esa línea, conservando lote/destino/campaña y cantidades; verificar total final contra original. No agregar otra compra ni más kilos.

### Agroquímicos FC 0020-00316792

IdDeuda 2143513785. SistemaUSD 30.994,83020; originalUSD 29.613,30. **Sobra deudaUSD 1.381,53020**.

Las cantidades agregadas coinciden con los 13 renglones del PDF. Cambian precios:1.000 L de glifosato a 12,24919298 enSQL frente 11,6952 enoriginal;180 L de 2,4-D a 7,34951579 frente 7,0171;40 L deFierce a 99,06142222 frente 94,6248. Tuken 5 kg existe en el original: no quitarlo. TC 128,25 en cabecera frente 230 del original es otra diferencia que afecta pesos; no sumarla otra vez al ajusteUSD.

Propuesta: corregir precios por producto en los repartos existentes, verificando si se habían incorporado costos internos que deban conservarse en un concepto separado. Mantener cantidades e imputaciones; no usar un ajuste global para bajar la factura.

### Otras diferencias menores y de fecha

El anexo enumera todos los documentos compartidos con diferencias mayores a 1,5 centavos. DestacanFC 389331 (+USD 1,05),389893 (+USD 5,48),423769 (+USD 0,94),348391 (-USD 0,24) y otras de centavos. Se incluyen en el puente aun sin proponer su aplicación todavía.

FC 357848/357849/357850 figuran fechadas 2023 enSQL frente 12/03/2024 enportal; también difieren algunosTC respecto de 848. Verificar originales y distinguir recepción de fecha fiscal. No declarar faltantes por año distinto ni corregir dólares dos veces por unTC incorrecto.

## 3. Comprobantes ausentes de Compras

Originales descargados y contrastados por número entre las 107 cabeceras:

| Documento | Fecha | Total original | Efecto en libroUSD |
|---|---|---:|---:|
| FC 0020-00251611 |15/06/2021|USD 143,75|+143,75|
| ND 0020-00096827 |28/08/2023|USD 654,46|+654,46|
| ND 0020-00090696 |03/05/2023|$21.536,15|0|
| NC 0020-00100961 |03/05/2023|$90.764,56|0|
| ND 0020-00095459 |02/08/2023|$35.055,77|0|
| ND 0020-00095460 |02/08/2023|$48.408,77|0|
| ND 0020-00096887 |29/08/2023|$4.385.355,23|0|

Los dosUSD suman 798,21. LaFC 251611 es contraparte deNC 78448 ya existente. LaND 96827 es financiaciónNERA 2%, no diferencia de cambio. Los otros cinco son diferencias de cambio en pesos: importan fiscalmente y para el saldo en pesos, pero no generanUSD nuevos según el libro del proveedor. Cargar cada documento con su función, sin dolarizar automáticamente todo.

## 4. Duplicación de pagoAgroNación y límite histórico

El historial externo comienza con saldos migrados 2020/2021 y no muestra toda la historia 2015–2020. Al 01/01/2021 el sistema presenta créditoUSD 7.262,46580 frente deuda externa migrada emitida en 2020 USD 5.146,31: **diferenciaUSD 12.408,77580**.

Dentro de ese bloque hay duplicación de **$471.336,79 del 25/06/2020**:

- Pagos efectivo 1909, contacto 226, forma de pago 18. El catálogo identifica 18 como **AgroNacion**.
- Tarjetas, IdOrigen 5577, corresponde al **IdVinculo**, no alIdLineaConsumo. Vincula línea 5917, resumen 651/código 9132958, aFC 215282/IdDeuda 2143512802 por el mismo importe.
- PDFlocal 20200625_Bayacasal.pdf imprime pago conAgroNación a 360 días,USD 6.502,78 yTC 73. No hay evidencia de dos pagos independientes; el registro efectivo es la representación histórica del mismo medio.

Retirar el efecto duplicado de efectivo 1909 aumentaría deudaUSD 6.723,7766 a la valuación vigente. Propuesta: conservar tarjeta respaldada y resolver el registro histórico con auditoría/reversión y respaldo; no borrar la compra, tarjeta ni un pago bancario real.

**Resto histórico tras esa duplicación:USD 5.684,9992 todavía sin causa reconstruida.** Localiza dónde seguir, no autoriza un ajuste de apertura. También falta valuar el pago real y retención alTC efectivamente reconocido: BNA del sistema no coincide conTC 73 del original.

Revisar especialmente canjes 2017 y hacienda 2018 contra saldo migrado. Mantener la percepciónIVA 2017 comprobada: no volver a la hipótesis descartada de eliminarla.

La cabecera 2143511963 repiteFC 168812 de 2018, pero no aporta movimiento a la vista; la cabecera 2143511945 sí muestraUSD 6.074,89. Es una inconsistencia de registro a revisar, no un segundo pago/factura que pueda descontarse del saldo.

## 5. Pagos, canjes y retenciones que faltan o requieren más información

### Cheque 8092

$5.797.560,71, endoso 09/06/2026 yRI 77444 confirmados. CA 145717 reconoce **USD 3.931,99**, con componentes adicionales en pesos. No usar la división simple por 1446,50 como créditoUSD de la cuenta. No se encontró registrado. Falta identificar de quién se recibió y su relación de origen antes de incorporarlo sin afectar otra cuenta.

### Canje 1801 kg

LC 330223253039 por$187.546,31, CA 78182: **USD 818,20**. No hay Venta Granos con eseCOE enWC. Es distinto del canje 30091 kg/COE 330223253060 ya cargado. Obtener liquidación y antecedentes de entrega/ajuste antes de agregarlo; no repetir la venta de 30091 kg.

La venta 177 existente está valuada alTC 224,25; el proveedor aplicaTC 224,65 yUSD 14.020,94 contraUSD 13.975,70 del sistema. Diferencia aproximadaUSD 45,24 de valuación, además del canje faltante.

### Ajustes de canjes 2024

LC 26576206/221 del 04/09/2024 acreditan$79.730 en el libro en pesos. CA 123088 del 22/05/2025 convierte el remanente$76.901,86 en **USD 83,17**,TC 958,50. Recuperar liquidaciones y aplicación antes de crear un crédito global conTCactual; el total original no es igual al saldo remanente aplicado.

### Retenciones no identificadas externamente

- Id 54, certificado 2022-15,$32.773,29,USD 262,79 en sistema.
- Id 183, certificado 2024-40,$132.097,95,USD 128,88 en sistema.

No se identificaron sus créditos en el historial visible. Buscar certificados, entrega y reconocimiento; **no anularlos porque no se vean**. Además, importe$7.787,68 está conciliado, pero número 49 enSQL frenteRG 50 del proveedor: verificar identificación, sin duplicarlo.

### Factura 235074 y su pago

FCUSD 393,25 másBNA 16332 por$36.768,88 yretención 7 por$3.919,97 no aparecen en el historial visible. Juntos dejan créditoUSD 64,78 a la valuación vigente. Puede ser diferencia de migración/valuación; revisar como conjunto antes de acusar ausencia o corregir uno solo de los movimientos.

### NERA 2023

RI 33178 dice tarjetaGalicia/NERA,$9.880.147,75. SQLGalicia 1375 muestra$9.880.148,00 y créditoUSD 28.233,03; proveedorUSD 26.786,96. La diferenciaUSD 1.446,07 corresponde aproximadamente a$506.051,12 que el proveedor conserva en pesos.

Validar siGalicia 1375 representa desembolso al proveedor o pago del préstamo antes de agregar un registro de tarjeta que duplique la acreditación. La diferencia documental$0,25 no explicaUSD 1.446 de saldo; son problemas distintos.

## 6. Valuación: conservar bancos y certificados reales

Retención 99 por$157.357,15 incluye componente que el portal mantiene en pesos$96.598,84: portalUSD 245,89 frente sistemaUSD 636,82. Retención 153 por$139.879,45 incluye componente en pesos$136.812,57: portalUSD 3,36 frente sistemaUSD 153,46. No implica reducir los certificados: verificar originales y separar aplicación/valuación.

Pagojunio 2026 ya registrado: proveedorUSD 28.611,17 en tresCA,TC 1441 y 1432,50; sistemaUSD 28.603,5316. DiferenciaUSD 7,6384. UnTCúnico no reproduce esa aplicación.

SeisNC en pesos sin marca de ajuste:120722,126312,134760,134761,135583,136689. TambiénND 134645. Llevar sus efectosUSD a 0, como el proveedor, aumenta deuda netaUSD 124,9316. Eso no elimina las notas ni sus importes en pesos.

Las facturas de fletes 437731/438310 y su pagoRI 70854 son exclusivamente en pesos. Revisar el conjunto: quitar solo las facturas del cálculoUSD dejaría un crédito artificial. La clasificaciónMixta de la interfaz y el cálculo genérico no sustituyen la regla de dólares que gobiernan esta cuenta.

## 7. Compras firmes sin facturar

Las tres existentes sumanUSD 21.392,26; diferencia preliminar+USD 3,61 por precios de dos decimales frente cuatro. No hay faltantes de cantidad por envases.

| Compra nueva | NetoUSD | Con 21%IVA, escenario |
|---|---:|---:|
| Agosto 57776/remito 70227 |820,04|992,25|
| Maíz 58758/remito 71919 |1.280,00|1.548,80|
| Agroquímicos 59027/remito 71918 |6.585,79|7.968,81|
| Soja 59111 |6.628,48|8.020,46|
| Totalnuevo |15.314,31|18.530,32|

No aparecen en líneasSQL bajo otras referencias. Son pedidos anteriores al 30/09, aun con entregas enoctubre. Soja tiene total/IVA explícitos; imagen original 59027 acredita 21%, pero el netoportal posterior sube de 6.238,50 a 6.585,79: reconstruir financiación sin sumarla dos veces. Faltan pies fiscales específicos deagosto/maíz para confirmar sus totales.

Pendientes totalesUSD 39.926,19 más facturadoUSD 2.055,85 dan **USD 41.982,04 como escenario**, no saldo externo definitivo ni importe a cargar sin los respaldos pendientes. Pedidos, remitos y facturas posteriores deben vincularse para no duplicar compras.

## 8. Orden de resolución

1. Corregir documentos respaldados: urea sin precio/IVA, preciosFC 316792, faltantes y notas de cambio; conservar repartos y traza antes/después, con respaldo previo a escrituras.
2. Resolver duplicaciónAgroNación 2020 y valuación del pago real. Reconstruir el resto históricoUSD 5.685 aproximadamente; no ajustar apertura para forzar coincidencia.
3. Completar compras firmes con precio exacto, IVA, vencimiento y origen, sin duplicar al facturar.
4. Recuperar fuente de cheque 8092, liquidación 1801 kg, ajustes de canjes 2024 y certificados 54/183. Buscar archivos/correo antes de consultar a Sergio lo que siga faltando.
5. Valuar pagos según aplicaciones reales del proveedor usando el mecanismo existente; conservar importes nominales de bancos y retenciones. Separar peso/IVA/financiación.
6. Recalcular al mismo corte y verificar documentos y monedas. Solo entonces FIFO y evaluación de cierre; una deuda no vencida legítima no se lleva a cero.

## Evidencia

Originales adicionales:FC 316792,FC 320049,RI 33178,CA 144661,CA 78182,CA 78185. Carpeta `C:/Users/Sergio/Documents/La Herencia/Administracion y gestion/Auditoria cuentas corrientes/Baya Casal/20261019/`. Factura 2020 enDropbox/Compras/04 2020-03 2021/20200625_Bayacasal.pdf. No se guardaron credenciales.

Extracciones fuera deGit en `backups/baya-conciliacion-20261019/`:sql-usd-preciso.json,puente-facturado.json,pagos-comparados.json,sql-lineas 2 facturas.json,sql-tarjeta 5577.json,sql-efectivo.json y textos dePDF. Las matrices siguientes se obtienen de esos datos. La comprobación numérica verifica el diagnóstico, no saldos modificados: no hubo cambios enSQL ni pruebas con escrituras.


## AnexoA. Puente verificado de lo facturado

| Categoría | Variación de deudaUSD |
|---|---:|
| Saldo sistema sinPENDIENTE/PED | -14.615,37 |
| Historia anterior a 2021 frente apertura externa | 12.408,78 |
| ImportesUSD de documentos compartidos | 5.144,91 |
| ConversiónUSD de documentos en pesos | -636,03 |
| FC 235074 solo visible enSQL | -393,25 |
| Dos documentosUSD faltantes | 798,21 |
| Pagos/canjes/aplicaciones desde 2021 | -651,40 |
| Saldo facturado proveedor | 2.055,85 |

Comprobación con valores sin redondear: error menor 0,001 USD; no hay fila residual creada para cerrar. Cada categoría contiene pendientes de interpretación indicados arriba.

## AnexoB. Matriz completa de pagos desde 2021

Variación positiva aumenta deuda respecto al sistema; negativa disminuye. Crédito externo 0 significa no identificado o exclusivamente en pesos, no autorización de anulación. Los CA/CD se consideran por efecto neto.

| Grupo | FuentesSQL | CréditoSQL USD | Crédito externoUSD | Variación deudaUSD | Evidencia/límite |
|---|---|---:|---:|---:|---|
| Pago de FC 235074 sin correlato visible | Banco Nacion 16332, Retenciones 7 | 458,02 | 0,00 | 458,02 | Factura 393,25 tampoco visible; revisar como conjunto, no borrar el pago |
| Transferencia abril 2021 | Banco Nacion 16333 | 1.399,97 | 1.324,04 | 75,93 | RI 888; diferencia de cambio en pesos |
| Anticipo 504278,14 | Banco Nacion 16334 | 5.389,89 | 5.282,55 | 107,34 | RI 3114, CA 7479/7480/53679; dolarizaciones repartidas |
| Pago mayo 2021 | Galicia 5, Retenciones 9 | 7.992,84 | 8.094,74 | -101,90 | RI 2709 + RG 5 y efecto neto CA/CD 4114 |
| Cheque FC 250733 | Galicia 423 | 2.435,91 | 2.438,00 | -2,09 | RI 3225 + efecto neto CA/CD 7430 |
| Cheque y retencion FC 250734 | Galicia 466, Retenciones 13 | 31.251,46 | 31.282,53 | -31,07 | RI 3209 + RG 9 + efecto neto CA/CD 5213 |
| FC 261752 | Galicia 219 | 500,19 | 499,13 | 1,06 | RI 7384 |
| FC 263993 | Galicia 260 | 668,66 | 667,92 | 0,74 | RI 9194 |
| Agronacion 2022 | Tarjetas 5583, Retenciones 49 | 4.672,32 | 4.659,47 | 12,85 | RI 16209 + RG 10; 270,25 pesos luego ajustados |
| Tarjeta FC 292987 | Tarjetas 654 | 17.786,90 | 17.877,10 | -90,20 | RI 17648 |
| Retencion 2022-15 | Retenciones 54 | 262,80 | 0,00 | 262,80 | No encontrada en libro visible; verificar certificado y aplicacion antes de excluir |
| FC 294558 | Galicia 719 | 787,66 | 820,81 | -33,15 | RI 19407 822,80 + efecto neto CA/CD 59135: reduce credito 1,99 |
| FC 314873 | Galicia 988 | 1.228,04 | 1.222,10 | 5,94 | RI 24763 |
| Canje 30091 kg | Venta Granos 177 | 13.975,70 | 14.020,94 | -45,24 | CA 78185, TC 224,65; sistemaTC 224,25 |
| Transferencia junio 2023 | Galicia 1262 | 26.654,38 | 26.654,38 | 0,00 | RI 30422 |
| Retencion 2023-25 | Retenciones 99 | 636,82 | 245,89 | 390,93 | RG 25 distingue porcionUSD y porcionpesos 96598,84 |
| Transferencia y retencion junio 22 | Galicia 1268, Retenciones 100 | 2.210,02 | 2.185,86 | 24,16 | CA 85473; incluye cuota en pesos de ND |
| Transferencia julio 2023 | Galicia 1324 | 1.221,92 | 1.191,15 | 30,77 | CA 85478 |
| Retencion 2023-33 | Retenciones 106 | 3,85 | 3,86 | -0,01 | RG 33 acreditada enero 2024 |
| Retencion 2023-36 | Retenciones 109 | 272,23 | 322,94 | -50,71 | RG 36 acreditada enero 2024 |
| NERA 2023 | Galicia 1375 | 28.233,03 | 26.786,96 | 1.446,07 | RI 33178:9.880.147,75, importeSQL 9.880.148,00; parte 506051,12 pesos |
| FC 348391 | Galicia 1621, Retenciones 122 | 919,86 | 919,86 | 0,00 | CA 95307 enero 2024; numero RG 50 proveedor frente 49 sistema |
| Transferencia enero 2024 | Galicia 1673 | 663,39 | 624,41 | 38,98 | RI 37873 624,11 + efecto neto CA/CD 1008790,30 |
| Transferencia junio 2024 | Galicia 1968 | 10.256,30 | 10.256,30 | -0,00 | RI 44686 |
| Retencion 2024-22 | Retenciones 153 | 153,46 | 3,36 | 150,10 | RG 22 distingue porcionUSD y porcionpesos 136812,57 |
| Retenciones julio 2024 | Retenciones 163, Retenciones 164 | 87,87 | 87,87 | 0,00 | RG 27 y RG 28 |
| Retencion 2024-40 | Retenciones 183 | 128,88 | 0,00 | 128,88 | 132097,95 no identificados en libro visible: comprobar certificado antes de excluir |
| Cheque 80553793 | Pagos Valores Recibidos 18 | 7.904,50 | 7.913,67 | -9,17 | RI 52670 y CA 115924 |
| Dos cheques debitados junio 2025 | Galicia 2580, Galicia 2581 | 5.809,62 | 5.809,62 | -0,00 | RI 46164 agosto 2024; diferencias de fecha, no nuevos pagos |
| Transferencia y retencion julio 2025 | Galicia 2682, Retenciones 204 | 17.036,97 | 16.656,29 | 380,68 | RI 61767: porcionespesos separadas de dolares |
| FC 432399 | Galicia 2979, Retenciones 221 | 882,95 | 885,89 | -2,94 | RI 69101 + RG 39 |
| Pago fletes en pesos 2026 | Galicia 3034, Retenciones 222 | 770,25 | 0,00 | 770,25 | RI 70854/RG 1: pago exclusivo pesos, compensar junto a FC 437731/438310 |
| Cheques y retencion abril 2026 | Galicia 3251, Retenciones 234 | 11.951,09 | 11.680,98 | 270,11 | CA 144661; TC 1410 y fechaaplicacion 29/05 |
| Transferencia y retencion junio 2026 | Galicia 3274, Retenciones 240 | 28.603,53 | 28.611,17 | -7,64 | CA 145870+145871+146076; TC 1441 y 1432,50 |
| Cheque 8092 faltante |  | 0,00 | 3.931,99 | -3.931,99 | RI 77444 + CA 145717; pago 5797560,71, origenemisor pendiente |
| Canje 1801 kg faltante |  | 0,00 | 818,20 | -818,20 | LC 330223253039 + CA 78182;187546,31, no existe Venta Granos por eseCOE |
| Dolarizacion saldo pesos de canjes |  | 0,00 | 83,17 | -83,17 | LC 26576206/221 suman 79730 pesos; CA 123088 aplica 76901,86, TC 958,50 |
| Ajuste proveedor diciembre 2021 |  | 0,00 | -0,50 | 0,50 | CD 26292 +2,62 y CA 26293 -2,12: deuda neta 0,50 |
| Ajuste proveedor enero 2024 |  | 0,00 | 0,03 | -0,03 | RI 37633:3 centavosUSD |

Cobertura: 47 movimientosSQL, todos asignados una sola vez; 39 grupos incluyendo fuentes externas sinSQL. Variación total:USD-651,40.

## AnexoC. Todos los documentos compartidos con diferencias mayores a 0,015 USD

| IdDeuda | Documento | DeudaSQL USD | Deuda externaUSD | DiferenciaUSD |
|---|---|---:|---:|---:|
| 2143513083 | 0020-00237394 | 5.901,20 | 5.901,17 | -0,03 |
| 2143513785 | 0020-00316792 | 30.994,83 | 29.613,30 | -1.381,53 |
| 2143513786 | 0020-00316797 | 12.288,93 | 12.288,96 | 0,03 |
| 2143514033 | 0020- 00320049 | 12.856,81 | 19.375,91 | 6.519,10 |
| 2143514336 | 0020-00357850 | 7.296,30 | 7.296,35 | 0,05 |
| 2143514337 | 0020-00357849 | 2.167,90 | 2.167,88 | -0,02 |
| 2143514192 | 0020-00348391 | 920,10 | 919,86 | -0,24 |
| 2143514757 | 0020-00389331 | 1.270,51 | 1.271,56 | 1,05 |
| 2143514758 | 0020-00389893 | 6.636,63 | 6.642,11 | 5,48 |
| 2143515167 | 0020-00120722 | -14,18 | 0,00 | 14,18 |
| 2143515205 | 0020-00423769 | 348,07 | 349,02 | 0,94 |
| 2143515337 | 0020-00126312 | -16,92 | 0,00 | 16,92 |
| 2143515345 | 0020-00437731 | 232,94 | 0,00 | -232,94 |
| 2143515343 | 0020-00438310 | 528,02 | 0,00 | -528,02 |
| 2143515204 | 0020-00451189 | 6.861,42 | 6.861,45 | 0,03 |
| 2143515281 | 0020-00451191 | 4.389,30 | 4.389,28 | -0,02 |
| 2143517449 | 0020-00134760 | -197,36 | 0,00 | 197,36 |
| 2143517451 | 0020-00134761 | -28,55 | 0,00 | 28,55 |
| 2143517463 | 0020-00134645 | 249,83 | 0,00 | -249,83 |
| 2143517488 | 0020-00135583 | -94,95 | 0,00 | 94,95 |
| 2143519526 | 0020- 00136689 | -22,80 | 0,00 | 22,80 |

78 movimientos de Compras tienen número compartido con el historial externo; otros 28 no. Estos últimos se listan sin asumir que sean errores: el portal no reproduce toda la historia y no incluye compras no facturadas.

| FechaSQL | IdDeuda | Número | DeudaSQL USD | Contexto |
|---|---|---|---:|---|
| 2015-11-17 | 2143510494 | 0020-00106994 | 3.647,75 | Historia anterior a migración |
| 2017-02-08 | 2143511280 | 0020-00134770 | 10.883,03 | Historia anterior a migración |
| 2017-02-08 | 2143511281 | 0020-00134771 | 425,84 | Historia anterior a migración |
| 2017-07-17 | 2143511282 | 0020-00036312 | 0,00 | Historia anterior a migración |
| 2017-07-17 | 2143511283 | 01-16557491 | 1.856,69 | Historia anterior a migración |
| 2017-08-07 | 2143511618 | 0020-00026407 | 474,63 | Historia anterior a migración |
| 2017-08-07 | 2143511619 | 0020-00026404 | 1.421,54 | Historia anterior a migración |
| 2018-03-13 | 2143511441 | 0020-00157346 | 2.616,48 | Historia anterior a migración |
| 2018-10-08 | 2143511945 | 0020-00168812 | 6.074,89 | Historia anterior a migración |
| 2019-04-03 | 2143512024 | 0020-00183135 | 1.216,05 | Historia anterior a migración |
| 2019-04-03 | 2143512119 | 0020-00183136 | 1.239,04 | Historia anterior a migración |
| 2019-04-09 | 2143512408 | 0020-00196397 | 2.890,09 | Historia anterior a migración |
| 2019-05-30 | 2143512293 | 0020-00042511 | 0,00 | Historia anterior a migración |
| 2019-05-30 | 2143512294 | 0020-00042513 | 0,00 | Historia anterior a migración |
| 2019-05-30 | 2143512295 | 0020-00051162 | 0,00 | Historia anterior a migración |
| 2019-12-27 | 2143512808 | 0020-00057707 | 0,00 | Historia anterior a migración |
| 2020-02-10 | 2143512407 | 0020-00202518 | 6.504,92 | Historia anterior a migración |
| 2020-02-10 | 2143512587 | 0020-00202519 | 3.285,25 | Historia anterior a migración |
| 2020-02-10 | 2143512588 | 0020-00202520 | 490,05 | Historia anterior a migración |
| 2020-04-03 | 2143512809 | 0020-00051128 | 0,00 | Historia anterior a migración |
| 2020-06-02 | 2143512810 | 0020-00053029 | 0,00 | Historia anterior a migración |
| 2020-06-25 | 2143512802 | 0020-00215282 | 6.502,78 | Historia anterior a migración |
| 2021-02-11 | 2143513044 | 0020-00235074 | 393,25 | FC 235074: revisar junto a pago yretención |
| 2025-07-07 | 2143515122 | PED. 43194 | 9.764,22 | Pedido yNC compensados entre sí |
| 2025-07-07 | 2143517432 | PENDIENTE | -9.764,22 | Pedido yNC compensados entre sí |
| 2026-06-19 | 2143517489 | PENDIENTE 56078 | 9.129,45 | Compra firme no facturada |
| 2026-06-22 | 2143517490 | PENDIENTE 68485 | 2.758,80 | Compra firme no facturada |
| 2026-06-22 | 2143517491 | PENDIENTE 68476 | 9.504,01 | Compra firme no facturada |


## Relación documental verificada de NC78448

El PDF original indica origen FC0020-00250734 y presentación imidacloprid35%X1L; FC251611 refactura5litros como presentaciónX5L. Se vinculó NC2143513255 con la factura original2143513220 y con la nueva2143523736 como referencia de la operación conjuntaCA7428. La asociación con la nueva no afirma que sea su factura fiscal de origen ni que la cancele. No se agregóAplicacionesPago ni se modificaron saldos/importes. Antes/después en `backups/baya-conciliacion-20261019/nc78448-relaciones-20261019_232314_139674.json`; respaldo verificado `C:\Program Files\Microsoft SQL Server\MSSQL17.SQLEXPRESS\MSSQL\Backup\WC_baya-relacion-nc78448-036_20261019_232313_101541.bak`. La descarga delPDFCAantiguo no devolvió PDF utilizable; la evidencia de aplicación es la fila de portal ya archivada y la referencia de la nota se comprobó en PDF local.

## ND96827 registrada con autorización de Sergio

Compra **2143523738**, ND0020-00096827 del28/08/2023, financiaciónNERA2%: netoUSD540,88,IVA21%,totalvisibleUSD654,46 (cálculo interno654,4648),TC349,95,vencimiento29/08/2023. RubroFinanciamiento2047893443,centro3,destino1,campañaNoAplica20,línea marcada ajuste financiero; no marcada como diferencia de cambio. PDF archivado y vinculado:`C:\Users\Sergio\Dropbox\Giamigli de Bolivar SA\Compras\04 2023 - 03 2024\20230828_BayaCasal_ND0020-00096827.pdf`.

Relacionada documentalmente conFC320048/320049/336203 segúnRI33178. No se registró otro pago, no se modificaronGalicia1375 ni facturas relacionadas, no se ejecutóFIFO/cierre. Datos,total,persistencia,relacionesyvariacióndesaldoverificados. La primera tentativa se revirtió por longitud de descripción; la alta final abrevia la descripción sin perder el detalle delPDF. Respaldoverificado:`C:\Program Files\Microsoft SQL Server\MSSQL17.SQLEXPRESS\MSSQL\Backup\WC_baya-nd96827-036_20261019_232859_984035.bak`. Auditoría:`backups/baya-conciliacion-20261019/nd96827-alta-20261019_232900_895312.json`. Script:`backend/scripts/baya_casal_nd_96827_036.py`. Hallazgos anteriores de documento faltante quedan históricos.


## Financiación distribuida

ND96827 ya no tiene clasificación genérica: ver [distribución aplicada por producto,cultivo ycampaña](baya-casal-nd96827-distribucion.md). Neto540,88 en23renglones; totalND,saldo,facturasypagosinalterados. La descripción anterior de la carga de una líneaFinanciamiento corresponde al estado previo a esta imputación.


## ND90696 resuelta

Registrada compra2143523739 y distribuida proporcionalmente, respetando diferenciasporfactura expresasdelPDF. [Detalle aplicado](baya-casal-nd90696-distribucion.md). Total$21.536,15,neto17.798,47,57renglones; efectoUSD0verificado. El hallazgo previo de faltante queda histórico.


## NC100961 resuelta

Cargada compra2143523740 yrelacionada conFC316792. [Distribución aplicada](baya-casal-nc100961-distribucion.md): crédito$90.764,56, reducciónneta75012,03 en73repartos,costosPesosnegativosyUSD0verificados. El hallazgo anterior de faltante queda histórico; elpuenteglobalanteriornofuepresentadocomosaldovigente.


## ND95459 resuelta

Registrada compra2143523741 ydistribuida, respetando incremento36.030,87 yreducción7.059,16 porfactura. [Detalle aplicado](baya-casal-nd95459-distribucion.md). Total35.055,77,57repartos,USD0. Se corrigió elsignoNDfinancieranegativa enCostosBase paraque lareducciónseaefectivaenresultados. La descripción anterior de faltante queda histórica.


## ND95460 resuelta

Cargada compra2143523742 eimputada porfactura/producto/cultivo/campaña en12renglones. [Detalleaplicado](baya-casal-nd95460-distribucion.md). Neto40.007,25,total48.408,77,USD0verificado. Documento ya no es faltante; quedaND96887de los7identificados originalmente.


## ND96887 resuelta; documentos faltantes completados

Compra2143523744, distribuida23líneas respetandoalícuotas21/10,5. [Detalleaplicado](baya-casal-nd96887-distribucion.md). Total4.385.355,23,USD0; sin cambiosenfacturasoriginales. PrecisiónIVA corregidaexclusivamente paraNDdiferenciaTCpesosfinancieras, con verificación de totalespreviosvisibles. Los7documentosfaltantesdelrelevamientoinicialyaestánregistrados;restodelpuentediagnósticosiguependiente de revisiónyrecalculación.
