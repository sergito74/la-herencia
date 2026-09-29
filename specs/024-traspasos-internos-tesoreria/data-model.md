# Data Model: Traspasos internos de Tesorería

## Entidad nueva: `TraspasosInternosTesoreria`

Insert-only — cada fila es un evento (`Vincular` o `Deshacer`), nunca un
estado mutable (research.md §1).

| Columna | Tipo | Notas |
|---|---|---|
| `IdEvento` | int identity, PK | |
| `MedioA` | varchar(20) | uno de los 6 medios soportados (mismo dominio que `ConciliacionesTesoreria.Medio`, sin `tarjetas`) |
| `IdMovimientoA` | bigint | id del movimiento en su tabla de origen |
| `MedioB` | varchar(20) | ídem, la contraparte |
| `IdMovimientoB` | bigint | ídem |
| `Accion` | varchar(10) | `Vincular` \| `Deshacer` |
| `Usuario` | varchar | quién (FR-013) |
| `Fecha` | datetime, default `getdate()` | cuándo (FR-013) |

**Validaciones (en el repository)**:
- `MedioA`/`MedioB` deben ser de los 6 medios soportados (FR-002).
- `(MedioA, IdMovimientoA)` ≠ `(MedioB, IdMovimientoB)` (FR-009: no vincular un movimiento consigo mismo).
- Al vincular (`Accion='Vincular'`): ni A ni B pueden estar ya `resueltos` (research.md §2) por ninguna vía, incluida una vinculación de traspaso interno ya activa con un tercer movimiento (FR-006/FR-008, validación simétrica).
- Al deshacer (`Accion='Deshacer'`): debe existir un vínculo activo para ese par; deshacer uno inexistente se rechaza.

**Vínculo activo de un movimiento** (nunca almacenado, siempre calculado):

```
SELECT TOP 1 *
FROM TraspasosInternosTesoreria
WHERE (MedioA=? AND IdMovimientoA=?) OR (MedioB=? AND IdMovimientoB=?)
ORDER BY IdEvento DESC
```

Si la fila de mayor `IdEvento` para ese movimiento tiene `Accion='Vincular'`,
el vínculo está activo (con esa contraparte); si es `'Deshacer'`, no lo está.

## Estado unificado de un movimiento de Tesorería (extiende 023)

Función central `esta_resuelto(medio, id_movimiento)` (research.md §2),
devuelve uno de 5 valores — los 4 que ya definió 023 más el nuevo:

```
"ya_reconocido"           — origen automático habitual (023)
"conciliado"              — conciliación completa a un contacto (023)
"parcialmente_conciliado" — conciliación parcial a uno o más contactos (023)
"traspaso_interno"        — vínculo activo de este módulo (024)   ← NUEVO
"sin_conciliar"           — ninguna de las anteriores
```

Un movimiento con `traspaso_interno` NUNCA puede tener a la vez
`conciliado`/`parcialmente_conciliado` ni viceversa (FR-006/FR-007/SC-005)
— la función evalúa en orden y las escrituras de ambos módulos (023 y 024)
validan contra el resultado de esta misma función antes de escribir.

## Entidades de solo lectura (sin cambios de esquema)

- **Movimiento de Tesorería**: igual que en 023 — este módulo tampoco
  escribe nunca sobre las tablas de origen (`Movimientos BNA`, `Movimientos
  Galicia`, `Movimientos Mercado Libre`, `Pagos efectivo`, `Valores
  propios`, `Valores Recibidos`).
