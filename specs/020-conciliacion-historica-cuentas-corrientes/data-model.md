# Data Model: Conciliación histórica de cuentas corrientes

## AplicacionesPago (extensión de la tabla existente, 019)

Se agregan dos columnas nuevas (no se toca ninguna columna existente ni su semántica):

| Columna | Tipo | Notas |
|---|---|---|
| Origen | varchar(30) NOT NULL DEFAULT 'manual' | `'manual'` (aplicaciones ya existentes y las que siga cargando un usuario) \| `'automatica-exacta'` \| `'automatica-mejor-esfuerzo'` — corregido a varchar(30) el 2026-09-25: `'automatica-mejor-esfuerzo'` son 25 caracteres, no entraba en varchar(20) (bug real encontrado en la primera corrida de `--apply`) |
| NotaConciliacion | nvarchar(255) NULL | Solo para `Origen <> 'manual'`: detalle de qué documentos se combinaron y, si es mejor esfuerzo, la diferencia de importe |

Reglas heredadas de 019 que siguen aplicando sin cambios: inmutabilidad (insertar/anular, nunca `UPDATE` de `ImporteAplicado`/`IdDocumentoAplicado`), índices existentes, y que el estado de documento/movimiento se sigue calculando siempre en el momento desde esta misma tabla — el proceso histórico no introduce una segunda fuente de verdad.

## SaldosReferenciaAccess (tabla nueva — implementada 2026-09-25, ver research.md §2)

| Columna | Tipo | Notas |
|---|---|---|
| IdContacto | int PK | Mismo `IdContacto` que el resto del sistema |
| SaldoAccess | money | `SaldoParcial` leído de `vw_MovimientosCuenta_Saldo` en `LaHerencia` (no un archivo — ver research.md §2: Access es hoy un front-end sobre `LaHerencia`) |
| FechaCorte | date | Fecha de la corrida que generó este valor |
| FechaCarga | datetime2 default sysutcdatetime() | |

Poblada por `backend/scripts/comparar_saldo_laherencia.py --apply`: lee `LaHerencia` en modo estrictamente solo-lectura (conexión dedicada, reutiliza el guard `_assert_read_only` de `src/db/connection.py`), nunca escribe ahí. Upsert por `IdContacto` en cada corrida — solo interesa el último valor leído.

## Entidades derivadas (calculadas, no persistidas)

- **Resumen de conciliación por contacto** (US2): `{ idContacto, aplicadosExactos, aplicadosMejorEsfuerzo, sinAplicar }` — cuenta de movimientos de tesorería 2015-2026 del contacto en cada categoría. Se deriva de `AplicacionesPago.Origen` (join con el movimiento original) más los movimientos sin ninguna aplicación vigente en ese rango.
- **Comparación de saldo** (US3): `{ idContacto, saldoActual, saldoReferencia, diferencia, estado }` — `saldoActual` sale de `cuentas_corrientes.get_saldos_todos()` (WC, sin modificar), `saldoReferencia` de `SaldosReferenciaAccess` (LaHerencia), `estado = 'conciliado'` si `abs(diferencia) <= max($1, abs(saldoReferencia) * 0.5%)`, `'con-diferencia'` en caso contrario.

## Relación con features existentes

- **019 (`aplicaciones_pago`)**: esta feature reutiliza `sugerencia.sugerir`/`sugerencia._contacto_e_importe` y `documentos.documentos_pendientes` sin modificarlos; solo agrega un modo de invocación no interactivo (el script) y las dos columnas nuevas en `AplicacionesPago`.
- **004 (`cuentas_corrientes`)**: no se toca ni se duplica; `SaldoParcial` (`vw_MovimientosCuenta_Saldo`) sigue siendo la única fuente de saldo. Aplicar el histórico (US1) no modifica ningún saldo — solo le da significado (a qué documento corresponde) a movimientos que ya estaban sumados en ese saldo.
- **018 (`flujo_caja`)**: se beneficia indirectamente — al reducirse los movimientos sin aplicar, más movimientos pasan a mostrar Rubro/Centro de Costos real vía `atribuir_egreso`/`atribuir_ingreso`, sin tocar ese código.
