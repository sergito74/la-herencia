# Traspaso a Gemini — menú Personal, 29/10/2026

Escrito por Claude Code. Gemini se ocupa **solo de los módulos del menú Personal**: Remuneraciones y Trabajos eventuales. La conciliación e imputación de cuentas (spec 036) la sigue Claude Code; **no tocar** `AplicacionesPago`, `recalculo_fifo`, las cuentas de proveedores ni los scripts `*_036.py`.

Antes de empezar, leer [GEMINI.md](../../GEMINI.md), la guía compartida y la Constitución.

## Alcance

| Pantalla | Ruta | Spec | Código |
|---|---|---|---|
| Remuneraciones | `/personal/remuneraciones` | [028](../028-alta-liquidacion-remuneraciones/spec.md) | `backend/src/features/remuneraciones/`, `frontend/src/components/remuneraciones/` |
| Adicional de Sierra (dentro de Remuneraciones) | — | [045](spec.md), US4 | `remuneraciones/adicional.py`, `AdicionalSierra.tsx` |
| Trabajos eventuales | `/personal/trabajos-eventuales` | [045](spec.md) | `backend/src/features/trabajos_eventuales/`, `frontend/src/components/trabajos-eventuales/`, `frontend/src/services/trabajosEventualesApi.ts` |

Relacionado: la carga automática de recibos de sueldo desde los mails (`documentos_nuevos/lectores/sueldos.py`, spec 043) alimenta Remuneraciones.

## Estado real (29/10/2026)

- Hay código de la 045 commiteado (commit 4d9c398) y del adicional de Sierra (commit bd594a1). Los tests pasan: `pytest tests/test_trabajos_eventuales.py tests/contract/test_trabajos_eventuales_api.py tests/test_adicional_sierra.py`.
- **`specs/045-trabajos-eventuales/tasks.md` está desactualizado:** casi todas las tareas figuran sin marcar aunque el código existe. El primer paso es `/speckit-converge`: contrastar spec, plan y tareas con el código, marcar lo que de verdad está hecho y agregar lo que falta.
- **Faltan, como mínimo:**
  - T010: aplicar la migración e importación de la planilla real y registrar la evidencia en `validacion.md`, que todavía no existe.
  - T012: build y verificación visual de las pantallas.
- **La planilla real de trabajos eventuales** hoy tiene 78 trabajos, 3 de ellos "Pendiente" (Mori, Pardo y Torrontegui, del 29 y 30/10). La spec y la T003 todavía hablan de 75 trabajos y un total de $2.500.558; hay que actualizarlas. El test de la planilla real controla solo la forma de los datos, no los totales.

## Reglas que aplican acá

- Solo **personal permanente**: Sierra e Irma Miranda. El resto es eventual y va en Trabajos eventuales.
- Sueldo = neto formal. Un faltante que Sergio pagó en efectivo **nunca** es una bonificación negativa (ver el caso Franco/Mori 2022).
- **Pantallas:**
  - Nada interno a la vista: ni ids, ni códigos, ni nombres de conectores.
  - Pedir solo lo que el usuario necesita.
  - Formato argentino: miles con ".", decimales con ","; nunca `type=number` ni `toLocaleString`. Usar los helpers existentes.
- Después de cualquier carga automática, mostrar un listado en pantalla para revisar la imputación.
- **Escrituras:**
  - Solo en la base `WC`, nunca en `LaHerencia`.
  - Respaldo verificado antes de una migración o una escritura masiva.
  - Los tests no escriben datos reales.
- **Recibos de sueldo:** están en PDF en `Documents/La Herencia/Administracion y gestion/Personal/Recibos/<año>`.
- **Git:**
  - Commits chicos, por spec.
  - Preservar los cambios de otros agentes.
  - Consultar a Sergio antes de hacer push.
