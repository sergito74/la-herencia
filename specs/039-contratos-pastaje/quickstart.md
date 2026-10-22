# Quickstart / validación — 039 Contratos de pastaje

## Prerrequisitos
- Backend y frontend del proyecto; base WC (nunca LaHerencia). Migración con respaldo COPY_ONLY verificado (patrón `migrar_gestion_cajas_038.py`: sin argumentos inspecciona, `--aplicar` escribe).
- Tests unitarios/contrato con `pyodbc.connect` bloqueado (patrón `tests/cajas_038_helpers.py`).

## Escenarios
| # | Escenario | Resultado esperado |
|---|---|---|
| 1 | Cálculo septiembre 2026 San Justo (70 vaquillonas desde 25/09, 5 kg, INMAG 4.068,212 / 4.241,828) | 70 kg; $4.155,02; neto $290.851,40; IVA $61.078,79; total $351.930,19 |
| 2 | Octubre 2026 completo (31 días, 70 cab) con INMAG de todos los días con remate | kg = 70×5×31/31 = 350; precio = promedio simple de octubre |
| 3 | Egreso de 10 cab el 15/10 | 70 cab del 1 al 14 (14 días) + 60 del 15 al 31 (17 días) |
| 4 | Muerte el día X | ese día no se cobra |
| 5 | Nacimiento y destete | crías sin cobro hasta destete |
| 6 | Recuento con diferencia | alerta, cabezas sin cambio |
| 7 | Mes sin ningún INMAG en días con hacienda | liquidación bloqueada, carga manual habilita |
| 8 | INMAG: actualización de 25–30/09 | 2 filas (25 y 29); 30/09 sin fila; reintento no duplica |
| 9 | Corrección de índice tras confirmar | liquidación fija; alerta diferencia; ajuste PDF |
| 10 | Leer factura 20261006_Giamigli.pdf | A 0002-00000008, 06/10/2026, CAE 86406417014230, neto/IVA/total exactos, sin diferencias con liq. de septiembre |
| 11 | Cargar la misma factura dos veces | 409 duplicado |
| 12 | Factura en cuenta corriente | una sola vez en `vw_MovimientosCuenta_Base`, saldo $351.930,19 hasta cobro |
| 13 | Cobro por banco con retención | aplicación `Pastaje`, saldo = total − cobrado − retención |
| 14 | Migración sin datos nuevos | 24.065+ filas de la vista con mismos totales debe/haber |
| 15 | Rol Lectura | consulta OK, escrituras 403, botones ocultos |
| 16 | Resultado campaña 2026/27 | "Otros ingresos — Pastaje" $290.851,40 (neto) en La Herencia |
| 17 | PDF de liquidación | mismo contenido/estructura que la liquidación de referencia, guardado en la carpeta del contrato |

## Comandos (a completar en implementación)
- `python -m pytest tests -q -k 039`
- `npx tsc --noEmit`
- `python -m scripts.migrar_pastaje_039` (inspección) / `--aplicar`
- `python -m scripts.indice_inmag --desde 2026-09-01`
