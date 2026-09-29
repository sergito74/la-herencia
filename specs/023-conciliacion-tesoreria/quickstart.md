# Quickstart: Conciliación de Tesorería

Guía de validación end-to-end una vez implementado. No reemplaza los tests
automáticos (`tasks.md`) — es para confirmar manualmente que el flujo real
funciona sobre `WC`.

## Prerrequisitos

- Backup verificado de `WC` tomado antes de aplicar el `ALTER VIEW` y crear
  `ConciliacionesTesoreria` (Constitution Check — obligatorio, no opcional).
- Backend corriendo con `--reload` contra `WC`, frontend corriendo contra
  ese backend (ver sesión anterior: reiniciar el backend después de cada
  cambio de esquema, no solo de código).
- Un usuario autenticado con permisos de escritura.

## Escenario 1 — Conciliación simple (Historia 1)

1. Ir a Tesorería → Banco Nación, filtrar por un rango de fechas donde se
   sepa (o se busque) un movimiento con `estadoConciliacion: sin_conciliar`
   — en `WC` real hay 34 movimientos BNA sin contacto (research.md §1),
   cualquiera sirve.
2. Abrir la acción de conciliar sobre esa fila.
3. Si "Referencia de origen" sugirió una candidata única, aceptarla como
   atajo; si no, buscar y elegir un contacto a mano, con el importe total
   del movimiento.
4. Confirmar.
5. Verificar: la fila en el listado de BNA pasa a `estadoConciliacion:
   conciliado`; la cuenta corriente de ese contacto (`/finanzas/
   cuentas-corrientes`) muestra el movimiento nuevo con el debe/haber
   correcto y el saldo recalculado.

## Escenario 2 — Reparto incremental entre varios contactos (Historia 2)

1. Ir a Tesorería → Mercado Libre (75 movimientos sin contacto en `WC`
   real), elegir un movimiento sin conciliar.
2. Conciliar una parte del importe (por ejemplo, la mitad) a un primer
   contacto. Confirmar.
3. Verificar: el movimiento queda `estadoConciliacion:
   parcialmente_conciliado`, con el saldo pendiente visible = la otra
   mitad.
4. Cerrar la sesión (recargar la página, o esperar a otro momento) y
   volver al mismo movimiento — el saldo pendiente debe seguir mostrando
   la otra mitad, no haberse perdido.
5. Conciliar el resto a un segundo contacto (o al mismo, con otro
   importe). Confirmar.
6. Verificar: el movimiento queda `conciliado`; cada contacto ve
   únicamente su parte en su propia cuenta corriente; la suma de ambas
   partes coincide con el importe total del movimiento original.

## Escenario 3 — No duplicar un movimiento ya reconocido (Historia 3)

1. Ir a Tesorería → Galicia, elegir un movimiento que YA tenga contacto
   (la mayoría — 113 de N no lo tienen, el resto sí).
2. Verificar: `estadoConciliacion: ya_reconocido`; la acción de conciliar
   no está disponible sobre esa fila (o, si se expone para corregir,
   dirige a la reasignación de contacto ya existente — FR-008/FR-008a),
   nunca ofrece "conciliar de cero".
3. Intentar el `POST` de conciliación directamente contra ese movimiento
   (vía API, para probar el guardrail del backend, no solo el de UI) →
   debe responder `409`.

## Escenario 4 — Corrección vía 022 extendido (FR-008a)

1. Sobre un movimiento ya conciliado en el Escenario 1, ir a la cuenta
   corriente del contacto asignado y usar "Reasignar" (022) para
   corregirlo a otro contacto.
2. Verificar: el movimiento desaparece de la cuenta corriente del contacto
   original y aparece en la del nuevo, con el historial de reasignación
   consultable — mismo comportamiento que ya funciona hoy para Galicia/BNA/
   Tarjetas, ahora también para un origen `Conciliación Tesorería`.

## Verificación de no regresión

- Los medios/movimientos que ya se posteaban automáticamente antes de este
  feature (Compras, Impuestos, Remuneraciones, Alquileres, y los
  movimientos de BNA/Galicia/Efectivo que YA tenían contacto) deben seguir
  viéndose exactamente igual en cuentas corrientes — correr
  `test_cuentas_corrientes_saldos.py` y comparar saldos totales antes/
  después del `ALTER VIEW` sobre una muestra de contactos conocidos.
- `Tarjetas` sigue conciliándose únicamente desde 008/009 — confirmar que
  ese flujo no cambió.
