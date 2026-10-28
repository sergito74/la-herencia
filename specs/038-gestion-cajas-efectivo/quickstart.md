# Guía de validación — 038

## Validación del canje socio — 28/10/2026

Implementado por pedido deSergio: menú «Efectivo contra transferencia al socio». Elegir socio, fecha, importe y transferencia; una confirmación aumenta caja, vincula el débito existente y conserva saldo del socio. Detalle y preview muestran ambas piernas sin pedir asientos separados. Selector de operación ampliado para leer el nombre completo; faltante de extracto y error conservan borrador. La transferencia debe ser del mismo día e importe; las de otra persona, usadas o con aporte/retiro previo se rechazan para revisión.

Archivos: backend schemas/service y `tests/test_cajas_contrato_canje_socio_038.py`; frontend cliente, OperacionCajaForm y DetalleOperacionCaja. Sin cambios de esquema, importes históricos ni operaciones reales de prueba. No se modificaron Access, Excel ni datosWC. Se conservaron los cambios ajenos en flujo_caja y los archivos036 encontrados al comenzar.

Comandos/resultados finales:
- `python -m pytest tests/test_cajas_contrato_base_038.py tests/test_cajas_contrato_pagos_038.py tests/test_cajas_contrato_canje_socio_038.py tests/test_cajas_contrato_traspasos_038.py tests/test_cajas_contrato_socios_038.py tests/test_cajas_contrato_consulta_038.py -q`: **56 passed**, conexionespyodbc prohibidas por simulador. Incluye idempotencia, aporte/retiro previo, destinatario, fecha/importe/signo, banco usado, dependencias, anulación y rollback por fallo intermedio.
- `npx --no-install tsc --noEmit`: PASS. ESLint de los tres archivos frontend modificados: PASS.
- `python tests/ui/cajas_038_smoke.py`: **PASS,25 escenarios,195 solicitudesAPI interceptadas, cero erroresJS y cero solicitudes sin fixture**. Canje confirmado en una carga, sin POST de asiento adicional; faltante de extracto bloquea registro y error conserva los datos. Captura revisada visualmente `backups/cajas-038-ui/canje-socio-preview.png`, resultado `backups/cajas-038-ui/resultado.json`.

Recorrido en servidor local3100 con compilación aislada `.next-canje-038-ui`; detenido al finalizar. Restaurado únicamente el cambio automático que Next añadió a tsconfig, verificando que no hubiera cambios ajenos. El lanzador normal recompila/reinicia cuando las fuentes son más nuevas; volver a abrir LaHerencia carga esta versión. No se inició ni ejecutó ninguna transferencia real.

Durante la verificación se corrigió una expectativa de test que esperaba excepción cuando el contrato devuelveHTTP500; se ajustaron selectores de etiquetas del recorrido y fixtures de avisos/controles añadidos anteriormente a la aplicación. Estos fallos fueron del ensayo y no produjeron escrituras reales. No se aplicó FIFO ni conciliación de cuentas en esta tarea.

## Preparación
Usar entorno backend/frontend existente, sin instalar dependencias. Consultar contracts/api.md y data-model.md. Pruebas con datos simulados; no ejecutar operaciones de prueba sobre WC. Antes del DDL real: inspección acotada del esquema y respaldo verificado, con ruta y resultado documentados. Preservar Access y Excel. No aplicar escrituras en esta fase de planificación.

## Verificaciones de implementación previstas
Desde backend: `python -m pytest tests/test_cajas_efectivo_038.py` (archivo a crear en implementación). Desde frontend: `npx --no-install tsc --noEmit`. Estos comandos no se ejecutaron durante el diseño.

