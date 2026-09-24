# Feature Specification: Flujo de caja real

**Feature Branch**: `018-flujo-caja-real`

**Created**: 2026-09-24

**Status**: Draft

**Input**: User description: "Consolidar los movimientos bancarios reales ya existentes (BNA con sus 3 cuentas separadas -12301640001709, 12301640029280, 6150111899- y Galicia) en un flujo de caja histórico único, mensual/semanal, con movimientos internos (transferencias propias entre cuentas, suscripciones/rescates de FIMA) excluidos del neto operativo pero visibles aparte. Pantalla en Finanzas → 'Flujo de caja real'."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver el neto mensual real de la empresa (Priority: P1)

Como dueño del campo, quiero ver cuánto entró y cuánto salió de mis cuentas bancarias cada mes, para entender la dinámica real de la plata sin tener que sumar extractos a mano.

**Why this priority**: Es la pregunta que el dueño se hace todo el tiempo ("¿cómo venimos?"); sin esto no hay flujo de caja. Los datos ya existen en el sistema (BNA y Galicia), así que es el entregable de menor riesgo y mayor valor inmediato.

**Independent Test**: Se puede probar completamente abriendo la pantalla "Flujo de caja real" con datos ya cargados en el sistema y verificando que los totales mensuales coincidan con la suma manual de los extractos de Tesorería para el mismo período.

**Acceptance Scenarios**:

1. **Given** que existen movimientos de BNA y Galicia cargados en el sistema, **When** el usuario abre "Flujo de caja real" con el período por defecto, **Then** ve una fila por mes con ingresos, egresos y neto, en pesos con el formato estándar del sistema (miles con punto, decimales con coma).
2. **Given** un mes y una cuenta específicos, **When** el usuario suma manualmente los movimientos de Tesorería para ese mismo rango, **Then** el total coincide exactamente con lo mostrado en Flujo de caja real (antes de excluir movimientos internos).
3. **Given** que el usuario está viendo el flujo mensual, **When** cambia el selector a "Semanal", **Then** la misma información se reagrupa por semana sin perder movimientos ni duplicarlos.

---

### User Story 2 - Distinguir la plata real del negocio de los movimientos internos (Priority: P1)

Como dueño, quiero que las transferencias entre mis propias cuentas y los movimientos hacia/desde el fondo FIMA no infjen el resultado operativo, para no confundir "mover plata de un bolsillo a otro" con ingresos o egresos reales del negocio.

**Why this priority**: Sin esto el flujo de caja miente: solo en 2025-2026 los movimientos de "Inversiones" de Galicia sumaron más de $590 millones entre créditos y débitos, muy por encima del movimiento operativo real. Un flujo de caja que no separa esto no sirve para decidir.

**Independent Test**: Se puede probar cargando un mes con una transferencia conocida entre cuentas propias y verificando que el neto operativo no la incluye, pero que el monto sigue siendo visible en un bloque separado.

**Acceptance Scenarios**:

1. **Given** un movimiento identificado como transferencia entre cuentas propias de la empresa, **When** se calcula el neto operativo del mes, **Then** ese movimiento no se suma al neto pero aparece en un bloque separado "Movimientos internos" con su propio total.
2. **Given** un movimiento de suscripción o rescate del fondo FIMA, **When** se calcula el neto operativo, **Then** ese movimiento se excluye del neto y se muestra en el mismo bloque de movimientos internos, nunca oculto.
3. **Given** el bloque de movimientos internos, **When** el usuario lo revisa, **Then** puede ver el detalle de cada movimiento que lo compone (fecha, cuenta, importe, concepto).

---

### User Story 3 - Distinguir las 3 cuentas históricas del BNA (Priority: P2)

Como dueño, quiero poder ver por separado los movimientos de cada una de las 3 cuentas que tuve en el BNA a lo largo de los años (dos ya dadas de baja, una vigente), para no mezclar información de cuentas distintas bajo un mismo número.

**Why this priority**: El BNA cambió el número de cuenta 3 veces; el sistema históricamente los cargó todos juntos "como si fuera una sola cuenta". Ya migrado el dato base (ver Assumptions), falta que la pantalla lo respete.

**Independent Test**: Se puede probar filtrando el flujo de caja por una de las 3 cuentas BNA y verificando que solo aparecen movimientos de ese número de cuenta específico, dentro de su rango de vigencia real.

