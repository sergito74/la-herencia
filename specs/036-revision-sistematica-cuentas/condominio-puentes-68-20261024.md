# Condominio: revisión de los68 pares de caja — 24/10/2026

Continuación autorizada por Sergio: resolver pendientes del plan y mantener contexto compartido. La confirmación de Sergio sobre HSBC Oscar como fondos Condominio rige también para este rastreo; no se incorporan otros gastos de esos resúmenes.

## Rastreo previo a la aplicación

Los68 pares por15109,68 tienen68 pagos existentes, todos con medio3=Efectivo, y68 documentos de compra con PDF registrado. No son pagos faltantes. Se extrajeron90 resúmenes originales HSBC2011–2015 de las dos carpetas (titularOscar y cuentaCondiminio), con caché local y huellasSHA256. El extractor no escribe bases ni originales.

Cruce por importe exacto, fecha de factura/pago hasta cinco días antes del débito, comercio identificado y texto explícito TARJETA DE DEBITO: **48 pagos por10318,06** tienen una única transacción bancaria.37 el mismo día; los otros11 a1–4 días, ninguno anterior. Se deduplican copias de resúmenes por fecha/número/operación/importe y cuenta origen. Comercios: OPESSA Saladillo21, OPESSA Nordelta8, Peuman2, Lioca1, PachecoGROC16 (facturas Esso, se revisó ticket con recibido Tarjeta Crédito/Débito; banco identifica comercio terminal). No se interpreta recibidoEfectivo de un ticket fiscal como prueba superior al débito bancario documentado.

Los48 pares son históricos sin IdOperacionCaja; representan egreso de caja y aporte compensatorio creados al reconstruir la apertura. Su neto es cero. Propuesta concreta: medio de los48 pagos3→10; anular exclusivamente sus96 renglones de caja, con nota de reclasificación y pago vigente, conservando importes, fechas, conceptos, referencias, filas originales y snapshot. No anular el pago ni duplicar débito bancario, aporte o socio. No cambiar importes ni aplicaciones fiscales ni reabrir cuentas de proveedores: se comprobará igualdad de todos sus saldos.

Scripts y secuencia reproducible:

1. Desde backend: `./.venv/Scripts/python.exe -m scripts.reclasificar_puentes_hsbc_condominio_036 --preparar` (insumos68 de WC, solo lectura).
2. Desde raíz: `python backend/scripts/rastrear_68_puentes_hsbc_036.py` (Python del sistema/pdfplumber, originales HSBC).
3. Desde backend: `./.venv/Scripts/python.exe -m scripts.reclasificar_puentes_hsbc_condominio_036` (inspección); `--aplicar` exige respaldo verificado, control de concurrencia, pares únicos y transacción.

Evidencia: `backups/condominio-15-medios-036/puentes-68-hsbc-verificado.json`, insumos puentes-68-pagos.json/documentos.json y textos en hsbc-68. La matriz histórica ahora incluye también puentes anulados como historia; no confundirá su retiro de la caja con pérdida de la financiación documentada.

## Otros pendientes contrastados

Quedan20 pares sin prueba bancaria bajo ese criterio. Sus pagos:14,31,40,88,177,331,362,360,516,530,562,604,611,625,660,715,725,733,739,752. No suponer efectivo real ni tarjeta ajena por ausencia de coincidencia.

Se inspeccionaron originales de cinco de esos20:

- Jumbo/pago31: PDF5754-00000002 total511,79 frente a pago356. La búsqueda del importe fiscal encontró compraHSBC511,79; falta completar comercio y fecha/contexto antes de resolver la diferencia. No corregir por simple resta ni atribuir todo al Condominio sin verificar.
- Sodimac/pago88: factura2282-00000483 total624,29, recibido TARJETA BANCARIA, frente a pago571,92. No apareció624,29 en los textos HSBC revisados; no equivale a pago efectivo. Requiere comparar detalle/percepciones y respaldo de tarjeta.
- Pago14/EESS14/10/2011: original122,80, recibidoEfectivo; sin débito identificado.
- Pago362/YPF09/01/2013: original93,72, efectivo93,71 +0,01; sin débito identificado.
- Pago530/YPF14/01/2014: original362,56, recibidoEfectivo; sin débito identificado.

