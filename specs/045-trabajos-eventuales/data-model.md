# Modelo de datos

TrabajosEventuales: IdTrabajo identity; IdContacto int requerido; Fecha date; Descripcion nvarchar(500) no vacía; Dias decimal(12,4)>=0 (alta nueva exige >0); Jornal decimal(18,2)>=0; Viaticos decimal(18,2)>=0; Redondeo decimal(18,2) explícito; Total decimal(18,2)>=0 (cero solo histórico cancelado) = ROUND(Dias*Jornal+Viaticos,2)+Redondeo; EstadoPago varchar(10) Pendiente/Pagado; NumeroRecibo nvarchar(40) nullable; Observaciones nvarchar(1000); OrigenClave nvarchar(180) nullable único filtrado (identidad de fuente/hoja/fila, independiente del SHA de una nueva lectura); Creado/Actualizado/Usuario. Un origen ya cargado no se pisa si cambia la fuente.

TrabajosEventualesVinculos: IdVinculo identity; IdTrabajo; IdSalario; Importe decimal(18,2)>0; Creado/Usuario; par único. Capacidad por trabajo = Total - SUM(vínculos); por liquidación = neto Remuneraciones - SUM(vínculos); mismo contacto. Revalidación dentro de transacción antes de insertar/quitar. Operación repetida devuelve conflicto, nunca duplica silenciosamente.

TrabajosEventualesAuditoria: Id identity; IdTrabajo nullable; Accion; Datos nvarchar(max) JSON antes/después; Usuario; Fecha. Incluye importación y vínculos.

TrabajosEventualesFuentes: Clave nvarchar(180) PK; SHA256; Ruta; Datos nvarchar(max) JSON con hojas auxiliares/cabeceras/detalles; Creado. Padrón fiscal se conserva como evidencia sin generar deudas.

Estados: pago manual/declarado independiente de vinculación calculada (Sin vincular, Parcial, Vinculado). Total filtrado y suma vinculada no se suman entre sí. Sin vínculo no significa impago.


## Ampliación solicitada por Sergio: adicional de Sierra (29/10/2026)
Incorporar en Remuneraciones cálculo del adicional fuera de recibo de Sierra, Antonio Marcelo, basado en `Personal/Remuneraciones modif..xlsx`, hoja Liquidaciones Encargado, columnas AF:AK: AG=MROUND(AF*30%,5), AH=MROUND(AF*8.5%,5), AJ=AG+AH+AI, siendo AI ajuste manual variable y AF neto del recibo. Se usa el neto fiscal real de la liquidación, excluyendo la Bonificación adicional ya registrada; no se extrapolan los brutos calculados de la planilla vieja. El archivo llega hasta agosto 2026 y no contiene octubre.

Presentar cada parte y el total a cobrar; permitir guardar en la columna existente Bonificacion adicional de esa misma liquidación, manteniendo los conceptos fiscales intactos y sin crear otro recibo/pago. Antes de guardar muestra el adicional actual. Calcular no guarda. Tabla auxiliar RemuneracionesAdicionalCalculo por IdSalario conserva componentes, ajuste, usuario y fecha; auditoría de la operación en tabla 045. Al consultar una liquidación histórica con adicional existente, mostrar el importe registrado junto al cálculo propuesto; nunca recalcular/grabar históricos en bloque. Sergio eligió redondear el total automáticamente hacia arriba a la centena. Se mantiene el redondeo individual a múltiplos de $5; el ajuste final pasa a ser la diferencia hasta la centena (si ya es centena exacta no se agrega otra). No hay ajuste manual en pantalla. Calcular no cambia datos: Guardar adicional aplica el resultado a la liquidación seleccionada. Límites de trabajos vinculados se revalidan antes de modificar total.

Hallazgo adicional de fuente de eventuales: fila 47 cancelada por lluvia tiene cero días y cero importe. Se conserva como antecedente dentro de los 75 registros, sin vínculo posible; esquema admite cero histórico, alta nueva exige días y total positivos. Una descripción ausente se presenta como Sin descripción en la planilla, sin inventar labor.
