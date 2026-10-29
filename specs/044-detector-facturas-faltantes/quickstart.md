# Quickstart: validar el detector (044)

1. Esquema: `cd backend && python -m scripts.crear_esquema_detector_044` (respaldo verificado previo; idempotente).
2. Pruebas: `python -m pytest tests -q -k 044`.
3. Lectura real (solo lectura): `GET /api/facturas-faltantes/tablero?mes=2025-07` → Movistar con faltante histórico jun-2025; Coop. Eléctrica bimestral sin atraso; Estudio Criado sin faltantes nov/dic-2024.
4. UI: Finanzas → "Facturas esperadas": estados con rótulo "a verificar", sin ids ni códigos.
5. Marcar un pago "falta factura" y verificar que el saldo del contacto no cambió (control de saldo antes = después).
6. Rutina 043: desde el día 5 el resumen muestra las atrasadas del mes anterior.

## Evidencia 28/10/2026

- `pytest -k 044`: 12 pruebas (motor y contrato) OK; suite de cajas 038 sin cambios.
- Datos reales: 9 proveedores recurrentes (Movistar y Sancor "llegó"; Allianz, bancos, Coop. Eléctrica bimestral, Estudio Criado, Fideicomiso La Esperanza, Starlink "pendiente"); 21 alarmas (8 remitos, 6 retenciones, 5 saldos a favor, 2 pagos sin comprobante); cálculo completo ≈3,7 s en frío.
- Recorrido UI con API interceptada (datos reales): sin errores JS, sin ids ni códigos visibles, rótulos "a verificar".
- tsc y eslint sin errores.
