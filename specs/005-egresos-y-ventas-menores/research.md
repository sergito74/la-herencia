# Phase 0 Research: Impuestos, remuneraciones, arrendamientos y ventas de hacienda

## Base técnica

**Decision**: Reutilizar las decisiones de `specs/002-compras`, `specs/003-tesoreria` y `specs/004-cuentas-corrientes` (FastAPI + Pydantic, pyodbc sin ORM, paginación offset/limit vía `db/pagination.py`, pytest + httpx con fixtures, concurrencia vía `run_in_threadpool` sin estado de servidor).

**Rationale**: Quinto y sexto/séptimo/octavo módulo sobre la misma base; no hay motivo técnico para divergir.

**Alternatives considered**: N/A.

## Esquema real confirmado (Phase 0 → resuelto durante `/speckit-clarify`, 2026-09-16)

A diferencia de 002-004, donde la verificación de esquema fue una tarea explícita de Foundational (T004), en este módulo se adelantó a la fase de clarificación de la spec porque las preguntas de negocio (consignatario/comprador, alcance de Remuneraciones) dependían directamente de la estructura real de las tablas. Confirmado contra `INFORMATION_SCHEMA` y datos reales:

| Tabla | PK | Referencia a `Contactos` | Notas |
|---|---|---|---|
| `Impuestos` | `IdImpuesto` | `IdOrganismo` → `IdContacto` (tipo "Organismo") | `IdOrganismo` puede ser NULL |
| `Tipo Impuesto` | `IdTipoImpuesto` | `IdOrganismo` → `IdContacto` | Catálogo, join por `IdTipoImpuesto` |
| `Retenciones` | `IdRetencionSQL` | `IdContacto` directo | Tabla plana, sin catálogo propio |
| `Remuneraciones` | `IdSalario` | `IdContacto` directo (tipo "Empleado") | Es la liquidación; NO tiene FK hacia `Pagos Remuneraciones` |
| `Pagos Remuneraciones` | `IdPago` | `IdEmpleado` → `IdContacto` | Pago efectivo; se relaciona con `Remuneraciones` solo por empleado+período a nivel de presentación (sin FK), per clarificación 2026-09-16 |
| `Alquileres` | `IdAlquiler` | `IdContacto` directo | Solo 5 filas en datos reales — dominio muy chico |
| `Detalles del alquiler` | `IdDetalleAlquiler` | — (via `IdAlquiler`) | Condiciones del contrato (lote, grano) |
| `Detalle Cobro Alquiler` | `IdCobroAlquiler` | — (via `IdAlquiler`) | Cobros/cuotas del contrato |
| `Venta Hacienda` | `IdVenta` | `IdConsignatario` → `IdContacto` | Cabecera de la venta; el consignatario es el intermediario, NO el comprador (clarificación 2026-09-16) |
| `Det_Ventas Hacienda` | `IdDetalleVenta` | `IdComprador` → `IdContacto` | Una venta puede tener varias líneas con compradores distintos (confirmado con datos reales: 11 compradores distintos en 26 líneas de 20 ventas) |
| `Retenciones Ventas Hacienda` | `Id` | `IdContacto` directo | Retención sobre la venta; **el único de estos 5 dominios con valor de `Origen` propio en `vw_MovimientosCuenta_Base`** — la venta en sí no tiene `Origen` propio |
| `Tipo Hacienda` | `IdTipoHacienda` | — | Catálogo simple |

**Resuelto — vínculo `IdOrigen` de cuentas corrientes**: en los 5 valores de `Origen` cubiertos por este spec (`Impuestos`, `Retenciones`, `Remuneraciones`, `Alquileres`, `Ret. Ventas Hacienda`), `IdOrigen` es siempre la clave primaria directa de la tabla correspondiente (`Impuestos.IdImpuesto`, `Retenciones.IdRetencionSQL`, `Remuneraciones.IdSalario`, `Alquileres.IdAlquiler`, `[Retenciones Ventas Hacienda].Id`) — verificado con consultas puntuales contra datos reales, no una suposición. No hay heurística ni intermediarios, igual que el resto de `origen_resolver.py` en 004.

**Rationale**: Mismo patrón que 004 (`origen_resolver.py`): resolución determinística por clave, no probabilística.

**Alternatives considered**: N/A — los datos reales no dejan ambigüedad.

## Extensión de `origen_resolver.py` (specs/004-cuentas-corrientes)

**Decision**: Ampliar el `_MEDIO_POR_ORIGEN_TIPO`-style de mapeo existente en `backend/src/features/cuentas_corrientes/origen_resolver.py` con 5 nuevas entradas (`Impuestos`→`impuesto`, `Retenciones`→`retencion`, `Remuneraciones`→`remuneracion`, `Alquileres`→`arrendamiento`, `Ret. Ventas Hacienda`→`venta_hacienda`), cada una con su propia función de lookup en el `repository.py` del dominio correspondiente (mismo patrón que `get_compra_referencia`/`get_bna_referencia` ya existentes). Los `origenTipo` no cubiertos (`Ret. IVA Granos`) siguen cayendo en el default `fuera_de_alcance`.

