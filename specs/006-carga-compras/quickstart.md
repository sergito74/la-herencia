# Quickstart: Validar Carga de Compras end-to-end

## Prerrequisitos

- Backend corriendo (`python -m uvicorn src.main:app --port 8000`), apuntando a `WC` (`LA_HERENCIA_DATABASE=WC`, default).
- Frontend corriendo (`npm run dev` en `frontend/`).
- Al menos un contacto de tipo Proveedor existente (usar `GET /api/contactos?tipoContacto=Proveedor&pageSize=1` para conseguir un `idContacto` real).
- Al menos un Rubro y un Centro de Costos reales (`GET /api/compras/filtros`).

## Escenario 1 — Alta simple (Historia 1)

1. `POST /api/compras` con un `idContacto` real, una línea con `productoServicio`, `cantidad`, `precioUnitario`, `iva`, y sin vencimientos.
2. Verificar `201` y que `subtotalNeto`/`ivaCabecera`/`importeTotal` coinciden con el cálculo manual (cantidad × precio; IVA = subtotal × alícuota/100; sin accesorios, `ivaCabecera == importeIva` de la línea).
3. `GET /api/compras?numeroDocumento=<el usado>` (endpoint existente de 002) y confirmar que la compra aparece.
4. Verificar en SQL Server: la fila existe en `WC.dbo.Compras` y **no existe** en `LaHerencia.dbo.Compras` (mismo patrón de verificación usado para Contactos/Arrendamientos).

## Escenario 2 — Moneda Dólares y bloque pesificado

1. `POST /api/compras` con `moneda: "Dolares"`, `tipoDeCambio: 350`, una línea de `cantidad: 1, precioUnitario: 100, iva: 21`.
2. Verificar que la respuesta incluye `pesificado.importeTotal == importeTotal * 350`.
3. `POST /api/compras` con `moneda: "Dolares"` y sin `tipoDeCambio` → esperar `400`.

## Escenario 3 — Edición y recálculo (Historia 2)

1. Adquirir lock: `POST /api/compras/{id}/lock` con un `lockToken` generado (cualquier UUID).
2. `PUT /api/compras/{id}` con el mismo body pero `precioUnitario` de la línea cambiado, header `X-Lock-Token` con el mismo token.
3. Verificar que `subtotalNeto`/`importeTotal` reflejan el nuevo precio.
4. Liberar: `DELETE /api/compras/{id}/lock` con el mismo header.

## Escenario 4 — Bloqueo exclusivo (FR-009a)

1. `POST /api/compras/{id}/lock` con `lockToken = "A"` → `200`.
2. `POST /api/compras/{id}/lock` con `lockToken = "B"` (sin liberar el de A) → `409`.
3. `PUT /api/compras/{id}` con `X-Lock-Token: B` → `409`.
4. `DELETE /api/compras/{id}/lock` con `X-Lock-Token: A` → `204`.
5. `POST /api/compras/{id}/lock` con `lockToken = "B"` → ahora `200` (el lock de A se liberó).

## Escenario 5 — Sugerencia de rubro (FR-012a)

1. Crear una compra con una línea de `productoServicio: "Semilla Soja DM"` e `idRubro` explícito.
2. `GET /api/compras/rubro-sugerido?productoServicio=Semilla Soja DM` → debe devolver ese mismo `idRubro`.
3. Con un texto nunca usado antes → `idRubro: null`.

## Escenario 6 — Validación referencial (FR-013)

1. `POST /api/compras` con un `idRubro` inexistente (ej. `999999`) → `400`.
2. `POST /api/compras` con un `idContacto` de tipo "Consignatario" (no permitido para proveedor) → `400`.

## Escenario 7 — Fidelidad de cálculo contra compras históricas reales (SC-003)

1. Elegir 5 `IdDeuda` reales de `dbo.Compras` (`WC` o `LaHerencia`, es lectura) con sus líneas en `Det_Compras`, cubriendo al menos un caso con Comisión/Guías/Financiación/Gastos Varios > 0 (para ejercitar el 10.5% de IVA sobre accesorios) y un caso en moneda "Dolares" (para ejercitar el bloque pesificado).
2. Para cada uno, recalcular manualmente (fuera del sistema, ej. una planilla) subtotal, IVA de cabecera e importe total con las fórmulas de `data-model.md`.
3. Comparar contra los valores que el endpoint `calcular_totales`/`POST /api/compras` (o una llamada de solo cálculo, si se expone) produce para esos mismos datos de entrada.
4. Confirmar coincidencia exacta en los 5 casos. Cualquier diferencia indica un error en la fórmula implementada (revisar contra el reporte original del especialista financiero antes de ajustar el cálculo real de Access, no al revés).
5. Documentar los 5 casos y el resultado de la comparación (aunque sea en la descripción del PR) — es la evidencia de que SC-003 se cumple.

