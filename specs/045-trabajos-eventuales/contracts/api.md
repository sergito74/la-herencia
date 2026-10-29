# API /api/trabajos-eventuales

GET /: filtros idContacto, desde/hasta, estadoPago, vinculacion (sin/parcial/completo), idSalario; page>=1, pageSize 1..100. Respuesta items,total,page,pageSize,resumen {totalTrabajos,totalVinculado,sinVincular}. Filtro por idSalario muestra solo trabajos asociados. Fechas ISO, dinero numérico en respuesta.
GET /{id}: trabajo, vínculos con período/fecha/neto y origen. GET /{id}/liquidaciones: hasta 200 candidatas del mismo trabajador, neto/capacidad y recibo.
POST /: fecha, idContacto, descripcion, dias,jornal,viaticos,redondeo opcional,estadoPago,numeroRecibo,observaciones. Decimal con límites del modelo; 201 detalle.
PATCH /{id}: mismos campos; 404 inexistente; 409 si viola monto vinculado o cambia trabajador con vínculos.
POST /{id}/vinculos: idSalario,importe>0; 201; 409 si distinto contacto, capacidad insuficiente o vínculo existente.
DELETE /{id}/vinculos/{idSalario}: quita solo ese vínculo y deja auditoría, 404 si no existe. No borra trabajo, liquidación ni pago.
Trabajadores seleccionables: usar GET /api/contactos con tipoContacto=Empleado para nuevos registros.

Sesiones Lectura: GET permitido, escrituras 403 mediante middleware existente. Consultas parametrizadas y paginadas. No SQL libre ni conexión del navegador a SQL Server.

Frontend: menú Personal > Trabajos eventuales; acceso desde cada liquidación con idSalario/empleado; enlaces de vuelta a Remuneraciones con highlight de liquidación. Detalle conserva filtro seleccionado. Estados, errores y vacíos en español de negocio.
