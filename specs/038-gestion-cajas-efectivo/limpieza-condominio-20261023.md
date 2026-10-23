# Corrección de alcance del Condominio — 23/10/2026

Autorizado por Sergio: limpiar/corregir su registro dejando únicamente vínculos con Giamigli; eliminar la confusión de dos cajas. El cambio reemplaza la excepción anterior que dejaba visible la historia completa 036. Primer commit/push previo: a160622 (040 y recorrido del rediseño).

## Relevamiento
Importación 036: 1.226 filas, sin IdOperacionCaja ni IdPagoEfectivo ni IdContactoRelacionado; suma $0,23. Proceden de Caja Efectivo de Movimientos LSC desde Abr 2016.xlsm. No es la cuenta de socio 3 y no debe sumarse a ella.

## Criterios
- Conservar relaciones explícitas en conceptos de la fuente: aportes de efectivo a Giamigli, retiro/préstamo Giamigli, gastos bancarios Giamigli, cobros de cuotas de motosierra Giamigli y pago de su balance.
- Conservar además Pago Honorarios Criado del 20/04/2016, -$3.818, fila 15: hoja Abr 16, fila 41 lo identifica como Honorarios Criado (dev. Giamigli) 3 2016. No extender ese criterio por coincidencia de nombre o importe a otras filas.
- Retiros de Sergio/Lucy/Ceci, alquileres, impuestos propios, saldo inicial y conceptos sin prueba de relación quedan fuera del libro operativo. No adjudicar a Giamigli por homonimia o inferencias.
- Preservar las 1.226 filas originales. Registrar clasificación, fuente/huella, evidencia y snapshot por fila en WC. Vista operativa con lista positiva de históricos relacionados; nuevas operaciones auditadas 038 permanecen trazables. No borrar, anular ficticiamente ni inventar saldo de apertura.
- El saldo del subconjunto significa neto de movimientos vinculados, no efectivo físico del Condominio ni deuda del socio. No admite arqueos físicos ni advertencia de falta de efectivo sobre ese neto.
- Una sola entrada Condominio LSC, con secciones Cuenta con Giamigli y Movimientos vinculados. No fusionar sumas ni duplicar efectos.
- Importador debe rechazar nuevas filas propias/sin relación y no comparar el saldo total H de la planilla contra el subconjunto; usar suma de movimientos relacionados al corte con cobertura explícita. Deshabilitar el importador 036 completo para impedir una recarga fuera de alcance.

## Plan y puertas
1. Contrato y pruebas simuladas del filtro/evidencia, exclusión de importación y prohibición de arqueos.
2. Script de inspección y clasificación verificando contra la fuente; respaldo verificado antes del esquema y clasificación. Transacción explícita, control de deriva y conservación de otras cajas/cuentas.
3. Lecturas operativas, formulario/etiquetas y navegación unificada.
4. Pruebas focalizadas, compilación/lint y recorrido UI con todas las API interceptadas. Validación de WC de solo lectura posterior.
5. Registrar evidencia aplicada y commitear/pushear la corrección para continuidad con Claude Code.

## Hallazgos que no se corrigen por inferencia
En la fuente, el aporte de fila 1107 tiene fecha 11/09/2024 aunque está entre movimientos de agosto/octubre 2025. Se conserva la fecha original y se deja señalado; no cambiar por posición. Las hojas mensuales mencionan otros importes Giamigli que no permiten identificar de forma inequívoca una fila del libro: no inventar movimientos ni reclasificar retiros personales.

Estado: limpieza aplicada en WC, verificada y pusheada en main: 58ebe14. Primer incremento USD/rediseño: a160622.

## Aplicación verificada
- Script: backend/scripts/depurar_condominio_038.py, inspección por defecto; --aplicar toma respaldo y ejecuta una transacción explícita.
- Respaldo con CHECKSUM + RESTORE VERIFYONLY: C:/Program Files/Microsoft SQL Server/MSSQL17.SQLEXPRESS/MSSQL/Backup/WC_condominio_alcance_038_20261023_113704_234510.bak.
- Informe por fila: backups/condominio-alcance-038/alcance-20261023-113704.json. Fuente SHA256 1100f8bf07b5478226a7974a4c82b0172a6ab330a64135759716bbf359fa7618.
- Clasificadas 1.226 filas: 31 relacionadas y 1.195 archivadas fuera del alcance operativo. Neto del subconjunto -$9.298.765,84, orientado desde el Condominio; no es efectivo disponible ni deuda del socio.
- Nuevos objetos: AlcanceHistoricoCaja (clasificación, motivo, fuente/huella, snapshot, usuario/fecha), vw_MovimientosCajaEfectivoOperativos (lista positiva histórica más operaciones auditadas nuevas). Los originales no se borraron ni se marcaron como anulados.
- Se comprobó igualdad del hash de los 1.226 originales antes/después; conservan suma $0,23 en archivo bruto. Otras cajas, movimientos de socios, pagos y operaciones permanecen idénticos según controles transaccionales del informe.
- Lecturas reales de repository: 31 filas y neto -$9.298.765,84. Exportación en memoria de la hoja original a xlsx para probar el parser, sin guardar sobre fuente: devuelve las mismas 31 filas y el mismo neto.
- Importador 038 versión 2: filtra relaciones antes de calcular su saldo al corte; no reutiliza previews de versión 1. Confirmar un lote antiguo no puede importar/vincular filas sin evidencia. Importador completo 036 retirado.
- Las lecturas de saldo, contexto, detalle, libro y comparación usan la vista operativa; los locks/escrituras conservan tabla base. El registro parcial no admite arqueo ni alerta de efectivo negativo sobre su neto.
- Backend restringe alta directa desde Condominio a pago de gasto de Giamigli; aportes/devoluciones se hacen desde caja de Giamigli con contraparte explícita. Navegación: una entidad Condominio LSC con Cuenta con Giamigli y Movimientos vinculados.

## Continuidad
No duplicar los 31 movimientos con efectos automáticos de socio/banco: esta limpieza clasifica historia, no concilia contrapartidas. Los vínculos con movimientos de Giamigli y socios siguen como tarea 036. Cualquier incorporación de filas hoy archivadas necesita evidencia nueva, clasificación explícita y auditoría; no restaurar por parecido de importe o nombre.



## Verificaciones finales
- 82 pruebas simuladas de contratos 038, consulta/anulación, arqueos, importación, USD y alcance: PASS. Tras ampliar cobertura y versionar parser, 31 pruebas USD/importación/alcance: PASS (incluyen 13 de alcance). Sin escrituras de prueba en WC.
- TypeScript --noEmit y ESLint de rutas/componentes afectados: PASS. Ruff de script, clasificador y pruebas nuevas (--ignore E501 para SQL embebido): PASS.
- Navegador Edge headless: 22 escenarios, 129 API interceptadas, cero errores JavaScript y cero API sin fixture. Incluye entrada única del Condominio, cambio entre cuenta y movimientos, ausencia de arqueo y alta directa restringida a pago documentado; se preservan recorridos previos de caja, USD, corrección y socios.
- Captura inspeccionada visualmente: backups/cajas-038-ui/condominio-vinculos.png. Resultado: backups/cajas-038-ui/resultado.json. Todos sus importes son simulados; no atribuirlos a la cuenta real.
- Lectura real posterior: 31 históricos visibles y neto -$9.298.765,84; 1.226 originales intactos con suma $0,23 en archivo. Parser de la fuente produce exactamente el mismo subconjunto de 31 y neto.
- Servidor UI de prueba aislado detenido y cambios automáticos de tsconfig retirados. No se tocaron Access ni la planilla original.
