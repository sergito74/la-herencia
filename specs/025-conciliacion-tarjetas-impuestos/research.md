# Research: Vincular líneas de resumen de tarjeta a pagos de Impuestos

## 1. ¿Cómo extender la tabla de vínculos sin romper el mecanismo de Compras ya en producción?

**Decisión**: `dbo.Tarjetas_Resumenes_Lineas_Compras` (1.598 filas reales) se
extiende de forma aditiva:
- `IdCompra` pasa de `NOT NULL` a `NULL` (las 1.598 filas existentes ya
  tienen un valor, no se ven afectadas).
- Se agrega `IdImpuesto int NULL`, con FK a `Impuestos.IdImpuesto`.
- `CHECK` que exige que **exactamente uno** de los dos esté cargado
  (`(IdCompra IS NOT NULL AND IdImpuesto IS NULL) OR (IdCompra IS NULL AND
  IdImpuesto IS NOT NULL)`).

No se renombra la tabla ni la columna `IdCompra` — decenas de queries y
tests existentes ya la usan para Compras (Principio VII: menor superficie
de cambio posible). El nombre de la tabla queda como identificador
histórico, igual que ya pasó con `WC`.

**Alternativas consideradas**:
- *Tabla nueva `Tarjetas_Resumenes_Lineas_Documentos` con un discriminador
  `Origen` desde el arranque, migrando los 1.598 vínculos existentes* —
  rechazado: exige migrar datos reales en producción sin necesidad, cuando
  agregar una columna nullable logra lo mismo sin tocar ni una fila
  existente.
- *Renombrar `IdCompra` a algo genérico (`IdOrigen`) + columna `Origen`* —
  rechazado: mismo resultado funcional que `IdImpuesto` nullable, pero
  obliga a tocar cada `SELECT`/`WHERE v.IdCompra = ...` ya existente en
  `repository.py` (15+ lugares) sin necesidad.

## 2. ¿Cómo calcular el saldo pendiente de un pago de Impuestos (Clarifications, reparto parcial)?

**Decisión**: mismo patrón que `vinculosPrevios` ya usa para Compras
(`get_documentos_candidatos`), pero sumando importes en vez de contar
filas:

```sql
SELECT ISNULL(SUM(v.ImporteImputado), 0) AS vinculado
FROM dbo.Tarjetas_Resumenes_Lineas_Compras v
WHERE v.IdImpuesto = ? AND v.IdLineaConsumo <> ?
```

`saldoPendiente = Impuestos.Importe - vinculado`. Se calcula en el momento
de buscar/vincular (nunca se guarda), mismo criterio insert-only/derivado
ya usado en 023 (`calcular_estado`) — evita que se desincronice.

Nota: Compras hoy **no** tiene este cálculo — `vinculosPrevios` es solo
informativo (cuenta líneas, no valida un tope). Extender ese control
retroactivamente a Compras queda fuera de alcance de esta feature (no lo
pidió el usuario, y tocarlo arriesga una regresión en un mecanismo ya
validado en producción — Principio VII); se implementa el control nuevo
solo para Impuestos, tal como se clarificó.

## 3. ¿Cómo distinguir el origen sin romper el módulo puro de cálculo (`conciliacion_documentos.py`)?

**Decisión**: no se toca `conciliacion_documentos.py`. Verificado contra
el esquema real: la tabla `Impuestos` no tiene columnas `Moneda` ni `Tipo
de Cambio` — todo pago de impuesto está en pesos. El diccionario "doc" que
arma `repository.py` para un pago de Impuestos simplemente no incluye
`moneda`/`tipoDeCambio` (quedan `None`), y `_es_dolar()`/`importe_pesos()`
ya manejan ese caso correctamente sin cambios (docs en pesos van directo
por la rama ARS). Se agrega sí un campo nuevo `origen: "Compras" |
"Impuestos"` al diccionario del documento — dato de presentación (FR-004),
no altera el cálculo puro.

**Alternativas consideradas**: ninguna — confirmar el esquema real de
`Impuestos` antes de asumir que haría falta lógica de moneda fue
justamente lo que evitó un cambio innecesario acá.

## 4. ¿Cómo extender el buscador ("Sumar documentos de otro proveedor")?

**Decisión**: `buscar_documentos` (texto libre por organismo/proveedor o
número de documento) pasa a un `UNION ALL` entre la consulta actual sobre
`Compras` y una nueva sobre `Impuestos` (con organismo asignado, FR-006),
devolviendo la misma forma de diccionario (con `origen` distinguido). El
límite (`TOP`) y el orden (`Fecha DESC`) se aplican sobre el conjunto ya
combinado.

**Alternativas consideradas**:
- *Dos buscadores separados (uno para Compras, otro para Impuestos)* —
  rechazado: el pedido explícito del usuario es que aparezcan "en las
  opciones de búsqueda de documentos para conciliar" — un único buscador
  combinado es más simple de usar y de mantener (FR-001 no distingue
  caminos).

## 5. ¿Qué endpoints/funciones del backend cambian?

**Decisión**:
- `buscar_documentos`: extendida (sección 4).
- `get_documentos_por_ids`: extendida para resolver también `IdImpuesto`
  (usada al reabrir una línea ya conciliada, para mostrar su respaldo).
- `vincular_compra`/`vincular_compras_lote`: el parámetro hoy llamado
  `id_compra` acepta también un id de Impuestos — se distingue con un
  prefijo/tupla `(origen, id)` en vez de dos parámetros paralelos, y antes
  de insertar valida el saldo pendiente (sección 2) cuando el origen es
  Impuestos.
- `conciliacion_documentos.py`: sin cambios (sección 3).

**Alternativas consideradas**: pasar `idCompra`/`idImpuesto` como dos
campos opcionales separados en vez de una tupla `(origen, id)` — se
descarta en favor de lo que decida `data-model.md`/`tasks.md` según cómo
quede más simple de validar (exactamente uno presente) en el contrato de
API; no es una decisión de research, es detalle de implementación.
