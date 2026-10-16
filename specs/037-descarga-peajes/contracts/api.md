# API Contract: /api/descarga-peajes

Todos los endpoints exigen sesión (middleware global). Los `POST` los rechaza el middleware con 403 si el rol es `Lectura` (FR-002). Las fechas van en ISO y los importes como número, que el frontend formatea con los helpers globales.

## GET /api/descarga-peajes/estado
Configuración y ejecución en curso (US1, US4).
```json
{
  "portales": [
    {"portal": "TelepeajePlus", "credenciales": true},
    {"portal": "TelePASE", "credenciales": true},
    {"portal": "CEAMSE", "credenciales": false},
    {"portal": "AUBASA", "credenciales": false}
  ],
  "tarea": {"instalada": true, "proximaCorrida": "2026-10-19T09:00:00", "ultimoResultado": "0"},
  "enCurso": {"idEjecucion": 12, "inicio": "...", "origen": "manual"} 
}
```
`enCurso` es `null` si no hay ninguna. `tarea.instalada=false` → `proximaCorrida=null`. Nunca incluye usuarios ni contraseñas.

## POST /api/descarga-peajes/ejecuciones
Inicia "Descargar ahora".
- 202 → `{"idEjecucion": 13}`; la ejecución sigue en segundo plano.
- 409 → `{"detail": "Ya hay una descarga en curso", "idEjecucion": 12}`.
- 403 → rol de solo lectura (middleware).

## GET /api/descarga-peajes/ejecuciones?limite=20&desde=0
Historial, de la más reciente a la más vieja (US3).
```json
{"items": [{"idEjecucion": 13, "origen": "manual", "usuario": "sergio", "inicio": "...", "fin": "...", "estado": "con_errores",
  "portales": [{"portal": "TelePASE", "estado": "ok", "nuevos": 1, "existentes": 23, "cargados": 1, "pendientes": 0, "error": null}]}],
 "total": 40}
```

## GET /api/descarga-peajes/ejecuciones/{id}
Igual que un ítem del historial, más `documentos` (los bajados en esa ejecución, mismo formato que abajo). Es lo que consulta la pantalla cada 2 s mientras `estado = en_curso`. Devuelve 404 si no existe.

## GET /api/descarga-peajes/documentos?estado=pendiente|cargado_auto|ya_cargado&limite=50&desde=0
```json
{"items": [{"idDocumento": 101, "portal": "TelePASE", "proveedor": "AutopistasDelSol", "idContacto": 276,
  "fechaDocumento": "2026-10-16", "numeroDocumento": "0840-00811111", "totalImpreso": 4120.55,
  "ruta": "C:\\Users\\...\\20261016_AutopistasDelSol.pdf", "nombreArchivo": "20261016_AutopistasDelSol.pdf",
  "estadoCarga": "pendiente", "motivo": "No cierra: calculado $4.118,20, impreso $4.120,55", "idCompra": null,
  "idEjecucion": 13}], "total": 3}
```
Antes de responder revalida los `pendiente` contra Compras (R8). El PDF se abre con el endpoint existente `GET /api/compras/documento-local?ruta=…`. "Cargar en Compras" navega a `/compras/nueva?idContacto=…&proveedor=…&fecha=…&numeroDocumento=…&documentoOriginal=…`.

## GET /api/descarga-peajes/resumen
Contador del menú (FR-020): `{"pendientes": 2, "portalesConError": 1}`.

## Script (tarea semanal)
`backend/.venv/Scripts/python.exe -m scripts.descargar_peajes --origen semanal [--dry-run]`. `--dry-run` no escribe nada (ni base, ni disco, ni lock) e imprime lo que bajaría y cargaría. En `POST /ejecuciones` el lock se decide antes de responder: nunca dos 202 simultáneos. Código de salida: 0 si terminó (completa o con errores, que quedan registrados); 2 si salteó porque había otra en curso; 1 si hubo un error general.
