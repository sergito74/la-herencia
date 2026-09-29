# API Contract: Traspasos internos de Tesorería

Prefijo base: `/api/tesoreria/{medio}/movimientos/{idMovimiento}/traspaso-interno`

`medio` es uno de: `bna`, `galicia`, `mercado-libre`, `efectivo`,
`valores-propios`, `valores-recibidos` (FR-002). `tarjetas` responde `400`.

## GET /api/tesoreria/{medio}/movimientos/{idMovimiento}/traspaso-interno

Estado del vínculo de traspaso interno de un movimiento, y candidatas
sugeridas si no está vinculado ni resuelto por otra vía.

**Response 200** (vinculado):

```json
{
  "vinculado": true,
  "contraparte": {
    "medio": "galicia",
    "idMovimiento": 2151,
    "fecha": "2024-10-10",
    "descripcion": "Debito Debin Preautorizado",
    "importe": 17595.82
  },
  "idEvento": 42,
  "usuario": "sgiamberardini",
  "fecha": "2026-09-28T12:00:00"
}
```

**Response 200** (sin vincular, con sugerencias — FR-005):

```json
{
  "vinculado": false,
  "contraparte": null,
  "candidatas": [
    {
      "medio": "galicia",
      "idMovimiento": 2151,
      "fecha": "2024-10-10",
      "descripcion": "Debito Debin Preautorizado",
      "importe": 17595.82
    }
  ]
}
```

`candidatas` viene vacío si el movimiento ya está resuelto por otra vía
(`ya_reconocido`/`conciliado`/`parcialmente_conciliado`) — en ese caso el
frontend no debe ofrecer la acción de vincular (mismo criterio que 023
con `ya_reconocido`).

## POST /api/tesoreria/{medio}/movimientos/{idMovimiento}/traspaso-interno

Aplica el vínculo con la contraparte elegida.

**Request body**:

```json
{ "medioB": "galicia", "idMovimientoB": 2151 }
```

**Response 201**: misma forma que el GET vinculado.

**Errores**:

| Status | Motivo |
|---|---|
| 400 | `medio`/`medioB` es `tarjetas`, o `(medio, idMovimiento) == (medioB, idMovimientoB)` (FR-009) |
| 404 | alguno de los dos movimientos no existe |
| 409 | `medio`/`idMovimiento` ya está resuelto por otra vía (ya reconocido, conciliado, o ya vinculado a un tercer movimiento) |
| 409 | `medioB`/`idMovimientoB` (la contraparte) ya está resuelto por otra vía — misma validación, simétrica (Clarifications 2026-09-28) |

## DELETE /api/tesoreria/{medio}/movimientos/{idMovimiento}/traspaso-interno

Deshace el vínculo activo del movimiento, si existe (FR-010).

**Response 200**: `{ "vinculado": false, "contraparte": null, "candidatas": [] }`

**Errores**: `404` si no había ningún vínculo activo para deshacer.

## Relación con 023-conciliacion-tesoreria y con el listado de Tesorería

- `GET /api/tesoreria/{medio}/movimientos` (003/023) extiende
  `estadoConciliacion` con el 5.º valor `traspaso_interno` (data-model.md).
- `POST /api/tesoreria/{medio}/movimientos/{id}/conciliacion` (023) pasa a
  rechazar con `409` un movimiento que ya tiene `traspaso_interno` activo
  (FR-007) — mismo mecanismo de `esta_resuelto` en ambos sentidos.
