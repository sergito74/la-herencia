# Quickstart: Validar el módulo de cuentas corrientes (solo lectura)

## Prerrequisitos

- DSN `SQL_LaHerencia` accesible.
- Módulos de compras (`specs/002-compras`) y tesorería (`specs/003-tesoreria`) implementados o, como mínimo, sus tablas de origen accesibles — la resolución de `Origen`/`IdOrigen` los referencia.

## 1. Verificar los valores reales del campo `Origen`

```sql
SELECT DISTINCT Origen FROM dbo.vw_MovimientosCuenta_Base;
```

Confirmar que los valores coinciden con lo asumido en `data-model.md` ("Compra", "Tesorería" u otros) antes de implementar `origen_resolver.py`. Si hay más variantes (por ejemplo, un valor distinto por banco), actualizar `data-model.md` y `contracts/cuentas-corrientes-api.md`.

## 2. Levantar el backend

```powershell
cd backend
uvicorn src.main:app --reload --port 8000
```

## 3. Consultar saldo y movimientos de un contacto conocido

```powershell
curl "http://localhost:8000/api/cuentas-corrientes/contactos?q=Rutas Sur"
curl "http://localhost:8000/api/cuentas-corrientes/contactos/42/saldo"
curl "http://localhost:8000/api/cuentas-corrientes/contactos/42/movimientos"
```

Verificar que el saldo coincide con lo ya validado en el prototipo (`memory.md`, sección 14: "Proveedor Rutas Sur Atlantico S.A. con 4 movimientos de cuenta corriente").

## 4. Verificar los 3 estados de origen

Revisar la respuesta de movimientos y confirmar que aparecen ejemplos (o se pueden forzar con otros contactos) de:
- `origen.tipo = "compra"` con referencia a una compra real.
- `origen.tipo = "tesoreria"` con referencia a un movimiento real.
- `origen.tipo = "no_disponible"` cuando `IdOrigen` no está cargado.

## 5. Confirmar que no hay imputación en las respuestas

Revisar que ninguna respuesta de este módulo incluye rubro/centro de costo/destino (FR-009) — si aparece, es una regresión respecto a la decisión de que compras es la única fuente de verdad de imputación.

## 6. Ejecutar los contract tests

```powershell
cd backend
pytest tests/contract/test_cuentas_corrientes_api.py -v
```

## 7. Frontend

```powershell
cd frontend
npm run dev
```

Verificar en la UI: búsqueda y filtro por tipo de contacto (US3), saldo y movimientos (US1), navegación hacia origen con los 3 estados (US2).

## Criterios de éxito de esta validación

Corresponde a `spec.md`: SC-001 (saldo en <30s), SC-002 (origen siempre explícito), SC-003 (saldo coincide con la vista SQL), SC-004 (sin imputación propia), SC-005 (sin escritura real).
