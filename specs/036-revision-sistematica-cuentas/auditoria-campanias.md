# Auditoría de vínculos de campaña

Procedimiento solicitado por Sergio el 20/10/2026 tras encontrar reiteradamente campañas escritas sin `IdCampaña`. El texto por sí solo no garantiza inclusión en los resultados filtrados por identificador.

## Ejecutar

Desde `C:\dev\LaHerencia\backend`, PowerShell:

```powershell
$env:PYTHONPATH='.'
.venv/Scripts/python.exe -m scripts.auditar_campanias_036
```

Solo lectura de WC. No cambia asignaciones, no ejecuta FIFO ni modifica importes. Genera JSON y CSV con fecha en `backups/auditoria-campanias/`, fuera de Git. Incluye identificadores de renglón/documento/contacto, texto actual, identificador actual y candidatos del catálogo. Cobertura y cantidades examinadas quedan en el JSON.

## Cobertura y clasificación

Revisa todas las compras, de todos los contactos y fechas, y labores de maquinaria propia. Son las tablas operativas verificadas que conservan ambos campos. Excluye respaldos y resúmenes derivados. Las ventas de granos y LibroImputaciones almacenan texto sin este mismo par de campos; no corresponde denunciarlas por falta de un identificador que su modelo no tiene. Las tablas que solo conservan identificador requieren otra auditoría de referencias, fuera de este procedimiento.

Clasifica sin inferir campañas por fecha, cultivo o proveedor:

- `falta_vinculo`: texto reconocido y único con identificador nulo.
- `no_aplica_sin_vinculo`: texto No Aplica sin vínculo, separado de campañas productivas.
- `texto_vinculo_discordantes`: ambos existen pero corresponden a nombres distintos.
- `identificador_inexistente`: referencia ausente del catálogo.
- `texto_desconocido` / `texto_ambiguo`: sin coincidencia o con varias coincidencias.
- `sin_texto` / `sin_asignacion`: falta texto o faltan ambos datos. No necesariamente son errores: pueden ser repartos pendientes o ajustes sin cultivo.

Solo elimina espacios exteriores y compara sin distinguir mayúsculas; no equipara campañas anuales y partidas (2023 es distinto de 2022/2023).

## Revisar y corregir

1. Ejecutar antes de cerrar una conciliación, después de importaciones/correcciones masivas de imputación y antes de validar resultados por campaña.
2. Agrupar por documento y contacto. Revisar primero vínculos faltantes de campañas productivas; corroborar reparto, destino y evidencia. La coincidencia textual única es candidata, no autorización automática.
3. Revisar discordancias contra el documento y la imputación aprobada. Especial atención a identificador 20 (No Aplica): puede ser intencional; no sustituirlo automáticamente.
4. Conservar No Aplica y ajustes sin destino productivo cuando estén justificados. Documentar excepciones por identificador de renglón, motivo y evidencia. El detector seguirá mostrándolas; no existe lista persistida de exclusiones automáticas.
5. Para corregir: respaldo verificado, foto de datos previos, transacción con control de concurrencia, actualización acotada de vínculos aprobados y verificación de importes/cantidades/destinos sin cambios. Conservar auditoría antes/después para revertir exactamente los campos cambiados.
6. Repetir el informe y comprobar que desaparezcan los casos corregidos; verificar en la vista de costos el identificador de campaña y sus importes. No suponer que toda anomalía afecta costos: el renglón puede no integrar esa vista.

## Primera ejecución: 20/10/2026, después de corregir FC320049

- 15.927 renglones de compras y 55 labores examinados.
- 41 vínculos faltantes en 13 documentos de 7 contactos, todos distintos de Bayá (515, 562, 217, 258, 4663, 634, 228).
- 13 discordancias en 11 documentos de 3 contactos; todas tienen identificador 20, No Aplica, y requieren corroboración individual.
- 199 No Aplica sin vínculo, separados de las campañas productivas.
- 1 sin asignación: línea de redondeo de FC316792 de Bayá; no asignar a un cultivo sin fundamento.
- 0 anomalías en labores. Total de señales: 254; no equivale a 254 errores confirmados.
- Informe: `backups/auditoria-campanias/auditoria-20261020_105802.json` y CSV homónimo. No se aplicaron correcciones generales.

## Corrección puntual de FC0020-00320049

Script `backend/scripts/baya_casal_fc320049_036.py`: precio de 9.488 kg de urea de USD0,62 a USD0,6218 según original; nueve vínculos completados por coincidencia exacta con el catálogo, sin cambiar reparto, cantidades, destinos ni otros precios. Total verificado USD19.375,91; nueve líneas verificadas con campaña en `vw_ResultadosCultivo_CostosBase`.

Respaldo verificado: `WC_baya-fc320049-036_20261020_105801_355367.bak`. Foto antes/después y hash del PDF en `backups/baya-conciliacion-20261019/fc320049-20261020_105802.json`. Script idempotente: segunda ejecución valida estado y no escribe.

## Lote A — vínculos faltantes (20/10/2026)

Causa raíz: `compras/repository.py` (alta y edición) guardaba solo el texto `Campaña`, nunca `IdCampaña`. Corregido: `_resolver_defaults_linea` resuelve el id por coincidencia exacta única del catálogo y ambos INSERT lo guardan; texto desconocido queda sin id (el auditor lo sigue mostrando). Pruebas `tests/test_compras_campania_id.py`.

