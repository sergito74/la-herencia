# Quickstart: validar el flujo de caja real (018)

## Prerrequisitos

- Backend y frontend corriendo (sesión requerida, 016-autenticacion).
- Migración previa ya aplicada en `WC`: `CuentasBancarias` con las 3 cuentas BNA + Galicia, `Movimientos BNA.IdCuentaBancaria` poblado al 100% (`backend/scripts/separar_cuentas_bna.py`, ya ejecutado).
- Datos reales de `Movimientos BNA`/`Movimientos Galicia` ya existentes en `WC` (no requiere carga nueva).

## Escenario 1 — El neto mensual cuadra contra Tesorería (SC-002)

1. Elegir un mes con movimientos conocidos en ambos bancos (ej. julio 2026).
2. `GET /api/flujo-caja/resumen?fechaDesde=2026-07-01&fechaHasta=2026-07-31&granularidad=mensual`.
3. Sumar manualmente, desde `GET /api/tesoreria/bna/movimientos` y `GET /api/tesoreria/galicia/movimientos` (mismo rango), los importes de ese mes.
4. Comparar: la suma de `porCuenta[].ingresos`/`egresos` de flujo-caja debe coincidir exactamente con la suma de Tesorería para el mismo banco y rango (antes de excluir internos).

**Resultado esperado**: SC-002 — ningún movimiento se pierde ni se duplica entre Tesorería y Flujo de caja real.

## Escenario 2 — Movimientos internos separados del neto (User Story 2)

1. Ubicar en `WC` un movimiento de Galicia con `[Grupo de Conceptos] LIKE '%Inversiones%'` en el rango consultado.
2. `GET /api/flujo-caja/detalle?fechaDesde=...&fechaHasta=...&soloInternos=true` y verificar que ese movimiento aparece con `esInterno = true`.
3. Verificar que su importe NO está incluido en `totalNeto` del resumen del mismo período, pero SÍ está incluido en `movimientosInternos.total`.

**Resultado esperado**: FR-002 — el neto operativo no se contamina con movimientos de inversión financiera.

## Escenario 3 — Las 3 cuentas BNA se distinguen (User Story 3)

1. `GET /api/flujo-caja/detalle?fechaDesde=2011-01-01&fechaHasta=2011-12-31&banco=BNA` (dentro de la vigencia de la primera cuenta, 12301640001709).
2. Verificar que todas las filas devueltas tienen `numeroCuentaBancaria = "12301640001709"`.
3. Repetir con un rango 2023 (dentro de la vigencia de 6150111899) y verificar que no aparece ningún movimiento de las cuentas dadas de baja.

**Resultado esperado**: FR-003 — ningún movimiento se atribuye a la cuenta equivocada.

## Escenario 4 — Última fecha con datos visible (User Story 4)

1. `GET /api/flujo-caja/resumen` sin filtros (rango por defecto).
2. Verificar que `ultimaCarga` trae una fecha por cada cuenta (BNA×3 o solo la vigente según se decida en el diseño de pantalla, y Galicia), y que esa fecha coincide con `MAX(Fecha)` real de cada tabla de origen.

**Resultado esperado**: FR-004 — el usuario puede distinguir "sin movimientos este mes" de "no se cargó el extracto".
