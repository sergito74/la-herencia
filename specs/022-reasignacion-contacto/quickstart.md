# Quickstart: Reasignación de contacto en movimientos de cuenta corriente

## Prerequisitos

- Backup verificado de `WC` antes de crear el esquema nuevo y antes de cualquier escritura real de validación (Constitución, Principio II).
- Backend corriendo (`uvicorn src.main:app`), sesión autenticada con rol distinto de `Lectura`.
- El caso real ya conocido y corregido manualmente (`IdMovimiento=2712` de `Movimientos Galicia`, Carbajo → Encode S.A.) sirve como escenario de validación: revertirlo primero (ver Escenario 0) para poder probar el flujo completo de punta a punta con la nueva feature, en vez de con datos sintéticos.

## Escenario 0 — preparar el caso real para validar (opcional, solo en `WC` de prueba/backup)

Si se quiere validar contra el caso real en vez de uno sintético: el movimiento ya fue corregido manualmente (`UPDATE` directo, ver historial de la conversación). Para probar el flujo nuevo de punta a punta, puede usarse cualquier otro par (Origen, IdOrigen) real, o revertir momentáneamente ese `IdContacto` a 605 en un entorno de prueba restaurado del backup — nunca en `WC` de producción sin necesidad real.

## Escenario 1 — Reasignar un movimiento bancario (US1)

1. `GET /api/cuentas-corrientes/contactos/605/movimientos` (Carbajo, Juan Manuel) — confirmar que la cuenta corriente expone el movimiento con `origenTipo="Galicia"`, `idOrigen=2712` (research.md §4).
2. `POST /api/reasignacion-contacto/reasignar` con `{"origen": "Galicia", "idOrigen": 2712, "idContactoNuevo": 1652}`.
3. Verificar `201` con `idContactoAnterior=605`, `idContactoNuevo=1652`.
4. `GET /api/cuentas-corrientes/contactos/605/movimientos` — el movimiento ya no aparece.
5. `GET /api/cuentas-corrientes/contactos/1652/movimientos` — el movimiento aparece, con el importe correcto reflejado en el saldo.
6. `GET /api/reasignacion-contacto/historial?origen=Galicia&idOrigen=2712` — devuelve la reasignación aplicada.

## Escenario 2 — Rechazar reasignar al mismo contacto (FR-011)

1. Repetir el `POST /api/reasignacion-contacto/reasignar` del Escenario 1 con el mismo `idContactoNuevo=1652` (ya vigente).
2. Verificar `409`.

## Escenario 3 — Origen sin soporte (FR-007)

1. `POST /api/reasignacion-contacto/reasignar` con `{"origen": "Impuestos", "idOrigen": 1, "idContactoNuevo": 119}`.
2. Verificar `400` con el mensaje claro de que ese origen no admite reasignación todavía.

## Escenario 4 — Reasignar un vínculo de tarjeta sin tocar la Compra (FR-014)

1. Elegir un `IdVinculo` real de `Tarjetas_Resumenes_Lineas_Compras` mal asignado (o uno de prueba).
2. `POST /api/reasignacion-contacto/reasignar` con `{"origen": "Tarjetas", "idOrigen": <IdVinculo>, "idContactoNuevo": <idContactoCorrecto>}`.
3. Verificar que la cuenta corriente refleja el cambio (igual que Escenario 1).
4. Verificar, consultando `Compras` directamente (o vía `/api/compras/{idCompra}`), que `IdContacto` de la Compra vinculada **no cambió** — la reasignación quedó acotada a cuentas corrientes.

## Escenario 5 — Detección de candidatos (US2)

1. `GET /api/reasignacion-contacto/candidatos`.
2. Verificar que la lista NO incluye el `IdMovimiento=2712` si ya fue reasignado (Escenario 1) — el contacto efectivo ya coincide con la sugerencia, deja de ser candidato.
3. Verificar que la lista no incluye los ~35 falsos positivos conocidos (términos genéricos bancarios) del escaneo manual previo.

## Escenario 6 — Descartar un falso positivo (FR-010)

1. De la lista del Escenario 5, elegir un candidato que sea claramente ruido (si quedara alguno pese a la lista de exclusión).
2. `POST /api/reasignacion-contacto/candidatos/descartar` con su `(origen, idOrigen, idContactoSugerido)`.
3. Repetir `GET /api/reasignacion-contacto/candidatos` — ya no aparece.
4. Repetirlo una segunda vez (mismo descarte) — no falla, no duplica (idempotente).

## Resultado esperado

Los 6 escenarios cubren US1 (P1/MVP), US2 (P2) y US3 (historial, integrado en Escenario 1 paso 6) end-to-end contra `WC` real, sin modificar `Movimientos Galicia`/`Movimientos BNA`/`Compras` en ningún caso — toda la corrección vive en `ReasignacionesContacto`.
