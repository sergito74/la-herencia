# Quickstart de validación

1. `pytest backend/tests/documentos_nuevos -q`: pasan los escenarios de carga, rechazo y prioridad.
2. `python backend/scripts/simular_lector_general.py`: compara contra facturas ya cargadas, sin escribir. Esperado: 100% de coincidencia en lo que cargaría (SC-001), más cobertura y motivos.
3. Sergio aprueba el informe y se activa el lector.
4. Tras la primera corrida real: cada carga aparece en "Nuevos para revisar", con archivo, y no hay duplicados ni contactos nuevos.
