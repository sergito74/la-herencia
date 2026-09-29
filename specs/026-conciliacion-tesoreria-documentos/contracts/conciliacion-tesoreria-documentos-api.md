# API: conciliación documental de Tesorería

Prefijo /api/tesoreria. Sesión obligatoria (401); escrituras requieren rol distinto de Lectura (403). Usuario de auditoría obtenido del servidor. Medios: bna, galicia, mercado-libre, efectivo, valores-propios, valores-recibidos. Todas las identidades documentales son compuestas.

## Tipos JSON

Referencia: `{ "origen": "Compras", "idOrigen": 123 }`; origen = Compras|Impuestos|Remuneraciones|Alquileres, idOrigen entero firmado de rango bigint (los IDs heredados pueden ser negativos). Documento: referencia más `fecha: string|null`, `tipoDocumento: string|null`, `numeroDocumento: string|null`, `moneda: string|null`, `tipoDeCambio: number|null`, `importeOriginal: number`, `importePesos: number`, `contraparte: string|null`, `idContacto: integer|null`, `saldoPendiente: number`, `vinculosPrevios: integer`. Saldo siempre en pesos, compartido con Tarjetas para Compras/Impuestos, firmado para NC. Importes originales no se alteran.

Imputado: referencia más `importeImputado: number`. Cálculo: `estado: exacta|parcial`, `diferencia: number`, `pagoParcial: boolean`, `permiteParcial: boolean`, `imputados: Imputado[]`, `tcImplicito: number|null`, `tcReferencia: number|null`, `desvioTc: number|null`. Sugerencia: Cálculo más `documentos: Referencia[]`.

Motivo: `{ "motivo": "Impuesto", "detalle": null }`. Para diferencia: AjusteTipoCambioSinNota|Redondeo|Impuesto|Otro. Sin documento: Impuesto|Interes|CompraNoCargada|Otro. Detalle máximo 255, no vacío si Otro. Motivo máximo 30. Campos extra rechazados en requests nuevos.

Conciliación: `idConciliacion: integer`, `idContacto: integer`, `contacto: string|null`, `importe: number`, `usuario: string`, `fecha: string`, `tipoOrigenDocumento: origen|null`, `idOrigenDocumento: integer|null`.

Auditoría: `idEstado: integer`, `estado: SinDocumento|DiferenciaAceptada`, `motivo: string`, `detalle: string|null`, `importeDiferencia: number|null`, `usuario: string`, `fecha: string`.

## GET /documentos-buscar?q=texto

Texto 2–100 caracteres, hasta 40 resultados. Busca contraparte/número entre cuatro orígenes con saldo disponible. Devuelve Documento[]. Sin coincidencias devuelve [].

## GET /{medio}/movimientos/{id}/candidatos

Hasta 60 documentos pendientes por importe/fecha, aun sin contacto; máximo 5 sugerencias, 18 documentos y combinaciones hasta 4 dentro del motor. Devuelve `{ "documentos": Documento[], "sugerencias": Sugerencia[] }`. Un parcial usa saldo restante. No restringir al contacto automático, pues ese estado bloquea nuevas conciliaciones.

## GET /{medio}/movimientos/{id}/conciliacion-preview?documentos=Compras:123&documentos=Impuestos:123

Parámetro documentos repetido, de 1 a 20 referencias únicas; origen de catálogo y entero firmado. Devuelve Cálculo. Sin escrituras. El ID aislado no identifica el documento. Documentos agotados o cambiados generan conflicto.

## POST /{medio}/movimientos/{id}/conciliacion-lote

Body `{ "documentos": [{"origen":"Compras","idOrigen":123}], "aceptarDiferencia": null }`. De 1 a 20 referencias únicas. aceptarDiferencia es Motivo opcional: permite elegir explícitamente cerrar la excepción, aunque el cálculo permita parcial/cuota. No se exige aceptar para continuar un parcial. Se revalidan saldo y documentos en la transacción común con Tarjetas/manual/traspasos. Total neto de selección positivo, NC con signo, saldo insuficiente o conflicto => rollback completo. Devuelve 201 Conciliación[] creadas por este lote.

Se conservan imputaciones reales calculadas. La diferencia firmada documenta la elección de cerrar el movimiento y no altera deuda fiscal ni inventa pagos sobre documentos. Ejemplos y efecto contable en spec.md.

## POST /{medio}/movimientos/{id}/sin-documento

Body Motivo, respuesta 204. Solo sin conciliaciones previas y sin resolución por otra vía.

## DELETE /{medio}/movimientos/{id}/estado

Respuesta 204. Inserta EstadoQuitado/Revocacion, con usuario/fecha. Idempotente sin estado vigente. No borra vínculos; recalcula el estado según sus importes, que puede seguir conciliado o parcial.

## GET/POST /{medio}/movimientos/{id}/conciliacion (023)

POST manual conserva body contacto+importe positivo; metadata documental NULL. GET mantiene estado, importeTotal, saldoPendiente, conciliaciones, idContactoReconocido, contactoReconocido y agrega `auditoria: Auditoria|null`. Conciliaciones incorpora metadata nullable de forma aditiva. saldoPendiente del movimiento es cero con excepción vigente; al revocarla se recalcula. Los listados suman estado sin_documento.

## Errores y transiciones

400 medio no soportado o motivo inválido; 404 movimiento/documento inexistente; 409 saldo agotado, lote no positivo, movimiento resuelto, cambio concurrente o espera de bloqueo agotada; 422 forma/tamaño/tipo de request inválido. Mensajes de negocio legibles, sin SQL. ya_reconocido/conciliado/traspaso_interno/sin_documento bloquean nueva imputación. parcialmente_conciliado permite continuar documental/manual y bloquea traspasos. SinDocumento solo sin imputaciones; DiferenciaAceptada cierra un parcial. No hay DELETE de conciliaciones.
