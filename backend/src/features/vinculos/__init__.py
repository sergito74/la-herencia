"""031 — Integridad de vínculos pago → documento.

Unifica las cinco vías donde se guarda "qué documento paga este dinero"
(AplicacionesPago, consumos de tarjeta, pagos de resumen, conciliaciones de
tesorería y backfill de impuestos) con las reglas de cadena acordadas con
Sergio: factura ← consumo / valor propio ← débito bancario."""
