# Research: Reasignación de contacto en movimientos de cuenta corriente

## §1. Cómo se resuelve hoy el contacto de cada movimiento

`vw_MovimientosCuenta_Base` (definida en `backend/scripts/agregar_tarjetas_a_vista_cuenta_corriente.py`) es un `UNION ALL` de ramas, una por origen. Cada rama ya expone `Origen` (etiqueta fija: `'Galicia'`, `'Banco Nacion'`, `'Tarjetas'`, `'Pagos efectivo'`, `'Retenciones'`, etc.) e `IdOrigen` (la clave real dentro de la tabla de ese origen). Confirmado por lectura directa del script:

| Origen (columna `Origen`) | Tabla de origen | Columna con el contacto hoy | `IdOrigen` es… |
|---|---|---|---|
| `'Galicia'` | `dbo.[Movimientos Galicia]` | `g.IdContacto` (columna propia de la fila) | `g.IdMovimiento` |
| `'Banco Nacion'` | `dbo.[Movimientos BNA]` | `b.IdContacto` (columna propia de la fila) | `b.IdMovimientoBNA` |
| `'Tarjetas'` | `dbo.Tarjetas_Resumenes_Lineas_Compras` (vínculo) | **no** viene de la línea — sale de `c.IdContacto` de la `Compra` vinculada (`dbo.Compras c ON c.IdDeuda = v.IdCompra`) | `v.IdVinculo` |

Esta tabla confirma exactamente la ambigüedad que motivó la Clarification de spec.md: para `'Galicia'`/`'Banco Nacion'` el contacto vive en la propia fila del movimiento; para `'Tarjetas'` vive en un registro completamente distinto (`Compras`) que otros módulos (stock, costos por cultivo) también usan.

**Decisión**: en vez de decidir caso por caso si "editar la fila" o "editar la Compra", se introduce una capa de *override* uniforme aplicada en la vista, keyed por el mismo par `(Origen, IdOrigen)` que la vista ya expone. Esto:
- Nunca escribe en `Movimientos Galicia`/`Movimientos BNA`/`Compras` (cumple FR-014 y evita mutar datos importados que podrían volver a cargarse).
- Es el mismo mecanismo para los dos orígenes soportados en el lanzamiento inicial, sin lógica especial por rama.
- Es extensible a futuros orígenes sin cambiar el mecanismo, solo agregando la rama correspondiente al `LEFT JOIN` de override (ya está ahí para todas, no hace falta tocarlo por origen nuevo).

**Alternativa descartada**: `UPDATE` directo de `IdContacto` en `Movimientos Galicia`/`Movimientos BNA` (lo que se hizo manualmente para el caso real de "Encode S.A."). Se descarta porque (a) para `Tarjetas` es directamente inviable sin violar FR-014, y (b) mutar la fila importada pierde el dato original y no deja rastro de "cuál era el valor antes" sin una tabla de auditoría aparte — la capa de *override* insert-only ya da ambas cosas (valor anterior recuperable, ningún dato de origen mutado) con un solo mecanismo.

## §2. Diseño de la tabla de override / auditoría

Mismo patrón que `MovimientosCuentaSocio`/`AplicacionesPago` (021/019): **insert-only**, nunca `UPDATE`/`DELETE`. La fila vigente para un `(Origen, IdOrigen)` es la de mayor `IdReasignacion` (no hace falta una columna "vigente" mutable: un `ROW_NUMBER() OVER (PARTITION BY Origen, IdOrigen ORDER BY IdReasignacion DESC)` en el punto de lectura ya resuelve "cuál es la última").

Esto resuelve varios requisitos de spec.md de forma directa:
- **FR-004/FR-013** (historial completo, no solo el último cambio): es la naturaleza misma de una tabla insert-only — todas las filas quedan, se consulta la última para el efecto actual.
- **FR-012** (reasignaciones concurrentes): dos inserts concurrentes nunca se pisan ni se pierden — ambos quedan grabados, y el orden de inserción (identity autoincremental) decide cuál es la vigente de forma determinística. No hace falta un mecanismo de locking optimista adicional.
- **FR-011** (rechazar reasignar al mismo contacto): se valida en la capa de aplicación antes de insertar, comparando contra el contacto efectivo actual (la última fila vigente, o el original si no hay ninguna).

## §3. Integración en `vw_MovimientosCuenta_Base`

Cambio quirúrgico (Principio VII): se envuelve el `UNION ALL` existente (sin tocar ninguna rama individual) en una subconsulta `base`, y una `SELECT` externa aplica el override:

```sql
SELECT
    base.Fecha,
    COALESCE(ov.IdContactoNuevo, base.IdContacto) AS IdContacto,
    COALESCE(ctov.[Razon Social], base.[Razon Social]) AS [Razon Social],
    base.Documento, base.[Nro Documento], base.Deuda, base.Credito,
    base.Origen, base.IdOrigen
FROM (
    -- el UNION ALL existente, sin modificar
) AS base
OUTER APPLY (
    SELECT TOP 1 r.IdContactoNuevo
    FROM dbo.ReasignacionesContacto r
    WHERE r.Origen = base.Origen AND r.IdOrigen = base.IdOrigen
    ORDER BY r.IdReasignacion DESC
) AS ov
LEFT JOIN dbo.Contactos AS ctov ON ctov.IdContacto = ov.IdContactoNuevo
```

