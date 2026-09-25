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

Comparación de saldo actual (`WC`) contra el saldo real de `LaHerencia` (US3 — la base que Access sigue escribiendo en producción, ver research.md §2), reutilizando el cálculo de saldo de 004 sin modificarlo. `SaldosReferenciaAccess` se puebla con `backend/scripts/comparar_saldo_laherencia.py --apply`, que lee `LaHerencia` en modo solo lectura.

**Query params**: `estado` (`'conciliado'` | `'con-diferencia'`, opcional).

**Response 200**:
```json
{
  "contactos": [
    {
      "idContacto": 5,
      "razonSocial": "Agrovet Integral SRL",
      "saldoActual": -541397.39,
      "saldoReferencia": -101483.57,
      "fechaCorteReferencia": "2026-09-25",
      "diferencia": -439913.82,
      "estado": "con-diferencia"
    }
  ]
}
```

Un contacto sin fila en `SaldosReferenciaAccess` no aparece en este listado (no se puede comparar sin referencia cargada). Tolerancia: `abs(diferencia) <= max($1, abs(saldoReferencia) * 0.5%)`.

**Resultado real (2026-09-25)**: 512/513 contactos conciliados; el único caso con diferencia (Agrovet Integral SRL, arriba) reveló una compra cargada en `WC` que nunca se registró en `LaHerencia` — un hallazgo real de datos, no un efecto de esta feature.
