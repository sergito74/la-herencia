# Spec Kit en La Herencia

Spec Kit 1.0.7 está instalado para GitHub Copilot mediante skills locales.

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

- SQL Server es la única fuente de datos.
- La base contiene datos reales: no modificar ni eliminar sin autorización explícita.
- Toda escritura requiere backup completo y verificado previamente.
- Las primeras especificaciones y APIs deben ser de solo lectura.
- Cada módulo debe expresar un proceso de negocio, no solo exponer tablas.
- Revisar los agentes especializados de `.github/agents/` antes de planificar una funcionalidad.

El workspace no tenía un repositorio Git inicializado al momento de instalar Spec Kit. Conviene inicializarlo y crear una línea base antes de comenzar el primer ciclo de especificación.
