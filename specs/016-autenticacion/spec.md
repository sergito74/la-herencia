# Feature Specification: Autenticación con usuarios y roles

**Feature Branch**: `016-autenticacion`

**Created**: 2026-09-22

**Status**: Draft

**Input**: User description: "Candidato #5 del relevamiento de funciones adicionales: hoy el sistema no tiene login, cualquiera con acceso a la red local puede entrar. El usuario pidió preparar la base para multiusuario con roles desde el inicio (no un login de un solo usuario sin roles), aunque hoy lo use una sola persona."

## Clarifications

### Session 2026-09-22

- Q1 (alcance de roles): ¿qué roles concretos hacen falta hoy? → **A: Dos roles amplios** — `Administrador` (lectura + escritura en todo lo que el sistema ya permite escribir) y `Lectura` (solo consulta, sin ningún botón de alta/edición/eliminación/confirmación/conciliación). No se modela un permiso fino por módulo (ej. "puede editar Compras pero no Tarjetas") porque no hay ningún caso de uso real que lo pida hoy — sería sobre-ingeniería sin evidencia (constitución VII). Si en el futuro hace falta un tercer rol o permisos por módulo, se agrega como extensión de `dbo.AuthRoles`, no requiere rediseño.
- Q2 (alta del primer usuario): ¿se crea un usuario admin por defecto con contraseña conocida? → **A: No** — un usuario/contraseña de fábrica es un agujero de seguridad conocido. Se entrega un script de línea de comandos (`backend/scripts/crear_usuario.py`) que el usuario real corre una sola vez para crear su propia cuenta con su propia contraseña, nunca elegida ni conocida por el agente de desarrollo.
- Q3 (mecanismo de sesión): ¿JWT, sesión en base de datos, o cookie firmada sin estado? → **A: Cookie firmada sin estado** (HMAC-SHA256 sobre `idUsuario:expiración`, secreto en un archivo local fuera de Git) — evita agregar una tabla de sesiones activas y una dependencia nueva (JWT) para un caso de uso de una sola app local, consistente con el principio de simplicidad (constitución VII). Si el negocio necesita revocar sesiones activas remotamente en el futuro, es una extensión, no un rediseño.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Iniciar sesión para usar el sistema (Priority: P1)

Un usuario necesita loguearse con su usuario y contraseña para poder ver y operar el sistema — hoy cualquiera con acceso a la red local (o a la máquina) puede abrir la app sin ninguna barrera.

**Why this priority**: Es el requisito mínimo de seguridad — sin login no hay control de acceso alguno, cualquier otra pieza de esta spec (roles) no tiene sentido sin esto primero.

**Independent Test**: Puede probarse abriendo la app sin sesión y verificando que redirige a `/login`; con credenciales válidas, verificando que entra y ve el sistema normalmente; con credenciales inválidas, verificando que el sistema rechaza el ingreso con un mensaje claro.

**Acceptance Scenarios**:

1. **Given** un usuario sin sesión iniciada, **When** intenta acceder a cualquier pantalla del sistema, **Then** el sistema lo redirige a `/login` sin mostrar ningún dato.
2. **Given** la pantalla de login, **When** el usuario ingresa usuario y contraseña correctos, **Then** el sistema lo autentica y lo lleva a la pantalla de inicio.
3. **Given** la pantalla de login, **When** el usuario ingresa una contraseña incorrecta, **Then** el sistema rechaza el ingreso con un mensaje genérico ("usuario o contraseña incorrectos"), sin indicar si el usuario existe o no (evita enumeración de usuarios).
4. **Given** una sesión iniciada, **When** el usuario cierra sesión, **Then** el sistema lo redirige a `/login` y ninguna pantalla protegida vuelve a ser accesible hasta loguearse de nuevo.
5. **Given** una sesión expirada (más de 12 horas desde el login), **When** el usuario intenta usar el sistema, **Then** el sistema lo trata como si no tuviera sesión (Acceptance Scenario 1).

---

### User Story 2 - Restringir escritura a usuarios con rol Administrador (Priority: P1)

Un usuario con rol `Lectura` necesita poder consultar todo el sistema con normalidad, pero el sistema debe impedirle cualquier alta, edición, eliminación o confirmación — esas acciones quedan reservadas a usuarios con rol `Administrador`.

**Why this priority**: Es la razón de ser de tener roles en vez de un login simple — sin esta distinción, cualquier usuario logueado podría escribir en `WC`, que es exactamente lo que se quiere evitar para el caso de uso real (dar acceso de consulta a alguien del Estudio Contable, por ejemplo, sin que pueda tocar datos).

**Independent Test**: Puede probarse logueado como un usuario `Lectura` e intentando confirmar una carga de Excel (013) o editar una Compra — el sistema debe rechazar la operación con un error claro, mientras que las mismas consultas de lectura siguen funcionando con normalidad.

**Acceptance Scenarios**:

