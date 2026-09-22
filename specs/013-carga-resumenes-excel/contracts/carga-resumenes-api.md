# API Contract: Confirmación de carga de resúmenes bancarios (013)

Extiende `specs/003-tesoreria/contracts/tesoreria-api.md`. Prefijo base: `/api/tesoreria`.

## POST /api/tesoreria/excel/confirmar

Reprocesa el archivo subido (FR-002), detecta duplicados (FR-003, research.md §2) y persiste los movimientos nuevos en `WC` dentro de una transacción (FR-005). Reusa exactamente el mismo parseo que `POST /api/tesoreria/excel/validar` — si el archivo ya no valida (FR-010), responde 422 sin escribir nada.

**Request**: `multipart/form-data`, campo `archivo` (mismo formato que `/excel/validar`).

**Response 200**:

```json
{
  "banco": "bna",
  "idCarga": 12,
  "insertados": 37,
  "omitidosDuplicado": 3,
  "omitidosIncompletos": 0,
  "total": 40
}
```

**Response 422** (archivo inválido o formato no reconocido, mismo `errores` que `/excel/validar`):

```json
{
  "valido": false,
  "errores": ["No se encontró la fila de encabezado esperada..."]
}
```

## POST /api/tesoreria/excel/previsualizar-confirmacion

Paso intermedio de la Historia 3 (FR-004): igual que `/excel/validar`, pero además marca cada movimiento previsualizado como `nuevo` u `omitidoDuplicado` sin escribir nada, para que el usuario vea el conteo antes de confirmar.

**Request**: igual que `/excel/validar`.

**Response 200**:

```json
{
  "medioDetectado": "bna",
  "valido": true,
  "errores": [],
  "resumen": { "nuevos": 37, "omitidosDuplicado": 3, "omitidosIncompletos": 0, "total": 40 },
  "movimientosPrevisualizados": [
    { "fecha": "2026-01-19", "comprobante": "81415", "concepto": "PLAZO FIJO", "importe": 5107397.26, "saldo": 3230108.83, "estado": "nuevo" },
    { "fecha": "2026-01-20", "comprobante": "81416", "concepto": "IMPUESTO SELLOS", "importe": -1200.00, "saldo": 3228908.83, "estado": "omitidoDuplicado" }
  ]
}
```

## GET /api/tesoreria/{medio}/cargas

Historial de cargas confirmadas de un banco (FR-009). `medio` ∈ `bna`, `galicia`.

**Response 200**:

```json
{
  "items": [
    { "idCarga": 12, "nombreArchivo": "BNA_agosto_2026.xls", "fechaHoraCarga": "2026-09-22T14:03:00Z", "insertados": 37, "omitidosDuplicado": 3, "omitidosIncompletos": 0 }
  ]
}
```

## GET /api/tesoreria/{medio}/movimientos (extensión de 003)

Cada movimiento devuelto MUST incluir `idCarga: number | null` cuando fue importado por esta vía (FR-008), reusando el `JOIN` contra `CargasResumenBancario_Movimientos`. `null` para movimientos que no vienen de una carga Excel (carga manual histórica).