Datos: `scripts/campanias_lote_a_036.py` completó los 41 renglones (13 documentos: Allianz, Fideicomiso La Esperanza, FEDEA, Cargill —ND/factura de la tarjeta 27/04/2023 que copian la clasificación de las facturas que ajustan—, San Cristóbal, Aguilar, Silva Rossi). Texto, importes, cantidades, destinos y rubros sin cambio; los 41 entran en `vw_ResultadosCultivo_CostosBase`. Respaldo `WC_campanias-lote-a-036_20261020_144628_851184.bak`. Auditoría posterior: `falta_vinculo` = 0.

## Lote B — discordancias (resuelto 20/10/2026)

13 renglones migrados de Access (texto 2025/2026 o 2026, `IdCampaña` 20 No Aplica), destino productivo, USD 1.040,28 hoy imputados a No Aplica. Evidencia de órdenes solo para Mulan (Pastura 2026) y Coady siliconado (Soja 2025/26); los demás no tienen producto vinculado.

Decisión de Sergio: vincular según el texto. `scripts/campanias_lote_b_036.py` pasó los 13 renglones al IdCampaña del texto; importes y destinos sin cambio, los 13 en la vista de costos (USD 1.040,28 salen de No Aplica). Respaldo `WC_campanias-lote-b-036_20261020_144838_816034.bak`. Auditoría posterior: solo quedan `no_aplica_sin_vinculo` 199 (195 destino General, 4 Stock: ninguno productivo) y `sin_asignacion` 1 (redondeo FC316792, excepción).

## Control para nuevas cargas (20/10/2026)

- App: `compras/repository.validar_compra` rechaza (400) un renglón con campaña escrita que no existe en el catálogo o cuyo IdCampaña no corresponde al texto; el alta/edición guarda el IdCampaña resuelto.
- Base WC: trigger `dbo.trg_Det_Compras_Campania` (AFTER INSERT, UPDATE) rechaza todo renglón con texto de campaña sin el IdCampaña que le corresponde; frena también scripts. Creado por `scripts/control_campania_det_compras_036.py`, que antes completó IdCampaña 'No Aplica' en los 199 renglones con ese texto (aprobado por Sergio). Probado: cambios inválidos rechazados y revertidos.
- Auditoría posterior: solo queda `sin_asignacion` 1 (redondeo FC316792, sin texto ni id: excepción).

## Campañas válidas según el plan agrícola (20/10/2026)

Decisión de Sergio: en la carga de compras solo se ofrecen y aceptan combinaciones destino + campaña válidas en `PlanAgricola` (destino↔cultivo por `Map_CultivoResultado`):
- destino de un cultivo → solo las campañas planificadas para ese cultivo (sin No Aplica);
- General → solo No Aplica;
- Stock, grupos (Cultivo Invierno/Verano, Verdeos) y Rye Grass → cualquier campaña del plan + No Aplica.

Backend: `campanias_validas_por_destino()` (catálogo `campañasPorDestino` en `/api/compras/filtros`) y `validar_compra` rechaza (400) combinaciones fuera del plan; al editar se conservan las combinaciones que la compra ya tenía guardadas. Frontend: la grilla filtra el selector por destino (`components/compras/campanias.ts`), limpia la campaña si se cambia a un destino donde no corresponde, descarta campañas pegadas fuera del plan y ya no permite crear campañas desde la compra (se planifican primero). Hoy Cebada no tiene campañas planificadas y Soja primera no figura en 2024/25.

## Renglones fuera del plan agrícola (20/10/2026)

Medición con la regla nueva: 46 renglones (USD 70.222,87) con destino + campaña fuera del plan.
- Correcciones evidentes aprobadas (`scripts/campanias_plan_evidentes_036.py`, 9 renglones): girasol PENDIENTE 56078 General→Girasol 2026/27; Pérez maíz diferido →2024/25; Sudol sorgo →2025/26; Nación Seguros 63288 soja segunda →2022/23; Avena 2020/2021 → 2020 (jun-2020) y 2021 (dic-2020, may-2021). Respaldo `WC_campanias-plan-evidentes-036_20261020_151747_970358.bak`.
- Plan agrícola completado (`scripts/plan_agricola_faltantes_036.py`, 9 filas, aprobado): Sorgo 2026/27 9A; Avena 2015 6B/6C/8A; Avena 2017 10A/10B; Cebada 2015/16 2A/5A/5B. Respaldo `WC_plan-agricola-faltantes-036_20261020_152401_453668.bak`.
- **Excepciones**: 16 renglones de campañas 2009/10–2013/14 (USD 61.459,44), anteriores al plan cargado (empieza 2015/16), aprobado por Sergio; Cebada 2026/27 Santos FC 00001-00000053 anulada por NC 00001-00000006 (neto USD 2,17 de tipo de cambio), no hubo cebada.
- Sin decidir: atrazina Cargill 1126-00014152 (may-2020, Sorgo No Aplica, USD 0) y voleo rye grass Yanquelen 00002-00000020 (jul-2022, Pastura 2021/2022, USD 143,64).
