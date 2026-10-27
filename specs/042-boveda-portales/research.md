# Research: 042 — Bóveda de portales

## R1. Cifrado de secretos

- **Decision**: Cifrado autenticado AES-256-GCM (librería `cryptography`, ya instalada en `backend/.venv`, 50.0.1). Una **clave maestra** de 32 bytes aleatorios vive en el Administrador de credenciales de Windows (`keyring`, servicio `LaHerencia-Boveda`, cuenta `clave-maestra`), protegida por DPAPI del usuario de Windows. En `WC` solo se guarda `nonce (12 B) + texto cifrado + tag`, con datos asociados (AAD) `boveda:<IdCredencial>:<campo>` para que un valor cifrado no pueda copiarse a otra fila o campo.
- **Rationale**: Cumple FR-002 (una copia de la base sola no descifra) sin servicios externos; `keyring` ya se usa en 037. GCM detecta alteraciones.
- **Recuperación** (edge case "se pierde la clave maestra"): el script `boveda_clave.py exportar` escribe la clave maestra envuelta con una frase de recuperación (scrypt + AES-GCM) en un archivo `.lhkey` que Sergio guarda fuera del repo y de Dropbox; `importar` la restaura en otro equipo. Sin la clave ni el archivo, las credenciales se vuelven a cargar a mano (los demás datos de la bóveda no se pierden).
- **Alternatives**: SQL Server Always Encrypted / TDE (requiere certificados y configuración de servidor, protege poco ante quien tiene acceso al equipo); Fernet (válido, pero sin AAD); guardar las credenciales directamente en `keyring` como 037 (no permite listado, auditoría ni credenciales compartidas en la base; difícil de respaldar).

## R2. Acceso solo administrador

- **Decision**: Todos los endpoints `/api/boveda/*` exigen `rol == "Administrador"` (mismo patrón `_exigir_admin` de `recalculo_fifo/router.py`), además del middleware de sesión existente. El frontend oculta la entrada del menú si el rol no es Administrador. No se pide reingreso de contraseña (Clarification 27/10).
- **Revelar/copiar**: `POST /api/boveda/credenciales/{id}/revelar` devuelve el secreto en esa sola respuesta, con `Cache-Control: no-store`; se audita. Ningún otro endpoint devuelve secretos.
- **Logs**: los conectores reciben las credenciales como objeto `Secreto` cuyo `__repr__`/`__str__` devuelven `***`; los mensajes de error se construyen solo con textos fijos o extraídos de la página, nunca con valores de credenciales.

## R3. Programación dentro de la aplicación

- **Decision**: Un hilo `planificador` que arranca en el evento `startup` del backend (patrón de `_precalentar_auditoria`) y cada 60 s busca portales con `ProximaCorrida <= ahora`, activos, autorizados, con conector y no suspendidos. Los corre de a uno (cola en serie). Al terminar calcula la próxima corrida **a partir de ahora** (no del horario perdido), lo que da la recuperación única al abrir la app (FR-013).
- **Concurrencia**: `sp_getapplock` por portal (`boveda-portal-<id>`), como el lock de 037; un portal en curso no se dispara de nuevo (manual o programado). Las corridas "en curso" sin lock vivo se marcan `incompleta` al arrancar.
- **Tarea semanal de 037**: se reemplaza. El script `instalar_descarga_peajes.ps1` gana `-Desinstalar`; `descargar_peajes.py` CLI queda para pruebas manuales.
- **Alternatives**: una tarea de Windows por portal o un tick de Windows (descartado por Clarification Q1 = B); APScheduler (dependencia nueva innecesaria para un tick de 60 s).

## R4. Conectores

- **Decision**: Registro en código `features/boveda/conectores/__init__.py`: `CONECTORES = {codigo: Conector}`. Interfaz:
  - `ingresar(pw, credencial) -> sesión` (lanza `RequiereIntervencion`, `CredencialesRechazadas`, `PortalCambio`)
  - `listar_documentos(sesion) -> [DocumentoPortal(clave, fecha, tipo, proveedor, numero, bajar())]`
  - `estado_cuenta(sesion) -> EstadoCuentaPortal | None` (opcional)
  - `leer_comprobante(pdf) -> DatosCompra | None` (opcional; para la carga automática FR-020)
