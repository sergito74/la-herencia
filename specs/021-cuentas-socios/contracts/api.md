# Contrato: API de cuentas de socios

Nuevo router `backend/src/features/cuentas_socios/router.py`, montado bajo `/api/cuentas-socios`.

## `GET /api/cuentas-socios`

Listado de los 4 socios con su saldo actual (para una pantalla tipo "todos los socios" análoga a `/finanzas/cuentas-corrientes/saldos`, 004).

**Response 200**:
```json
{
  "socios": [
    { "idSocio": 1, "nombre": "Sergio", "saldo": 29699.10 },
    { "idSocio": 2, "nombre": "Lucy", "saldo": 0.0 },
    { "idSocio": 3, "nombre": "Cond LSC", "saldo": -5000.0 },
    { "idSocio": 4, "nombre": "Ceci", "saldo": 0.0 }
  ]
}
```

## `GET /api/cuentas-socios/{idSocio}/movimientos`

Detalle de un socio: saldo y movimientos ordenados por fecha, incluidos los anulados (nunca se ocultan, mismo criterio que 019 FR-005). Cada movimiento `AsignacionGasto` incluye `huerfano: true` si su `IdOrigen` ya no existe en `Compras` (FR-011) — se muestra igual, con un aviso, nunca se oculta ni se recalcula como si fuera válido.

**Response 200**:
```json
{
  "idSocio": 1,
  "nombre": "Sergio",
  "saldo": 29699.10,
  "movimientos": [
    {
      "idMovimiento": 42,
      "tipo": "AsignacionGasto",
      "importe": 29699.10,
      "fecha": "2025-11-14",
      "origen": "CompraParticular",
      "idOrigen": 2143515240,
      "proveedorOrigen": "Cumo Store",
      "numeroDocumentoOrigen": "0004-00000201",
      "medio": null,
      "motivo": null,
      "usuario": "sgiamberardini",
      "anulada": false,
      "motivoAnulacion": null,
      "huerfano": false
    }
  ]
}
```

## `GET /api/cuentas-socios/compras-particulares-candidatas`

Compras marcadas "particular" (`GranTotal = 0` vía línea negativa) que todavía no tienen una asignación vigente a ningún socio — para elegir cuál asignar. Reutiliza la misma fórmula de importe bruto ya corregida en `tarjetas_resumenes` (research.md §3).

**Query params**: `proveedor` (opcional, filtro por razón social).

**Response 200**:
```json
{
  "compras": [
    {
      "idCompra": 2143515240,
      "fecha": "2025-11-14",
      "proveedor": "Cumo Store",
      "numeroDocumento": "0004-00000201",
      "importeBruto": 29699.10
    }
  ]
}
```

## `POST /api/cuentas-socios/{idSocio}/asignar-gasto`

Crea un `MovimientosCuentaSocio` de tipo `AsignacionGasto` a partir de una compra particular candidata. Rechaza (409) si esa compra ya tiene una asignación vigente a otro socio (FR-009 — índice único en base, este es el mensaje legible antes de llegar ahí).

**Request**:
```json
{ "idCompra": 2143515240, "motivo": null }
```

**Response 201**: el movimiento creado (mismo shape que en `/movimientos`).

## `POST /api/cuentas-socios/movimientos/{idMovimiento}/anular`

Anula una asignación o una devolución (no destructivo — ver data-model.md). Registra también una fila en `AuditoriaReflejoSocio` (`Accion='ReversionAsignacion'` o `'ReversionDevolucion'`).

**Request**: `{ "motivo": "Se asignó al socio equivocado" }`

**Response 200**: el movimiento actualizado (`anulada: true`, con motivo/usuario/fecha de anulación).

## `POST /api/cuentas-socios/{idSocio}/devolucion`

Crea un `MovimientosCuentaSocio` de tipo `Devolucion` (registro manual).

**Request**:
```json
{ "importe": 15000.0, "fecha": "2025-11-20", "medio": "Transferencia", "motivo": "Devolución parcial gasto Cumo Store" }
```

**Response 201**: el movimiento creado.

---

Cada `POST` exitoso (asignación, anulación, devolución) inserta también su fila correspondiente en `AuditoriaReflejoSocio` dentro de la misma transacción (`execute_write_transaction`, mismo mecanismo que usan 019/020) — nunca queda un movimiento sin su rastro de auditoría.
