# Quickstart: Alta de liquidación de remuneraciones

## Prerrequisitos

- Sin cambio de esquema (la tabla y la columna `Recibo` ya existen) — no requiere backup previo específico de esta feature, más allá de la disciplina normal de escritura contra `WC`.
- Empleado de prueba ya existente como Contacto tipo `Empleado` (ej. IdContacto 46, "Armando Oscar Mori" — usado en la validación real de `buscar_archivo_recibo` en la sesión anterior).

## Escenario 1 — Cargar una liquidación nueva sin recibo

```
POST /api/remuneraciones
{ "idContacto": 376, "fechaPago": "2026-09-30", "periodoLiquidado": "Septiembre 2026",
  "sueldoBasico": 85096.38, "jubilacion": 18631.02, "obraSocial": 5081.19, "aporteSindical": 3471.43 }
```

**Esperado**: `201`, con `idSalario` nuevo y `importeNeto = 85096.38 - 18631.02 - 5081.19 - 3471.43 = 57912.74`. La liquidación aparece de inmediato en `GET /api/remuneraciones?empleado=Armando` con ese mismo importe (FR-014/FR-015) y `recibo: null`.

## Escenario 2 — Adjuntar el PDF después

```
POST /api/remuneraciones/{idSalario}/recibo   (multipart, archivo=recibo_septiembre.pdf)
```

**Esperado**: `200`, `recibo: "Personal\\Recibos\\2026\\2026 09 Armando Oscar Mori.pdf"`. El archivo existe en disco en esa ruta relativa a `CARPETA_RECIBOS`. El link "Recibo" del listado existente (`GET /api/remuneraciones/{idSalario}/recibo`) lo abre sin cambios adicionales — usa la columna `Recibo` recién escrita, con prioridad sobre el matching por archivo.

## Escenario 3 — Intentar cargar un duplicado

Repetir el `POST` del Escenario 1 con el mismo `idContacto` y el mismo `periodoLiquidado`, sin `confirmarDuplicado`.

**Esperado**: `409` con el `idSalarioExistente` de la liquidación del Escenario 1 — no bloquea, solo advierte (FR-004). Reintentar con `"confirmarDuplicado": true` debe crear una segunda liquidación igual, sin error — mismo criterio que los pagos "Extra" reales del histórico.

## Escenario 4 — Adjuntar un archivo que no es PDF

```
POST /api/remuneraciones/{idSalario}/recibo   (multipart, archivo=foto.jpg)
```

**Esperado**: `400`, mensaje explícito de que solo se aceptan PDF — no se escribe nada en `Recibo` ni se guarda ningún archivo (FR-008).

## Escenario 5 — Verificar que el bug del listado quedó corregido

```
GET /api/remuneraciones?empleado=Armando&periodoLiquidado=Septiembre 2026
```

**Esperado**: el campo `importe` de esa liquidación es `57912.74` (el neto), no `112280.02` (la suma sin restar descuentos que devolvía `_IMPORTE_SQL` antes de esta feature).

## Escenario 6 — Rol de solo lectura

Con una sesión de un usuario con rol `SoloLectura`: el botón "Nueva liquidación" y "Adjuntar recibo" no aparecen (o están deshabilitados) en `/personal/remuneraciones` — mismo comportamiento ya verificado en Cuentas de Socios.
