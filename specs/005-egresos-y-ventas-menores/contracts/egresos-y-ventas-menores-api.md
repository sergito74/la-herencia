# API Contract: Impuestos, remuneraciones, arrendamientos y ventas de hacienda (solo lectura)

Todos los endpoints son `GET`. Ningún endpoint admite escritura (FR-008).

## Impuestos — prefijo `/api/impuestos`

### GET /api/impuestos

Busca/lista movimientos de impuestos (FR-001).

**Query params**: `organismo` (razón social, búsqueda parcial), `fechaDesde`, `fechaHasta`, `page`, `pageSize`.

**Response 200**:

```json
{
  "items": [
    {
      "idImpuesto": 14,
      "fecha": "2011-05-16",
      "tipoImpuesto": "Ingresos Brutos",
      "periodoLiquidado": "2011-04",
      "numeroDocumento": "0001-00000123",
      "importe": 1500.00,
      "organismo": "ARBA"
    }
  ],
  "page": 1,
  "pageSize": 50,
  "total": 1076
}
```

### GET /api/impuestos/retenciones

Busca/lista retenciones impositivas genéricas (FR-001).

**Query params**: `contacto` (razón social, búsqueda parcial), `fechaDesde`, `fechaHasta`, `page`, `pageSize`.

**Response 200**: análoga a `/api/impuestos`, con `idRetencion`, `numeroCertificado`, `fecha`, `contacto`, `importe`.

## Remuneraciones — prefijo `/api/remuneraciones`

### GET /api/remuneraciones

Busca/lista liquidaciones de remuneraciones (FR-002).

**Query params**: `empleado` (razón social, búsqueda parcial), `periodoLiquidado`, `page`, `pageSize`.

**Response 200**:

```json
{
  "items": [
    {
      "idSalario": 1829633151,
      "empleado": "Juan Pérez",
      "fechaPago": "2019-11-30",
      "periodoLiquidado": "2019-11",
      "importe": 85000.00
    }
  ],
  "page": 1,
  "pageSize": 50,
  "total": 631
}
```

### GET /api/remuneraciones/pagos

Busca/lista pagos efectivos de remuneraciones, **como listado independiente** (FR-002; confirmado contra datos reales que `Pagos Remuneraciones.IdEmpleado` no es una FK hacia `Contactos` — ver `data-model.md`/`research.md`).

**Query params**: `page`, `pageSize` (sin filtro por empleado: no hay clave confiable para ese filtro).

**Response 200**:

```json
{
  "items": [
    { "idPago": 501, "fecha": "2019-12-02", "cuenta": "BNA", "caja": null, "importe": 85000.00 }
  ],
  "page": 1,
  "pageSize": 50,
  "total": 205
}
```

## Arrendamientos — prefijo `/api/arrendamientos`

### GET /api/arrendamientos

Busca/lista contratos de arrendamiento con sus cobros asociados (FR-003).

**Query params**: `contacto` (razón social, búsqueda parcial), `page`, `pageSize`.

**Response 200**:

```json
{
  "items": [
    {
      "idAlquiler": 138210671,
      "fecha": "2011-08-09",
      "inicioPeriodo": "2011-09-01",
      "finPeriodo": "2012-08-31",
      "contacto": "Estancia El Rincón",
      "importeTotalContrato": 500000.00,
      "cantidadCuotas": 6,
      "cobros": [
        {
          "idCobroAlquiler": 3001,
          "numeroCuota": 1,
          "importeCuota": 83333.33,
          "estado": "Cobrado",
          "fechaVencimiento": "2011-10-01"
        }
      ]
    }
  ],
  "page": 1,
  "pageSize": 50,
  "total": 5
}
```

`cobros` MUST ser una lista vacía (no omitida) cuando el contrato no tenga cobros registrados todavía.

## Ventas de Hacienda — prefijo `/api/ventas-hacienda`

### GET /api/ventas-hacienda

Busca/lista ventas de hacienda con sus líneas de detalle por comprador (FR-004).

**Query params**: `consignatario` (razón social, búsqueda parcial), `fechaDesde`, `fechaHasta`, `page`, `pageSize`.

**Response 200**:

```json
{
  "items": [
    {
      "idVenta": 1,
      "fecha": "2024-06-01",
      "consignatario": "Consignataria del Sur S.A.",
      "numeroDocumento": "2024-0042",
      "lineas": [
        {
          "idDetalleVenta": 10,
          "comprador": "Frigorífico Norte S.A.",
          "tipoHacienda": "Novillo",
          "cantidad": 45,
          "unidadMedida": "cabezas",
          "pesoTotal": 13620.0,
          "precioUnitarioA": 7.45,
          "precioUnitarioB": 1.5930
        }
      ]
    }
  ],
  "page": 1,
  "pageSize": 50,
  "total": 26
}
```

`lineas` MUST tener al menos un elemento (una venta sin líneas no es un caso de negocio válido, per datos reales). Cada línea MUST mostrar su propio `comprador` — el sistema MUST NOT mezclar ni promediar entre compradores de una misma venta. Cada línea MUST exponer `precioUnitarioA` y `precioUnitarioB` tal cual están en el origen (`Det_Ventas Hacienda`) — el sistema MUST NOT calcular un "importe total" de línea combinándolos, porque no hay una regla confirmada contra datos reales sobre cómo se relacionan entre sí (ver `data-model.md`).

### GET /api/ventas-hacienda/retenciones

Busca/lista retenciones sobre ventas de hacienda, **como listado independiente** (FR-004; no existe clave confiable para vincular una retención a una venta específica — ver `data-model.md`/`research.md`).

**Query params**: `contacto` (razón social, búsqueda parcial), `fechaDesde`, `fechaHasta`, `page`, `pageSize`.

**Response 200**: análoga a `/api/impuestos/retenciones`, con `idRetencion`, `fecha`, `contacto`, `documento`, `numeroDocumento`, `importe`.

## Ampliación de `GET /api/cuentas-corrientes/contactos/{id}/movimientos` (specs/004-cuentas-corrientes)

`origen.tipo` se amplía con 4 nuevos valores posibles: `"impuesto"`, `"retencion"`, `"remuneracion"`, `"arrendamiento"`, `"venta_hacienda"` (5 en total, ver `data-model.md` para los campos de cada uno). El enum completo pasa a ser:

`"compra"` | `"tesoreria"` | `"impuesto"` | `"retencion"` | `"remuneracion"` | `"arrendamiento"` | `"venta_hacienda"` | `"fuera_de_alcance"` | `"no_disponible"`

`origen.tipo = "fuera_de_alcance"` sigue existiendo, ahora exclusivamente para `origenTipo = "Ret. IVA Granos"`.

Ejemplo de movimiento con origen en impuestos:

```json
{
  "fecha": "2011-05-16",
  "documento": "Pago impuesto",
  "numeroDocumento": "0001-00000123",
  "deuda": 1500.00,
  "credito": 0,
  "origen": {
    "tipo": "impuesto",
    "idImpuesto": 14,
    "tipoImpuesto": "Ingresos Brutos",
    "importe": 1500.00
  }
}
```