| Escenario | Evidencia esperada |
|---|---|
| Pago total, parcial y varias facturas | Una salida física y un pago del proveedor; aplicaciones correctas |
| Compra particular | Pago proveedor, asiento Particular y una deuda de socio, sin duplicados |
| Gasto sin comprobante | Baja caja y rubro/reparto correcto; no nueva deuda en 97 |
| Aporte y retiro a cuenta | Signo correcto de socio, cotizaciones históricas y kg/US$ persistidos |
| Ganancias iguales | Salida por socio sin deuda ni crédito en socios |
| Traspaso caja-caja | Dos movimientos opuestos; cero efecto en contactos/socios |
| Banco-caja con intermediario | Banco y efectivo enlazados, banco fuera de contacto; no aporte del intermediario |
| Cobro de venta | Entrada y cobro único aplicado; alquiler exige adaptador real antes de habilitar |
| Arqueo distinto en $249,10 | Diferencia visible; ajuste solo tras confirmar y una sola vez |
| Anulación | Saldo caja/contacto/socio y vínculos regresan juntos; auditoría intacta |
| Fallo en cada paso de escritura | Rollback completo, sin efectos parciales |
| Reintento y concurrencia | Idempotencia; misma clave diferente contenido da conflicto; capacidad revalidada |
| Fecha retroactiva y saldo negativo | Avisos explícitos, aceptación vigente, conflicto si cambió el contexto |
| Planilla importada dos veces | Cero duplicados; operación manual enlazada tras revisión |
| Fila desplazada, modificada o dos filas iguales | No perder movimientos reales ni importar ambiguos automáticamente |
| Condominio | Historia visible; nuevo movimiento sin relación Giamigli rechazado; cobertura clara |
| Rol Lectura, vacío y error | 403 en escrituras, consulta disponible y UI recuperable |

SC-002: muestra simulada de 50 operaciones variadas con conteo exacto por libro y reintentos. SC-004: lectura de saldos al corte histórico respectivo (Giamigli $381.785,15, chica $96.907, Condominio $0,23); no exigir esos importes al saldo actual si ya hay operaciones posteriores. Confirmar que la migración por sí sola no cambia ninguno.
Para imputaciones productivas o validación final de resultados por campaña, ejecutar auditoría de vínculos de specs/036-revision-sistematica-cuentas/auditoria-campanias.md, sin asignar automáticamente partidas ambiguas.

## Registro de esta fase
22/10/2026: solo diseño y revisión local de fuentes. Sin pruebas de implementación, consulta/escritura SQL, respaldo nuevo ni cambios en planillas. Pendientes: generar tasks.md, implementar, registrar comandos/resultados y evidencia real de validación. El traspaso histórico de 036 no se considera completado por este diseño.

## Casos adicionales exigidos tras analyze
Antes de cada cliente/UI, ejecutar su prueba de contrato SQL/API con SQL simulado y registrar comandos/resultados; no basta que exista el archivo. Los archivos concretos están en tasks.md.
- Condominio: aporte de $100.000 produce dos piernas físicas y un crédito socio; devolución invierte ambas piernas y produce un débito. Pago directo: proveedor y socio una vez, sin caja Giamigli ficticia. Rechazar cruce en traspaso interno.
- Gasto sin comprobante: un registro GastoCaja y repartos con sumatoria exacta; resultado incluye costo una sola vez y lo excluye al anular; sin factura/deuda. Costo no valuado en USD no se presenta como cero válido.
- Arqueo: anular ajuste cambia a Invalidado y conserva recuento; nuevo correctivo enlazado. Retroactividad aceptada cambia afectados a Desactualizado; UI no declara conciliación vigente.
- Filtro: ingreso 100, salida 30 oculta por filtro, ingreso visible 20 → saldo real final 90 y subtotal de ingresos 120, no saldo ficticio de 120. Probar páginas y anulados.
- Compatibilidad: GET mantiene saldo/importe numéricos; campos Decimal nuevos son cadenas. Cliente anterior sigue deserializando.
- Opción A documentada por $10.000: banco −10.000, caja +10.000, ajuste interno no cobrado cancela liquidación, cero aporte y cero doble pago; anulación controlada restaura clasificación anterior. Bloquear diferencias sin respaldo y preservar pares históricos de socio.

Registro 22/10/2026: generación de tareas completada y siete hallazgos corregidos por autorización explícita. Son cambios documentales, sin DDL, consultas/escrituras WC ni pruebas de implementación. Las menciones anteriores a «generar tasks.md» describen la fase histórica; actualmente hay 57 tareas pendientes. Evidencia de esta corrección: revisión de coherencia de documentos y validación de formato/secuencia/dependencias, sin afirmar validación funcional del software.

