# API Contract: Tesorería (solo lectura)

Prefijo base: `/api/tesoreria`

Todos los endpoints de consulta son `GET`. El endpoint de Excel es `POST` pero MUST NOT persistir nada en SQL Server (solo valida/previsualiza).

## GET /api/tesoreria/medios

Lista los medios de tesorería disponibles para seleccionar (FR-001).

**Response 200**:

```json
{
  "medios": ["bna", "galicia", "efectivo", "valores-propios", "valores-recibidos", "tarjetas"]
}
```

## GET /api/tesoreria/{medio}/movimientos

Lista movimientos de un medio, con la forma propia de ese medio (FR-002, FR-003, FR-012, FR-013).

**Query params**: `fechaDesde`, `fechaHasta`, `page`, `pageSize` (mismas reglas que en compras).

**Response 200** (ejemplo para `bna`):

```json
{
  "items": [
    {
      "idMovimientoBNA": 555,
      "fechaHora": "2026-08-05T10:15:00",
      "concepto": "Transferencia",
      "importe": -60500.00,
      "contacto": { "idContacto": 42, "razonSocial": "Rutas Sur Atlantico S.A." }
    }
  ],
  "page": 1,
  "pageSize": 50,
  "total": 9386
}
```

La forma exacta del objeto en `items` varía por medio (ver `data-model.md`); el frontend renderiza columnas específicas por medio.

## GET /api/tesoreria/{medio}/movimientos/{id}/referencia

Referencia (heurística) a la compra de origen de un movimiento puntual (FR-004, FR-005).

**Response 200**:

```json
{
  "estado": "coincidencia_unica",
  "candidatas": [
    {
      "idCompra": 12345,
      "numeroDocumento": "0001-00012345",
      "proveedor": "Rutas Sur Atlantico S.A.",
      "fecha": "2026-08-01",
      "importe": 60500.00
    }
  ]
}
```

`estado` MUST ser uno de `"sin_coincidencia"`, `"coincidencia_unica"`, `"ambigua"`. El frontend MUST renderizar cada estado de forma distinta y explícita (FR-005, SC-002).

Para `medio = "valores-propios"`, este endpoint MUST devolver siempre `{"estado": "sin_coincidencia", "candidatas": []}`, ya que ese medio no tiene campo de contacto para aplicar la heurística (clarificación 2026-09-16).

## POST /api/tesoreria/excel/validar

Sube un archivo Excel de resumen bancario o de tarjeta, valida su estructura y devuelve una previsualización (FR-007, FR-008, FR-009). No persiste nada.

**Request**: `multipart/form-data`, campo `archivo` (`.xlsx` para Galicia, `.xls` binario antiguo para BNA — ambos formatos confirmados contra archivos reales el 2026-09-16).

**Response 200** (archivo BNA válido — nótese que BNA trae 5 filas de metadata antes del encabezado real, e importes como texto con formato argentino que el backend parsea a número):

```json
{
  "medioDetectado": "bna",
  "valido": true,
  "errores": [],
  "movimientosPrevisualizados": [
    { "fecha": "2026-01-19", "comprobante": "81415", "concepto": "PLAZO FIJO", "importe": 5107397.26, "saldo": 3230108.83 }
  ]
}
```

**Response 200** (archivo Galicia válido — sin columna de contacto estructurada, el contraparte queda en `leyendas` tal cual):

```json
{
  "medioDetectado": "galicia",
  "valido": true,
  "errores": [],
  "movimientosPrevisualizados": [
    {
      "fecha": "2026-08-20",
      "descripcion": "Trf Inmed Proveed",
      "debitos": 46044.04,
      "creditos": 0,
      "numeroComprobante": "57808209",
      "leyendas": ["Jauregui Y Morales", "30545419110", "FACTURAS", null],
      "saldo": 774943.40
    }
  ]
}
```

**Response 200** (archivo inválido — se informa igual con `valido: false`, no HTTP error, para poder mostrar el detalle en UI):

```json
{
  "medioDetectado": null,
  "valido": false,
  "errores": ["No se encontró la fila de encabezado esperada ('Fecha, Comprobante, Concepto, Importe, Saldo' para BNA, o 'Fecha, Descripción, ...' para Galicia) en las primeras 10 filas"],
  "movimientosPrevisualizados": []
}
```
