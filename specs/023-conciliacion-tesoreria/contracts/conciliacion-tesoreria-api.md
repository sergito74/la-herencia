# API Contract: Conciliación de Tesorería

Prefijo base: `/api/tesoreria/{medio}/movimientos/{idMovimiento}/conciliacion`

`medio` es uno de: `bna`, `galicia`, `mercado-libre`, `efectivo`,
`valores-propios`, `valores-recibidos` (FR-002). `tarjetas` responde `400`
con un mensaje explicando que ese medio se concilia desde 008/009.

## GET /api/tesoreria/{medio}/movimientos/{idMovimiento}/conciliacion

Estado de conciliación de un movimiento puntual (FR-009) — sin conciliar,
parcialmente conciliado (con saldo pendiente) o conciliado por completo —
y el detalle de las conciliaciones ya aplicadas (FR-011).

**Response 200**:

```json
{
  "estado": "parcialmente_conciliado",
  "importeTotal": 60500.00,
  "saldoPendiente": 15500.00,
  "conciliaciones": [
    {
      "idConciliacion": 88,
      "idContacto": 42,
      "contacto": "Rutas Sur Atlantico S.A.",
      "importe": 45000.00,
      "usuario": "sgiamberardini",
      "fecha": "2026-09-28T11:04:00"
    }
  ]
}
```

`estado` es uno de: `sin_conciliar`, `parcialmente_conciliado`,
`conciliado`, o **`ya_reconocido`** — este último cuando el movimiento ya
tiene un `IdContacto` por su origen automático habitual (no por este
módulo); en ese caso `conciliaciones` viene vacío y el frontend dirige a
022-reasignación-contacto en vez de ofrecer conciliar de nuevo (FR-008).

## POST /api/tesoreria/{medio}/movimientos/{idMovimiento}/conciliacion

Aplica una conciliación — el caso simple (Historia 1) es un único POST con
`importe` igual al `saldoPendiente` completo; un reparto (Historia 2) es
más de un POST, uno por contacto, en la misma sesión o en sesiones
distintas (Clarifications 2026-09-28).

**Request body**:

```json
{
  "idContacto": 42,
  "importe": 45000.00
}
```

**Response 201** (misma forma que una fila de `conciliaciones` en el GET):

```json
{
  "idConciliacion": 88,
  "idContacto": 42,
  "contacto": "Rutas Sur Atlantico S.A.",
  "importe": 45000.00,
  "usuario": "sgiamberardini",
  "fecha": "2026-09-28T11:04:00"
}
```

**Errores**:

| Status | Motivo |
|---|---|
| 400 | `medio` es `tarjetas`, o el `idContacto` no existe, o `importe` ≤ 0 |
| 404 | el movimiento (`medio` + `idMovimiento`) no existe |
| 409 | el movimiento ya está `ya_reconocido` (FR-008) — el mensaje dirige a 022-reasignación-contacto |
| 409 | `importe` excede el `saldoPendiente` recalculado en el momento de la escritura (FR-010 — dos usuarios conciliando el mismo saldo a la vez) |

## Relación con endpoints ya existentes

- `GET /api/tesoreria/{medio}/movimientos` (003-tesoreria, sin cambios de
  contrato) agrega, para los medios cubiertos por este feature, un campo
  `estadoConciliacion` por ítem (mismos 4 valores que el GET de arriba) —
  así el listado puede distinguir visualmente los tres estados sin una
  llamada aparte por fila (FR-009).
- `GET /api/tesoreria/{medio}/movimientos/{id}/referencia` (003-tesoreria,
  sin cambios) sigue devolviendo la sugerencia automática de "Referencia de
  origen"; el frontend la usa para pre-completar `idContacto`/`importe`
  antes de hacer el POST de conciliación (FR-007), pero es una integración
  de UI, no un cambio de contrato en ese endpoint.
- La corrección de una conciliación ya aplicada (FR-008a) usa el contrato
  ya existente de 022 (`POST /api/reasignacion-contacto/reasignar`) con
  `origen = "Conciliación Tesorería"` e `idOrigen = idConciliacion` — sin
  un endpoint nuevo para esto.
