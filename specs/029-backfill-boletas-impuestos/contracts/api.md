# API propuesta: backfill de impuestos

Prefijo `/api/impuestos/backfill`. Sesión cookie existente; 401 sin sesión; 403 para rol Lectura en escrituras. Sin SQL, rutas arbitrarias o organismo/importe confiados al cliente. Importes nuevos como cadenas decimales de dos posiciones; fechas ISO. Mantener compatibles los contratos existentes de Impuestos/cuenta corriente.

## Lecturas sin persistencia

- `GET /diagnostico?organismoId=&page=1&pageSize=50`: sin organismo devuelve resumen paginado; con organismo devuelve pagos y resumen. pageSize máximo 200. Respuesta: items, total, totalesPorEstado, saldoActual, totalFaltanteConfirmado, saldoProyectado, diferenciaNoExplicada, advertencias, fechaLectura. Pago: medio, idMovimiento, fecha, concepto, importe, referenciaContable, estado, motivo, respaldos, huella. No aceptar filtros de fecha que recorten silenciosamente el histórico.
- `GET /propuesta?organismoId=&page=1&pageSize=50`: propuesta recalculada sin escribir WC; filas con salida comprobante/generada/pendiente, tipo propuesto, candidatos, motivo, coberturaBusqueda y huella. Resumen completo del organismo independiente de paginación. Búsqueda incompleta bloquea filas generadas.
- `GET /comprobantes/{archivoId}`: PDF/imagen permitida, identificador resuelto por servidor bajo raíces canónicas; 404 si falta, 409 si cambió; nunca resolver una ruta recibida libremente.
- `GET /lotes?page=1&pageSize=50` y `GET /lotes/{idLote}`: auditoría, fuentes, boletas históricas, total, estado, permisos de reversión y motivos de bloqueo.

## Revisión y confirmación

`POST /validar`: sin persistencia; cuerpo organismoId, huellaFuente y 1..200 decisiones únicas `{medio,idMovimiento,accion: incluir|excluir,fuente: comprobante|generada,archivoId?,tipoImpuesto,confirmacionDocumento?,periodoLiquidado?,numeroDocumento?}`. No aceptar cambio libre del organismo/fecha/importe del pago. Respuesta vista previa completa recalculada, huellaPropuesta que incluye correcciones y selección, total exacto, saldo proyectado, exclusiones y conflictos. Esta vista previa es la que el usuario confirma; ante corrección posterior se valida de nuevo.

`tipoImpuesto` es una unión discriminada: `{modo:"existente",idTipoImpuesto:enteroPositivo}` o `{modo:"generico"}` sin ID. El servidor valida pertenencia al organismo. El modo genérico permanece simbólico en propuesta/huella y se resuelve bajo bloqueo al confirmar, reutilizando o creando el catálogo dentro de la misma transacción. No se crean tipos en GET ni POST validar. Para decisiones excluidas solo se requieren medio, idMovimiento y accion; no se exige tipo ni archivo.

Para fuente comprobante se requiere `archivoId` y `confirmacionDocumento:true`, tanto en coincidencias únicas como en elección manual. Un ambiguo documental pasa a confirmable cuando el usuario selecciona un candidato del conjunto vigente y el servidor comprueba archivo libre, identidad/hash, organismo, ausencia de colisiones en toda la selección y pago totalmente descubierto. La decisión manual y el conjunto de candidatos se incluyen en la huella y en el evento de confirmación. No levanta bloqueos financieros, de cobertura incompleta o de identidad. Una elección inválida devuelve 422; un candidato cambiado desde la revisión devuelve 409. Las filas pendientes sin resolver siguen rechazadas.

`POST /confirmar`: `{idLote: UUID, organismoId, huellaPropuesta, decisiones, preparacion, backupId}`. Validar usuario, evidencia de backup, archivos, fuentes, respaldo, capacidad y huella dentro de transacción común antes de INSERT. Respuesta 201 `{idLote,estado,cantidad,total,boletas:[{idImpuesto,medio,idMovimiento,fuente}]}`. Repetición exacta del UUID devuelve 200 con lote previo; mismo UUID con payload distinto devuelve 409. No dividir automáticamente un request en transacciones parciales.

Respuestas: 422 selección inválida/tipo incorrecto/fila pendiente; 409 datos obsoletos, duplicados, archivo usado, backup no válido o lock ocupado; 404 referencia ausente; 503 fuente SQL/carpeta no disponible. Errores incluyen código estable y detalle legible, sin conexiones ni secretos. Todo error previo a commit deja cero boletas nuevas.

