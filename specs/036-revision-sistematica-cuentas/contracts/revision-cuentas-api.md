# Contrato: API de revisión sistemática de cuentas (036)

Base: `/api/revision-cuentas`. JSON, textos en español simple. Modelo de datos en [../data-model.md](../data-model.md). Las lecturas no escriben. Todo cambio exige el rol con permiso de escritura (el rol `Lectura` recibe 403), registra quién, cuándo y por qué, y nunca borra filas. Los importes son en la moneda que gobierna la cuenta; el signo es crédito menos deuda (positivo = a favor nuestro). Los endpoints de la 035 (`/api/auditoria-cuentas`) no cambian de contrato, salvo la puerta del FIFO (ver al final).

## Códigos de error comunes

| Código | Cuándo |
|---|---|
| 403 | el rol no puede cambiar datos |
| 404 | la cuenta, el movimiento o la fila no existe |
| 409 | la acción no corresponde al estado actual (etapa previa sin cumplir, lote ya aplicado, el saldo cambió desde la simulación) |
| 422 | dato inválido o falta un campo obligatorio (por ejemplo el motivo de una excepción) |

## Corte

### `GET /corte`
Corte vigente: `{ "corte": "2026-09-30", "motivo": "...", "usuario": "...", "fecha": "..." }`.

### `PUT /corte`
`{ "corte": "2026-10-31", "motivo": "..." }`. Crea una fila nueva (no sobrescribe). 422 si la fecha es futura. Cambiar el corte recalcula las reaperturas (las cuentas cerradas al corte anterior no se reabren por eso: conservan su corte).

## Tablero

### `GET /tablero`
Estado actual calculado en vivo. Parámetros: `corte` (opcional, por defecto el vigente).
```json
{
  "corte": "2026-09-30",
  "totalCuentas": 518,
  "porEstado": { "pendiente": 0, "en-proceso": 0, "esperando-evidencia": 0, "esperando-sergio": 0,
                 "cerrada": 0, "cerrada-con-excepcion": 0, "reabierta": 0 },
  "casillas": [ { "cola": "D", "etapa": "E1", "cuentas": 12, "importe": 38000000.00 } ],
  "totalesPorCola": { "A": { "cuentas": 0, "importe": 0 } },
  "comparacion": { "semanaAnterior": "2026-10-05", "cerradasEnLaSemana": 0, "variacionExcepciones": 0 },
  "preguntas": 0
}
```
La suma de `casillas[].cuentas` es igual a `totalCuentas` (cada cuenta cae en una sola casilla). `comparacion` es `null` si no hay foto anterior.

### `GET /tablero/fotos`
Lista de fotos semanales (`semana`, `corte`, `fecha`, totales). Paginado.

### `POST /tablero/fotos`
Crea la foto de la semana actual si no existe (409 si ya existe; el tablero la crea solo al abrirse, ver D13). 201.

### `GET /preguntas`
Preguntas que bloquean cuentas, una por cuenta: `[ { "idContacto", "razonSocial", "cola", "etapa", "pregunta", "desde" } ]`, ordenadas con el mismo criterio de las colas.

## Colas y lotes

### `GET /colas/{cola}`
`cola` es `A` a `I`. Cuentas de la cola ordenadas de las más fáciles a las más complejas: menos movimientos primero y, a igual cantidad, menor importe (D6). Parámetros: `pagina`, `tamano` (máximo 100).
```json
{ "cola": "A", "total": 0, "pagina": 1,
  "cuentas": [ { "idContacto": 48, "razonSocial": "...", "movimientos": 603, "importe": 0.0,
                 "saldo": -3.31, "moneda": "Pesos", "etapa": "E6", "estado": "pendiente",
                 "otrosProblemas": [ "plazo" ] } ] }
```

### `GET /reglas`
Reglas de lote disponibles: `[ { "regla": "aprobar-cierre", "cola": "A", "descripcion": "..." } ]`. Primer corte: `aprobar-cierre` (A), `fifo-tandas` (B), `anular-doble-descuento` (C).

