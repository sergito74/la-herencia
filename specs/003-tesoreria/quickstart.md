# Quickstart: Validar el módulo de tesorería (solo lectura)

## Prerrequisitos

- Módulo de compras (`specs/002-compras`) implementado o, como mínimo, su tabla `Compras` accesible — la referencia heurística lo necesita para funcionar.
- DSN `SQL_LaHerencia` accesible.
- Backend con `openpyxl` y `xlrd` instalados.
- Formato de archivos confirmado el 2026-09-16 (ver `research.md`/`data-model.md`): copias sanitizadas (sin datos reales de terceros) de un extracto Galicia (`.xlsx`) y uno de BNA (`.xls`) como fixtures de test.

## 1. Verificar esquema real de los medios menos documentados

```sql
SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'Pagos efectivo';
SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'Valores propios';
SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'Valores Recibidos';
SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'Tarjetas_Resumenes_Lineas';
```

Actualizar `data-model.md` con los campos reales antes de `/speckit-tasks`.

## 2. Levantar el backend y consultar un medio

```powershell
cd backend
uvicorn src.main:app --reload --port 8000
curl "http://localhost:8000/api/tesoreria/bna/movimientos?fechaDesde=2026-08-01"
```

Verificar que devuelve movimientos con la forma propia de BNA (concepto/importe), no forzada a la forma de Galicia.

## 3. Probar la referencia heurística

Tomar un `idMovimientoBNA` de un movimiento vinculado a un contacto con compras conocidas y consultar:

```powershell
curl "http://localhost:8000/api/tesoreria/bna/movimientos/<id>/referencia"
```

Verificar los tres estados posibles manualmente con distintos movimientos: `sin_coincidencia`, `coincidencia_unica`, `ambigua` (este último puede forzarse eligiendo un contacto con varias compras del mismo importe/fecha aproximada).

## 4. Probar la carga de Excel (sin persistencia)

```powershell
curl -F "archivo=@bna_ejemplo.xls" "http://localhost:8000/api/tesoreria/excel/validar"
curl -F "archivo=@galicia_ejemplo.xlsx" "http://localhost:8000/api/tesoreria/excel/validar"
```

Verificar:
- Con un archivo válido: `valido: true` y `movimientosPrevisualizados` con datos coherentes.
- Con un archivo con columnas alteradas: `valido: false` y un mensaje de error claro en `errores`.
- Confirmar contra la base (`SELECT COUNT(*) FROM ...`) que ningún movimiento se persistió como resultado de este paso.

## 5. Ejecutar los contract tests

```powershell
cd backend
pytest tests/contract/test_tesoreria_api.py -v
```

## 6. Frontend

```powershell
cd frontend
npm run dev
```

Verificar en la UI: selector de medio (US1), estados de referencia claros incluyendo ambigüedad (US2), carga de Excel con previsualización y aviso de que no persiste (US3).

## Criterios de éxito de esta validación

Corresponde a `spec.md`: SC-001 (consulta rápida por medio), SC-002 (estado de referencia siempre explícito, incluida ambigüedad), SC-003 (sin imputación mostrada en tesorería), SC-004 (previsualización de Excel <1 min), SC-005 (sin persistencia real desde este módulo).
