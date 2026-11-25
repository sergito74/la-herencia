# Registro de aplicación: 052 Módulo Ganadero

## 25/11/2026: dólar de gestión único (T004–T008)
- Ver [auditoria-dolar-20261125.md](auditoria-dolar-20261125.md). Respaldo de la vista en `backups/vw_TC_BNA_PorCompra-antes-20261125.sql`. Commit 9f0b029.

## 25/11/2026: tablas y forrajes (T009–T012, T014)
- **Respaldo verificado:** `C:\Program Files\Microsoft SQL Server\MSSQL17.SQLEXPRESS\MSSQL\Backup\WC_pre_ganaderia_052_20261125_123429.bak` (BACKUP COPY_ONLY + CHECKSUM + RESTORE VERIFYONLY).
- **Script:** `backend/scripts/ganaderia_tablas_20261125.py --aplicar`.
  - Creó 13 tablas `Gan*`.
  - Agregó la columna `Map_CultivoResultado.EsGanaderia`, en 1 para Maíz diferido (2), Sorgo (5), Pastura (7) y Avena (9).
  - Cargó los datos iniciales: categorías 14, alias 24, reglas de forraje 4, calendario 6, reparto de personal 1 (70/20/10), mapa de rubros 32.
- **Resultado de cultivos:** los cultivos ganaderos ya no suman en la campaña. El bloque nuevo `pasaAGanaderia` (cultivos ganaderos + maíz picado para silo) se muestra en la pantalla.
- **Invariante SC-005 verificado con datos reales:** costo agrícola anterior + silo (que antes no figuraba en ningún lado) = costo agrícola nuevo + lo que pasa a Ganadería. Diferencia 0,00.

  | Campaña | Agrícola antes | Agrícola ahora | Pasa a Ganadería | Del cual silo |
  |---|---|---|---|---|
  | 2023/24 | US$ 130.253,81 | US$ 108.635,88 | US$ 21.617,93 | — |
  | 2024/25 | US$ 77.977,35 | US$ 62.389,60 | US$ 22.442,63 | US$ 6.854,88 |
  | 2025/26 | US$ 87.525,37 | US$ 82.251,32 | US$ 5.274,05 | — |

- **Pruebas:** `tests/ganaderia` (8) y `test_resultado_cultivo_resultado.py` (10, ajustado + caso nuevo) pasan. Frontend `tsc` sin errores.
- **Pendiente T013:** `vw_Gan_Costos` (costos de compras imputados a Ganadería). Pasa al inicio de US1.

## 25/11/2026 — T032/T033 stock histórico de hacienda
- Respaldo verificado: `WC_pre_ganaderia_052_20261125_152248.bak` (dos intentos previos fallaron antes de escribir: fecha sin convertir para el driver; no quedó nada aplicado).
- DDL: `GanMovimiento.IdVenta` (int NULL, índice filtrado). Alias nuevo "Vaquillonas 2do servicio" → Vaquillonas 2 dientes.
- 24 recuentos: 23 de la solapa "Stock Hacienda" (origen Planilla, 2016-03-15 a 2023-10-26, La Herencia y San Pedro) y el de "Req Vacunas Oct 26" (origen Acta, 15/10/2026, 393 cabezas; 70 Terneras Miguel de Ganadera San Justo como terceros).
- 245 movimientos Venta, uno por renglón de hacienda de las 146 ventas (los renglones en pesos o sin tipo no son hacienda).
- Quickstart §5: 26/10/2023 La Herencia = 248 vacas, 20 toros, 7 toritos, 133 terneros, 96 terneras ✔; 15/10/2026 terceros = 70 vaquillonas de San Justo ✔. §6: venta 0003-00010318 = 2 vacas, 880 kg ✔.
- Los stocks al 31/03 de los mails al Estudio no se importaron como base (2021 solo trae totales y 2023 suma los dos campos); 31/03/2023 en el sistema: 263 vacas (Estudio 260), 13+3 = 18 toros (Estudio 16).
- Quedan en negativo, a la vista: San Pedro "Vacas conserva" −4 (la venta las clasifica como conserva y el recuento como vacas) y San Pedro Toros −2 hoy (ventas posteriores al último recuento de 10/2023; falta el recuento de cierre del campo, 2025).
- 25/11 (Sergio): las ventas de "Vacas conserva" descuentan de Vacas (alias Vacas conserva → Vacas; 20 ventas resincronizadas). San Pedro cerrado en cero el 10/07/2025 con la venta de los últimos 2 toros (00004-00001355): recuento 25, origen Cierre. Hoy no queda ningún negativo.
- 25/11 (Sergio): los 2 toros de la NC Wallace 00004-00001355 (10/07/2025) son los mismos que salieron con el último DTe a la feria (liquidación 000003-00024837, 11/06/2024). Regla general: las notas de crédito y débito no mueven stock (10 movimientos de 9 notas eliminados). Cierre de San Pedro movido al 11/06/2024: existencia 0 y diferencia sin explicar 0.