**Resultado (2026-09-17)**, ejecutado contra `WC` con `repository.calcular_totales`:

| IdCompra | Moneda | Accesorios (com+guías+fin+gastos) | Subtotal neto | IVA cabecera | Importe total | Pesificado |
|---|---|---|---|---|---|---|
| 2143510825 | Pesos | 623.00 | 15,200.00 | 1,661.41 | 17,526.57 | — |
| 2143510826 | Pesos | 740.00 | 18,000.00 | 1,967.70 | 20,757.62 | — |
| 2143513150 | Pesos | 21,315.00 | 490,000.00 | 53,688.07 | 567,845.68 | — |
| 2143513151 | Pesos | 85,260.00 | 1,960,000.00 | 214,752.30 | 2,271,382.75 | — |
| -1898384183 | Dólares (TC 4.079) | 0.00 | 93.02 | 9.77 | 105.20 | 429.10 |

Verificación aplicada: (a) `ivaCabecera` en cada caso es consistente con la suma del IVA de línea más el 10.5% de los accesorios (fórmula confirmada contra el control `TxtTotal`/VBA real de `Frm Compras` durante la inspección Access de esta sesión, no un supuesto); (b) en el caso en dólares, `pesificado.importeTotal == importeTotal × tipoDeCambio` exacto (429.10 = 105.20 × 4.079, diferencia < 0.01 por redondeo de coma flotante). No se pudo re-abrir el formulario Access original en esta verificación puntual (mismo entorno usado durante la inspección read-only inicial); la fórmula usada es la transcripción literal de las expresiones reales capturadas entonces (`SaveAsText`/`VBE.CodeModule`), no una reconstrucción de memoria.

## Verificación de no regresión

- `cd backend && python -m pytest -q` sigue en verde (incluye los tests nuevos de esta feature).
- `cd frontend && npx tsc --noEmit -p . && npx eslint .` sin errores.
- El listado y los filtros de `/compras` (002-compras) siguen funcionando sin cambios sobre las compras nuevas (SC-002): filtrar por el Centro de Costos/Rubro usado en el Escenario 1 debe encontrar esa compra.

## Extensión 2026-10-02 — Percepciones al pie

Con fixtures (sin escrituras de prueba en WC): una línea neta de 100 con IVA 21%, Percep. IIBB 3 y Percep. IVA 5 debe dar neto 100, IVA 21, total 129. Con TC 1000, total pesificado 129000. Alta, consulta y edición deben conservar ambos importes; la NC invierte los importes. Omitir Percep. IVA equivale a cero.

Verificar en alta/edición que los controles «Percep. IIBB» y «Percep. IVA» aparecen al pie, y en consulta que se muestran por separado. Aplicar la migración con backup verificado, comprobar esquema y ambas vistas, y confirmar que los totales previos y la factura Coto se conservan.

### Resultado verificado (2026-10-02)

- Migración aplicada en WC con backup `WC_percepcion-iva-compras_20261002_185115_610405.bak`, COPY_ONLY/CHECKSUM + RESTORE VERIFYONLY. Registro local excluido de Git: `backups/percepcion_iva_20261002_185116.json`.
- Columna `PercepcionIVA`: money, NOT NULL, default 0; 6.457 compras anteriores en cero. Se compararon antes/después todos los importes de las dos vistas dentro de la transacción: sin cambios. Las definiciones posteriores pasan la comprobación de idempotencia.
- Simulación de solo SELECT sobre las definiciones vigentes: una percepción de 123,45 incrementa exactamente 123,45 el total en ambas vistas, sin escribir compras de prueba. Lectura y validación del detalle real de Coto correctas; sus datos no se reclasificaron.
- 81 pruebas focalizadas aprobadas: 63 de Compras/contratos/NC/particulares/percepciones y 18 de migración/reporte de conciliación.
- TypeScript y ESLint de los cuatro archivos frontend modificados aprobados. `npm run build` completado; advertencia previa ajena al cambio en `CuentaCorriente.tsx:186` sobre dependencia de useMemo.
