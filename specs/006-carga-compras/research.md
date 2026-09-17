# Phase 0 Research: Carga de Compras

## 1. Escritura transaccional multi-tabla (cabecera + líneas + vencimientos)

**Decision**: Agregar `execute_write_transaction(statements: list[tuple[str, tuple]]) -> list[int]` a `backend/src/db/connection.py`. Abre una única conexión con `autocommit=False`, valida cada sentencia con las mismas reglas que `execute_write` (solo INSERT/UPDATE/DELETE, sin DDL, sin múltiples statements por entrada) y `_assert_target_is_wc()` una sola vez al inicio, ejecuta todas las sentencias en orden, hace `commit()` si todas tienen éxito o `rollback()` ante cualquier excepción, y devuelve la lista de `rowcount` (o el id insertado si la sentencia trae `OUTPUT`, reutilizando la misma detección que `execute_insert_returning_id`).

**Rationale**: Guardar una compra implica escribir en tres tablas sin FKs reales a nivel de motor (confirmado: `sys.foreign_keys` vacío para `Compras`/`Det_Compras`/`Vencimiento Compras`). Sin una transacción, una falla a mitad de camino (ej. al insertar la tercera línea) dejaría una compra con cabecera y algunas líneas pero no todas — un estado parcial que el usuario no pidió y que rompería la Historia 1, Escenario 3 ("sin crear ningún registro parcial"). `execute_write` actual abre y cierra una conexión por llamada (una transacción implícita de una sola sentencia), insuficiente para esto.

**Alternatives considered**:
- *Una llamada a `execute_write` por tabla, sin transacción*: rechazada — permite estados parciales, viola FR-002/Historia 1 Escenario 3.
- *Stored procedure en SQL Server que reciba todo el payload como JSON/TVP*: rechazada por complejidad y porque el principio VII pide la implementación más simple; además introduciría lógica de negocio en la base, que el resto del sistema evita deliberadamente (toda la lógica vive en Python).
- *ORM con unit-of-work (SQLAlchemy)*: rechazada — no está en el stack aprobado (principio VIII) y el resto del backend usa pyodbc directo con SQL parametrizado.

## 2. Bloqueo de edición exclusivo (FR-009a) sin sistema de autenticación real

**Decision**: Tabla nueva `dbo.CompraEditLocks` en `WC` (`IdCompra` int PK, `LockToken` uniqueidentifier NOT NULL, `LockedAt` datetime NOT NULL, `ExpiresAt` datetime NOT NULL). El frontend genera un `LockToken` (UUID v4) por pestaña/sesión de edición (no persistido en localStorage — vive solo en memoria de esa sesión de edición) y lo manda en cada request de escritura sobre esa compra. El backend expone `POST /api/compras/{id}/lock` (adquiere o renueva el lock si no existe uno vigente de otro token, devuelve 409 si está tomado por otro token no vencido), `DELETE /api/compras/{id}/lock` (libera, solo si el token coincide) y valida el lock en `PUT /api/compras/{id}` (rechaza con 409 si hay un lock vigente de otro token). Expiración por inactividad: `ExpiresAt = LockedAt + 15 minutos`, renovada en cada `PATCH` de autoguardado o al reabrir el formulario; un lock vencido se trata como inexistente (se puede sobrescribir).

**Rationale**: La Clarification del spec pidió explícitamente bloqueo pesimista ("nadie más puede abrirla en modo edición hasta que se libere"), no "último en gana" ni resolución de conflictos. El sistema no tiene autenticación de usuarios todavía (confirmado: el botón de usuario en `NavHeader.tsx` está deshabilitado con "autenticación pendiente de implementar"), así que no hay un `IdUsuario` real contra el cual bloquear. Un token de sesión de navegador es la pieza mínima que cumple el requisito sin adelantar trabajo de autenticación que no fue pedido (principio VII). El TTL de inactividad evita que un lock quede huérfano para siempre si el usuario cierra la pestaña sin liberar explícitamente.

**Alternatives considered**:
- *Lock en memoria del proceso backend (diccionario Python)*: rechazada — el backend corre con reload/múltiples workers en el futuro; un lock en memoria no sobrevive un restart ni se comparte entre procesos, y esta app ya persiste todo su estado compartido en SQL Server.
- *Optimistic concurrency vía `SSMA_TimeStamp` (rowversion) existente en ambas tablas*: rechazada para esta feature porque el usuario pidió explícitamente bloqueo pesimista en la clarificación, no detección de conflicto al guardar. Queda documentado como alternativa válida si en el futuro se decide relajar el requisito.
- *Esperar al módulo de autenticación real antes de implementar bloqueo*: rechazada — bloquearía indefinidamente un requisito ya aprobado por el usuario; el token de sesión es trivialmente reemplazable por `IdUsuario` real cuando exista login, sin cambiar el contrato (`LockToken` seguiría siendo una cadena opaca).

