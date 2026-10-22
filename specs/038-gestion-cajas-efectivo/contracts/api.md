# Contrato API propuesto — 038

Base /api/cajas-efectivo. Conservar slugs giamigli-sa, campo-chica, condominio-lsc. Autenticación existente; escrituras solo rol habilitado, usuario obtenido de sesión. GET existentes conservan saldo e importe numéricos y su significado. Operaciones nuevas usan cadenas decimales monetarias de dos decimales; cotizaciones/valuaciones conservan precisión de data-model.md. Nuevos campos: saldoDecimal, saldoAnteriorDecimal, saldoCorridoDecimal y subtotalFiltradoDecimal, sin cambiar tipos existentes. Fechas YYYY-MM-DD y auditoría UTC.

| Método y ruta | Resultado |
|---|---|
| GET /{caja}/saldo?detalleSaldo=true | Saldo vigente al corte, último arqueo y cobertura Condominio |
| GET /{caja}/movimientos | items,page,pageSize,total; filtros desde,hasta,tipo,idContacto,idSocio,incluirAnuladas; saldoAnteriorDecimal, saldoCorridoDecimal real por fila y subtotalFiltradoDecimal separado |
| GET /operaciones/{id} | Operación, estado, efectos y enlaces a documentos/banco/socio; auditoría |
| POST /operaciones/previsualizar | Validación, efectos previstos, saldo resultante, cotizaciones y advertencias; no escribe libros |
| POST /operaciones | Crear atómicamente y devolver operación y efectos |
| POST /operaciones/{id}/anular | Motivo obligatorio; anulación conjunta idempotente |
| POST /{caja}/arqueos | Crear borrador con corte y denominaciones |
| PUT /{caja}/arqueos/{id} | Actualizar únicamente borrador con versión esperada |
| POST /{caja}/arqueos/{id}/confirmar | Confirmar una vez; aceptar explícitamente diferencia y advertencias; devolver ajuste si existe |
| GET /{caja}/arqueos | Historial paginado con detalle de recuento |
| POST /importaciones/previsualizar | Archivo xlsx, libro lógico y corte; vista previa de filas y comparación, sin escribir libros |
| POST /importaciones/{id}/confirmar | Resoluciones por fila e idempotencia; importar/vincular solo filas resueltas |
| GET /importaciones/{id} | Estado, evidencia, comparación por caja, exclusiones y conflictos |

## Crear operación
Cabecera Idempotency-Key UUID obligatoria. Cuerpo: tipo (pago,cobro,aporte,retiro_a_cuenta,retiro_ganancias,traspaso_cajas,extraccion_banco,deposito_banco,gasto_sin_comprobante,retorno_sueldo_opcion_a), caja, fecha, importe positivo, concepto, cuenta A/B; según tipo idContacto, idSocio, cajaDestino, banco:{medio,idMovimiento}, intermediario, evidencia, rubro/centroCosto, compraParticular:{idCompra,idSocio}, aplicaciones:[{tipoDocumento,idDocumento,importeAplicado}]. Diferencia de arqueo solo se crea desde confirmar arqueo. Denegar combinaciones de campos incompatibles y destinos iguales. Condominio exige motivoRelacionGiamigli. Gasto sin comprobante requiere rubro y reparto productivo válido, sin crear deuda al contacto 97 por defecto.

Respuesta 201 con idOperacion,estado,movimientos,efectos,advertencias; reintento idéntico 200. La previsualización devuelve una versión de los datos y códigos SALDO_NEGATIVO/PERIODO_ARQUEADO; confirmación exige aceptación explícita vinculada a esa versión. Si cambió el saldo/corte, 409 y nueva previsualización; no reutilizar aprobación desactualizada. Verificar signos y capacidad en servidor. Aplicaciones no pueden pertenecer a otro contacto ni exceder disponibilidad; devolver advertencias monetarias 036 sin inventar ND/NC. Alquiler soportado: tipoDocumento Alquiler usa IdCobroAlquiler (cuota), su IdAlquiler determina el contacto y el importe es Importe Cuota en pesos; una cuota Cobrado histórica sin aplicaciones nuevas no se ofrece como pendiente ni se cobra otra vez.