AFIP192/junio: consulta adicional a la carpeta Outlook La Herencia/Administracion/Personal/Recibos de Sueldo y Cargas Sociales, entre01/06 y15/07/2011, no devuelve mensajes. Sigue faltando comprobante fiscal identificatorio; el débitoHSBC13/06 por95 y titularidad de fondosCond están documentados. No inventar boleta ni cargar impuesto nuevo por correspondencia mensual.

Los resúmenes de las tarjetas Naldo/Cooperativa/Easy y el recibo/endoso de cheque2926 siguen sin localizar; el origenMaignal del cheque ya está probado. Estas faltas externas no habilitan duplicar pagos/asientos.

## Aplicaciones y controles terminados

- Auditoría131:48 pagos por10318,06 de medio3→10 y96 renglones ficticios de caja anulados. Pagos vigentes, importes intactos y todos los saldos de contactos/cajas/socios idénticos; cantidades brutas de historia intactas. Caja activa reduce96 filas, saldo idéntico. Snapshot `reclasificacion-48-20261024-111023.json`; backup verificado `C:/Program Files/Microsoft SQL Server/MSSQL17.SQLEXPRESS/MSSQL/Backup/WC_condominio_48_debitos_036_20261024_111022_854593.bak`.
- Auditoría132: originales Jumbo y Sodimac corregidos. En Jumbo faltaban productos del ticket, ajuste0,01 sinIVA y percepciónIIBB10,36: neto gravado414,40, IVA87,02, ajuste0,01, total511,79. HSBC12/12/2011, operación246885, comercioJumboPacheco, confirmó débito511,79 por factura08/12. Pago31 existente356→511,79 y medio10; se anuló su par de caja, manteniendo los356 históricos en las filas anuladas. No crear otro pago ni ajustar apertura. En Sodimac faltaban dos C.TUBO neto20,62 cada uno y percepciónIIBB29,49 (tenía27,02): neto491,57 +IVA103,23 +IIBB29,49 =624,29. Pago88 conserva571,92; falta resumen/titular para resolver52,37. Fichas60/91 pasan a esperando-evidencia, con cierre anterior preservado. Saldo nominal60=0,0060;91=-52,3698, que no se presenta como deuda externa exigible. Todos los otros contactos y socios intactos. Snapshot `jumbo-sodimac-20261024-111513.json`; backup `C:/Program Files/Microsoft SQL Server/MSSQL17.SQLEXPRESS/MSSQL/Backup/WC_condominio_jumbo_sodimac_036_20261024_111512_383150.bak`.
- Auditoría133: Movs355,29/02/2012,CompraGiamigli,TJC,571,92 y originalSodimac recibidoTarjetaBancaria corroboran medio tarjeta. Pago88 medio3→20 y su par de caja anulado, sin cambiar importe ni saldo; titular/resumen siguen pendientes. Snapshot `sodimac-tarjeta-20261024-111851.json`; backup `C:/Program Files/Microsoft SQL Server/MSSQL17.SQLEXPRESS/MSSQL/Backup/WC_condominio_sodimac_tarjeta_036_20261024_111850_375003.bak`.

Los tres snapshots están en backups/condominio-15-medios-036; contienen fotos previas y controles para reversión. Ningún cambio en Access/LaHerencia. Anulación de renglones históricos de caja no anula el pago: comprobado contra vw_PagosEfectivoVigentes. Sin operaciones nuevas ni asientos socio3.

Resultado actualizado de los68: **49 débitos documentados +1 tarjeta documentada +18 pendientes**.100 renglones de caja anulados, historia íntegra, saldo de efectivo sin cambio. Los49 débitos vigentes suman10829,85; no sumar los importes históricos de caja otra vez. El parJumbo conserva356 en historia, mientras el pago vigente es511,79; la matriz expone ambos valores para no ocultar la corrección.

