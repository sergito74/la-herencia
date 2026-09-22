# Especificaciones funcionales

Esta carpeta contiene la fuente funcional compartida por Claude y Codex. La guía de agentes está en [`../.specify/memory/agent-guidance.md`](../.specify/memory/agent-guidance.md), y las normas de arquitectura en [`../.specify/memory/constitution.md`](../.specify/memory/constitution.md).

## Cómo interpretar el estado

`Status: Draft` en un `spec.md` describe la revisión/aprobación de los requisitos. **No significa por sí solo que el módulo no esté implementado.** Para saber qué falta, comparar la spec con `tasks.md`, el código actual, las pruebas existentes y Git. Una tarea marcada completa sin el artefacto esperado tampoco es evidencia suficiente.

## Índice de módulos

| Spec | Dominio | Documentación disponible |
|---|---|---|
| `001-cuentas-tesoreria` | Cuentas y tesorería inicial | spec, checklist |
| `002-compras` | Consulta y trazabilidad de compras | spec, plan, tareas, investigación, modelo, contrato, quickstart, checklist |
| `003-tesoreria` | Tesorería | spec, plan, tareas, investigación, modelo, contrato, quickstart, checklist |
| `004-cuentas-corrientes` | Cuentas corrientes | spec, plan, tareas, investigación, modelo, contrato, quickstart, checklist |
| `005-egresos-y-ventas-menores` | Impuestos, remuneraciones, arrendamientos y ventas menores | spec, plan, tareas, investigación, modelo, contrato, quickstart, checklist |
| `006-carga-compras` | Alta y edición de compras | spec, plan, tareas, investigación, modelo, contrato, quickstart, checklist |
| `007-ventas-hacienda-granos` | Ventas de hacienda y granos | spec, plan, tareas, investigación, modelo, contrato, quickstart, checklist |
| `008-tarjetas` | Tarjetas, cuotas y resúmenes | spec, plan, tareas, investigación, modelo, contrato, quickstart, checklist |
| `009-conciliacion-tarjetas` | Conciliación manual de tarjetas | spec |
| `010-remitos` | Remitos y control de stock | spec |
| `011-ordenes-trabajo` | Órdenes de trabajo agrícolas | spec, plan, tareas, investigación, modelo, contrato, quickstart, checklist |
| `012-resultado-costos-cultivo` | Resultado y costos de cultivo | spec, plan, tareas, investigación, modelo, contrato, quickstart, checklist |
| `013-carga-resumenes-excel` | Confirmar carga de resúmenes bancarios BNA/Galicia (completa 003 US3) | spec, plan, tareas, investigación, modelo, contrato, quickstart, checklist, validación |

## Reanudar trabajo interrumpido

Antes de continuar una implementación, revisar `git status` y preservar todos los cambios locales. Para el módulo 012, la implementación fue iniciada con `/speckit-implement` y quedó interrumpida; continuar desde el código y las tareas existentes en `012-resultado-costos-cultivo/tasks.md`, no reiniciar ni regenerar el trabajo.
