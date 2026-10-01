# API Contract: Integridad de vínculos (031)

Todas las rutas requieren sesión. Las de escritura requieren el rol Administrador (016).

## GET /api/integridad-vinculos/control

Control de integridad (FR-011).

**Respuesta 200**

```json
{
  "generado": "2026-09-30T18:00:00",
  "totales": {"documento-excedido": 180, "movimiento-excedido": 0, "doble-imputacion": 158,
              "fecha-incoherente": 1736, "moneda-mezclada": 340},
  "hallazgos": [HallazgoIntegridad]
}
```

**Query**: `categoria?` filtra los hallazgos. Los totales vienen siempre.

## POST /api/integridad-vinculos/lotes

Genera una propuesta nueva (estado `propuesto`). No escribe en `AplicacionesPago`.

**Respuesta 201**: `{idLote, grupos: [{grupo, cantidad, importe}], ambiguos: n}`

## GET /api/integridad-vinculos/lotes/{idLote}

Devuelve el lote con sus ítems agrupados.

**Query**: `grupo?`, `pagina`, `tamanio`.

## PATCH /api/integridad-vinculos/lotes/{idLote}/items

Cuerpo:

```json
{"incluir": [idItem], "excluir": [idItem], "elegir": [{"idItem": 1, "candidato": 0}]}
```

Solo se permite con el lote en estado `propuesto`. En cualquier otro estado devuelve 409.

## POST /api/integridad-vinculos/lotes/{idLote}/aplicar

1. Toma un backup verificado. Si falla, devuelve 500 y no escribe nada.
2. Aplica todo en una transacción.

- **409** si quedan reemplazos ambiguos incluidos sin elegir.
- **200**: `{anuladas, creadas, backup}`

## POST /api/integridad-vinculos/lotes/{idLote}/revertir

Solo sobre lotes `aplicado`.

**200**: `{reactivadas, anuladas}`

## Cambio en endpoints existentes (FR-012)

Estos endpoints validan el exceso con `vinculos.verificar_exceso`:

- `POST /api/aplicaciones-pago`
- la imputación de consumos de tarjeta
- las conciliaciones de tesorería

Reglas:

- Exceso > 2% → **422** `{detail: "El vínculo deja <documento> imputado por $X sobre su total ($Y)"}`.
- Exceso ≤ 2% → **200** con `advertencia: "..."` en la respuesta.

## Cambio en 030

`GET /api/flujo-caja/por-rubro` y `/detalle` reparten con la fuente unificada:

- Los débitos de resumen y de cheque se distribuyen por sus documentos.
- `documentoAplicado` incluye `via`.
- El contrato no cambia de forma. Solo se agrega `via` en las partes del detalle.
