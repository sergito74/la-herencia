# Feature Specification: Inicio con indicadores reales del negocio

**Feature Branch**: `015-inicio-kpis`

**Created**: 2026-09-22

**Status**: Draft

**Input**: User description: "Candidato #3 del relevamiento de funciones adicionales (2026-09-22): la pantalla de inicio (frontend/src/app/page.tsx) hoy es un menú de 4 tarjetas de proceso sin ningún indicador consolidado real entre módulos, y además está desactualizada — sigue mostrando 'Producción — próximamente' aunque Órdenes de Trabajo, Remitos y Resultado de Cultivo (010/011/012) ya están migrados, y no lista Tarjetas en el menú de Finanzas aunque NavHeader.tsx sí la tiene. Agregar indicadores reales (deuda total a proveedores vía 014, líneas de tarjeta pendientes de conciliar vía 009, resultado de la campaña agrícola actual vía 012) sin fabricar ningún número que no venga de un endpoint ya existente, y corregir el contenido desactualizado."

## Clarifications

### Session 2026-09-22

- Q1 (alcance de "indicadores reales"): ¿se agregan endpoints nuevos de agregación, o se reusan exclusivamente los que ya existen? → **A: Solo los que ya existen** — `GET /api/cuentas-corrientes/saldos` (014), `GET /api/tarjetas-resumenes/pendientes` (009), `GET /api/resultado-cultivo/campania/{id}` (012) y `GET /api/arrendamientos` (ya usado hoy). Ningún indicador se "inventa": si no hay un endpoint que ya lo calcule, no entra en esta spec (mismo criterio ya aplicado al KPI de arrendamientos existente).
- Q2 (qué pasa si un indicador tarda o falla): la pantalla de inicio es la primera que ve el usuario todos los días. ¿Un error en un indicador bloquea toda la pantalla? → **A: No** — cada indicador se carga y falla de forma independiente (mismo patrón que ya usa `CuotasArrendamientoKpis`, que hoy simplemente no renderiza nada si `data` no llegó); un indicador caído no debe impedir ver el resto ni el menú de procesos.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver de un vistazo la salud financiera y operativa del negocio (Priority: P1)

Un usuario administrativo, al entrar al sistema por la mañana, necesita ver de un vistazo la deuda total con proveedores, cuántas líneas de tarjeta quedan sin conciliar, y el resultado de la campaña agrícola en curso, sin tener que entrar módulo por módulo para armarse una idea general.

**Why this priority**: Es el valor central de esta spec — sin indicadores reales, la pantalla de inicio sigue siendo solo un menú, y el usuario repite el mismo recorrido manual todos los días.

**Independent Test**: Puede probarse entrando a la pantalla de inicio y verificando que la deuda total a proveedores coincide con la suma de saldos negativos de `/api/cuentas-corrientes/saldos`, que las líneas de tarjeta pendientes coinciden con el `total` de `/api/tarjetas-resumenes/pendientes`, y que el resultado de campaña coincide con `/api/resultado-cultivo/campania/{id}` de la campaña actual.

**Acceptance Scenarios**:

1. **Given** la pantalla de inicio, **When** carga, **Then** muestra la deuda total a proveedores (suma de saldos negativos de todos los contactos, 014), calculada a partir del mismo endpoint que ya usa el listado de saldos.
2. **Given** la pantalla de inicio, **When** carga, **Then** muestra la cantidad de líneas de resumen de tarjeta pendientes de conciliar (009), con un link directo a la bandeja de conciliación.
3. **Given** la pantalla de inicio, **When** carga, **Then** muestra el resultado consolidado de la campaña agrícola actual (superficie, margen bruto, rentabilidad — mismos campos que ya expone 012), con un link directo al módulo de Resultado de Cultivo.
4. **Given** uno de los tres indicadores nuevos falla o tarda, **When** el usuario ve la pantalla, **Then** los otros indicadores y el menú de procesos se muestran igual, sin bloquear ni mostrar un error general de página (Clarifications Q2).

---

### User Story 2 - Encontrar cualquier módulo migrado desde el inicio (Priority: P2)

Un usuario que entra al sistema necesita que el menú de la pantalla de inicio refleje todos los módulos realmente migrados, sin que le falte ninguno ni le sobren placeholders de "próximamente" para cosas que ya existen.

**Why this priority**: Es una corrección de contenido desactualizado, no una función nueva — de menor prioridad que los indicadores (US1), pero necesaria porque hoy el menú activamente desinforma (dice "próximamente" sobre algo que ya está migrado desde hace semanas).

**Independent Test**: Puede probarse comparando el menú de la pantalla de inicio contra `NavHeader.tsx` (fuente de verdad de la navegación) y verificando que todos los módulos con submenú ahí aparecen también en la pantalla de inicio.