Matriz posterior: `matriz-financiacion-20261024-111924.json/CSV`. Mantiene140 puentes históricos,72 del universo inicial y50 reclasificados entre los otros68. Los18 pendientes de origen/reintegro tienen importe histórico3863,70: pagos14,40,177,331,362,360,516,530,562,604,611,625,660,715,725,733,739,752. No eliminar ni reasignar por ausencia de débito.

Validaciones: scripts Ruff PASS con exclusiónE501 por literalesSQL; tres repeticiones de aplicación devuelven ya_aplicado_sin_escrituras. Auditoría campañas `backups/auditoria-campanias/auditoria-20261024_111925.json`:16350 líneas de compras y55 labores; solo excepción conocida sin_asignacion, sin anomalías nuevas.

## Pausa y nuevo control solicitado por Sergio

Sergio preguntó si todas las compras estaban a nombre de Giamigli; se informó que no todas y se reconoció que faltaba revisar sistemáticamente el destinatario fiscal antes de atribuir la historia a socio3. Ejemplo comprobado: pago14/EESS14/10/2011 a nombreOscarVicente,122,80, sin corrección aplicada. Easy/Cooperativa/Naldo/Jumbo/Sodimac revisados están a nombreGiamigli. La titularidad del comprobante se revisa por separado del medio/pagador y de su relación económica con la empresa; no basta confirmar fondosCond para reconocer un gasto de Giamigli. Ningún aporte nuevo se registró.

Sergio pausó para pedir explicación, luego autorizó continuar. Se retoma primero inventario de destinatarios de los68 originales, dejando los ajenos o ilegibles pendientes antes de cualquier asiento de socio. Las correcciones anteriores de medio no crearon gastos nuevos: los documentos y pagos ya existían. Revisar destinatario/justificación también antes de considerar firmes las imputaciones históricas.


### Presencia en el sistema Access comprobada — 24/10/2026
Lectura puntual y exclusiva de SELECT sobre LaHerencia, base enlazada por los archivos Access; no se abrieron ni modificaron archivos accdb. Coinciden los identificadores de las68 compras y los68 pagos: ninguno falta en origen. Comparación normalizada contra WC vivo:50 diferencias de medio y1 diferencia de importe (pago31/Jumbo356→511,79), correspondientes a auditorías131–133; ninguna diferencia de contacto u operación. No confundir esos documentos históricos con los puentes compensatorios creados después en WC. Evidencia privada: backups/condominio-15-medios-036/comparacion-access-68-20261024.json. La presencia en Access no valida destinatario, destino económico, saldo ni aporte de socio.

Pendientes inmediatos: justificar relación económica de pagos13,14,15,16,18 (Sucesión) y75 (consumidor final); corregir enlaces documentales375/568 con respaldo; resolver18 medios/reintegros sin prueba suficiente, las tarjetas y las diferencias fiscales; contrastar apertura/compensaciones de socio3 y continuación2016–2026 antes de nuevos asientos. Ninguna escritura financiera en este control de destinatarios/origen.


### Continuación — enlaces y centavos, 24/10/2026
Registro vigente: [condominio-18-centavos-20261024.md](condominio-18-centavos-20261024.md). Aplicada corrección de los2 enlacesPDF375/568, con respaldo y controles de saldos idénticos; idempotencia comprobada. Nueva revisión de18:10 tickets Visa débito coinciden exactamente con el importe bancario separado de su total fiscal por centavos;5 candidatos contradicen el medio Efectivo del original;3 sin candidato. Los18 conservan su contabilización: no aplicar tolerancia automática ni aumentar/aplicar pagos por inferencia. Siguiente: resolver representación de total fiscal/cobro bancario/centavos en esos10 y preservar ambos valores; aclarar5 contradicciones y procedencia/reintegro de3 efectivos, además de6 excepciones fiscales y apertura de socio3. Sin asientos nuevos de socio ni importes financieros modificados en este tramo. Evidencia y respaldo en el registro enlazado.
