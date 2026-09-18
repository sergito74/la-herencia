# Quickstart: Validar Tarjetas de Crédito end-to-end

## Prerrequisitos

- Backend corriendo (`python -m uvicorn src.main:app --port 8000`), apuntando a `WC` (`LA_HERENCIA_DATABASE=WC`, default).
- Frontend corriendo (`npm run dev` en `frontend/`).
- Preflight CORS verificado para `PUT`/`DELETE`/`PATCH` de los nuevos endpoints (mismo chequeo que 006/007) — `curl -X OPTIONS .../tarjetas-resumenes/1 -H "Access-Control-Request-Method: DELETE"` debe responder `200` con el método en `access-control-allow-methods`.
- Al menos un contacto real existente para usar como comprador de una compra en cuotas (`GET /api/contactos?pageSize=1`).

## Escenario 1 — Catálogo de tarjetas (Historia 4)

1. `GET /api/tarjetas` → devuelve las 5 tarjetas reales con nombre, banco y `activa`.
2. Confirmar que las 5 aparecen como `activa=true` (estado real actual en `WC`).

## Escenario 2 — Búsqueda y detalle de resúmenes reales (Historia 1)

1. `GET /api/tarjetas-resumenes` sin filtros → `items: []` (FR-010).
2. `GET /api/tarjetas-resumenes?idTarjeta=<real>&fechaCierreDesde=2020-01-01&fechaCierreHasta=2026-12-31` → devuelve resúmenes reales de esa tarjeta.
3. Elegir un `idResumen` real con líneas y otro sin líneas (usar `WC` directo para encontrar uno con `NOT EXISTS` en `Tarjetas_Resumenes_Lineas` — hay 70 de 293 reales así). `GET /api/tarjetas-resumenes/{id}` en ambos casos → el segundo responde `200` con `lineas: []`, sin error (FR-009).
4. Verificar en el resumen con líneas que `totalCalculado` coincide con la fórmula real (data-model.md) sumada a mano contra los valores reales de esa fila.

## Escenario 3 — Alta de resumen nuevo, con y sin líneas (Historia 1)

1. `POST /api/tarjetas-resumenes` con cabecera completa y 2 líneas (una con importe negativo). Verificar `201` y `totalCalculado` correcto incluyendo el signo negativo.
2. `POST /api/tarjetas-resumenes` con `lineas: []` (solo cabecera). Verificar `201` igual, sin exigir líneas.
3. Repetir el alta del paso 1 con el mismo `idTarjeta`+`codigo` → verificar `201` (no `400`) con `warnings` no vacío (FR-012).
4. `GET /api/tarjetas-resumenes?numeroDocumento=...` (o el filtro correspondiente) y confirmar que ambos aparecen.

## Escenario 4 — Edición, bloqueo y eliminación de resumen (FR-013)

1. `POST /api/tarjetas-resumenes/{id}/lock` con `lockToken = uuid A` → `200`.
2. `POST .../lock` con `lockToken = uuid B` (sin liberar A) → `409`.
3. `POST .../lock` con `lockToken = uuid B, force: true` → `200`.
4. `PUT /api/tarjetas-resumenes/{id}` con `X-Lock-Token: B` cambiando un cargo de cabecera → `200`, `totalCalculado` recalculado.
5. `DELETE /api/tarjetas-resumenes/{id}` con `X-Lock-Token: B` → `204`. Verificar en `WC` que cabecera y líneas desaparecieron sin dejar huérfanos.

## Escenario 5 — Alta de compra en cuotas con cronograma automático (Historia 3)

1. `POST /api/tarjetas-cuotas` con `importeTotal=10000`, `cantidadCuotas=3` → verificar `201` y que las 3 cuotas generadas son `3333.33 / 3333.33 / 3333.34` (o el orden que dé el redondeo — la suma debe ser exactamente `10000`), con vencimientos mensuales sucesivos desde la fecha de compra.
2. `GET /api/tarjetas-cuotas?idContacto=<el usado>` → aparece en el listado con su cantidad de cuotas.
3. `PATCH /api/tarjetas-cuotas/{id}/cuotas/{idCuota}` con `{"cobrado": true}` → `200`, y el listado de cuotas de ese `idPagoTarjeta` refleja el cambio.
4. Confirmar en `WC` que la fila existe en `[Tarjetas de Credito]`/`[Cuotas Tarjetas de Credito]` y **no existe** en `LaHerencia`.

## Escenario 6 — Compra en cuotas con una sola cuota (edge case)

1. `POST /api/tarjetas-cuotas` con `cantidadCuotas=1` → `201`, una sola cuota con el importe total completo.

## Escenario 7 — Cuenta corriente de tarjeta (Historia 2)

1. Elegir una tarjeta real con varios resúmenes cargados. `GET /api/tarjetas/{idTarjeta}/movimientos` → un movimiento por resumen, ordenados por `fechaCierre`, con `saldoAcumulado` correcto.
2. Verificar a mano que el `saldoAcumulado` del último movimiento es igual a `Σ(deuda) - Σ(credito)` de todos los movimientos de esa tarjeta (SC-002).
3. Confirmar que ninguna cuota de compra en cuotas aparece como movimiento separado en esta cuenta corriente (decisión de "solo resúmenes", evita doble conteo — ver research.md §3).

## Escenario 8 — Navegación desde el movimiento hacia el resumen (FR-003)

1. Desde la pantalla de cuenta corriente de la tarjeta (Escenario 7), hacer clic en un movimiento.
2. Verificar que navega a `/finanzas/tarjetas/resumenes/{idResumen}` con el resumen correcto abierto.

## Escenario 9 — Fidelidad de cálculo contra datos históricos reales (SC-002)

1. Elegir las 5 tarjetas reales. Para cada una, sumar a mano (fuera del sistema) `totalCalculado` de todos sus resúmenes reales, ordenados por `fechaCierre`.
2. Comparar contra el `saldoAcumulado` final que devuelve `GET /api/tarjetas/{idTarjeta}/movimientos` para esa tarjeta.
3. Confirmar coincidencia exacta en las 5 tarjetas — documentar el resultado (mismo criterio que T086/T087 de 006/007).

## Escenario 10 — Navegación del menú

1. Abrir el nav y confirmar que "Tarjetas" aparece dentro de "Finanzas", entre "Cuentas corrientes" e "Impuestos y retenciones".
2. Confirmar que el catálogo, resúmenes y compras en cuotas son accesibles desde ahí.