**Acceptance Scenarios**:

1. **Given** las 3 cuentas BNA con vigencias distintas, **When** el usuario ve el detalle de un movimiento BNA, **Then** puede identificar a cuál de las 3 cuentas pertenece.
2. **Given** una cuenta BNA ya dada de baja, **When** el usuario consulta un período posterior a su fecha de baja, **Then** no aparecen movimientos de esa cuenta en ese período.

---

### User Story 4 - Saber si los datos están actualizados (Priority: P2)

Como dueño, quiero ver hasta qué fecha tiene carga cada cuenta, para no confundir "no hubo movimientos este mes" con "todavía no cargué el extracto".

**Why this priority**: Los extractos se cargan manualmente y pueden atrasarse; sin esta señal el usuario puede tomar una decisión con información incompleta sin saberlo.

**Independent Test**: Se puede probar comparando la fecha del último movimiento real de cada cuenta contra lo que muestra la pantalla como "última carga".

**Acceptance Scenarios**:

1. **Given** que la cuenta Galicia tiene su último movimiento cargado el 31/08, **When** el usuario abre la pantalla en cualquier fecha posterior, **Then** ve "Última carga: 31/08" junto a esa cuenta, sin importar si el mes actual todavía no tiene movimientos.
2. **Given** un mes sin ningún movimiento cargado para una cuenta, **When** el usuario lo consulta, **Then** la columna de esa cuenta se distingue visualmente entre "sin movimientos reales" y "sin datos cargados aún".

---

### User Story 5 - Ver el detalle de un mes (Priority: P3)

Como dueño, quiero poder hacer clic en un mes o una cuenta y ver los movimientos individuales que lo componen, para verificar o explicar un número puntual sin salir de la pantalla.

**Why this priority**: Mejora la confianza en los números pero no es imprescindible para el valor central del flujo de caja (el resumen agregado).

**Independent Test**: Se puede probar haciendo clic sobre una celda del flujo mensual y verificando que el detalle mostrado suma exactamente el valor de esa celda.

**Acceptance Scenarios**:

1. **Given** una celda de la tabla (mes × cuenta), **When** el usuario hace clic, **Then** se abre un panel con el listado de movimientos individuales de ese cruce, ordenados por fecha.
2. **Given** el panel de detalle abierto, **When** el usuario suma los importes mostrados, **Then** el total coincide con el valor de la celda que lo originó.

### Edge Cases

- ¿Qué pasa si un movimiento no tiene contacto ni concepto claro que permita saber si es interno u operativo? → Se muestra sin clasificar, nunca se descarta ni se asume automáticamente que es operativo o interno.
- ¿Qué pasa si el usuario consulta un período anterior a la apertura de la primera cuenta BNA (antes del 31/08/2010)? → El sistema no debe mostrar saldo ni movimientos anteriores al saldo de apertura conocido; se indica explícitamente que no hay datos antes de esa fecha.
- ¿Qué pasa si dos cuentas BNA estuvieron vigentes al mismo tiempo (superposición real de hasta varios meses durante la migración de cuenta)? → Ambas se muestran como activas en ese período; no se fuerza un único "activo" por fecha.
- ¿Qué pasa si el usuario cambia de vista mensual a semanal a mitad de un mes en curso? → La semana en curso se muestra con los datos disponibles hasta la fecha, sin proyectar ni completar con ceros.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE mostrar, para un período seleccionado, el total de ingresos, egresos y neto operativo agrupado por mes o por semana, según selección del usuario.
- **FR-002**: El sistema DEBE excluir del neto operativo los movimientos clasificados como internos (transferencias entre cuentas propias de la empresa y movimientos hacia/desde inversiones financieras como FIMA), mostrándolos en un bloque separado y visible con su propio total.
- **FR-003**: El sistema DEBE distinguir los movimientos de cada una de las 3 cuentas históricas del BNA y de la cuenta Galicia, respetando el período real de vigencia de cada una.
- **FR-004**: El sistema DEBE mostrar, para cada cuenta, la fecha del último movimiento cargado, de forma visible sin necesidad de navegar a otra pantalla.
- **FR-005**: El sistema DEBE permitir ver el detalle de movimientos individuales que componen cualquier total mostrado (por mes, por cuenta, o la combinación de ambos).
- **FR-006**: El sistema NO DEBE permitir editar ni eliminar movimientos bancarios desde esta pantalla — es una vista de solo lectura sobre datos ya existentes en Tesorería.
- **FR-007**: El sistema DEBE mostrar todos los importes con el formato numérico estándar del proyecto (separador de miles ".", decimales ",", negativos con signo "-" en color rojo).
- **FR-008**: El sistema DEBE permitir acotar la consulta por un rango de fechas, con un período por defecto razonable (los últimos 24 meses) sin impedir consultar el historial completo desde 2010.
- **FR-009**: Cuando un movimiento no pueda clasificarse con certeza como interno u operativo, el sistema DEBE mostrarlo igualmente (nunca ocultarlo ni excluirlo en silencio) y señalar que su clasificación no es automática/cierta.

