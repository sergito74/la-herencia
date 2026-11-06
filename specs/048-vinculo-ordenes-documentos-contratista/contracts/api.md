# API Contract: 048 (revisado 06/11)

## Compras

### GET /api/compras/{idCompra}/ordenes-trabajo

```json
{ "esDocumentoDeLabor": true, "esNotaCreditoDebito": false,
  "ordenes": [ { "idOrden": 162, "fecha": "2026-10-25", "labor": "Pulverizacion terrestre",
                 "lotes": "3A, 5", "hectareas": 198.0, "vinculada": true, "tieneOtraFactura": false } ],
  "reparto": [ { "lote": "3A", "cultivo": "Soja", "campania": "26/27", "importe": 1188000.0 } ] }
```

Si no es documento de labor o es una NC/ND: `ordenes: []` y el flag correspondiente (la UI explica por qué).

### PUT /api/compras/{idCompra}/ordenes-trabajo

Body `{ "idsOrden": [162] }`. Deja vinculadas exactamente esas órdenes, imputa y aprueba. 200 → `{ reparto }`. 422 si el documento no es de labor, es una NC/ND o alguna orden no es de ese contratista. 403 para solo lectura.

### Relacionados (existentes)

`agregar/quitar` documento relacionado: sin cambio de contrato; además recalculan la imputación de la NC/ND (R4).

## Órdenes

### GET /api/ordenes/{idOrden} (existente)

`facturasContratista` pasa a traer, por documento: `idCompra`, `tipoDocumento`, `numeroDocumento`, `fecha`, `neto`, `moneda` y `notasRelacionadas` (con los mismos campos), más `reparto` de la orden. Solo lectura. Se eliminan `POST /api/ordenes/{id}/factura`, `POST /{id}/factura-contratista` y `DELETE /{id}/factura-contratista/{idCompra}`.

## Sin orden

### GET /api/ordenes/contratistas/sin-orden · GET .../sin-orden/exportar

Facturas de labor sin vínculo: contratista, fecha, número, moneda y renglones (rubro, concepto, cantidad, unidad, neto, cultivo/destino y campaña cargados a mano), más `idCompra` para el enlace. `/exportar` devuelve un .xlsx.
