# Instrucciones compartidas para agentes

Este documento es la guía común de trabajo para Claude Code, Codex y cualquier otro agente que trabaje en el repositorio. `AGENTS.md` y `CLAUDE.md` solo indican a cada herramienta que lea esta guía; las reglas del proyecto se mantienen aquí y en la Constitución, no se copian entre archivos de agente.

## Autoridad y contexto

1. Seguir la instrucción más reciente del usuario.
2. Tratar `.specify/memory/constitution.md` como norma de arquitectura y seguridad.
3. Para una funcionalidad, usar como fuente funcional su `spec.md` y los contratos/modelos/decisiones de la misma carpeta `specs/NNN-*/`.
4. Antes de editar, leer `memory.md`, esta guía, la documentación relevante y el código actual. La memoria es contexto histórico y puede estar desactualizada; no prevalece sobre la Constitución ni sobre una aclaración posterior del usuario.
5. Si código, memoria y especificación discrepan, no ocultar la discrepancia: señalarla y actualizar los documentos afectados en el mismo cambio cuando el alcance lo permita.

## Bases de datos y archivos Access

- `WC` es la copia de trabajo del sistema. Es la base prevista para desarrollo, pruebas funcionales y las escrituras de la aplicación durante esta etapa. No pedir autorización de nuevo para cada escritura normal de desarrollo sobre `WC` cuando la tarea del usuario ya la implique.
- La base SQL Server oficial `LaHerencia` debe preservarse intacta durante el desarrollo. No ejecutar escrituras, DDL, migraciones ni pruebas con efectos secundarios contra ella, ni configurar la aplicación nueva para usarla durante el desarrollo.
- El paso futuro desde `WC` a la base oficial requiere una decisión explícita de puesta en marcha, reconciliación de cambios ingresados entretanto y un plan de respaldo/restauración. No asumir que la autorización para usar `WC` autoriza ese paso.
- Los archivos Access locales pertenecen al sistema que sigue en uso. Son artefactos protegidos: no borrarlos, reemplazarlos, modificar sus datos ni ejecutar scripts que los alteren. Su eventual retiro requiere una decisión posterior del usuario.
- La aplicación nueva usa SQL Server a través del backend Python. No agregar una conexión directa del navegador a SQL Server, nuevas dependencias de Access, ni persistencia paralela.

## Forma de trabajar con Spec Kit

- Claude y Codex usan el mismo Spec Kit, las mismas carpetas `specs/`, la misma Constitución y el mismo Git. No iniciar una metodología paralela para uno de los agentes.
- Para trabajo funcional, respetar la fase de Spec Kit que corresponda (`specify`, `clarify`, `plan`, `tasks`, `analyze`, `implement`, `converge`). No regenerar una especificación aprobada solo por preferencia del agente.
- Antes de implementar, leer `spec.md`, `plan.md`, `tasks.md` y los documentos existentes de `research.md`, `data-model.md`, `contracts/`, `quickstart.md` y `checklists/`.
- En `/speckit-implement`, continuar desde el estado real de `tasks.md` y del código. Revisar `git status` y los cambios locales antes de tocar archivos. Preservar trabajo existente de Claude/Codex; no descartar ni sobrescribir cambios ajenos.
- Marcar una tarea como terminada solo cuando el código/documentación pedido esté presente y las verificaciones requeridas para esa tarea se hayan completado. No confundir checklist de calidad de una especificación con checklist de implementación.
- Mantener juntas la especificación y su implementación: si una decisión cambia, actualizar la spec/contrato/plan/tareas afectados. No declarar un módulo terminado por la sola existencia de código.

## Arquitectura y calidad

- Stack objetivo: Python + FastAPI, SQL Server, Next.js + TypeScript, Tailwind CSS y TanStack Query, según la Constitución vigente.
- Organizar el backend por módulos en `backend/src/features/` y el frontend por rutas/componentes/servicios en `frontend/src/`, siguiendo el patrón existente del módulo más cercano.
- Las consultas SQL deben usar parámetros, objetos conocidos y límites apropiados. Mantener los resguardos centrales de conexión; nunca construir SQL ejecutable con datos libres del usuario.
- Cada cambio debe ser acotado, revisable y reversible; preservar los cambios locales sin commit y evitar refactors ajenos al alcance.
- Añadir o ejecutar verificaciones solo cuando el usuario o la tarea activa lo pida o lo requiera expresamente. No afirmar que algo fue probado si no se ejecutó.
- No instalar dependencias, publicar, hacer push, modificar datos fuera de `WC` ni ejecutar acciones destructivas salvo que el usuario lo solicite explícitamente.

## Comunicación

- Hablar con el usuario en español claro y coloquial. Explicar términos técnicos con palabras sencillas la primera vez.
- Informar discrepancias, decisiones asumidas, riesgos concretos y verificaciones realizadas. No esconder incertidumbre ni convertir una inferencia en un hecho.

