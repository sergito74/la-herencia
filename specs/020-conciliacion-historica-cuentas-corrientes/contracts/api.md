# Contrato: endpoints de revisión y verificación

Nuevo router `backend/src/features/conciliacion_historico/router.py`, montado bajo `/api/conciliacion-historico`.

## `GET /api/conciliacion-historico/resumen`

Lista, por contacto, el resultado de la conciliación histórica (US2).

**Query params**: `soloConDudas` (bool, default `false`) — si `true`, filtra a contactos con al menos un caso de mejor esfuerzo o excepción.

**Response 200**:
```json
{
  "contactos": [
    {
      "idContacto": 123,
      "razonSocial": "Rutas Sur Atlantico S.A.",
      "aplicadosExactos": 14,
      "aplicadosMejorEsfuerzo": 2,
      "sinAplicar": 1
    }
  ]
}
```

## `GET /api/conciliacion-historico/{idContacto}/detalle`

Detalle de las aplicaciones automáticas y excepciones de un contacto (US2), para revisión antes de decidir si corregir con el mecanismo de anulación existente (019).

**Response 200**:
```json
{
  "idContacto": 123,
  "aplicaciones": [
    {
      "idAplicacion": 456,
      "origen": "automatica-mejor-esfuerzo",
      "origenMovimiento": "bna",
      "idMovimientoOrigen": 789,
      "tipoDocumento": "CompraDeuda",
      "idDocumentoAplicado": 321,
      "importeAplicado": 15000.0,
      "notaConciliacion": "Diferencia de $120 (0.8%) contra combinación FIFO de 2 documentos"
    }
  ],
  "excepciones": [
    { "origenMovimiento": "efectivo", "idMovimientoOrigen": 987, "motivo": "sin documentos candidatos" }
  ]
}
```

Para anular una aplicación, se usa el endpoint ya existente de 019 (`POST /api/aplicaciones-pago/{idAplicacion}/anular`) — no se duplica aquí.

## `GET /api/conciliacion-historico/saldos`

Comparación de saldo contra Access (US3), reutilizando el cálculo de saldo de 004.

**Query params**: `estado` (`'conciliado'` | `'con-diferencia'`, opcional).

**Response 200**:
```json
{
  "contactos": [
    {
      "idContacto": 123,
      "razonSocial": "Rutas Sur Atlantico S.A.",
      "saldoActual": 148500.0,
      "saldoAccess": 148500.0,
      "fechaCorteAccess": "2026-08-31",
      "diferencia": 0.0,
      "estado": "conciliado"
    }
  ]
}
```

Un contacto sin fila en `SaldosReferenciaAccess` no aparece en este listado (no se puede comparar sin referencia cargada).