## Preparación y consulta de respaldo

`POST /validar` devuelve además `preparacion`, un token firmado por el servidor que contiene finalidad confirmar, huellaPropuesta, usuario y fechaPreparacion UTC. La prevalidación de reversión emite el mismo formato con finalidad revertir y huellaReversion. No persiste borradores ni cambia la huella al consultar el estado de backup. El servidor comprueba firma, finalidad, usuario y huella; fechaPreparacion nunca procede de un campo libre del cliente.

La herramienta local `backend/scripts/crear_tablas_backfill_impuestos.py --backup-only --preparacion <token>` verifica el token, crea COPY_ONLY BACKUP de WC con CHECKSUM y ejecuta RESTORE VERIFYONLY WITH CHECKSUM; no ejecuta DDL ni carga boletas en este modo. Guarda evidencia firmada en directorio privado configurado fuera de Git: backupId aleatorio, hash del token, base WC, ruta interna, hora de inicio y verificación, hash del archivo y resultado. No emitir evidencia si falla cualquier paso. Inicio del respaldo debe ser posterior a fechaPreparacion. Sin token, el respaldo del modo migración sirve solo para DDL, no para confirmar lotes.

`GET /respaldo (header X-Backfill-Preparacion: <token>)` requiere sesión y pertenencia del token al usuario; consulta exclusivamente esa evidencia y devuelve `{estado:pendiente|verificado|invalido,backupId?,verificadoEn?,motivo?}` sin ruta ni secretos. UI permite refrescar y usa backupId solo si verificado; el operador ejecuta la herramienta después de la revisión final. Confirmar/revertir incluyen `preparacion`, revalidan evidencia, archivo y hash antes de abrir la transacción y comprueban de nuevo la huella bajo bloqueo. Si cambia la selección o las fuentes se requiere nueva validación y nuevo respaldo. La herramienta no acepta SQL o rutas de respaldo elegidos desde navegador. Los tokens no se incluyen en logs de acceso.

## Mantenimiento limitado a boletas 029

- `PATCH /boletas/{idImpuesto}/tipo`: `{idTipoImpuesto,version}`; mismo organismo, auditoría antes/después, 409 ante versión vieja, 404 si no pertenece a 029.
- `PATCH /boletas/{idImpuesto}/comprobante`: `{archivoId,version,confirmadoPorUsuario:true}`; revalidar archivo libre, usuario confirma contenido; actualizar Documento Original y TieneComprobante, conservar procedencia y registrar evento. No modificar PDF ni importe/fecha/pago. La API no considera el booleano autorización suficiente sin sesión y rol.
- `POST /lotes/{idLote}/reversion/validar`: informe sin escritura de dependencias y cambios posteriores, huellaReversion.
- `POST /lotes/{idLote}/revertir`: `{huellaReversion,preparacion,backupId}`; revalidación atómica, borrar solo vínculos y boletas propios sin cambios posteriores, conservar eventos/procedencia. 409 si cualquier fila ya fue modificada, adjuntada o vinculada; sin reversión parcial. Repetición devuelve estado revertido existente.

## Integración con lecturas existentes

`GET /api/impuestos`: filtros opcionales `generadaDesdePago`, `sinIdentificar`; campos aditivos `origenCreacion`, `generadaDesdePago` (marca actual), `tieneComprobante`, `idLote`, `version`. Tipo genérico corregible desde listado. En cuenta corriente enriquecer origen Impuestos por IdOrigen para mostrar la misma marca; no cambiar Documento/número/importes de la vista ni multiplicar filas por joins.

## Contrato de UI

Ruta `/finanzas/impuestos/backfill`: organismo → diagnóstico con diferencia explicada → comprobantes reales → generadas → revisión final → resultado/lote. Mostrar todo el histórico, filtros por estado, totales completos, exclusiones individuales y vista previa de documento. Ninguna casilla ambigua se selecciona automáticamente. Confirmar deshabilitado hasta vista previa válida y backup verificado. Mostrar vacío, cargando, búsqueda incompleta, error, cambio concurrente y reintento idempotente. Invalidar queries de Impuestos, cuenta corriente, diagnóstico y saldos documentales tras mutaciones.

Decisión de implementación: la preparación viaja en el header X-Backfill-Preparacion al consultar respaldo; nunca en querystring, para no exponerla en logs de acceso. Código de mutaciones separado en escrituras.py y firmas/evidencia en respaldo.py, dentro del mismo módulo 029.
