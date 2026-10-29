# Validación Rutas Sur — 29/10/2026

## Estado y contexto compartido

Sergio autorizó corregir lectura automática, controles de contactos y quitar Corresur como proveedor separado. Durante el primer tramo otro proceso restauró los archivos; se detuvo sin escrituras en WC. Sergio pidió esperar y después autorizó continuar indicando que la otra sesión quedó pausada. Los cambios fueron recuperados antes de retomar y revisados.

## Evidencia y verificaciones

- PDF originales revisados visualmente con pypdfium2 y texto con pdfplumber. No se modifican ni renombran originales.
- Factura 0002-01210978: emisión 28/10/2026, neto $1.280,02, IVA $268,80, total $1.548,82.
- Factura 0002-01348415: emisión 29/10/2026 (aunque el nombre de descarga dice 28/10), neto $1.476,94, IVA $310,16, total $1.787,10.
- WC: solo existe contacto 2657 Rutas Sur Atlantico S.A., CUIT 30719454190; no existe contacto Corresur. Compras existentes 2143525172 y 2143525173, totales recalculados coincidentes al centavo con originales. Portales_Documentos 220/221 y DocumentosNuevos 49/50 eran los registros a reparar. DescargaPeajes_Documentos no tenía filas Corresur.
- `python -m pytest tests/test_rutas_sur.py tests/test_descarga_peajes_lectores.py tests/test_descarga_peajes_carga.py tests/contract/test_contactos_api.py -q`: **44 pasan**, sin escrituras reales. Incluye los dos PDF por ambos nombres y registro de lector general, rechazo de CUIT/IVA/total alterados, CUIT equivalente y alias/nombre equivalente. Avisos previos de FastAPI por on_event.
- El script `backend/scripts/reprocesar_rutas_sur.py` simula por defecto y con `--aplicar` toma respaldo COPY_ONLY CHECKSUM verificado antes de reparar en una transacción. Solo opera en WC. Mantiene las compras existentes y los originales; completa nombres oficiales, números, fechas, totales y vínculos de avisos sin marcarlos revisados.

## Aplicación

Aplicada con `python -m scripts.reprocesar_rutas_sur --aplicar`.

Respaldo **COPY_ONLY, CHECKSUM + RESTORE VERIFYONLY exitoso**: `C:\Program Files\Microsoft SQL Server\MSSQL17.SQLEXPRESS\MSSQL\Backup\WC_rutas-sur-20261029_20261029_095235_715527.bak`.

Verificación posterior por SELECT en WC:
- Portales_Documentos 220/221: nombre oficial, números correctos, fechas 28/10 y 29/10, totales 1548.82 / 1787.10, estado `ya_cargado`, sin motivo pendiente, vinculados a compras originales.
- DocumentosNuevos 49/50: `cargado_solo`, números, fechas y totales completos; IdRegistro 2143525172 / 2143525173. Revisado sigue NULL: permanecen para revisión del usuario, ya no para carga manual.
- COUNT por contacto y número: exactamente una compra por factura. Un solo contacto oficial; ningún contacto Corresur para borrar.
- Nueva simulación del script después de aplicar: ambas `ya cargada`, sin escrituras.

Aplicación activada: se comprobó que no había corridas de portales ni rutina en curso; se reinició únicamente el backend de este repositorio y se actualizó el PID del lanzador. `/health` responde `{"status":"ok"}`; arranque completo sin errores.

Se añadieron además dos pruebas del contrato HTTP 409 (alta/edición duplicada). `pytest tests/contract/test_contactos_api.py -q`: 11 pasan. Total de casos distintos verificados: **46** (44 del conjunto inicial + 2 nuevos). `git diff --check` sin observaciones. No se ejecutó una descarga nueva de portales: se verificó el lector con ambos PDF originales y se repararon los registros existentes.

Imágenes de revisión local: `C:\dev\LaHerencia\backups\rutas-sur-20261029\corresur-0.png` y `corresur-1.png`, fuera de Git. Cambios sin commit, sin push; listos para que la otra sesión los continúe respetando este registro. No hay pendientes de este pedido.

