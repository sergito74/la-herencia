# Data Model: Carga de Compras

Todas las tablas de negocio ya existen en `WC`/`LaHerencia` (confirmadas por `INFORMATION_SCHEMA` e inspección Access, ver el reporte del especialista financiero de esta sesión). Este spec agrega únicamente `CompraEditLocks`. Ninguna FK real existe a nivel de motor SQL Server — toda relación se valida en aplicación (research.md §5).

## Compra (tabla `dbo.Compras`)

| Campo (API) | Columna real | Tipo | Obligatorio en alta | Notas |
|---|---|---|---|---|
| idCompra | IdDeuda (PK, identity) | int | — (generado) | Se expone como `idCompra` en el contrato para consistencia con 002-compras. |
| idContacto | IdContacto | int, nullable | Sí | Debe existir en `Contactos`, tipo ∈ {Proveedor, Multiple, Organismo, Empleado, Banco} (FR-001, FR-013). |
| fecha | Fecha | datetime, nullable | Sí | |
| tipo | Tipo | nvarchar(1), nullable | Sí | Enum: A, B, C, M, X. |
| tipoDocumento | [Tipo documento] | nvarchar(50), nullable | Sí | Enum: Factura, Nota de Crédito, Nota de Débito, C. Deposito Cereales. |
| numeroDocumento | [Nro Documento] | nvarchar(15), nullable | Sí | Máx. 15 caracteres; advertencia (no bloqueo) si se repite para el mismo proveedor (FR-014). |
| moneda | Moneda | nvarchar(255), nullable | Sí | Enum: Pesos, Dolares. |
| tipoDeCambio | [Tipo de Cambio] | money, nullable | Solo si moneda = Dolares | Obligatorio condicional (FR-007). |
| ingresosBrutos | [Ingresos Brutos] | money, nullable | No (default 0) | |
| conceptosNoGravados | [Conceptos no gravados] | money, nullable | No (default 0) | |
| guias | Guias | money, nullable | No (default 0) | |
| comision | Comision | money, nullable | No (default 0) | Entra en el 10.5% de IVA sobre accesorios. |
| financiacion | Financiacion | money, nullable | No (default 0) | Entra en el 10.5% de IVA sobre accesorios. |
| gastosVarios | [Gastos Varios] | money, nullable | No (default 0) | Entra en el 10.5% de IVA sobre accesorios. |
| leyDeSellos | [Ley de Sellos] | money, nullable | No (default 0) | |
| resGral4169 | [Res gral 4169/96] | money, nullable | No (default 0) | |
| documentoOriginal | [Documento Original] | nvarchar(MAX), nullable | No | Texto libre/observaciones. |
| ajustaTipoCambio | [Ajusta Tipo Cambio] | bit, default 0 | No | |

Columnas del esquema real no expuestas en v1 (Assumptions del spec): `Fecha Vto`, `IdOperacion`.

**Campos calculados (no se persisten como input directo del usuario, se derivan y se muestran)**:
- `subtotalNeto` = Σ(línea.cantidad × línea.precioUnitario)
- `ivaCabecera` = Σ(línea.subtotal × línea.iva / 100) + 0.105 × (comision + guias + financiacion + gastosVarios)
- `importeTotal` = subtotalNeto + ivaCabecera + ingresosBrutos + conceptosNoGravados + guias + comision + financiacion + gastosVarios + leyDeSellos + resGral4169
- Bloque `pesificado.*` = cada uno de los anteriores × tipoDeCambio, presente solo si moneda = Dolares (si moneda = Pesos, el contrato omite el bloque `pesificado` en vez de duplicar los mismos valores — más simple para el frontend que "tipo de cambio implícito 1").

## Línea de Detalle (tabla `dbo.Det_Compras`)

