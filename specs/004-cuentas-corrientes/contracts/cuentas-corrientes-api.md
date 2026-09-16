# API Contract: Cuentas corrientes (solo lectura)

Prefijo base: `/api/cuentas-corrientes`

Todos los endpoints son `GET`. Ningún endpoint admite escritura (FR-010).

## GET /api/cuentas-corrientes/contactos

Busca contactos por razón social y/o tipo (FR-001, FR-002).

**Query params**: `q` (razón social, búsqueda parcial), `tipoContacto` (opcional).

**Response 200**:

```json
{
  "items": [
    { "idContacto": 42, "razonSocial": "Rutas Sur Atlantico S.A.", "tipoContacto": "Proveedor" }
  ]
}
```

## GET /api/cuentas-corrientes/contactos/{idContacto}/saldo

Saldo actual del contacto (FR-003).

**Response 200**:

```json
{ "idContacto": 42, "saldoParcial": -60500.00 }
```

## GET /api/cuentas-corrientes/contactos/{idContacto}/movimientos

Movimientos de cuenta corriente del contacto (FR-004, FR-005, FR-012, FR-013, FR-014).

**Query params**: `fechaDesde`, `fechaHasta`, `page`, `pageSize`.

**Response 200**:

```json
{
  "items": [
    {
      "fecha": "2026-08-05",
      "documento": "Factura A",
      "numeroDocumento": "0001-00012345",
      "deuda": 60500.00,
      "credito": 0,
      "origen": {
        "tipo": "compra",
        "idCompra": 12345,
        "numeroDocumento": "0001-00012345",
        "proveedor": "Rutas Sur Atlantico S.A."
      }
    },
    {
      "fecha": "2026-08-10",
      "documento": "Pago",
      "numeroDocumento": "REC-001",
      "deuda": 0,
      "credito": 60500.00,
      "origen": {
        "tipo": "no_disponible",
        "motivo": "IdOrigen sin cargar"
      }
    }
  ],
  "page": 1,
  "pageSize": 50,
  "total": 123
}
```

`origen.tipo` MUST ser uno de `"compra"`, `"tesoreria"`, `"fuera_de_alcance"`, `"no_disponible"` — nunca omitido (FR-008, FR-008b, SC-002). El frontend MUST NOT mostrar ni derivar imputación (rubro/centro de costo/destino) a partir de `origen` (FR-009, SC-004).

Cuando `origen.tipo` es `"tesoreria"`, `origen.medio` MUST ser uno de `"bna"`, `"galicia"`, `"efectivo"`, `"valores_recibidos"` (ver mapeo cerrado en `data-model.md`) — nunca un valor libre derivado directamente de la columna SQL `Origen`.

Ejemplo de movimiento con origen en tesorería (medio efectivo, sin contacto propio en `dbo.[Pagos efectivo]` — la resolución es directa por `idOrigen`, no heurística):

```json
{
  "fecha": "2026-08-12",
  "documento": "Pago",
  "numeroDocumento": "EF-0007",
  "deuda": 0,
  "credito": 15000.00,
  "origen": {
    "tipo": "tesoreria",
    "medio": "efectivo",
    "idMovimiento": 987,
    "fecha": "2026-08-12",
    "importe": 15000.00
  }
}
```

Ejemplo de movimiento fuera de alcance:

```json
{
  "fecha": "2026-08-15",
  "documento": "Alquiler",
  "numeroDocumento": "ALQ-0042",
  "deuda": 0,
  "credito": 85000.00,
  "origen": { "tipo": "fuera_de_alcance", "origenTipo": "Alquileres" }
}
```
