# Quickstart: validar Órdenes de Trabajo (011)

## Prerrequisitos

- Backend y frontend corriendo igual que para Remitos (ver `specs/010-remitos/spec.md` si hace falta recordar el arranque).
- Conexión de solo lectura a `WC` disponible para las consultas de verificación; escritura solo tras backup verificado y autorización explícita (Principio II de la constitución).
- Tablas nuevas creadas (`backend/scripts/crear_tablas_ordenes.py`, idempotente) e índices aplicados (`backend/scripts/indices_ordenes.py`) antes de migrar datos.
- Migración ejecutada (`backend/scripts/migrar_ordenes.py`) solo en un entorno autorizado, nunca contra `LaHerencia`.

## Escenario 1 — Planificar una orden multi-lote y multi-campaña

1. `POST /api/ordenes` con dos lotes de cultivos distintos (ej. un lote de girasol campaña 2026/2027 y otro de soja campaña 2025/2026) en el mismo renglón de insumo, cada uno con su propia dosis/ha.
2. Verificar que `CantidadTotal` del renglón de insumo = suma de `CantidadAsignada` calculada en cada distribución.
3. Verificar que se generó un `Formulario de Retiro` con numeración propia (`GET /api/ordenes/{id}/formulario-retiro`).
4. Verificar que el stock del insumo bajó exactamente esa cantidad (comparar contra el costeo FIFO de 010-remitos, `GET` de existencias).

**Resultado esperado**: SC-001 — el flujo completo (crear orden + obtener Formulario de Retiro) toma menos de 5 minutos de uso real; la orden queda en estado `Planificada`.

## Escenario 2 — Devolución que ajusta el cierre exacto

1. Sobre la orden del escenario 1, registrar una devolución parcial de uno de los insumos.
2. Verificar que el stock reingresa esa cantidad (nueva capa FIFO).
3. Intentar registrar una devolución mayor a lo retirado y no devuelto → debe rechazarse.
4. Verificar que `suma(CantidadAsignada) + suma(Devoluciones) = CantidadTotal` sigue cerrando exacto.

**Resultado esperado**: SC-002 — 0% de diferencias sin explicar.

## Escenario 3 — Maquinaria propia y contratista en la misma orden

1. Agregar un renglón de maquinaria propia (`POST /api/ordenes/{id}/maquinaria`) con costo por hectárea cargado a mano.
2. Vincular una factura de contratista (`POST /api/ordenes/{id}/factura`) a la misma orden.
3. Verificar que ambos costos se prorratean entre los lotes de la orden por superficie y quedan visibles en el detalle de la orden, en pesos y dólares.

**Resultado esperado**: costos de insumo, maquinaria y contratista conviven en la misma orden sin excluirse.

## Escenario 4 — Anulación devuelve stock

1. Anular una orden `Planificada` con motivo.
2. Verificar que las capas FIFO consumidas por esa orden vuelven al stock disponible.

**Resultado esperado**: SC-004 — el saldo de existencias después de anular coincide con el saldo previo a crear la orden.

## Escenario 5 — Costo por Cultivo/Campaña sin fecha de cierre

1. Consultar `GET /api/ordenes/resultado-cultivo?idCultivo=...&idCampania=...` para una campaña ya cosechada (fecha de cosecha pasada).
2. Agregar una orden nueva de esa misma campaña (ej. un control post-cosecha) y volver a consultar.
3. Verificar que el costo total se actualiza sin ningún paso de "reapertura" de período.

**Resultado esperado**: SC-003.

## Escenario 6 — Migración de datos heredados (entorno autorizado únicamente)

1. Ejecutar `migrar_ordenes.py` en modo dry-run (si el script lo soporta, siguiendo el patrón de `migrar_remitos.py`) y revisar el resumen: 153 órdenes, 820 renglones, 4.319 distribuciones, contratista unificado a `Contactos`, lote `PRUE` excluido, 13 renglones marcados `RevisarMigracion`.
2. Solo tras backup verificado, ejecutar la migración real.
3. Verificar que el conteo final coincide con lo relevado en `spec.md` (Hallazgos de datos reales).