### `POST /lotes/simular`
`{ "cola": "C", "regla": "anular-doble-descuento" }`. Crea una corrección registrada en estado `simulada` (tabla `AuditoriaCorrecciones`) con una fila por cuenta (`Tildada = 0`, saldo antes y después, detalle). No cambia nada. 201 con `idCorreccion`. 422 si la regla no corresponde a la cola.

### `PUT /lotes/{idCorreccion}/cuentas`
`{ "idsContacto": [ ... ] }` o `{ "tildarTodas": true }`. Con `idsContacto` tilda exactamente esas cuentas; con `tildarTodas` tilda todas las cuentas del lote que cumplen la regla (acción explícita de quien aprueba; ninguna viene tildada de antemano), y después se pueden desmarcar cuentas sueltas enviando de nuevo `idsContacto`. 409 si el lote no está simulado.

### `POST /lotes/{idCorreccion}/aplicar`
Requiere al menos una cuenta tildada y estado `simulada`. Hace respaldo verificado, aplica en una sola transacción y guarda lo necesario para revertir. 409 si no hay cuentas tildadas, si el lote ya estaba aplicado o si el saldo de una cuenta cambió desde la simulación. Cada cuenta del lote queda con una entrada de historial.

### `POST /lotes/{idCorreccion}/revertir`
Devuelve las cuentas del lote al estado anterior. 409 si no estaba aplicado.

### `DELETE /lotes/{idCorreccion}`
Descarta un lote simulado (baja lógica). 409 si ya fue aplicado.

## Ficha de una cuenta

### `GET /cuentas/{idContacto}/ficha`
```json
{
  "idContacto": 48, "razonSocial": "...", "corte": "2026-09-30",
  "estado": "pendiente", "estadoEfectivo": "pendiente", "etapa": "E1", "cola": "D",
  "otrosProblemas": [ "doble-descuento-tarjeta" ],
  "saldoAlCorte": -3.31, "moneda": "Pesos", "saldoEsperado": "puede-tener-saldo",
  "criterios": [ { "codigo": "C1", "etapa": "E1", "cumple": false, "medido": "8 pagos sin factura por 1.872.240,00",
                   "texto": "Hay pagos sin factura que los respalde" } ],
  "inventarioFuentes": null,
  "pagosSinFactura": 8,
  "saldosExternos": 0,
  "antecedente035": { "estado": "revisada", "nota": "...", "fecha": "..." },
  "fifoAplicadoAntes": true,
  "pregunta": null,
  "cierre": null,
  "historial": [ { "accion": "ficha-estado", "detalle": "...", "usuario": "...", "fecha": "..." } ]
}
```
`estadoEfectivo` es `reabierta` cuando el saldo al corte cambió desde el cierre (D7). `etapa` es la primera con un criterio sin cumplir (D3).

### `PUT /cuentas/{idContacto}/ficha`
Cambia el estado manual y las notas.
```json
{ "estado": "cerrada", "nota": "...", "motivoExcepcion": null, "pregunta": null }
```
- `estado` admite `en-proceso`, `esperando-evidencia`, `esperando-sergio`, `cerrada`, `cerrada-con-excepcion`.
- `cerrada` exige los 7 criterios cumplidos al corte; si no, 409 con la lista de los que faltan.
- `cerrada-con-excepcion` exige `motivoExcepcion` (422 si falta) y registra los criterios no cumplidos en el historial.
- `esperando-sergio` exige `pregunta` (422 si falta).
Al cerrar guarda corte, saldo al cierre, moneda, usuario y fecha. Una cuenta con saldo cero que cierra en cero se aprueba con esta misma llamada (aprobación rápida).

### `PUT /cuentas/{idContacto}/ficha/inventario`
Confirma la etapa E0: `{ "fuentes": [ { "tipo": "estado-proveedor|extracto|resumen-tarjeta|certificado|dropbox|access", "disponible": true, "detalle": "..." } ] }`. 422 si la lista está vacía.

## Decisiones

### `GET /cuentas/{idContacto}/decisiones`
Decisiones registradas de la cuenta, de la más nueva a la más vieja: `[ { "idDecision", "tipo", "texto", "evidencia", "usuario", "fecha" } ]`. Se guardan en `AuditoriaRevisionesHistorial` con `Accion = decision`.

