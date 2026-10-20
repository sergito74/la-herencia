# ND0020-00096887: alta y distribución aplicada

Compra **2143523744**, fecha/vencimiento29/08/2023. Documentoenpesos, AjustaTipoCambio1, PDForiginalarchivadoyvinculado. Carga aplicada por autorización de Sergio el20/10/2026.

| Factura | Diferencia neta$ | IVA |
|---|---:|---:|
|320048|940.230,37|21%|
|320049|2.911.618,00|10,5%|
|336203|27.455,74|10,5%|
|Totalneto|3.879.304,11||

Elimporte atribuidoacadafactura surge deldiferencialdepesificación impreso. Dentrodecadafactura seprorrateóproporcionalmente alneto de susrenglonesvigentes, sinIVA, por mayoresrestos a centavos.

| Alícuota | Neto$ | IVA$ |
|---|---:|---:|
|21%|940.230,37|197.448,38|
|10,5%|2.939.073,74|308.602,74|
|Total|3.879.304,11|506.051,12|

**Totaldocumento$4.385.355,23.** Verificados subtotales porfactura, alícuota,IVAyneto. EfectoUSD0tanto enmotorbimonetario comoencostos.23renglones financieros cantidad1ARS, producto/rubro/centro/cultivo/campañaheredados. Códigos de campañafaltantes resueltospor eltexto existente enorigen, sin modificar facturasoriginales. No se alteraron cantidades/precios originales, no se crearon pagos ni se ejecutóFIFO/cierre.

## Precisión del cálculo fiscal

IVA esSQLreal. Elcoeficiente1+IVA/100 se calculaba conprecisiónsimple: paraestosimportes producía total4.385.355,3223 envezde4.385.355,2304 (ambosantesde redondeovisual). Elprimerintento se revirtióentero alfallarcomprobación deltotal.

Se corrigieron `vw_Compras_ImporteDocumento` y `vw_Cns_Total_Det_Compras` para calcular elcoeficiente conprecisióndoble **solo enNDdediferenciadecambioenpesosconrenglonesfinancieros**. La ramarestante conserva elcoeficienteoriginal. No se agregaronrenglonesdeajuste, ni se adulteraronprecios, netos oIVA.

Unintento de alcanceatodoslosfinancierosdetectó cambio visible enunafacturaajena y se revirtió completo. La versión final acotada verificó antesydespués todoslosdocumentosexistentesconrenglonesfinancieros: mismos totalesvisibles enambasvistas. Loscuatroescenariosdeprecisióndealícuota21/10,5yramas financierano/no se comprobaronconSELECTsin escriturasdeprueba. SQLantes/después ycomparacióndetotales incluidos enauditoría. Construcciónreproducible en `backend/scripts/baya_casal_precision_iva_036.py`, invocada dentro de lamismatransacciónrespaldadadelalta.

| Línea origen | Producto | Cultivo/destinoId | Campaña | Neto diferencia$ | IVA | LíneaND |
|---|---|---|---|---:|---:|---|
| 2141374918 | Lts. Glifosato Sniper 48% | 14 | 2023/2024 | 157488.59 | 21% | 2141390265 |
| 2141375342 | Lts. Glifosato Sniper 48% | 8 | 2023/2024 | 163507.37 | 21% | 2141390266 |
| 2141375343 | Lts. Glifosato Sniper 48% | 11 | 2023/2024 | 95055.98 | 21% | 2141390267 |
| 2141375344 | Lts. Glifosato Sniper 48% | 6 | 2023/2024 | 228910.32 | 21% | 2141390268 |
| 2141375345 | Lts. Glifosato Sniper 48% | 10 | 2023/2024 | 29653.03 | 21% | 2141390269 |
| 2141375346 | Lts. Glifosato Sniper 48% | 6 | 2023/2024 | 114735.44 | 21% | 2141390270 |
| 2141375347 | Lts. Glifosato Sniper 48% | 10 | 2023/2024 | 48629.59 | 21% | 2141390271 |
| 2141375618 | Lts. Glifosato Sniper 48% | 11 | 2023/2024 | 17939.52 | 21% | 2141390272 |
| 2141375619 | Lts. Glifosato Sniper 48% | 8 | 2023/2024 | 30858.07 | 21% | 2141390273 |
| 2141375620 | Lts. Glifosato Sniper 48% | 10 | 2023/2024 | 13964.58 | 21% | 2141390274 |
| 2141375621 | Lts. Glifosato Sniper 48% | 6 | 2023/2024 | 39487.88 | 21% | 2141390275 |
| 2141390008 | Kg. UREA GRANULADA GRANEL | 10 | 2022/2023 | 1388.83 | 10.5% | 2141390276 |
| 2141390009 | Kg. UREA GRANULADA GRANEL | 8 | 2022/2023 | 6202.52 | 10.5% | 2141390277 |
| 2141390010 | Kg. UREA GRANULADA GRANEL | 8 | 2023/2024 | 636531.70 | 10.5% | 2141390278 |
| 2141390011 | Kg. UREA GRANULADA GRANEL (Orden 124) | 10 | 2023/2024 | 153630.68 | 10.5% | 2141390279 |
| 2141390012 | Kg. UREA GRANULADA GRANEL (Orden 124) | 11 | 2023/2024 | 296041.12 | 10.5% | 2141390280 |
| 2141390013 | Kg. UREA GRANULADA GRANEL | 12 | 2023 | 164246.06 | 10.5% | 2141390281 |
| 2141390014 | Kg. UREA GRANULADA GRANEL | 14 | 2023/2024 | 674435.26 | 10.5% | 2141390282 |
| 2141390015 | Kg. UREA GRANULADA GRANEL | 11 | 2022/2023 | 1400.06 | 10.5% | 2141390283 |
| 2141390016 | Kg. UREA GRANULADA GRANEL (Orden 124) | 14 | 2024/2025 | 977741.77 | 10.5% | 2141390284 |
| 2141375146 | Kg. Urea Granulada | 14 | 2024/2025 | 21684.70 | 10.5% | 2141390285 |
| 2141377043 | Kg. Urea Granulada | 8 | 2024/2025 | 2323.91 | 10.5% | 2141390286 |
| 2141378459 | Kg. Urea Granulada | 10 | 2024/2025 | 3447.13 | 10.5% | 2141390287 |

RespaldoWCverificado: `C:\Program Files\Microsoft SQL Server\MSSQL17.SQLEXPRESS\MSSQL\Backup\WC_baya-nd96887-distribucion-036_20261020_000308_134497.bak`. Auditoríaantes/después,SQLycomparaciones: `backups/baya-conciliacion-20261019/nd96887-alta-distribucion-20261020_000309_028136.json`.

Script: `backend/scripts/baya_casal_nd96887_036.py`. Persistencia,origenintacto,relacionesconlastresfacturas,23costospor3.879.304,11ytotalfiscalcorrecto verificados.
