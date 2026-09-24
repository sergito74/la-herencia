# Research: Flujo de caja real

## 1. Clasificación de movimientos internos

**Decision**: clasificar como "interno" (excluido del neto operativo, mostrado aparte) los movimientos que cumplan cualquiera de estas reglas, verificadas contra datos reales de `WC`:

1. **Galicia, `[Grupo de Conceptos]` = "Inversiones"** (código 916, ~115 filas reales) → FIMA u otro instrumento financiero. Grupo angosto y sin ambigüedad: no incluye pagos a proveedores ni cobros de clientes.
2. **BNA, `Concepto` contiene el patrón de transferencia entre titulares propios** (`MIS TIT`, `DIS TIT`, `TRANSF.INT.DIST.TITULAR`) **con el CUIT de la propia empresa** (30712114602, confirmado contra la constancia de CBU real de la empresa) en el texto del concepto.

**Rationale**: ambas reglas usan señales ya presentes en los datos reales de origen (no requieren que el usuario clasifique nada a mano), y son angostas — priorizan no clasificar de más (falso positivo: un pago real de proveedor marcado como interno) por sobre no clasificar de menos.

**Alternatives considered**:
- Clasificar todo `[Grupo de Conceptos]` = "Transferencias" de Galicia (907, ~1.113 filas) como interno: **rechazado**. Ese grupo mezcla transferencias a proveedores/terceros (operativas) con transferencias entre cuentas propias — clasificarlo entero como interno ocultaría egresos/ingresos reales del negocio. Queda **fuera de alcance de esta iteración**: esos movimientos se muestran como operativos por defecto, sin marca especial, hasta que haya una regla más fina (posible trabajo futuro: cruzar por CBU destino contra las cuentas propias conocidas).
- Matching de transferencias BNA↔Galicia por importe+fecha (par de movimientos que se cancelan entre las dos cuentas): **rechazado para el MVP** por complejidad (requiere tolerancia de fecha por acreditación bancaria, y no hay garantía de correspondencia 1 a 1 si hay comisiones). El patrón de concepto (regla 2) ya cubre el caso real encontrado en los datos; se revisita si en el futuro aparecen transferencias sin ese patrón de texto.

## 2. Dónde vive el código de agregación

**Decision**: feature nuevo `backend/src/features/flujo_caja/`, que lee `Movimientos BNA`/`Movimientos Galicia` directamente (mismas tablas que usa `tesoreria/repository.py`, sin importar su código).

**Rationale**: Tesorería pagina movimiento a movimiento por medio; Flujo de caja real agrega por período cruzando ambos bancos a la vez — son formas de consulta distintas sobre las mismas tablas, no una extensión natural de `MEDIOS_CONFIG`. Mantenerlos separados evita acoplar la paginación de Tesorería a la agregación de este módulo (constitución VII: cambio simple y reversible en cada lado).

**Alternatives considered**: extender `tesoreria/repository.py` con una función de agregación — rechazado porque mezclaría dos responsabilidades (listar movimientos crudos vs. agregar y clasificar) en el mismo archivo, dificultando tocar una sin arriesgar la otra.

## 3. Movimientos sin contacto/sin clasificar

**Decision**: un movimiento que no cae en ninguna regla de la sección 1 se trata como **operativo por defecto** (no se excluye del neto), pero si además no tiene `IdContacto` asignado se cuenta aparte como "sin clasificar" para que el usuario vea el % (FR-009), sin bloquear el cálculo del neto.

**Rationale**: el neto operativo tiene que poder calcularse siempre; ocultar o excluir por defecto un movimiento sin contacto sería peor que incluirlo con una marca de advertencia (perdería plata real del flujo).

## 4. Período por defecto y rango completo

**Decision**: período por defecto = últimos 24 meses; selector permite rango libre desde 2010-08-31 (apertura de la primera cuenta BNA) en adelante. Ningún dato antes de esa fecha (FR-008, edge case de spec.md).

**Rationale**: acota la carga de la vista principal sin perder acceso al histórico completo cuando el usuario lo necesite explícitamente.
