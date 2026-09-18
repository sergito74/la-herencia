# Contract: API de Tarjetas de Crédito

Cuatro subdominios bajo `/api/tarjetas`, `/api/tarjetas-resumenes`, `/api/tarjetas-cuotas`. Todo `POST`/`PUT`/`DELETE` escribe exclusivamente contra `WC`.

## Catálogo de tarjetas (Historia 4, solo lectura)

### GET /api/tarjetas — Listado

Sin filtros ni paginación (5 filas reales). Response: `[{ idTarjeta, nombre, banco, activa }]`. Usado como fuente de los combos de resumen (con `activa=true` filtrado del lado del cliente o vía `?soloActivas=true`).

## Cuenta corriente de tarjeta (Historia 2)

### GET /api/tarjetas/{idTarjeta}/movimientos — Movimientos con saldo acumulado

Un movimiento por resumen de la tarjeta (data-model.md, sección "Movimiento de Cuenta Corriente de Tarjeta"), ordenados por `fechaCierre`. Response:

```json
{
  "idTarjeta": 3,
  "tarjeta": "Visa Galicia",
  "movimientos": [
    {
      "idResumen": 187,
      "fecha": "2026-06-10",
      "codigo": "0532-000123456",
      "deuda": 45230.50,
      "credito": 0,
      "saldoAcumulado": 45230.50
    }
  ]
}
```

`idResumen` es el `idOrigen` para la navegación de FR-003: cada fila linkea directo a `GET /api/tarjetas-resumenes/{idResumen}` / `/finanzas/tarjetas/resumenes/{idResumen}`.

## Resúmenes de tarjeta (Historia 1)

### GET /api/tarjetas-resumenes — Búsqueda

Sin resultados hasta aplicar al menos un filtro (FR-010, mismo criterio que Compras/Ventas/Contactos). Filtros: `idTarjeta`, `fechaCierreDesde`/`fechaCierreHasta`, `fechaVencimientoDesde`/`fechaVencimientoHasta`. Response paginado: `{ items: [{ idResumen, tarjeta, codigo, fechaCierre, fechaVencimiento, totalCalculado, soloCabecera }], page, pageSize, total }`. `soloCabecera` es un campo derivado (ausencia de líneas), no la columna real `SoloCabecera` (siempre NULL en datos reales — ver data-model.md).

### GET /api/tarjetas-resumenes/{idResumen} — Detalle

Cabecera completa (los 14 cargos/impuestos de FR-008) + `totalCalculado` (fórmula en data-model.md) + `lineas: []` (vacío si es "solo cabecera", sin error).

### POST /api/tarjetas-resumenes — Crear un resumen

**Request body** (`ResumenAltaRequest`):

```json
{
  "idTarjeta": 3,
  "codigo": "0532-000123457",
  "fechaCierre": "2026-07-10",
  "fechaVencimiento": "2026-07-20",
  "impuestoSellos": 120.50,
  "gastosAdmin": 0,
  "mantCuenta": 0,
  "renovAnual": 0,
  "promocionBNA": 0,
  "creditoContingente": 0,
  "intFinanc": 0,
  "intCompens": 0,
  "iva105": 0,
  "percepIVA105": 0,
  "iva21": 350.20,
  "percepIVA21": 0,
  "percepIIBB": 0,
  "ajusteResAnterior": 0,
  "lineas": [
    { "fechaCompra": "2026-06-15", "detalle": "SUPERMERCADO XYZ", "importe": 15230.00, "fechaVencimientoCompra": null, "idContacto": null, "nroDocumento": null }
  ]
}
```

`lineas: []` es válido (FR-009, "solo cabecera" — 24% de los resúmenes reales son así). **Validaciones** (400 si fallan): `idTarjeta` inexistente; `codigo`/`fechaCierre`/`fechaVencimiento` faltantes.

**Response 201** (`ResumenDetalleResponse`): cabecera + `totalCalculado` + `lineas` + `warnings` (mismo código+tarjeta ya existente — FR-012, no bloqueante, mismo criterio que FR-009a/012a de 007).

### PUT /api/tarjetas-resumenes/{idResumen} — Editar (requiere `X-Lock-Token`)

Mismo body que el alta. Reemplaza cabecera+líneas por completo. 404 si no existe; 409 si el lock pertenece a otro token.