## Anular
Cuerpo {motivo,versionEsperada}. Respuesta 200 con estado y efectos revertidos; segundo intento no duplica efectos. Dependencias externas activas: 409 con identificadores y acción requerida. Historia importada sin operación no admite anulación compuesta hasta identificar sus vínculos mediante revisión.

## Arqueo
Cuerpo: fechaCorte, secuenciaCorte, denominaciones:[{valor,cantidad}], versionEsperada al modificar. Devuelve saldoSistema,totalContado,diferencia,estado,version. Confirmación incluye aceptarDiferencia y aceptaciones vigentes. No permitir modificación del confirmado.

## Importación
Lectura del archivo sin ejecutar macros ni modificarlo; límites de tamaño/filas y hojas permitidas definidos en servidor. Decisiones por fila: importar, vincular a idMovimiento/idOperacion, excluir con motivo o dejar pendiente. Archivo o fila modificada exige nueva vista previa. Lotes repetidos no duplican; ambiguas no se importan automáticamente. Confirmación transaccional del lote resuelto; error revierte el lote completo. Las relaciones históricas se preservan y vincular nunca recrea pagos existentes.

## Errores y permisos
401 sin sesión; 403 Lectura; 404 caja/operación inexistente; 409 concurrencia, idempotencia incompatible o dependencia; 422 campos/combinaciones/capacidad inválidos. Fallo SQL: rollback completo, respuesta sin SQL ni datos sensibles. Listados vacíos devuelven items=[] y saldo de arrastre correcto. UI muestra carga/error/reintento sin perder el borrador y oculta acciones de escritura al rol Lectura.

## Precisiones vinculantes del análisis

- aporte/devolución del socio 3 admite cajaContraparte con dos piernas físicas. Devolución usa retiro_a_cuenta como débito contra su crédito, mostrando naturaleza «devolución de aporte». traspaso_cajas solo permite Giamigli↔chica; cruce Condominio en ese tipo devuelve 422. Pago directo de gasto Giamigli desde Condominio crea además crédito socio 3, sin contacto 549 ni caja Giamigli ficticia; no combinar con compraParticular.
- gasto_sin_comprobante exige repartos:[{idRubro,idCentroCostos,idDestino?,idCampania?,idLote?,importePesos}], suma exacta y referencias válidas. Devuelve idGasto y origen GastoCaja; no factura/deuda. Anulación incluye costos/resultados.
- retorno_sueldo_opcion_a exige idSalario, banco, importe y evidencia, sin idSocio. Preview muestra traspaso, exclusión salarial y ajuste no cobrado; monto parcial/diferencia sin regla documentada o período ya tratado por otro mecanismo devuelve 409/422, sin efectos. Reversión restaura clasificación/aplicaciones previas bajo versión. No transformar pares históricos compensados.
- Operación/arqueo exponen version; crear operación envía previewVersion y advertenciasAceptadas. Resolver reintento idempotente idéntico antes de exigir nueva preview. Confirmar arqueo exige versionEsperada/previewVersion y aceptarDiferencia. Cambios de contexto: 409 sin efectos parciales.
- Anular ajuste devuelve arqueo Invalidado. Crear arqueo correctivo acepta idArqueoAnterior. Retroactividad aceptada devuelve arqueos afectados Desactualizado. Conservar saldo/contado/diferencia originales y agregar saldoRecalculadoDecimal/diferenciaVigenteDecimal; último arqueo incluye estado/vigencia. Invalidado/Desactualizado no acredita conciliación actual.
- Filtros tipo/contacto/socio seleccionan filas y no excluyen del saldo real movimientos ocultos. Ventana temporal/páginas conserva arrastre real; subtotalFiltradoDecimal es independiente. Anulados no alteran saldo/subtotal vigente.

## Detalles cerrados antes de implementación (T003)

