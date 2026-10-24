# Ejecución del plan Condominio — 24/10/2026

Sergio autorizó continuar el plan de `condominio-15-medios-20261024.md`. Se avanzó sobre los tres bloques: diferencias documentales, evidencia del pagador y matriz histórica sin doble cómputo. Esta nota se actualiza con la aplicación y sus controles; no tomar una propuesta como escritura aplicada.

## Originales Easy y Cooperativa

Easy1266-00024737, 07/03/2014: neto1098,02 + IVA230,58 + percepciónIVA32,94 = **1361,54**. VISA1362, vuelto/donación0,46. WC había omitido cuatro lámparas halógenas (neto65,95), cargado el cepillo115mm a67,50 en lugar de65,70, agrupado tres esmaltes a92,56 cuando uno tiene neto92,57 y omitido la percepciónIVA. El resto del detalle se conserva: respirador90,09 y caja65,29 son correctos según ampliación del original. La lectura preliminar a menor resolución no era suficiente para esos centavos.

Cooperativa0021-00010018, 05/12/2013: netos37,96 al21% y1997,38 al10,5%; IVA impreso7,97 y209,72; total **2253,03**, recibido tarjeta2253,03. El cálculo sin redondear IVA por alícuota da2253,0365; redondeando cada IVA como el original da2253,03. La hipótesis inicial de precisión simple se descartó al validar. La vista usa para este comprobante el redondeo de cada una de sus dos alícuotas, sin cambiar netos ni precios. No corresponde modificar precios ni inventar un centavo de gasto para resolverlo.

Las fichas22/29/130 estaban cerradas en bloque el09/10 por comparación con Access. Se notificó a Sergio antes de la revisión puntual; se corrigen solo originales comprobados de22/29, sin declarar deuda nueva ni cierres nuevos. Titularidad y eventual reintegro siguen requiriendo evidencia externa.

Aplicación8568 asociaba Easy2014 a origen `tarjetas217`: el vínculo217 actual pertenece a compra2143513885, peaje2022 por272. No es otra tarjeta que pagó Easy. Se aplicó anulación conservada y reemplazo por el pago existente561/op995, por sus1250,97, sin aumentar el pago ni crear otro. La diferencia del pago frente al original no se atribuye automáticamente al Condominio.

## Búsqueda externa y matriz histórica

Outlook local consultado por COM, solo lectura: almacenes Outlook (entrada/enviados), Alquileres, La Herencia y Sucesion, subcarpetas incluidas; período2011–2014 y asuntos pertinentes. Catálogo local de214 mensajes candidatos en `backups/condominio-15-medios-036/correo-candidatos-2011-2014.json`. Sin enviar, mover ni marcar correos. No apareció asunto de las tres compras o resumen de sus tarjetas en ese filtro; esto no excluye mensajes con otros asuntos. La ampliación por asuntos y nombres de adjuntos generó203 candidatos en correo-ampliacion-medios.json; no se localizaron resúmenes de las tres tarjetas. Los correos HSBC aportan contexto de transferencias, no identificación del titular de esas compras.

Nuevos solapamientos comprobados en `Aportes de Capital Directores.xlsx`, hoja Depositos1: tres aportes de efectivo1500/3000/3000 (filas7/21/33) **ya integran733781**, igual que cheque3031 de fila14. También están el préstamo10000 del28/03/2016 y su devolución-10000 del20/04/2016 (filas61/62). No sumar733781 +7500 ni recargar el préstamo de2016. La hoja tiene61 importes y el total733781 es neto, incluye la devolución.

## Aplicación verificada en WC

Script `backend/scripts/corregir_easy_cooperativa_condominio_036.py`, inspección por defecto y aplicación explícita con respaldo, bloqueo de conciliación, comprobación de concurrencia, transacción y auditoría130 (`condominio-documentos-easy-cooperativa-036`).

- Easy: detalle corregido, agregado neto65,95 de cuatro lámparas, esmalte separado2×92,56 +1×92,57, cepillo65,70 y PercepcionIVA32,94. Total calculado1361,5442, redondeado **1361,54**, igual al original. Clasificación conservada General/No Aplica20; lámparas en Mantenimiento Construcciones5.
- Cooperativa: vista fiscal redondea el IVA de sus dos renglones/alícuotas como el original; total2253,0300. Precios y cantidades intactos. El caso de Easy usa doble precisión antes de IVA para no sumar centavos espurios. Cambios acotados a estos dos IDs en las dos vistas existentes; definiciones anteriores en snapshot para revertir.
- Aplicación8568 anulada, conservada. Nueva aplicación21107 desde pago561 por1250,97 a la misma factura Easy. No cambió ningún pago ni se cargó la diferencia como aporte.
- Fichas22/29 → esperando-evidencia por revisión puntual; valores/fechas del cierre anterior preservados como antecedente. Naldo130 sigue cerrada, sin cambio.
- Control antes/después: cantidades/sumas de todas las cajas, pagos y socios (pesos/kg/US$) idénticos. Todos los saldos de contactos distintos22/29 idénticos, incluido549=-296987,50. Las diferencias22/29 corresponden exclusivamente a sus documentos.
- Saldo nominal posterior Easy=-110,5752 (incluye redondeos anteriores): **no se presenta como deuda externa exigible**. Diferencia del comprobante frente al pago561:110,5742, redondeada110,57; no confundirla con el saldo global redondeado110,58. Cooperativa=-0,0131 global, pendiente de su evidencia de pago/libro.

