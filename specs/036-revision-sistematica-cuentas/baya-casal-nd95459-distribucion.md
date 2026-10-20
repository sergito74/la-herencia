# ND0020-00095459: carga y distribución aplicada

Compra2143523741, fecha/vencimiento02/08/2023, documentoenpesos marcadoAjustaTipoCambio. Neto **$28.971,71**, IVA21% **$6.084,06**, total **$35.055,77**. PDFvinculado. Sin nueva deudaUSD ni pagos/FIFO.

El original combina incremento yreducción:

| Factura | Diferencia neta$ | Cálculo original |
|---|---:|---|
|316797|+36.030,87|415.303,17−379.272,30|
|332563|−7.059,16|135.206,09−142.265,25|
|Total|28.971,71||

Se respeta ese reparto. Dentro de cada factura, proporción delnetoUSD de susrenglones, sinIVA, por mayoresrestos a centavos.57renglonesfinancieros, cantidad1ARS, clasificación deproducto/cultivo/centro/rubro/campañaheredada. Lasfacturasoriginales no se tocaron. Una campaña contexto2025/2026 eId20NoAplica se resolvió comoId24 enlaND, sinmodificar elorigen.

## Verificación del signo de costos

La vista `vw_ResultadosCultivo_CostosBase` convertía valores en absolutos, loque hacía positiva la reducción incluida en estaND. Se ajustó exclusivamente el caso de ND con marcaAjustefinanciero: mantener monto firmado ySigno−1si su renglón es negativo. LasNCmantienen su convención previa; otros documentos no cambian. Antesdelalta no existían NDfinancierasnegativas: elprimer cambio no alteraba costos deotros documentos. La corrección quedó en el script deestaND, con definiciónSQLantes/después enauditoría.

Se verificó tanto el monto firmado como el cálculo que consume la pantalla `ABS(monto)×Signo`: ambos dan **$28.971,71** netos, con reduccióncorrecta de$7.059,16. Tambiénsecomprobóque laNC100961siguiera reduciendo$75.012,03. Se probaron6combinacionesdesigno conSELECTsobrevalores ficticios,sin escriturasdeprueba. La parteUSDdelanota ydecostos sigueen0.

