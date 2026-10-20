# Bayá Casal — relevamiento del 19/10/2026

## Corrección aplicada por autorización de Sergio

FC0020-00316792/IdDeuda2143513785 corregida enWC el19/10/2026: precios de los13productos restituidos alPDF en73repartos, sin cambios en cantidades, lotes, destinos ni campañas. TC128,25→230 y vencimiento30/05/2023 según comprobante. Total confirmado por relectura independiente: **USD29.613,30** frenteUSD30.994,8302 anterior; reducciónUSD1.381,5302.

Se agregó una línea financiera explícita `Redondeo IVA segun comprobante FC 0020-00316792`, IVA0 y cantidad1, porUSD0.0097, aproximadamente1centavo, para reproducir el total fiscal sin alterar precios originales de cuatro decimales. El detalle de productos sigue intacto. Respaldo verificado:`C:\Program Files\Microsoft SQL Server\MSSQL17.SQLEXPRESS\MSSQL\Backup\WC_baya-fc316792-036_20261019_230129_907858.bak`. Auditoría antes/después:`backups/baya-conciliacion-20261019/fc316792-correccion-20261019_230129_907369.json`. Script:`backend/scripts/baya_casal_factura_316792_036.py`. Las dos primeras ejecuciones fallidas se revirtieron transaccionalmente; la ejecución final y su persistencia fueron verificadas. No se corrigieron otras facturas, pagos ni cierres.

Las tablas del diagnóstico siguiente son la foto **anterior** a esta corrección; no representan el saldo actualizado. Sergio informó además que corrigió por su cuenta una línea a la que le faltaba precio (la identificó como trigo); no asumir que eso equivale a verificar otra factura sin relectura.


**Continuación detallada:** [Diferencias entre el sistema y el proveedor](baya-casal-diferencias-20261019.md). El puente completo ya separa los USD16.671,22 de diferencia facturada; las menciones previas a diferencia aún sin descomponer corresponden a una etapa anterior. El informe nuevo identifica errores de facturas, duplicaciónAgroNación, canjes, pagos/valuación y límites históricos. No hubo cambiosSQL.

Contacto 226; cuenta proveedor 13338, Giamigli de Bolívar SA. Investigación solicitada por Sergio: correo, extranet, archivos locales y SQL, para discutir diferencias antes de corregir. **Gobiernan dólares**, por instrucción expresa de Sergio. Solo lecturas de WC y fuentes externas; no se registraron ajustes, pagos, documentos ni cierre.

## Confirmación posterior de Sergio

Todos los documentos vencidos están cancelados: no hay deuda vencida con Bayá Casal. Usar este hecho al reconstruir la historia y no proponer pagos por diferencias del sistema. Mantener separados los compromisos futuros2027 y compras firmes PENDIENTE, cuya cancelación no fue confirmada específicamente. No forzar saldo total cero ni borrar compras; ver informe detallado actualizado.

## Resultado externo y comparación

**Corrección de alcance tras aclaración de Sergio:** el saldo siguiente corresponde solo a lo facturado. La deuda total también incluye compras firmes no facturadas, entregadas o pendientes de entrega; todavía no se determinó un total conciliado con impuestos y sin duplicaciones.

El estado completo por fecha de emisión hasta 30/09/2026 y la composición de deuda vigente consultada el 19/10/2026 coinciden: **deuda US$2.055,85; pesos $0,00**.

