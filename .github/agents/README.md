# Equipo de agentes La Herencia

Estos agentes trabajan como un equipo para migrar La Herencia a una aplicación web integrada sobre SQL Server.

## Orden de colaboración

1. `integrated-agro-management-engineer` define el proceso y el alcance.
2. `agricultural-production-specialist`, `livestock-health-specialist` y `financial-direction-specialist` validan el significado del negocio.
3. `sql-server-engineer` define consultas, vistas y contratos de datos.
4. `agroux-lead-product-architect` diseña la arquitectura de producto completa: árbol de navegación, design system y especificación funcional de cada pantalla — se consulta antes de diseñar o rediseñar cualquier pantalla o flujo nuevo. `agro-erp-frontend-specialist` queda para consultas puntuales de nomenclatura/agrupación de un módulo aislado, siempre alineadas con el design system que define el arquitecto de producto.
5. `web-frontend-engineer` implementa los componentes y la experiencia operativa siguiendo esa especificación.
6. `python-engineer` automatiza auditorías, análisis y pruebas.

## Reglas compartidas

- Antes de trabajar, leer `AGENTS.md` o `CLAUDE.md` y seguir `.specify/memory/agent-guidance.md`; ambos agentes usan la misma Constitución y las mismas specs.
- SQL Server es la única fuente de datos.
- Usar `WC` como base mutable de desarrollo. No conectar la aplicación nueva a la base oficial `LaHerencia` durante el desarrollo.
- Preservar la base oficial y los archivos Access locales del sistema que sigue en uso. La futura puesta en marcha sobre la base oficial requiere aprobación separada.
- Documentar supuestos, fórmulas, fuentes y decisiones.
- Coordinar antes de crear una tabla, vista, endpoint, indicador o regla de negocio nueva.

## Fuentes base consultadas

- Microsoft Learn, SQL Server Relational Databases
- MDN Learn Web Development
- Python Documentation
- FAO Investment Centre y FAO Animal Health
- SENASA Argentina
- COSO Internal Control Integrated Framework
- IFRS Standards Navigator
