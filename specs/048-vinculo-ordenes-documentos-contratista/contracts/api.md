# API Contract: 048

Todos los importes van como número (el frontend los formatea con los helpers de moneda). Ninguna respuesta se muestra con ids internos: los ids viajan solo para operar.

## Desde la orden

### GET /api/ordenes/{idOrden}/documentos-contratista

```json
{
  "contratista": "Perez, Claudio",
  "documentos": [
    { "idCompra": 2143525198, "tipo": "Factura", "numero": "00002-00000735", "fecha": "2026-11-05",
      "moneda": "Pesos", "hectareas": 198.0, "netoRepartible": 2376000.0,
      "vinculada": false, "vinculadaAOtras": [], "sugerida": true, "rotulo": "coincide" }
  ]
}
```

Solo documentos de labor del contratista de la orden (R1), del más nuevo al más viejo: primero los vinculados y sugeridos. Si la orden es de maquinaria propia o no tiene documentos: `documentos: []`.

### PUT /api/ordenes/{idOrden}/documentos-contratista

Body: `{ "idsCompra": [2143525198] }`. Deja vinculados exactamente esos documentos a la orden: agrega y quita, y recalcula y aprueba el reparto de cada documento afectado. 200 → `{ "repartos": [{ "idCompra", "total", "fracciones": [{ "lote", "cultivo", "campania", "importe" }] }] }`. 422 si algún documento no es de labor, es de otro contratista o es una NC/ND (las NC/ND se relacionan con su factura). 403 para solo lectura.

Los endpoints viejos `POST /{id}/factura-contratista` y `DELETE /{id}/factura-contratista/{idCompra}` se mantienen y delegan en la misma lógica.

## Revisión del histórico

### GET /api/ordenes/contratistas/revision?idContratista=&estado=

`estado` ∈ `sin_revisar | vinculada | descartada | sin_orden | todas` (por defecto `sin_revisar`).

```json
{ "contratistas": [{ "idContacto": 467, "nombre": "Perez, Claudio", "pendientes": 3 }],
  "facturas": [
    { "idCompra": 2143515170, "numero": "00002-00000691", "fecha": "2025-10-03", "hectareas": 214.0,
      "netoRepartible": 2022514.0, "estado": "sin_revisar", "rotulo": "cerca", "difHectareasPct": 7.4,
      "ordenesPropuestas": [{ "idOrden": 141, "fecha": "2025-09-15", "labor": "Pulverizacion terrestre", "hectareas": 231.1 }] }
  ] }
```

### POST /api/ordenes/contratistas/revision/{idCompra}/confirmar

Body: `{ "idsOrden": [141] }` (puede corregir la propuesta). Igual que el PUT de la orden, pero visto desde la factura.

### POST /api/ordenes/contratistas/revision/{idCompra}/descartar

Body: `{ "motivo": "propuesta_incorrecta" | "sin_orden", "observacion": "..." }`.

### DELETE /api/ordenes/contratistas/revision/{idCompra}/descarte

Reabre la factura.

### POST /api/ordenes/contratistas/revision/{idNc}/relacionar

Body: `{ "idFactura": 2143515170 }`. Relaciona una NC/ND del contratista con su factura (en `CompraDocumentosRelacionados`) y, si la factura está vinculada, imputa la NC/ND con sus proporciones. 422 si la factura no es de labor o es de otro contratista.

### GET /api/ordenes/contratistas/sin-orden y GET /api/ordenes/contratistas/sin-orden/exportar

Detalle de FR-008a: facturas en estado `sin_orden`, o históricas sin propuesta, con sus renglones (rubro, concepto, cantidad, unidad, neto, cultivo/destino y campaña cargados a mano). La versión `/exportar` devuelve un .xlsx.

## Resultado por cultivo (sin contrato nuevo)

`costos_contratista` devuelve las mismas claves que hoy (`concepto`, `rubro`, `montoPesos`, `montoDolares`, `origen`, `idCompra`, `idDetalleCompra`, `idOrdenTrabajo`), ahora tomadas de las fracciones aprobadas.
