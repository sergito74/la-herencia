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
