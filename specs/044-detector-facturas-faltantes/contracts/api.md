# Contrato API: /api/facturas-faltantes

Todas las respuestas en pesos con importes decimales como número; sin ids internos visibles en UI (los ids viajan solo para enlaces/acciones).

## GET /tablero?mes=YYYY-MM (default: mes actual)
```json
{ "mes": "2026-10", "items": [
  { "idContacto": 71, "proveedor": "Movistar", "ciclo": "mensual", "cicloFijado": false,
    "estado": "llego|pendiente|atrasada|baja", "periodoDesde": "2026-10-01", "periodoHasta": "2026-10-31",
    "fechaEsperada": "2026-10-14", "montoEsperado": 243640.80, "cambioMonto": false,
    "ultimo": { "idDeuda": 1, "numero": "2467-01676367", "fecha": "2026-10-14", "importe": 243640.80 },
    "pagoSinComprobante": { "origen": "galicia", "idPago": 3, "fecha": "...", "importe": 1 } | null,
    "faltantesHistoricos": [ { "periodoDesde": "2025-06-01", "periodoHasta": "2025-06-30", "montoEsperado": 1 } ] } ],
  "resumen": { "llegaron": 0, "pendientes": 0, "atrasadas": 0, "bajas": 0 } }
```

## GET /alarmas?tipo=&page=&pageSize= (pageSize ≤ 200)
Item: `{ clave, tipo: "pago-sin-factura|saldo-a-favor|retencion-sin-factura|remito-sin-factura", idContacto, proveedor, fecha, importe, detalle, origen: { medio, id } }`. Excluye descartadas y las convertidas en marca abierta. Rótulo de UI: "A verificar".

## POST /alarmas/{clave}/descartar  body `{ "motivo": "..." }` → 204. Motivo 1–255 obligatorio.

## GET /marcas?estado=abierta|cerrada
## POST /marcas  body `{ idContacto, origenPago, idPago, periodoDesde?, periodoHasta?, importeAprox? }` → marca. 409 si ya hay una abierta para el pago.
## POST /marcas/{id}/anular  body `{ "motivo": "..." }` → 204; anula una marca abierta.

## PUT /perfil/{idContacto}  body `{ cicloDias: 30|60|90|null, sinCiclo: bool, margenDias: int|null }`
## POST /perfil/{idContacto}/baja  body `{ dadoDeBaja: bool }`

## GET /resumen-mensual (para la rutina 043)
`{ "mostrar": true (día ≥ 5), "mes": "2026-09", "atrasadas": 3, "proveedores": ["Movistar", ...] }`

## GET /pago-sin-factura?origen=&idPago= → `{ "sinAplicar": true, "puedeMarcar": true }` (aviso del formulario de pagos)

Errores: 404 contacto/marca inexistente; 409 conflicto; 422 validación; escrituras requieren rol con permiso (SoloLectura → 403).
