# Plan — 033 Alta de boletas de impuestos

## Backend (`backend/src/features/impuestos/`)

- `repository.py`: `ORGANISMOS` (contacto, nombre, código heredado),
  `get_catalogo()` (organismos + tipos filtrados, FR-001/002),
  `get_impuesto(id)`, `validar(...)`, `buscar_duplicado(...)` (FR-004),
  `crear/actualizar/eliminar` con `execute_write_transaction` (FR-007),
  `vinculos(id)` para FR-005.
- `schemas.py`: `ImpuestoInput`, `ImpuestoDetalle`, `CatalogoImpuestos`.
- `router.py`: `GET /catalogo`, `GET /{id}`, `POST`, `PUT /{id}`,
  `DELETE /{id}`. Se actualiza el comentario "GET only" (005 FR-008
  reemplazado por 033).
- El middleware global ya rechaza escrituras del rol `Lectura` (FR-006).

## Frontend

- `services/impuestosApi.ts`: tipos y llamadas nuevas.
- `components/impuestos/ImpuestoForm.tsx`: formulario de alta/edición.
- Rutas `app/finanzas/impuestos/nueva` y `app/finanzas/impuestos/[id]/editar`.
- Listado: botón "Nueva boleta" (envuelto en `SoloLectura`) y fila con
  enlace a edición.

## Datos

Sin cambios de esquema: usa `dbo.Impuestos` tal como está
(`Fecha`, `IdOrganismo`, `IdTipoImpuesto`, `[Periodo liquidado]`,
`[Numero de documento]`, `Importe`, `[Documento Original]`).

## Verificación

Tests unitarios del repositorio (catálogo, validación, duplicado, baja
bloqueada) con mocks; suite completa; build del frontend.
