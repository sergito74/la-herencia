# Bayá Casal: análisis de duplicación AgroNación1909

## Corrección aplicada y verificada

Autorización explícita de Sergio: «Ok. Adelante entonces». Auditoría SQL **95**. El registro 1909 se conserva con todos sus campos e importe efectivo 0; el importe original **$471.336,79** está guardado en Parametros de AuditoriaCorrecciones y en el archivo antes/después. Esto retira el crédito duplicado y evita que el FIFO vuelva a utilizarlo. No se trasladó a otra cuenta.

Anuladas lógicamente **15644, 15645, 15646, 15647 y 15648**, con motivo, usuario y fecha. Consumo 5917, vínculo 5577, débitos BNA 18215/18216 y pagos de resumen 93/94 conservados exactamente por comparación antes/después. No se tocó la imputación 15598 de $27,27: queda como revisión separada. Sin FIFO ni cierre.

Respaldo WC verificado: `C:\Program Files\Microsoft SQL Server\MSSQL17.SQLEXPRESS\MSSQL\Backup\WC_baya-duplicado1909-036_20261019_231640_513130.bak`. Auditoría: `backups/baya-conciliacion-20261019/duplicado1909-20261019_231641_537044.json`. Script: `backend/scripts/baya_casal_duplicado_1909_036.py`. Reversión completa mediante `--revertir 95`: restaura importe original y las cinco aplicaciones en una transacción con respaldo. La reversión genérica 035 quedó bloqueada para esta regla: restauraría solo aplicaciones y dejaría el pago en 0. Cinco pruebas del módulo pasaron, incluida prueba con mocks de ese resguardo; sin escrituras de prueba sobre datos reales.

El análisis siguiente corresponde al estado anterior. Las otras diferencias de Bayá siguen pendientes; no se declaró saldo conciliado ni se recalculó el puente como si fuera vigente.


## Resultado

La reglaFR-029 está cumplida en los débitos bancarios del resumen651: **no corregir ni reasignar esos débitos**. El problema es un registro histórico de pago1909 que duplica el consumo de tarjeta ya vinculado a la factura y que además fue reutilizado porFIFO. Este análisis no aplica cambiosSQL.

## Cadena reconstruida

1. FC0020-00215282/IdDeuda2143512802 del25/06/2020:USD6.502,78,TC73; PDFindica AgroNación360días. Equivalente$474.702,94 por total impreso; consumo471.336,79 más retención3366,33 suma474.703,12: diferencia$0,18 por precisión, no asumir que son dos pagos.
2. Consumo5917,$471.336,79,fecha25/06/2020, resumen651/código9132958; vínculo5577 apunta a esa factura por todo el importe. El consumo es el crédito válido al proveedor.
3. RegistroPagos efectivo1909:misma fecha,importe y contacto226; IdFormaPago18 corresponde aAgroNación. No es un retiro de billetes ni pago del resumen; es la representación histórica del pago al proveedor que sigue sumándose junto al consumo importado.
4. Resumen651 cierra15/06/2021 y vence28/06/2021. Pagos del resumen:93/BNA18215 por489.287,53 y94/BNA18216 por71.898,30; ambos28/06/2021. Total561.185,83 incluye otros consumos/cargos, no soloBayá. Los dos bancos tienen contacto373AgroNación y ningunaAplicacionesPago a facturas. Se conservan íntegros.
5. Fuente original`Bancos/BNA/AgroNacion/2021/Resumen 2021 06.PDF`:línea25/06/2020,importe471.336,79 y denominacióncomercialMONSANTO ARGENTINA. El sistema describeBayáCasal y lo vincula aFC215282; la asociación está apoyada en coincidenciafecha/importe y formaAgroNación delPDFdecompra. Conservar ambos rótulos como evidencia; no reasignar al contactoMonsanto por su sola descripción bancaria.

## Imputaciones generadas por el duplicado

ElFIFOejecución50 del07/10/2026 tomó1909 como otro dinero disponible y generó:

| IdAplicacion | Factura/IdDeuda | Importe aplicado |
|---|---|---:|
|15644|215282 /2143512802|3.339,04|
|15645|219332 /2143512861|300.724,78|
|15646|235074 /2143513044|36.768,88|
|15647|240846 /2143513106|129.300,60|
|15648|63227 /2143513252|1.203,49|
|Total||471.336,79|

También está vigente15598,BNA16331,por27,27 aplicado aFC215282, que ya está cubierta por tarjeta: candidata independiente para anulación de imputación por la reglaFR-029. No eliminar ni reasignarBNA16331 solo por esa imputación; es otro pago real de proveedor y debe quedar disponible para conciliaciónposterior. La1865,BNA16334,por6502,78 ya fue anulada porFIFO; no tocarla de nuevo. Las unidades de AplicacionesPago y conversiones de documentosUSD deben validarse al reconstruir elFIFO; no confundir estos importes históricos con cantidadesUSDdecompra.

## Corrección concreta a preparar

- Conservar consumo5917,vínculo5577,factura,retención y ambosdébitos18215/18216 con sus pagos93/94.
- Neutralizar el efecto del registro histórico1909 como pago duplicado, conservando importeoriginal471.336,79 y todos sus campos en auditoría/restauración. No trasladarlo al contactoAgroNación: no es pago del resumen.
- Anular lógicamente las cinco aplicaciones15644–15648 con motivo/usuario/fecha y restauración; no recircular ese dinero porFIFO.
- Revisar/anular imputación15598 aFC215282 por ya estar pagada con tarjeta, conservandoBNA16331 y su disponibilidad.
- Verificar saldoBayá antes/después: neutralizar1909 retira un crédito471.336,79 enpesos. No equivale a deuda realvencida, ya confirmada cancelada porSergio; las otras diferencias continúan pendientes.
- No corregir soloAplicacionesPago: la vista de movimientos suma1909 directamente y la anulación de aplicaciones sola no cambia el saldo ni impidequeFIFOreutilice1909.
- RespaldarWC y guardar antes/después antes de aplicar. El mecanismo genérico035solo revierte aplicaciones; una corrección del registrofuente necesita además restauración expresa de ese registro. No registrar una operación que la interfaz anuncie reversible si no restaura también el origen.

## Alcance

Se completó análisis y propuesta; no se anuló nada, no se modificaronbancos/tarjeta, no se ejecutóFIFO ni cierre. Evidenciaestructurada en`backups/baya-conciliacion-20261019/analisis1909-*.json` y textoextraído delresumenoriginal. ReglaFR-029 en`specs/036-revision-sistematica-cuentas/spec.md`; baja lógica de aplicaciones en`backend/src/features/revision_cuentas/dobles.py` y`auditoria_cuentas/correcciones.py`.
