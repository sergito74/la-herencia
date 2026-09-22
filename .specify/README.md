# Spec Kit en La Herencia

Spec Kit 1.0.7 está instalado desde `https://github.com/github/spec-kit.git`, tag `v1.0.7` (commit `fe1d00e3ccaf495880aaf90fb0e17679e82f065b`), con instrucciones para Codex, Claude y GitHub Copilot. Codex es la integración predeterminada desde el 2026-09-22. Codex y Claude comparten las specs y reglas del repositorio mediante `AGENTS.md`, `CLAUDE.md` y `.specify/memory/agent-guidance.md`.

## Flujo recomendado para la migración

1. `/speckit-constitution` para fijar principios del proyecto.
2. `/speckit-specify` para describir un módulo acotado.
3. `/speckit-clarify` para resolver ambigüedades.
4. `/speckit-plan` para diseñar la implementación contra el código y SQL existentes.
5. `/speckit-tasks` para dividir el trabajo.
6. `/speckit-analyze` para revisar consistencia.
7. `/speckit-implement` para ejecutar las tareas aprobadas.
8. `/speckit-converge` para encontrar brechas restantes.

## Restricciones de este proyecto

- Leer `.specify/memory/agent-guidance.md` y `.specify/memory/constitution.md` antes de usar Spec Kit. Son las instrucciones compartidas para Claude y Codex.
- SQL Server `WC` es la base mutable de desarrollo; el usuario autorizó escrituras de desarrollo dentro de `WC`.
- La base oficial `LaHerencia` debe permanecer intacta durante el desarrollo. Su puesta en marcha requiere una decisión y aprobación separadas.
- Los archivos Access del sistema actual deben preservarse sin cambios mientras sigan en uso.
- Cada módulo debe expresar un proceso de negocio, no solo exponer tablas.
- Revisar los agentes especializados de `.github/agents/` antes de planificar una funcionalidad.

Claude y Codex comparten las mismas especificaciones de `specs/`, la misma Constitución y el mismo ciclo Spec Kit. Los archivos `AGENTS.md` y `CLAUDE.md` apuntan a la guía común para que las instrucciones no diverjan.

El índice de módulos y el significado de `Status: Draft` están documentados en [`specs/README.md`](../specs/README.md). `Draft` no equivale a "sin código": se debe contrastar con las tareas, implementación y Git.


## Uso con Codex

Spec Kit es la herramienta acordada para el desarrollo de este proyecto. Las diez skills de Codex están en `.agents/skills/` y usan la misma infraestructura PowerShell y las mismas especificaciones que Claude.

En el chat de Codex se invocan como `$speckit-specify`, `$speckit-clarify`, `$speckit-plan`, `$speckit-tasks`, `$speckit-analyze`, `$speckit-implement` y `$speckit-converge`. También están disponibles `$speckit-constitution`, `$speckit-checklist` y `$speckit-taskstoissues`. Las referencias `/speckit-*` de arriba representan las mismas fases en otras integraciones.

Instalación realizada con `specify integration install codex --script ps --force` y `specify integration use codex`. En ese comando de instalación, `--force` permite coexistencia con Copilot; no regeneró ni sobrescribió las especificaciones existentes. Se verificó por SHA-256 que `specs/`, `.specify/memory/`, `.claude/` y `.github/` quedaron intactos durante la instalación.

`specify integration status` confirma Codex como predeterminado, plantillas alineadas y cero archivos gestionados modificados o faltantes. Conserva el diagnóstico previo `unsafe-multi-install`: esta versión no declara Copilot compatible con instalación múltiple. Las integraciones existentes se conservan y esta limitación no se oculta ni se corrige alterando los metadatos del instalador.