| Campo (API) | Columna real | Tipo | Obligatorio | Notas |
|---|---|---|---|---|
| idDetalleCompra | IdDetalleCompra (PK, identity) | int | — (generado) | |
| idCompra | IdCompra | int, nullable | Sí (FK lógica) | Asignado por el backend al insertar dentro de la misma transacción que la cabecera. |
| productoServicio | [Producto/Servicio] | nvarchar(50), nullable | Sí | Texto libre; dispara sugerencia de rubro (FR-012a) y autocompletado contra `CnsU Producto` (ver quickstart). |
| cantidad | Cantidad | real, nullable | Sí | Sin validar > 0 (FR-004a). |
| precioUnitario | [Precio Unitario] | float, nullable | Sí | Sin validar > 0 (FR-004a). |
| iva | IVA | real, nullable | Sí | Porcentaje (ej. 21, no 0.21). |
| unidad | Unidad | nvarchar(255), nullable | No (default vacío) | Combo contra `UnidadesMedida`. |
| idCentroCostos | IdCentroCostos | int, nullable | No (default "Adm. General") | Debe existir en `[Centro de costos]` si se especifica (FR-013). |
| idDestino | IdDestino | int, nullable | No (default "General") | Debe existir en `DestinoCompras` si se especifica (FR-013). |
| idRubro | IdRubro | int, nullable | No | Debe existir en `Rubros` si se especifica (FR-013); sugerido pero no forzado por FR-012a. |
| campaña | Campaña | nvarchar(15), nullable | No (default "No Aplica") | Ver research.md §4 sobre resolución del nombre de columna. |
| ajusteFinanciero | [Ajuste financiero] | bit, default 0 | No | |

Columna del esquema real no expuesta en v1: `IdFormulado`.

**Campos calculados**: `subtotal` = cantidad × precioUnitario; `importeIva` = subtotal × iva / 100.

## Vencimiento (tabla `dbo.[Vencimiento Compras]`)

| Campo (API) | Columna real | Tipo | Obligatorio | Notas |
|---|---|---|---|---|
| idVencimiento | IdVencimiento (PK, identity) | int | — (generado) | |
| idCompra | IdCompra | int, nullable | Sí (FK lógica) | |
| fechaVencimiento | [Fecha de vencimiento] | datetime, nullable | Sí (si se agrega un vencimiento) | Sin monto — el esquema real no lo tiene (confirmado). |

## CompraEditLocks (tabla nueva, `WC` únicamente)

| Campo | Tipo | Notas |
|---|---|---|
| IdCompra | int, PK | 1 lock activo por compra como máximo. |
| LockToken | uniqueidentifier, NOT NULL | Generado por el frontend por sesión de edición (research.md §2). |
| LockedAt | datetime, NOT NULL | |
| ExpiresAt | datetime, NOT NULL | `LockedAt + 15 minutos`, renovable. |

No se replica en `LaHerencia` (no es dato de negocio migrado, es infraestructura de esta app — igual que las tablas de sistema `usuarios`/`sesiones_*` ya excluidas del alcance de migración).

## Reglas de validación cruzada (aplicación, no motor de base)

1. `idContacto` debe existir en `Contactos` con `Tipo Contacto` ∈ {Proveedor, Multiple, Organismo, Empleado, Banco} — HTTP 400 si no.
2. Si `moneda = "Dolares"`, `tipoDeCambio` es obligatorio y > 0 — HTTP 400 si falta.
3. Cada línea requiere `productoServicio`, `cantidad`, `precioUnitario`, `iva` no nulos (aunque puedan ser 0/negativos, FR-004a) — HTTP 400 si falta alguno.
4. `idRubro`/`idCentroCostos`/`idDestino`, si se especifican, deben existir en su catálogo — HTTP 400 si no.
5. Al menos una línea es obligatoria para guardar (FR-002) — HTTP 400 si la lista de líneas viene vacía.
6. Si existe una compra previa del mismo `idContacto` con el mismo `numeroDocumento` (y no es la misma compra que se está editando), la respuesta incluye una advertencia no bloqueante (`warnings: [...]`), no un error (FR-014).
7. `PUT /api/compras/{id}` requiere un `LockToken` vigente y coincidente para esa compra — HTTP 409 si no.

## Relaciones

```
Compra (1) ──< Línea de Detalle (0..N)
Compra (1) ──< Vencimiento (0..N)
Compra (N) ──> Contacto (1)          [FK lógica, sin constraint real]
Línea de Detalle (N) ──> Rubro (0..1), Centro de Costos (0..1), Destino (0..1), Campaña (0..1)   [FKs lógicas]
Compra (1) ──< CompraEditLock (0..1)  [infraestructura, no dato de negocio]
```
