# Quickstart: Migración histórica de Cajas Giamigli

## Prerrequisitos

- Backup verificado de `WC` (Constitución, Principio II — la migración hace un `ALTER TABLE` y bulk inserts).
- `Cajas Giamigli.xlsx` accesible en `C:\Users\Sergio\Documents\La Herencia\Administracion y gestion\Cuentas a pagar\`.
- `openpyxl` instalado en el entorno del backend.
- Los 7 movimientos ya cargados a mano el 2026-09-29/30 (El Luchador ×2, GMRA SA, Coto ×2, DER S.A.) siguen en `WC` — son la prueba viva de que la deduplicación funciona.

## Paso 1 — Esquema

```powershell
cd backend
.venv\Scripts\python.exe -m scripts.crear_tablas_cajas_efectivo
```

**Esperado**: confirma el `ALTER` de `MovimientosCuentaSocio` (o dice que ya existía) y la creación de `MovimientosCajaEfectivo`/`MigracionCajasGiamigliRevision`.

## Paso 2 — Migrar las 4 cuentas de socios

```powershell
.venv\Scripts\python.exe -m scripts.migracion_cajas_giamigli.migrar_socios
```

**Validación (spec SC-001)**: para cada socio, el script imprime el saldo final en pesos/USD/Kg carne. Comparar contra la planilla:

| Socio | Saldo pesos (col. N) | Saldo Kg carne (col. K) | Saldo USD (col. L) |
|---|---|---|---|
| Sergio | *(abrir `Cuenta Sergio`, última fila con datos)* | | |
| Lucy | | | |
| Cond LSC | | | |
| Ceci | | | |

Diferencia esperada: menor a $1 / 0,01 Kg / 0,01 USD por cuenta. Si no coincide, **no continuar** — revisar `MigracionCajasGiamigliRevision` para esa hoja antes de seguir.

**Validación (spec SC-003, deduplicación)**: confirmar que los 7 movimientos cargados a mano no se duplicaron:

```sql
SELECT IdSocio, Motivo, Importe, COUNT(*)
FROM dbo.MovimientosCuentaSocio
WHERE Usuario IN (
    'fix-el-luchador-compra-particular', 'fix-el-luchador-pago-lucy',
    'fix-coto-gmra-compra-particular', 'fix-der-bateria-fiesta'
)
GROUP BY IdSocio, Motivo, Importe
HAVING COUNT(*) > 1
```

**Esperado**: 0 filas.

## Paso 3 — Migrar la caja de Giamigli SA

```powershell
.venv\Scripts\python.exe -m scripts.migracion_cajas_giamigli.migrar_caja_giamigli_sa
```

**Validación (spec SC-002)**: comparar el saldo final impreso contra la última fila de la hoja `Caja Efectivo Pesos` (columna Saldo).

```
GET /api/cajas-efectivo/giamigli-sa/saldo
GET /api/cajas-efectivo/giamigli-sa/movimientos?page=1&pageSize=20
```

## Paso 4 — Migrar la caja chica del campo

```powershell
.venv\Scripts\python.exe -m scripts.migracion_cajas_giamigli.migrar_caja_chica_campo
```

**Validación**: comparar contra la última fila de `Caja chica campo` (columna Saldo).

```
GET /api/cajas-efectivo/campo-chica/saldo
GET /api/cajas-efectivo/campo-chica/movimientos?page=1&pageSize=20
```

## Paso 5 — Revisar la cola de casos pendientes (spec SC-004)

```
GET /api/migracion-cajas-giamigli/revision?resuelto=false
```

**Esperado**: cada fila de la planilla con fecha o importe faltante aparece acá con su motivo — ninguna se perdió en silencio. Revisar a mano cada caso contra la fila real del Excel (`Hoja` + `NumeroFila`).

## Paso 6 — Verificación end-to-end en la UI

1. Abrir `/finanzas/cuentas-socios/{idSocio}` para Lucy → confirmar que aparecen los movimientos migrados junto a los 7 ya cargados a mano, con columnas de USD y Kg de carne, sin duplicados visibles.
2. Abrir `/finanzas/cajas-efectivo/giamigli-sa` y `/finanzas/cajas-efectivo/campo-chica` → confirmar historial y saldo.
3. Confirmar que **ningún** dato de `Compras`, `Tarjetas_Resumenes_Lineas_Compras` o `Pagos efectivo` cambió (spec FR-010) — comparar conteos de filas de esas tablas antes/después de la migración.

## Éxito (spec SC-005)

Sergio puede abrir `/finanzas/cuentas-socios/2` (Lucy) y responder "¿cuánto le debe la empresa a Lucy hoy?" mirando únicamente el sistema — sin abrir `Cajas Giamigli.xlsx`.