## 25/11/2026 — Actas de vacunación 2024–2026 (La Herencia)
- Respaldo verificado: `WC_pre_ganaderia_052_20261125_164612.bak`.
- Recuentos origen Acta (Toros/toritos juntos → Toros): 05/04/2024 FUNDEBO 00086593 = 380 (182 vacas, 24 toros, 94 terneros, 80 terneras); 22/04/2025 00090515 = 240 (113, 11, 54, 62); 03/12/2025 00092257 = 265 (menores 149 + observación "aparte 107 vacas y 9 toros"; terneros/terneras con corrección a mano 48/46, se tomó lo escrito 49/50); 09/04/2026 00094112 = 259 (103, 7, 49, 50, 50 vaquillonas).
- No cargada: 13/11/2024 00088584 (solo menores: 2 toritos, 55 terneros, 60 terneras, 48 novillitos; sin vacas ni toros).
- Reglas generales nuevas:
  - Notas de crédito/débito: solo mueven stock los renglones con cabezas negativas (NC que anula una liquidación reemplazada: Elordi 00002-00005483, CUT WEST 00002-00000003, J y M 0003-00013212). Con cabezas positivas son ajuste de precio (Wallace 00004-00001355).
  - Una salida mayor que la existencia de su categoría toma el faltante de la categoría más cercana del mismo sexo y menor orden (vacas preñadas ← vacas; novillos ← novillitos ← terneros): es el cambio de categoría que el recuento no registró.
  - Antes del primer recuento del campo no hay existencia (antes daba negativos desde 2011).
  - Renglón "Unidades" con Peso Total < Cantidad y kg/cabeza verosímil (40–1200) = cargado al revés (PDF 0003-00006904: 1 ternera de 170 kg cargada como 170 unidades).
- Resultado: 239 movimientos de venta; negativos restantes solo 01–04/2025 (Novillos −2, Vaquillonas −4). 26/10/2023 sigue = planilla.
- Para Sergio: venta 0120-00012139 Monasterio Tattersal (29/12/2023) = 50 vacas preñadas de Tapalqué (guía TAPALQUE, RENSPA 01.111.0.00467/13) según el PDF, cargada con establecimiento La Herencia y como 50 vacas + 50 terneros/as a $350.000. Importes correctos; corregir campo y renglones no cambia saldos.
- 25/11 (Sergio confirmó con el PDF): venta 0120-00012139 Monasterio Tattersal = 50 vacas preñadas a $700.000 (25 Rodriguez + 25 Reinaudo), La Herencia. Venía heredada de la base original como 25 vacas + 25 vacas conserva + 50 terneros/as a $350.000. Corregida en WC a 2 renglones; bruto $35.000.000 antes = después. Respaldo `WC_pre_ganaderia_052_20261125_170642.bak`.

