# Contrato: API de Flujo de caja por Rubro

Router existente `backend/src/features/flujo_caja/router.py`, prefijo `/api/flujo-caja`. Todo es de solo lectura.

## `GET /api/flujo-caja/por-rubro` (extendido)

**Query**: `fechaDesde`, `fechaHasta` (opcionales, mismo default que hoy), `granularidad` = `semanal|mensual|trimestral|anual` (default `mensual`), **`moneda` = `ARS|USD`** (nuevo, default `ARS`).

**Response 200**:
```json
{
  "moneda": "USD",
  "periodos": ["2026-01", "2026-02"],
  "saldoInicial": {
    "cuentas": [
      {"cuenta": "Nación", "importe": 707225.94},
      {"cuenta": "Galicia CC", "importe": 2667606.12},
      {"cuenta": "Galicia Fondo FIMA", "importe": 12178368.01, "aclaracion": "Capital neto colocado, sin rendimiento"}
    ],
    "total": 15553200.07
  },
  "ingresos": {
    "rubros": [{"rubro": "Venta Terneros", "valores": {"2026-01": 0, "2026-02": 37340.16}, "total": 37340.16}],
    "totalPorPeriodo": {"2026-01": 0, "2026-02": 37340.16}
  },
  "egresos": {
    "centrosCosto": [
      {"centroCosto": "Personal", "rubros": [{"rubro": "Sueldos", "valores": {}, "total": 0}],
       "subtotalPorPeriodo": {}, "subtotal": 0}
    ],
    "totalPorPeriodo": {}
  },
  "netoOperativoPorPeriodo": {"2026-01": 0, "2026-02": 0},
  "internos": {
    "rubros": [
      {"rubro": "Colocación FIMA", "valores": {}, "total": 0},
      {"rubro": "Rescate FIMA", "valores": {}, "total": 0},
      {"rubro": "Traspaso entre bancos", "valores": {}, "total": 0}
    ],
    "totalPorPeriodo": {}
  },
  "saldoFinalPorPeriodo": {"2026-01": 0, "2026-02": 0},
  "sinTipoCambio": [
    {"periodo": "2026-05", "seccion": "egresos", "centroCosto": "Personal", "rubro": "Sueldos", "cantidad": 3, "importeArs": 2554545.0}
  ]
}
```

**Notas**:
- `saldoInicial` pasa de número a objeto, lo que cambia el contrato de 018 v2. No hay otros consumidores en el frontend (verificado en tasks).
- En `moneda=USD`, los importes son la suma de cada parte convertida con su cotización del día. `saldoInicial` se convierte con la cotización del día de inicio del rango y cada `saldoFinalPorPeriodo` con la del último día del período; si falta, el saldo viene `null` y se agrega `saldosSinTipoCambio: ["inicial" | clave de período]`. `sinTipoCambio` lista las celdas con partes excluidas por falta de cotización; en `ARS` viene vacío.
- Las tres filas de `internos` vienen siempre, aunque estén en cero. Cada parte interna de tipo "Traspaso entre bancos" sin contraparte encontrada se informa en `traspasosSinContraparte: [{fecha, cuenta, importe, idMovimiento}]`.
- "Pendiente de aplicar" e "Histórico sin aplicar" aparecen como rubros de ingresos o egresos según el signo, siempre visibles.

## `GET /api/flujo-caja/por-rubro/detalle` (nuevo)

Movimientos (partes) que componen una celda.

**Query**: `fechaDesde`, `fechaHasta`, `granularidad`, `moneda`, `periodo` (clave de columna, ej. `2026-02`), `seccion` = `ingresos|egresos|internos`, `rubro`, `centroCosto` (opcional, solo egresos).

**Response 200**:
```json
{
  "total": 37340.16,
  "items": [
    {
      "fecha": "2026-02-10", "cuenta": "Galicia CC", "concepto": "Transferencia recibida",
      "contacto": "Consignataria X", "importeArs": 44808192.0,
      "importeParteArs": 37340160.0,
      "documentoAplicado": {"tipo": "VentaHacienda", "id": 312, "numero": "0001-00000123"},
      "cotizacion": 1200.0, "fechaCotizacion": "2026-02-10", "importeUsd": 31116.8,
      "origenMovimiento": "galicia", "idMovimiento": 98765
    }
  ]
}
```

**Garantía**: `total` es igual al valor de la celda en la respuesta de `por-rubro` con los mismos parámetros (FR-006).

**Response 422**: `periodo` inválido para la granularidad elegida.

## `GET /api/flujo-caja/por-rubro/exportar` (nuevo)

Mismos parámetros que `por-rubro`. Devuelve un `.xlsx` (`Content-Disposition: attachment`) con la misma estructura de filas y subtotales, importes numéricos con formato de moneda y un encabezado con rango, granularidad, moneda y fecha de generación. En USD, una hoja adicional "Sin tipo de cambio" lista lo excluido.
