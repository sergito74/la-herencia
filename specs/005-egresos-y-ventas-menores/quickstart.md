# Quickstart: Validar Impuestos, Remuneraciones, Arrendamientos y Ventas de Hacienda

## Prerrequisitos

- DSN `SQL_LaHerencia` accesible.
- `specs/004-cuentas-corrientes` implementado (ya lo está) — este módulo amplía su `origen_resolver.py`.

## 1. Confirmar el esquema real (ya verificado en research.md, repetir si cambia la base)

```sql
SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME IN
  ('Impuestos','Tipo Impuesto','Retenciones','Remuneraciones','Pagos Remuneraciones',
   'Alquileres','Detalles del alquiler','Detalle Cobro Alquiler',
   'Venta Hacienda','Det_Ventas Hacienda','Retenciones Ventas Hacienda','Tipo Hacienda')
ORDER BY TABLE_NAME, ORDINAL_POSITION;
```

## 2. Levantar el backend

```powershell
cd backend
uvicorn src.main:app --reload --port 8000
```

## 3. Consultar cada dominio contra datos reales conocidos

```powershell
curl "http://localhost:8000/api/impuestos?organismo=ARBA"
curl "http://localhost:8000/api/impuestos/retenciones"
curl "http://localhost:8000/api/remuneraciones"
curl "http://localhost:8000/api/arrendamientos"
curl "http://localhost:8000/api/ventas-hacienda"
curl "http://localhost:8000/api/ventas-hacienda/retenciones"
```

Verificar contra los casos reales ya confirmados en `research.md`: contacto 12 = "ARBA" (Impuestos), 5 filas en `Alquileres`, ventas de hacienda con más de un comprador por venta (ej. `IdVenta` con líneas de `IdComprador` distintos).

## 4. Verificar la ampliación de `origen_resolver.py`

```powershell
curl "http://localhost:8000/api/cuentas-corrientes/contactos/72/movimientos"
```

Confirmar que un movimiento con `Origen = "Impuestos"` para el contacto 72 (caso real usado en `research.md`) resuelve a `origen.tipo = "impuesto"`, no a `"fuera_de_alcance"`. Repetir con contactos conocidos para `Origen` en `{Retenciones, Remuneraciones, Alquileres, Ret. Ventas Hacienda}`.

## 5. Confirmar que `Ret. IVA Granos` sigue `fuera_de_alcance`

```powershell
curl "http://localhost:8000/api/cuentas-corrientes/contactos/{id}/movimientos"
```

para un contacto con un movimiento `Origen = "Ret. IVA Granos"` — MUST seguir devolviendo `origen.tipo = "fuera_de_alcance"` (dominio de Agricultura, fuera de este spec).

## 6. Confirmar que no hay imputación cruzada

Revisar que ninguna respuesta de estos módulos incluye rubro/centro de costo/destino (FR-007) — si aparece, es una regresión.

## 7. Ejecutar los contract tests

```powershell
cd backend
pytest tests/contract/test_impuestos_api.py tests/contract/test_remuneraciones_api.py tests/contract/test_arrendamientos_api.py tests/contract/test_ventas_hacienda_api.py tests/contract/test_cc_origen.py -v
```

## 8. Frontend

```powershell
cd frontend
npm run dev
```

Verificar en la UI: navegación desde `NavHeader`/home hacia cada uno de los 4 módulos nuevos, listados con estado vacío explícito, y navegación desde un movimiento de cuentas corrientes hacia cada uno de los 5 nuevos tipos de origen.

## Criterios de éxito de esta validación

Corresponde a `spec.md`: SC-001 (detalle en <30s), SC-002 (5 de 6 estados `fuera_de_alcance` resueltos), SC-003 (sin escritura real), SC-004 (campos mínimos sin errores, incluyendo casos sin contacto).
