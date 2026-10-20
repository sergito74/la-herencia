# Finales de soja y aplicaciones — registradas20/10/2026

Por autorización de Sergio, dos ajustes fiscales cargados en Venta Granos:

| IdVenta | COE | Neto pesos | Original |
|---|---|---:|---|
| 1231 | 330226576206 | 75.227,50 | 330223253060/venta177 |
| 1232 | 330226576221 | 4.502,50 | 330223253039/venta1230 |

Fecha04/09/2024, soja2022/2023, **cantidad0**, precio de referencia$100.000/t y ajuste porimporte `Pago a Cuenta (DRC)`; IVA0 según pie fiscal. No se agregan kilos ni se modifica ninguna de las dos liquidaciones iniciales. Los originales completos de2páginas se guardaron y vincularon en `Dropbox/Giamigli de Bolivar SA/Ventas/04 2024 - 03 2025/20240904_BayaCasal_LC330226576206.pdf` y `...LC330226576221.pdf`. Cada ajuste referencia suCOE original enConcepto. Recuperan reservas que se habían descontado; resultados deSoja recuperan$79.730 sin nueva producción.

## Aplicaciones según comprobantes reales

**CA115924,09/01/2025:** usa$2.828,14 deLC221 junto al cheque80553793. Se reimputa completo el cheque recibido18 ($8.137.687,20), ambasNC y las dos facturas a las que refiere el comprobante. Orígenes:

- NC116557$129.269,81: distribuida por sus diferencias explícitas deFC389331/389893 másIVA21%, créditos$20.770,93/$108.498,88.
- Cheque18: $1.308.009,27 aFC389331 y$6.829.677,93 aFC389893.
- LC221:$2.828,14 aFC389893.

Totales fiscales aplicados$1.328.780,20/$6.941.004,95 de ambas facturas. Anuladas lógicamente9aplicaciones previas incidentes incorrectas (incluíanNC120722 ypagos ajenos); otras fuentes liberadas conservan registros y demás aplicaciones. Las pequeñas diferencias entre capacidadSQL y documento del proveedor son pendientes de carga/valuación, no deuda externa ni motivo para volver a imputar pagos aleatorios.

**CA123088,22/05/2025:** LC206$75.227,50+remanenteLC221$1.674,36=$76.901,86 aFC401515, más laNC120722 porimporte reconocido$16.248,54. Total$93.150,40, equivalente aUSD83,17 alTC original de lafactura1120. LaNC fiscal es$16.252,67; **$4,13 quedan sin aplicar**, porque la observación y el resumen reconocen neto$13.427,83+IVA$2.820,71, no neto fiscal$13.431,96. Se conserva el fiscal y se documenta esta diferencia sin ajuste inventado.

Se crearon8aplicaciones documentales entre enero y mayo, que consumen exactamente ambas finales y todo el cheque. La aplicación histórica del cheque se corrigió a30/12/2024 (FechaEndoso), segúnPDF enviado ese día, en lugar de27/12 (emisión); su importe, emisorCargill y receptorBayá intactos. No se reconoce otra vez retención183: el proveedor no la incluyó en estos comprobantes.

## LibroUSD con fecha real

ValuacionProveedor ampliada con fecha/comprobante opcionales. FuenteLC206/221 no anticipa dólares en septiembre2024: se registra efecto conjunto **USD83,17 el22/05/2025, CA123088**, con pesos0 en ese evento. El reparto interno entre las dos fuentes es proporcional al saldo de origen ($75.227,50/$1.674,36): USD81,36/USD1,81; el comprobante externo acredita el total, no esos subtotalesUSD separados. Se agrupan para presentar un solo evento externo.

Cheque18 permanece enpesos hasta **09/01/2025, CA115924, USD7913,67**. Su fecha de recepción/endoso permanece30/12/2024. No duplicar dólares por convertir el cheque en la recepción y de nuevo al aplicarlo. Los movimientos derivados no agregan otro pago en pesos ni cambian los costos.

Verificados dos eventosUSD con fechas/documentos eimportes exactos desde la carga real de la cuenta; originales177/1230 intactos, finales suman$79.730/0kg, todas sus aplicaciones consumen su capacidad y cheque completo. Tres pruebas nuevas con datos simulados pasaron junto a16bimonetarias existentes (19total); pruebas fallaron antes de implementar el contrato. Respaldo verificado `WC_baya-finales-soja-036_20261020_095711_943676.bak`; script `backend/scripts/baya_casal_finales_soja_036.py`. Auditoría local `backups/baya-conciliacion-20261019/finales-soja-alta-*.json` contiene fuentes, hashPDFs, originales,8aplicaciones yvaluaciones. SinFIFOglobal ni cierre de la cuenta.
