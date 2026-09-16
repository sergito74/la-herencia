# Equipo de agentes La Herencia

Estos agentes trabajan como un equipo para migrar La Herencia a una aplicación web integrada sobre SQL Server.

## Orden de colaboración

1. `integrated-agro-management-engineer` define el proceso y el alcance.
2. `agricultural-production-specialist`, `livestock-health-specialist` y `financial-direction-specialist` validan el significado del negocio.
3. `sql-server-engineer` define consultas, vistas y contratos de datos.
4. `agro-erp-frontend-specialist` define cómo debe organizarse la navegación y el vocabulario del módulo desde la lógica operativa de una empresa agropecuaria, antes de implementar UI.
5. `web-frontend-engineer` implementa la navegación y la experiencia operativa siguiendo esa organización.
6. `python-engineer` automatiza auditorías, análisis y pruebas.

## Reglas compartidas

- SQL Server es la única fuente de datos.
- Los datos actuales son reales: no modificar ni eliminar.
- Trabajar en modo lectura hasta contar con autorización explícita y backup verificado.
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