- FC 0020-00465204, 02/07/2026: US$2.143,26, con saldo pendiente US$2.055,85 tras crédito previo de US$87,41. Vencimiento **30/06/2027**. PDF original recuperado: 2.000 kg de fertilizante mezcla (7N-40P-5S-8Ca), por cuenta y orden de Profertil, TC fiscal $1.840.
- La consulta inicial predeterminada del portal usa últimos 60 días por vencimiento: no sirve como reconstrucción histórica. Se amplió por emisión desde 2010 y se incluyeron aplicaciones. El historial visible comienza con documentos/saldos migrados de 2020/2021; no demuestra ausencia de documentos anteriores.
- Vista bimonetaria del sistema: saldo US$-6.776,89 y $-26.235.366,59, signo crédito menos deuda. Clasifica como `Mixta`; no expresa la regla de dólares indicada por Sergio. Diferencia entre saldos deudores mostrados: US$4.721,04. **Todavía no hay puente conciliatorio que explique ese importe**: no sumar los hallazgos de abajo como si fueran ajustes independientes.
- Se relevaron 169 movimientos y 107 cabeceras de compras. No existen valuaciones específicas de este contacto en `ValuacionProveedor`; la conversión genérica de pagos en pesos usa BNA anterior, mientras el proveedor aplica tipos propios y divide pagos entre distintas fechas. La tolerancia calculada no justifica cerrar ni borrar diferencias.

## Pago faltante y pagos ya cargados

**eCheq 00008092, $5.797.560,71**, endosado el 09/06/2026, Galicia operación LR69BPm765:

- Endoso local y correo enviado 09/06 11:28; recibo proveedor RI 0006-00077444 recibido 12:09 confirman entrega y aceptación. No se encontró en Valores Recibidos, valores propios ni movimiento equivalente de la cuenta/bancos.
- CA 0006-00145717 original confirma aplicación completa: ND 00130997 $316.725,64 + ND 00134486 $109.941,84 + RD 00136157 $5.370.893,23, al TC $1.446,50. El RD refiere cambio de vencimiento de FC 416539; no es una compra adicional.
- El endoso identifica al endosante Giamigli y al beneficiario, pero **no al emisor original**. Falta ese dato y su origen para incorporarlo sin alterar otra cuenta por error. No asumir que es un cheque propio ni inventar contacto de origen.

**Transferencia 10/06/2026 $40.596.244,94 + retención Ganancias $621.445,56**:

- RI 0006-00077612 confirma total $41.217.690,50. Ya registrados como Galicia 3274 y Retenciones 240: **no duplicar**.
- Correo Susana Vesque 10/06 11:25 informa US$28.617,52 excluyendo FC 451184 por devolución de 23 bolsas de maíz (US$4.705,41). Sergio remite pago/retención a las 15:30 para saldar; respuesta 15:58 agradece. No tomar esa intención como saldo final posterior a nuevas compras/devoluciones.
- CA 00145870: $36.962.653,41 de transferencia más retención $621.445,56, TC $1.441, aplicado a FC 451182/187/189/190/191/193 y NC 134760.
- CA 00145871: $259.059,15 de transferencia, TC $1.441, aplicado a FC 431429 y NC 134761.
- CA 00146076 del 16/06: restante $3.374.532,38, TC **$1.432,50**, aplicado a ND 134645 y RD 136157/FC 416539. Las tres partes de transferencia suman exactamente $40.596.244,94. No convertir todo al TC del primer recibo.

## Comprobantes externos no encontrados por número en Compras

Se contrastaron números con las 107 cabeceras y se recuperaron originales del portal. Falta revisar posibles registros bajo otra referencia antes de cargarlos; diferencias de cambio en pesos requieren reconstruir su aplicación, no convertirlas automáticamente a dólares y duplicar cancelaciones.

| Documento | Fecha | Total del PDF | Concepto |
|---|---|---:|---|
| FC 0020-00251611 | 15/06/2021 | US$143,75 | 5 litros imidacloprid; TC fiscal 95,50 |
| ND 0020-00090696 | 03/05/2023 | $21.536,15 | Diferencia de cambio FC 292987/318391 |
| NC 0020-00100961 | 03/05/2023 | $90.764,56 | Diferencia de cambio FC 316792 |
| ND 0020-00095459 | 02/08/2023 | $35.055,77 | Diferencia de cambio FC 316797/332563 |
| ND 0020-00095460 | 02/08/2023 | $48.408,77 | Diferencia de cambio FC 332563/320048 |
| ND 0020-00096827 | 28/08/2023 | US$654,46 | Gastos financiación tarjeta, 2% sobre US$27.044,16; TC fiscal 349,95 |
| ND 0020-00096887 | 29/08/2023 | $4.385.355,23 | Diferencia de cambio FC 320048/320049/336203 |

