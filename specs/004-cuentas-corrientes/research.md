# Phase 0 Research: Cuentas corrientes por proveedor/cliente

## Base técnica

**Decision**: Reutilizar las decisiones de `specs/002-compras/research.md` y `specs/003-tesoreria/research.md` (FastAPI + Pydantic, pyodbc sin ORM, paginación offset/limit, pytest + httpx con fixtures, concurrencia sin estado de servidor).

**Rationale**: Tercer módulo sobre la misma base; no hay motivo técnico para divergir.

**Alternatives considered**: N/A.

## Resolución de `Origen`/`IdOrigen`

**Decision**: `origen_resolver.py` interpreta el campo `Origen` de `vw_MovimientosCuenta_Base` (valor tipo texto: "Compra", "Tesorería" u otro) y usa `IdOrigen` como clave directa hacia la tabla correspondiente (`Compras.IdDeuda` o el identificador del movimiento de tesorería según el tipo), sin heurística (clarificación 2026-09-15).

**Rationale**: A diferencia de tesorería→compra, acá sí hay clave explícita disponible en el propio dato, por lo que no corresponde aplicar la misma lógica de coincidencia por aproximación usada en `tesoreria/matching.py` — sería una complejidad innecesaria (principio VII).

**Alternatives considered**: Reutilizar `matching.py` de tesorería "por las dudas" — rechazado: mezclaría un mecanismo probabilístico con uno determinístico y ocultaría cuándo el sistema realmente tiene certeza.

**Resuelto 2026-09-16**: se confirmaron contra datos reales 12 valores distintos de `Origen` (no un genérico "Tesorería"): `Compras`, `Banco Nacion`, `Galicia`, `Pagos efectivo`, `Cobros Valores Recibidos`, `Pagos Valores Recibidos`, `Alquileres`, `Impuestos`, `Remuneraciones`, `Ret. IVA Granos`, `Ret. Ventas Hacienda`, `Retenciones`. Los últimos 6 no corresponden a ningún módulo dentro del alcance de `002-compras`/`003-tesoreria` — por decisión del usuario (clarificación 2026-09-16), `origen_resolver.py` MUST devolver un tercer estado `"fuera_de_alcance"` para esos casos, distinto de `"no_disponible"`. Ver la tabla de mapeo completa en `data-model.md`.

**Resuelto 2026-09-16 (medio de tesorería)**: `origen.medio` se fija como enum cerrado (`"bna"`, `"galicia"`, `"efectivo"`, `"valores_recibidos"`) en vez de exponer la columna `Origen` cruda, para no acoplar el contrato de API al nombre exacto de la tabla SQL. `Cobros Valores Recibidos` y `Pagos Valores Recibidos` colapsan al mismo `medio` porque el sentido (cobro/pago) ya lo dan `deuda`/`credito` del movimiento. Para `Pagos efectivo`: aunque en `specs/003-tesoreria` ese medio no tiene campo de contacto y por eso queda fuera de la referencia heurística hacia compras, acá no aplica esa limitación — la resolución en `004-cuentas-corrientes` es directa vía `IdOrigen` (no heurística), así que no hace falta confirmar el contacto para resolver la referencia.

## Cálculo de saldo

**Decision**: Consumir `vw_MovimientosCuenta_Saldo` directamente para el saldo, sin reimplementar la fórmula en Python (Assumptions de la spec).

**Rationale**: La vista ya resuelve la regla de negocio de acumulación de deuda/crédito; reimplementarla en el backend duplicaría lógica y arriesgaría discrepancias (violaría SC-003: "coinciden con el saldo calculado por las vistas de origen").

**Alternatives considered**: Calcular el saldo sumando movimientos en Python — descartado, mayor riesgo de divergencia y trabajo redundante.

## Deduplicación de contactos tipo "Multiple" (FR-014)

**Decision**: La deduplicación se resuelve a nivel de consulta SQL (agrupando por `IdContacto` al traer movimientos), no en una capa Python posterior, para evitar traer y descartar filas innecesariamente.

**Rationale**: Es más simple y eficiente resolverlo en la consulta que traer duplicados y filtrarlos en memoria, especialmente con miles de movimientos.

**Alternatives considered**: Deduplicar en Python después de la consulta — descartado por ineficiencia sin beneficio claro.

## Resolución de NEEDS CLARIFICATION

No quedan marcadores `NEEDS CLARIFICATION` bloqueantes. Un punto de verificación de datos (valores exactos del campo `Origen`) queda documentado arriba y en `quickstart.md`, sin bloquear el resto del diseño.
