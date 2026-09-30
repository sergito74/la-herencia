# Contrato: API de alta de liquidación de remuneraciones

Extiende el router existente `backend/src/features/remuneraciones/router.py` (montado bajo `/api/remuneraciones`) — hoy 100% GET, agrega escritura.

## `POST /api/remuneraciones`

Crea una liquidación nueva. Requiere sesión con rol distinto de `SoloLectura` (mismo middleware ya usado por el resto de las escrituras).

**Request body**:
```json
{
  "idContacto": 376,
  "fechaPago": "2026-09-30",
  "periodoLiquidado": "Septiembre 2026",
  "sueldoBasico": 85096.38,
  "antiguedad": 0,
  "adicFuturosAumentos": 0,
  "diaGremio": 0,
  "aguinaldo": 0,
  "vacaciones": 0,
  "ajuste": 0,
  "ajusteNoRemunerativo": 0,
  "redondeo": 0,
  "bonificacionAdicional": 0,
  "jubilacion": 18631.02,
  "ley19032": 0,
  "obraSocial": 5081.19,
  "obraSocialAcuerdos": 0,
  "aporteSindical": 3471.43,
  "servicioDeSepelio": 0,
  "confirmarDuplicado": false
}
```

Todos los conceptos monetarios son opcionales (default 0) y **siempre en positivo** (ver `research.md` §1) — el backend resta internamente los de descuento. `idContacto`, `fechaPago` y `periodoLiquidado` son obligatorios.

**Response 201** (alta exitosa):
```json
{
  "idSalario": 1829633233,
  "importeNeto": 57912.74,
  "recibo": null
}
```

**Response 409** (ya existe una liquidación para ese empleado+período y `confirmarDuplicado` es `false` — FR-004):
```json
{
  "detail": "Ya existe una liquidación (IdSalario 1829633180) para este empleado en el período 'Septiembre 2026'."
}
```
`detail` es un string simple (mismo formato que cualquier otro error de este backend, ver `leerDetalleError` en `apiClient.ts`) — el frontend lo muestra como confirmación; si la persona confirma, reintenta el mismo POST con `confirmarDuplicado: true`, que ignora el chequeo y crea la liquidación igual.

**Response 400**: `idContacto` no corresponde a un Contacto de tipo `Empleado`, o falta un campo obligatorio.

## `POST /api/remuneraciones/{idSalario}/recibo`

Adjunta o reemplaza el PDF del recibo de una liquidación ya existente (con o sin recibo previo). `multipart/form-data`, mismo patrón que `POST /api/tesoreria/.../validar-excel` (`UploadFile`).

**Request**: campo `archivo` (PDF), máximo 10 MB (SC-004).

**Response 200**:
```json
{
  "idSalario": 1829633233,
  "recibo": "Personal\\Recibos\\2026\\2026 09 Armando Oscar Mori.pdf"
}
```

**Response 400**: el archivo no es PDF, o supera el límite de tamaño.

**Response 404**: no existe una liquidación con ese `idSalario`.

## Sin cambios

`GET /api/remuneraciones`, `GET /api/remuneraciones/pagos` y `GET /api/remuneraciones/{idSalario}/recibo` (ya existentes) no cambian su contrato — solo se corrige el valor devuelto en el campo `importe` de `GET /api/remuneraciones` (FR-015: pasa a ser el neto real, no la suma sin restar descuentos).