Los importes incluyen IVA. El portal muestra renglones de base/IVA y aplicaciones: no sumar todos los renglones como nuevos comprobantes. Los dos documentos en dólares totalizan US$798,21; ese subtotal no explica por sí solo la diferencia del sistema.

## Compras firmes pendientes de facturación

**Aclaración expresa de Sergio:** los PENDIENTE son productos comprados, exigibles como deuda, todavía no facturados. Pueden estar remitidos o pendientes de remitir. Se conservan como deuda; no son previsiones ni se excluyen por ausencia en cuenta corriente facturada. La compra y su factura posterior deben vincularse para evitar duplicar deuda.

| IdDeuda | Referencia | Fecha | US$ del sistema | Detalle |
|---|---|---|---:|---|
| 2143517489 | PENDIENTE 56078 | 19/06/2026 | 9.129,45 | 20 bolsas girasol SYN3970 CL-B1 |
| 2143517490 | PENDIENTE 68485 | 22/06/2026 | 2.758,80 | 4.000 kg trigo DM Aromo con Sistiva |
| 2143517491 | PENDIENTE 68476 | 22/06/2026 | 9.504,01 | Agroquímicos por lotes, campaña 2026/27 |

Total calculado antes de redondear cada fila: **US$21.392,26**. Conservar como compras firmes pendientes de facturación según Sergio; contrastar entrega, precio e impuestos con el portal. No confundir con PED.43194 y NC PENDIENTE del 07/07/2025 (Ids 2143515122/2143517432), que se compensan exactamente por US$9.764,2163.

## Hipótesis descartada y antecedentes

- Conservar deducción 137 de Venta Granos 58, COE 330208663868, 17/07/2017. PDF `Dropbox/Giamigli de Bolivar SA/Ventas/04 2017 - 03 2018/20170717_BayaCasal 001.pdf` imprime percepción IVA RG2459 C.I. $2.109,06; IVA RG2300/2007 es $0. La sospecha histórica de quitarla era incorrecta.
- `Cuentas a pagar/Pagos BayaCasal.xlsx` es antecedente de financiación 2023/24, no resumen actual. Resumen local de 25/04/2016 tampoco acredita saldo actual.
- Se identificó liquidación de canje COE 330223253060 del 03/05/2023 en `Agricultura/BayaCasal/descarga.pdf`: conservar trazabilidad al reconstruir aplicaciones históricas.

## Evidencia y próximos pasos

Comprobantes archivados en:

`C:/Users/Sergio/Documents/La Herencia/Administracion y gestion/Auditoria cuentas corrientes/Baya Casal/20261019/`

Contiene 12 PDFs recuperados del portal (los siete de la tabla, FC 465204 y cuatro CA), dos recibos recuperados de Outlook y copia del endoso: **15 PDFs**. También `portal-texto.txt` y `portal-composicion-deuda.txt`, transcripciones de consultas; no son resúmenes PDF emitidos por el proveedor. Las credenciales no se guardaron.

Extracciones de trabajo fuera de Git: `backups/baya-conciliacion-20261019/`, con movimientos, compras, bimonetaria y filas/links observados del portal. Código de valuación consultado: `backend/src/features/auditoria_cuentas/bimonetaria.py`.

Para la revisión conjunta: integrar las compras firmes no facturadas, verificar las referencias y el origen del cheque; luego preparar propuesta de documentos faltantes y valuación por aplicaciones reales. Reconciliar desde un saldo externo comprobable sin descartar la historia anterior a la migración del portal. Solo después corregir WC con respaldo y trazabilidad, aplicar imputaciones y evaluar cierre con deuda pendiente documentada. No se solicitó ni ejecutó FIFO, ajuste global ni cierre en esta etapa.


