# Contract: API de Ventas de Hacienda y Ventas de Granos

Dos features nuevas, independientes entre sí (comparten solo `Contactos` y el patrón de infraestructura): `/api/ventas-hacienda` (extiende spec 005, hoy solo GET) y `/api/ventas-granos` (nueva desde cero). Todo `POST`/`PUT`/`DELETE` escribe exclusivamente contra `WC`.

## Ventas de Hacienda

### POST /api/ventas-hacienda — Crear una venta

**Request body** (`VentaHaciendaAltaRequest`):

```json
{
  "idConsignatario": 82,
  "idEstablecimiento": 3,
  "idTipoDocumento": 6,
  "numeroDocumento": "0001-00004567",
  "fecha": "2026-09-17",
  "porcComision": 4,
  "visMunicipal": 0,
  "balanza": 0,
  "gsVsNoGravados": 0,
  "alicuotaIVA": 10.5,
  "retencionGanancias": 0,
  "retencionIVA": 0,
  "ingresosBrutos": 0,
  "leyDeSellos": 0,
  "flete": 0,
  "gastosVarios": 0,
  "complemento": 0,
  "documentoOriginal": null,
  "lineas": [
    {
      "idComprador": 512,
      "idTipoProducto": 4,
      "cantidad": 25,
      "unidadMedida": "Cabezas",
      "pesoTotal": 6250,
      "precioUnitarioA": 1200,
      "precioUnitarioB": 0
    }
  ],
  "vencimientos": [
    { "fecha": "2026-10-15", "importe": 500000 }
  ]
}
```

**Validaciones** (400 si fallan): `idConsignatario` inexistente o de tipo no permitido (Comprador/Consignatario/Multiple); `idEstablecimiento` inexistente; lista `lineas` vacía; línea sin `idComprador`/`idTipoProducto`/`cantidad`/`precioUnitarioA`; `idComprador` de línea inexistente o de tipo no permitido (Comprador/Multiple); `idTipoProducto` inexistente en `Tipo Hacienda`.

**Response 201** (`VentaHaciendaDetalleResponse`): cabecera + `subTotal`/`subtotalB`/`comision`/`iva`/`importe`/`importeTotal` calculados (fórmula en data-model.md) + `lineas` + `vencimientos` + `warnings` (documento duplicado, no bloqueante — FR-009a).

### PUT /api/ventas-hacienda/{idVenta} — Editar (requiere `X-Lock-Token`)

Mismo body que el alta. Reemplaza cabecera+líneas+vencimientos por completo (mismo patrón que Compras). 404 si no existe; 409 si el lock pertenece a otro token.

### DELETE /api/ventas-hacienda/{idVenta} — Eliminar (requiere `X-Lock-Token`)

Borra cabecera+líneas+vencimientos+vínculos de documentos relacionados en una sola transacción. 404 si no existe; 409 si el lock pertenece a otro token. 204 en éxito.

### POST /api/ventas-hacienda/{idVenta}/lock — Adquirir/renovar lock

Body: `{ "lockToken": "<uuid>", "force": false }`. 200 con `expiresAt`; 409 si está tomado por otro token vigente y `force=false`.

### DELETE /api/ventas-hacienda/{idVenta}/lock — Liberar lock

Header `X-Lock-Token`. 204; 409 si pertenece a otro token.

### GET /api/ventas-hacienda/{idVenta}/relacionados, POST/DELETE .../relacionados/{idVentaRelacionada}

Mismo contrato que `compras/{id}/relacionados` (006), aplicado a ventas.

### GET /api/ventas-hacienda/documento-local?ruta=...

Mismo contrato que `compras/documento-local` (006) — sirve el PDF desde el disco local, `Content-Disposition: inline`.

## Ventas de Granos

### GET /api/ventas-granos — Listar (mismos filtros/paginación/orden que `/api/compras`)

Query params: `q`/`consignatario`, `numeroDocumento`, `fechaDesde`, `fechaHasta`, `campania`, `sortBy`/`sortDir`, `page`/`pageSize`. Sin filtro aplicado, `items: []` (mismo criterio "vacío por defecto" que Compras/Contactos — FR-010).

### GET /api/ventas-granos/{idVenta} — Detalle

Response incluye cabecera + `ajustes[]` + `deducciones[]` por separado (FR-011) + campos calculados (`precioKg`, `subTotal`, `iva`, `importeConIVA`, `totalRetenciones`, `totalDeducciones`, `importeNetoAPercibir`).

### POST /api/ventas-granos — Crear una venta

**Request body** (`VentaGranosAltaRequest`):

```json
{
  "idConsignatario": 219,
  "idTipoDocumento": 6,
  "numeroDocumento": "0002-00001122",
  "fecha": "2026-09-17",
  "precioUnitario": 285000,
  "tipoCambio": null,
  "gradoOperacion": "1",
  "idProducto": 1,
  "tipoDeGrano": "Soja",
  "campania": "2025/2026",
  "flete": 0,
  "nroDeposito": "12345",
  "gradoMercaderia": "1",
  "factor": 100,
  "contProteico": 0,
  "cantidadEntregada": 32000,
  "cantidadVendida": 32000,
  "alicuotaIVA": 10.5,
  "retencionIVA": 0,
  "retIG": 0,
  "percepciones": 0,
  "otraRetenciones": 0,
  "sellado": 0,
  "derechoRegistro": 0,
  "honorariosCamara": 0,
  "aCuentaCalidad": 0,
  "iibb": 0,
  "documentoOriginal": null,
  "ajustes": [
    { "concepto": "Bonificación por calidad", "importe": 5000, "alicuotaIVA": 10.5 }
  ],
  "deducciones": [
    { "idConcepto": 3, "detalle": "Comisión corretaje", "porc": 2, "baseCalculo": 9125000, "alicuota": 10.5 }
  ]
}
```

**Validaciones** (400 si fallan): `idConsignatario` inexistente; `idProducto` inexistente en `Granos`; `idTipoDocumento` inexistente; `cantidadEntregada`/`cantidadVendida`/`precioUnitario` requeridos; `idConcepto` de deducción inexistente en `Venta Granos_ConceptosDeducciones`.

**Response 201** (`VentaGranosDetalleResponse`): cabecera + campos calculados + `ajustes[]`/`deducciones[]` + `warnings` (documento duplicado, no bloqueante — FR-012a).

### PUT /api/ventas-granos/{idVenta} — Editar (requiere `X-Lock-Token`)

Mismo body que el alta. Reemplaza cabecera+ajustes+deducciones por completo.

### DELETE /api/ventas-granos/{idVenta} — Eliminar (requiere `X-Lock-Token`)

Borra cabecera+ajustes+deducciones+vínculos en una sola transacción. 204 en éxito.

### POST/DELETE /api/ventas-granos/{idVenta}/lock

Mismo contrato que Ventas de Hacienda.

## Transversal

- Todo endpoint `POST`/`PUT`/`DELETE` requiere que `main.py` tenga `PUT`/`DELETE` en `allow_methods` de CORS (ya corregido en 006 — verificar con `curl -X OPTIONS`, research.md §6, no reimplementar).
- `documentoOriginal` en ambos dominios reusa `esRutaLocalWindows`/`urlParaAbrirDocumento`/`normalizarDocumentoOriginal` de `frontend/src/lib/documentoLocal.ts` tal cual, sin duplicar lógica.
