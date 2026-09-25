# Research: Cuentas corrientes de socios/directores y condominio

## 1. Modelo de inmutabilidad y anulación

**Decision**: `MovimientosCuentaSocio` sigue el mismo patrón que `AplicacionesPago` (019): nunca se hace `UPDATE`/`DELETE` sobre una fila ya creada. Deshacer una asignación o una devolución significa poner `Anulada = 1` (+ `MotivoAnulacion`, `UsuarioAnulacion`, `FechaAnulacion`), nunca borrar ni modificar el importe/origen original.

**Rationale**: decidido explícitamente en `/speckit-clarify` (2026-09-26), replicando un patrón ya validado y con tests reales en 019. El saldo de un socio se calcula siempre `SUM(Importe con signo) WHERE Anulada = 0`, la misma regla que ya usa `aplicaciones_pago.repository.estado_movimiento`.

**Alternatives considered**: borrado físico al deshacer — rechazado explícitamente por el usuario en la clarificación (perdería la trazabilidad de "esto se cargó y se corrigió", que es justamente el valor de tener auditoría).

## 2. Por qué una tabla de auditoría separada, no el patrón liviano de otras features

**Decision**: `AuditoriaReflejoSocio` es una tabla de solo-inserción (append-only), independiente de `MovimientosCuentaSocio`. Cada fila registra una *acción* (asignar, revertir asignación, registrar devolución, revertir devolución) con `Usuario`, `Fecha`, `IdMovimiento` (a qué fila de la cuenta corriente corresponde) y un detalle.

**Rationale**: decisión ya tomada por el usuario con el equipo de especialistas el 2026-09-24 (confirmada por el agente de búsqueda en memoria persistente, `project_flujo_caja_financiero.md`): explícitamente **no** el patrón liviano de imputación que ya usan otras features (ej. las columnas `Origen`/`NotaConciliacion` agregadas directamente a `AplicacionesPago` en 020). La razón de fondo: acá el reflejo es *automático* (no una acción manual del usuario elemento por elemento como en 019/020), y una tabla de auditoría separada dejaría rastro incluso si en el futuro se decide cambiar cómo se calcula o se muestra el movimiento en sí, sin mezclar "qué pasó" con "cuál es el saldo actual".

**Alternatives considered**: agregar columnas de auditoría directamente a `MovimientosCuentaSocio` (como se hizo en 020 con `AplicacionesPago`) — rechazado, es la decisión que el usuario ya había descartado explícitamente el 24/09.

## 3. Cómo calcular el "importe bruto real" de un gasto marcado como particular

**Decision**: reutilizar la misma fórmula ya implementada y corregida en `tarjetas_resumenes/repository.py` (`_APLICA_PARTICULAR`/`_IMPORTE_BRUTO`, corregida 2026-09-26 para reconocer tanto `Precio Unitario` negativo como `Cantidad` negativa en la línea "particular"): el importe bruto es el total de la compra *antes* de la línea negativa que la netea a $0. Se extrae esa lógica a una función compartida (ej. `compras.particular.importe_bruto(id_compra)` o similar) para que tanto el módulo de tarjetas como el de cuentas de socios usen la misma fuente de verdad, en vez de duplicar la consulta SQL en dos lugares.

**Rationale**: la fórmula ya está validada contra datos reales (2JM, ACA Bolívar, Agüero Shamaim, Cumo Store) y tuvo dos bugs reales corregidos recientemente — reimplementarla en un segundo lugar arriesgaría reintroducir los mismos problemas. Consistente con Constitución Principio VII (simplicidad, no duplicar lógica).

**Alternatives considered**: que el usuario tipee manualmente el importe a asignar — rechazado, ya existe el dato real calculable, pedirlo a mano es una fuente de error (es literalmente el bug que motivó esta conversación: importes mal cargados a mano).

## 4. Origen inicial de las asignaciones: solo compras "particular"

**Decision**: para esta primera versión, la única acción de "marcar un gasto como de un socio" disponible en la UI parte de una `Compra` ya identificada con el patrón "particular" (`GranTotal = 0` vía línea negativa). El campo `Origen`/`IdOrigen` en `MovimientosCuentaSocio` queda diseñado como genérico (`varchar(20)`/`int`) para poder extender a otros orígenes (tesorería, remuneraciones) sin cambiar el esquema, pero la UI de esta versión solo ofrece el flujo desde Compras.

**Rationale**: acordado en Clarifications de la spec; evita construir una superficie de UI genérica ("marcar cualquier movimiento como de un socio") antes de validar el flujo con el caso real que la motivó.

**Alternatives considered**: exponer la asignación desde todos los módulos de tesorería/compras/remuneraciones de entrada — pospuesto, no bloquea el valor de esta versión.

## 5. Prevención de doble asignación (FR-009)

**Decision**: índice único filtrado en SQL Server: `CREATE UNIQUE INDEX ... ON MovimientosCuentaSocio (Origen, IdOrigen) WHERE Anulada = 0 AND Origen IS NOT NULL AND Tipo = 'AsignacionGasto'`. Un mismo origen (ej. una Compra) no puede tener más de una asignación vigente simultánea — hay que anular la anterior antes de crear una nueva.

**Rationale**: enforced a nivel de base, no solo aplicación — consistente con Constitución Principio IV/V (integridad de datos verificada, no solo confiada al código de la UI).

**Alternatives considered**: validación solo en el backend antes del INSERT — insuficiente por sí sola (carrera entre dos requests simultáneos), pero se mantiene igual como primera línea de validación con mensaje de error legible; el índice es la garantía final.
