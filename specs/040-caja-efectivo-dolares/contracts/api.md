# Contrato 040 — extensión de API 038

## Identidad y moneda
`giamigli-dolares` → `dbo.MovimientosCajaEfectivo.Caja = GiamigliUSD`. Todo `importe`, `saldo`, `saldoDecimal`, `subtotalFiltradoDecimal`, `saldoCorridoDecimal`, importes de arqueo y efectos físicos de esta caja significa dólares estadounidenses. No sumar con cajas en pesos. La moneda se deriva del slug permitido, no de un valor arbitrario del cliente.

Se conservan rutas, paginación, filtros, permisos e idempotencia de 038. GET /api/cajas-efectivo/giamigli-dolares/saldo y /movimientos devuelven exclusivamente esa caja.

## Operaciones
POST /operaciones/previsualizar y POST /operaciones (Idempotency-Key UUID) aceptan para caja USD:
- ingreso_dolares: pierna física positiva; sin asiento implícito de contacto/socio/banco.
- egreso_dolares: pierna negativa; mismo criterio.
- aporte / retiro_a_cuenta: caja y movimiento de socio atómicos, ImporteUSD exacto, ImporteKgCarne=0. Importe nominal del socio en pesos = US$ × promedio billete BNA de la última fecha <= fecha del movimiento; guardar fuente y fecha en contexto auditado. Falta de dólar impide guardar, sin inventar equivalencia. El saldo de caja nunca utiliza esta conversión.
- retiro_ganancias: salida física, sin deuda de socio.

Mantener advertencias de saldo negativo y períodos arqueados, previsualización vigente, auditoría y anulación conjunta. Entradas/salidas requieren concepto, importe positivo, fecha y cuenta A/B. No son aplicaciones de documentos ni conciliaciones bancarias.

422 para circuitos de pagos/cobros/costos/bancos en pesos sobre caja USD, o para traspasos entre distintas monedas; no tratar dólares como pesos ni usar pase 1:1.

## Arqueos e importación
Mismas rutas y reglas de 038, denominaciones y diferencias USD. Un arqueo exacto no crea ajuste.
El libro CajasGiamigli admite hoja Caja Efectivo Dolares: fecha A, concepto B, cuenta C, detalle D, referencia F en pesos no utilizada como importe, movimiento G en dólares y saldo H. Preservar fila, cruda y huella. Candidatos/vínculos siempre restringidos a esta caja. Se mantienen comparaciones A/B y clasificaciones expresas antes de importar.
