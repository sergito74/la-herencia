# ND0020-00095460: alta e imputación aplicada

Compra2143523742, fecha yvencimiento02/08/2023, pesos ymarcaAjustaTipoCambio. Neto **$40.007,25**, IVA21% **$8.401,52**, total **$48.408,77**. PDF original archivado yvinculado.

Desglose original respetado:

- FC332563:198.377,11−192.493,35 = **$5.883,76 netos**.
- FC320048:126.926,77−92.803,28 = **$34.123,49 netos**.

Dentro de cadafactura se distribuyó proporcionalmente alneto cantidad×preciodesusproductos, sinIVA, con mayoresrestos a centavos.12renglones financieros, cantidad1ARS; producto,centro,destino/cultivo,rubro,formulado ycampaña heredados. Campaña2023/2024. No se alteraronfacturasoriginales ni cantidades/precios; no se crearonpagos ni se ejecutóFIFO/cierre.

| Factura origen | Línea origen | Producto | CentroId | Cultivo/destinoId | Campaña | Neto diferencia$ | LíneaND |
|---|---|---|---|---|---|---:|---|
| 2143514123 | 2141374909 | Kit. Sistiva | 1 | 14 | 2023/2024 | 5883.76 | 2141390230 |
| 2143514032 | 2141374918 | Lts. Glifosato Sniper 48% | 1 | 14 | 2023/2024 | 5715.69 | 2141390231 |
| 2143514032 | 2141375342 | Lts. Glifosato Sniper 48% | 1 | 8 | 2023/2024 | 5934.12 | 2141390232 |
| 2143514032 | 2141375343 | Lts. Glifosato Sniper 48% | 2 | 11 | 2023/2024 | 3449.84 | 2141390233 |
| 2143514032 | 2141375344 | Lts. Glifosato Sniper 48% | 1 | 6 | 2023/2024 | 8307.77 | 2141390234 |
| 2143514032 | 2141375345 | Lts. Glifosato Sniper 48% | 2 | 10 | 2023/2024 | 1076.19 | 2141390235 |
| 2143514032 | 2141375346 | Lts. Glifosato Sniper 48% | 1 | 6 | 2023/2024 | 4164.06 | 2141390236 |
| 2143514032 | 2141375347 | Lts. Glifosato Sniper 48% | 2 | 10 | 2023/2024 | 1764.90 | 2141390237 |
| 2143514032 | 2141375618 | Lts. Glifosato Sniper 48% | 2 | 11 | 2023/2024 | 651.07 | 2141390238 |
| 2143514032 | 2141375619 | Lts. Glifosato Sniper 48% | 1 | 8 | 2023/2024 | 1119.92 | 2141390239 |
| 2143514032 | 2141375620 | Lts. Glifosato Sniper 48% | 2 | 10 | 2023/2024 | 506.81 | 2141390240 |
| 2143514032 | 2141375621 | Lts. Glifosato Sniper 48% | 1 | 6 | 2023/2024 | 1433.12 | 2141390241 |

Respaldo verificado: `C:\Program Files\Microsoft SQL Server\MSSQL17.SQLEXPRESS\MSSQL\Backup\WC_baya-nd95460-distribucion-036_20261019_235501_749834.bak`. Auditoríaantes/después: `backups/baya-conciliacion-20261019/nd95460-alta-distribucion-20261019_235502_624142.json`. Script: `backend/scripts/baya_casal_nd95460_036.py`.

Verificaciones ejecutadas: no duplicado; sumas porfactura yneto40007,25 exactos; totalfiscal48408,77; errorproporcionalmenor1centavo; clasificaciónheredada;12costosvisibles enpesos;USD0enmotorbimonetarioyenresultados;facturasoriginalesintactas,relacionesconambas,persistenciaporrelectura. No fue necesario modificar vistas.
