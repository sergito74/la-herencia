# Quickstart / validación: 048

## Prerrequisitos

- Backup verificado de `OrdenesContratistaFacturas` y `ImputacionPropuestas` antes de correr `backend/scripts/vinculos_contratista_048.py`.
- Foto previa: saldos de todas las cuentas corrientes (`get_saldos_todos`, sin caché) y Resultado por cultivo de las campañas 24/25, 25/26 y 26/27, guardados en el scratchpad.
- Sistema reiniciado con `LaHerencia.ps1 -Reiniciar -NoBrowser`.

## Escenarios

1. **Orden 162 (Pérez, 25/10/2026, 198 ha)**: abrir la orden. La factura 00002-00000735 aparece sugerida con el rótulo "coincide". Tildarla y guardar. Esperado: el reparto se muestra por lote/cultivo/campaña y suma el neto al centavo.
2. **Resultado**: en el cultivo/campaña de la orden 162, el costo de contratista viene de la orden (con enlace a la compra). La factura no aparece además como costo heredado.
3. **Destildar** la factura en la orden 162: el costo vuelve a la carga manual (el total previo se restituye).
4. **Revisión de Yanquelen**: no aparece "Vacas preñadas" ni facturas solo de semilla o urea. En una factura mixta (00002-00000025), el neto repartible excluye los renglones de semilla.
5. **Descartar como "sin orden"** una factura histórica: pasa al detalle "sin orden" y su costo sigue por la carga manual. Reabrirla la devuelve a "sin revisar".
6. **Factura nueva sin orden** (con fecha posterior a la puesta en marcha): aparece como pendiente en la revisión y en el listado de la rutina 043.
7. **Usuario de solo lectura**: ve la lista y las propuestas, sin los botones; el PUT responde 403.
8. **Controles finales**: saldos de cuentas iguales al centavo que en la foto previa (SC-005); total de costo de contratista por campaña igual que antes, salvo los repartos entre cultivos, que se listan (SC-004).

## Tests automáticos

`cd backend && python -m pytest tests/ordenes tests/imputacion tests/resultado_cultivo -q`, más `npm run lint` y `npx tsc --noEmit` en `frontend`.
