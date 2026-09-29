# Data Model: Reasignación de contacto en movimientos de cuenta corriente

## `ReasignacionesContacto` (nueva, insert-only)

El "Movimiento reasignable" y la "Reasignación" de spec.md son, en la base, una sola tabla append-only: cada fila **es** una reasignación aplicada, y el conjunto de filas para un `(Origen, IdOrigen)` **es** el historial completo de ese movimiento (FR-004/FR-013).

| Columna | Tipo | Regla |
|---|---|---|
| `IdReasignacion` | `int identity` PK | — |
| `Origen` | `varchar(30) NOT NULL` | Mismo valor que `vw_MovimientosCuenta_Base.Origen` (`'Galicia'`, `'Banco Nacion'`, `'Tarjetas'`, …) — ver research.md §1. |
| `IdOrigen` | `bigint NOT NULL` | Mismo valor que `vw_MovimientosCuenta_Base.IdOrigen` para ese origen. |
| `IdContactoAnterior` | `int NOT NULL` | El contacto efectivo antes de esta reasignación (el original si es la primera, o el `IdContactoNuevo` de la reasignación previa vigente) — se guarda explícito para que el historial no dependa de recalcularlo. |
| `IdContactoNuevo` | `int NOT NULL`, `FOREIGN KEY → Contactos.IdContacto` | El contacto correcto elegido. `CHECK (IdContactoNuevo <> IdContactoAnterior)` — FR-011. |
| `Motivo` | `nvarchar(500) NULL` | Opcional (a diferencia de 021, la spec no exige motivo obligatorio; se acepta si el usuario lo da). |
| `Usuario` | `nvarchar(100) NOT NULL` | FR-004. |
| `Fecha` | `datetime2 NOT NULL DEFAULT SYSUTCDATETIME()` | FR-004. |

**Índice**: `IX_ReasignacionesContacto_Origen (Origen, IdOrigen, IdReasignacion DESC)` — soporta tanto la resolución del override en la vista (§3 de research.md) como la consulta de historial por movimiento (US3).

**Regla de vigencia**: para un `(Origen, IdOrigen)` dado, la reasignación vigente es la de mayor `IdReasignacion`. No existe columna de estado — la vigencia es siempre "la última fila", igual que el patrón de resolución usado en `vw_MovimientosCuenta_Base` en sí (última fila por fecha para saldo acumulado).

## `CandidatosDescartados` (nueva, insert-only)

Recuerda qué sugerencias de la detección (US2) un usuario ya revisó y decidió que eran falsos positivos, para que no vuelvan a aparecer (FR-010).

| Columna | Tipo | Regla |
|---|---|---|
| `IdDescarte` | `int identity` PK | — |
| `Origen` | `varchar(30) NOT NULL` | Acotado a `'Galicia'`/`'Banco Nacion'` en el lanzamiento inicial (Clarifications). |
| `IdOrigen` | `bigint NOT NULL` | `IdMovimiento`/`IdMovimientoBNA` del movimiento bancario. |
| `IdContactoSugerido` | `int NOT NULL` | El contacto que la detección sugirió y que el usuario descartó para este movimiento — se guarda junto al origen porque un mismo movimiento podría, en teoría, tener más de un candidato sugerido. |
| `Usuario` | `nvarchar(100) NOT NULL` | Quién descartó. |
| `Fecha` | `datetime2 NOT NULL DEFAULT SYSUTCDATETIME()` | Cuándo. |

**Índice único**: `UX_CandidatosDescartados (Origen, IdOrigen, IdContactoSugerido)` — un mismo candidato no se descarta dos veces (idempotente).

## Entidad derivada: "Candidato de detección" (no persistida como tal)

Se computa en el momento (US2), no se guarda como fila propia salvo cuando se descarta (tabla de arriba). Forma:

```
{ origen, idOrigen, fecha, descripcion, importe,
  idContactoActual, contactoActual,
  idContactoSugerido, contactoSugerido }
```

Una fila por cada `(movimiento, contacto sugerido)` que:
1. No está ya en `CandidatosDescartados`.
2. El nombre del contacto sugerido (menos palabras de la lista de ruido, research.md §5) aparece completo en el texto de la descripción del movimiento.
3. El contacto sugerido no es el mismo que el actualmente efectivo (considerando ya el override vigente, si lo hay).

## Relaciones

- `ReasignacionesContacto.IdContactoNuevo` / `IdContactoAnterior` → `Contactos.IdContacto` (sin `ON DELETE CASCADE`; `Contactos` no se borra en este sistema).
- `ReasignacionesContacto`/`CandidatosDescartados` no tienen FK hacia `Movimientos Galicia`/`Movimientos BNA`/`Tarjetas_Resumenes_Lineas_Compras` — el `(Origen, IdOrigen)` es una referencia lógica (el mismo patrón ya usado por `vw_MovimientosCuenta_Base` en sí, que tampoco tiene esa FK física entre ramas), para no acoplar el esquema nuevo a la estructura interna de cada tabla de origen.

## Validaciones de aplicación (no expresables como CHECK simple)

- FR-011 (rechazar reasignar al mismo contacto): comparar contra el **contacto efectivo actual** (que puede ya venir de una reasignación previa), no contra `IdContactoAnterior` crudo de la tabla de origen.
- FR-007 (origen sin soporte): la lista de orígenes soportados (`'Galicia'`, `'Banco Nacion'`, `'Tarjetas'`) es una constante de la capa de aplicación, no una tabla — se valida antes de insertar.
