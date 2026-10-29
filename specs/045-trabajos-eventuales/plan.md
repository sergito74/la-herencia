# Plan: Trabajos eventuales (045)

Python/FastAPI y SQL Server WC; Next.js/TypeScript/Tailwind/TanStack Query. Sin dependencias nuevas. Constitución: una única persistencia, respaldo verificado antes de DDL/importación; Access y LaHerencia intactos. Contrato antes de UI, controles transaccionales y pruebas simuladas.

1. Definir esquema aditivo dbo.TrabajosEventuales, dbo.TrabajosEventualesVinculos, dbo.TrabajosEventualesAuditoria y dbo.TrabajosEventualesFuentes. Índices para trabajador/fecha, origen único y par trabajo/liquidación. Claves a Contactos/Remuneraciones cuando esquema permita; operaciones verifican existencia.
2. Backend en backend/src/features/trabajos_eventuales/: modelos tipados, repositorio, router. Alta/edición, lista/detalle, candidatos y distribución con bloqueo central. No mutar deudas/pagos.
3. Migración/importador scripts/trabajos_eventuales_045.py: simulación predeterminada, --aplicar con respaldo, fuente XML en memoria, CUIT normalizado, importación idempotente, respaldo original externo, informe de vínculos seguros y pendientes.
4. Frontend /personal/trabajos-eventuales, componente con listado/formulario/detalle/distribución. Integrar menú y enlaces por contacto y liquidación desde Remuneraciones. No mostrar códigos internos en pantallas.
5. Pruebas backend de cálculos, límites y contrato; compilar frontend y revisar flujo. Verificar lectura WC y cantidades/total de importación. Registrar aplicación y pendientes en validacion.md.

## Riesgos y mitigaciones
Pagado histórico no equivale a prueba nueva de pago; no se crean movimientos. Coincidencias ambiguas permanecen sin vincular. Redondeos explícitos preservados. La edición de un trabajo no cambia su identidad si tiene vínculos; no se reduce total debajo de lo vinculado. Desvincular no borra remuneraciones. No se introducen borrados de trabajos: edición con auditoría conserva historia.


## Ampliación solicitada por Sergio: adicional de Sierra (29/10/2026)
Incorporar en Remuneraciones cálculo del adicional fuera de recibo de Sierra, Antonio Marcelo, basado en `Personal/Remuneraciones modif..xlsx`, hoja Liquidaciones Encargado, columnas AF:AK: AG=MROUND(AF*30%,5), AH=MROUND(AF*8.5%,5), AJ=AG+AH+AI, siendo AI ajuste manual variable y AF neto del recibo. Se usa el neto fiscal real de la liquidación, excluyendo la Bonificación adicional ya registrada; no se extrapolan los brutos calculados de la planilla vieja. El archivo llega hasta agosto 2026 y no contiene octubre.

Presentar cada parte y el total a cobrar; permitir guardar en la columna existente Bonificacion adicional de esa misma liquidación, manteniendo los conceptos fiscales intactos y sin crear otro recibo/pago. Antes de guardar muestra el adicional actual. Calcular no guarda. Tabla auxiliar RemuneracionesAdicionalCalculo por IdSalario conserva componentes, ajuste, usuario y fecha; auditoría de la operación en tabla 045. Al consultar una liquidación histórica con adicional existente, mostrar el importe registrado junto al cálculo propuesto; nunca recalcular/grabar históricos en bloque. Sergio eligió redondear el total automáticamente hacia arriba a la centena. Se mantiene el redondeo individual a múltiplos de $5; el ajuste final pasa a ser la diferencia hasta la centena (si ya es centena exacta no se agrega otra). No hay ajuste manual en pantalla. Calcular no cambia datos: Guardar adicional aplica el resultado a la liquidación seleccionada. Límites de trabajos vinculados se revalidan antes de modificar total.

Hallazgo adicional de fuente de eventuales: fila 47 cancelada por lluvia tiene cero días y cero importe. Se conserva como antecedente dentro de los 75 registros, sin vínculo posible; esquema admite cero histórico, alta nueva exige días y total positivos. Una descripción ausente se presenta como Sin descripción en la planilla, sin inventar labor.