- Los 4 peajes envuelven el código existente de `descarga_peajes/portales.py` y `lectores.py` sin reescribirlo.
- Un portal registrado desde la UI con `CodigoConector = NULL` es "solo bóveda".
- **Orden de conectores** (FR-023): peajes → Bayá Casal (extranet `ctacteA/`, PDF embebido en base64, relevado 19/10) → Cargill (API libro financiero por trimestre, customerId 35192801, relevado 20/10) → ARCA → ARBA → Municipalidad de Bolívar → Sancor → Allianz → Jáuregui y Morales → Lartirigoyen.
- **Relevamiento pendiente**: para ARCA, ARBA, Municipalidad, Sancor, Allianz, Jáuregui y Morales y Lartirigoyen no hay relevamiento del portal. Cada conector empieza con una tarea de relevamiento con Chromium/Playwright (vía de `.specify/memory/local-access.md`), solo lectura, autorizada por Sergio el 27/10/2026. Si un portal exige segundo factor o captcha en cada ingreso, queda "requiere intervención"/"solo bóveda" (no se elude).

## R5. Carga automática en Compras para todos los portales

- **Decision**: Generalizar `descarga_peajes/carga.py` a `boveda/carga.py` con la misma regla: formato reconocido (el conector tiene `leer_comprobante` y devolvió datos), suma de renglones + impuestos = total impreso al centavo, sin tolerancia (Sergio 27/10/2026: conciliar al centavo; los ±$0,05 de 037 no se heredan; si no cierra por redondeo de lectura, queda pendiente con motivo), proveedor mapeado a `IdContacto`, sin duplicado `(IdContacto, Nro Documento)`. Rubro y centro de costo **obligatorios** (commit 168534b): el mapeo del conector los define por proveedor; si falta, queda pendiente con motivo.
- Los conectores sin `leer_comprobante` bajan y dejan "pendiente de carga manual" (motivo "lector no implementado").
- Nunca crea pagos, asientos ni ajustes.

## R6. Foto de estado de cuenta

- **Decision**: Tablas `Portales_EstadoCuenta` (cabecera por moneda) y `Portales_EstadoCuentaMovimientos`. Al guardar se calcula el saldo del sistema del contacto asociado con la vista de saldos existente (`cuentas_corrientes`), en la misma moneda, al mismo corte. Diferencia ≠ 0,00 ⇒ alerta. **Sin umbral** (Sergio 27/10/2026: los $300 no se aplican). Fotos marcadas `Completa = 0` no se comparan.
- En cuentas en US$ la comparación es en US$ (regla US$ al TC del comprobante).

## R7. Migración de 037

- **Decision**: Tablas nuevas `Portales_*`/`Boveda_*`; script `crear_esquema_boveda_042.py` (respaldo verificado antes, idempotente, `--revertir`) que:
  1. crea los 4 portales de peaje con su autorización del 16/10/2026 y programación semanal equivalente a la tarea actual (leída de `schtasks`, por defecto lunes 07:00),
  2. copia usuario/clave desde `keyring` `LaHerencia-Peajes` a `Boveda_Credenciales` cifradas (no las borra del keyring hasta verificar),
  3. copia `DescargaPeajes_Ejecuciones/EjecucionPortales/Documentos` a `Portales_Corridas`/`Portales_Documentos` conservando claves (sin duplicados por `UNIQUE(IdPortal, Clave)`).
- Las tablas de 037 quedan intactas (solo lectura) para poder revertir. La pantalla `compras/descarga-peajes` se mantiene con el permiso actual de 037 (usuarios que dan de alta compras): muestra corridas y documentos de los 4 peajes y "Descargar ahora", nunca credenciales ni configuración. Contadores: el de peajes (permiso de Compras) se mantiene; el de la bóveda (todos los portales) solo para Administrador.
- Registra Bayá Casal (19/10), Cargill (20/10) y los 7 portales del 27/10 con su autorización; los sin conector quedan "solo bóveda" hasta que se implemente.