**Acceptance Scenarios**:

1. **Given** la pantalla de inicio, **When** el usuario la ve, **Then** la tarjeta de "Producción" lista sus módulos reales (Planificación agrícola, Remitos, Existencias de insumos, Órdenes de trabajo, Resultado de cultivo), no un mensaje de "próximamente".
2. **Given** la pantalla de inicio, **When** el usuario ve la tarjeta de "Finanzas", **Then** incluye el link a Tarjetas, igual que ya lo tiene `NavHeader.tsx`.

### Edge Cases

- ¿Qué pasa si no hay ninguna campaña con datos (sistema recién instalado)? El indicador de campaña actual debe mostrar un estado vacío explícito ("sin datos de campaña"), nunca un error ni un número inventado.
- ¿Qué pasa si todos los contactos tienen saldo $0 (deuda total $0)? Se muestra "$0" tal cual, no se oculta el indicador ni se confunde con "no disponible".
- ¿Qué pasa si `/api/tarjetas-resumenes/pendientes` devuelve 0? Se muestra "0 líneas pendientes" con tono neutro/positivo, no de advertencia.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST mostrar en la pantalla de inicio la deuda total a proveedores, calculada como la suma de los saldos negativos de `GET /api/cuentas-corrientes/saldos` (014) — sin sumar los saldos a favor, que no son "deuda".
- **FR-002**: El sistema MUST mostrar en la pantalla de inicio la cantidad de líneas de resumen de tarjeta pendientes de conciliar, tomada de `GET /api/tarjetas-resumenes/pendientes` (009), con un link a `/finanzas/tarjetas/conciliacion`.
- **FR-003**: El sistema MUST mostrar en la pantalla de inicio el resultado consolidado de la campaña agrícola actual (superficie, margen bruto, rentabilidad en pesos y dólares), tomado de `GET /api/resultado-cultivo/campania/{idCampaniaActual}` (012, reusando `GET /api/resultado-cultivo/campanias` para conocer cuál es la actual), con un link a `/produccion/resultado-cultivo`.
- **FR-004**: El sistema MUST NOT calcular ni fabricar ningún indicador que no provenga de un endpoint ya existente (Clarifications Q1) — mismo criterio que ya aplica el KPI de arrendamientos.
- **FR-005**: El sistema MUST cargar cada indicador de forma independiente — si uno falla o tarda, los demás y el menú de procesos deben mostrarse igual (Clarifications Q2).
- **FR-006**: El sistema MUST actualizar el menú de "Producción" de la pantalla de inicio para listar sus módulos reales (Planificación agrícola, Remitos, Existencias de insumos, Órdenes de trabajo, Resultado de cultivo), quitando el mensaje de "próximamente".
- **FR-007**: El sistema MUST agregar el link a Tarjetas en el menú de "Finanzas" de la pantalla de inicio.
- **FR-008**: El sistema MUST mostrar un estado vacío explícito para el indicador de campaña cuando no haya ninguna campaña con datos, sin error ni número inventado.
- **FR-009**: El sistema MUST operar en modo lectura — ningún indicador nuevo escribe en `WC`.

### Key Entities *(include if feature involves data)*

- **Indicador de inicio**: composición de datos ya existentes (deuda total, tarjetas pendientes, resultado de campaña), sin entidad ni tabla propia — se calcula en el cliente a partir de 3 endpoints ya existentes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un usuario ve los 3 indicadores nuevos (deuda total, tarjetas pendientes, resultado de campaña) en menos de 5 segundos desde que abre la pantalla de inicio.
- **SC-002**: La deuda total mostrada coincide exactamente con la suma manual de saldos negativos del listado de saldos (014), verificado contra datos reales.
- **SC-003**: El menú de "Producción" de la pantalla de inicio lista los mismos módulos que `NavHeader.tsx`, sin ningún placeholder de "próximamente" para módulos ya migrados.
- **SC-004**: Si cualquiera de los 3 indicadores nuevos falla, el resto de la pantalla (menú de procesos, otros indicadores) sigue siendo usable, verificado simulando la falla de cada uno por separado.

## Assumptions

- "Campaña actual" usa el mismo criterio ya definido en 012 (`campaniaActualId` de `GET /api/resultado-cultivo/campanias`), no una nueva regla de negocio.
- El indicador de deuda total no distingue por tipo de contacto (proveedor vs. otros) — usa todos los saldos negativos de 014 tal cual, ya que 014 no filtra por tipo de contacto.
- No se agregan indicadores de otros dominios (ventas, remuneraciones, impuestos) en esta primera iteración — el candidato #4 del relevamiento (auditoría) y futuras iteraciones pueden ampliar esta pantalla.
