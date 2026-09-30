# Phase 0 Research: Migración histórica de Cajas Giamigli

## 1. Estructura real del archivo fuente (confirmada por inspección directa, 2026-09-29/30)

**Decision**: usar `openpyxl` en modo `data_only=True` para leer valores calculados (no fórmulas) de las 6 hojas relevantes de `C:\Users\Sergio\Documents\La Herencia\Administracion y gestion\Cuentas a pagar\Cajas Giamigli.xlsx`.

**Rationale**: las hojas de socios (`Cuenta Sergio`, `Cuenta Lucy`, `Cuenta Cond LSC`, `Cuenta Ceci`) comparten una estructura idéntica confirmada por inspección:

| Col | Contenido |
|---|---|
| A | Fecha |
| B | Proveedor / Servicio |
| C | Detalle |
| D | Nro. Documento |
| E–G | Debe: AR$, Kg. Carne, Dólares |
| H–J | Haber: AR$, Kg. Carne, Dólares |
| K–L | Saldos acumulados: Kg. Carne, Dólares |
| M | Forma Pago |
| N | Saldo (+ A Favor del socio / − A Favor Giamigli), solo en pesos |

Fila 1 tiene además la celda de "Deuda Actualizada" con una fórmula que referencia un libro externo (ver §2). Fila 2 es el encabezado. Los datos empiezan en fila 3.

`Caja Efectivo Pesos` (futura `MovimientosCajaEfectivo` con `Caja='GiamigliSA'`) tiene: Fecha, Concepto, Cuenta (Blue/White), Razón Social, PC, Nro. Documento, Importe (con signo: negativo = egreso), Saldo, Recuento — 1.841 filas, 2011-2026.

`Caja chica campo` (futura `MovimientosCajaEfectivo` con `Caja='CampoChica'`) tiene: Fecha, Proveedor/Servicio, Detalle, Debe, Haber, Forma Pago, Saldo — ~95 filas, 2020-2026.

**Alternatives considered**: parsear con `pandas.read_excel` — descartado porque no da acceso directo a fórmulas/valores cacheados de libros externos si hiciera falta inspeccionarlos más adelante, y el proyecto no tiene `pandas` como dependencia ya aprobada; `openpyxl` es más liviano y ya se usó ad-hoc en esta misma sesión para explorar el archivo.

## 2. La "Deuda Actualizada" y por qué queda fuera de alcance

**Decision**: no importar `Bancos y finanzas\Parametros financieros.xlsx` ni replicar la fórmula de revalorización en esta iteración (confirmado con el usuario en `/speckit-clarify`).

**Rationale**: la celda `C1` de cada hoja de socio calcula:

```
Deuda Actualizada = (saldo acumulado Kg. Carne × Índice Novillo de hoy)
                   + (saldo acumulado Dólares × Dólar BNA de hoy)
```

usando `VLOOKUP` contra las hojas `Indice Novillo` y `Dolar BNA` de un archivo externo vinculado (`Parametros financieros.xlsx`, confirmado vía `xl/externalLinks/externalLink1.xml` dentro del `.xlsx`: 935 filas de Índice Novillo desde 2020, ~5.333 filas de Dólar BNA desde 2010). Es decir, la columna en pesos (E/H/N) es el valor **nominal histórico** al momento de cada movimiento; el valor real que le importa al negocio hoy surge de revalorizar los saldos de Kg de carne y USD (su verdadera reserva de valor) a la cotización del día. Replicar esto correctamente requeriría importar ~6.000 filas adicionales de series de precios y construir un motor de "precio más cercano a una fecha" — una pieza de arquitectura separada y no trivial, que el usuario decidió diferir explícitamente.

**Alternatives considered**: importar solo el último valor de cada índice (snapshot fijo) — rechazado porque dejaría de reflejar la revalorización diaria real, dando una falsa sensación de estar completo cuando en realidad sería un número congelado el día de la migración.

## 3. Regla de deduplicación (spec Clarifications)

**Decision**: dos movimientos se consideran "el mismo" cuando coinciden **fecha + proveedor/contacto + importe** (en la moneda correspondiente), con tolerancia de redondeo de $0,01.

**Rationale**: es la regla más simple posible y es, de hecho, la que ya se usó para confirmar a mano los 7 movimientos cargados hoy antes de esta migración (El Luchador ×2, GMRA SA, Coto ×2, DER S.A.) — encontrados originalmente cruzando exactamente esos tres campos contra `Tarjetas_Resumenes_Lineas_Compras`/`Pagos efectivo`. Para los socios, el universo de "ya cargado a mano" es chico y conocido (7 filas) — se resuelve con una consulta directa a `MovimientosCuentaSocio` por `(IdSocio, Fecha, Importe)` antes de insertar cada fila migrada. Para la caja de Giamigli SA (que se solapa con `Pagos efectivo`, FR-008), la coincidencia se hace resolviendo el proveedor de la fila del Excel a un `IdContacto` (por nombre exacto contra `dbo.Contactos`) y comparando `(IdContacto, Fecha, Importe)` contra `Pagos efectivo`.

