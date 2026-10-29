# Validación

1. Desde backend, python -m scripts.trabajos_eventuales_045: simula planilla, informa 75 trabajos y $2.500.558; --aplicar crea esquema e importa con respaldo verificado. Repetir simulación: 0 nuevos.
2. pytest tests/test_trabajos_eventuales.py tests/contract/test_trabajos_eventuales_api.py -q (repositorio simulado, sin WC).
3. En frontend ejecutar npm run build. Abrir Personal > Trabajos eventuales, verificar filtros, totales e histórico; abrir trabajo e ir a Remuneraciones y volver por una liquidación.
4. En pruebas simuladas, vincular parcialmente y rechazar otro trabajador, excesos, importes negativos y reintentos. Simular edición incompatible y falta de permiso. No usar datos reales para pruebas de escritura.
5. Consulta real solo lectura: 75 trabajos, ocho trabajadores, total 2500558; mismo número de remuneraciones y ningún pago nuevo. Registrar respaldo, vínculos aplicados y casos sin vínculo en validacion.md.
