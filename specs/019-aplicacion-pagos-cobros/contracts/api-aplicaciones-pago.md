# API Contract: `/api/aplicaciones-pago` (019-aplicacion-pagos-cobros)

Estilo idéntico al resto del sistema: toda la API requiere sesión (016-autenticacion); errores de negocio → 400.

## `GET /api/aplicaciones-pago/documentos-pendientes`

Query params: `idContacto` (requerido), `tipo?` (`compra`|`venta`, default ambos).

- Lista los documentos pendientes/parciales de ese contacto (compras y/o ventas), con `{tipoDocumento, idDocumento, fecha, numeroDocumento, importeTotal, aplicado, saldoPendiente, estado}`.
- Documentos ya totalmente aplicados no se listan acá (usar el endpoint de estado de documento para verlos).

## `POST /api/aplicaciones-pago/sugerir`

Body: `{ origenMovimiento: string, idMovimientoOrigen: number }`.

- Resuelve el contacto e importe reales del movimiento (mismo patrón que `tesoreria/matching.py`), busca sus documentos pendientes (mismo contacto, mismo tipo según si el movimiento es ingreso o egreso) y devuelve la sugerencia FIFO (research.md §3):
  ```json
  {
    "importeMovimiento": 500000.00,
    "sugerencias": [
      { "tipoDocumento": "CompraDeuda", "idDocumento": 123, "fecha": "2026-06-01", "saldoPendiente": 300000.00, "importeSugerido": 300000.00 },
      { "tipoDocumento": "CompraDeuda", "idDocumento": 145, "fecha": "2026-06-15", "saldoPendiente": 250000.00, "importeSugerido": 200000.00 }
    ],
    "saldoSinAsignar": 0.00
  }
  ```
- No persiste nada — es una lectura pura, el usuario edita antes de confirmar (FR-003/FR-004).

## `POST /api/aplicaciones-pago`

Body: `{ origenMovimiento: string, idMovimientoOrigen: number, aplicaciones: [{ tipoDocumento: string, idDocumento: number, importeAplicado: number }] }`.

- Confirma las aplicaciones (ya editadas por el usuario o tomadas de la sugerencia tal cual).
- Valida (400 si falla, FR-008): ningún documento queda sobre-aplicado (con tolerancia, research.md §4); la suma de `importeAplicado` no supera el importe real del movimiento (con la misma tolerancia).
- Inserta una fila por cada entrada de `aplicaciones` (nunca actualiza filas existentes).

## `POST /api/aplicaciones-pago/{idAplicacion}/anular`

Body: `{ motivo: string }` (requerido).

- Marca `Anulada=1`, `MotivoAnulacion`, `UsuarioAnulacion`, `FechaAnulacion` — nunca borra ni edita `ImporteAplicado`/`IdDocumentoAplicado` (FR-005).
- Sin restricción de rol (FR-011, confirmado por el dueño) — cualquier usuario autenticado puede anular.

## `GET /api/aplicaciones-pago/documento/{tipoDocumento}/{idDocumento}`

- Estado actual del documento (`{importeTotal, aplicado, saldoPendiente, estado}`) + historial completo de aplicaciones (vigentes y anuladas, con motivo/usuario/fecha de cada una) — FR-007, User Story 3.

## `GET /api/aplicaciones-pago/movimiento/{origenMovimiento}/{idMovimientoOrigen}`

- Estado del movimiento (`{importe, aplicado, saldoSinAplicar}`) + lista de sus aplicaciones vigentes, cada una con los datos del documento aplicado (para mostrar en el flujo de caja por rubro qué Rubro/Centro de Costos le corresponde — FR-010).