**Alternatives considered**: fecha+importe sin proveedor — rechazado por el usuario en clarify (más riesgo de fusionar movimientos distintos); revisión manual caso por caso sin regla automática — rechazado por el usuario (demasiado lento para ~7.000 filas).

## 4. Filas incompletas, vacías y "casos a revisar"

**Decision**: una fila se migra automáticamente solo si tiene fecha Y al menos un importe (pesos, USD o Kg de carne) no nulo/no cero. Toda fila con fecha pero sin ningún importe, o con importe pero sin fecha, se registra en `MigracionCajasGiamigliRevision` con el motivo y los valores crudos originales, sin insertar ningún movimiento a partir de ella. Una fila completamente vacía (todas las celdas relevantes `None`) se ignora en silencio (no genera caso a revisar) — se confirmó este patrón en la hoja `Cuenta Ceci`, que tiene filas vacías después del último movimiento real.

**Rationale**: FR-005/FR-006 de la spec, y el edge case ya confirmado por inspección directa del archivo.

## 5. Proveedores no reconocidos (incluye "XXXXXXXXX")

**Decision**: el nombre de proveedor/servicio de la planilla se guarda tal cual en `Motivo` de `MovimientosCuentaSocio` (o `Concepto` de `MovimientosCajaEfectivo`) sin intentar resolverlo a un `IdContacto` para las cuentas de socios (no hace falta, FR-001 no lo requiere). Para la caja de Giamigli SA sí se intenta resolver a `IdContacto` (por nombre exacto) únicamente para la deduplicación contra `Pagos efectivo` (FR-008); si no resuelve a ningún contacto, la fila se migra igual como movimiento nuevo de la caja (no como caso a revisar) — la ausencia de contacto no es una ambigüedad, es la norma para la mayoría de las filas de caja chica.

**Rationale**: edge case confirmado en spec; ya existe un contacto literal `"XXXXXXXXX"` (`IdContacto=97`) en el sistema — no hace falta lógica especial, se trata como cualquier otro nombre.

## 6. Cambio de esquema en `MovimientosCuentaSocio`

**Decision**: `ALTER TABLE` aditivo (no se toca ninguna fila existente): agregar `ImporteUSD money NOT NULL DEFAULT 0` y `ImporteKgCarne decimal(14,3) NOT NULL DEFAULT 0`; reemplazar el `CHECK (Importe > 0)` existente por `CHECK (Importe > 0 OR ImporteUSD > 0 OR ImporteKgCarne > 0)`. La columna `Medio` ya existente (nvarchar(60), NULL) se reutiliza para la "Forma Pago" de la planilla — no hace falta una columna nueva.

**Rationale**: evita introducir columnas nulas y lógica de "SUM con NULL" en los cálculos de saldo; `money`/`decimal` son los mismos tipos ya usados en el resto del esquema (`Importe money` en `Pagos efectivo`, `Tarjetas_Resumenes_Lineas_Compras`, etc.) — consistencia con el resto de `WC`.

**Alternatives considered**: tabla separada `MovimientosCuentaSocioDivisas` (1:1 con `MovimientosCuentaSocio`) — rechazada por complejidad innecesaria; el 100% de los movimientos migrados van a tener como máximo estas 3 componentes, no hace falta normalizar a una tabla aparte.

## 7. Modelo de datos para las 2 cajas nuevas

**Decision**: una única tabla `MovimientosCajaEfectivo` con columna discriminadora `Caja` (`'GiamigliSA'` | `'CampoChica'`), `Importe money NOT NULL` con signo (positivo = ingreso, negativo = egreso) — normalizando la representación distinta de cada hoja origen (`Caja Efectivo Pesos` ya viene con signo; `Caja chica campo` viene en columnas `Debe`/`Haber` separadas, se convierte a `Importe = Haber - Debe` al migrar). El saldo se calcula on-the-fly con una suma acumulada ordenada por `(Fecha, IdMovimiento)`, mismo patrón que `vw_MovimientosCuenta_Saldo` (004) pero sin necesidad de una vista SQL nueva dado el volumen bajo (recalcular en Python al leer es suficiente, ver `cuentas_socios.calcular_saldo` como precedente de patrón "sumar todo lo vigente cada vez").

**Rationale**: ambas cajas son, en esencia, el mismo concepto (una caja de efectivo con historial y saldo) con distinto conjunto de columnas de contexto (`Cuenta` Blue/White solo aplica a Giamigli SA) — separarlas en 2 tablas duplicaría columnas y consultas sin necesidad real.

## 8. Idempotencia de los scripts de migración

**Decision**: cada script verifica antes de insertar (`SELECT` por la clave de deduplicación de §3) y es seguro re-correrlo completo las veces que haga falta sin duplicar — mismo patrón que `cargar_boletas_uatre_faltantes.py` (`WHERE Importe IS NULL` como guarda) y que los scripts de conciliación masiva de esta sesión (verificación post-insert).

**Rationale**: una migración de ~7.000 filas contra `WC` real puede fallar a mitad de camino (timeout, conexión); sin esta propiedad, cada reintento arriesgaría duplicar lo ya insertado.
