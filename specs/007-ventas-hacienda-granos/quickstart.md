# Quickstart: Validar Ventas de Hacienda y Ventas de Granos end-to-end

## Prerrequisitos

- Backend corriendo (`python -m uvicorn src.main:app --port 8000`), apuntando a `WC` (`LA_HERENCIA_DATABASE=WC`, default).
- Frontend corriendo (`npm run dev` en `frontend/`).
- Preflight CORS ya verificado para `PUT`/`DELETE` de los nuevos endpoints (research.md §6) — `curl -X OPTIONS .../ventas-hacienda/1 -H "Access-Control-Request-Method: DELETE"` debe responder `200` con `DELETE` en `access-control-allow-methods` antes de probar nada desde el navegador.
- Al menos un contacto de tipo Consignatario/Comprador/Multiple existente para Hacienda; uno de tipo Multiple para Granos (`GET /api/contactos?tipoContacto=Multiple&pageSize=1`).

## Escenario 1 — Alta de Venta de Hacienda (Historia 1)

1. `POST /api/ventas-hacienda` con un `idConsignatario`/`idEstablecimiento`/`idTipoDocumento` reales, una línea con `idComprador`/`idTipoProducto`/`cantidad`/`precioUnitarioA`.
2. Verificar `201` y que `subTotal`/`comision`/`iva`/`importe`/`importeTotal` coinciden con la fórmula real (data-model.md).
3. `GET /api/ventas-hacienda?numeroDocumento=<el usado>` y confirmar que aparece.
4. Verificar en SQL Server: la fila existe en `WC.dbo.[Venta Hacienda]` y **no existe** en `LaHerencia.dbo.[Venta Hacienda]`.

## Escenario 2 — Comprador distinto por línea (Historia 1, Acceptance Scenario 2)

1. Cargar una venta con dos líneas, cada una con un `idComprador` distinto.
2. Verificar que ambas líneas se guardan con su propio comprador, sin que la cabecera exija un comprador único.

## Escenario 3 — Edición, bloqueo y "forzar" (Historias 2, 3)

1. `POST /api/ventas-hacienda/{id}/lock` con `lockToken = "A"` → `200`.
2. `POST /api/ventas-hacienda/{id}/lock` con `lockToken = "B"` (sin liberar A) → `409`.
3. `POST /api/ventas-hacienda/{id}/lock` con `lockToken = "B", force: true` → `200` (toma el lock igual).
4. `PUT /api/ventas-hacienda/{id}` con `X-Lock-Token: B` y un precio de línea cambiado → `200`, totales recalculados.
5. `DELETE /api/ventas-hacienda/{id}` con `X-Lock-Token: B` → `204`. Verificar que cabecera, líneas y vencimientos desaparecieron de `WC`.

## Escenario 4 — Vencimientos con importe propio (Historia 2)

1. Cargar una venta con 2 vencimientos, cada uno con `fecha` e `importe` distintos.
2. Editar la venta quitando uno de los vencimientos.
3. Verificar que el vencimiento restante conserva su importe original.

## Escenario 5 — Documento duplicado, advertencia no bloqueante (FR-009a)

1. Cargar dos ventas de hacienda con el mismo `idConsignatario` y el mismo `numeroDocumento`.
2. Verificar que la segunda igual devuelve `201` (no `400`), con `warnings` no vacío.

## Escenario 6 — Listado de Ventas de Granos vacío por defecto (Historia 5, FR-010)

1. `GET /api/ventas-granos` sin ningún filtro → `items: []`.
2. `GET /api/ventas-granos?campania=2025/2026` → devuelve resultados reales si existen ventas de esa campaña en el histórico migrado a `WC`.

## Escenario 7 — Alta de Venta de Granos con ajustes y deducciones (Historia 6)

1. `POST /api/ventas-granos` con cabecera completa, un ajuste y una deducción.
2. Verificar `201` y que `importeNetoAPercibir` coincide con la fórmula real (data-model.md): `subTotal = cantidadVendida × precioKg + Σajustes`; `totalDeducciones` restado al final.
3. `GET /api/ventas-granos/{id}` y confirmar que `ajustes[]`/`deducciones[]` se devuelven por separado, no mezclados en una sola línea (FR-011).

## Escenario 8 — Edición y eliminación de Venta de Granos (Historia 7)

1. `PUT /api/ventas-granos/{id}` agregando una deducción nueva → verificar que `importeNetoAPercibir` baja en consecuencia.
2. `DELETE /api/ventas-granos/{id}` → `204`, verificar que cabecera+ajustes+deducciones desaparecieron sin dejar huérfanos (`SELECT` directo por `IdVenta` en `Venta Granos_Ajustes`/`Venta Granos_Deducciones`).

## Escenario 9 — Fidelidad de cálculo contra ventas históricas reales (SC-002, SC-003)

1. Elegir 5 `IdVenta` reales de `Venta Hacienda` (y 5 de `Venta Granos`) con sus detalles/ajustes/deducciones.
2. Recalcular manualmente (fuera del sistema) el importe/importe total (Hacienda) o el importe neto a percibir (Granos) con las fórmulas de `data-model.md`.
3. Comparar contra lo que produce el backend real para esos mismos datos de entrada.
4. Confirmar coincidencia exacta en los 10 casos — documentar el resultado (igual criterio que el Escenario 7 de `006-carga-compras/quickstart.md`).

## Escenario 10 — Navegación

1. Abrir `/ventas` (o el nav) y confirmar el submenú "Ventas" con "Hacienda"/"Granos".
2. Confirmar que "+ Nueva venta de hacienda" vive en `/ventas/hacienda` y "+ Nueva venta de granos" en `/ventas/granos`.
