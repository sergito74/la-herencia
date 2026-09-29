# Quickstart: Vincular líneas de resumen de tarjeta a pagos de Impuestos

## Prerrequisitos

- Backup verificado de `WC` antes del `ALTER TABLE` sobre
  `Tarjetas_Resumenes_Lineas_Compras` (1.598 filas reales en producción).
- Backend con `--reload`, frontend reconstruido y reiniciado
  (`npm run build` + restart — `next start` no tiene hot-reload).

## Escenario 1 — Encontrar y vincular un pago de AFIP real

1. Ir a Tesorería/Tarjetas → Conciliación (008/009), abrir una línea de
   resumen sin conciliar.
2. En "Sumar documentos de otro proveedor", buscar "AFIP".
3. Verificar que aparecen pagos reales de Impuestos (hay 749 en `WC`),
   distinguidos visualmente de un documento de Compras (FR-004).
4. Agregar uno a la selección y confirmar.
5. Verificar que la línea queda conciliada (exacta o parcial según el
   importe) con ese pago de Impuestos como respaldo.

## Escenario 2 — Reparto mixto Compras + Impuestos

1. Sobre una línea sin conciliar, agregar un documento de Compras y un
   pago de Impuestos (ej. ARBA) a la vez.
2. Verificar que el reparto proporcional (agregado en el fix de ASP,
   2026-09-29) funciona igual mezclando ambos orígenes.

## Escenario 3 — Reparto parcial de un pago de Impuestos en varias líneas

1. Buscar un pago de Impuestos cuyo importe sea mayor al de una línea de
   resumen sin conciliar.
2. Vincularlo a esa línea (queda como "cuota" — pago_parcial).
3. Buscar el mismo pago de Impuestos otra vez (en otra línea, u otra
   sesión) y verificar que aparece con `saldoPendiente` reducido
   (importe total menos lo ya vinculado).
4. Completar el resto en otra línea y verificar que, al llegar el saldo
   pendiente a cero, el pago deja de aparecer como candidato.

## Escenario 4 — No regresión de Compras

1. Correr los escenarios ya existentes de conciliación contra Compras
   (documento único, varios documentos, dólares con ajuste de tipo de
   cambio, aceptar diferencia, sin documento/no aplica).
2. Verificar que dan exactamente el mismo resultado que antes de esta
   feature (FR-007/SC-002).

## Verificación de no regresión

- Correr la suite completa de tests de `tarjetas_resumenes` — ningún test
  existente debe cambiar de resultado.
- Confirmar que el conteo de vínculos reales (1.598 antes del cambio de
  esquema) sigue siendo el mismo después del `ALTER TABLE`.
