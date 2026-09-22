# Quickstart: validar Conciliación manual de consumos de tarjeta (009)

## Prerrequisitos

- Backend y frontend corriendo igual que para Órdenes de Trabajo (ver `specs/011-ordenes-trabajo/quickstart.md`).
- Conexión contra `WC` — confirmar con `DB_NAME()` antes de cualquier escritura. Este módulo **sí escribe** en `WC` (vínculos y estados de línea), a diferencia de 012; toda escritura de prueba debe revertirse con el `DELETE` correspondiente al terminar.
- Frontend contra `http://localhost:3000` (no `127.0.0.1`, falla por CORS).

## Escenario 1 — Bandeja de pendientes

1. Entrar a `/finanzas/tarjetas/conciliacion`. Verificar que carga la lista de líneas pendientes (sin vínculo ni estado).
2. Probar filtros por tarjeta, proveedor y período (`fechaCierreDesde`/`fechaCierreHasta`).
3. Verificar que las líneas con sugerencia exacta (`GET /api/tarjetas-resumenes/pendientes` → `sugerencia.estado === "exacta"`) aparecen primero.

**Resultado esperado**: Historia 1. Verificado 2026-09-22 vía API: 281 líneas pendientes reales, 35 con sugerencia exacta.

## Escenario 2 — Panel de conciliación de una línea real

1. Abrir una línea desde la bandeja (`GET /api/tarjetas-resumenes/lineas/{id}/candidatos`).
2. Verificar que se ven: la línea, las "hermanas" (otras líneas pendientes del mismo proveedor), el PDF del resumen si existe (`urlResumenOriginal`), y la canasta de documentos del proveedor de la línea.
3. Usar el buscador de la canasta (`GET /api/tarjetas-resumenes/documentos-buscar?q=`) para sumar un documento de otro proveedor.
4. Vincular la línea a un documento que cierre exacto en pesos (`POST /api/tarjetas-resumenes/lineas/{id}/compras`), confirmar que sale de pendientes, y quitar el vínculo (`DELETE /api/tarjetas-resumenes/lineas/{id}/compras/{idVinculo}`) para revertir y confirmar que vuelve a pendientes.

**Resultado esperado**: Historia 2. Verificado 2026-09-22: línea 704 (Corredores Viales, $1.258,38) vinculada a su factura exacta (HTTP 201), desaparece de pendientes; `DELETE` la devuelve. WC vuelve al estado original.

## Escenario 3 — Notas de ajuste de tipo de cambio (USD)

1. Buscar una línea pendiente cuya sugerencia/candidatos incluya una factura en dólares (`moneda: "Dolares"`).
2. Verificar que las NC/ND `ajustaTipoCambio: true` del mismo proveedor aparecen destacadas, ordenadas por cercanía de fecha a la factura.
3. Si no hay nota disponible, verificar que se muestra el importe aproximado (tipo de cambio implícito) como pista, sin inventar una conversión definitiva.
4. Al vincular factura + nota, confirmar que queda guardada la relación en `CompraDocumentosRelacionados`.

**Resultado esperado**: Historia 3. **Nota**: el 2026-09-22 no se encontró entre las 281 líneas pendientes reales ninguna con factura en USD y nota de ajuste disponible para probar de punta a punta (`spec.md` documenta que `CompraDocumentosRelacionados` tiene 0 filas hoy); la lógica se verificó por los 16 tests de `test_conciliacion_documentos.py` y lectura de código (`conciliacion_documentos.py`, `PanelConciliacion.tsx`). Repetir este escenario quan aparezca un caso real.

## Escenario 4 — Muchas líneas contra muchos documentos

1. En la bandeja, tildar 2+ líneas pendientes del mismo proveedor.
2. Tildar 2+ documentos de la canasta.
3. Verificar la propuesta de reparto editable (`POST /api/tarjetas-resumenes/lineas/reparto-propuesta`): debe proponer un reparto por importe y mostrar la diferencia de cada línea.
4. Guardar de una vez (`POST /api/tarjetas-resumenes/lineas/conciliar-reparto`), con motivo de diferencia si alguna línea queda fuera de tolerancia (±$0,10).
5. Revertir cada vínculo creado con `DELETE .../compras/{idVinculo}`.

**Resultado esperado**: Historia 4. Verificado 2026-09-22: líneas 704+710 (Corredores Viales) contra 2 facturas distintas — reparto 1:1 por importe, diferencia $0,01 en una línea (dentro de tolerancia, no requirió motivo), `conciliar-reparto` devolvió `{"lineas":2,"vinculos":2}` (HTTP 201). Revertido, bandeja vuelve a 281.

## Escenario 5 — Aceptar sugerencias exactas con vista previa

1. Abrir la vista previa (`GET /api/tarjetas-resumenes/pendientes/exactas`): debe listar solo combinaciones únicas y exactas en pesos, sin aplicar nada todavía.
2. Confirmar una o más (`POST /api/tarjetas-resumenes/pendientes/aceptar-exactas` con `idsLineas`).
3. Verificar la respuesta `{"aplicadas": N, "omitidas": [...]}` — una línea puede quedar omitida si su combinación dejó de ser única/exacta entre el momento de la vista previa y la confirmación (revalidación de seguridad).
4. Revertir los vínculos aplicados.

**Resultado esperado**: Historia 5. Verificado 2026-09-22: 35 propuestas reales en la vista previa; se confirmaron 2 (706, 707) — se aplicó 1 (707) y se omitió 1 (706, revalidación correcta). Revertido el vínculo aplicado.

## Escenario 6 — Sin documento / no aplica

1. Elegir una línea real sin sugerencia (ej. un impuesto o interés).
2. Marcarla "sin documento / no aplica" con motivo (`POST /api/tarjetas-resumenes/lineas/{id}/sin-documento`). Verificar que sale de pendientes.
3. Verificar el link precargado a `/compras/nueva` con proveedor, fecha e importe de la línea.
4. Quitar el estado (`DELETE /api/tarjetas-resumenes/lineas/{id}/estado`) y verificar que vuelve a pendientes.

**Resultado esperado**: Historia 6. Verificado 2026-09-22: línea 2699 ("Mercado Lobre", $100.000) marcada sin documento (motivo `Otro`, HTTP 204), pendientes 281→280; `DELETE` del estado devolvió pendientes a 281. El link a `/compras/nueva` se verificó por código (construcción de query params), no se hizo clic real en navegador.

## Escenario 7 — Exportar a Excel

1. Descargar el reporte (`GET /api/tarjetas-resumenes/reporte-conciliacion`, con filtros opcionales de tarjeta/fecha de cierre).
2. Abrir el `.xlsx` y verificar que tiene las hojas "Resúmenes", "Conciliación", "Pagos", "Proveedores sin CUIT" y "Ayuda".

**Resultado esperado**: transversal a todas las historias. Verificado 2026-09-22: HTTP 200, `.xlsx` válido, 5 hojas, 295 filas en la hoja "Resúmenes".

## Cómo revertir cualquier prueba

- Vínculo línea↔compra: `DELETE /api/tarjetas-resumenes/lineas/{idLineaConsumo}/compras/{idVinculo}` (el `idVinculo` viene en la respuesta del `POST` que lo creó, o en `comprasVinculadas` dentro de `GET /api/tarjetas-resumenes/{idResumen}`).
- Estado de línea (sin documento / diferencia aceptada): `DELETE /api/tarjetas-resumenes/lineas/{idLineaConsumo}/estado`.
- Verificar siempre que `GET /api/tarjetas-resumenes/pendientes?pageSize=300` vuelve al mismo `total` que antes de empezar a probar.
