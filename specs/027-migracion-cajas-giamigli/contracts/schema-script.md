# Schema/Script Contract: Migración histórica de Cajas Giamigli

## 1. `backend/scripts/crear_tablas_cajas_efectivo.py`

Idempotente (mismo patrón que `crear_tablas_cuentas_socios.py`, `IF OBJECT_ID(...) IS NULL` / chequeo de columna antes de `ALTER`):

1. `ALTER TABLE dbo.MovimientosCuentaSocio` — agrega `ImporteUSD`, `ImporteKgCarne`; reemplaza el `CHECK` de importe (ver data-model.md §1). Verificar antes de correr: `IF COL_LENGTH('dbo.MovimientosCuentaSocio','ImporteUSD') IS NULL`.
2. `CREATE TABLE dbo.MovimientosCajaEfectivo` (data-model.md §2).
3. `CREATE TABLE dbo.MigracionCajasGiamigliRevision` (data-model.md §3).

Requiere backup verificado de `WC` antes de correr (Constitución, Principio II — cambio de esquema).

## 2. `backend/scripts/migracion_cajas_giamigli/lector_excel.py`

Función pública: `leer_hoja_socio(ruta_excel: str, nombre_hoja: str) -> tuple[list[FilaSocio], list[CasoARevisar]]` y `leer_hoja_caja(ruta_excel: str, nombre_hoja: str, caja: str) -> tuple[list[FilaCaja], list[CasoARevisar]]`.

- No escribe nada — solo parsea y clasifica. Los scripts `migrar_*.py` son los que insertan.
- `FilaSocio`: fecha, proveedor, detalle, importe_pesos, importe_usd, importe_kg_carne, forma_pago, tipo (`AsignacionGasto` si hay valor en Debe, `Devolucion` si hay valor en Haber — ver research.md §1 para el mapeo de columnas).
- `FilaCaja`: fecha, concepto/proveedor, detalle, importe (con signo, normalizado según research.md §7), cuenta (solo Giamigli SA), forma_pago (solo campo chica), numero_documento.
- `CasoARevisar`: hoja, numero_fila, motivo, datos_crudos (dict serializable a JSON).
- Filas completamente vacías: se descartan sin generar `CasoARevisar` (research.md §4).

## 3. `backend/scripts/migracion_cajas_giamigli/dedup.py`

- `ya_existe_movimiento_socio(id_socio: int, fecha: date, importe_pesos: float) -> bool` — consulta `MovimientosCuentaSocio` por `(IdSocio, Fecha, Importe)` con tolerancia $0,01, `Anulada = 0`.
- `resolver_contacto_por_nombre(nombre: str) -> int | None` — consulta `dbo.Contactos` por `[Razon Social]` exacto (case-insensitive).
- `ya_existe_pago_efectivo(id_contacto: int, fecha: date, importe: float) -> bool` — consulta `Pagos efectivo` por `(IdContacto, Fecha, [Importe imputado])` con tolerancia $0,01.

## 4. `backend/scripts/migracion_cajas_giamigli/migrar_socios.py`

- Recorre las 4 hojas de socios, usa `lector_excel.leer_hoja_socio` + `dedup.ya_existe_movimiento_socio`.
- Inserta en `MovimientosCuentaSocio` (`Tipo`, `Importe`, `ImporteUSD`, `ImporteKgCarne`, `Fecha`, `Medio`=forma_pago, `Motivo`="{proveedor} — {detalle}", `Usuario='migracion-cajas-giamigli'`).
- Inserta cada `CasoARevisar` en `MigracionCajasGiamigliRevision`.
- Al final, imprime por socio: total de filas leídas, migradas, deduplicadas (ya existían), y a revisar — y el saldo resultante en las 3 monedas, para comparar a mano contra la planilla (spec SC-001).

## 5. `backend/scripts/migracion_cajas_giamigli/migrar_caja_giamigli_sa.py`

- Usa `lector_excel.leer_hoja_caja(..., caja='GiamigliSA')`.
- Para cada fila, intenta `dedup.resolver_contacto_por_nombre` sobre el proveedor; si resuelve y `dedup.ya_existe_pago_efectivo` es `True`, no inserta (ya representado) y lo cuenta como "duplicado detectado", pero no lo trata como caso a revisar (FR-008: coincidencia clara, se omite en silencio del lado de la caja nueva — el movimiento real ya vive en `Pagos efectivo`). Si no resuelve a ningún contacto, o resuelve pero no hay coincidencia de importe/fecha, inserta como movimiento nuevo de la caja.
- Imprime el mismo resumen que `migrar_socios.py`, más el saldo final de la caja (spec SC-002).

## 6. `backend/scripts/migracion_cajas_giamigli/migrar_caja_chica_campo.py`

- Usa `lector_excel.leer_hoja_caja(..., caja='CampoChica')`. Sin deduplicación contra otras tablas (no existe overlap conocido) — solo evita re-insertar si el script se corre dos veces (mismo criterio de idempotencia por `(Caja, Fecha, Importe, Concepto)`).
- Mismo resumen final.

## Orden de ejecución

1. Backup de `WC` verificado.
2. `python -m scripts.crear_tablas_cajas_efectivo`
3. `python -m scripts.migracion_cajas_giamigli.migrar_socios`
4. `python -m scripts.migracion_cajas_giamigli.migrar_caja_giamigli_sa`
5. `python -m scripts.migracion_cajas_giamigli.migrar_caja_chica_campo`
6. Comparar a mano los saldos impresos contra la planilla (quickstart.md).

Cada script puede re-correrse solo o en cualquier orden relativo a los otros dos `migrar_*` (no dependen entre sí) sin duplicar datos.