| Línea origen | Producto | Cultivo/destinoId | Campaña | Neto diferencia$ | LíneaND |
|---|---|---|---|---:|---|
| 2141373836 | CLETODIM 24% SELECT X 10 L | 6 | 2022/2023 | 1890.06 | 2141390173 |
| 2141373837 | GLIFOSATO 54% FULL II SIGMA X 20 L | 14 | 2023/2024 | 666.30 | 2141390174 |
| 2141373838 | CARFENTRAZONE 40% SHARK X 1 L | 6 | 2023/2024 | 941.70 | 2141390175 |
| 2141373839 | S-METOLACLORO 96% STRIM X 20 L | 7 | 2022/2023 | 3860.84 | 2141390176 |
| 2141373840 | BIFENTRIN 25% X 1 L | 7 | 2024/2025 | 208.22 | 2141390177 |
| 2141373841 | IMIDACLOPRID 35% X 5 L | 14 | 2024/2025 | 306.50 | 2141390178 |
| 2141373842 | LAMBDA CIALOTRINA 25% PULSAR GOLD micro encapsulad | 14 | 2023/2024 | 390.90 | 2141390179 |
| 2141373843 | ACEITE METILADO ARN EBC X 20 L | 6 | 2022/2023 | 519.71 | 2141390180 |
| 2141373845 | SULFATO DE AMONIO X 20 L | 7 | 2022/2023 | 88.84 | 2141390181 |
| 2141373847 | AZOXI 20% CIPRO 8% LANFOR X 5 L | 6 | 2025/2026 | 168.80 | 2141390182 |
| 2141374286 | CLETODIM 24% SELECT X 10 L | 6 | 2023/2024 | 205.44 | 2141390183 |
| 2141374294 | S-METOLACLORO 96% STRIM X 20 L | 8 | 2024/2025 | 496.39 | 2141390184 |
| 2141374315 | LAMBDA CIALOTRINA 25% PULSAR GOLD micro encapsulad | 11 | 2022/2023 | 236.91 | 2141390185 |
| 2141374316 | LAMBDA CIALOTRINA 25% PULSAR GOLD micro encapsulad | 7 | 2022/2023 | 319.82 | 2141390186 |
| 2141374317 | ACEITE METILADO ARN EBC X 20 L | 8 | 2023/2024 | 53.13 | 2141390187 |
| 2141374443 | CRIPTON (trifloxistrobina 15% protioconazol 17,5%) | 14 | 2023/2024 | 3586.91 | 2141390188 |
| 2141374595 | ACEITE METILADO ARN EBC X 20 L | 12 | 2023 | 83.62 | 2141390189 |
| 2141374596 | ACEITE METILADO ARN EBC X 20 L | 13 | 2023 | 38.19 | 2141390190 |
| 2141374597 | ACEITE METILADO ARN EBC X 20 L | 6 | 2022/2023 | 224.66 | 2141390191 |
| 2141374601 | COADY SILICONADO ARN EBC X 1 L | 7 | 2022/2023 | 181.36 | 2141390192 |
| 2141374602 | COADY SILICONADO ARN EBC X 1 L | 6 | 2022/2023 | 230.92 | 2141390193 |
| 2141374603 | COADY SILICONADO ARN EBC X 1 L | 12 | 2023 | 85.95 | 2141390194 |
| 2141374604 | COADY SILICONADO ARN EBC X 1 L | 13 | 2023 | 39.25 | 2141390195 |
| 2141374607 | AZOXI 20% CIPRO 8% LANFOR X 5 L | 6 | 2022/2023 | 1519.16 | 2141390196 |
| 2141374613 | GLIFOSATO 54% FULL II SIGMA X 20 L | 7 | 2022/2023 | 4524.66 | 2141390197 |
| 2141374614 | GLIFOSATO 54% FULL II SIGMA X 20 L | 6 | 2022/2023 | 4508.81 | 2141390198 |
| 2141374615 | GLIFOSATO 54% FULL II SIGMA X 20 L | 12 | 2023 | 3263.20 | 2141390199 |
| 2141374616 | GLIFOSATO 54% FULL II SIGMA X 20 L | 13 | 2023 | 1362.46 | 2141390200 |
| 2141374617 | IMIDACLOPRID 35% X 5 L | 6 | 2022/2023 | 842.87 | 2141390201 |
| 2141374620 | LAMBDA CIALOTRINA 25% PULSAR GOLD micro encapsulad | 7 | 2022/2023 | 359.72 | 2141390202 |
| 2141374621 | LAMBDA CIALOTRINA 25% PULSAR GOLD micro encapsulad | 6 | 2022/2023 | 458.03 | 2141390203 |
| 2141374622 | LAMBDA CIALOTRINA 25% PULSAR GOLD micro encapsulad | 12 | 2023 | 170.48 | 2141390204 |
| 2141374623 | LAMBDA CIALOTRINA 25% PULSAR GOLD micro encapsulad | 13 | 2023 | 77.85 | 2141390205 |
| 2141374912 | COADY SILICONADO ARN EBC X 1 L | 14 | 2023/2024 | 244.31 | 2141390206 |
| 2141374913 | COADY SILICONADO ARN EBC X 1 L | 13 | 2023 | 73.29 | 2141390207 |
| 2141374916 | GLIFOSATO 54% FULL II SIGMA X 20 L | 13 | 2023 | 999.45 | 2141390208 |
| 2141375334 | CRIPTON (trifloxistrobina 15% protioconazol 17,5%) | 16 | No Aplica | 818.07 | 2141390209 |
| 2141375338 | ACEITE METILADO ARN EBC X 20 L | 14 | 2023/2024 | 43.12 | 2141390210 |
| 2141375367 | COADY SILICONADO ARN EBC X 1 L | 12 | 2023 | 104.90 | 2141390211 |
| 2141375368 | COADY SILICONADO ARN EBC X 1 L | 12 | 2023 | 206.30 | 2141390212 |
| 2141375369 | COADY SILICONADO ARN EBC X 1 L | 11 | 2023/2024 | 119.93 | 2141390213 |
| 2141375370 | COADY SILICONADO ARN EBC X 1 L | 6 | 2023/2024 | 288.82 | 2141390214 |
| 2141375371 | COADY SILICONADO ARN EBC X 1 L | 10 | 2023/2024 | 37.41 | 2141390215 |
| 2141375372 | COADY SILICONADO ARN EBC X 1 L | 8 | 2023/2024 | 38.59 | 2141390216 |
| 2141375373 | COADY SILICONADO ARN EBC X 1 L | 13 | 2021 | 85.51 | 2141390217 |
| 2141375374 | COADY SILICONADO ARN EBC X 1 L | 6 | 2023/2024 | 179.83 | 2141390218 |
| 2141375375 | COADY SILICONADO ARN EBC X 1 L | 10 | 2023/2024 | 38.11 | 2141390219 |
| 2141375575 | CLETODIM 24% SELECT X 10 L | 8 | 2023/2024 | 369.79 | 2141390220 |
| 2141375583 | S-METOLACLORO 96% STRIM X 20 L | 8 | 2023/2024 | 34.88 | 2141390221 |
| 2141375584 | S-METOLACLORO 96% STRIM X 20 L | 11 | 2023/2024 | 20.28 | 2141390222 |
| 2141375599 | LAMBDA CIALOTRINA 25% PULSAR GOLD micro encapsulad | 11 | 2023/2024 | 41.56 | 2141390223 |
| 2141375600 | LAMBDA CIALOTRINA 25% PULSAR GOLD micro encapsulad | 6 | 2023/2024 | 91.49 | 2141390224 |
| 2141375601 | LAMBDA CIALOTRINA 25% PULSAR GOLD micro encapsulad | 8 | 2023/2024 | 71.50 | 2141390225 |
| 2141375602 | LAMBDA CIALOTRINA 25% PULSAR GOLD micro encapsulad | 10 | 2023/2024 | 32.36 | 2141390226 |
| 2141375998 | BIFENTRIN 25% X 1 L | 12 | 2024 | 96.98 | 2141390227 |
| 2141377092 | BIFENTRIN 25% X 1 L | 11 | 2024/2025 | 82.73 | 2141390228 |
| 2141374909 | Kit. Sistiva | 14 | 2023/2024 | -7059.16 | 2141390229 |

Respaldoantesdealta/vista: `C:\Program Files\Microsoft SQL Server\MSSQL17.SQLEXPRESS\MSSQL\Backup\WC_baya-nd95459-distribucion-036_20261019_235110_486878.bak`. RespaldoantesdeajustarSignoparaconsumidores: `C:\Program Files\Microsoft SQL Server\MSSQL17.SQLEXPRESS\MSSQL\Backup\WC_baya-nd95459-signoresultado-036_20261019_235217_050571.bak`.

Auditorías: `backups/baya-conciliacion-20261019/nd95459-alta-distribucion-20261019_235111_463307.json` y `backups/baya-conciliacion-20261019/nd95459-signoresultado-20261019_235218_375334.json`. Script: `backend/scripts/baya_casal_nd95459_036.py`.

Confirmadas:suma porfactura,totalneto,totalfiscal,clasificaciónheredada,persistencia,relacionescondosfacturas,origensincambios,USD0ymontosfirmadosenresultados. Los informes globalesprevios son históricos hasta recálculocompleto.
