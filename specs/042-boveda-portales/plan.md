# Implementation Plan: Bóveda de portales y sincronización periódica

**Branch**: `042-boveda-portales` | **Date**: 2026-10-27 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/042-boveda-portales/spec.md`

## Summary

Nuevo módulo `features/boveda` que generaliza `descarga_peajes` (037): registro de portales con enlace, credenciales cifradas (AES-256-GCM con clave maestra en el Administrador de credenciales de Windows), autorización registrada, programación por portal ejecutada por un planificador dentro del backend (solo con la app abierta), conectores en código con interfaz común (ingresar, listar documentos, estado de cuenta, leer comprobante), carga automática en Compras con la regla de cierre exacto de 037 para todos los portales, y fotos de estado de cuenta comparadas al centavo con el saldo del sistema. Acceso a la bóveda solo para el rol Administrador; la pantalla de peajes de Compras conserva su permiso actual sin exponer credenciales. Cierre de comprobantes al centavo, sin tolerancia. Los 4 peajes se migran sin perder historial; la tarea semanal de Windows se retira. Conectores nuevos en orden: Bayá Casal, Cargill, ARCA, ARBA, Municipalidad de Bolívar, Sancor, Allianz, Jáuregui y Morales, Lartirigoyen. Detalle en [research.md](research.md).

## Technical Context

**Language/Version**: Python 3.13 (`backend/.venv`); TypeScript (Next.js 14)

**Primary Dependencies**: FastAPI, pyodbc, pdfplumber, playwright, keyring, cryptography (todas ya instaladas; ninguna nueva). Frontend: TanStack Query, Tailwind

**Storage**: SQL Server `WC`: tablas nuevas `Boveda_*` y `Portales_*` ([data-model.md](data-model.md)); compras vía `compras.repository.create_compra`; PDFs en la carpeta de Compras del ejercicio (Dropbox); clave maestra en Windows Credential Manager

**Testing**: pytest con repositorio y conectores simulados (no escribe en `WC`); lectores contra PDFs reales locales con skip si faltan; `npm run build`

**Target Platform**: PC de Sergio (Windows 11), backend local lanzado por `launcher/LaHerencia.ps1`

**Project Type**: Web app (backend FastAPI + frontend Next.js)

**Performance Goals**: tick del planificador 60 s; corrida de un portal < 3 min; pantalla de bóveda < 1 s

**Constraints**: solo lectura en portales; sin eludir captcha/2FA; secretos nunca en logs/Git/respuestas (salvo revelar); una corrida por portal a la vez, portales en serie; respaldo verificado antes del DDL; comparación de saldos sin umbral

**Scale/Scope**: ~15 portales, decenas de documentos por mes, 1 usuario

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Cumplimiento |
| --- | --- |
| I. WC sistema de registro | ✅ Todo en `WC`; no toca `LaHerencia` ni Access |
| II. Protección de datos | ✅ Respaldo verificado antes del DDL y de la migración; tablas 037 intactas para revertir; tests sin escrituras en `WC` |
| III. Proceso de negocio | ✅ Portal → autorización → programación → documentos → compra cargada / pendiente → foto de saldo vs sistema |
| IV. Trazabilidad | ✅ Documento ↔ corrida ↔ portal ↔ compra; foto con fecha de corte y moneda; auditoría de toda acción sobre la bóveda |
| V. Contrato primero | ✅ [contracts/api.md](contracts/api.md) antes de la UI; tests de contrato, cifrado y planificador |
| VI. Especialistas | ✅ Revisión de checkpoint con agentes de seguridad/Python y dirección financiera (carga automática y fotos de saldo) |
| VII. Simplicidad / reversible | ✅ Hilo + tick, sin colas ni scheduler externo; envuelve conectores 037 sin reescribirlos; `--revertir` |
| VIII. Stack aprobado | ✅ Sin dependencias nuevas |
| Seguridad | ✅ Secretos cifrados con AAD, clave fuera de la base, solo Administrador, `no-store`, `Secreto.__repr__` enmascarado, auditoría |

Excepciones de política registradas: acceso a portales externos solo lectura/descarga autorizado por Sergio: peajes 16/10/2026, Bayá Casal 19/10/2026, Cargill 20/10/2026, ARCA/ARBA/Municipalidad de Bolívar/Sancor/Allianz/Jáuregui y Morales/Lartirigoyen 27/10/2026 (Clarifications de spec.md).

**Re-check post-diseño**: sin violaciones; Complexity Tracking vacío.

## Project Structure

### Documentation (this feature)

```text
specs/042-boveda-portales/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/api.md
└── tasks.md            # /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── scripts/
│   ├── crear_esquema_boveda_042.py      # DDL + respaldo + migración 037 + alta de portales + --revertir
│   ├── boveda_clave.py                  # generar / exportar / importar clave maestra (.lhkey)
│   └── instalar_descarga_peajes.ps1     # + -Desinstalar (retira la tarea semanal)
├── src/features/boveda/
│   ├── cifrado.py        # clave maestra (keyring), AES-GCM con AAD, clase Secreto
│   ├── repository.py     # tablas Boveda_*/Portales_*
│   ├── servicio.py       # correr_portal(): autorización, lock, conector, documentos, carga, foto
│   ├── planificador.py   # hilo de tick, próxima corrida, recuperación única
│   ├── carga.py          # generalización de descarga_peajes/carga.py
│   ├── estado_cuenta.py  # foto + saldo del sistema (vista de saldos existente) + diferencia
│   ├── router.py         # /api/boveda/* (exige Administrador)
│   ├── schemas.py
│   └── conectores/
│       ├── __init__.py   # interfaz Conector + registro CONECTORES
│       ├── peajes.py     # envuelve descarga_peajes/portales.py y lectores.py
│       ├── baya_casal.py
│       ├── cargill.py
│       └── arca.py, arba.py, municipalidad_bolivar.py, sancor.py, allianz.py, jauregui_morales.py, lartirigoyen.py
├── src/features/descarga_peajes/router.py   # pasa a leer/disparar vía boveda (compatibilidad)
└── src/main.py                              # include_router + arranque del planificador
└── tests/boveda/

frontend/src/
├── app/boveda/page.tsx                  # lista de portales, estado, programación
├── app/boveda/[id]/page.tsx             # detalle: credencial, autorización, corridas, documentos, fotos
├── components/boveda/                   # PortalForm, CredencialForm, Programacion, Corridas, Documentos, EstadoCuenta, Revelar
├── services/bovedaApi.ts
├── app/compras/descarga-peajes/page.tsx # se mantiene para usuarios de Compras (sin credenciales)
└── components/layout/NavHeader.tsx      # entrada "Bóveda" solo Administrador + contador
```

**Structure Decision**: módulo nuevo `boveda` siguiendo el patrón de `descarga_peajes`; 037 queda como capa de compatibilidad y fuente de los conectores de peaje.

## Fases de entrega

1. **Bóveda + migración de peajes** (US1, US2, US4, US6 para peajes): cifrado, tablas, UI, planificador, conectores de peaje envueltos. Retiro de la tarea semanal tras verificar una corrida programada.
2. **Bayá Casal y Cargill** (relevados): documentos, estado de cuenta, carga automática.
3. **Conectores con relevamiento** (uno por portal, en el orden de FR-023): relevar → implementar → verificar con una corrida manual → programar.

## Complexity Tracking

Sin violaciones.
