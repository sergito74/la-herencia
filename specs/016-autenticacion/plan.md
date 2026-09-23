# Implementation Plan: Autenticación con usuarios y roles

**Branch**: `016-autenticacion` | **Date**: 2026-09-22 | **Spec**: [spec.md](spec.md)

## Summary

Agrega login/logout con cookie de sesión firmada sin estado (HMAC-SHA256, sin JWT ni tabla de sesiones), 2 tablas nuevas en `WC` (`AuthRoles`, `AuthUsuarios`), un middleware único que protege todos los endpoints de la API salvo `/api/auth/login`, `/health` y `/docs`, y rechaza escrituras (POST/PUT/PATCH/DELETE) de usuarios con rol `Lectura`. Sin dependencias nuevas — todo con la librería estándar de Python (`hashlib`, `hmac`, `secrets`).

## Technical Context

**Language/Version**: Python 3.13 (backend), TypeScript/Next.js 14 (frontend).

**Primary Dependencies**: ninguna nueva — `hashlib`/`hmac`/`secrets`/`base64` (stdlib) para hashing de contraseña y firma de cookie.

**Storage**: SQL Server `WC`. 2 tablas nuevas (`AuthRoles`, `AuthUsuarios`), infraestructura de esta app (mismo criterio que `Tarjetas_Resumenes_Lineas_Estado`).

**Testing**: `pytest` (mock de `connection.py` para las funciones de hash/verificación; `TestClient` para el middleware, con y sin cookie, con cada rol).

**Target Platform**: Web local.

**Project Type**: Web application. Nuevo feature `backend/src/features/auth/`; middleware global en `backend/src/main.py`; `frontend/src/app/login/page.tsx` + guard global en `layout.tsx`/`Providers`.

**Performance Goals**: la verificación de cada request MUST ser O(1) — sin consulta a `WC` por request (cookie autocontenida, FR-004/Clarifications Q3), salvo el propio login.

**Constraints**: constitución II — las tablas `AuthUsuarios`/`AuthRoles` son infraestructura de esta app, no tocan `LaHerencia`/`.accdb`. El secreto de firma nunca se versiona (`.gitignore`).

**Scale/Scope**: 1 feature backend nuevo (`auth`), 1 middleware en `main.py`, 1 script de alta de usuario, 1 página de login, 1 guard global de frontend, ajuste de `apiClient.ts` (`credentials: "include"`).

## Constitution Check

- **I/II**: ✅ tablas nuevas en `WC`, ninguna escritura a `LaHerencia`/`.accdb`; el secreto de sesión es un archivo local fuera de Git, no un dato de negocio.
- **III**: ✅ protege el acceso a los procesos de negocio ya existentes, no altera su forma.
- **IV**: N/A (no es un dato financiero).
- **V**: ✅ tests de middleware antes/junto con el código (con y sin sesión, con cada rol).
- **VII (simplicidad)**: ✅ cookie firmada sin estado en vez de JWT (dependencia nueva) o tabla de sesiones (estado adicional a mantener); 2 roles amplios en vez de permisos granulares por módulo, ambos por decisión explícita del usuario (Clarifications Q1/Q3).
- **VIII**: ✅ sin nuevas dependencias de stack.

Sin violaciones.

## Project Structure

```text
backend/
├── scripts/
│   └── crear_usuario.py            # nuevo: alta de usuario por CLI (Clarifications Q2)
├── src/
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── passwords.py             # hash/verificación (pbkdf2_hmac, stdlib)
│   │   ├── tokens.py                # firma/verificación de cookie (hmac, stdlib)
│   │   └── secret.py                # lee o genera backend/.auth_secret
│   └── features/auth/
│       ├── __init__.py
│       ├── repository.py            # get_usuario_por_nombre, etc.
│       ├── router.py                # POST /login, POST /logout, GET /me
│       └── schemas.py
├── main.py                          # + AuthMiddleware, + auth_router
└── tests/
    ├── test_auth_passwords_tokens.py
    └── test_auth_middleware.py

frontend/src/
├── app/login/page.tsx                # nuevo
├── components/auth/
│   ├── AuthGuard.tsx                 # nuevo: redirige a /login sin sesión
│   └── SoloLectura.tsx               # nuevo: oculta children si rol === "Lectura" (FR-011)
├── services/authApi.ts                # nuevo: login, logout, fetchMe
└── services/apiClient.ts              # + credentials: "include" en todos los fetch
```

**Structure Decision**: `src/auth/` (sin prefijo `features/`) para las primitivas puras de hashing/tokens, reusables por el middleware sin depender de un router — separado de `src/features/auth/` (el feature con endpoints HTTP), mismo criterio que `src/db/` es infraestructura compartida y `src/features/*` son los dominios de negocio.

## Complexity Tracking

*Sin violaciones.*
