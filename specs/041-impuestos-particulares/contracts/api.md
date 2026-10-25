# API — 041 (prefijo /api/impuestos)

Refinado25/10/2026. Autenticación y rolLectura del sistema existentes: todas las consultas permitidas, todas las escrituras403 paraLectura. Usuario se toma de sesión, no del cuerpo. Respuestas de error:{detail:{codigo,mensaje,...contexto}}; mantener códigosHTTP existentes de operaciones no afectadas. Ninguna ruta escribe fuera deWC.

## Consulta y creación de carga

- `GET /{id}/particular?partida=...` → `{cargas:[{idCarga,idSocio,socio,importe,motivo,partida,titularOscar,estado,devuelto,pendienteNominal,estadoDevolucion,idMovimientoSocio,devoluciones:[{idVinculo,idMovimientoSocio,importe,estado}]}],parteEmpresa,avisos:[]}`. `devuelto` es nominal en pesos. Incluye historialanulado claramente identificado; los derivados solo suman vigentes. Partida de query opcional permite consulta auxiliar, no guarda asociación.
- `POST /{id}/particular` → 201 carga nueva; 200 operación ya registrada al reintentar. Cuerpo:`{claveIdempotencia:UUID,idSocio,importe | porcentaje,motivo,partida?,titularOscar?:bool,reemplazarMovimientoManual?:int,confirmarCuentaCerrada?:bool}`.
- Exactamente uno de importe/porcentaje; importe>0,porcentaje>0 y≤100. Calcular sobre total original de la boleta, redondeoHALF_UP a0,01; rechazar si resulta0 o supera remanente, sin recorte automático. Motivo1–255 caracteres no blancos y partida opcional1–60, normalizada según modelo. titularOscar=true requiere partida y socio3; una partida ya declaradaOscar vigente tampoco admite otro socio.
- 409:`SUPERARIA_IMPORTE`, `CUENTA_CERRADA` con requiereConfirmacion=true o `DEBE_MANUAL_EQUIVALENTE` con requiereConfirmacion=true y candidatos. Los avisos independientes deben resolverse todos; confirmar cierre no autoriza reemplazar un Debe. Selección de reemplazo siempre explícita. Candidato válido: socio/importe iguales,TipoAsignacionGasto,vigente,origenManual oNULL, diferencia histórica≤3 días corridos. No usar CreadoEn/fecha de carga. Mostrar varios sin elegir automáticamente.

## Devoluciones

- `POST /particular/{idCarga}/devoluciones` admite exactamente una variante:
  - Haber existente:`{claveIdempotencia:UUID,idMovimientoSocio,importe}`.
  - Haber nuevo:`{claveIdempotencia:UUID,fecha,importe,medio,motivo}`; campos con longitudes del módulo de socios vigente, motivo obligatorio, e importe>0 en pesos.
- Haber existente del mismo socio,TipoDevolucion,vigente. Importe explícito≤pendienteCarga y≤disponibleHaber en todos sus vínculos vigentes. No usar todo el Haber por defecto ni dividirlo automáticamente. 409:`CAPACIDAD_HABER_INSUFICIENTE`, `SUPERARIA_PENDIENTE`, `HABER_NO_VALIDO`, `VINCULO_DUPLICADO` o `CARGA_ANULADA`.
- 201 vínculo creado / 200 reintento, con carga/estadoNominal y vínculo. Haber nuevo se crea una sola vez con origen **DevImpParticular** (16 caracteres),IdOrigen=IdCarga; se valúa a su fecha con magnitudes positivas y TipoDevolucion. No genera banco/caja. Una compensación explícita se trata como vínculo a un Haber válido elegido por el usuario, sin deducción automática.
- `POST /particular/{idCarga}/devoluciones/{idVinculo}/anular` `{motivo}` → 200 vínculo anulado, capacidad liberada y carga recalculada; repetición devuelve estado actual sin escrituras nuevas. No anula el Haber. Para corregir importe se anula el vínculo y se crea otro con clave nueva; se preservan ambos en historial.
- La UI obtiene los Haber consultables del listado de movimientos de socios existente y permite seleccionar uno; POST comprueba nuevamente todas las capacidades. No suponer disponibilidad por ver el movimiento en la lista.