Respaldo verificado: `C:/Program Files/Microsoft SQL Server/MSSQL17.SQLEXPRESS/MSSQL/Backup/WC_condominio_documentos_easy_coop_036_20261024_103544_630286.bak`.
Snapshot: `backups/condominio-15-medios-036/correccion-documentos-20261024-103545.json`. Dos intentos anteriores se revirtieron completos: primero por valor Origen no admitido (se adoptó manual), segundo porque el control rechazó2253,04 y obligó a corregir la hipótesis de IVA. No quedaron cambios parciales; registros revertidos103412/103433 conservados. La repetición posterior informa ya_aplicado_sin_escrituras.

## Nuevas fuentes: HSBC y Maignal

La búsqueda fuera de la carpeta Condominio LSC encontró originales anteriores bajo:

- `Documents/Alquileres urbanos/Estacion de Servicio/Condiminio/Resumenes de cuenta/HSBC`: cuenta titulada **Condominio Giamberardini Oscar y otros**.
- `Documents/Resumenes Bancarios/HSBC`: cuenta titulada **Oscar Vicente Giamberardini**. Sergio confirmó el24/10/2026 (opción1) que se administraba como fondos del Condominio LSC; conservar la titularidad bancaria original.
- `Documents/Maignal/Pagos Venta Camion.xlsx` y `Pagos Venta Camion 1.xlsx`.

Se corrigió la cobertura insuficiente del rastreo anterior: ahora hay23 originales HSBC/104 páginas consultados en los meses pertinentes. Script de extracción de solo lectura `backend/scripts/rastrear_resumenes_hsbc_condominio_036.py` (Python del sistema con pdfplumber); huellas y cobertura en `hsbc-cobertura-verificada.json`, líneas/fecha/página en `hsbc-coincidencias.json`, todo bajo backups/condominio-15-medios-036. Páginas bancarias relevantes renderizadas e inspeccionadas; originales intactos.

| Pago | Respaldo nuevo | Conclusión |
|---|---|---|
| 333 | HSBC Condominio noviembre2012, pág2, 12/11, P.SERV.PCBE ref33023,10004,70; servicioRSBA y partida de boleta0079575 | **Origen Condominio comprobado**, mismo pago existente. No importar otro débito. |
| 378 | HSBC Condominio marzo2013, pág2, 11/03, ref37948,10004,70; servicioRSBA y misma partida | **Origen Condominio comprobado**, pago anterior al vencimiento12/03 coherente. No tocar ARBA cerrada. |
| 190 | HSBC Oscar abril2011, pág4:12/04,ref72238,95; servicioDA95 identifica CUIT de Irma y período03/2011 | Contrasta fechaWC11/04 vs débito12/04. Fondos del Condominio confirmados por Sergio; no crear otro pago ni duplicar aporte. |
| 191 | HSBC Oscar mayo2011, pág4:11/05,ref73665,95; DA95 Irma/período04/2011 | Fondos del Condominio confirmados por Sergio; sin asiento nuevo. |
| 192 | HSBC Oscar junio2011, pág3:13/06,ref90290,95; la línea no identifica contribuyente | Candidato bancario fuerte, aún falta comprobante fiscal/identificación. No afirmar prueba completa. |
| 193 | HSBC Oscar agosto2011, pág5:08/08,ref07309,95; DA95 Irma/período07/2011 | Fondos del Condominio confirmados por Sergio; sin asiento nuevo. |
| 194 | HSBC Oscar septiembre2011, pág4:19/09,ref21794,95; DA95 Irma/período08/2011 | Fondos del Condominio confirmados por Sergio; sin asiento nuevo. |
| 28 | Maignal/Pagos Venta Camion.xlsx, Cheques 3os A8:H8; libro1/Pagos A4:L4: cheque87678128,Macro,titularMaignal,2926,vto25/10/2011 | Origen del cheque identificado por número, no por importe. Destino vacío: falta recibo/endoso a Jauregui. |
| 290 | Mismos libros: Cheques 3os A17:H17 y libro1/Pagos A13:L13:95512293,3031,Carlos Torrontegui/siembra avena | Origen/destino respaldados, una sola financiación ya incluida en733781. Sin reasignar97 cerrado. |

Sergio respondió opción1 el24/10/2026: la cuenta HSBC titulada Oscar se administraba como fondos del Condominio LSC. Clasificación patrimonial resuelta para este rastreo; los pagos190/191/193/194 por380 tienen origen Condominio confirmado, además del respaldo bancario que identifica aIrma. Pago192 por95 mantiene pendiente su identificación fiscal, aunque la procedencia patrimonial de la cuenta ya está aclarada. Conservar la titularidad bancaria original, los pagos existentes y el control de eventuales reintegros antes de socio3. No se crearon impuestos de Irma ni se reabrieron su cuenta46/AFIP por inferencia. Los otros gastos personales de esos resúmenes quedan fuera del sistema.

