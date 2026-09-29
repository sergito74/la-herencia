# API Contract: `/api/reasignacion-contacto`

Ver data-model.md para las entidades. Todos los endpoints requieren sesión autenticada (middleware global existente); las escrituras (`POST`) rechazan rol `Lectura` con 403 (mismo comportamiento global ya vigente).

## `POST /api/reasignacion-contacto/reasignar`

US1 — aplica una reasignación.

**Request**:
```json
{
  "origen": "Galicia",
  "idOrigen": 2712,
  "idContactoNuevo": 1652,
  "motivo": "El texto de la transferencia dice Encode S.A."
}
```

**Response 201**:
```json
{
  "idReasignacion": 1,
  "origen": "Galicia",
  "idOrigen": 2712,
  "idContactoAnterior": 605,
  "idContactoNuevo": 1652,
  "contactoAnterior": "Carbajo, Juan Manuel",
  "contactoNuevo": "Encode S.A.",
  "motivo": "El texto de la transferencia dice Encode S.A.",
  "usuario": "sgiamberardini",
  "fecha": "2026-09-25T21:00:00"
}
```

- 409 si `idContactoNuevo` es igual al contacto efectivo actual (FR-011).
- 400 si `origen` no está en la lista de orígenes soportados (FR-007) — mensaje: `"El origen '{origen}' todavía no admite reasignación."`
- 404 si `idOrigen` no existe para ese `origen`, o si `idContactoNuevo` no existe en `Contactos`.

## `GET /api/reasignacion-contacto/historial?origen=&idOrigen=`

US1 (mostrar historial de un movimiento puntual) y US3 (historial general). Sin parámetros, devuelve todas las reasignaciones (paginado); con `origen`+`idOrigen`, el historial de ese movimiento puntual.

**Response 200**:
```json
{
  "items": [
    {
      "idReasignacion": 1,
      "origen": "Galicia",
      "idOrigen": 2712,
      "idContactoAnterior": 605,
      "idContactoNuevo": 1652,
      "contactoAnterior": "Carbajo, Juan Manuel",
      "contactoNuevo": "Encode S.A.",
      "motivo": "El texto de la transferencia dice Encode S.A.",
      "usuario": "sgiamberardini",
      "fecha": "2026-09-25T21:00:00"
    }
  ]
}
```

## `GET /api/reasignacion-contacto/candidatos`

US2 — ejecuta la detección (solo lectura, nunca escribe — FR-009) sobre `Movimientos Galicia`/`Movimientos BNA` y devuelve los candidatos pendientes (excluyendo los ya descartados).

**Response 200**:
```json
{
  "candidatos": [
    {
      "origen": "Galicia",
      "idOrigen": 2712,
      "fecha": "2025-08-01",
      "descripcion": "TRF INMED PROVEED Encode S.A. 30711103534 VARIOS BANCO DE LA NACION A",
      "importe": 159720.0,
      "idContactoActual": 605,
      "contactoActual": "Carbajo, Juan Manuel",
      "idContactoSugerido": 1652,
      "contactoSugerido": "Encode S.A."
    }
  ]
}
```

## `POST /api/reasignacion-contacto/candidatos/descartar`

US2 — marca un candidato como falso positivo (FR-010), sin aplicar ningún cambio de contacto.

**Request**:
```json
{ "origen": "Galicia", "idOrigen": 2633, "idContactoSugerido": 575 }
```

**Response 200**: `{ "ok": true }`. Idempotente: descartar un candidato ya descartado no falla ni duplica.
