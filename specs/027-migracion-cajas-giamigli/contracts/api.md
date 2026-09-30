# API Contract: Migración histórica de Cajas Giamigli

## Endpoints extendidos (021 — `cuentas_socios`)

Sin cambios de rutas; se extiende el payload de los endpoints ya existentes.

### `GET /api/cuentas-socios/{idSocio}/movimientos` (existente, payload extendido)

```jsonc
{
  "idSocio": 2,
  "nombre": "Lucy",
  "saldo": 33041.40,       // pesos — sin cambios de nombre (compatibilidad)
  "saldoUSD": 1405.71,     // nuevo
  "saldoKgCarne": 92.79,   // nuevo
  "movimientos": [
    {
      "idMovimiento": 8,
      "tipo": "AsignacionGasto",
      "importe": 48841.02,
      "importeUSD": 21.71,       // nuevo, 0 si no aplica
      "importeKgCarne": 8.49,    // nuevo, 0 si no aplica
      "fecha": "2025-05-12",
      "origen": "TarjetaLineaConsumo",
      "idOrigen": 640,
      "medio": "Galicia",
      "motivo": "El Luchador — Compra particular",
      "usuario": "fix-el-luchador-compra-particular",
      "anulada": false,
      "motivoAnulacion": null,
      "huerfano": false
    }
  ]
}
```

## Endpoints nuevos (`cajas_efectivo`, solo lectura)

### `GET /api/cajas-efectivo/{caja}/saldo`

`{caja}` = `giamigli-sa` | `campo-chica`, mapeado literal al valor guardado en `MovimientosCajaEfectivo.Caja`: `{"giamigli-sa": "GiamigliSA", "campo-chica": "CampoChica"}`.

```jsonc
{ "caja": "giamigli-sa", "saldo": 152340.18 }
```

404 si `{caja}` no es uno de los 2 valores válidos.

### `GET /api/cajas-efectivo/{caja}/movimientos?page=1&pageSize=50`

```jsonc
{
  "items": [
    {
      "idMovimiento": 1204,
      "fecha": "2011-02-17",
      "concepto": "AFIP",
      "detalle": null,
      "importe": -1214.19,
      "cuenta": "White",
      "formaPago": null,
      "numeroDocumento": null,
      "idContactoRelacionado": null
    }
  ],
  "page": 1,
  "pageSize": 50,
  "total": 1841
}
```

Paginado igual que `cuentas-corrientes` (004) y `cuentas-socios` (021): `page`/`pageSize` en query, `total` en la respuesta.

## Endpoint nuevo (`migracion_cajas_giamigli`, solo lectura)

### `GET /api/migracion-cajas-giamigli/revision?resuelto=false`

```jsonc
{
  "items": [
    {
      "idRevision": 42,
      "hoja": "Cuenta Sergio",
      "numeroFila": 137,
      "motivo": "Sin fecha",
      "datosCrudos": "{\"proveedor\": \"...\", \"importe\": null}",
      "fechaCarga": "2026-09-30T14:00:00",
      "resuelto": false
    }
  ],
  "total": 3
}
```

`resuelto` en query filtra por el estado (`true`/`false`); sin el parámetro devuelve todos. No hay endpoint de escritura para marcar `resuelto` en esta iteración (la spec no lo pide — la cola es de consulta, no de gestión de flujo; se puede marcar directo en `WC` si hace falta, como cualquier corrección puntual de datos).

## Sin cambios

- `Compras`, `Det_Compras`, `Tarjetas_Resumenes_Lineas_Compras`, `Pagos efectivo`: ningún endpoint nuevo, ninguna modificación de los existentes (FR-010).
- No hay endpoint para `Parametros financieros.xlsx` / revalorización diaria — fuera de alcance (spec Clarifications).