## Matriz única producida

`backend/scripts/matriz_financiacion_condominio_036.py`, solo lectura, cruza fuentes, pagos vigentes, caja completa, BNA/contacto549, libro completo socio3 y31 históricos operativos del Condominio. Evidencia final JSON/CSV `backups/condominio-15-medios-036/matriz-financiacion-20261024-104448.*`.

| Universo de fuente | Filas | Importe neto | Tratamiento |
|---|---:|---:|---|
| Depósitos/transferencias según referencia |54|720282,00|Banco candidato; no todos vinculados ni atribuidos en WC.|
| Cheque venta camión sin ruta explícita,07/03/2012 |1|2968,00|Pendiente de identificar ruta, no asumir depósito.|
| Aportes efectivo ya incluidos |3|7500,00|Caja2088/2089/2090; forman parte de733781, no adicionales.|
| Cheque directo por avena |1|3031,00|Pago290; forma parte de733781 y también de105 pagos.|
| Préstamo28/03/2016 y devolución20/04/2016 |2|0,00|+10000/-10000; cajaCond2129 y cajaGiamigli78 como representaciones, no nueva financiación neta.|
| **Planilla aportes** |**61**|**733781,00**|Suma neta, incluye la devolución.|
| Pagos directos EF de Movs |105|110536,02|Pago290 ya está en planilla aportes.|
| **Unión de ambos universos, quitando pago290 repetido** |**165**|**841286,02**|**Universo de fuentes, NO deuda ni asiento listo para socio3.**|

Los140 ingresos de caja «Aporte Condominio (pago directo)» por65645,76 son representaciones de egresos existentes. Los140 tienen par identificado por referencia al egreso y monto opuesto;72 ya remiten a operaciones del universo de165 y **no se suman**. Los68 restantes por15109,68 quedan como filas de investigación separadas, sin convertirlos en aportes adicionales:66 no tienen coincidencia en Compra Giamigli de Movs al mismo día/importe; dos coinciden en otras modalidades (Peuman CC, Sodimac TJC). Esto no demuestra ausencia de documento ni autoriza borrar puentes.

Cuenta549:20 movimientos actuales (19 créditos bancarios de financiación en sentido económico y un pago4134 de la empresa por impuestos del Condominio). Dos ingresos BNA10348/11240 no tienen candidato en esta planilla61 bajo el criterio acotado: no borrarlos ni reasignarlos; ampliar fuente antes de concluir. Las coincidencias bancarias son candidatos por fecha/importe; sus importes no se acumulan otra vez al aporte fuente. La matriz conserva las31 filas posteriores aparte, sin inventar contrapartidas de2016–2026.

Socio3 sigue con41 movimientos desde29/12/2023, sin asiento individual de2011–2014. Se revisaron todas sus filas: la matriz las conserva completas para controlar aperturas/compensaciones; no se dedujo deuda histórica por restar fuentes al saldo actualizado. **Ningún asiento nuevo ni valuación kg/US$ aplicado.**

## Verificaciones y pendientes reales

- Ruff check de los tres scripts PASS; inspección SQL de originales, controles transaccionales y repetición idempotente PASS.
- Auditoría de campañas posterior:16341 renglones de compras y55 labores; solo permanece la excepción conocida sin_asignacion del redondeo ajeno a estos documentos. Informe `backups/auditoria-campanias/auditoria-20261024_103940.json`. No se validó ni cerró una campaña nueva.
- Siguen faltando resúmenes/titular y eventual reintegro para Naldo/Cooperativa/Easy; no hay respaldo para aumentar los pagos registrados ni cargar la diferencia al socio. Las facturas sí están corregidas.
- AFIP: clasificación patrimonial confirmada por Sergio (fondos Condominio); pendiente boleta de junio; ARBA20009,40 ya tiene fuente bancaria; cheque2926 ya tiene origen, todavía no recibo/endoso; combustibles519,53 tienen medio efectivo documentado, pero no origen/reintegro. No crear egresos de caja nuevos.
- La matriz evita las duplicaciones detectadas, pero falta revisar los68 puentes restantes y completar los vínculos de banco/2016–2026 antes de llevar historia a socio3. No cargar841286,02 como un aporte global.
- Pago581/AFIP-UATRE conserva el pendiente externo anterior. No se modificó en este tramo.

## Aclaración de Sergio incorporada — 24/10/2026
Respuesta «1» a la consulta sobre HSBC Oscar: fondos del Condominio LSC. Matriz y tareas actualizadas; no supone aprobación de todos los gastos de la cuenta como gastos de Giamigli, ni valida el documento de junio ni habilita sumar otra vez pagos/aportes. No hubo escrituras contables en esta actualización.

Matriz regenerada con la aclaración: `backups/condominio-15-medios-036/matriz-financiacion-20261024-105647.json` y CSV homónimo. Universos e importes sin cambio; actualización de evidencia solamente. La respuesta explícita posterior «Fondos del Condominio LSC» ratifica la opción1, sin ampliar el alcance a gastos propios.
