# NC134760 — reconstrucción y corrección aplicada

Sergio autorizó20/10/2026 corregir Id2143517449. Documento ya existente, sin duplicar compra, pago ni crédito. Fiscal **neto$235.045,89+IVA21%$49.359,64=crédito$284.405,53**. Antes SQL mostraba$284.392,48: crédito aumentado$13,05 a centavos.

Se reconstruyó primero el importe por factura desde diferencias expresas del PDF, luego prorrata por netos de sus líneas, con mayores restos a centavos:

| Factura | IdDeuda | Crédito neto pesos |
|---|---:|---:|
| 451182 | 2143515126 | 45.070,47 |
| 451187 | 2143515202 | 50.320,53 |
| 451189 | 2143515204 | 61.753,05 |
| 451190 | 2143515280 | 15.414,03 |
| 451191 | 2143515281 | 39.503,52 |
| 451193 | 2143516380 | 22.984,29 |

Reemplazadas137líneas anteriores por139correspondientes a todos los renglones de las seis facturas. Son financieros, cantidad1/unidadARS/precio negativo/IVA21, sin devolución física. Se conservan producto, formulado, rubro, centro, destino y campaña textual del origen. IdCampaña se resuelve por el texto de la campaña para corregir inconsistencias internas del origen exclusivamente en la NC, sin modificar facturas. Los `No Aplica` reales del origen se conservan; no se asignan a cultivos por conjetura. Relaciones agregadas con las seis facturas, cuyos datos y líneas quedan intactos.

Cabecera: ajusteTC activado y vencimiento10/06/2026 según PDF. Verificados139costos, reducción neta$235.045,89 yUSD0; efecto en cuenta bimonetariaUSD0, total fiscal y relación con las seis facturas. Verificación posterior adicional de139renglones contra producto/dimensiones/campaña/importe de su plan.

## Precisión fiscal

Las dos vistas de importe tenían la corrección de coeficiente IVA en precisión doble solo paraND financieras en pesos/ajusteTC. Se amplió el mismo criterio aNC financieras en pesos/ajusteTC para evitar deriva de centavos del IVA SQL REAL. Dentro de la misma transacción respaldada se verificó que los totales visibles a centavos de todos los demás documentos financieros, en ambas vistas, permanecieran iguales. SQL de vistas antes/después y comparación completa quedan en auditoría local. No se creó una línea de redondeo artificial.

PDF `C:/Users/Sergio/Dropbox/Giamigli de Bolivar SA/Compras/04 2026 - 03 2027/20260610_BayaCasal 001.pdf`. Respaldo verificado `WC_baya-nc134760-036_20261020_091216_739573.bak`. Script `backend/scripts/baya_casal_nc134760_036.py`; auditoría `backups/baya-conciliacion-20261019/nc134760-correccion-*.json` incluye cabeceras/líneas originales,139partes, hash PDF, vistas y verificaciones. Transacción con bloqueo y guardas, lectura trascommit; sin FIFO/cierre ni pruebas con datos ficticios.
