# Contrato interno: lector general

`evaluar(texto, pdf, id_contacto) -> Evaluacion`, sin escrituras.

- `cargable: bool`
- `datos: DatosCompra | None`, presente solo si es cargable
- `motivo: str | None`, en palabras de negocio si no es cargable

Motivos: "Los importes no cierran con el total", "No se pudieron leer todos los datos de la factura", "El código de la factura no coincide con su texto", "El proveedor no tiene tres facturas con la misma imputación", "La campaña habitual ya no está vigente", "Este proveedor mueve stock: cargar a mano", "Factura en dólares sin tipo de cambio", "Falta la factura asociada".

Orden en la rutina: lector específico → lector general (si está activo) → para cargar a mano. Con el lector apagado no cambia ningún comportamiento.
