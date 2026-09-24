# API Contract: `/api/imputacion` y extensión de `/api/ordenes` (017-imputacion-automatica-costos)

Estilo y convenciones idénticas a `/api/remitos`/`/api/ordenes`: errores de negocio → 400; escritura exclusiva contra `WC`; toda la API requiere sesión (016-autenticacion).

## Propuestas de reclasificación

### `GET /api/imputacion/propuestas`
Query params: `idDetalleCompra?`, `estado?` (`pendiente|aprobada|requiereIntervencion`), `origen?` (`insumo|contratista`), `page`, `pageSize`.
- Lista las fracciones vigentes (última `IdCorrida` por renglón de factura).
- Cada fila incluye `idPropuesta`, `idCorrida`, `origen`, `idDetalleCompra` (con datos legibles del proveedor/factura), `idOrdenTrabajo`, `idLote/idCultivo/idCampania` (o `idCentroCosto` para Adm. General, o `null` para "en stock"), `esGanaderia`, `importe`, `estado`.

### `GET /api/imputacion/propuestas/{idDetalleCompra}/trazabilidad`
- Remonta la cadena real (capa FIFO → `tblRemitoCompra` → remito; o `OrdenesContratistaFacturas` → Orden) para explicar de dónde sale cada fracción de la propuesta vigente de ese renglón (FR-013). No persiste nada — se recalcula on-demand.

### `POST /api/imputacion/propuestas/{idCorrida}/aprobar`
- Sin body, o `{ correcciones?: [{ idPropuesta, idLote?, idCultivo?, idCampania?, importe? }] }` para aprobar con cambios (User Story 2, Acceptance Scenario 2).
- Marca todas las fracciones de esa `IdCorrida` como `Aprobada`, `FechaAprobacion = now()`.
- Si hubo `correcciones`, actualiza `ImputacionReferencias` para ese producto/contexto (FR-008).
- 409 si la corrida ya no es la vigente (una corrida más nueva la reemplazó mientras tanto).

### `POST /api/imputacion/recalcular`
Body: `{ idDetalleCompra? , idOrdenTrabajo? }` (al menos uno).
- Dispara manualmente una corrida nueva para el/los renglón(es) afectados — uso principal: pruebas y resolución manual de un caso `RequiereIntervencion` después de corregir su causa (ej. vincular la Orden faltante).
- El disparo automático (FR-011/FR-012) ocurre igual sin este endpoint, al detectar el sistema un cambio en remito/distribución/vínculo de contratista.

## Vínculo factura de contratista ↔ Órdenes (N a N)

Reemplaza el `POST /api/ordenes/{idOrden}/factura` de 011 (que solo aceptaba una factura por orden).

### `POST /api/ordenes/{idOrden}/factura-contratista`
Body: `{ idCompra: number }`.
- Agrega un vínculo en `OrdenesContratistaFacturas` — ya no bloquea si la Orden u otra Orden ya tienen esa (u otra) factura vinculada (User Story 4, Acceptance Scenario 2).

### `DELETE /api/ordenes/{idOrden}/factura-contratista/{idCompra}`
- Quita un vínculo puntual (antes solo se podía reemplazar el único vínculo existente).

## Comparación contra el motor heredado

### `GET /api/imputacion/comparacion`
Query params: `idCampania` (requerido).
- Devuelve `{ campania, costoHeredado: { totalCostoPesos, totalCostoDolares }, costoNuevo: { totalPesos, totalAprobado, totalPendiente }, diferenciaPesos, diferenciaPorcentual, comparacionParcial: boolean }`.
- `costoHeredado` viene de `resultado.py::resumen_campania_heredado()` (012, sin modificar).
- `costoNuevo` suma únicamente fracciones `Estado = 'Aprobada'` de `ImputacionPropuestas` para ese `idCampania`; `comparacionParcial = true` si existen fracciones `Pendiente`/`RequiereIntervencion` para esa campaña.

## Ampliación de lecturas — 2026-09-24

Propuestas y fracciones de documentos incorporan `cantidad: number | null` y `unidad: string | null`: cantidad física atribuida al destino; null significa no registrada/no aplicable, nunca cero implícito. Propuestas incorporan `producto`, `idCompra`, `proveedor`, `tipoDocumento`, `numeroDocumento`, `fechaDocumento`, `monedaDocumento`, `cultivo`, `campania`, `lote`, `centroCosto` (nullable). El origen Contratista resuelve el encabezado por IdCompra; Insumo por IdDetalleCompra. Intervención devuelve el mismo contexto comercial. Los importes de fracciones son pesos; monedaDocumento identifica únicamente el documento original. Los resúmenes se calculan sobre las fracciones completas mostradas de cada documento/propuesta, separando cantidades por producto/unidad.

## Intervención manual

### `GET /api/imputacion/pendientes-intervencion`
Query params: `page`, `pageSize`.
- Lista las corridas en `Estado = 'RequiereIntervencion'`, con el motivo (`sinOrdenVinculada` | `repartoNoCierra`) y el detalle necesario para que el usuario resuelva (factura, monto, diferencia).
