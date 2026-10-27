# Implementation Plan: Rutina automática de documentos nuevos

**Branch**: `043-rutina-documentos-nuevos` (se trabaja sobre `main`, como 042) | **Date**: 2026-10-27 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/043-rutina-documentos-nuevos/spec.md`

## Summary

Una rutina interna del backend corre todos los días a las 7:00 y a las 14:00: sincroniza las cuentas automatizadas de la bóveda (042, más De Campo a Campo), lee por Outlook los mails nuevos desde la última corrida, guarda los comprobantes en sus carpetas, carga solos los que tienen lector probado y registra todo en `DocumentosNuevos`. El menú muestra por módulo cuántos hay para revisar; el clic abre "Nuevos para revisar" con el documento cargado. Se retira el listado de revisión de la bóveda. Detalle de decisiones en [research.md](research.md).

## Technical Context

**Language/Version**: Python 3.13 (backend), TypeScript / Next.js (frontend)

**Primary Dependencies**: FastAPI, pyodbc, Playwright (Chrome/Chromium), pdfplumber, pywin32 (Outlook COM); TanStack Query, Tailwind

**Storage**: SQL Server `WC` (tablas nuevas en [data-model.md](data-model.md)); archivos en Dropbox/Documents según [research.md R3](research.md)

**Testing**: pytest (unitarias del clasificador y la marca de mails; contrato de API con datos simulados); `tsc --noEmit`

**Target Platform**: computadora de la oficina (Windows 11, Outlook clásico, Chrome instalado), backend local

**Project Type**: aplicación web (backend + frontend)

**Performance Goals**: una corrida completa en menos de 15 minutos (11 cuentas en serie + mails del medio día)

**Constraints**: solo lectura en portales y mails; nada de Ganadera San Justo; nada se crea en Contactos; cierre al centavo para cargar solo; interfaz sin términos internos

**Scale/Scope**: ~12 cuentas, decenas de mails por día, 6 módulos de aviso

## Constitution Check

| Principio | Cumple | Cómo |
|---|---|---|
| I. SQL Server es el registro | Sí | Todo en `WC`; nada en `LaHerencia` ni Access |
| II. Protección de datos | Sí | Respaldo verificado antes del esquema; pruebas con datos simulados |
| III. Procesos antes que tablas | Sí | El aviso lleva al módulo de negocio con el documento, no a una tabla técnica |
| IV. Trazabilidad | Sí | Cada documento guarda origen (cuenta o mail), archivo, registro creado y quién revisó |
| V. Contrato primero | Sí | [contracts/api.md](contracts/api.md) antes de la UI; pruebas de contrato |
| VI. Exactitud de dominio | Sí | Imputación igual a la manual; lectores incorporados uno por uno contra cargas reales |
| VII. Simplicidad y reversibilidad | Sí | Reusa planificador, conectores y carga de 042; script de esquema con `--revertir` |
| VIII. Stack aprobado | Sí | Python, SQL Server, Next.js, Tailwind, TanStack Query; sin dependencias nuevas |

Sin violaciones. Re-chequeo post-diseño: sin cambios.

## Project Structure

### Documentation (this feature)

```text
specs/043-rutina-documentos-nuevos/
├── spec.md, plan.md, research.md, data-model.md, quickstart.md
├── contracts/api.md
├── checklists/requirements.md
└── tasks.md            # /speckit-tasks
```

### Source Code

```text
backend/
├── scripts/crear_esquema_rutina_043.py          # tablas nuevas + quitar Portales_Documentos.Revisado
├── src/features/documentos_nuevos/
│   ├── repository.py      # DocumentosNuevos, Rutina_*
│   ├── router.py          # /api/documentos-nuevos (contracts/api.md)
│   ├── rutina.py          # corrida: cuentas + mails + registro; horario 07:00/14:00
│   ├── mails.py           # lectura Outlook por almacén con marca (reusa boveda/mails.py)
│   ├── clasificador.py    # tipo, emisor, receptor, módulo, carpeta
│   └── lectores/          # registro de lectores (peajes, Allianz, Movistar; luego los de scripts)
├── src/features/boveda/
│   ├── planificador.py    # agrega el tick de la rutina
│   ├── servicio.py        # cada documento de portal también genera DocumentosNuevos
│   ├── router.py, repository.py   # se retiran /revision y /revisado
│   └── conectores/decampoacampo.py
└── tests/ (unit + contract)

frontend/src/
├── services/documentosNuevosApi.ts
├── components/layout/NavHeader.tsx              # números por módulo
├── components/documentos-nuevos/NuevosParaRevisar.tsx   # lista + detalle + Revisado
├── app/compras, app/ventas/*, app/finanzas/{tesoreria,cuentas-corrientes,impuestos}  # ?nuevos=1
└── components/boveda/RevisionCargas.tsx          # se elimina
```

**Structure Decision**: módulo nuevo `documentos_nuevos` en backend (patrón de `boveda`), componente compartido en frontend que cada módulo monta con su `modulo`.

## Fases de entrega (para tasks)

1. Esquema + registro `DocumentosNuevos` + avisos en el menú + vista de revisión (con lo que ya bajan las cuentas); retirar el listado de la bóveda. → cumple la regla de Sergio desde el primer día.
2. Rutina programada (07:00/14:00) que corre todas las cuentas.
3. Lectura de mails nuevos + clasificador + carpetas.
4. Conector De Campo a Campo (solo Giamigli).
5. Lectores adicionales, uno por tarea (retenciones, liquidaciones Cargill, resúmenes Visa/ML, extractos) contra cargas reales.

## Complexity Tracking

Sin violaciones de la Constitución.