Verificación documental ejecutada tras la corrección: script de formato/IDs/referencias/rutas y ocho puertas de contrato PASS (57 tareas); git diff --check sin errores. Relectura de los siete hallazgos: reglas y dependencias incorporadas; sin bloqueantes documentales de esos hallazgos. La verificación viva de esquema y las pruebas funcionales siguen pendientes de implementación.

## Implementación iniciada — 22/10/2026
T001–T003 completadas: metadatos y agregados reales en schema-verification.md; nueve tablas nuevas definidas, IdContacto efectivo nullable, columna de vínculo físico IdOperacionCaja (no confundir con IdOperacion legado de efectivo).
Migración ejecutada: primer intento revertido por ausencia de clave única en Centro de costos; corregida referencia con validación de aplicación. Segundo intento aplicado en una transacción, sin modificar cantidades/IDs/saldos: chica 100/$96.907; Condominio 1.226/$0,23; Giamigli 2.024/$381.785,15.
Respaldo previo COPY_ONLY/CHECKSUM y RESTORE VERIFYONLY: C:/Program Files/Microsoft SQL Server/MSSQL17.SQLEXPRESS/MSSQL/Backup/WC_cajas_038_20261022_164750_360262.bak. Evidencia local backups/cajas-038-schema/migration-20261022T194751404928.json; definición anterior de vista central en la misma carpeta. No se modificó Access/Excel ni se insertaron movimientos de prueba.

### Contratos backend antes de UI
Ejecutado: python -m pytest tests/test_cajas_contrato_base_038.py tests/test_cajas_contrato_pagos_038.py tests/test_cajas_contrato_socios_038.py tests/test_cajas_contrato_traspasos_038.py tests/test_cajas_contrato_cobros_038.py tests/test_cajas_contrato_arqueos_038.py tests/test_cajas_contrato_consulta_038.py tests/test_cajas_contrato_importacion_038.py -q → 49 passed. Sin conexiones a WC: las suites bloquean pyodbc.connect y simulan persistencia/rollback. Cubren contratos HTTP, ocho puertas previas a cliente/UI, muestra de 50 operaciones con reintentos/anulación, importación XLSX y fallos parciales. Warnings de deprecación de dependencias existentes, sin instalaciones.
Lectura real de contrato: previsualización de traspaso de $1 sin creación, listado con saldo corrido (2.024 movimientos), arqueos vacíos y fuente de costos vacía. Se detectó y corrigió datetime2 devuelto como texto por ODBC; lectura posterior correcta. Vista de efectivo vigente conserva 2.601 filas históricas. No son pruebas de escritura real.
Ampliación de CHECK de aplicaciones para cuota de alquiler y exclusión de AjusteNoCobrado al anular: respaldada y aplicada con saldos/cantidades idénticos. Backup C:/Program Files/Microsoft SQL Server/MSSQL17.SQLEXPRESS/MSSQL/Backup/WC_cajas_038_20261022_165801_214921.bak; evidencia backups/cajas-038-schema/migration-20261022T195802200544.json.
Implementación organizada en operaciones.py (persistencia Decimal), service.py (coordinación), arqueos.py e importacion.py, en lugar de concentrar todo en repository.py. Repositorio histórico sigue compatible. Pendiente: UI, verificaciones ampliadas de bordes, auditoría de campaña y cierre de tareas. No declarar terminado el módulo por las pruebas de backend.

