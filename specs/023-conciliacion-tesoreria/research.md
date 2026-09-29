# Research: Conciliación de Tesorería

Todas las decisiones de esta feature parten de leer código y datos reales de
`WC` (no de suposiciones) — ver comandos y resultados citados en cada sección.

## 1. ¿Cómo se postean hoy los movimientos de Tesorería a cuentas corrientes?

**Decisión**: `vw_MovimientosCuenta_Base` es un `UNION ALL` de una rama por
origen (Compras, Alquileres, Impuestos, Remuneraciones, Galicia, Banco
Nación, Pagos efectivo, Valores Recibidos [2 ramas], Retenciones [2 ramas],
Tarjetas), cada una con un `INNER JOIN dbo.Contactos` sobre el `IdContacto`
de la tabla de origen — es decir, **cualquier fila cuyo `IdContacto` sea
`NOT NULL` y válido ya se refleja automáticamente en cuentas corrientes**,
sin que exista hoy ningún mecanismo de "conciliación manual". Sobre el
resultado de ese `UNION`, un `OUTER APPLY` a `dbo.ReasignacionesContacto`
(022) aplica el último override de contacto si existe.

**Implicación central para esta feature**: el "movimiento conciliable" de la
spec (FR-001) no es "cualquier movimiento de Tesorería", es específicamente
el subconjunto con `IdContacto IS NULL` en su tabla de origen — el resto ya
tiene efecto contable y conciliarlo de nuevo duplicaría el importe (FR-008,
SC-003).

**Volumen real verificado (`WC`, 2026-09-28)**:

| Medio | Filas sin contacto | Presente hoy en la vista |
|---|---|---|
| Banco Nación | 34 | Sí (rama `Banco Nacion`) |
| Galicia | 113 | Sí (rama `Galicia`) |
| Mercado Libre | 75 | **No** — `Movimientos Mercado Libre` no tiene ninguna rama en la vista hoy |
| Pagos efectivo | 0 | Sí (rama `Pagos efectivo`, con `WHERE IdContacto IS NOT NULL`) |
| Valores propios | 1.142 (100%, la tabla no tiene columna de contacto) | **No** — no existe ninguna rama para `Valores propios` |
| Valores Recibidos | 17 totales | Sí, vía `vw_CnsPagosValoresRecibidos`/`vw_CnsCobrosValoresRecibidos` (cubre "Endoso a tercero"; los casos sin endoso no) |

**Alternativas consideradas**:
- *Modificar las ramas existentes (BNA/Galicia/Efectivo) para que dejen de exigir `IdContacto NOT NULL` y resuelvan el contacto desde la conciliación en su lugar* — rechazado: complica cada rama existente con un `COALESCE`/`OUTER APPLY` adicional contra la tabla de conciliaciones, y esas ramas ya están cubiertas por el override de 022 para el caso "tiene contacto pero está mal". Es más simple y más aditivo (Principio VII) agregar UNA rama nueva dedicada a conciliaciones manuales, que solo aporta las filas que las ramas existentes no cubren.
- *Escribir `IdContacto` directamente en `Movimientos BNA`/`Movimientos Galicia`/etc. al conciliar* — rechazado: no soporta reparto entre varios contactos (una sola columna `IdContacto` por fila), y estas tablas se recargan por importación de resúmenes (013), lo que arriesga perder la conciliación en una recarga futura.

## 2. ¿Cómo modelar el reparto entre varios contactos con conciliación incremental?

**Decisión**: tabla nueva insert-only `dbo.ConciliacionesTesoreria`, mismo
patrón ya validado en 021 (`MovimientosCuentaSocio`) y 022
(`ReasignacionesContacto`) — nunca `UPDATE`/`DELETE`, cada fila es una
"parte" de la conciliación de un movimiento:

```
IdConciliacion  (PK, identity)
Medio           (bna | galicia | mercado-libre | efectivo | valores-propios | valores-recibidos)
IdMovimiento    (id del movimiento en su tabla de origen)
IdContacto
Importe         (positivo; el signo/Debe-Haber se deriva del signo del movimiento original, no se duplica)
Usuario
Fecha           (default getdate())
```

El "saldo pendiente" de un movimiento se calcula, no se guarda:
`importe_total_movimiento - SUM(Importe) FROM ConciliacionesTesoreria WHERE Medio=? AND IdMovimiento=?`.
Sin esa columna redundante no hay riesgo de que quede desincronizada
(Principio VII). El estado (sin conciliar / parcial / completo) es una
función de ese saldo, no un campo mutable.