## Contraste de remitos tras aclaración de Sergio

Consulta de las tres secciones de Insumos, información vigente al 19/10/2026. No confundir este listado actual con una foto histórica exacta al 30/09: separar movimientos de octubre y posibles facturaciones posteriores al corte.

- **68485, 22/06:** trigo DM Aromo con Sistiva, 4.000 kg. Figura remitido y pendiente de facturar. Importe mostrado 2.282,40; sistema US$2.758,80. Conciliar precio e impuestos antes de proponer corrección.
- **68476, 22/06:** coinciden productos y cantidades de los cinco agroquímicos con Remitida y Pendiente Facturar: glifosato 840 L, carfentrazone 5 L, atrazina 150 kg, dicamba 30 L y 2,4-D 260 L. Importes de renglones suman 7.855,21; sistema US$9.504,01. El listado no desglosa IVA: no comparar como totales equivalentes sin verificarlo.
- **Girasol:** el portal muestra 20 bolsas SYN3970 CL-B1 en remito **70561 del 08/09**, pendiente de facturar, importe 7.544,93. Coincide producto/cantidad con PENDIENTE **56078 del 19/06**, pero número y fecha difieren. Posible pedido previo contra remito posterior; vínculo todavía no confirmado. No generar una segunda compra por esa sola diferencia de referencia.
- **70227 del 31/08:** remitido y pendiente de facturar: cletodim 40 L, flumetsulam 10 L, coady metilado 60 L y siliconado 4 L. Importes 260,73 + 252,32 + 164,01 + 142,98 = 820,04. Referencia no encontrada en las cabeceras de Compras relevadas; revisar también líneas de otras referencias antes de concluir omisión.
- **59111 del 25/09:** 6.400 kg soja DM46 E25 tratada, importe 6.628,48, figura tanto en Pendiente Facturar como en Pendiente Remitir. Es **una sola compra**, exigible según Sergio, no dos deudas. Referencia no encontrada en las cabeceras relevadas; confirmar importe/impuestos y documentación de compra.
- **71918 y 71919 del 09/10:** fecha de remisión, no de compra. **Corrección por imágenes de correo:** corresponden a pedidos 59027 del 23/09 y 58758 del 16/09, anteriores al corte; integrar como compras firmes pendientes al 30/09, comprobando que no se hayan cargado bajo otra referencia. No excluirlos por entrega en octubre.
- Remito **68488** de 2.000 kg fertilizante corresponde a FC465204 ya facturada: no sumarlo nuevamente por aparecer en mercadería remitida.

La página Remitida muestra precios/total cero en estas filas: eso no significa entrega gratuita ni deuda cero. Usar Pendiente Facturar y documentos de compra para valuar. Los listados sin desglose fiscal no bastan para afirmar un nuevo saldo global.

Se archivaron `merpenfac.txt`, `merpenrem.txt` y `merrem.txt` junto a la evidencia anterior como transcripciones de consultas, sin atribuirles condición de comprobantes fiscales.


## Correos e imágenes de pedidos revisados

Revisión autorizada de Outlook en lectura, sin enviar, mover ni marcar mensajes. Imágenes inspeccionadas visualmente, no inferidas solo del cuerpo. Evidencia archivada en `Mails pedidos/` bajo la carpeta de auditoría indicada arriba; cuerpos de nueve mensajes y siete imágenes relevantes, sin logos repetidos. No se modificó SQL.