Importes nuevos decimal(19,2); cotizaciones decimal(19,6), valuación USD decimal(19,4), kg decimal(14,3), redondeo comercial HALF_UP. Concepto 1–255 caracteres, motivo/evidencia máximo 255, usuario máximo 60 tomado de sesión; identificadores positivos. Texto opcional NULL, no cadena vacía. Version bigint NOT NULL default 0. Preview SHA-256 canónico del pedido y dependencias, sin confiar en saldo enviado por navegador.
Corte: fecha operativa America/Argentina/Buenos_Aires y secuencia IdMovimiento dentro del día; lectura estable por Fecha,IdMovimiento. Desde/hasta inclusivos, saldo a fin del día, orden ascendente. Filtros no alteran saldo real. Página >=1, pageSize 1..200. Detalles de operación y arqueo por identificador; listados paginados.
XLSX máximo 10 MiB, 20.000 filas por hoja y 50 MiB de contenido ZIP descomprimido; hojas permitidas Caja Efectivo Pesos y Caja chica campo del libro lógico CajasGiamigli, y hoja de Condominio explícitamente configurada. Rechazar archivo cifrado/macros/enlaces externos; fórmulas sin valor cacheado quedan pendientes, nunca cero por defecto. No abrir Excel ni escribir archivos originales.
BancoOperacionCaja: IdOperacion FK, Medio catálogo bna/galicia/mercado-libre, IdMovimiento bigint; unicidad activa por movimiento se revalida bajo bloqueo común. Vista de efectivo vigente excluye efectos de operaciones anuladas; tabla física permanece auditable. Pagos efectivo.IdContacto pasa a nullable para puente real sin contacto, según metadatos WC. No reutilizar su IdOperacion int para la cabecera 038 bigint.

## Contrato implementado — 22/10/2026

POST /operaciones/previsualizar recibe la operación directamente. POST /operaciones recibe {operacion: {...}, previewVersion, advertenciasAceptadas}; mantiene Idempotency-Key UUID. Los GET originales siguen compatibles; detalleSaldo=true habilita arrastre/subtotal/saldo corrido en movimientos y último arqueo/cobertura en saldo. El cliente 038 pide esa variante.
GET /operaciones/{id} agrega anulacion:{previewVersion,advertencias,efectosPrevistos}; si cambió el movimiento físico de forma ajena, muestra bloqueo sin ocultar su auditoría. POST /operaciones/{id}/anular admite previewVersion y advertenciasAceptadas, obligatorios cuando anular deja saldo negativo o afecta arqueos; un contexto cambiado devuelve 409. No basta reutilizar una aceptación anterior.
GET /particulares/asientos?idContacto=...&fecha=...&importe=... permite elegir una nota particular histórica coincidente; es lectura y no crea movimientos. compraParticular admite idAsientoParticular o confirmarAsientoNuevo para resolver candidatos sin duplicarlos. Los vínculos formales anteriores de la misma compra se reutilizan automáticamente. Los documentos pendientes incluyen esParticular e importePersonal (pesos a TC de factura); el importe pendiente se calcula sobre el bruto previo a la línea interna negativa. No cambia el fiscal ni se crea otra deuda en la cuenta del proveedor.
Un pago particular puede ser parcial o corresponder a una compra con parte empresarial: una sola compra por operación, aplicaciones por lo efectivamente pagado. El gasto del socio y la nota Particular corresponden a la parte personal completa documentada, según 021, y se crean una vez; asignación a fecha de compra, pago físico a fecha de caja. Pagos siguientes enlazan ese soporte. Se bloquea anular la operación que lo creó mientras otros pagos dependan de él.
Confirmar importación acepta aceptarSaldoNegativoLote. Se validan todas las vistas previas antes de aplicar filas; solo se recalculan por cambios internos del propio lote bajo los mismos bloqueos. Capacidades y advertencias se revalidan por fila. Un lote con pendientes conserva Preview, permite continuarlas y no recrea las ya vinculadas; la misma resolución es idempotente. Dos operaciones realmente distintas con igual fecha/importe requieren confirmarDistinto y motivo. Cambios de cuenta/detalle/número de documento también quedan visibles como Modificada respecto de la instantánea anterior.