## Anulación de carga y protección de otras rutas

- `POST /particular/{idCarga}/anular` `{motivo}` → 200 carga y Debe anulados, vínculos vigentes anulados con auditoría y padrón recalculado; no anula ningún Haber. Motivo1–255 caracteres no blancos. Repetición sin nuevas escrituras.
- `DELETE /{id}` → 409 `IMPUESTO_CON_CARGAS` si hay cargas vigentes.
- `PUT /{id}` existente → 409 `IMPUESTO_CON_CARGAS` si cambia Fecha,Importe,IdOrganismo oIdTipoImpuesto con cargas vigentes. Anular cargas antes de modificar datos financieros; metadatos documentales/descriptivos permitidos siguen el contrato existente. El control ocurre también en persistencia/transacción.
- Rutas de edición/anulación de socios y anulación/corrección de una operación que afecte sus movimientos → 409 `MOVIMIENTO_VINCULADO_A_IMPUESTO` si alteran un Debe de carga vigente o un Haber con vínculos vigentes, incluyendo identificadores y enlace a la ficha. Se conserva el comportamiento de orígenes no relacionados. Tras desvincular, el movimiento solo admite las operaciones habituales de su origen; no se amplían permisos de movimientos de caja.

## Lista y padrón

- `GET /` conserva filtros/paginación y agrega `aCargoDe:[{idSocio,socio,importe}]`, `estadoDevolucion` y `pendienteNominal`; filtro `?particular=true` incluye boletas con cargas vigentes. Estado agregado según modelo; etiquetas siempre informan alcance nominal.
- `GET /partidas/{partida}` → `{partida,estado:vigente|ambigua|sin_cargas|desconocida,idSocio:null|int,socio:null|string,candidatos:[{idSocio,socio}],titularOscar:bool}`. No existente →200 desconocida con candidatosvacíos, sin crear registro. La referencia se codifica en la URL y se valida/normaliza en servidor; usar un parámetro de ruta que admita barras (`{partida:path}`) para no perder referencias completas.
- Partida nueva se ingresa en formulario/panel y consulta este endpoint. Con una carga existente se conoce la partida de esa carga; sin cargas ni entrada del usuario no se inventa una partida ni se muestra propuesta. Padrónambiguo muestra aviso y candidatos, nunca un titular preseleccionado. Sin_cargas no propone titular. El usuario siempre decide crear la carga.

## Idempotencia y concurrencia

La clave de creación es obligatoria en las dos variantes de devolución y al crear carga. Unicidad por tabla de carga/vínculo; huellaSHA256 del cuerpo normalizado y usuario autenticado, con formatos monetarios equivalentes canonizados. Consulta de clave precede a recalcular cotizaciones/remanentes. Misma clave y huella → misma entidad en su estado actual, sin crear ni reactivar nada incluso si se anuló. Clave con otra huella →409 `CLAVE_IDEMPOTENCIA_REUTILIZADA`. Dos solicitudes simultáneas idénticas producen una sola operación; no devolver errorSQL ni crear un segundo Haber.

Nueva intención confirmada por usuario → clave nueva. El frontend conserva la clave mientras se reintenta la misma intención y no la regenera por error de red. Los conflictos de capacidad/estado y los reintentos se prueban bajo transacciones; todos los estados finales respetan los límites de boleta y Haber.

## Caso3206 y unidades

Migración usa una clave estable y conserva el Haber3150 ya existente; sustituye el Debe3149 por el vinculado sin alterar saldo nominal oUSD/kg ni cotizaciones. Fechas históricas07/11/2017 y13/11/2017;25/10/2026 es la fecha de carga manual, no la fecha del impuesto. Verificar identificadores/valores en inspección, no confiar ciegamente en números escritos aquí.

Estado devuelto del3206 es nominal8852,10. El Debe501,5354USD yHaber505,8343USD conservan su diferencia histórica de4,2989USD; no se genera ajuste para poner la cuenta a cero ni se cambia el Haber de fecha.