## 3. Sugerencia de rubro por texto de producto/servicio (FR-012a)

**Decision**: Consulta de solo lectura: `SELECT TOP 1 IdRubro, COUNT(*) AS frecuencia FROM Det_Compras WHERE [Producto/Servicio] = ? AND IdRubro IS NOT NULL GROUP BY IdRubro ORDER BY COUNT(*) DESC`. Se expone como `GET /api/compras/rubro-sugerido?productoServicio=...`, se llama on-blur del campo producto/servicio en el frontend, y solo rellena el combo de Rubro si el usuario todavía no eligió uno manualmente.

**Rationale**: Cumple FR-012a con el mecanismo más simple que iguala razonablemente el "alias exacto" del motor original (nivel 1 de 3 del sistema Access), sin el paso de normalización de texto ni el aprendizaje por frecuencia de palabras sueltas (Assumptions del spec, explícitamente fuera de alcance v1). Es una consulta agregada sencilla sobre una tabla ya indexada por PK, sin necesidad de tablas de aprendizaje nuevas (`ClasifPalabras`, `ClasifReglas`, `CatItemAlias`/`CatItemCanon` quedan fuera de alcance).

**Alternatives considered**:
- *Replicar el motor de 3 niveles completo (alias→reglas→palabras) del Access original*: rechazada por el spec (Assumptions) — mucho mayor complejidad para una mejora de UX no bloqueante, y el sistema original ya tiene ese motor con un bug real (RowSource roto) que no vale la pena portar tal cual.
- *Sin sugerencia alguna (Rubro siempre manual)*: rechazada — el usuario aprobó explícitamente incluir la sugerencia en v1 (clarificación 2026-09-17).

## 4. Encoding de columnas `Campaña`/`IdCampaña`

**Decision**: Resolver estas dos columnas por posición ordinal (`INFORMATION_SCHEMA.COLUMNS` con `ORDINAL_POSITION`) una única vez al arrancar el backend (o cachear el nombre exacto de columna resuelto), en vez de escribir el literal `[Campaña]` en el SQL. Alternativa más simple y ya validada: probar en desarrollo si `sp_columns`/pyodbc con la conexión configurada correctamente (`charset`/`ANSI` vs `Unicode` en el DSN `SQL_LaHerencia`) devuelve el nombre bien formado — si es así, no hace falta ningún workaround y el hallazgo de la inspección fue un artefacto del método de verificación (COM automation / consola), no del driver de producción.

**Rationale**: Se confirmó en `/speckit-clarify` (2026-09-17) que el problema persiste incluso consultando directo con pyodbc (mismo DSN que usa el backend), así que no puede descartarse como artefacto de la inspección Access. Antes de escribir código de producción contra esta columna hay que confirmar cómo la ve exactamente el proceso backend real (mismo intérprete, mismo pyodbc, misma configuración de conexión que `src/db/connection.py`), no una consulta ad-hoc de investigación.

**Alternatives considered**: n/a — este ítem se resuelve empíricamente en la primera tarea de implementación (T0 de tasks.md), no por decisión de diseño.

## 5. Validación referencial en aplicación (FR-013)

**Decision**: Antes de cada `execute_write_transaction`, el repository ejecuta lecturas de existencia (`SELECT 1 FROM Contactos WHERE IdContacto = ?`, ídem para `Rubros`, `[Centro de costos]`, `DestinoCompras`) y aborta con un error de dominio (400) sin llegar a la transacción si alguna referencia no existe.

**Rationale**: Confirmado que no hay FKs reales en SQL Server (`sys.foreign_keys` vacío) — sin esta validación en aplicación, una compra podría quedar apuntando a un `IdRubro` inexistente, silenciosamente, tal como puede pasar hoy en el Access original. Cumple FR-013 y el principio IV (trazabilidad).

**Alternatives considered**:
- *Agregar FKs reales a `WC`*: rechazada para esta feature — es un cambio de esquema con impacto más amplio (afectaría también el histórico migrado, que puede tener huérfanos reales) y no fue pedido; queda como posible mejora de infraestructura a proponer aparte, no dentro de este spec.
