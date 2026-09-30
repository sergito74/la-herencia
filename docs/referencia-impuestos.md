# Referencia de impuestos por organismo

Listado de referencia de los impuestos que la empresa paga a entidades públicas, agrupados por jurisdicción. Fuente: Sergio, 2026-09-30, ampliado ese mismo día con los tipos que ya estaban en uso. Cruzado con el catálogo real `dbo.[Tipo Impuesto]` y con las boletas cargadas en `dbo.Impuestos` a esa fecha.

`Código` es `[Tipo Impuesto].IdOrganismo`, una numeración heredada de Access (1 = AFIP, 2 = ARBA, 3 = Municipalidad de Bolívar) que **no** coincide con `Contactos.IdContacto`.

## Impuestos nacionales — AFIP / ARCA (contacto 119, código 1)

| Impuesto | Tipo en el catálogo | Boletas cargadas | Nota |
|---|---|---|---|
| IVA | 1 · IVA | 5 | |
| Cargas Sociales | 2 · Cargas Sociales | 337 | |
| Autónomos | 5 · Autonomos | 307 | |
| Bienes Sociedad | 13 · Bienes Sociedad | 59 | |
| Impuesto a las Ganancias | 3 · Impuesto a las ganancias | 3 | |
| Anticipo Ganancias | 22 · Anticipo Ganancias | 25 | |
| Intereses | 23 · Intereses | 11 | Intereses por pago fuera de término |
| Retenciones Ganancias | 20 · Retenciones Ganancias | 0 | Ver regla abajo: no es un impuesto propio |

**Regla — Retenciones de Ganancias:** la empresa es agente de retención. Retiene el importe al pagarle a un proveedor y después lo deposita en AFIP/ARCA. Por eso la retención se imputa **al pago del proveedor**, porque es parte de lo que se le debe, y no se trata como un impuesto propio de la empresa. Las retenciones hoy viven en `dbo.Retenciones` (227 certificados, $4.848.584,19) y se reflejan como crédito en la cuenta del proveedor.

## Impuestos provinciales — ARBA (contacto 12, código 2)

| Impuesto | Tipos en el catálogo | Boletas cargadas | Nota |
|---|---|---|---|
| Patentes | — **no existe** | — | Falta en el catálogo |
| Inmobiliario | 6 · Impuesto Inmobiliario | 56 | |
| Ingresos Brutos | 7 · Ingresos Brutos, 12 · Alta Ingresos Brutos, 25 · Percepción Ingresos Brutos | 14 + 1 + 0 | Los tres se agrupan como Ingresos Brutos |
| Sellos | 16 · Imp. De Sellos | 2 | |

**Regla — Percepción de IIBB:** "RECAUDACION ARBA" en el extracto bancario es percepción sin comprobante y va a ARBA. La percepción incluida en una factura queda en la cuenta del proveedor, que después la rinde a ARBA.

## Impuestos municipales — Municipalidad de Bolívar (contacto 72, código 3)

| Impuesto | Tipo en el catálogo | Boletas cargadas | Nota |
|---|---|---|---|
| Tasa Vial | 8 · Tasa Vial | 92 | Los comprobantes se guardan como `…_TasaVial.pdf` |
| Guías | 19 · Guias | 1 | |
| Boleto de Marca | 9 · Boleto de Marca | 5 | |
| Transf. Prop. Hacienda | 10 · Transf. Prop. Hacienda | 1 | |
| Alta Hacienda | 14 · Alta Hacienda | 1 | |

## Impuestos municipales — Municipalidad de Tapalqué (contacto 422, sin código)

| Impuesto | Tipo en el catálogo | Boletas cargadas | Nota |
|---|---|---|---|
| Guías | — **no existe para Tapalqué** | 0 | El tipo 19 · Guias es de Bolívar (código 3); Tapalqué no tiene código propio |

## En el catálogo pero fuera de la referencia (a revisar)

| Organismo | Tipo | Boletas | Observación |
|---|---|---|---|
| AFIP | 11 · ART | 2 | La ART es una aseguradora, no AFIP |
| UATRE (contacto 315) | 15 · Aporte Sindical | 169 | Es un sindicato, no una entidad pública; el tipo figura con el código de AFIP |
| AFIP | 4 · Bienes Personales, 17 · Bienes Sustitutos, 21 · Retenciones IVA | 0 | Sin uso |
| Bolívar | 18 · Permiso de Marca | 0 | Sin uso |
| ARBA | 24 · Sin identificar (generada desde el pago) | 1 | Creado por el backfill 029, para boletas cuyo tipo no se pudo identificar |

## Pendiente de decidir

1. Crear en el catálogo: **Patentes** (ARBA) y **Guías** para Tapalqué, con un código propio para Tapalqué.
2. Revisar ART (11) y Aporte Sindical (15), que figuran como AFIP.
