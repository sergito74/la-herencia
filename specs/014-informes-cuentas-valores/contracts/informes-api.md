# API Contract: Informes de Cuentas Corrientes y Valores Propios (014)

Extiende `specs/004-cuentas-corrientes/contracts/cuentas-corrientes-api.md` y `specs/003-tesoreria/contracts/tesoreria-api.md`. Todos los endpoints son `GET`, 100% solo lectura (FR-007).

## GET /api/cuentas-corrientes/contactos/{idContacto}/exportar

Exporta la cuenta corriente de un contacto a `.xlsx` (US1, FR-001). Mismos query params que `GET /api/cuentas-corrientes/{idContacto}/movimientos` (`fechaDesde`, `fechaHasta`).

**Response 200**: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`, adjunto `cuenta-corriente-{idContacto}-{fecha}.xlsx`. Una hoja "Movimientos": fecha, documento, número de documento, deuda, crédito, saldo acumulado — más una fila de saldo final.

## GET /api/cuentas-corrientes/saldos

Lista el saldo actual de todos los contactos con al menos un movimiento (US2, FR-002, FR-003, FR-004).

**Query params**: `orden` (`razonSocial` | `saldo`, default `razonSocial`).

**Response 200**:

```json
{
  "items": [
    { "idContacto": 42, "razonSocial": "Rutas Sur Atlantico S.A.", "saldoParcial": -125000.50 }
  ]
}
```

## GET /api/cuentas-corrientes/saldos/exportar

Mismo listado que arriba, en `.xlsx` (US2, FR-003). Mismos query params.

**Response 200**: adjunto `saldos-cuentas-corrientes-{fecha}.xlsx`. Una hoja "Saldos": razón social, saldo.

## GET /api/tesoreria/valores-propios/exportar

Exporta el listado de valores propios a `.xlsx` (US3, FR-005, FR-006). Mismos query params que `GET /api/tesoreria/valores-propios/movimientos` (`fechaDesde`, `fechaHasta`), sin paginar (exporta todo el rango filtrado).

**Response 200**: adjunto `valores-propios-{fecha}.xlsx`. Una hoja "Valores propios": número de cheque, fecha de emisión, fecha de vencimiento, importe, estado, fecha de cobro, número de cuenta, comentarios.

## GET /api/tesoreria/{medio}/movimientos (extensión, solo `valores-propios`)

Se agrega el campo `comentarios` (columna `Comentarios`, no expuesta hasta ahora) a la forma de `ValorPropio` (data-model.md).
