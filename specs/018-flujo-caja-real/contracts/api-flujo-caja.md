# API Contract: `/api/flujo-caja` (018-flujo-caja-real)

Estilo y convenciones idénticas al resto del sistema: solo lectura (nunca INSERT/UPDATE/DELETE); toda la API requiere sesión (016-autenticacion); errores de negocio → 400.

## `GET /api/flujo-caja/resumen`

Query params: `fechaDesde?` (default: hoy - 24 meses), `fechaHasta?` (default: hoy), `granularidad` (`mensual` | `semanal`, default `mensual`).

- Agrega `Movimientos BNA` (las 3 cuentas, distinguidas) + `Movimientos Galicia` por período según `granularidad`.
- Cada período devuelve:
  ```json
  {
    "periodo": "2026-07",
    "porCuenta": [
      { "banco": "BNA", "numeroCuenta": "6150111899", "ingresos": 0, "egresos": 0, "neto": 0 },
      { "banco": "Galicia", "numeroCuenta": "0000798-8 383-4", "ingresos": 0, "egresos": 0, "neto": 0 }
    ],
    "totalIngresos": 0,
    "totalEgresos": 0,
    "totalNeto": 0,
    "movimientosInternos": { "ingresos": 0, "egresos": 0, "total": 0 },
    "sinClasificar": { "cantidad": 0, "importeAbsoluto": 0 }
  }
  ```
- Incluye además, a nivel de respuesta (no por período), `ultimaFechaConDatos` por cuenta (FR-004). Lista **las 4 cuentas conocidas** (las 3 de BNA — incluidas las 2 dadas de baja, que tienen una fecha fija e histórica — más Galicia), sin filtrar por vigencia: es informativo, coherente con "distinguir las 3 cuentas" (US3), no solo un indicador operativo de la cuenta activa:
  ```json
  "ultimaCarga": [
    { "banco": "BNA", "numeroCuenta": "12301640001709", "fecha": "2012-06-29" },
    { "banco": "BNA", "numeroCuenta": "12301640029280", "fecha": "2022-07-05" },
    { "banco": "BNA", "numeroCuenta": "6150111899", "fecha": "2026-07-30" },
    { "banco": "Galicia", "numeroCuenta": "0000798-8 383-4", "fecha": "2026-08-31" }
  ]
  ```
- 400 si `fechaDesde` es anterior a 2010-08-31 (no hay saldo de apertura conocido antes de esa fecha, edge case de spec.md).

## `GET /api/flujo-caja/detalle`

Query params: `fechaDesde`, `fechaHasta` (requeridos, acotan un período puntual — ej. un mes), `banco?` (`BNA` | `Galicia`), `numeroCuenta?`, `soloInternos?` (bool, default `false`).

- Devuelve el listado de movimientos individuales que componen ese período/cuenta (drill-down, FR-005), con `esInterno: bool` calculado por movimiento (research.md §1) y `contacto` cuando existe.
- `soloInternos=true` filtra solo los movimientos clasificados como internos — usado por el bloque "Movimientos internos" de la pantalla.
- Cada fila: `{ fecha, banco, numeroCuentaBancaria, concepto, importe, idContacto, contacto, esInterno }`.
