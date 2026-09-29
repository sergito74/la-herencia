# Data Model: Vincular líneas de resumen de tarjeta a pagos de Impuestos

## Cambio de esquema: `dbo.Tarjetas_Resumenes_Lineas_Compras`

Tabla existente (1.598 filas reales), extendida de forma aditiva
(research.md §1):

| Columna | Cambio | Notas |
|---|---|---|
| `IdVinculo` | sin cambios | PK identity |
| `IdLineaConsumo` | sin cambios | FK a `Tarjetas_Resumenes_Lineas` |
| `IdCompra` | `NOT NULL` → `NULL` | FK a `Compras.IdDeuda`; las filas existentes no se tocan |
| `IdImpuesto` | **nueva**, `NULL` | FK a `Impuestos.IdImpuesto` |
| `ImporteImputado` | sin cambios | money, NOT NULL |

**Constraint nueva**: `CHECK ((IdCompra IS NOT NULL AND IdImpuesto IS NULL) OR (IdCompra IS NULL AND IdImpuesto IS NOT NULL))` — exactamente un origen por vínculo (FR-002/FR-004).

## Documento candidato (forma de datos, sin cambio de esquema de origen)

El diccionario que ya arma `repository._documento_dict` para un
documento de Compras se extiende con:

| Campo | Notas |
|---|---|
| `origen` | `"Compras"` \| `"Impuestos"` — nuevo, discrimina qué es (FR-004) |
| `idCompra` | `None` cuando `origen == "Impuestos"` |
| `idImpuesto` | `None` cuando `origen == "Compras"`; id real cuando es un pago de impuesto |
| `proveedor` | para `origen == "Impuestos"`, es la razón social del organismo (`Contactos` vía `Impuestos.IdOrganismo`) — mismo campo, para no duplicar la forma del objeto, pero el frontend etiqueta distinto según `origen` (FR-004: nunca decir "proveedor" para un organismo en la UI) |
| `saldoPendiente` | solo para `origen == "Impuestos"` (research.md §2) — `Impuestos.Importe` menos lo ya vinculado en otras líneas; `None`/no aplica para Compras (fuera de alcance retroactivo, research.md §2) |

Sin cambios en `moneda`/`tipoDeCambio`/`ajustaTipoCambio` — para Impuestos
siempre `None`/`False` (research.md §3, la tabla no tiene esas columnas).

## Entidades de solo lectura (sin cambios de esquema)

- **Pago de Impuestos**: `dbo.Impuestos` — este feature nunca escribe acá,
  solo lee (`IdOrganismo`, `Importe`, `Fecha`, `Numero de documento`,
  `Periodo liquidado`) para mostrarlo como candidato y vincularlo.
- **Compra**: sin cambios — sigue funcionando exactamente igual
  (research.md §2/§3, FR-007 no regresión).
