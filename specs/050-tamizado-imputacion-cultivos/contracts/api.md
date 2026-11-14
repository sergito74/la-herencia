# API contract — 049 + 050

Todos los endpoints viven bajo `/api/imputacion`, requieren sesión (middleware 016) y nunca devuelven identificadores internos para mostrar. Los ids viajan solo como claves.

## Tamiz

### `POST /tamiz/compra/{idCompra}`
Tamiza los renglones de una compra. Se llama solo al guardar la compra; el endpoint se expone para reintentar.

**Respuesta**:
```json
{ "renglones": [ { "idDetalleCompra": 1, "etiqueta": "A cultivo", "parte": "Agroquímicos",
  "destinoTexto": "Va a stock · se imputa al usarse", "cultivo": null, "campania": null,
  "estado": "Aprobada", "motivo": null, "sugerido": true } ] }
```

`etiqueta` ∈ {`A cultivo`, `Va a stock`, `Gasto general`, `Ganadería`, `Financiero`, `No se imputa`}.

### `GET /tamiz/compra/{idCompra}`
Devuelve la misma forma, con la clasificación vigente. La usa la pantalla de edición de la compra.

### `PUT /tamiz/renglon/{idDetalleCompra}`
Corrige un renglón.

**Body**:
```json
{ "destino": "Cultivo", "idParte": 4, "idCultivo": 3, "idCampania": 12, "guardarRegla": false }
```

- Deja la clasificación aprobada y dispara el recálculo.
- Con `guardarRegla: true` crea una `TamizReglaProducto`.

## Revisión

### `GET /revisar?page=&pageSize=`
```json
{ "dudosos": [ { "tipo": "renglon|vinculoRemito|productoSugerido|reparto",
   "documento": "Factura 0001-00012345", "proveedor": "…", "fechaCarga": "2026-11-14",
   "texto": "…", "motivo": "Dos productos posibles", "opciones": [ … ] } ],
  "aprobadosPorDia": [ { "fecha": "2026-11-14", "items": [ … ] } ], "total": 0 }
```

### `POST /revisar/{tipo}/{id}/resolver`
Body: `{ "opcion": <índice o valor>, "guardarRegla": bool }`.

### `GET /revisar/contador`
Responde `{ "pendientes": 3 }`.

## Vínculo remito↔factura

### `POST /vinculos-remito/auto?idCompra=` o `?idRemito=`
Busca el par que corresponde y lo vincula si la coincidencia es única. Responde `{ "vinculados": n, "pendientes": m }`.

## Resultado

### `GET /api/resultado-cultivo/{idCultivo}/{idCampania}/por-parte`
```json
{ "superficieHa": 0, "partes": [ { "parte": "Agroquímicos", "pesos": 0, "dolares": 0,
  "pesosHa": 0, "dolaresHa": 0, "documentos": [ … ] } ],
  "estructuraCampania": { "pesos": 0, "dolares": 0 }, "enStockSinConsumir": { "pesos": 0, "dolares": 0 } }
```

## Listado para el Estudio

### `POST /listado-estudio/generar`
Genera el Excel en la carpeta Compras de Dropbox y lo reemplaza.

- **Responde**: `{ "filas": n, "archivo": "Listado General Compras - Imputacion (1-9-2015 en adelante).xlsx" }`.
- **Error 409**: el archivo está abierto. Responde `{ "error": "El listado está abierto en Excel; cerralo y volvé a generarlo." }`.

## Activación e impacto (uso interno, lo corre Claude)

- `scripts/activar_alcance_050.py --dry-run`: genera el Excel antes/después por cultivo/campaña sin escribir nada.
- `scripts/activar_alcance_050.py --aplicar`: fija el corte y marca los renglones `StockSinImputar`. Requiere backup verificado y el OK de Sergio sobre el informe.
