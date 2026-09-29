# API Contract: Vincular líneas de resumen de tarjeta a pagos de Impuestos

Extiende los endpoints ya existentes de `008-tarjetas`/`009-conciliacion-tarjetas`
bajo `/api/tarjetas-resumenes` — ningún endpoint nuevo, se amplía la forma
de los ya existentes (research.md §5).

## `DocumentoCandidato` (forma extendida)

Usado por `GET /documentos-buscar`, `GET /lineas/{id}/documentos-candidatos`
y en la respuesta de `POST .../compras` \| `.../compras/lote`.

```json
{
  "origen": "Impuestos",
  "idCompra": null,
  "idImpuesto": 48213,
  "fecha": "2026-08-10",
  "tipoDocumento": "AFIP",
  "numeroDocumento": "0001-00012345",
  "moneda": null,
  "tipoDeCambio": null,
  "importeOriginal": 45000.0,
  "importePesos": 45000.0,
  "proveedor": "AFIP",
  "saldoPendiente": 15000.0,
  "vinculosPrevios": 1,
  "compraParticular": 0,
  "ajustaTipoCambio": false
}
```

Cambios respecto del contrato actual (data-model.md):
- `origen`: `"Compras"` \| `"Impuestos"` (nuevo, siempre presente).
- `idCompra`: pasa a **opcional** (`null` cuando `origen == "Impuestos"`).
- `idImpuesto`: **nuevo**, opcional (`null` cuando `origen == "Compras"`).
- `saldoPendiente`: **nuevo**, opcional — solo poblado para `Impuestos`
  (Compras no tiene este control, research.md §2).
- El resto de los campos (incluido `proveedor`, que para Impuestos trae el
  nombre del organismo) no cambia de forma, solo de contenido.

## `GET /api/tarjetas-resumenes/documentos-buscar?q=...`

Sin cambio de firma — la búsqueda por texto ahora también encuentra pagos
de Impuestos con organismo asignado (FR-001/FR-006), devueltos con el
`DocumentoCandidato` extendido.

## `POST /api/tarjetas-resumenes/lineas/{idLineaConsumo}/compras/lote`, `GET .../conciliacion` (preview) y `GET .../candidatos`

**Decisión de contrato (revisada durante `/speckit-tasks`, menor riesgo que
un rename)**: en vez de reemplazar `idCompra`/`idsCompra` por un campo
`origen`+`idOrigen`, se agrega un campo **paralelo** `idsImpuesto` en cada
uno de estos tres endpoints, con la misma forma que ya tiene `idsCompra`
(`list[int]`). El camino 100% Compras (`idsImpuesto` vacío u omitido)
queda byte-a-byte igual que hoy — FR-007 (no regresión) se cumple por
construcción, no por testeo posterior. Los IDs de ambas listas se
combinan del lado del servidor antes de armar los `docs` que ya recibe
`conciliacion_documentos.calcular_imputacion`/`sugerir` (sin cambios en
ese módulo, research.md §3).

```json
{ "idsCompra": [4821], "idsImpuesto": [48213], "aceptarDiferencia": null }
```

`POST .../compras` (vínculo de un único documento, sin lote) se extiende
igual: agrega un campo opcional `idImpuesto: int | null` junto al ya
existente `idCompra: int | null` (ambos opcionales, exactamente uno
presente — mismo `CHECK` que en la tabla).

**Errores nuevos**:

| Status | Motivo |
|---|---|
| 400 | ninguno de los dos ids presente, o los dos presentes a la vez, en un vínculo de un único documento |
| 404 | un `idImpuesto` no existe, o no tiene `IdOrganismo` asignado (FR-006) |
| 409 | la suma imputada a un `idImpuesto` (en este lote + lo ya vinculado en otras líneas) excede su importe real — recalculado en el momento de escribir (mismo criterio de concurrencia ya usado en 023) |

## `GET .../candidatos` (auto-sugerencia por contacto de la línea)

**Fuera de alcance**: sigue devolviendo solo Compras del proveedor de la
línea, sin cambios — la spec (US1) solo exige que la **búsqueda manual**
(`documentos-buscar`) encuentre Impuestos; la auto-sugerencia por contacto
no aplica de la misma forma porque una línea de tarjeta no tiene un
organismo "propio" precargado como sí tiene un proveedor.

## `DELETE /api/tarjetas-resumenes/lineas/{idLineaConsumo}/compras/{idVinculo}`

Sin cambios de firma — desvincula cualquier vínculo (Compras o Impuestos)
por su `IdVinculo`, dejando el pago de Impuestos disponible de nuevo con
su saldo pendiente recalculado (FR-008).
