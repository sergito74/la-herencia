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
