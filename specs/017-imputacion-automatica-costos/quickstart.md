# Quickstart: validar el motor de auto-clasificación (017)

## Prerrequisitos

- Backend y frontend corriendo (ver `specs/016-autenticacion/` para login, ya requerido en toda la API).
- Tablas nuevas creadas (`backend/scripts/crear_tablas_imputacion.py`, idempotente): `ImputacionPropuestas`, `OrdenesContratistaFacturas`, `ImputacionReferencias`.
- `OrdenesContratistaFacturas` migrada 1:1 desde `Ordenes_Trabajo_Contratista_Factura` (ver data-model.md) antes de probar el caso N a N.
- Datos reales disponibles en `WC`: al menos una factura de insumo con remito vinculado renglón a renglón (`tblRemitoCompra`) y consumida por una Orden de Trabajo (010/011 ya migrados).

## Escenario 1 — Propuesta de un insumo consumido íntegro por una sola campaña

1. Elegir una factura de insumo con un único vínculo `tblRemitoCompra` cuyo remito fue consumido en su totalidad por una sola Orden de Trabajo (`GET /api/ordenes/{id}` para confirmar el consumo).
2. `GET /api/imputacion/propuestas?idDetalleCompra={id}` (o equivalente) y verificar que devuelve una única fracción `Estado = 'Pendiente'` con `Importe` = importe total del renglón, `IdCultivo`/`IdCampania` de esa Orden.
3. Verificar que la propuesta expone (o permite consultar) el remito, la capa FIFO y el renglón de distribución de origen.

**Resultado esperado**: SC-001 — la propuesta se generó sin intervención manual previa.

## Escenario 2 — Reparto multi-campaña y stock sin consumir

1. Elegir (o preparar) una factura de insumo cuyo remito fue consumido parcialmente por dos Órdenes de distinto Cultivo/Campaña, con saldo todavía en stock.
2. Consultar la propuesta y verificar tres fracciones: una por cada Cultivo/Campaña (`Estado = 'Pendiente'`) y una "en stock sin consumir" (`Estado = 'Aprobada'` automáticamente, sin Cultivo/Campaña).
3. Verificar que la suma de las tres fracciones = importe total del renglón de factura.

**Resultado esperado**: FR-001/FR-002 — el reparto cierra exacto y la porción sin consumir no aparece como costo de ninguna campaña.

## Escenario 3 — Aprobar y corregir una propuesta

1. Sobre la propuesta del Escenario 1, `POST /api/imputacion/propuestas/{idCorrida}/aprobar` sin cambios.
2. Verificar que su `Estado` pasa a `Aprobada` y que `GET /api/imputacion/pendientes` ya no la lista.
3. Sobre otra propuesta pendiente, corregirla (reasignar una fracción a otro Cultivo/Campaña) antes de aprobar.
4. Verificar que la corrección queda como reparto vigente y que `ImputacionReferencias` se actualizó para ese producto (aprendizaje simple, FR-008).

**Resultado esperado**: SC-002 — revisar y aprobar toma menos de 2 minutos por factura, sin tener que buscar manualmente el origen.

## Escenario 4 — Reversión genera nueva corrida, no ajuste incremental

1. Sobre una propuesta ya `Aprobada` (Escenario 3), anular la Orden de Trabajo que la consumía.
2. Verificar que se genera una `IdCorrida` nueva con el reparto completo corregido, en estado `Pendiente`, sin sobrescribir en silencio la corrida aprobada anterior hasta que el usuario la apruebe (FR-012, Clarifications: reemplazo completo).

**Resultado esperado**: User Story 2, Acceptance Scenario 3.

## Escenario 5 — Factura de contratista sin Orden vinculada

1. Elegir una factura de un contratista (`Contactos.EsContratistaLabores = 1`) que todavía no está vinculada a ninguna Orden en `OrdenesContratistaFacturas`.
2. Consultar la propuesta para esa factura y verificar `Estado = 'RequiereIntervencion'`, sin ningún reparto calculado.

**Resultado esperado**: SC-004 — la factura queda visiblemente marcada, no se propone un reparto silencioso.

## Escenario 6 — Una factura de contratista cubre varias Órdenes (caso N a N)

1. `POST /api/ordenes/{id1}/factura-contratista` y `POST /api/ordenes/{id2}/factura-contratista` con la misma `idCompra` (dos Órdenes distintas, misma factura).
2. Verificar que ambos vínculos se guardan en `OrdenesContratistaFacturas` sin el bloqueo "la Orden ya tiene una factura" del modelo 1:1 anterior.
3. Consultar la propuesta de esa factura y verificar que el costo se reparte entre los Cultivo/Campaña de ambas Órdenes, prorrateado por superficie.
4. Forzar que la suma de lo repartido no cierre contra el total de la factura por más del umbral (research.md) y verificar `Estado = 'RequiereIntervencion'`.

**Resultado esperado**: User Story 3/4 completas; FR-010.

## Escenario 7 — Comparación contra el motor heredado

1. Elegir una Cultivo/Campaña histórica con propuestas ya aprobadas que cubran todo su período.
2. `GET /api/imputacion/comparacion?idCampania={id}` y verificar que devuelve el costo total según `vw_ResultadoCultivo_Campaña` (motor heredado, spec 012) junto al costo total de las propuestas aprobadas de este motor, con la diferencia absoluta y porcentual.
3. Repetir con una Cultivo/Campaña que todavía tiene propuestas pendientes y verificar que la respuesta aclara que la comparación es parcial.
4. Verificar que ningún valor de `vw_ResultadoCultivo_Campaña` ni de `resultado.py::costo_por_cultivo_campania` (012) cambió como consecuencia de correr este motor.

**Resultado esperado**: SC-003, SC-005 — comparación disponible sin error y sin efecto sobre los reportes existentes.

## Arranque para pruebas de usuario — 2026-09-24

Después de cambios en frontend, ejecutar `npm run build` desde `frontend` con el servidor detenido. Abrir el acceso directo habitual: ahora usa la versión compilada (`next start`) y evita compilar cada pantalla al navegar. Para desarrollo con recarga automática: `powershell -File launcher/LaHerencia.ps1 -Dev`. No alternar modos sobre un servidor que ya esté abierto; cerrarlo antes. El build se debe repetir tras cada cambio de frontend; el backend requiere reinicio tras cambios Python.
