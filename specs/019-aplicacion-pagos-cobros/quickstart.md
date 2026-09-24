# Quickstart: validar la aplicación de pagos y cobros (019)

## Prerrequisitos

- Backend/frontend corriendo (sesión requerida).
- Tabla `AplicacionesPago` creada (`backend/scripts/crear_tabla_aplicaciones_pago.py`, idempotente).
- Un proveedor con al menos 2 compras pendientes reales en `WC`, y un movimiento bancario real (pago) a ese proveedor posterior a 2015-09-01.
- Un consignatario con al menos 1 venta (Hacienda o Granos) real, y un movimiento bancario real (cobro) de ese consignatario posterior a 2015-09-01.

## Escenario 1 — Sugerencia FIFO y aplicación parcial (User Story 1)

1. `GET /api/aplicaciones-pago/documentos-pendientes?idContacto={proveedor}&tipo=compra` — anotar las 2 compras pendientes más antiguas y sus saldos.
2. `POST /api/aplicaciones-pago/sugerir` con el movimiento de pago real — verificar que sugiere primero la compra más antigua, y que si el importe no alcanza para las dos, la segunda queda con `importeSugerido < saldoPendiente`.
3. Editar la sugerencia (cambiar un importe) y `POST /api/aplicaciones-pago` con la versión editada — verificar que se guarda tal cual quedó, no la sugerencia original (Acceptance Scenario 2 de User Story 1).
4. `GET /api/aplicaciones-pago/documento/CompraDeuda/{idCompra}` — verificar que el estado (`Parcial`/`Total`) coincide con lo aplicado.

**Resultado esperado**: FR-003/FR-004/FR-007.

## Escenario 2 — Anulación no destructiva (Acceptance Scenario 5, User Story 1)

1. Anotar el estado de un documento con una aplicación vigente.
2. `POST /api/aplicaciones-pago/{idAplicacion}/anular` con un motivo.
3. `GET /api/aplicaciones-pago/documento/...` — verificar que el estado volvió al anterior (recalculado) y que el historial muestra la fila anulada con su motivo, sin que haya desaparecido.

**Resultado esperado**: FR-005.

## Escenario 3 — Ventas (User Story 2)

1. `GET /api/aplicaciones-pago/documentos-pendientes?idContacto={consignatario}&tipo=venta` — confirmar que devuelve la venta real (Hacienda o Granos) con su `importeTotal` calculado igual que en el módulo de ventas.
2. Aplicar el cobro real y verificar el estado resultante, igual que en el Escenario 1 pero del lado de ingresos.

**Resultado esperado**: FR-002/FR-012.

## Escenario 4 — No sobre-aplicación (FR-008, SC-002)

1. Intentar `POST /api/aplicaciones-pago` con un `importeAplicado` que deje un documento con saldo negativo (más allá de la tolerancia de $1).
2. Verificar 400.

## Escenario 5 — Flujo de caja por rubro usa la aplicación (User Story 4)

1. Antes de aplicar: `GET /api/flujo-caja/por-rubro` en el período del movimiento — el egreso/ingreso aparece como "Sin rubro asignado" o "pendiente de aplicar".
2. Aplicar el movimiento a un documento con Rubro/Centro de Costos conocido (Escenario 1 o 3).
3. Repetir `GET /api/flujo-caja/por-rubro` — verificar que ahora aparece bajo el Rubro correcto, no más como pendiente.

**Resultado esperado**: FR-010, SC-003.

## Escenario 6 — Histórico sin aplicar se distingue (Edge case de spec.md)

1. `GET /api/flujo-caja/por-rubro` con un período anterior a 2015-09-01.
2. Verificar que los movimientos sin aplicación de ese período aparecen bajo una categoría "Histórico sin aplicar", distinta de "Sin rubro asignado"/"pendiente de aplicar" de un movimiento posterior al corte.