### DELETE /api/tarjetas-resumenes/{idResumen} — Eliminar (requiere `X-Lock-Token`)

Borra cabecera+líneas en una transacción. 404/409 igual que arriba. 204 en éxito.

### POST /api/tarjetas-resumenes/{idResumen}/lock — Adquirir/renovar lock

Mismo contrato que `compras/{id}/lock` (006): `{ lockToken, force? }` → 200 `{ idResumen, lockToken, expiresAt }` / 409 si está tomado por otro token sin `force`.

## Compras en cuotas (Historia 3)

### GET /api/tarjetas-cuotas — Búsqueda de compras en cuotas

Filtros: `idContacto`, `fechaDesde`/`fechaHasta` (sin filtro por tarjeta — FR-006, la compra en cuotas no está vinculada a una tarjeta del catálogo, ver data-model.md). Response paginado: `{ items: [{ idPagoTarjeta, contacto, fecha, nroComprobante, cantidadCuotas, cuotasCobradas, cuotasPendientes }], page, pageSize, total }`.

### GET /api/tarjetas-cuotas/{idPagoTarjeta} — Detalle con cronograma

`{ idPagoTarjeta, contacto, fecha, nroComprobante, cantidadCuotas, importeTotal, cuotas: [{ idCuota, numeroCuota, fechaVencimiento, importe, cobrado }] }`. `importeTotal` es `Σ(cuotas.importe)`.

### POST /api/tarjetas-cuotas — Crear una compra en cuotas

**Request body** (`CompraCuotasAltaRequest`):

```json
{
  "idContacto": 245,
  "fecha": "2026-09-18",
  "nroComprobante": 8834,
  "importeTotal": 60000,
  "cantidadCuotas": 6
}
```

Al guardar, genera automáticamente 6 filas en `Cuotas Tarjetas de Credito` con la fórmula de data-model.md (cuota fija, ajuste de redondeo en la última, vencimiento mensual sucesivo desde `fecha`). **Validaciones** (400 si fallan): `idContacto` inexistente; `cantidadCuotas` < 1; `importeTotal` sin definir.

**Response 201**: mismo shape que el detalle, con `cuotas` ya generadas.

### PUT /api/tarjetas-cuotas/{idPagoTarjeta} — Editar (requiere `X-Lock-Token`)

Mismo body que el alta — regenera el cronograma completo (reemplaza todas las cuotas, pierde el estado `cobrado` de las cuotas anteriores si cambia `importeTotal`/`cantidadCuotas`; si solo se edita `fecha`/`nroComprobante`/`idContacto` sin tocar `importeTotal`/`cantidadCuotas`, el cronograma no se regenera — a definir en implementación con un test de contrato explícito para ambos casos).

### DELETE /api/tarjetas-cuotas/{idPagoTarjeta} — Eliminar (requiere `X-Lock-Token`)

Borra cabecera+cuotas en una transacción. 204 en éxito.

### PATCH /api/tarjetas-cuotas/{idPagoTarjeta}/cuotas/{idCuota} — Marcar cobrada/no cobrada

**Request body**: `{ "cobrado": true }`. No requiere lock (cambio de un solo campo, bajo riesgo de colisión, mismo criterio que otros toggles puntuales del sistema). Response 200 con la cuota actualizada.

### POST /api/tarjetas-cuotas/{idPagoTarjeta}/lock — Adquirir/renovar lock

Mismo contrato que el de resúmenes, sobre `TarjetaCuotasEditLocks`.

## Transversal

- Todos los `POST`/`PUT`/`DELETE` pasan por `execute_write`/`execute_write_transaction` (`backend/src/db/connection.py`, sin cambios) — `_assert_target_is_wc()` bloquea cualquier escritura si `LA_HERENCIA_DATABASE` no es `WC` (FR-015).
- CORS ya acepta `PUT`/`DELETE`/`PATCH` (confirmado en 006/007, `research.md` de esta feature no necesita repetir la verificación salvo que se agregue un método nuevo — `PATCH` ya estaba habilitado, confirmar en quickstart igual que los otros métodos).
- Advertencias no bloqueantes (`warnings: string[]`) siguen el mismo criterio que FR-009a/FR-012a de 007: nunca `400`, siempre `201`/`200` con el arreglo poblado.