## 25/11/2026 — Auditoría de las 146 ventas de hacienda contra sus PDF
- 101 PDF con texto (cruce automático renglón por renglón) + 45 escaneados (leídos uno por uno). Importe bruto: coincide en todos.
- Regla de stock ajustada: un comprobante con importe negativo devuelve hacienda solo si anula una venta anterior del mismo consignatario por el mismo importe; si no, es diferencia de precio (ND Frigal 0001-00008954 por diferencia de precio, cargada como liquidación de 2 vacas).
- Pares liquidación reemplazada + nota que la anula: todos cerrados (Gregec, Elordi, CUT WEST, J y M 2024, J y M 10/2025).
- Errores de carga hallados (sin corregir, esperan a Sergio): ver mensaje del 25/11 (Frigal 0001-00008285 25 novillos cargados como 78; Las Heras 0001-00005418 23 terneros/as cargados como 28; J y M 0003-00006904 1 ternera de 170 kg cargada como 170 unidades; categorías: J y M 0003-00000196 vaquillona como ternera, Senosiain 0003-00000001 y Pavón Arriba 00003-00000012 vaca como vaca conserva, Rioplatense 00003-00000015 novillitos como novillos; NC bonificación J y M 0002-00000033 y Wallace 00004-00001355 cargadas con renglones de hacienda).
- 25/11 (Sergio autorizó 1–6 y agregar Novillitos): respaldo `WC_pre_ganaderia_052_20261125_180934.bak`. Corregidos: Frigal 0001-00008285 78→25 cab; Las Heras 0001-00005418 terneras 28→23; J y M 0003-00006904 renglón 170 u × $147,0588 → 1 cab × $25.000 (170 kg; bruto +$0,002 por redondeo del precio viejo); J y M 0003-00000196 ternera→vaquillona; Senosiain 0003-00000001 y Pavón Arriba 00003-00000012 vaca conserva→vacas. Nuevo [Tipo Hacienda] 10 "Novillitos" (GanCategoria Novillitos apunta a él); Rioplatense 00003-00000015 novillos→novillitos. Brutos iguales.
- 25/11 (Sergio OK 8, 9, 10): respaldo `WC_pre_ganaderia_052_20261125_181502.bak`. Frigal 0001-00008954 pasa a Nota de Débito (la vista de saldos no usa el tipo; importe igual). Resultado ganadero: NC del consignatario con importe positivo = "Bonificaciones del consignatario" (menos comercialización), no venta ni kg/cabezas (J y M 0002-00000033 $4.540,80 en 2015/16; Wallace 00004-00001355 $387.495,88 en 2025/26). Las 7 liquidaciones Frigal 2011–2014 quedan con consignatario Ferias del Centro por decisión de Sergio (el intermediario real fue J y M de la Serna).

## 25/11/2026 — Inventario en el resultado (FR-008/FR-020 etapa 1, estimado)
- Tabla GanValuacionRegla (respaldo `WC_pre_ganaderia_052_20261125_182540.bak`): Toros = 500 kg × coeficiente 1 (toro usado = 500 kg de novillo).
- Valor = cabezas × kg × INMAG del día × coeficiente de la categoría (mediana $/kg ÷ INMAG de nuestras ventas desde 2016; sin 5 ventas, la categoría de origen) × (1 − % gastos de venta del ejercicio). Coeficientes 25/11: terneros/as 1,15; vaquillonas 0,93; novillos/toritos 0,87; vacas 0,61; toros por regla.
- Existencia a una fecha: recuento más cercano, también el posterior dentro de 120 días deshaciendo movimientos (31/03/2025 sale del acta 22/04/2025, no del acta 2024 menos ventas sin parición).
- Indicadores: kg producidos = kg vendidos + kg cierre − kg inicio; kg/ha; costo directo por kg; EV promedio y EV/ha.
- Pendiente de dato: traslado La Herencia → San Pedro de 2020 no registrado (2019/20 de La Herencia sola da pocos kg producidos; todos los campos da 35.312 kg).