1. **Given** un usuario con rol `Lectura`, **When** intenta ejecutar cualquier operación de escritura (POST/PUT/PATCH/DELETE) contra la API, **Then** el sistema la rechaza con un error 403 explícito, sin ejecutar ningún cambio en `WC`.
2. **Given** un usuario con rol `Lectura`, **When** consulta cualquier pantalla o endpoint de solo lectura (GET), **Then** el sistema responde con normalidad, igual que un `Administrador`.
3. **Given** un usuario con rol `Administrador`, **When** ejecuta cualquier operación ya soportada hoy (alta, edición, eliminación, confirmación, conciliación), **Then** el sistema la procesa exactamente igual que antes de esta spec — ningún flujo de escritura existente cambia de comportamiento para este rol.

### Edge Cases

- ¿Qué pasa si el archivo de secreto de firma de sesión no existe todavía (primera vez que arranca el backend)? El sistema debe generarlo automáticamente y seguir funcionando, sin requerir un paso manual adicional.
- ¿Qué pasa con las sesiones activas si se reinicia el backend? Como el secreto persiste en un archivo local (Clarifications Q3), las sesiones siguen siendo válidas después de un reinicio del backend, siempre que no hayan expirado.
- ¿Qué pasa si dos pestañas del navegador tienen sesiones de usuarios distintos? No es un caso soportado — la sesión es por navegador (cookie), no por pestaña, mismo comportamiento que cualquier sistema web con cookies de sesión.
- ¿Qué pasa con `GET /health` y la documentación automática de la API (`/docs`)? Quedan fuera del requisito de autenticación — no exponen datos de `WC`.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST exigir autenticación para acceder a cualquier endpoint de la API que exponga o modifique datos de `WC`, excepto `POST /api/auth/login` y `GET /health`.
- **FR-002**: El sistema MUST permitir iniciar sesión con usuario y contraseña, devolviendo un error genérico si la combinación es incorrecta, sin revelar si el usuario existe.
- **FR-003**: El sistema MUST permitir cerrar sesión, invalidando el acceso inmediatamente para esa sesión.
- **FR-004**: El sistema MUST expirar toda sesión a las 12 horas de haberse iniciado, sin requerir una acción explícita del usuario.
- **FR-005**: El sistema MUST asociar cada usuario a exactamente un rol (`Administrador` | `Lectura`, Clarifications Q1).
- **FR-006**: El sistema MUST rechazar con 403 cualquier operación de escritura (POST/PUT/PATCH/DELETE contra endpoints que ya escriben en `WC`) cuando el usuario autenticado tenga rol `Lectura`.
- **FR-007**: El sistema MUST permitir todas las operaciones de lectura existentes a cualquier usuario autenticado, sin distinción de rol.
- **FR-008**: El sistema MUST almacenar las contraseñas con un hash con sal, nunca en texto plano ni reversible.
- **FR-009**: El sistema MUST proveer un mecanismo fuera de la aplicación web (script de línea de comandos) para crear el primer usuario y los siguientes, sin exponer un endpoint público de alta de usuarios ni un usuario de fábrica (Clarifications Q2).
- **FR-010**: El frontend MUST redirigir a `/login` cualquier intento de acceso a una pantalla protegida sin sesión válida.
- **FR-011**: El frontend MUST ocultar o deshabilitar los controles de escritura (botones de alta/editar/eliminar/confirmar) cuando el usuario autenticado tenga rol `Lectura`, además de que el backend los rechace (defensa en profundidad, FR-006).

### Key Entities *(include if feature involves data)*

- **Usuario** (nuevo, infraestructura de esta app en `WC`): nombre de usuario único, hash de contraseña, nombre para mostrar, rol, activo/inactivo.
- **Rol** (nuevo, infraestructura de esta app en `WC`): `Administrador` | `Lectura` — catálogo simple, ampliable sin rediseño (Clarifications Q1).
- **Sesión**: no es una entidad persistida — es una cookie firmada sin estado (Clarifications Q3), validada por firma y expiración, no por consulta a una tabla.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Ningún endpoint que exponga datos de `WC` responde sin una sesión válida (verificable probando cada router sin cookie de sesión y confirmando 401).
- **SC-002**: Un usuario con rol `Lectura` no puede ejecutar ninguna de las operaciones de escritura ya existentes en el sistema (verificado contra al menos 5 endpoints de escritura reales de módulos distintos).
- **SC-003**: Un usuario con rol `Administrador` no pierde ninguna funcionalidad existente — los flujos de escritura ya probados (013, 014, compras, etc.) siguen funcionando exactamente igual.
- **SC-004**: Una sesión expira a las 12 horas sin intervención del usuario, verificado forzando una fecha de expiración pasada.

## Assumptions

- El sistema sigue siendo usado por poca gente (uno o dos usuarios reales) — dos roles amplios alcanzan; permisos granulares por módulo quedan fuera de esta spec (Clarifications Q1).
- No se pide recuperación de contraseña por email (no hay servidor de correo configurado en este sistema) — si un usuario olvida su contraseña, un Administrador la resetea con el mismo script de línea de comandos.
- `/docs` (Swagger UI de FastAPI) y `/health` quedan sin autenticar — no exponen datos de negocio.
- El archivo de secreto de firma de sesión (`backend/.auth_secret`, fuera de Git) es exclusivo de cada instalación del sistema — no se comparte entre entornos ni se versiona.
