# API: 043 — Documentos nuevos

Prefijo `/api/documentos-nuevos`. Autenticación: cookie de sesión (016). Lectura: cualquier usuario; escritura (revisado, módulo, cargar): rol Administrador. Respuestas en palabras de negocio (sin términos internos).

## GET /resumen

Cantidad pendiente de revisar por módulo (para los números del menú).

```json
{ "compras": 2, "impuestos": 0, "ventas": 1, "tesoreria": 3, "cuentasCorrientes": 0, "sinClasificar": 1, "total": 7 }
```

## GET /?modulo={modulo}&limite=50&desde=0

`modulo` ∈ `compras | impuestos | ventas | tesoreria | cuentas_corrientes | sin_clasificar` (obligatorio, lista permitida). Solo pendientes de revisión, más antiguos primero.

```json
{
  "items": [{
    "idDocumentoNuevo": 12,
    "origen": "Portal Allianz" ,
    "origenDetalle": "Llegó el 27/10/2026 14:03",
    "tipo": "Factura",
    "estado": "cargado_solo | para_cargar",
    "motivo": null,
    "contacto": "Allianz", "idContacto": 515,
    "fecha": "2026-10-13", "numero": "260040606375 10", "total": 0.0,
    "archivo": "20261013_Allianz.pdf", "ruta": "C:\\…\\20261013_Allianz.pdf",
    "idRegistro": 2143524139,
    "enlace": "/compras/2143524139",
    "renglones": [{ "detalle": "Prima", "rubro": "Seguros Generales", "centroCosto": "Adm. General", "importe": 124693.56, "iva": 21.0 }]
  }],
  "total": 1
}
```

`origen` para mail: "Mail de <remitente>" y `origenDetalle` con asunto y fecha. `renglones` solo cuando el módulo los tiene (Compras).

## POST /{id}/revisado

Marca revisado (quién y cuándo). 404 si no está pendiente. `{ "ok": true }`

## POST /{id}/modulo

Body `{ "modulo": "impuestos" }`. Solo para `sin_clasificar` (o corrección de clasificación). Auditado. Devuelve el ítem actualizado.

## GET /rutina

Estado de la rutina para la bóveda (solo Administrador): última corrida, próxima corrida, resultado por cuenta y cantidades.

```json
{ "proxima": "2026-10-28T07:00:00", "ultima": { "inicio": "…", "fin": "…", "estado": "ok", "mailsLeidos": 14, "documentosNuevos": 3, "cargadosSolos": 2, "paraCargarAMano": 1, "mensaje": null } }
```

## Cambios a la bóveda (042)

- Se retiran `GET /api/boveda/revision` y `POST /api/boveda/documentos/{id}/revisado`.
- `GET /api/boveda/resumen` deja de contar pendientes de carga (pasan a los menús de cada módulo).
