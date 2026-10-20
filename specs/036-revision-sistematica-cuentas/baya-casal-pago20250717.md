# Pago17/07/2025 — reimputación y valuación documental

Aplicado20/10/2026 por autorización de Sergio. Se conservan transferenciaGalicia2682 **$21.177.819,22**, retención204/cert2025-21 **$305.920,52** y ambos movimientos nominales. Total cancelación del reciboRI61767 **$21.483.739,74**. No se crea otro pago ni retención.

## Aplicaciones

El recibo original descargado confirma FC401514/401515/401516/401517/401518/401519/409044 yND124811, en lugar de las asignaciones FIFO a documentos ajenos, algunos posteriores. Se anularon lógicamente21aplicaciones activas incidentes al pago/retención o esos documentos y se crearon9manuales: siete del banco a facturas, banco aND y retención aND. Las otras fuentes antes mal asignadas a estas facturas recuperan disponibilidad; sus registros y demás aplicaciones quedan intactos, pendientes de reconstrucción propia.

Las aplicaciones del sistema están expresadas en pesos de origen: principal de cada factura a suTC original, diferencia de cambio aND124811. Se usó capacidadSQL vigente para seis facturas (sin sobreimputarlas); enFC401515 solo el saldo de **USD3131,20×1120=$3.506.944**, explícito enRI yND, porque el proveedor ya reconocióUSD83,17 de crédito anterior. No se copian importes de facturas pesificados a1261 sobre capacidades pesificadas a1120/1180, lo que duplicaría el cambio además deND.

Verificado pago íntegro aplicado$21.177.819,22 yretención íntegra$305.920,52,9aplicaciones solo a los8documentos delRI, seis facturas sin saldo de capacidad y sin sobreimputación. Cabeceras y líneas de los8documentos no se modificaron.

## Dólares del proveedor

ValuacionProveedor existente: Galicia2682 **USD16.656,29**, Retenciones204 **USD0**. El libro coloca retención$305.920,52 y componente del banco$174.237,53 en pesos, totalIVA deND$480.158,05, mientras cancelaUSD16.656,29 de principal. No dividir todo el banco/retención por1261 ni sumarIVA como principalUSD. Verificado créditoUSD total16656,29 y pesos21483739,74 con motor bimonetario.

## Pendientes explícitos: no declarar cerrado el conjunto

- FC401515 conserva saldo de capacidad$93.151,74 para el crédito anterior de soja yNC120722; no es evidencia de deuda impaga. Esos créditos requieren su imputación propia y revisión de discrepancias fiscales ya identificadas.
- **Nuevo error confirmado ND124811:** SQL$2.770.331,61 frentePDF$2.766.624,94, exceso$3.706,67. Su saldo tras la reimputación es$3.704,39. La diferencia$2,28 se debe conciliar con pequeñas diferencias de importes/valuación de las facturas originales; si se corrige soloND, quedaría sobreimputada$2,28. La siguiente corrección debe revisar simultáneamente el reparto/aplicación, no ajustar apertura ni declarar esa diferencia nueva deuda.
- ND tiene62líneas con cantidades físicas, sin marca financiera, aunque su cabecera sí tiene ajusteTC. PDF original `Compras/04 2025 - 03 2026/20250717_BayaCasal.pdf` detalla las diferencias por las7facturas, neto$2.286.466,89+IVA$480.158,05. Reconstrucción deND pendiente, no ejecutada en esta etapa de pago.

## Verificaciones y evidencia

RI original `backups/baya-conciliacion-20261019/RI_0006_00061767.pdf`, PDFs enviados aSusana17/07/2025 y certificado del14/07. Respaldo verificado `WC_baya-pago20250717-036_20261020_094036_067885.bak`. Script `backend/scripts/baya_casal_pago20250717_036.py`; auditoría local `pago20250717-correccion-*.json` conserva21aplicaciones originales, estados de documentos, plan,9aplicaciones,2valuaciones, hashRI y residuos. Transacción con bloqueo/guardas, sumas nominales, no sobreimputación según capacidadesSQL y lectura posterior alcommit. Sin FIFOglobal, cierre ni cambios de bancos/certificados/compras/costos.
