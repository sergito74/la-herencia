# Feature Specification: Trabajos eventuales vinculados a Remuneraciones

**Created**: 2026-10-29 | **Status**: Especificado para implementación
**Input**: Sergio solicita módulo dentro de Personal, basado en Planilla trabajos eventuales.xlsx y vinculado con Remuneraciones.

## Clarifications
- Sergio confirmó: cada trabajo puede vincularse total o parcialmente a una liquidación, sin contar el importe dos veces.
- Sergio confirmó: incorporar histórico conservando importes, recibos y estados, revisando lo existente para no duplicarlo.

## User Scenarios & Testing
### User Story 1 — Administrar trabajos (P1)
Registrar fecha, trabajador, descripción, días (incluyendo fracciones), jornal y viáticos. Consultar totales, estado de pago y recibo; editar datos conservando trazabilidad.
**Independent Test**: crear medio día a $10.000 más $1.000 de viáticos → $6.000. Filtrar y editar sin afectar liquidaciones existentes.
**Acceptance**: validación de cantidades e importes; no sobrescribir total ya vinculado por un valor menor; usuario Lectura no puede escribir.

### User Story 2 — Relacionar liquidaciones (P1)
Desde un trabajo consultar liquidaciones del mismo trabajador y distribuir importes en una o varias; desde una liquidación consultar los trabajos incluidos.
**Independent Test**: trabajo $10.000, vincular $6.000 a liquidación, visualizar $4.000 sin vincular. Una segunda vinculación no puede exceder el total ni la capacidad neta de la liquidación.
**Acceptance**: solo mismo trabajador, importe positivo, control acumulado en ambos extremos, navegación recíproca, desvinculación reversible. Vincular no genera deuda, pago ni modifica conceptos del recibo.

### User Story 3 — Incorporar planilla (P2)
Importar 75 trabajos históricos y sus recibos, con identidad fiscal y origen por fila, sin repetir al ejecutar nuevamente. Conservar los cinco redondeos explícitos y estados de pago declarados.
**Independent Test**: 75 registros, total $2.500.558, ocho trabajadores; segunda importación no agrega trabajos. Comparar con remuneraciones existentes y conservar los casos no inequívocos para vinculación manual.

### Edge Cases
- Trabajo parcialmente vinculado, liquidación con varios trabajos, mismo día y trabajador con labores distintas.
- Trabajador sin contacto: resolver CUIT/CUIL antes de crear, nunca unir por parecido de nombres.
- Total histórico redondeado distinto de días × jornal + viáticos: conservar total y diferencia explícita.
- Estado Pagado de la planilla no acredita un movimiento nuevo de caja; no crear pagos.
- Recibos 1/2 tienen detalle anterior no presente en Trabajos; conservar cabeceras y detalles como respaldo, sin sumar nuevamente sus importes a los 75 trabajos. Detalles 3/4 duplican conceptos de Trabajos.
- Liquidación borrada o editada: vínculos mantienen integridad y no permiten alterar importes por debajo de lo vinculado en este módulo. El alta/lector habitual de liquidaciones continúa funcionando.

## Requirements
- FR-001: acceso Personal > Trabajos eventuales con filtros de trabajador, fechas, pago y vinculación, paginación y resumen del conjunto filtrado.
- FR-002: alta/edición de trabajo con validación, cálculo monetario al centavo y redondeo explícito opcional.
- FR-003: distinguir Total del trabajo, Incluido en liquidaciones y Sin vincular; este último no se presenta como deuda adicional ni como saldo por pagar.
- FR-004: registrar estado Pendiente/Pagado, número de recibo y observación; no ejecutar pagos bancarios ni de caja.
- FR-005: vincular importes a liquidaciones existentes del mismo trabajador, con límites acumulados atómicos en ambos extremos; permitir quitar vínculo.
- FR-006: enlaces recíprocos por trabajador y liquidación exacta; mostrar trabajos asociados desde Remuneraciones.
- FR-007: importar histórico de fuente en solo lectura de forma idempotente, con respaldo verificado antes de esquema/escrituras masivas; sin alterar remuneraciones, movimientos de caja ni archivo Excel.
- FR-008: trazabilidad del origen, autor y cambios; lectura para sesiones válidas y escritura según permisos existentes.
- FR-009: vinculación histórica automática solo para coincidencias inequívocas documentadas (mismo trabajador, período, neto exacto y candidato único); no convertir coincidencia de importe por sí sola en vínculo.

### Key Entities
Trabajo eventual; trabajador/contacto; recibo histórico y detalle de respaldo; distribución de importe a liquidación; auditoría de cambios.

## Success Criteria
- SC-001: los 75 trabajos conservan $2.500.558 y las ocho identidades fiscales de la fuente.
- SC-002: un reintento de importación produce cero duplicados.
- SC-003: se puede acceder desde un trabajo a su liquidación y volver al detalle de sus trabajos en un paso.
- SC-004: se rechazan excesos de vinculación, trabajador diferente e importes inválidos, incluidos intentos concurrentes.
- SC-005: el histórico importado no aumenta las deudas ni pagos existentes.

## Assumptions
Moneda pesos. Días hasta cuatro decimales; importes monetarios al centavo. El módulo administra labores y distribuye lo ya liquidado; las liquidaciones y sus pagos siguen en sus procesos actuales. No se calculan impuestos laborales nuevos. La planilla es evidencia histórica de trabajos y estado declarado; no se presume fecha ni medio de pago faltante. No se modifica Excel.


## Ampliación solicitada por Sergio: adicional de Sierra (29/10/2026)
Incorporar en Remuneraciones cálculo del adicional fuera de recibo de Sierra, Antonio Marcelo, basado en `Personal/Remuneraciones modif..xlsx`, hoja Liquidaciones Encargado, columnas AF:AK: AG=MROUND(AF*30%,5), AH=MROUND(AF*8.5%,5), AJ=AG+AH+AI, siendo AI ajuste manual variable y AF neto del recibo. Se usa el neto fiscal real de la liquidación, excluyendo la Bonificación adicional ya registrada; no se extrapolan los brutos calculados de la planilla vieja. El archivo llega hasta agosto 2026 y no contiene octubre.

Presentar cada parte y el total a cobrar; permitir guardar en la columna existente Bonificacion adicional de esa misma liquidación, manteniendo los conceptos fiscales intactos y sin crear otro recibo/pago. Antes de guardar muestra el adicional actual. Calcular no guarda. Tabla auxiliar RemuneracionesAdicionalCalculo por IdSalario conserva componentes, ajuste, usuario y fecha; auditoría de la operación en tabla 045. Al consultar una liquidación histórica con adicional existente, mostrar el importe registrado junto al cálculo propuesto; nunca recalcular/grabar históricos en bloque. Sergio eligió redondear el total automáticamente hacia arriba a la centena. Se mantiene el redondeo individual a múltiplos de $5; el ajuste final pasa a ser la diferencia hasta la centena (si ya es centena exacta no se agrega otra). No hay ajuste manual en pantalla. Calcular no cambia datos: Guardar adicional aplica el resultado a la liquidación seleccionada. Límites de trabajos vinculados se revalidan antes de modificar total.

Hallazgo adicional de fuente de eventuales: fila 47 cancelada por lluvia tiene cero días y cero importe. Se conserva como antecedente dentro de los 75 registros, sin vínculo posible; esquema admite cero histórico, alta nueva exige días y total positivos. Una descripción ausente se presenta como Sin descripción en la planilla, sin inventar labor.
