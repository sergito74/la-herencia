# Contrato API: /api/ganaderia (etapa 1)

Todas las respuestas usan camelCase. Los importes son números con 2 decimales; la moneda va explícita en la respuesta. Las escrituras exigen el rol admin.

## GET /api/ganaderia/resultado
**Parámetros:**

| Parámetro | Valores | Default |
|---|---|---|
| `vista` | `ejercicio` \| `campania` | `ejercicio` |
| `moneda` | `ARS` \| `USD` | `USD` |
| `desde`, `hasta` | etiquetas de ejercicio ("2025/26") o de campaña | — |
| `establecimiento` | id | todos |

**Respuesta:**
```json
{ "vista": "ejercicio", "moneda": "USD", "conversion": "TC del comprobante",
  "periodos": [{"clave": "2025/26", "desde": "2025-04-01", "hasta": "2026-03-31", "sinInventario": true}],
  "filas": [{"rubro": "Terneros", "grupo": "Ventas", "valores": {"2025/26": 12345.67}, "abreDetalle": true}],
  "indicadores": {"2025/26": {"haGanaderas": 230.4, "margenBruto": 0, "mbHa": 0, "ev": 0, "evHa": 0, "kgVendidos": 0}},
  "avisos": [{"periodo": "2025/26", "texto": "Falta el stock al cierre"}] }
```
- **Grupos (orden de la planilla):** Ventas (por categoría, con A/B/total), Comercialización, Pastaje, Directos, Sanidad, Alimentación (incluye forrajes y amortización de pasturas), Margen bruto.
- **Sin dato:** cuando no hay datos el valor es `null` y la UI muestra "—".

## GET /api/ganaderia/resultado/detalle
**Parámetros:** `rubro`, `periodo`, `vista`, `moneda`.

**Respuesta:** `[{fecha, documento, contacto, idContacto, concepto, fraccion, importe, enlace}]`. El campo `enlace` lleva a `/compras/{id}/editar`, `/ventas/hacienda/{id}` o la orden.

## GET /api/ganaderia/superficie?periodo=
Respuesta: `[{lote, superficie, mesesGanaderos, haEfectivas, origen: "plan"|"orden"|"calendario"|"ajuste"}]` y el total.

## GET /api/ganaderia/stock?fecha=&establecimiento=&dueno=propia|terceros|todos
Respuesta: `{fecha, base: {fecha, origen}, categorias: [{categoria, cabezas, kg, dueno, establecimiento}], sinExplicar: [{categoria, diferencia}]}`

## GET /api/ganaderia/movimientos?desde=&hasta=&tipo=&categoria=&establecimiento=
**Respuesta:** filas paginadas (máx. 500) con fecha, tipo, categoría, cabezas, kg, kgEstimado, dueño, establecimiento, fuente y enlace.

## POST /api/ganaderia/movimientos (admin)
**Body:** `{fecha, tipo, categoria, categoriaDestino?, cabezas, kg?, dueno?, establecimiento, causa?, motivo?}`

| Respuesta | Cuándo |
|---|---|
| 201 | movimiento guardado |
| 409 | la existencia quedaría negativa y no viene `confirmar: true` |
| 422 | `AjusteRecuento` sin motivo |

Las ventas no se cargan por acá: el movimiento de una venta lo crea Ventas de hacienda.

## POST /api/ganaderia/movimientos/{id}/anular (admin)
**Body:** `{motivo}`. Los movimientos de venta no se anulan acá: se corrigen editando la venta.

## GET /api/ganaderia/recuentos · POST /api/ganaderia/recuentos (admin)
- **Body:** `{fecha, establecimiento, origen, detalle: [{categoria, dueno?, cabezas, kgPromedio?}]}`
- **Respuesta:** la diferencia contra la existencia teórica.

## GET /api/ganaderia/controles · POST /api/ganaderia/controles/correr
- **Respuesta:** `{corrido, grupos: [{grupo, items: [{tipo, clave, texto, enlace}]}], aceptados: [...]}`
- **Grupos:** Ventas, Consignatarios, Stock, Pastaje, Imputación.

## POST /api/ganaderia/controles/aceptar (admin) · POST /api/ganaderia/controles/aceptados/{id}/quitar (admin)
Body de aceptar: `{tipo, clave, motivo}`.

## GET|PUT /api/ganaderia/configuracion/{categorias|alias|rubros|forrajes|calendario|superficie}
Hacen CRUD acotado. El PUT exige admin.

## Cambios en contratos existentes
- `GET /api/flujo-caja/por-rubro`: agrega el parámetro opcional `centroCosto`.
- `GET /api/resultado-cultivo/*`: deja de devolver los cultivos con `EsGanaderia=1`.