**Rationale**: Evita duplicar la lógica de resolución fuera de `origen_resolver.py`; mantiene un único punto de verdad para "qué significa cada valor de `Origen`" (principio VII).

**Alternatives considered**: Crear un resolver propio por dominio — rechazado, fragmentaría la lógica que hoy vive en un solo lugar y complicaría el contrato de `GET .../movimientos` de cuentas corrientes.

## Estructura consignatario/comprador en Ventas de Hacienda

**Decision**: El consignatario se modela a nivel de cabecera de venta; el comprador se modela por línea de detalle. La referencia desde cuentas corrientes (`origen.tipo = "venta_hacienda"`) apunta a la retención (no a la venta ni a una línea específica), por lo que solo expone los datos de cabecera de la venta (fecha, consignatario, documento) — el desglose por comprador se consulta en el propio módulo de ventas de hacienda, no desde la referencia de origen.

**Rationale**: Resuelto en `/speckit-clarify` contra datos reales (una venta puede tener múltiples compradores); forzar un único "comprador" en la referencia de origen sería engañoso.

**Alternatives considered**: Mostrar el comprador de la primera línea en la referencia de origen — rechazado, oculta información real cuando hay múltiples compradores.

## Alcance de Remuneraciones (liquidación + pagos) — CORREGIDO 2026-09-17

**Decision original (clarify 2026-09-16)**: El endpoint de detalle de una liquidación de remuneración traería también sus pagos asociados, emparejados por `IdContacto` (empleado) + período liquidado.

**Corrección (implementación 2026-09-17)**: Al implementar, se verificó contra datos reales que `Pagos Remuneraciones.IdEmpleado` **no es una FK hacia `Contactos`**: sus valores van de 1 a 6 y resuelven a contactos tipo "Proveedor", mientras que los empleados reales referenciados por `Remuneraciones.IdContacto` van de 46 a 632 — espacios de ID completamente distintos, sin relación real. La verificación de `/speckit-clarify` que asumió lo contrario solo comprobó 3 filas con IDs bajos que "por casualidad" resolvían a un contacto en `Contactos`, sin confirmar su `Tipo Contacto`.

**Decision final**: `PagoRemuneracion` se modela y consulta como entidad **independiente** (`GET /api/remuneraciones/pagos`, sin filtro por empleado), igual que `Retención de Venta de Hacienda` — no anidada bajo `Remuneracion`, y sin intentar resolver un contacto/empleado para cada pago (constitution principio IV: no inventar trazabilidad que los datos no respaldan).

**Rationale**: Mostrar una relación empleado↔pago inexistente sería peor que no mostrarla — induciría a error a quien audite una liquidación.

**Alternatives considered**: Mantener el emparejamiento asumido por período/fecha aproximada — rechazado, sería una heurística no solicitada y no confirmada, en un dominio (nómina) donde una asociación incorrecta tiene consecuencias serias.

## Filtro por período en Ventas de Hacienda — respuesta escalada (T052, 2026-09-17)

**Pregunta escalada a `04-integrated-agro-management-engineer`** (per Nota UX de `plan.md`): ¿"campaña" aplica a Ventas de Hacienda con el mismo sentido que en agricultura, o el corte natural ahí es otro?

**Respuesta**: No — "campaña agrícola" está definida por un ciclo biológico (siembra→cosecha) con límites de período naturales y compartidos entre las operaciones de cultivo. La venta de hacienda no tiene un ciclo equivalente: se vende de forma continua durante el año según precio de mercado, estado del animal y oportunidad del consignatario — no según un calendario de siembra/cosecha. Confirmado además por los datos: `Venta Hacienda` solo tiene `Fecha`, sin columna de campaña/ejercicio, así que no hay ningún concepto operativo real detrás de un selector de campaña ahí.

**Decision**: Mantener el filtro de Ventas de Hacienda como rango de fecha libre (`fechaDesde`/`fechaHasta`) + `consignatario`, tal como ya se implementó — no agregar un selector de campaña. Si en el futuro se quiere un atajo de conveniencia, el corte natural para ganadería sería el **ejercicio fiscal** (o "últimos 12 meses"), no campaña — queda como mejora opcional futura, no bloqueante.

**Alternatives considered**: Agregar un selector de campaña como en agricultura — rechazado, sería una ficción de UI sin respaldo en cómo se maneja realmente la venta de hacienda.

## Resolución de NEEDS CLARIFICATION

No quedan marcadores `NEEDS CLARIFICATION` bloqueantes — las 3 clarificaciones de negocio (alcance de `Retenciones`, consignatario/comprador, Remuneraciones+pagos) y la verificación de esquema completa se resolvieron durante `/speckit-clarify` contra datos reales.
