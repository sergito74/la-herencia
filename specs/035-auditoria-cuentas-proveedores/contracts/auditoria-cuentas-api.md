# Contrato de API: auditoría de cuentas corrientes

Prefijo `/api/auditoria-cuentas`. Lectura para cualquier usuario autenticado; escritura (`POST`, `DELETE`, `PUT`) solo para roles distintos de `Lectura`. Importes en la moneda de la cuenta; fechas `YYYY-MM-DD`.

## 1. Resumen por causa

`GET /api/auditoria-cuentas/resumen?fechaCorte=`

```json
{
  "fechaCorte": "2026-09-25",
  "parametros": { "plazoMaximoMeses": 24, "umbralPesos": 300, "anticipoDias": 60 },
  "totalCuentas": 513,
  "coinciden": 436,
  "conDiferencia": 77,
  "causas": [
    { "causa": "aplicacion-fuera-de-plazo", "cuentas": 40, "importe": 38887994.46, "excepcion": true },
    { "causa": "coincide-causa-conocida", "cuentas": 163, "importe": 0, "excepcion": false }
  ],
  "avisoCorte": "Los movimientos posteriores al 25/09/2026 no se comparan."
}
```

`fechaCorte` es opcional y por defecto toma la de la referencia. `excepcion: false` indica los grupos que no cuentan como excepción (coincide, coincide con causa conocida, diferencia menor al umbral).

## 2. Cuentas de un grupo

`GET /api/auditoria-cuentas/grupos/{causa}?pagina=&tamano=`

```json
{
  "causa": "aplicacion-fuera-de-plazo",
  "items": [
    { "idContacto": 258, "razonSocial": "Cargill", "moneda": "Pesos", "saldoSistema": -123.45,
      "saldoAccess": -123.45, "diferencia": 0.0, "sinExplicar": 0.0, "hallazgos": 1 }
  ],
  "total": 40
}
```

## 3. Hallazgos de una cuenta

`GET /api/auditoria-cuentas/cuentas/{idContacto}/hallazgos`

```json
{
  "idContacto": 258,
  "hallazgos": [
    { "causa": "aplicacion-fuera-de-plazo", "medio": "galicia", "idMovimiento": 3240, "fechaPago": "2026-05-28",
      "importeAplicado": 7868575.41, "cantidadFacturas": 90, "facturaMasVieja": "2019-05-07",
      "diasMaximos": 2578, "origenAplicacion": "automatica-exacta",
      "motivo": "El pago se aplicó a facturas de hace más de 24 meses" }
  ]
}
```

## 4. Parámetros

`GET /api/auditoria-cuentas/parametros` → `{ "plazoMaximoMeses": 24, "umbralPesos": 300, "anticipoDias": 60 }`

`PUT /api/auditoria-cuentas/parametros` con `{ "plazoMaximoMeses": 18 }` → `200` con los valores nuevos; `422` si el valor no es un entero positivo. Cada corrida del control informa con qué valores se calculó.

## 5. Exportar

`GET /api/auditoria-cuentas/exportar?causa=` devuelve el `.xlsx` con las mismas cuentas e importes que la pantalla, más la fecha de corte y los parámetros usados. Sin `causa` incluye todas las excepciones.

## 6. Correcciones por regla

`GET /api/auditoria-cuentas/reglas` → reglas disponibles: `[{ "regla": "anular-doble-descuento-tarjeta", "causa": "doble-descuento-tarjeta", "descripcion": "..." }]`.

`POST /api/auditoria-cuentas/correcciones/simular` con `{ "regla": "anular-doble-descuento-tarjeta" }` → `201`:

```json
{
  "idCorreccion": 4, "estado": "simulada", "regla": "anular-doble-descuento-tarjeta",
  "cuentas": [
    { "idContacto": 17, "razonSocial": "Cooperativa Agropecuaria", "aplicaciones": 6, "importe": 454000.0,
      "saldoAntes": -454000.0, "saldoDespues": -454000.0, "tildada": false, "detalle": "Anula 6 aplicaciones sobre BNA 14417 y 14418" }
  ]
}
```

Ninguna cuenta viene tildada. `422` si la regla no existe.

`PUT /api/auditoria-cuentas/correcciones/{idCorreccion}/cuentas` con `{ "tildadas": [17] }` → `200` (marca las cuentas que se aplican; solo en estado `simulada`).

`POST /api/auditoria-cuentas/correcciones/{idCorreccion}/aplicar` → `200` con el respaldo, las cuentas aplicadas y el saldo antes y después. `409` si no está simulada, no tiene cuentas tildadas o el saldo de una cuenta cambió desde la simulación (hay que volver a simular); `403` para el rol `Lectura`.

`POST /api/auditoria-cuentas/correcciones/{idCorreccion}/revertir` → `200`; `409` si no estaba aplicada.

`DELETE /api/auditoria-cuentas/correcciones/{idCorreccion}` → `204` (descarta una simulación); `409` si ya fue aplicada.

`GET /api/auditoria-cuentas/correcciones` → historial con regla, estado, usuario, fechas y resumen.

## 7. FIFO completo

Se opera con el contrato ya vigente de `/api/recalculo-fifo/ejecuciones` (crear la simulación con el alcance, listar contactos, aplicar, revertir). La auditoría agrega solo la lectura:

`GET /api/auditoria-cuentas/fifo/estado` → `{ "contactosAplicados": 7, "contactosPendientes": 478, "cuentasARevisar": [{ "idContacto": 374, "motivo": "..." }], "ultimaSimulacion": { "idEjecucion": 33, "cierranDespues": 435, "empeoran": 0 } }`.

## 8. Referencias entre pantallas

Cada hallazgo trae `medio` e `idMovimiento` para abrir el movimiento en Tesorería (`/finanzas/tesoreria?medio=&highlight=`) y cada cuenta enlaza a su cuenta corriente.

## 9. Lo ya conocido (reglas)

`GET /api/auditoria-cuentas/conocidos` → reglas activas `[{ "idConocido", "tipo", "clave", "importeRef", "motivo", "usuario", "activo" }]`.

`POST /api/auditoria-cuentas/conocidos` (rol de escritura) con `{ "tipo": "concepto-movimiento", "clave": "INTERESES", "motivo": "Intereses del banco" }` o `{ "tipo": "cuenta", "clave": "315", "motivo": "...", "importeRef": -605332.07 }` → `201`; `422` (tipo desconocido, clave de menos de 4 caracteres, sin motivo, cuenta sin diferencia), `409` (ya existe).

`DELETE /api/auditoria-cuentas/conocidos/{id}` → `204` (baja lógica con usuario y fecha); `404`, `409`.

`GET /api/auditoria-cuentas/grupos/movimiento-sin-contacto` → `{ "total", "conceptos": [{ "concepto", "movimientos", "importe", "neto", "ejemplos": [...] }], "explicados": [{ "clave", "movimientos", "importe" }] }`: movimientos del banco sin contacto, de cualquier monto, que no están conciliados ni cruzados; los explicados por una regla se cuentan aparte y el resto se agrupa por concepto.
