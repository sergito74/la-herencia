# Quickstart: Conciliación histórica de cuentas corrientes

**Estado (2026-09-25)**: Escenarios 1-4 ejecutados y validados contra `WC` real. Escenario 5 no se ejecutó de punta a punta para no anular una aplicación real como efecto de una validación (se deja para cuando el usuario corrija un caso real). Escenario 6 no aplica todavía: US3 está pospuesta (no existe `SaldosReferenciaAccess` con datos ni el endpoint `/saldos` — ver research.md §2).

## Prerrequisitos

- Backup de `WC` verificado (Constitución, Principio II) antes de correr `--apply` — hecho: `backups/WC_pre_conciliacion_historico_20260925.bak`.
- Migración de esquema aplicada: columnas `Origen`/`NotaConciliacion` en `AplicacionesPago`, tabla `SaldosReferenciaAccess` creada — hecho.
- ~~Archivo de saldos de referencia Access...~~ no aplica: US3 pospuesta, ver research.md §2.

## Escenario 1 — Dry-run del histórico

```
cd backend
.venv\Scripts\python.exe -m scripts.conciliar_historico_cuentas_corrientes
```

**Esperado**: reporte en consola con total de movimientos, exactos/mejor esfuerzo/excepciones, sin ninguna escritura en `WC` (verificar contando filas de `AplicacionesPago` antes y después).

**Resultado real**: 12.762 movimientos → 5.010 exactos, 3 mejor esfuerzo, 7.749 excepciones. 0 filas escritas (confirmado).

## Escenario 2 — Aplicar el histórico

```
.venv\Scripts\python.exe -m scripts.conciliar_historico_cuentas_corrientes --apply
```

**Esperado**: las filas reportadas como "exacto"/"mejor esfuerzo" en el Escenario 1 ahora existen en `AplicacionesPago` con el `Origen` correspondiente; el CSV de auditoría se generó en el directorio actual.

**Resultado real**: 3.786 movimientos aplicados (3.781 exactos + 5 mejor esfuerzo — menos que en el dry-run porque la corrida real descuenta saldo entre movimientos del mismo run, a diferencia del dry-run que no escribe nada). Encontrados y corregidos 2 bugs reales en el camino (ver tasks.md Fase 3): reclasificación duplicada causando `KeyError`, y columna `Origen` demasiado angosta (`varchar(20)` → `varchar(30)`).

## Escenario 3 — Re-ejecución idempotente

Correr el mismo comando (`--apply`) una segunda vez.

**Esperado**: 0 filas nuevas insertadas (todos los movimientos ya tienen aplicación vigente); el reporte lo indica explícitamente.

**Resultado real**: segundo dry-run tras el `--apply` → 8.976 movimientos restantes (los que quedaron como excepción), 0 exactos, 0 mejor esfuerzo. Confirmado.

## Escenario 4 — Revisar un contacto con casos de mejor esfuerzo

```
GET /api/conciliacion-historico/resumen?soloConDudas=true
GET /api/conciliacion-historico/258/detalle
```

**Esperado**: la respuesta lista las aplicaciones `automatica-mejor-esfuerzo` con su `notaConciliacion`, y las excepciones si las hay (spec US2, contracts/api.md).

**Resultado real**: `resumen?soloConDudas=true` → 190 contactos. `258/detalle` (Cargill) → 285 aplicaciones automáticas + 291 excepciones con `subcategoria`/`motivo`. También validado en la pantalla `/finanzas/conciliacion-historico` del frontend.

## Escenario 5 — Corregir un caso mal aplicado

1. `POST /api/aplicaciones-pago/{idAplicacion}/anular` (endpoint existente de 019) sobre una aplicación de mejor esfuerzo incorrecta.
2. Aplicar manualmente el movimiento al documento correcto vía el flujo existente de 019 (botón "Aplicar a factura/venta…").

**Esperado**: `GET /api/conciliacion-historico/123/detalle` refleja el cambio (la anulada sigue en el historial, la nueva aparece con `Origen='manual'`).

**Estado**: no ejecutado contra datos reales — anularía una de las únicas 5 aplicaciones de mejor esfuerzo existentes sin necesidad real de corregirla todavía. La lógica está cubierta por los tests de 019 (endpoint de anulación) y por el filtro `Anulada = 0` que ya usa `detalle_contacto` (mismo filtro que `aplicaciones_pago.repository.estado_movimiento`). Queda para ejecutarse la primera vez que el usuario corrija un caso real.

## Escenario 6 — Verificar saldo contra Access

**Pospuesto (US3)**: no existe el endpoint `/saldos` ni datos en `SaldosReferenciaAccess` — ver research.md §2 (actualizado 2026-09-25). El saldo reconstruido ya existe en `vw_MovimientosCuenta_Saldo` (misma fuente que 004); falta un dato de verdad externo con el cual compararlo, a conseguir en una etapa posterior.
