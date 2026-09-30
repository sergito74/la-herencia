# Research: Alta de liquidación de remuneraciones

## 1. Fórmula de importe neto — corregir el bug de `_IMPORTE_SQL`

**Decisión**: el importe neto de una liquidación es la suma de los conceptos de haberes menos la suma de los conceptos de descuento, ambos siempre almacenados en positivo:

- **Haberes** (suman): `Sueldo basico`, `Antiguedad`, `Adic futuros aumentos`, `Dia Gremio`, `Aguinaldo`, `Vacaciones`, `Ajuste`, `Ajuste No Remunerativo`, `Redondeo`, `Bonificacion adicional`.
- **Descuentos** (restan): `Jubilacion`, `Ley 19032`, `Obra Social`, `Obra Social Acuerdos`, `Servicio de Sepelio`, `Aporte Sindical`.

**Rationale**: es exactamente la fórmula que ya usa `vw_MovimientosCuenta_Base` (rama `Remuneraciones`, ver `scripts/crear_tabla_conciliaciones_tesoreria.py` y la definición actual de la vista) para calcular el crédito/débito que refleja en la cuenta corriente del empleado — la fuente de verdad ya existente y correcta. `_IMPORTE_SQL` (usado hoy por `search_remuneraciones`/`get_remuneracion_referencia` para el "Importe liquidado (calculado)" del listado) hace `SUM` de las mismas ~15 columnas con `+` para todas, sin restar los descuentos — confirmado contra datos reales 2026-09-30 (ej. Armando Oscar Mori, liquidación con `Sueldo basico=85096.38`, `Jubilacion=18631.02` guardado en positivo: la vista resta ese valor, `_IMPORTE_SQL` lo suma).

**Alternativas consideradas**:
- Dejar `_IMPORTE_SQL` como está y solo usar la fórmula correcta en el formulario nuevo → rechazado: dejaría dos "importes" distintos e inconsistentes para la misma liquidación en la misma pantalla (el listado seguiría mostrando un número sin sentido financiero), justo lo que la Constitución (Principio IV) pide evitar.
- Guardar los conceptos de descuento en negativo en la base (para que un `SUM` simple funcione) → rechazado: rompería la consistencia con ~600 registros históricos ya cargados en positivo, y con `vw_MovimientosCuenta_Base`, que ya asume signo positivo y resta explícitamente.

**Cómo aplicar**: se extrae una función pura `calcular_importe_neto(conceptos: dict) -> float` en `repository.py`, reusada tanto por `search_remuneraciones`/`get_remuneracion_referencia` (reemplazando `_IMPORTE_SQL` calculado en SQL por un cálculo en Python sobre las columnas ya traídas, o manteniendo el cálculo en SQL pero con signos correctos — a decidir en el detalle de implementación, no en el research) como por el nuevo endpoint de alta, para no duplicar la fórmula.

## 2. Almacenamiento del PDF y de su referencia

**Decisión**: el PDF se guarda en `CARPETA_RECIBOS/{año}/{año} {mes:02d} {Nombre Apellido}.pdf` (mismo formato ya usado como referencia por `buscar_archivo_recibo`, backlog post-025), y la ruta relativa (`Personal\Recibos\{año}\{archivo}.pdf`, sin la base) se escribe en `dbo.Remuneraciones.Recibo` — el mismo formato que ya usan ~262 registros históricos reales (confirmado 2026-09-30 leyendo la columna).

**Rationale**: reusa dos mecanismos que ya existen y ya funcionan en el listado de solo lectura (columna `Recibo` con prioridad, matching por archivo como fallback) — no inventa un tercer mecanismo. Nombrar el archivo con espacios (no `_` ni nombre pegado, a diferencia de gran parte del histórico) hace que el propio matching CamelCase lo encuentre trivialmente incluso si por algún motivo la columna `Recibo` quedara vacía.

**Alternativas consideradas**:
- Guardar la ruta completa (no relativa) en `Recibo` → rechazado: rompe el formato ya usado por ~262 registros reales, que el frontend ya sabe normalizar (`normalizarDocumentoOriginal` + `BASE_DOCUMENTOS_RECIBOS`).
- No escribir la columna `Recibo` y depender solo del matching por archivo → rechazado: la columna es más explícita y confiable (no depende de heurística), y es gratis escribirla ya que se conoce el nombre exacto del archivo recién creado.

**Cómo aplicar**: reusar `CARPETA_RECIBOS` de `repository.py` (ya existente) como base de escritura; el nombre de archivo debe evitar colisión si ya existe uno para ese empleado/período (ver §3).

## 3. Duplicados de empleado + período

**Decisión**: antes de guardar, el backend chequea si ya existe una fila en `dbo.Remuneraciones` con el mismo `IdContacto` y el mismo texto exacto de `Periodo liquidado` (comparación literal, sin normalizar mes/año). Si existe, el endpoint de alta responde con una advertencia (no un error 4xx duro) que el frontend muestra como confirmación explícita antes de reintentar el guardado con un flag `confirmarDuplicado=true`.

**Rationale**: el histórico real tiene duplicados legítimos del mismo empleado+período con texto distinto ("Diciembre 2021" y "Diciembre 2021 (Extra)") — normalizar el período perdería esa distinción real. Comparar el texto tal cual evita falsos positivos entre "Noviembre 2025" y "30/11/2025" (mismo mes, texto distinto, ambos reales) sin necesidad de parsear fechas en texto libre inconsistente.

**Alternativas consideradas**:
- Bloquear directamente el duplicado exacto → rechazado por decisión explícita del usuario en `/speckit-clarify` (spec FR-004): hay pagos "Extra" legítimos.
- Normalizar el período a mes/año antes de comparar → rechazado: perdería distinciones reales como "(Extra)"/"(Retroactivo)" que hoy conviven en el histórico con el mismo mes.

## 4. Patrón de subida de archivo (backend)

**Decisión**: reusar `fastapi.UploadFile` con `multipart/form-data`, mismo patrón ya implementado en `tesoreria/router.py` (`validar_excel`, `confirmar_excel`) para la carga de extractos — no hay que introducir ninguna librería nueva.

**Rationale**: patrón ya probado en producción para un flujo de subida de archivo real dentro de este mismo backend.

## 5. Permisos (`SoloLectura`)

**Decisión**: el botón "Nueva liquidación" (y el de adjuntar/reemplazar recibo) se envuelven en el componente `<SoloLectura>` ya existente (`frontend/src/components/auth/SoloLectura.tsx`), igual que en Cuentas de Socios (`AsignarGastoForm.tsx`, `CuentaSocio.tsx`).

**Rationale**: patrón ya establecido y consistente en todos los módulos de alta del sistema — no requiere ninguna decisión de diseño nueva.
