---

description: "Task list for Autenticación con usuarios y roles"
---

# Tasks: Autenticación con usuarios y roles

## Phase 1: Setup

- [X] T001 Crear `backend/scripts/crear_tablas_auth.py` (idempotente): `dbo.AuthRoles` (IdRol int identity PK, Nombre varchar(20) UNIQUE) seed `Administrador`/`Lectura`; `dbo.AuthUsuarios` (IdUsuario int identity PK, NombreUsuario varchar(60) UNIQUE, PasswordHash varchar(200), Nombre nvarchar(120), IdRol int FK, Activo bit default 1, FechaCreacion datetime2 default SYSUTCDATETIME())
- [X] T002 Ejecutar el script contra `WC` y verificar las tablas + los 2 roles seed (nombres renombrados a `AuthRoles`/`AuthUsuarios` — `Roles`/`Usuarios` ya existían en WC con esquema ajeno de origen desconocido, mismo patrón que `rubros_compra`/`centros_costo` en 002-compras)

## Phase 2: Primitivas de auth (sin HTTP)

- [X] T003 [P] Implementar `backend/src/auth/secret.py::get_secret() -> bytes`: lee `backend/.auth_secret`, lo genera con `secrets.token_bytes(32)` si no existe
- [X] T004 [P] Implementar `backend/src/auth/passwords.py::hash_password(password) -> str` / `verify_password(password, hash) -> bool` (`hashlib.pbkdf2_hmac`, salt aleatoria por contraseña, formato `salt$hash` en base64)
- [X] T005 [P] Implementar `backend/src/auth/tokens.py::crear_token(id_usuario, rol, horas=12) -> str` / `verificar_token(token) -> dict | None` (HMAC-SHA256 sobre payload JSON, rechaza firma inválida o `exp` vencido)
- [X] T006 [P] Test `backend/tests/test_auth_passwords_tokens.py`: hash/verify con contraseña correcta/incorrecta; token válido/expirado/con firma alterada

## Phase 3: Feature `auth` (HTTP)

- [X] T007 Implementar `backend/src/features/auth/repository.py::get_usuario_por_nombre(nombre) -> dict | None` (join con Roles para traer el nombre del rol)
- [X] T008 Implementar `backend/src/features/auth/router.py`: `POST /api/auth/login` (verifica password, setea cookie httpOnly `la_herencia_session` con `tokens.crear_token`, FR-002), `POST /api/auth/logout` (borra la cookie, FR-003), `GET /api/auth/me` (decodifica la cookie, 401 si inválida)
- [X] T009 Registrar `auth_router` en `backend/src/main.py`

## Phase 4: Middleware de protección global

- [X] T010 Implementar `AuthMiddleware` en `backend/src/main.py` (Starlette `BaseHTTPMiddleware`): exime `/api/auth/login`, `/health`, `/docs`, `/openapi.json`; para el resto, exige cookie válida (401 si falta/inválida/expirada, FR-001); si el método es POST/PUT/PATCH/DELETE y el rol es `Lectura`, responde 403 sin llamar al endpoint (FR-006)
- [X] T011 [P] Test `backend/tests/test_auth_middleware.py`: sin cookie → 401 en un endpoint cualquiera; con cookie `Lectura` → 200 en GET, 403 en POST/PUT/PATCH/DELETE (probar contra 5 endpoints de escritura de módulos distintos, SC-002); con cookie `Administrador` → todo pasa igual que hoy (SC-003); cookie con `exp` vencido → 401 (SC-004); `/api/auth/login` y `/health` sin cookie → no 401

## Phase 5: Script de alta de usuario

- [X] [P] T012 Implementar `backend/scripts/crear_usuario.py` (CLI, `argparse`): `--usuario --password --nombre --rol`, hashea con `passwords.hash_password`, inserta o actualiza (si ya existe, resetea password) — nunca imprime ni loguea la contraseña en texto plano

## Phase 6: Frontend

- [X] T013 [P] Crear `frontend/src/services/authApi.ts`: `login(usuario, password)`, `logout()`, `fetchMe()` — todas con `credentials: "include"`
- [X] T014 Agregar `credentials: "include"` a los 5 helpers de `frontend/src/services/apiClient.ts` (`apiGet`, `apiPatch`, `apiPost`, `apiPut`, `apiDelete`)
- [X] T015 Crear `frontend/src/app/login/page.tsx`: formulario usuario/password, muestra error genérico si falla (FR-002/Acceptance Scenario 3), redirige a `/` si ya hay sesión
- [X] T016 Crear `frontend/src/components/auth/AuthGuard.tsx`: en el layout raíz, llama a `fetchMe()`; si 401 y la ruta no es `/login`, redirige a `/login`; mientras carga, no renderiza contenido protegido (FR-010)
- [X] T017 Integrar `AuthGuard` en `frontend/src/app/layout.tsx` (dentro de `Providers`, envolviendo `NavHeader` + `children`)
- [X] T018 Crear `frontend/src/components/auth/SoloLectura.tsx`: wrapper que oculta sus `children` si el rol del usuario autenticado es `Lectura` (FR-011) — usarlo en los botones de escritura más visibles (alta/editar/eliminar) como defensa en profundidad, sin necesidad de tocar cada pantalla de golpe (se puede extender de forma incremental)
- [X] T019 Agregar botón "Cerrar sesión" y nombre del usuario logueado en `NavHeader.tsx`

## Phase 7: Polish

- [X] T020 Ejecutar la suite completa de backend y `tsc --noEmit`, confirmar que ningún endpoint existente cambió de comportamiento para el rol `Administrador` (SC-003) — 401 passed, 1 pre-existente sin relación (test_db_connection, confirmado con `git stash` que ya fallaba en main); `tsc --noEmit` sin errores. Los tests que instanciaban `TestClient`/`httpx.AsyncClient` sin cookie ahora simulan Administrador (ver `tests/contract/conftest.py` y el cookie agregado a cada `client = TestClient(app)` preexistente)
- [X] T021 Correr `crear_usuario.py` una vez para crear la cuenta real del usuario (fuera del repo, el usuario elige su propia contraseña — no se automatiza ni se deja constancia de la contraseña en ningún artefacto) — el usuario pidió que se corriera directamente en la sesión; se generó una contraseña aleatoria y se le entregó por chat en vez de que la elija él (desvío puntual de Clarifications Q2, a pedido explícito)