| Correo / imagen | Evidencia comprobada | Consecuencia |
|---|---|---|
| Ani, 19/06 15:12, image004.png | PED0006-56078 del 19/06: los cinco agroquímicos y 20 bolsas girasol SYN3970CL-B1 a 377,2467, subtotal 7.544,93 | Pedido agrupa agroquímicos remitidos como68476 y girasol70561. Coinciden cantidades y subtotales con portal; no duplicar compra por cambio de referencia |
| Mismo correo, image005.png | PED0006-56076: trigo4.000kg a0,5706 =2.282,40, financiadoUSD | Vincula pedido con remito68485. Sistema total2.758,80; 21% sobre neto mostrado daría2.761,70: diferencia2,90 a revisar con precisión/documentación, sin aplicar ajuste automático |
| Ani, 22/06 10:45, image001.png | Nuevo pedido56109: mezcla física7N-40P-5S-8Ca2.000kg, 1.763,20 + flete176,40 =1.939,60 | Sustituye fertilizante inicialmente cotizado. Coincide con neto FC465204; con IVA10,5%=2.143,26. Ya facturado: no sumar pedido otra vez |
| Ani, 26/08 10:08, image008.png | PED57776: metilado60L, cletodim40L, flumetsulam10L, siliconado4L; subtotales164,01/260,73/252,32/142,98 | Coincide con remito70227, neto820,04. Pedido escrito de Sergio25/08 solicitaba50/30/8/4: diferencias justificadas por Sergio: redondeo hacia arriba a envases completos; tomar cantidades confirmadas del pedido/remito |
| Junior, 25/09 16:29, image.png | Soja6.400kg a1,0357: subtotal6.628,48, IVA1.391,98, **totalUSD8.020,46** | Confirma que importe portal de soja es neto y agrega21%IVA. No trasladar sin prueba esa alícuota a todos los productos |
| Mismo correo, image001.png | Listado de pedidos: agroquímicos PED0006-59027 **23/09** y maíz10bolsas PED0006-58758 **16/09** | Ambas compras anteriores al30/09 aunque remitos71918/71919 sean09/10. Revisar incorporación por pedido, sin duplicar al remitirse |

**Regla confirmada por Sergio:** las cantidades solicitadas por correo se redondean hacia arriba según la presentación comercial del producto, porque no siempre pueden entregarse cantidades fraccionadas. Estas diferencias están justificadas y no son errores ni pendientes de aclaración. Para conciliar, tomar cantidades confirmadas del pedido/remito, sin volver a reducirlas al pedido inicial. Así se explican metilado50→60L, cletodim30→40L, flumetsulam8→10L, flurocloridona15→20L y sulfentrazone12→20L. Esta aclaración resuelve cantidades; el pedido muestra carfentrazone SHARK frente a AFFINITY en remito. Precio de lambda microencapsulada en imagen15,835 frente a cotización17,00 aceptada por Sergio: diferencias de marca/precio a verificar, sin asumir identidad de marcas ni modificación aceptada.

Correos aportan condiciones: junio base contado más0,5%mensual a cosecha; Sergio confirma trigo enero2027 y resto junio2027. Septiembre confirma compra financiadaUSD a junio2027; soja cotizada1,03/kg base contado con0,6%mensual según Ani. Imagen final de pedido es fuente para monto financiado efectivamente cargado; no sumar financiación de nuevo sin reconstruir su fórmula.

Las búsquedas en107 cabeceras no encontraron referencias57776/59027/58758/59111. No equivale a ausencia definitiva: revisar líneas y documentos alternativos antes de proponer nuevas altas. Las imágenes de junio muestran subtotales, sin pie fiscal; queda por respaldar tratamiento fiscal de cada grupo. Corrección esencial: excluir pedidos por fecha de remisión posterior al corte subestimaría deuda ya comprada.


## Continuación: contraste de líneas SQL y cuantificación preliminar

Se consultaron todas las líneas de Compras de226 desde01/01/2026, incluidas posteriores al corte, y se agruparon por producto/precio/IVA para respetar los repartos por lote. Extracción `backups/baya-conciliacion-20261019/sql-lineas-2026.json`. Las únicas compras de productos pendientes desde junio son los tres PENDIENTE ya identificados: no hay líneas para nuevas compras de agosto/septiembre, soja ni maíz58758 bajo otras referencias. Los otros documentos posteriores son diferencias de cambio, devolución de maíz y FC465204 ya identificadas. No se incorporó nada a WC.

