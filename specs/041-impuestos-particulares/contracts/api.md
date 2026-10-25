# API — 041 (prefijo /api/impuestos)

- `GET /{id}/particular` → `{cargas: [{idCarga, idSocio, socio, importe, motivo, partida, estado, devuelto, estadoDevolucion, idMovimientoSocio}], parteEmpresa, avisos: []}`. Avisos: partida en el padrón con titular; Debe manual equivalente en la cuenta del socio.
- `POST /{id}/particular` `{idSocio, importe | porcentaje, motivo, partida?, reemplazarMovimientoManual?: idMovimiento, confirmarCuentaCerrada?: bool}` → carga creada. 409 si supera el importe; 409 con `requiereConfirmacion` si la cuenta del socio está cerrada o hay doble carga sin decidir.
- `POST /particular/{idCarga}/anular` `{motivo}` → carga anulada (Debe anulado).
- `POST /particular/{idCarga}/devoluciones` `{idMovimientoSocio}` (vincula un Haber existente) o `{fecha, importe, medio, motivo}` (crea un Haber nuevo).
- `GET /` (lista): agrega por impuesto `aCargoDe: [{socio, importe}]` y `estadoDevolucion`; filtro `?particular=true`.
- `DELETE /{id}` → 409 si tiene cargas vigentes.
- `GET /partidas/{partida}` → titular del padrón, si existe.

Escrituras: 403 para rol Lectura.
