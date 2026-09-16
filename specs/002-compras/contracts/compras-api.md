# API Contract: Compras (solo lectura)

Prefijo base: `/api/compras`

Todas las respuestas son JSON. Todos los endpoints son `GET`. Ningún endpoint de este contrato admite creación, edición ni borrado (FR-010).

## GET /api/compras

Busca y lista compras (FR-001, FR-002, FR-012, FR-013).

**Query params**:

| Param | Tipo | Requerido | Notas |
|---|---|---|---|
| proveedor | string | no | Búsqueda parcial por razón social |
| numeroDocumento | string | no | Búsqueda exacta o parcial por número de documento |
| fechaDesde | date (ISO) | no | |
| fechaHasta | date (ISO) | no | |
| page | int | no (default 1) | |
| pageSize | int | no (default 50, máx 200) | |

**Response 200**:

```json
{
  "items": [
    {
      "idCompra": 12345,
      "fecha": "2026-08-01",
      "proveedor": { "idContacto": 42, "razonSocial": "Rutas Sur Atlantico S.A." },
      "tipoDocumento": "Factura A",
      "numeroDocumento": "0001-00012345"
    }
  ],
  "page": 1,
  "pageSize": 50,
  "total": 6436
}
```

Si no hay resultados, `items` es `[]` y el frontend MUST mostrar el estado vacío (FR-012), no un error.

## GET /api/compras/{idCompra}

Detalle completo de una compra, incluidas sus líneas e imputación (FR-003, FR-004, FR-006, FR-007).

**Response 200**:

```json
{
  "idCompra": 12345,
  "fecha": "2026-08-01",
  "proveedor": { "idContacto": 42, "razonSocial": "Rutas Sur Atlantico S.A." },
  "tipoDocumento": "Factura A",
  "numeroDocumento": "0001-00012345",
  "conceptosNoGravados": 0,
  "ingresosBrutos": 150.50,
  "lineas": [
    {
      "idDetalleCompra": 98765,
      "productoServicio": "Flete",
      "cantidad": 1,
      "precioUnitario": 50000,
      "iva": 10500,
      "imputacion": {
        "idRubro": 7,
        "rubro": "Transporte",
        "idCentroCosto": 3,
        "centroCosto": "Campo Norte",
        "idDestino": 12,
        "destino": "Cosecha Norte",
        "idCampania": 4,
        "campania": "Cosecha 2026"
      }
    },
    {
      "idDetalleCompra": 98766,
      "productoServicio": "Servicio sin imputar",
      "cantidad": 1,
      "precioUnitario": 1000,
      "iva": 210,
      "imputacion": null
    }
  ]
}
```

`imputacion: null` indica explícitamente que esa línea no tiene rubro/centro de costo/destino asignado (FR-006) — el frontend MUST distinguir esto de un error.

**Response 404**: compra no encontrada.

## GET /api/compras/{idCompra}/trazabilidad

Referencia a los movimientos de cuenta corriente/tesorería originados por la compra, vía `IdOrigen` (FR-008, FR-009).

**Response 200**:

```json
{
  "idCompra": 12345,
  "movimientos": [
    {
      "origenTipo": "Compra",
      "idOrigen": 12345,
      "documento": "0001-00012345",
      "fecha": "2026-08-05",
      "importe": 60500.00,
      "tipoImporte": "Deuda"
    }
  ]
}
```

Si `movimientos` es `[]`, el frontend MUST mostrar "sin movimientos asociados todavía" (FR-009), no un error ni una lista vacía sin contexto.
