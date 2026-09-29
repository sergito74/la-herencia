# Data Model: Conciliación de Tesorería

## Entidad nueva: `ConciliacionesTesoreria`

Insert-only (nunca `UPDATE`/`DELETE`) — mismo patrón que
`MovimientosCuentaSocio` (021) y `ReasignacionesContacto` (022). Cada fila
es una "parte" de la conciliación de un movimiento: la conciliación simple
(Historia 1) es el caso particular de una única fila cuyo `Importe` cubre
el 100% del movimiento; el reparto (Historia 2) son varias filas que,
sumadas a lo largo del tiempo (una o más sesiones), llegan al 100%.

| Columna | Tipo | Notas |
|---|---|---|
| `IdConciliacion` | int identity, PK | |
| `Medio` | varchar(20) | uno de: `bna`, `galicia`, `mercado-libre`, `efectivo`, `valores-propios`, `valores-recibidos` (FR-002: nunca `tarjetas`) |
| `IdMovimiento` | bigint | id del movimiento en su tabla de origen (`IdMovimientoBNA`, `IdMovimiento` de Galicia/ML, `IdPagoEfectivo`, `IdValor`) |
| `IdContacto` | int, FK → `Contactos.IdContacto` | contacto al que se le asigna esta parte |
| `Importe` | money | positivo; el signo del efecto (debe/haber) se deriva del signo del movimiento original, no se guarda dos veces |
| `Usuario` | varchar | quién concilió (FR-011) |
| `Fecha` | datetime, default `getdate()` | cuándo (FR-011) |

**Validaciones (aplicadas en el repository, no solo en el schema)**:
- `Medio` debe ser uno de los 6 valores soportados (FR-002).
- `IdContacto` debe existir en `Contactos`.
- `Importe` > 0.
- `Importe` no puede exceder el saldo pendiente del movimiento en el momento de la escritura (recalculado en la misma transacción — ver research.md §5, FR-010).
- El movimiento (`Medio`+`IdMovimiento`) no puede tener ya un `IdContacto NOT NULL` en su tabla de origen ni en el override vigente de 022 — si ya está reconocido por otro camino, se rechaza (FR-008, SC-003).

**Estado derivado de un movimiento** (nunca almacenado, siempre calculado — research.md §2):

```
saldo_pendiente = importe_total_movimiento - SUM(Importe) FROM ConciliacionesTesoreria WHERE Medio=? AND IdMovimiento=?

estado =
  "sin_conciliar"          si SUM = 0
  "parcialmente_conciliado" si 0 < SUM < importe_total (dentro de tolerancia de redondeo)
  "conciliado"              si SUM ≈ importe_total (dentro de tolerancia de redondeo)
```

## Cambio de esquema: `vw_MovimientosCuenta_Base`

`ALTER VIEW` aditivo — una rama `UNION ALL` nueva (research.md §3):

```sql
SELECT
    m.Fecha,                                  -- fecha del movimiento original, no de la conciliación
    ct.IdConciliacion.IdContacto AS IdContacto,
    c.[Razon Social],
    'Conciliación Tesorería' AS Documento,
    CAST(ct.IdMovimiento AS varchar(50)) AS [Nro Documento],
    CASE WHEN <importe_original> > 0 THEN ct.Importe ELSE 0 END AS Deuda,
    CASE WHEN <importe_original> < 0 THEN ct.Importe ELSE 0 END AS Credito,
    CAST('Conciliación Tesorería' AS varchar(50)) AS Origen,
    CAST(ct.IdConciliacion AS bigint) AS IdOrigen
FROM dbo.ConciliacionesTesoreria ct
JOIN dbo.Contactos c ON c.IdContacto = ct.IdContacto
-- + resolución del movimiento/importe original según ct.Medio (una expresión por medio, ver plan de tasks)
```

Requiere backup verificado de `WC` antes de aplicarse (Constitution Check,
Principio II) por ser un cambio de esquema en producción.

## Extensión de entidad existente: `ReasignacionesContacto` (022)

Sin cambios de esquema. Cambio de código únicamente:
`ORIGENES_SOPORTADOS` (`reasignacion_contacto/repository.py`) pasa de
`{"Galicia", "Banco Nacion", "Tarjetas"}` a incluir también
`"Conciliación Tesorería"` — el `(Origen, IdOrigen)` de una corrección
sobre una conciliación es `("Conciliación Tesorería", IdConciliacion)`.

## Entidades de solo lectura (sin cambios de esquema)

- **Movimiento de Tesorería**: fila existente en `Movimientos BNA` /
  `Movimientos Galicia` / `Movimientos Mercado Libre` / `Pagos efectivo` /
  `Valores propios` / `Valores Recibidos` — el dato de origen sobre el que
  se concilia. Este feature nunca escribe sobre estas tablas.
- **Candidata de Referencia de origen**: la sugerencia ya existente de
  `tesoreria/matching.py` — se consume como atajo (FR-007) para
  pre-completar el contacto y el importe al conciliar, sin cambios en su
  propia lógica.
