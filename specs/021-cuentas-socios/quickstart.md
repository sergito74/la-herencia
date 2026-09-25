# Quickstart: Cuentas corrientes de socios/directores y condominio

## Prerrequisitos

- Backup de `WC` verificado (Constitución, Principio II) antes de correr el script de esquema.
- `backend/scripts/crear_tablas_cuentas_socios.py` corrido (crea `Socios` con las 4 filas fijas, `MovimientosCuentaSocio`, `AuditoriaReflejoSocio`).

## Escenario 1 — Ver los 4 socios y sus saldos

```
GET /api/cuentas-socios
```

**Esperado**: los 4 socios (Sergio, Lucy, Cond LSC, Ceci), cada uno con saldo — $0 si no tiene movimientos (FR-010, nunca ausente del listado).

## Escenario 2 — Asignar un gasto particular a un socio (caso real "Cumo Store")

```
GET /api/cuentas-socios/compras-particulares-candidatas?proveedor=Cumo
POST /api/cuentas-socios/1/asignar-gasto  { "idCompra": 2143515240 }
```

**Esperado**: la compra de Cumo Store ($29.699,10 bruto) aparece como candidata; al asignarla, se crea un movimiento `AsignacionGasto` en la cuenta de Sergio por ese importe, y una fila en `AuditoriaReflejoSocio` con `Accion='Asignacion'`. El saldo de Sergio pasa a reflejar esa deuda.

## Escenario 3 — Intentar asignar la misma compra dos veces

Repetir el `POST` del Escenario 2 (misma `idCompra`, mismo u otro socio) sin anular la asignación anterior.

**Esperado**: rechazo (409) con mensaje legible — la compra ya tiene una asignación vigente (FR-009).

## Escenario 4 — Deshacer una asignación

```
POST /api/cuentas-socios/movimientos/{idMovimiento}/anular  { "motivo": "Se asignó al socio equivocado" }
```

**Esperado**: el movimiento queda `anulada: true` (visible en el historial, no desaparece), el saldo del socio se recalcula sin él, y se agrega una fila `AuditoriaReflejoSocio` con `Accion='ReversionAsignacion'`. Repetir el Escenario 2 sobre la misma compra ahora debe funcionar (ya no hay asignación vigente).

## Escenario 5 — Registrar una devolución

```
POST /api/cuentas-socios/1/devolucion  { "importe": 15000.0, "fecha": "2025-11-20", "medio": "Transferencia", "motivo": "Devolución parcial" }
```

**Esperado**: el saldo de Sergio se reduce en $15.000; el movimiento aparece en `GET /api/cuentas-socios/1/movimientos` con `tipo: "Devolucion"`.

## Escenario 6 — Consultar auditoría

Verificar, tras los escenarios 2, 4 y 5, que `AuditoriaReflejoSocio` tiene una fila por cada acción (asignación, reversión, devolución) — ninguna acción queda sin su rastro.
