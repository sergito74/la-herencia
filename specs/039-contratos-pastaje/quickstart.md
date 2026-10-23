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

## Registro de implementación — 22/10/2026 (Claude)

**Migración** (`python -m scripts.migrar_pastaje_039` → `--aplicar`): primer intento revertido completo (CHECK con comparación booleana no válida en T-SQL; corregido). Segundo intento aplicado: 9 tablas, 3 índices, rama `'Pastaje'` en vw_MovimientosCuenta_Base (facturas/ND a Credito, NC a Deuda, como las ventas), `CK_AplicacionesPago_TipoDocumento` + `'Pastaje'`. Gate: vista 24.065 filas, Deuda 2.006.660.639,17 / Credito 1.877.899.205,20 idénticos antes y después. Respaldo verificado `C:/Program Files/Microsoft SQL Server/MSSQL17.SQLEXPRESS/MSSQL/Backup/WC_pastaje_039_20261022_194608_788710.bak`; evidencia `backups/pastaje-039-schema/migration-20261022T224608780431.json` y definición anterior de la vista en la misma carpeta.

**INMAG**: carga histórica 2020-03-01 → 2026-10-21: 967 días con índice, 239 días sin índice publicado (o 0) no guardados. Verificado 25/09/2026 = 4.068,212 (6.316 cab) y 29/09/2026 = 4.241,828 (5.009 cab); 30/09 sin índice. Tarea programada: `backend/scripts/instalar_indice_inmag.ps1` (la instala Sergio una vez; diaria 19 h, recupera 10 días, del 1 al 10 prepara borradores de liquidación sin duplicar).

**IndiceNovillo.CabIngresadas**: 1.026 fechas corregidas (miles con punto); plan con valores previos en `backups/indice-novillo/cabingresadas-plan-20261022.json`.

**Pruebas** (sin conexión a WC: pyodbc bloqueado):
- `python -m pytest tests/test_pastaje_calculo_039.py tests/test_pastaje_inmag_039.py tests/test_pastaje_contrato_039.py tests/test_pastaje_factura_039.py -q` → 31 passed. Cubre escenarios 1–11, 13 (cobrado/saldo simulado), 15 de la tabla.
- Escenario 1: 70 kg; $4.155,02; neto $290.851,40; IVA $61.078,79; total $351.930,19 ✔. Escenario 10: factura A 0002-00000008, CAE 86406417014230, importes exactos, detalle "Servicio de pastaje de 70 Vaquillonas del 25 al 30 de septiembre de 2026" ✔.
- Escenario 17: PDF generado reproduce el contenido y orden de la liquidación de referencia (texto extraído comparado).
- Suite completa backend: 1.431 passed, 5 failed — las mismas 5 fallas preexistentes por datos vivos (auditoría ×2, Jáuregui ×2, tarjetas ×1) registradas en 038; ninguna nueva.
- Frontend: `npx tsc --noEmit` y `npx eslint` de los archivos nuevos sin errores.

**Consolidado de campaña**: `otrosIngresos` (Pastaje neto por establecimiento) en el resultado de campaña; lectura real 2026/2027 = [] (aún sin facturas cargadas).

**US7 / FR-019 — comparación socios (solo lectura, `python -m scripts.comparar_indice_socios_039`)**, informe `backups/pastaje-039-schema/comparacion-indice-socios-20261022.json`. Índice anterior hoy 3.969,528; INMAG hoy 3.926,156.

| Socio | kg guardados | kg con INMAG | Dif. kg | $ hoy índice actual | $ hoy INMAG | Dif. $ |
|---|---|---|---|---|---|---|
| Sergio | 15.125,296 | 15.375,274 | +249,978 | 60.040.285,98 | 60.365.724,27 | +325.438,29 |
| Lucy | 13.901,923 | 14.145,580 | +243,657 | 55.184.072,60 | 55.537.753,79 | +353.681,19 |
| Cond LSC | 2.425,938 | 2.457,410 | +31,472 | 9.629.828,82 | 9.648.175,02 | +18.346,20 |
| Ceci | 26,854 | 27,789 | +0,935 | 106.597,70 | 109.103,95 | +2.506,25 |

Los kg guardados incluyen filas migradas de la planilla Cajas Giamigli (que usaba el índice anterior). **Pendiente aprobación de Sergio (T034)**; no se cambió la valuación.

**Pendientes reales**: T034 (aprobación), T035 (alta de Ganadera San Justo y carga del contrato real con Sergio), recorrido UI completo y mediciones SC-002/SC-003 (T036, la segunda a 30 días de instalada la tarea).

**Revisión de especialistas**: T016a (08/09 frontend/UX) aplicada: pestañas accesibles (`ui/Tabs.tsx`, `?tab=`), KPIs, alertas con texto y enlace para resolver, carga de factura en 3 pasos con comparación y aceptación explícita de diferencias. T024a (06/07 hacienda/finanzas), 6 hallazgos corregidos con pruebas: (1) ND/NC sin liquidación hereda la campaña de su factura; (2) IVA del ajuste = IVA recalculado − IVA liquidado (sin redondeo aparte); (3) ND solo respalda ajustes a favor del campo y NC a favor del cliente (422 si no); (4) texto de factura con una línea por cantidad de cabezas; (5) otros tributos de ARCA en la comparación neto+IVA+otros=total; (6) bajas de crías al pie no restan cabezas cobrables. (7) signo de la rama de cuenta corriente confirmado contra Venta Hacienda (Credito = nos deben). Pruebas 039: 35 passed.

## 22/10/2026 — aprobaciones de Sergio aplicadas
- **T034 (FR-019) aprobado y aplicado**: respaldo verificado `WC_socios_inmag_039_20261022_235724_741610.bak`; 784 movimientos de socios (todos desde 16/03/2020 con kg) revaluados con INMAG a su fecha (kg = 50% importe / INMAG, signo conservado), plan con valores anteriores en `backups/pastaje-039-schema/socios-kg-inmag-plan-20261022.json`. Kg totales: Sergio 15.375,276, Lucy 14.145,580, Cond LSC 2.457,413, Ceci 27,789. Código: valuación y deuda actualizada leen dbo.IndiceINMAG; `cotizaciones_dolar_novillo.py` ya no carga IndiceNovillo (queda histórico) y actualiza el INMAG. Lectura en vivo: deuda actualizada con INMAG 3.926,156 (21/10/2026).
- **Contacto**: Ganadera San Justo S.S. (CUIT 30715943278) dado de alta, IdContacto 5671, tipo Comprador.
- **Tarea programada** "LaHerencia - Indice INMAG" instalada; prueba inmediata resultado 0; próxima corrida 23/10/2026 19:00.
- Pendiente T035: cargar el contrato real, ingreso del 25/09 (DTe), liquidación de septiembre y factura A 0002-00000008 desde la UI.