### UI y verificaciones ampliadas
UI implementada en OperacionCajaForm.tsx, ArqueoCajaPanel.tsx, ImportacionCajaPanel.tsx y DetalleOperacionCaja.tsx, integrada a CajaEfectivo.tsx. Cliente tipado con UUID por intento, advertencias versionadas y consultas TanStack Query; enlaces a rutas existentes y permisos SoloLectura. Compilación TypeScript ejecutada sin errores.
Recorrido Playwright/Edge headless: PASS con toda API interceptada (sin acceso a WC), 61 solicitudes simuladas y cero errores JS. Pago de fixture completado en 0,46 s: medida de la interacción en entorno simulado, no del rendimiento SQL de producción. Escenarios: pago, anulación, arqueo, vínculo de importación, error conservando borrador, aporte, ganancias, traspaso, extracción bancaria, cobro, gasto sin comprobante y rol Lectura. Script reproducible backend/tests/ui/cajas_038_smoke.py; capturas y resultado backups/cajas-038-ui/.
Pruebas 038 ampliadas: 76 passed; cada suite bloquea pyodbc.connect y no usa datos reales. Regresiones existentes de cajas, aplicaciones, vínculos y costos/resultados: 38 passed. No ejecutar más allá de estos módulos sin nueva causa.
Auditoría de campañas solo lectura ejecutada: 16.338 renglones de compras y 55 labores, un caso sin asignación, cero reasignaciones. Informe backups/auditoria-campanias/auditoria-20261022_172004.json y CSV correspondiente.
Reejecución de migración detectó un defecto de CREATE VIEW para vista existente y revirtió transacción. Se corrigió a CREATE OR ALTER VIEW; reejecución aplicada y saldos/cantidades originales idénticos. Nuevo índice único filtrado garantiza un pago físico vigente por operación/pago. Respaldo verificado: C:/Program Files/Microsoft SQL Server/MSSQL17.SQLEXPRESS/MSSQL/Backup/WC_cajas_038_20261022_172945_519311.bak. Evidencia backups/cajas-038-schema/migration-20261022T202946501418.json. Intento fallido anterior registrado como revertido en esa carpeta; nunca se restauró producción.
Refinamiento de compras particulares conforme a 021: el gasto del socio corresponde a la parte particular documentada completa, aunque el proveedor reciba un pago parcial; asiento y asignación se generan una vez y se enlazan en pagos posteriores. El saldo documental usa el importe bruto previo a la línea interna negativa, sin alterar factura fiscal ni movimientos previos. Si otros pagos dependen del soporte particular, se bloquea anular su operación creadora hasta resolverlos. Cotización/fecha de asignación: fecha de compra; aportes/retiros conservan fecha de caja.
Hallazgo técnico: IdFormaPago 30 usado por notas históricas no existe en el catálogo consultado. Las nuevas notas Particular usan tipo 2 válido y método NULL (no son efectivo físico), con vínculo formal y auditoría; el pago físico usa tipo 1/método 3 válidos. No se alteraron códigos históricos.
Pendiente de cierre: últimos bordes de contratos, revisión estática/diff y sincronización final de documentos/tareas. No hay datos operativos nuevos cargados en WC.

## Cierre — 22/10/2026 (Claude, continuidad de Codex)
Comparación final: las 24.065 filas de la vista de cuentas corrientes conservan los mismos totales de deuda y crédito que antes de la migración; ninguna operación real de caja creada en WC.
Última ejecución: `python -m pytest tests/ -q -k 038` → 81 passed; `npx tsc --noEmit` sin errores. Suite completa (sin tests/ui): 1400 passed, 5 failed. Las 5 fallas (test_auditoria_cuentas_api ×2, test_revision_cuentas_api ×2 Jáuregui, test_vista_cuenta_tarjetas ×1) fallan idénticas con el código anterior a 038 (git stash): son pruebas contra datos vivos desactualizadas por las conciliaciones de 036, no regresiones de este módulo. Quedan como pendiente de mantenimiento de pruebas.
Revisión T057: git diff --check limpio, sin secretos ni binarios en el diff; respaldos y capturas en backups/ (ignorado por Git). 57/57 tareas cerradas con evidencia registrada arriba.
Pendiente real: uso operativo en paralelo con la planilla hasta que Sergio confíe en el sistema (aclaración de spec).


## Corrección de alcance del Condominio — 23/10/2026
Aplicada y verificada: 31 vínculos documentados visibles, 1.195 filas archivadas sin borrar originales. Ver [informe completo, respaldo y continuidad](limpieza-condominio-20261023.md). Una sola entidad Condominio LSC con Cuenta con Giamigli / Movimientos vinculados. No usar neto del subconjunto como efectivo ni deuda. Pruebas 82 y luego 31 focalizadas PASS; TypeScript/lint PASS; navegador 22 escenarios con 129 API interceptadas, sin errores y sin pruebas en WC. Los pendientes de conciliación/contrapartidas 036 siguen abiertos y no se duplicaron efectos.
