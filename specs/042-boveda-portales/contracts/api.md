# API Contract: /api/boveda

Todos los endpoints exigen sesión (middleware global) **y** `rol == "Administrador"`; cualquier otro rol recibe 403 `{"detail": "Solo el administrador accede a la bóveda"}` (FR-001). Ninguna respuesta incluye secretos salvo `POST …/revelar`. Fechas ISO; importes como número (el frontend formatea con los helpers globales). Respuestas con secretos llevan `Cache-Control: no-store`.

## Portales

### GET /api/boveda/portales
```json
{"items": [{
  "idPortal": 5, "nombre": "Cargill", "url": "https://...", "tipo": "proveedor",
  "idContacto": 258, "contacto": "Cargill SACI",
  "credencial": {"idCredencial": 3, "nombre": "Cargill Giamigli", "usuario": "giamigli", "claveConfigurada": true, "estado": "ok"},
  "conector": {"codigo": "cargill", "disponible": true, "estadoCuenta": true, "cargaCompras": true},
  "autorizacion": {"vigente": true, "fecha": "2026-10-20", "autorizadoPor": "Sergio", "alcance": "solo_lectura_descarga"},
  "programacion": {"frecuencia": "semanal", "diaSemana": 1, "diaMes": null, "hora": "07:00", "proximaCorrida": "2026-11-02T07:00:00", "suspendida": false, "motivoSuspension": null},
  "ultimaCorrida": {"idCorrida": 88, "inicio": "...", "estado": "ok", "nuevos": 2},
  "ultimaFoto": {"fechaCorte": "2026-10-27", "moneda": "USD", "saldoPortal": -60000.10, "saldoSistema": -60000.10, "diferencia": 0.00},
  "enCurso": false
}]}
```
`credencial.estado`: `ok` | `faltante` | `rechazada`. `conector.disponible=false` ⇒ "solo bóveda".

### POST /api/boveda/portales
Body: `{nombre, url, tipo, idContacto?, idCredencial? | credencialNueva?: {nombre, titular, idSocio?, usuario, clave, datos: [{nombre, secreto, valor}]}, codigoConector?, notas?}` → 201 `{"idPortal": 12}`. 400 si URL no es http/https, nombre repetido o `codigoConector` desconocido.

### PATCH /api/boveda/portales/{id}
Mismos campos, parciales. No toca secretos.

### GET /api/boveda/conectores
Lista de conectores implementados en código: `[{codigo, nombre, estadoCuenta, cargaCompras}]`.

## Credenciales

### GET /api/boveda/credenciales
`[{idCredencial, nombre, titular, idSocio, usuario, claveConfigurada, datos: [{nombre, secreto, valor | null}], portales: [ids]}]` — `valor` es `null` en los secretos.

### POST /api/boveda/credenciales · PATCH /api/boveda/credenciales/{id}
Alta / edición. `clave` y datos secretos se aceptan en el body y se cifran; nunca se devuelven.

### PUT /api/boveda/credenciales/{id}/clave
`{"clave": "..."}` → 204. Si el portal estaba suspendido por credenciales rechazadas, se levanta la suspensión y se recalcula la próxima corrida. Audita `cambio_clave`.

### POST /api/boveda/credenciales/{id}/revelar
`{"campo": "clave" | "dato:<Nombre>"}` → 200 `{"valor": "..."}`, `Cache-Control: no-store`. Audita `revelar`. El frontend lo muestra 30 s o lo copia al portapapeles.

## Autorización y programación

### POST /api/boveda/portales/{id}/autorizacion
`{"fecha": "2026-10-27", "autorizadoPor": "Sergio", "fuente": "..."}` → 201. Alcance fijo `solo_lectura_descarga`.

### DELETE /api/boveda/portales/{id}/autorizacion
Revoca la vigente → 204; efecto inmediato: la corrida en curso de ese portal verifica la autorización antes de cada descarga y se detiene (`sin_autorizacion`) sin bajar nada más.

### PUT /api/boveda/portales/{id}/programacion
`{frecuencia, diaSemana?, diaMes?, hora}` → 200 con `proximaCorrida`. 400 si el portal no tiene conector.

## Corridas

### POST /api/boveda/portales/{id}/corridas · POST /api/boveda/corridas (todos los activos)
202 `{"idCorrida": 90}` (o lista). 409 `{"detail": "Ya hay una corrida en curso", "idCorrida": 89}`. 409 `{"detail": "Falta autorización"}` si no hay vigente. 400 si "solo bóveda".

### GET /api/boveda/corridas?idPortal=&limite=20&desde=0
Historial paginado: `{items: [{idCorrida, idPortal, portal, origen, usuario, inicio, fin, estado, nuevos, existentes, cargados, pendientes, mensaje}], total}`.

### GET /api/boveda/corridas/{id}
Detalle con documentos y fotos de esa corrida.

## Documentos y estado de cuenta

### GET /api/boveda/documentos?idPortal=&estado=&limite=50&desde=0
`{items: [{idDocumento, portal, tipo, proveedor, fechaDocumento, numeroDocumento, totalImpreso, moneda, ruta, nombreArchivo, estadoCarga, motivo, idCompra}], total}`. Antes de responder revalida pendientes (regla 037 R8).

### GET /api/boveda/estado-cuenta?idPortal=
Fotos, de la más reciente a la más vieja; `GET /api/boveda/estado-cuenta/{idFoto}` con movimientos.

### PATCH /api/boveda/estado-cuenta/{idFoto}
`{"revisada": true}` — solo marca vista; no crea movimientos.

## Contador del menú

### GET /api/boveda/resumen
`{"pendientesCarga": 3, "conError": 1, "requiereIntervencion": 1, "diferenciasSaldo": 2, "total": 7}`. Para usuarios no administradores el menú no lo consulta. `GET /api/descarga-peajes/resumen` sigue respondiendo (filtrado a peajes) por compatibilidad.

## Compatibilidad 037

`/api/descarga-peajes/*` se mantiene: `estado`, `ejecuciones` y `documentos` leen de las tablas nuevas filtrando los portales de peaje; `POST ejecuciones` dispara las corridas de esos 4 portales. Estos endpoints conservan el permiso de 037 (sesión + no `Lectura` para escrituras), **no** exigen Administrador y nunca exponen credenciales, autorización ni programación editable. `GET /api/descarga-peajes/resumen` alimenta el contador de peajes de Compras.
