# Revisión de los18 pagos y AFIP/UATRE — 23/10/2026

Sergio pidió avanzar con los18 pagos señalados y la discrepancia. Se revisaron los registros efectivos de WC, catálogo de medios, aplicaciones, documentos y fuente de planilla. No se consideró fecha/importe como prueba suficiente ni se reabrieron cuentas cerradas.

## Hallazgo principal: falta de enlace no significa egreso faltante
Los18 pagos por $32.419,62 se distribuyen según su medio actual:

| Medio registrado | Cantidad | Importe |
|---|---:|---:|
| Efectivo | 3 | $376,68 |
| Débito bancario | 10 | $21.003,93 |
| Valor de terceros | 2 | $5.957,00 |
| Tarjeta de crédito no propia | 3 | $5.082,01 |

EF de Movimientos LSC no alcanza para afirmar que el gasto se pagó físicamente con la caja de Giamigli. Los15 medios no efectivos no deben forzarse a esa caja ni generar egresos nuevos. Su medio registrado necesita contraste con comprobante/banco/tarjeta, especialmente si contradice la planilla. No se declaran conciliados fiscalmente por el solo catálogo.

IDs no efectivos: débitos190,191,192,193,194,333,378,441,442,467; valores28/290; tarjetas315/503/561. Varios ya tienen aplicaciones fiscales previas (incluido FIFO): no modificarlas para fabricar coincidencia con caja.

## Tres vínculos completados
| Caja Giamigli | Pago existente | Fecha | Importe | Contacto |
|---:|---:|---|---:|---|
| 3 | 223 | 04/04/2011 | $200,00 | Municipalidad72 |
| 4 | 222 | 06/07/2011 | $71,78 | Municipalidad72 |
| 29 | 581 | 07/05/2014 | $104,90 | UATRE315 |

Fecha, importe, forma3=Efectivo y origenCondominio comprobados. Se verificó que los pagos no estuvieran enlazados a ninguna otra fila (incluidas anuladas/archivadas). Solo se agregó IdPagoEfectivo y una referencia en Detalle. Ningún egreso, aplicación, asiento de socio ni reasignación nuevo.

## AFIP/UATRE
Pago581: contacto315, efectivo, IdOperacion1046. Impuesto228: IdOrganismo315, Aporte Sindical, período04 2014, $104,90, misma IdOperacion1046 (fecha08/05/2014). El documento original no tiene PDF registrado.

La relación interna de operación respalda conservar UATRE. La fuenteMovs y caja29 decían AFIP: se preservó ese concepto original y se anotó la discrepancia y los IDs documentales en Detalle, sin moverlo a AFIP ni alterar saldos. La comprobación externa del original queda pendiente dentro del control documental; no presentar el cruce interno como boleta original.

## Aplicación y verificación
Script: backend/scripts/vincular_tres_pagos_condominio_036.py, inspección por defecto; --aplicar con respaldo, validación de identidades/medio/organismo, control de exclusividad, transacción y auditoría. La comparación anterior/posterior abarcó cantidades y sumas de todas las cajas, saldos de todos los contactos y cantidades/importes/kg/US$ de socios: idénticos.

Backup verificado: C:/Program Files/Microsoft SQL Server/MSSQL17.SQLEXPRESS/MSSQL/Backup/WC_condominio_vinculos_tres_036_20261023_121249_669104.bak.
Evidencia aplicada: backups/condominio-18-pagos-036/aplicacion-20261023-121250.json. Clasificación18: revision-18-20261023.json en la misma carpeta. El primer intento excedió Detalle y revirtió completo; se comprobaron los tres enlaces todavíaNULL y se aplicaron notas compactas con nuevo backup. El informe fallido se conserva como revertido. Ruff (--ignore E501 por SQL) PASS. Lectura posterior confirma los tres vínculos, sin cambios de concepto.

## Continuidad Claude/Codex
La observación anterior de18 pagos sin IdPagoEfectivo en caja queda desglosada: tres vínculos resueltos y15 registros con medios no efectivos, no15 egresos faltantes. Próximo paso: contrastar esos15 con débitos bancarios, valores y tarjetas/compensaciones del Condominio; luego revisar cómo se representan en socio3 sin duplicar cuentas/pagos existentes. No recargar las fuentes ni reabrir UATRE/AFIP/ARBA/otras cuentas cerradas por inferencia. No declarar cierre del Condominio todavía.

### Actualización 24/10: medio registrado contrastado con originales

Ver [rastreo de los15](condominio-15-medios-20261024.md). «No efectivos» describía el catálogo, no el pago probado: los tres combustibles519,53 dicen efectivo en sus tickets. Cheque95512293/pago290 por3031 ya integra los aportes733781; no duplicar. Diferencias documentales Easy110,57 y Cooperativa0,01, y Naldo a cuenta corriente sin identificación de tarjeta. Sin coincidencias directas de banco/tarjeta/socio en la búsqueda acotada; quedan pendientes comprobantes y financiación histórica conjunta de socio3. Sin nuevas escrituras en WC.
