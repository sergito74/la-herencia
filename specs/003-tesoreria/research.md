# Phase 0 Research: Tesorería por banco, caja, valores y tarjetas

## Base técnica

**Decision**: Reutilizar las decisiones ya tomadas en `specs/002-compras/research.md` (FastAPI + Pydantic, pyodbc sin ORM, paginación offset/limit, pytest + httpx con fixtures, concurrencia sin estado de servidor).

**Rationale**: Es el mismo backend/frontend, agregando un módulo de features. Repetir el análisis sería trabajo redundante y podría introducir inconsistencias entre módulos hermanos.

**Alternatives considered**: N/A — divergir del stack ya elegido para compras violaría el principio de simplicidad (VII) sin ninguna necesidad técnica nueva.

## Modelado de medios de tesorería heterogéneos

**Decision**: No forzar una interfaz única entre BNA, Galicia, efectivo, valores y tarjetas. Cada medio tiene su propio modelo Pydantic de respuesta, y el frontend renderiza una tabla adaptada por medio (columnas distintas), en vez de intentar una tabla genérica.

**Rationale**: FR-002 lo exige explícitamente ("sin forzar un modelo único"); forzar una interfaz común perdería campos reales (por ejemplo, `Saldo` de Galicia no existe en BNA) o inventaría campos vacíos sin sentido, violando el principio IV (significado financiero explícito).

**Alternatives considered**: Modelo único con campos opcionales para todos los medios — descartado por generar una tabla con muchos `null` sin indicar por qué, confuso para el usuario.

## Coincidencia tesorería → compra (heurística)

**Decision**: Implementar la heurística de coincidencia (`IdContacto` + fecha + importe) como una función pura y aislada (`matching.py`), documentando que puede devolver 0, 1 o N candidatas, y que el contrato de API expone las tres situaciones de forma explícita (clarificación 2026-09-15).

**Rationale**: Al no existir clave directa (a diferencia de compras→cuenta corriente), aislar la lógica permite reemplazarla sin tocar el router si en el futuro aparece una clave mejor, y evita que la ambigüedad quede escondida detrás de una función que "adivina" silenciosamente.

**Alternatives considered**: Elegir automáticamente "la más cercana" por fecha cuando hay varias candidatas — rechazado explícitamente por la clarificación de la spec (FR-005: "sin elegir una al azar").

**Actualización 2026-09-16**: `Valores propios` no tiene campo de contacto (confirmado contra `INFORMATION_SCHEMA`), por lo que `matching.py` MUST devolver `estado: "sin_coincidencia"` para ese medio sin ejecutar ninguna consulta de coincidencia (clarificación de spec 2026-09-16). El resto de los medios (BNA, Galicia, efectivo, valores recibidos vía `IdEmisor`, tarjetas) sí tienen contacto y usan la heurística completa.

## Carga de resúmenes por Excel

**Decision**: `openpyxl` para leer el archivo subido en memoria, validar contra un esquema de columnas esperado por tipo de medio (BNA/Galicia/tarjeta), y devolver una previsualización JSON. No se usa `pandas` para mantener la dependencia mínima (principio VII); no se persiste nada en SQL Server desde este endpoint (FR-008, alineado con el modo solo lectura vigente).

**Rationale**: `openpyxl` es suficiente para leer celdas y validar encabezados sin traer una dependencia pesada como `pandas` solo para este propósito acotado.

**Alternatives considered**: `pandas` — descartado por ser una dependencia mucho más pesada de lo que este alcance (validar + previsualizar) necesita.

## Formato esperado de los archivos Excel

**Decision (resuelto 2026-09-16)**: Confirmado contra archivos reales provistos por el usuario:

- **Galicia** (`.xlsx`): hoja `Movimientos`, encabezado en la fila 1 (sin filas de metadata previas), 16 columnas: `Fecha, Descripción, Origen, Débitos, Créditos, Grupo de Conceptos, Concepto, Número de Terminal, Observaciones Cliente, Número de Comprobante, Leyendas Adicionales 1, Leyendas Adicionales 2, Leyendas Adicionales 3, Leyendas Adicionales 4, Tipo de Movimiento, Saldo`. Fechas ya como `datetime` (no texto) al leer con `openpyxl`. **Sin columna de contacto explícita** — el contraparte aparece disperso en las columnas "Leyendas Adicionales" (nombre, CUIT, referencia), sin una posición fija garantizada.
- **BNA** (`.xls`, formato binario antiguo leíble con `xlrd`): la hoja tiene **5 filas de metadata/título antes del encabezado real** (`Banco Nación`, `[BNA + Empresas]`, `Últimos movimientos`, filas vacías); el encabezado real está en la fila 6: `Fecha, Comprobante, Concepto, Importe, Saldo`. Los importes vienen como **texto con formato argentino** (`"$ 5.107.397,26"`, negativos `"$ -9,00"`), no como número — requieren parseo (`$`, separador de miles `.`, decimal `,`). **Sin columna de contacto**.

**Rationale**: Verificar contra archivos reales (en vez de asumir un formato) evita reescribir `excel_import.py` después de haberlo construido sobre un supuesto incorrecto — ya se detectaron 3 diferencias significativas respecto a lo asumido originalmente (filas de metadata en BNA, formato de importe argentino, ausencia de columna de contacto en ambos).

**Alternatives considered**: Mantener el formato genérico asumido antes de ver los archivos reales — descartado porque ya se demostró incorrecto (BNA no es `.xls` "limpio": requiere saltar 5 filas y parsear importes como texto).

**Consecuencia sobre matching (FR-004 de `specs/003-tesoreria`)**: como ninguno de los dos formatos trae contacto de forma directa y estructurada, la previsualización de Excel (esta spec, User Story 3) **no intenta resolver la referencia a compra** durante la carga — esa resolución solo aplica a movimientos ya existentes en SQL Server (que sí tienen `IdContacto`, cargado por otro medio). Esto es coherente con el alcance ya definido: la carga de Excel es solo validación + previsualización, sin persistencia ni matching.

## Resolución de NEEDS CLARIFICATION

Un punto queda explícitamente diferido (formato de columnas Excel por banco/tarjeta), documentado arriba y en `quickstart.md` como paso previo a implementar `excel_import.py`. No bloquea el resto del diseño de esta fase.
