# Contract: API de alta/edición de Compras

Extiende `/api/compras` (spec 002, hoy solo GET) con endpoints de escritura, exclusivamente contra `WC`. Ninguno de los endpoints GET existentes de 002-compras cambia.

## POST /api/compras — Crear una compra

**Request body** (`CompraAltaRequest`):

```json
{
  "idContacto": 461,
  "fecha": "2026-09-17",
  "tipo": "A",
  "tipoDocumento": "Factura",
  "numeroDocumento": "0001-00012345",
  "moneda": "Pesos",
  "tipoDeCambio": null,
  "ingresosBrutos": 0,
  "conceptosNoGravados": 0,
  "guias": 0,
  "comision": 0,
  "financiacion": 0,
  "gastosVarios": 0,
  "leyDeSellos": 0,
  "resGral4169": 0,
  "ajustaTipoCambio": false,
  "documentoOriginal": null,
  "lineas": [
    {
      "productoServicio": "Fertilizante Urea",
      "cantidad": 10,
      "precioUnitario": 55000,
      "iva": 21,
      "unidad": "TN",
      "idCentroCosto": 3,
      "idDestino": 1,
      "idRubro": 12,
      "campaña": "2026/27",
      "ajusteFinanciero": false
    }
  ],
  "vencimientos": [
    { "fechaVencimiento": "2026-10-15" }
  ]
}
```

**Validaciones** (400 si fallan, ver data-model.md "Reglas de validación cruzada"): `idContacto` inexistente o de tipo no permitido; `moneda = "Dolares"` sin `tipoDeCambio`; lista `lineas` vacía; línea sin `productoServicio`/`cantidad`/`precioUnitario`/`iva`; `idRubro`/`idCentroCosto`/`idDestino` inexistente en su catálogo si se especifica.

**Response 201** (`CompraDetalleResponse`):

```json
{
  "idCompra": 6437,
  "...": "todos los campos de cabecera",
  "subtotalNeto": 550000,
  "ivaCabecera": 115500,
  "importeTotal": 665500,
  "pesificado": null,
  "lineas": [ { "idDetalleCompra": 20481, "subtotal": 550000, "importeIva": 115500, "...": "..." } ],
  "vencimientos": [ { "idVencimiento": 9001, "fechaVencimiento": "2026-10-15" } ],
  "warnings": []
}
```

Si `numeroDocumento` ya existe para el mismo `idContacto` (FR-014): `"warnings": ["Ya existe una compra con este número de documento para este proveedor."]`, igual código 201 (no bloquea).

## PUT /api/compras/{idCompra} — Editar una compra existente

Mismo body que `POST`, reemplaza cabecera completa y el conjunto de líneas/vencimientos (reemplazo total, no parches parciales — el frontend siempre manda el estado completo del formulario). Requiere header `X-Lock-Token` con el token del lock vigente.

**Responses**:
- `200`: igual forma que la respuesta de `POST`.
- `404`: `idCompra` no existe.
- `409`: no hay lock vigente para esa compra a nombre de ese `X-Lock-Token` (alguien más la tiene en edición, o el token no adquirió el lock).

## POST /api/compras/{idCompra}/lock — Adquirir o renovar el bloqueo de edición

**Request body**: `{ "lockToken": "3fa85f64-5717-4562-b3fc-2c963f66afa6" }`

**Responses**:
- `200` (`LockResponse`): `{ "idCompra": 6437, "lockToken": "...", "expiresAt": "2026-09-17T15:45:00" }` — lock adquirido o renovado (mismo token que ya lo tenía, o no había lock vigente).
- `409`: `{ "detail": "La compra está siendo editada." }` — hay un lock vigente de otro token.

## DELETE /api/compras/{idCompra}/lock — Liberar el bloqueo

**Request**: header `X-Lock-Token`.

**Responses**:
- `204`: liberado (o no existía ningún lock vigente).
- `409`: existe un lock vigente pero de otro token (no se puede liberar el lock de otra sesión).

## GET /api/compras/rubro-sugerido — Sugerencia de rubro por texto

**Query params**: `productoServicio` (string, requerido).

**Response 200**: `{ "idRubro": 12, "rubro": "Fertilizantes", "frecuencia": 7 }` o `{ "idRubro": null, "rubro": null, "frecuencia": 0 }` si no hay coincidencias previas exactas.

## Endpoints de catálogo reutilizados (ya existentes, sin cambios)

- `GET /api/compras/filtros` (002-compras) ya expone `centrosCosto`/`rubros` — se reutiliza tal cual para poblar los combos de línea.
- `GET /api/contactos` (`ContactoSelect`) para el combo de proveedor, filtrando por los 5 tipos permitidos (FR-001) desde el frontend, no un parámetro nuevo del backend.
- Catálogos sin endpoint propio todavía (`DestinoCompras`, `UnidadesMedida`, `Campañas`) se agregan a la respuesta de `GET /api/compras/filtros` en esta feature (amplía el contrato existente de forma aditiva, no rompe a los consumidores actuales de 002-compras).
