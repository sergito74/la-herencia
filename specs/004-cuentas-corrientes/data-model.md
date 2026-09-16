# Data Model: Cuentas corrientes por proveedor/cliente

## Contacto

Origen: `dbo.Contactos`

| Campo (API) | Columna SQL | Notas |
|---|---|---|
| idContacto | `IdContacto` | PK |
| razonSocial | `Razon Social` | |
| tipoContacto | `Tipo Contacto` | `Banco`, `Comprador`, `Consignatario`, `Empleado`, `Multiple`, `Organismo`, `Proveedor`, `Tarjeta de Credito` |

## Movimiento de cuenta corriente

Origen: `dbo.vw_MovimientosCuenta_Base`

| Campo (API) | Columna SQL | Notas |
|---|---|---|
| fecha | `Fecha` | |
| idContacto | `IdContacto` | |
| documento | `Documento` | |
| numeroDocumento | `Nro Documento` | |
| deuda | `Deuda` | |
| credito | `Credito` | |
| origenTipo | `Origen` | Ej. "Compra", "Tesorería"; determina a qué se resuelve `idOrigen` |
| idOrigen | `IdOrigen` | Clave directa hacia la compra o el movimiento de tesorería (clarificación 2026-09-15) |

## Saldo

Origen: `dbo.vw_MovimientosCuenta_Saldo`

| Campo (API) | Columna SQL | Notas |
|---|---|---|
| idContacto | `IdContacto` | |
| saldoParcial | `SaldoParcial` | Fuente de verdad del saldo — no recalculado en el backend |

## Referencia de origen resuelta

No es una tabla propia; construida por `origen_resolver.py` a partir de `origenTipo`/`idOrigen`.

**Caso compra**:

| Campo (API) | Descripción |
|---|---|
| tipo | `"compra"` |
| idCompra | = `idOrigen` |
| numeroDocumento | de `Compras.Nro Documento` |
| proveedor | de `Compras` → `Contactos.Razon Social` |

**Caso tesorería**:

| Campo (API) | Descripción |
|---|---|
| tipo | `"tesoreria"` |
| medio | derivado de `origenTipo` — ver mapeo cerrado abajo |
| idMovimiento | = `idOrigen` |
| fecha | del movimiento de tesorería correspondiente |
| importe | del movimiento de tesorería correspondiente |

Mapeo cerrado `origenTipo` → `medio` (enum, sin valores libres):

| `origenTipo` | `medio` |
|---|---|
| `Banco Nacion` | `"bna"` |
| `Galicia` | `"galicia"` |
| `Pagos efectivo` | `"efectivo"` |
| `Cobros Valores Recibidos` | `"valores_recibidos"` |
| `Pagos Valores Recibidos` | `"valores_recibidos"` |

Nota (`Pagos efectivo`): en `specs/003-tesoreria` este medio no participa de la referencia heurística hacia compras porque no tiene campo de contacto — pero eso solo afecta a la heurística de tesorería. Acá la resolución es directa vía `IdOrigen` (no heurística), así que la ausencia de contacto en `dbo.[Pagos efectivo]` no bloquea la resolución: alcanza con `idMovimiento`/`fecha`/`importe`. El resolver MUST NOT intentar confirmar que el movimiento de efectivo pertenece al mismo contacto de la cuenta corriente consultada — no hay campo para hacerlo y no es un requisito (FR-006).

Nota (`Cobros`/`Pagos Valores Recibidos`): ambos comparten `medio: "valores_recibidos"`; el sentido (cobro vs. pago) ya se distingue por `deuda`/`credito` del movimiento de cuenta corriente y no requiere un valor de `medio` separado.

**Caso fuera de alcance** (confirmado 2026-09-16 contra datos reales):

| Campo (API) | Descripción |
|---|---|
| tipo | `"fuera_de_alcance"` |
| origenTipo | Valor real de `Origen`: `"Alquileres"`, `"Impuestos"`, `"Remuneraciones"`, `"Retenciones"`, `"Ret. IVA Granos"` o `"Ret. Ventas Hacienda"` |

**Caso no disponible**:

| Campo (API) | Descripción |
|---|---|
| tipo | `"no_disponible"` |
| motivo | ej. "IdOrigen sin cargar" o "registro de origen no encontrado" |

**Mapeo completo de `Origen` → `tipo` de referencia** (12 valores confirmados contra datos reales el 2026-09-16):

| Valor real de `Origen` | `tipo` resuelto | Tabla/medio de destino |
|---|---|---|
| `Compras` | `compra` | `dbo.Compras` (`specs/002-compras`) |
| `Banco Nacion` | `tesoreria` | `dbo.[Movimientos BNA]` (`specs/003-tesoreria`) |
| `Galicia` | `tesoreria` | `dbo.[Movimientos Galicia]` |
| `Pagos efectivo` | `tesoreria` | `dbo.[Pagos efectivo]` |
| `Cobros Valores Recibidos` | `tesoreria` | `dbo.[Valores Recibidos]` |
| `Pagos Valores Recibidos` | `tesoreria` | `dbo.[Valores Recibidos]` |
| `Alquileres` | `fuera_de_alcance` | Sin módulo en alcance actual |
| `Impuestos` | `fuera_de_alcance` | Sin módulo en alcance actual |
| `Remuneraciones` | `fuera_de_alcance` | Sin módulo en alcance actual |
| `Ret. IVA Granos` | `fuera_de_alcance` | Sin módulo en alcance actual |
| `Ret. Ventas Hacienda` | `fuera_de_alcance` | Sin módulo en alcance actual |
| `Retenciones` | `fuera_de_alcance` | Sin módulo en alcance actual |

Nota: no se relevó un valor de `Origen` específico para `Valores propios` ni `Tarjetas` en la muestra consultada — si aparecen en datos reales durante la implementación, tratar como `fuera_de_alcance` por defecto hasta confirmar su tabla de destino.

## Validaciones y reglas transversales

- Ninguna entidad admite escritura (FR-010).
- El módulo MUST NOT calcular ni exponer imputación (rubro/centro de costo/destino) — ese dato se consulta únicamente en `specs/002-compras` (FR-009).
- Los movimientos de contactos tipo "Multiple" MUST deduplicarse a nivel de consulta (FR-014).