Mismo patrón de `ALTER VIEW` con backup previo que las iteraciones v1-v4 del fix de tarjetas en cuenta corriente (`backups/WC_pre_fix_vista_tarjetas_*`).

## §4. Exposición al frontend: qué necesita el botón "Reasignar"

`backend/src/features/cuentas_corrientes/repository.py`/`origen_resolver.py` ya leen `Origen`/`IdOrigen` de la vista por cada movimiento (variables `origenTipo`/`idOrigen` internas), pero hoy no siempre se los devuelve al frontend tal cual — se transforman según el tipo (`"tesoreria"`, `"fuera_de_alcance"`, etc.), y el caso `'Tarjetas'` cae hoy en `"fuera_de_alcance"` sin exponer su `idOrigen` (`origen_resolver.py` línea ~130).

**Decisión**: agregar `origenTipo`/`idOrigen` **crudos** (los valores reales de la vista) a nivel del propio `MovimientoCuentaCorriente`, además del objeto `origen` ya resuelto — así el botón "Reasignar" siempre tiene la clave `(Origen, IdOrigen)` que necesita para llamar al endpoint, sin depender de que cada rama de `origen_resolver` haya sido actualizada para exponerlo. Es un campo adicional, no un reemplazo — no rompe el contrato existente de `cuentas-corrientes` (004).

## §5. Heurística de detección (US2) — reducir el ruido ya demostrado

El escaneo manual ya hecho (ver conversación previa) comparaba, para cada movimiento con contacto asignado, las palabras (>3 letras) del nombre de **otros** contactos contra las palabras del texto de la descripción del movimiento. Resultado real: 36 candidatos, 35 falsos positivos por términos genéricos (`"Banco Galicia"`, `"Banco Nacion"`, `"Argentina"`, `"Bolivar"`).

**Decisión**: mantener la misma heurística de solapamiento de palabras, pero excluir de antemano una lista fija de términos de ruido bancario/genérico confirmados por el escaneo real:
`BANCO, GALICIA, NACION, ARGENTINA, BOLIVAR, BBVA, CREDICOOP, SOCIEDAD, ANONIMA, RESPONSABILIDAD, LIMITADA, COMPANIA, SRL, SA`. Esta lista es un dato de configuración (constante en el repositorio), no una tabla — se puede ampliar en el futuro si aparecen nuevos falsos positivos, sin requerir migración de esquema.

Confirmado por el escaneo real: con esta lista, el candidato real (`Encode S.A.` vs `Carbajo, Juan Manuel`) sigue detectándose, porque `"Encode"` no es un término de la lista de ruido.

**Alcance del origen para la detección (US2)**: acotado a `Movimientos Galicia`/`Movimientos BNA` (los únicos con un campo de texto libre — `Descripción`) por decisión de Clarifications en spec.md. `Tarjetas` no tiene ese texto y queda fuera de la detección automática (pero disponible para reasignación manual, US1).

## §6. Descarte de falsos positivos (FR-010)

Tabla chica `CandidatosDescartados` (insert-only, sin `UPDATE`/`DELETE`): `(Origen, IdOrigen, IdContactoSugerido, Usuario, Fecha)`. La consulta de detección excluye (`NOT EXISTS`) cualquier candidato ya presente ahí para el mismo `(Origen, IdOrigen, IdContactoSugerido)`. No hace falta un estado "confirmado": una vez que un candidato se reasigna (US1), el contacto efectivo pasa a coincidir con el sugerido y el candidato deja de aparecer de forma natural (ya no hay mismatch que detectar) — sin necesidad de marcarlo aparte.

## Decisiones consolidadas

- **Decision**: capa de *override* insert-only (`ReasignacionesContacto`) aplicada en la vista vía `OUTER APPLY` + `COALESCE`, uniforme para todos los orígenes soportados.
  **Rationale**: nunca muta tablas de origen (FR-014), un solo mecanismo para historial (FR-013) y concurrencia (FR-012) sin lógica extra.
  **Alternatives considered**: `UPDATE` directo por origen (descartado: inviable para `Tarjetas` sin violar FR-014, y pierde el valor anterior sin tabla aparte).

- **Decision**: exponer `origenTipo`/`idOrigen` crudos en `MovimientoCuentaCorriente` además del objeto `origen` ya resuelto.
  **Rationale**: el botón "Reasignar" necesita la clave real sin depender de que cada rama de `origen_resolver` la exponga de forma amigable.
  **Alternatives considered**: resolver `idOrigen` amigable para `Tarjetas` primero (se pospone como mejora incremental, no bloquea el MVP).

- **Decision**: lista fija de términos de ruido para la heurística de detección, basada en los falsos positivos reales ya observados.
  **Rationale**: evidencia real disponible (35 de 36 candidatos eran ruido bancario genérico); una lista de configuración es más simple y auditable que un modelo de confianza.
  **Alternatives considered**: umbral de confianza numérico/score (descartado por ahora: no hay suficientes casos reales para calibrarlo, se puede añadir después si la lista de exclusión no alcanza).