### `POST /cuentas/{idContacto}/decisiones`
`{ "tipo": "descartar-access|cierre-con-excepcion|otro", "texto": "...", "evidencia": "..." }`. `texto` es obligatorio (422 si falta); `descartar-access` exige además `evidencia` con el análisis que lo respalda (jerarquía de evidencia, FR-018). 201. Solo el rol con permiso de escritura.

## Pagos sin factura (detector)

### `GET /cuentas/{idContacto}/pagos-sin-factura`
Parámetros: `desde` (opcional), `incluirMarcados` (por defecto `true`).
```json
{
  "idContacto": 48, "corte": "2026-09-30",
  "consistencia": { "pagosSinFactura": 1872239.77, "facturasSinPago": 0.0, "saldo": 1872239.77, "cierra": true },
  "pagos": [ { "medio": "galicia", "idMovimiento": 2794, "fecha": "2025-09-18", "importe": 1563484.73,
               "retencionAsociada": 18515.27, "importeEsperadoFactura": 1582000.00,
               "fechaEsperadaDesde": "2025-09-10", "fechaEsperadaHasta": "2025-09-18",
               "confianza": "alta", "anteriorA2021": false, "marca": null } ],
  "facturasSinPago": []
}
```
Si `consistencia.cierra` es falso, la respuesta lo informa como "detector sin cerrar" y no oculta la diferencia.

### `PUT /cuentas/{idContacto}/pagos-sin-factura/{medio}/{idMovimiento}`
`{ "estado": "factura-cargada|sin-documento|anticipo|pendiente", "idCompra": null, "fuenteRespaldo": null, "nota": "..." }`. `sin-documento` exige `nota` (422). `factura-cargada` exige `fuenteRespaldo` (`portal`, `estado-de-cuenta` o `pdf`) cuando la factura no tiene archivo (422). `factura-cargada` admite `idCompra`. La marca se conserva en las recomputaciones (FR-015).

## Evidencia externa

### `GET /cuentas/{idContacto}/saldos-externos`
Lista de saldos cargados, con la diferencia contra el saldo de la cuenta a esa fecha:
`[ { "idSaldoExterno", "fechaSaldo", "saldo", "moneda", "fuente", "referencia", "saldoCuentaALaFecha", "diferencia", "clasificacion": "cierra|menor-al-umbral|con-diferencia" } ]`.

### `POST /cuentas/{idContacto}/saldos-externos`
`{ "fechaSaldo": "2026-10-09", "saldo": -0.01, "moneda": "Pesos", "fuente": "portal", "referencia": "...", "nota": null }`. `fuente = sin-estado` exige `nota` con el motivo. 422 si la fecha es futura. 201.

### `DELETE /cuentas/{idContacto}/saldos-externos/{idSaldoExterno}`
Baja lógica (`Anulado = 1`). 204.

## Archivos de comprobantes

### `GET /archivos/incompletos`
Solo lectura de las carpetas de compras. Parámetros: `periodo` (por ejemplo `04 2025 - 03 2026`; por defecto todos), `estado` (opcional), `pagina`.
```json
{ "raiz": "...\\Compras", "total": 0,
  "archivos": [ { "ruta": "...", "periodo": "04 2025 - 03 2026", "proveedor": "JaureguiYMorales",
                  "fecha": "2025-09-23", "estado": "comprobante-legible-extension-incorrecta",
                  "numero": "0009-00077393", "importe": 30017.03,
                  "cargado": false, "idCompra": null } ] }
```
`estado`: `comprobante-legible-extension-incorrecta`, `no-legible`, `vacio`, `imagen-revisar`. Nunca modifica, renombra ni borra archivos. 422 si `periodo` no tiene el formato esperado; la raíz no es un parámetro del cliente.

## Puerta del FIFO (cambio en la 035)

`POST /api/auditoria-cuentas/cuentas/{id}/fifo/simular` y `.../aplicar` consultan la ficha: si la cuenta no completó E1 a E4 devuelven **409** con `{ "detail": "...", "etapaPendiente": "E1", "criterios": [ ... ] }`. Las tandas de la 035 (`/fifo/tandas/...`) respetan la misma puerta y omiten, informándolas, las cuentas que no la cumplen. `revertir` no tiene puerta.
