# Phase 0 Research: Compras como fuente de verdad de imputación

## Framework de backend Python

**Decision**: FastAPI + Pydantic.

**Rationale**: La constitución exige "documented, typed API contracts" (Data and Security Constraints) y contrato-primero (principio V). FastAPI genera contrato OpenAPI a partir de modelos Pydantic tipados, soporta async nativo (útil para lectura concurrente, FR-014) y es liviano — no impone un ORM ni un patrón de escritura que no se necesita en un módulo de solo lectura.

**Alternatives considered**:
- Flask: requiere librerías adicionales (Marshmallow/Flask-RESTX) para lograr el mismo nivel de tipado; más piezas sueltas para el mismo resultado.
- Django REST Framework: trae ORM y migraciones orientadas a escritura que no aplican a este módulo de solo lectura; viola el principio de simplicidad (VII) para este alcance.

## Acceso a SQL Server desde Python

**Decision**: `pyodbc` con el DSN existente `SQL_LaHerencia`, consultas parametrizadas directas (sin ORM), encapsuladas en una capa `repository.py` por módulo de negocio y una conexión compartida en `backend/src/db/connection.py`.

**Rationale**: El DSN ya está configurado y probado (ver `memory.md`). Un ORM introduciría mapeo de un esquema histórico complejo (con nombres de columna con espacios, ej. `"Tipo documento"`) sin beneficio real para consultas de solo lectura. `pyodbc` con parámetros vinculados cumple el principio V (consultas parametrizadas, acotadas) sin capa adicional.

**Alternatives considered**:
- SQLAlchemy Core (sin ORM completo): agrega una capa de abstracción de queries que no aporta valor claro sobre SQL parametrizado directo para este alcance; se reconsiderará si los tres módulos (compras/tesorería/cuentas corrientes) muestran duplicación significativa de lógica de queries.
- pymssql: alternativa viable, pero `pyodbc` ya es el driver validado en las pruebas de conexión documentadas en `memory.md`.

## Paginación

**Decision**: Paginación por offset/limit, tamaño de página por defecto 50, máximo 200 por request.

**Rationale**: El volumen (~6.400 compras) no justifica paginación por cursor/keyset; offset/limit es más simple de implementar y de consumir desde TanStack Query, y cumple FR-013/SC-005 sin complejidad adicional.

**Alternatives considered**: Keyset pagination (por `IdDeuda`) — más eficiente a gran escala, pero prematuro para el volumen actual; se documenta como opción futura si el volumen crece significativamente.

## Estrategia de pruebas de contrato

**Decision**: `pytest` + `httpx.AsyncClient` contra la app FastAPI, usando fixtures/datos de ejemplo fijos (no contra la base real) para los contract tests automatizados. La validación contra datos reales se hace de forma manual/guiada mediante `quickstart.md` (SELECT de solo lectura), no como parte de la suite automatizada.

**Rationale**: La constitución exige que los tests no escriban en la base real; además, depender de datos reales mutables en tests automatizados los haría frágiles (los saldos/movimientos pueden cambiar). Fixtures fijas dan contract tests deterministas; `quickstart.md` cubre la validación funcional contra datos reales de forma controlada y manual.

**Alternatives considered**: Ejecutar los contract tests directamente contra SQL Server con SELECT reales — descartado como suite automática por fragilidad ante cambios de datos, aunque se mantiene como paso de validación manual en `quickstart.md`.

## Concurrencia multiusuario (FR-014/FR-015)

**Decision**: Backend FastAPI async, sin estado de sesión en memoria del servidor; cada request abre/usa una conexión del pool de `pyodbc` de forma independiente.

**Rationale**: Al ser un módulo 100% de lectura, no hay necesidad de locks: múltiples usuarios pueden ejecutar SELECT concurrentes sin conflicto. Evitar estado compartido en el servidor es la forma más simple de soportar concurrencia sin construir infraestructura de sesiones que nadie usa todavía (alineado con la Assumption de la spec: hoy 1 usuario, mañana varios).

**Alternatives considered**: Mantener estado de sesión/cache por usuario en el servidor — se descarta por ahora al no aportar valor y violar el principio de simplicidad (VII).

## Resolución de NEEDS CLARIFICATION

No quedan marcadores `NEEDS CLARIFICATION` en el Technical Context del plan: todas las decisiones anteriores resuelven los puntos que habrían quedado abiertos (framework, acceso a datos, paginación, testing, concurrencia).
