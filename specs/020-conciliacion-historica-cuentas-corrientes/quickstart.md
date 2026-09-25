# Quickstart: Conciliación histórica de cuentas corrientes

## Prerrequisitos

- Backup de `WC` verificado (Constitución, Principio II) antes de correr `--apply`.
- Migración de esquema aplicada: columnas `Origen`/`NotaConciliacion` en `AplicacionesPago`, tabla `SaldosReferenciaAccess` creada.
- Archivo de saldos de referencia Access (CSV/Excel) provisto por el usuario, cargado con `cargar_saldos_referencia_access.py`.

## Escenario 1 — Dry-run del histórico

```
cd backend
.venv\Scripts\python.exe -m scripts.conciliar_historico_cuentas_corrientes
```

**Esperado**: reporte en consola con total de movimientos, exactos/mejor esfuerzo/excepciones, sin ninguna escritura en `WC` (verificar contando filas de `AplicacionesPago` antes y después).

## Escenario 2 — Aplicar el histórico

```
.venv\Scripts\python.exe -m scripts.conciliar_historico_cuentas_corrientes --apply
```

**Esperado**: las filas reportadas como "exacto"/"mejor esfuerzo" en el Escenario 1 ahora existen en `AplicacionesPago` con el `Origen` correspondiente; el CSV de auditoría se generó en el directorio actual.

## Escenario 3 — Re-ejecución idempotente

Correr el mismo comando (`--apply`) una segunda vez.

**Esperado**: 0 filas nuevas insertadas (todos los movimientos ya tienen aplicación vigente); el reporte lo indica explícitamente.

## Escenario 4 — Revisar un contacto con casos de mejor esfuerzo

```
GET /api/conciliacion-historico/123/detalle
```

**Esperado**: la respuesta lista las aplicaciones `automatica-mejor-esfuerzo` con su `notaConciliacion`, y las excepciones si las hay (spec US2, contracts/api.md).

## Escenario 5 — Corregir un caso mal aplicado

1. `POST /api/aplicaciones-pago/{idAplicacion}/anular` (endpoint existente de 019) sobre una aplicación de mejor esfuerzo incorrecta.
2. Aplicar manualmente el movimiento al documento correcto vía el flujo existente de 019 (botón "Aplicar a factura/venta…").

**Esperado**: `GET /api/conciliacion-historico/123/detalle` refleja el cambio (la anulada sigue en el historial, la nueva aparece con `Origen='manual'`).

## Escenario 6 — Verificar saldo contra Access

```
GET /api/conciliacion-historico/saldos?estado=con-diferencia
```

**Esperado**: solo aparecen contactos con `SaldosReferenciaAccess` cargado y `abs(diferencia) > TOLERANCIA_SALDO`; para cada uno se puede cruzar con el Escenario 4 para ver si la diferencia coincide con casos de mejor esfuerzo o excepciones pendientes de ese contacto (spec US3).