### Tres pendientes existentes: precisión del precio

El sistema usa IVA21% en los tres grupos existentes. Los precios unitarios quedaron con dos decimales: girasol377,25 frente377,2467; trigo0,57 frente0,5706; agroquímicos5,42/7,49/5,47/106,27 frente5,4196/7,4918/5,4727/106,2667. La suma por lotes conserva cantidades salvo fracciones numéricas. Por ello hay diferencias pequeñas, sin faltantes de volumen.

| Grupo | Neto portal/pedido | Sistema, con IVA | Neto externo ×1,21, redondeado | Diferencia preliminar |
|---|---:|---:|---:|---:|
| Girasol56078/70561 | 7.544,93 | 9.129,45 | 9.129,37 | -0,08 |
| Trigo56076/68485 | 2.282,40 | 2.758,80 | 2.761,70 | +2,90 |
| Agroquímicos56078/68476 | 7.855,21 | 9.504,01 | 9.504,80 | +0,79 |
| Total | 17.682,54 | 21.392,26 | 21.395,87 | +3,61 |

Estos son cálculos comparativos, no totales fiscales recuperados para cada pedido. Revisar cálculo de IVA por renglón y precisión antes de aplicar. No redondear el precio antes de multiplicar por cantidad ni ajustar cuentas globalmente para compensarlo.

### Compras no cargadas detectadas

| Pedido / remito | Fecha compra | NetoUSD portal | Con21%IVA, cálculo preliminar |
|---|---|---:|---:|
| 57776 /70227, agroquímicos | 26/08/2026 | 820,04 | 992,25 |
| 58758 /71919, maíz10bolsas | 16/09/2026 | 1.280,00 | 1.548,80 |
| 59027 /71918, agroquímicos | 23/09/2026 | 6.585,79 | 7.968,81 |
| 59111, soja6.400kg | 25/09/2026 | 6.628,48 | **8.020,46**, total explícito en imagen |
| Total | | 15.314,31 | 18.530,32 |

La imagen adicional de59027 del23/09 (`Mails pedidos/2026-09-23-18-09/image.png`) tiene subtotal6.238,50, IVA1.310,09 y total7.548,59: acredita21% para ese pedido original. El portal posterior muestra neto6.585,79, un aumento347,29: es compatible con financiación, pero aún falta reconstruir la fórmula y días; no añadir interés encima del importe portal sin comprobarlo. Maíz y agosto carecen de pie fiscal completo en las capturas recuperadas:21% es hipótesis apoyada por compras similares, pendiente de respaldo específico, no una corrección ya aprobada.

### Puente provisional de saldos comparables

Bajo la hipótesis fiscal anterior y sin otras compras/pagos posteriores que alteren el corte, el listado de pendientes suma neto32.996,85; con21% sería39.926,19. Más saldo facturado2.055,85 da **US$41.982,04 de deuda estimada**. No es saldo definitivo del proveedor ni un nuevo saldo cargado.

La comparación anterior entre deuda sistema6.776,89 y solo saldo facturado2.055,85 mezclaba alcances. Al extraer los pendientes existentes21.392,26, el resto del sistema equivale a **crédito14.615,37**, contra deuda facturada externa2.055,85: diferencia histórica/valuación **16.671,22** pendiente de explicar. El puente provisional global sería:

- Deuda mostrada por sistema:6.776,89.
- Compras no cargadas, escenario21%: +18.530,32.
- Precisión en pendientes existentes, cálculo comparativo: +3,61.
- Diferencia restante histórica/pagos/valuación: +16.671,22.
- Deuda externa integral estimada:41.982,04.

Este puente separa magnitudes; **no autoriza un ajuste de16.671,22**. Hay que reconstruir aplicación del cheque8092, documentos históricos faltantes y tipos del proveedor. El cheque es un pago no cargado y reduciría deuda; por sí solo no explica el crédito excesivo del resto del sistema. Resolver por documento y aplicación, sin mover importes entre contactos ni cerrar todavía.
