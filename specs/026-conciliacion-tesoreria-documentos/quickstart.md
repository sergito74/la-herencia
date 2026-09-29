# Quickstart: Conciliación de Tesorería con documentos

**Escenarios históricos de referencia; no ejecutar escrituras sobre estos movimientos reales como pruebas.** Los montos de US2 son fixtures ilustrativas distintas de las cifras de esta sección. Usar fixtures de tests para confirmar reparto y estados.

Prerequisito: DDL aplicado (`scripts/extender_conciliaciones_tesoreria_documentos.py`),
backup de `WC` verificado antes.

## Escenario 1 — Buscar y conciliar un documento real de Compras

1. `GET /api/tesoreria/documentos-buscar?q=Primor` → debe aparecer la
   factura real de Primor Mayorista ($ 23.051,11, 2025-11-12) con
   `origen: "Compras"`.
2. Abrir la conciliación de un movimiento de Mercado Libre real sin
   contacto reconocido; confirmar que `GET .../candidatos` ofrece buscar
   documentos (no exige tipear un contacto de memoria).
3. `POST .../conciliacion-lote` con ese documento → el movimiento debe
   quedar conciliado, y la fila de `ConciliacionesTesoreria` debe tener
   `TipoOrigenDocumento='Compras'` e `IdOrigenDocumento` = el `IdDeuda` real.

## Escenario 2 — Reparto proporcional entre 3 documentos (caso real ML)

1. Elegir las 3 facturas reales (Primor $ 23.051,11 / Luvik $ 41.900,16 real
   / Sedafe $ 13.384,06 real) contra el movimiento de saldo de Mercado Libre
   ($ 3.717,61).
2. `GET .../conciliacion-preview` con los 3 `idsOrigen` → debe devolver
   `pagoParcial: true` y el importe repartido proporcionalmente entre los 3,
   sin que el usuario haya tipeado ningún monto.
3. Confirmar (`POST .../conciliacion-lote`) y verificar que las 3 quedan con
   `saldoPendiente` reducido en la proporción esperada.

## Escenario 3 — Aceptar diferencia por Ley 25413

1. Sobre el mismo caso, conciliar el resto (tarjeta Visa Galicia, vía
   Tarjetas/025) y verificar el residual de $ 22,17.
2. Si ese residual quedara del lado de Tesorería en vez de Tarjetas en algún
   caso futuro, `POST .../conciliacion-lote` con
   `aceptarDiferencia: {motivo: "Impuesto", detalle: "Ley 25413"}` debe
   cerrar el movimiento sin exigir que los documentos sumen exacto.

## Escenario 4 — No regresión de 024 (gate simétrico)

1. Vincular un movimiento como traspaso interno (024).
2. Intentar `POST .../conciliacion-lote` contra ese mismo movimiento →
   debe responder `409` (mismo criterio que ya prueba T025 de 024).

## Escenario 5 — Conciliación manual simple sigue funcionando (FR-009)

1. `POST /api/tesoreria/{medio}/movimientos/{id}/conciliacion` (023, sin
   pasar por el buscador) con `idContacto`+`importe` → debe seguir
   funcionando exactamente igual que hoy, con `TipoOrigenDocumento`/
   `IdOrigenDocumento` en `NULL` en la fila resultante.

## Verificación previa de esquema — 2026-09-29

Se consultó INFORMATION_SCHEMA.COLUMNS para ConciliacionesTesoreria, tablas de Tarjetas, Impuestos, Remuneraciones y Detalle Cobro Alquiler. Se confirmó CK_ConciliacionesTesoreria_Importe = Importe > 0; IdCobroAlquiler es la unidad de cuota; Remuneraciones tiene Fecha de pago y conceptos monetarios previstos. Sin escrituras.

## Evidencia de cierre — 2026-09-29 (sesión de continuación)

- **Migración aplicada**: backup de `WC` verificado, `scripts/extender_conciliaciones_tesoreria_documentos.py --apply` corrido contra producción. Esquema confirmado por lectura: `ConciliacionesTesoreria.TipoOrigenDocumento` (varchar(20), NULL) e `IdOrigenDocumento` (bigint, NULL) existen; tabla `ConciliacionesTesoreriaEstado` existe con las 9 columnas de data-model.md. `dbo.ConciliacionesTesoreria` tiene 7 filas (todas conciliaciones manuales previas de 023, `TipoOrigenDocumento IS NULL` — sin romper), `ConciliacionesTesoreriaEstado` en 0 filas (sin pollución de pruebas).
- **Regresión completa**: `pytest` backend 672/672 ✅ (incluye 79 tests propios de 026: contrato + repository). `tsc --noEmit` frontend limpio ✅.
- **Escenario 1 confirmado contra WC real**: `documentos.buscar("Primor")` devuelve la factura real de Primor Mayorista ($ 23.051,11, 2025-11-12, `idContacto: 611`).
- **SC-002 medido contra WC real**: 42 movimientos reales de Mercado Libre sin contacto reconocido (egresos) → 42/42 (100%) encuentran al menos una candidata por importe/fecha entre los 4 orígenes — supera el 90% requerido.
- **Frontend**: reconstruido (`npm run build`) y reiniciado; `ConciliacionDocumentos.tsx` integrado en `ConciliarMovimiento.tsx`, con el panel movido a diálogo (hallazgo de revisión visual: la tabla recortaba el panel en `MovimientosPorMedio.tsx`, corregido por Codex).
- **IDs heredados de Access negativos**: confirmado que existen y se admiten tal cual (el signo del ID no implica nota de crédito — solo el signo del importe lo hace).