**Alternativas consideradas**:
- *Guardar un estado mutable (`Estado` con UPDATE) en vez de derivarlo* — rechazado: reintroduce el problema que 021/022 ya evitaron (una columna que puede desincronizarse del historial real); además complica la concurrencia (FR-010) porque dos escrituras concurrentes sobre un campo mutable necesitan locking explícito, mientras que dos INSERTs concurrentes de conciliaciones parciales son naturalmente seguros (se aplican ambos, y el saldo pendiente los ve a los dos).
- *Reutilizar `ReasignacionesContacto` para esto* — rechazado: esa tabla modela *(Origen, IdOrigen) → un único contacto vigente*, sin concepto de importe parcial ni de que puedan coexistir varias filas activas para el mismo `IdOrigen`. Forzar el reparto ahí requeriría cambiar su significado para 022, que ya está en producción con ese contrato.

## 3. ¿Cómo integrar el resultado en `vw_MovimientosCuenta_Base` sin tocar las ramas existentes?

**Decisión**: agregar una rama `UNION ALL` nueva que lee
`ConciliacionesTesoreria` directamente (no las tablas de origen), con
`Origen = 'Conciliación Tesorería'` y `IdOrigen = IdConciliacion`. Cada fila
de conciliación aparece como su propio renglón de cuenta corriente, con el
importe parcial que le corresponde a ese contacto — así el reparto entre
varios contactos funciona sin cambiar el resto de la vista.

Esta rama nueva automáticamente queda cubierta por el `OUTER APPLY` de
022 que ya existe al final de la vista (aplica sobre el resultado del
`UNION` completo, sin importar de qué rama viene la fila) — de ahí que
FR-008a ("la corrección pasa por 022") no requiera tocar el mecanismo de
override en sí, solo extender `ORIGENES_SOPORTADOS` en
`reasignacion_contacto/repository.py` para aceptar `'Conciliación
Tesorería'` como origen válido.

**Signo (Debe/Haber)**: se deriva en la rama nueva con el mismo `CASE WHEN
... > 0 THEN ... ELSE 0` que usan las demás ramas, a partir del signo del
`Importe` de `ConciliacionesTesoreria` (que a su vez se carga con el mismo
signo que tenía el movimiento original en su medio).

**Alternativas consideradas**:
- *Una rama por medio (6 ramas nuevas) en vez de una única rama genérica* — rechazado: la tabla `ConciliacionesTesoreria` ya normaliza el medio como columna; una sola rama genérica es más simple y más fácil de mantener (Principio VII) que 6 casi-idénticas.

## 4. ¿Qué endpoints necesita el backend?

**Decisión**: nuevo router `conciliacion_tesoreria` con:
- `GET /api/tesoreria/{medio}/movimientos/{id}/conciliacion` — estado del movimiento (sin conciliar / parcial con saldo pendiente / completo) + lista de conciliaciones ya aplicadas.
- `POST /api/tesoreria/{medio}/movimientos/{id}/conciliacion` — aplica una conciliación (un contacto + importe; se llama una vez por contacto en un reparto, o una sola vez para el caso simple con el importe total).

Se reutiliza el patrón ya usado en 022 (`router.py` delgado, `repository.py`
con la lógica y validaciones, `schemas.py` con los contratos Pydantic).

**Alternativas consideradas**:
- *Un único endpoint que reciba la lista completa de repartos en un solo POST* — rechazado por la Clarification de reparto incremental: el usuario puede confirmar partes en sesiones distintas, así que el contrato debe permitir un POST por parte, no exigir el reparto completo en una sola llamada.

## 5. ¿Cómo evitar que dos usuarios concilien el mismo saldo pendiente a la vez (FR-010)?

**Decisión**: en el `INSERT` de cada conciliación, validar dentro de la
misma transacción que `Importe` solicitado no exceda el saldo pendiente
recalculado en ese momento (no el que el cliente vio al abrir la pantalla).
Si ya no alcanza, la escritura se rechaza con un error claro y el cliente
debe refrescar el saldo pendiente real. Mismo principio de "recalcular en
el server, no confiar en el estado que trae el cliente" que ya usa 022 en
`_contacto_efectivo`.

**Alternativas consideradas**: locking pesimista explícito (`sp_getapplock`
o similar) — rechazado por sobre-ingeniería para el volumen real (máximo
unas pocas decenas de movimientos concurrentes, uso interno de un puñado de
personas); la validación transaccional alcanza y es el mismo patrón ya
usado en el resto del sistema.

## 6. Extensión de 022-reasignación-contacto (FR-008a)

**Decisión**: agregar `'Conciliación Tesorería'` a
`ORIGENES_SOPORTADOS` y a `_contacto_original` en
`reasignacion_contacto/repository.py`, resolviendo el contacto original
desde `ConciliacionesTesoreria.IdContacto WHERE IdConciliacion = ?`. No
requiere cambios en el mecanismo de override en sí (`OUTER APPLY`, ya
genérico por `(Origen, IdOrigen)`), ni en la detección automática de
candidatos (US2 de 022, que sigue acotada a los orígenes con texto libre de
descripción — Galicia/Banco Nación — sin cambios).
