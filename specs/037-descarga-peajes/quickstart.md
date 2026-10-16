# Quickstart / validación: 037 — Descarga de peajes

## Prerrequisitos
1. `backend/.venv` con `playwright` y `keyring` instalados (`requirements.txt`).
2. Esquema creado: `python -m scripts.crear_esquema_descarga_peajes_037` (desde `backend/`, con respaldo verificado) e importación del manifiesto (`--importar-manifiesto`).
3. Instalador corrido por Sergio: `backend/scripts/instalar_descarga_peajes.ps1` (credenciales y tarea semanal).

## Pruebas automáticas (sin portales ni escritura real)
- `pytest backend/tests/test_descarga_peajes_lectores.py`: cada lector contra un PDF real de cada formato copiado a `tests/fixtures/peajes/` (sin datos de credenciales). Verifica número, fecha, renglones y que el total calculado cierre con el impreso. Incluye un caso alterado que no cierra y debe quedar pendiente.
- `pytest backend/tests/contract/test_descarga_peajes_api.py`: contratos de los endpoints con repositorio y servicio simulados; 409 en concurrencia; 403 con rol `Lectura`; `estado` nunca expone credenciales.

## Validación manual end-to-end
1. **Estado (US4)**: abrir Compras › Descarga de peajes. Antes del instalador, los 4 portales figuran "sin configurar" y la tarea "no instalada". Después, todo configurado y aparece la próxima corrida (lunes 9:00).
2. **Simulación**: `python -m scripts.descargar_peajes --dry-run` lista lo que bajaría y lo que cargaría, sin escribir.
3. **Descargar ahora (US1)**: apretar el botón. Se ve el avance por portal. Con la carpeta al día, el resultado es "sin documentos nuevos" en los 4.
4. **Concurrencia**: apretar de nuevo mientras corre → aviso de "ya hay una en curso".
5. **Carga automática (US2)**: para probarla sin esperar un comprobante nuevo, sacar del registro la clave de un documento cuya compra exista (en un entorno de prueba). La ejecución lo baja con sufijo " 001" y lo marca `ya_cargado` (mismo proveedor y número), sin duplicar la compra. Con el primer comprobante nuevo real, verificar que la compra creada coincide con el PDF.
6. **Pendiente**: un formato no reconocido aparece en la lista con su motivo, el contador del menú sube, "Cargar en Compras" abre el alta precargada y, al guardarla, el contador baja.
7. **Semanal (US3)**: ejecutar la tarea desde el Programador de tareas; queda en el historial con origen "semanal".
8. **Solo lectura**: con un usuario `Lectura`, el botón no aparece y el `POST` devuelve 403.