### Key Entities *(include if feature involves data)*

- **Cuenta bancaria**: representa una cuenta real de un banco (BNA o Galicia) con su número, fecha de apertura, fecha de baja (si corresponde) y saldo de apertura conocido. El BNA tuvo 3 cuentas distintas a lo largo del tiempo; Galicia tiene una sola cuenta vigente desde 2021.
- **Movimiento bancario**: un ingreso o egreso real ya registrado en el sistema (fecha, importe con signo, concepto, cuenta a la que pertenece, contraparte cuando se conoce).
- **Movimiento interno**: un movimiento bancario que mueve fondos entre posiciones propias de la empresa (entre cuentas, o hacia/desde una inversión financiera) sin ser ingreso ni egreso real del negocio agropecuario.
- **Período de consulta**: rango de fechas y granularidad (mensual o semanal) que el usuario elige para ver el flujo de caja.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El dueño puede ver el neto operativo del último mes cerrado en menos de 10 segundos desde que abre el sistema (sin tener que abrir Tesorería ni sumar nada a mano).
- **SC-002**: El total de ingresos/egresos que muestra Flujo de caja real para cualquier cuenta y rango de fechas coincide exactamente (100%) con la suma de los movimientos que muestra Tesorería para ese mismo filtro.
- **SC-003**: Los movimientos internos identificados (transferencias propias, FIMA) representan el 100% de lo detectable por reglas de clasificación automática, mostrado siempre con su propio total, nunca mezclado en el neto operativo.
- **SC-004**: Ningún movimiento bancario histórico queda fuera de las 3 cuentas BNA o de Galicia — el 100% de los movimientos existentes se puede atribuir a una cuenta conocida.
- **SC-005**: El usuario puede identificar, sin ambigüedad, si una cuenta no tiene datos recientes cargados (vs. simplemente no tuvo movimientos), en el 100% de los casos.

## Assumptions

- El saldo de apertura de la cuenta BNA 12301640001709 (-$24.219,37 al 31/08/2010) y la separación de los movimientos históricos de `Movimientos BNA` en sus 3 cuentas reales ya fueron migrados en la base de datos (`WC.CuentasBancarias`, columna `IdCuentaBancaria` en `Movimientos BNA`) antes de esta feature — esta especificación cubre la pantalla y la lógica de consulta, no la migración de datos ya realizada.
- La detección de "movimiento interno" se basa en reglas sobre el concepto/contraparte del movimiento (ej. transferencias entre cuentas propias identificables, conceptos de "Inversiones"/FIMA de Galicia); no requiere que el usuario marque manualmente cada movimiento, aunque puede haber casos sin clasificar que se muestran como tales (ver FR-009).
- El catálogo de tipos de flujo (Operativo/Financiero/Socios/Inversión/Cartera/Ajuste) definido para el conjunto de módulos financieros (018-021) se usa como base de clasificación, pero esta feature solo necesita distinguir "operativo" vs. "interno" para su alcance — las categorías más finas (Socios, Cartera) pertenecen a las features 019/020 y no se muestran acá todavía.
- El período por defecto (últimos 24 meses) es una elección de usabilidad, no una limitación técnica: el historial completo (desde 2010 para BNA, desde 2021 para Galicia) sigue disponible mediante selección de rango.
- Esta feature es de solo lectura sobre datos ya existentes (Tesorería, cuentas bancarias); no incluye carga de nuevos movimientos ni edición — eso ya existe en Tesorería y no se duplica acá.
- La cuenta en efectivo y las cuentas de socios (feature 019) están fuera de alcance de esta especificación — se integrarán al flujo de caja consolidado en una iteración posterior.
