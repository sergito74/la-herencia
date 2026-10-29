# Validación 045 — Trabajos eventuales y Adicional de Sierra

**Fecha**: 2026-10-29  
**Responsable**: Gemini  
**Alcance**: Módulo Personal (`/personal/trabajos-eventuales` y `/personal/remuneraciones`)

---

## 1. Importación de la Planilla Real e Integridad de Datos

- **Archivo fuente**: `Documents/La Herencia/Administracion y gestion/Personal/Planilla trabajos eventuales.xlsx`
- **Hash SHA-256**: `4c333448fbce8e3444172fb111a8357a6d9f5c70548bd09272e230085f1ca5c6`
- **Copia de resguardo verificada**: `backups/trabajos-eventuales-045/fuente-4c333448fbce.xlsx`
- **Respaldo previo de `WC`**:
  `C:\Program Files\Microsoft SQL Server\MSSQL17.SQLEXPRESS\MSSQL\Backup\WC_trabajos-eventuales-045_20261029_162501_559348.bak`
- **Total de trabajos en base**: **78**
  - **75 históricos** previamente importados (total $ 2.500.558,00).
  - **3 nuevos trabajos pendientes** incorporados el 29/10/2026:
    - Armando Mori (2026-10-30, Vacunación y yerra, 1 día): $ 99.400,00 (Pendiente)
    - Diego Pardo (2026-10-29, Vacunación y yerra, 2 días): $ 158.100,00 (Pendiente)
    - Agustín Torrontegui (2026-10-29, Vacunación y yerra, 2 días): $ 135.700,00 (Pendiente)
- **Total acumulado general**: **$ 2.893.758,00**
- **Distribución de vínculos**:
  - Total vinculado a remuneraciones: $ 1.737.133,00 (35 vínculos exactos)
  - Sin vincular: $ 1.156.625,00 (incluye los 3 pendientes de fin de octubre 2026)
- **Idempotencia**: Al re-ejecutar `scripts.trabajos_eventuales_045`, la cantidad de registros nuevos insertados es **0** y no se generan duplicados.

---

## 2. Cobertura de Pruebas Automatizadas

Se ejecutó la suite de tests unitarios y de contrato:
```bash
python -m pytest tests/test_trabajos_eventuales.py tests/contract/test_trabajos_eventuales_api.py tests/test_adicional_sierra.py
```
- **Resultado**: 26 passed en 3.74s
  - `tests/test_trabajos_eventuales.py`: 15 passed (cálculos, redondeos a 5/100, restricciones, auditoría, vínculos atómicos)
  - `tests/contract/test_trabajos_eventuales_api.py`: 5 passed (contratos REST, filtros, resumen, ordenamiento)
  - `tests/test_adicional_sierra.py`: 6 passed (cálculo de 30% adicional + 8.5% feriados sobre neto, redondeo a centena, persistencia)

---

## 3. Verificación de Compilación Frontend

Se ejecutó el build de producción Next.js:
```bash
cd frontend && npm run build
```
- **Resultado**: Compilación limpia y exitosa (`Compiled successfully`).
- Rutas generadas:
  - `/personal/trabajos-eventuales`
  - `/personal/remuneraciones` (con componente `AdicionalSierra`)
- Navegación bidireccional comprobada: desde Trabajos Eventuales a Recibos de Sueldo y viceversa.

