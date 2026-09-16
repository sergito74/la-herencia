# Quickstart: Validar el módulo de compras (solo lectura)

## Prerrequisitos

- DSN `SQL_LaHerencia` configurado y accesible (ver `memory.md`, sección 6).
- Backend Python con dependencias instaladas (`fastapi`, `pyodbc`, `pydantic`, `pytest`, `httpx`).
- Frontend Next.js con dependencias instaladas (`next`, `@tanstack/react-query`, `tailwindcss`).
- Acceso de solo lectura confirmado: ninguna credencial de escritura debe estar configurada en el entorno de este módulo.

## 1. Verificar el contrato contra el esquema real (antes de implementar)

Ejecutar SELECT de solo lectura para confirmar columnas asumidas en `data-model.md` (en particular, el nombre exacto de las columnas de centro de costo/destino en `Det_Compras`, y la estructura de `Rubros`):

```sql
SELECT COLUMN_NAME, DATA_TYPE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'Det_Compras';

SELECT TOP 5 * FROM dbo.Det_Compras;
SELECT TOP 5 * FROM dbo.Rubros;
```

Si los nombres reales difieren de los asumidos en `data-model.md`, actualizar `data-model.md` y `contracts/compras-api.md` antes de `/speckit-tasks`.

## 2. Levantar el backend

```powershell
cd backend
# instalar dependencias según el gestor de paquetes elegido en la implementación
uvicorn src.main:app --reload --port 8000
```

## 3. Ejecutar los contract tests (sin tocar la base real)

```powershell
cd backend
pytest tests/contract/test_compras_api.py -v
```

Resultado esperado: todos los tests pasan usando fixtures fijas, sin conexión a SQL Server real.

## 4. Validar contra datos reales (manual, solo lectura)

Con el backend corriendo contra el DSN real:

```powershell
curl "http://localhost:8000/api/compras?proveedor=Rutas Sur"
```

Verificar:
- Aparece "Rutas Sur Atlantico S.A." con sus compras (dato ya validado en el prototipo, ver `memory.md` sección 14).
- Tomar un `idCompra` del resultado y consultar:

```powershell
curl "http://localhost:8000/api/compras/<idCompra>"
curl "http://localhost:8000/api/compras/<idCompra>/trazabilidad"
```

Verificar que las líneas muestran imputación (`imputacion` con datos o `null` explícito, nunca omitido) y que la trazabilidad muestra movimientos o el estado "sin movimientos asociados".

## 5. Levantar el frontend

```powershell
cd frontend
npm run dev
```

Abrir el módulo de compras, repetir la búsqueda por "Rutas Sur" y confirmar en la UI:
- El listado y el estado vacío (US1, FR-012).
- El detalle con imputación por línea, incluyendo el caso de línea sin imputación (US2, FR-006).
- La referencia de trazabilidad hacia cuenta corriente/tesorería (US3, FR-008/FR-009).

## 6. Confirmar modo solo lectura

- Revisar que no exista ningún botón, formulario ni endpoint `POST`/`PUT`/`DELETE` en este módulo (FR-010).
- `next build` y la suite de contract tests del backend deben pasar sin advertencias de tipado.

## Criterios de éxito de esta validación

Corresponde a los Success Criteria de `spec.md`: SC-001 (búsqueda rápida), SC-002 (imputación siempre explícita), SC-003 (trazabilidad siempre explícita), SC-004 (sin escritura posible), SC-005 (listado paginado sin degradación).
