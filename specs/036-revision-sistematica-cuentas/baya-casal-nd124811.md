# ND124811 y aplicación julio2025 — manda el resumen del proveedor

Autorización de Sergio20/10/2026: continuar las diferencias identificadas y adoptar el resumen como referencia general para cuentas que lo tengan. Regla incorporada al instructivo compartido y a spec036.

## Corrección de documento

Id2143515121 tenía total$2.770.331,61 y62renglones físicos. Se corrige a **neto$2.286.466,89+IVA21%$480.158,05=total$2.766.624,94**, coincidente con PDF y resumen (reducción$3.706,67). Se conservan marca de ajusteTC y monedaPesos, vencimiento17/07/2025. Se reconstruyen63renglones financieros cantidad1ARS de las siete facturas, por diferencia individual explícita deND y luego netos de sus productos, mayores restos a centavos. Campaña numérica resuelta por texto, preservando NoAplica del origen. Relacionadas las siete facturas, sin alterar datos ni líneas originales.

| Factura | Diferencia neta pesos | Principal pesos de origen cancelado |
|---|---:|---:|
| 401514 | 140.333,07 | 1.114.702,40 |
| 401515 | 441.499,20 | 3.506.944,00 |
| 401516 | 265.560,81 | 2.109.419,20 |
| 401517 | 927.534,66 | 7.367.651,20 |
| 401518 | 407.083,92 | 3.233.574,40 |
| 401519 | 20.660,73 | 164.113,60 |
| 409044 | 83.794,50 | 1.220.710,00 |

## Aplicación fiel al proveedor

Las9aplicaciones de la etapa anterior usaban capacidadSQL vigente, cuyos importes fraccionarios no son la referencia. Anuladas lógicamente y reemplazadas por9manuales a los importes literales anteriores. Banco2682 cubre esos siete principales más **$2.460.704,42 deND**; retención204 aplica **$305.920,52 aND**. ND queda cubierta exactamente$2.766.624,94; banco total$21.177.819,22 yretención total$305.920,52 intactos e íntegramente aplicados. Se elimina el residuo externo ficticio de$2,28: no se creó un ajuste por esa cifra.

La vista genérica de capacidad conserva pequeñas diferencias respecto al libro porque calcula los totales de facturas con cuatro decimales deUSD y redondeos de carga. No interpretar una diferencia de esa vista contra las aplicaciones documentadas como nueva deuda o un sobrepago al proveedor. Es un pendiente de presentación/valuación de documento; no se alteran sus líneas fiscales ni los costos para ocultarlo. Cuenta de dólares conserva valuación específica de bancoUSD16.656,29/retUSD0 aplicada anteriormente.

## Crédito anterior de soja respaldado; pendiente de registrar íntegramente

Se recuperaron y validaron los originales completos LC330226576206/221 de04/09/2024 yCA123088 del22/05/2025 (base64 de PDF contiene saltos de línea; el extractor anterior podía truncarlo). Confirmación fiscal: ajustesDRC de$75.227,50/$4.502,50, sin nuevos kg niIVA. CA123088 aplica LC206$75.227,50+remanenteLC221$1.674,36=$76.901,86 aFC401515$79.722,57 menosIVA deNC120722$2.820,71. CréditoUSD83,17 en el libro; los$2.828,14 usados previamente deLC221 constan enCA115924.

Los PDF recuperados están en `backups/baya-conciliacion-20261019/canje-conjunto-26576206.pdf`, `canje-conjunto-26576221.pdf` y `canje-conjunto-00123088.pdf`, con textos parseados. No se han creado todavía los dos ajustes de liquidación ni todas sus aplicaciones monetarias. La falta de PDF de las finales ya está resuelta; no volver a pedírselo al usuario. No asumir que este crédito faltante representa deuda real deFC401515 ni sumar nuevos kilos.

## Verificación

Verificados63costos por neto$2.286.466,89 yUSD0, total fiscal,USD0 deND en cuenta, relación con7facturas, conservación de cada origen y de sus productos/cultivos/campañas,9aplicaciones, sumas nominales completas y lectura posterior a commit. Respaldo verificado `WC_baya-nd124811-036_20261020_094916_633432.bak`. Script `backend/scripts/baya_casal_nd124811_036.py`; auditoría local `backups/baya-conciliacion-20261019/nd124811-correccion-*.json` conserva estados,63partes y aplicaciones antes/después. Sin banco/retención nuevos, FIFOglobal ni cierre.
