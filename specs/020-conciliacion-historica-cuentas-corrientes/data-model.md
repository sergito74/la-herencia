# Data Model: Conciliación histórica de cuentas corrientes

## AplicacionesPago (extensión de la tabla existente, 019)

Se agregan dos columnas nuevas (no se toca ninguna columna existente ni su semántica):

| Columna | Tipo | Notas |
|---|---|---|
| Origen | varchar(30) NOT NULL DEFAULT 'manual' | `'manual'` (aplicaciones ya existentes y las que siga cargando un usuario) \| `'automatica-exacta'` \| `'automatica-mejor-esfuerzo'` — corregido a varchar(30) el 2026-09-25: `'automatica-mejor-esfuerzo'` son 25 caracteres, no entraba en varchar(20) (bug real encontrado en la primera corrida de `--apply`) |
| NotaConciliacion | nvarchar(255) NULL | Solo para `Origen <> 'manual'`: detalle de qué documentos se combinaron y, si es mejor esfuerzo, la diferencia de importe |

Reglas heredadas de 019 que siguen aplicando sin cambios: inmutabilidad (insertar/anular, nunca `UPDATE` de `ImporteAplicado`/`IdDocumentoAplicado`), índices existentes, y que el estado de documento/movimiento se sigue calculando siempre en el momento desde esta misma tabla — el proceso histórico no introduce una segunda fuente de verdad.

## SaldosReferenciaAccess — **pospuesta** (ver research.md §2, actualizado 2026-09-25)

No se crea esta tabla por ahora. El usuario aclaró que no existe (ni va a armar en el corto plazo) una exportación de Access con la que comparar, y que el "saldo reconstruido desde el arrastre de movimientos" ya existe en el sistema: es `dbo.vw_MovimientosCuenta_Saldo` (columna `SaldoParcial`), la misma fuente que ya consume `cuentas_corrientes.repository.get_saldo`/`get_saldos_todos` (004). Construir una segunda reconstrucción del saldo a partir de los mismos datos de `WC` compararía el sistema contra sí mismo, sin aportar ninguna validación real.

Cuando exista un dato de verdad externo (saldo real de cada cuenta, a conseguir en una etapa posterior), esta tabla se diseña recién en ese momento, con la forma concreta que tenga ese dato disponible.

## Entidades derivadas (calculadas, no persistidas)

- **Resumen de conciliación por contacto** (US2): `{ idContacto, aplicadosExactos, aplicadosMejorEsfuerzo, sinAplicar }` — cuenta de movimientos de tesorería 2015-2026 del contacto en cada categoría. Se deriva de `AplicacionesPago.Origen` (join con el movimiento original) más los movimientos sin ninguna aplicación vigente en ese rango.

## Relación con features existentes

- **019 (`aplicaciones_pago`)**: esta feature reutiliza `sugerencia.sugerir`/`sugerencia._contacto_e_importe` y `documentos.documentos_pendientes` sin modificarlos; solo agrega un modo de invocación no interactivo (el script) y las dos columnas nuevas en `AplicacionesPago`.
- **004 (`cuentas_corrientes`)**: no se toca ni se duplica; `SaldoParcial` (`vw_MovimientosCuenta_Saldo`) sigue siendo la única fuente de saldo. Aplicar el histórico (US1) no modifica ningún saldo — solo le da significado (a qué documento corresponde) a movimientos que ya estaban sumados en ese saldo.
- **018 (`flujo_caja`)**: se beneficia indirectamente — al reducirse los movimientos sin aplicar, más movimientos pasan a mostrar Rubro/Centro de Costos real vía `atribuir_egreso`/`atribuir_ingreso`, sin tocar ese código.
