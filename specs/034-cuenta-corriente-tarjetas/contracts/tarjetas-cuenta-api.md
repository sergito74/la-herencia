# Contrato de API: cuentas de tarjetas, control y cruces

Prefijo: `/api/tarjetas-cuenta`. Los valores de los ejemplos son ilustrativos salvo los identificadores reales de los casos conocidos (devolución BNA 9426, débito BNA 18093, línea 505, movimiento de Mercado Libre 20). Todas las respuestas son JSON salvo las exportaciones (`.xlsx`). Los importes están en pesos con dos decimales, las fechas en formato `YYYY-MM-DD`.

**Autenticación y roles**: el middleware global ya exige sesión. Las lecturas están abiertas a todos los roles que ven cuentas corrientes. `POST` y `DELETE` de cruces rechazan el rol `Lectura` con `403`.

**Errores comunes**: `404` si la tarjeta no existe; `409` si un cruce choca con otro vigente o ya existe; `422` si falla una validación de negocio (importes que no coinciden, línea de otra tarjeta). Cuerpo de error: `{"detail": "texto claro en español"}`.

## 1. Resumen de las cinco tarjetas

`GET /api/tarjetas-cuenta/resumen?hasta=YYYY-MM-DD` (por defecto, hoy)

```json
{
  "hasta": "2026-10-06",
  "tarjetas": [
    {
      "idTarjeta": 1, "tarjeta": "AgroNacion", "banco": "Banco Nacion", "activa": true,
      "idContacto": 373,
      "deuda": 30194174.94, "credito": 30193831.61, "saldo": -343.33,
      "pendienteNeto": 0.0, "diferenciaConModuloTarjetas": 0.0,
      "ultimoMovimiento": "2026-08-14", "cuotasAVencer": 0,
      "hallazgosControl": 24
    }
  ],
  "total": { "deuda": 58538417.16, "credito": 58341022.20, "saldo": -197394.96 },
  "tarjetasSinContacto": []
}
```

`saldo` usa el criterio de la vista (`credito − deuda`; negativo = se debe). `diferenciaConModuloTarjetas` es `|saldo + pendienteNeto|` y debe ser menor a $1 (FR-009). Una tarjeta sin contacto o con más de uno aparece en `tarjetasSinContacto` y no lleva saldo (FR-006).

## 2. Cuenta de una tarjeta

`GET /api/tarjetas-cuenta/{idTarjeta}?desde=&hasta=&agrupar=movimientos|resumenes`

- `agrupar=movimientos` (por defecto): una fila por consumo, cargo, pago y devolución.
- `agrupar=resumenes`: una fila por resumen con su total y una por pago (reproduce la cuenta de 008).

```json
{
  "idTarjeta": 4, "tarjeta": "Visa Galicia", "idContacto": 532,
  "desde": "2026-01-01", "hasta": "2026-10-06",
  "saldoInicial": -120000.00,
  "filas": [
    {
      "fecha": "2026-04-09", "origen": "Consumo", "idResumen": 4120, "codigo": "VI0000…",
      "detalle": "MERPAGO*MERCADOLIBRE", "proveedor": null,
      "deuda": 155568.86, "credito": 0.0, "saldo": -275568.86,
      "estadoVinculo": "vinculado",
      "referencia": { "tipo": "linea-consumo", "idLineaConsumo": 4776, "idResumen": 4120 }
    }
  ],
  "saldoFinal": -300000.00,
  "cuotasAVencer": [],
  "apertura": { "idContactoAnterior": null, "informativo": true }
}
```

- `origen`: `Consumo`, `Cargo del resumen`, `Pago`, `Devolución`.
- `estadoVinculo` (solo en consumos): `vinculado`, `resto-con-proveedor`, `sin-proveedor`, `cruzado-con-devolucion`.
- `referencia.tipo`: `linea-consumo`, `resumen`, `movimiento-bancario` o `cruce`, para llegar al detalle (historia 6).
- `cuotasAVencer` (FR-015): `[{ "fechaVencimiento", "importe", "idCompra"? }]`, aparte del saldo.
- `saldoInicial` suma todo lo anterior a `desde`; las `filas` son solo las del período.

`GET /api/tarjetas-cuenta/{idTarjeta}/exportar?desde=&hasta=&agrupar=` devuelve el `.xlsx` con las mismas filas y saldos.

## 3. Control de integridad

`GET /api/tarjetas-cuenta/control?idTarjeta=&categoria=`

```json
{
  "generado": "2026-10-06T16:00:00",
  "resumenPorCategoria": { "movimiento-sin-resumen": 23, "devolucion-sin-cruzar": 1 },
  "hallazgos": [
    {
      "categoria": "movimiento-sin-resumen", "idTarjeta": 1, "tarjeta": "AgroNacion",
      "medio": "bna", "idMovimiento": 18093, "idResumen": null, "idLineaConsumo": null,
      "fecha": "2025-09-01", "importe": 966654.20,
      "motivo": "Movimiento asignado a la tarjeta sin resumen vinculado"
    }
  ]
}
```

Categorías (FR-010): `pago-en-proveedor` (a), `movimiento-sin-resumen` (b), `pago-sin-origen-o-importe` (c), `resumen-con-pendiente` (d), `devolucion-sin-cruzar` (e), `saldo-inicial-con-pagos` (f), `tarjeta-sin-contacto` (g), `consumo-sin-vinculo-con-deuda-abierta` (h), `consumo-sin-proveedor` (i), `diferencia-contrapartida` (j).

`GET /api/tarjetas-cuenta/control/exportar?idTarjeta=&categoria=` devuelve el `.xlsx` de los hallazgos (FR-011).

## 4. Sugerencias de cruce

`GET /api/tarjetas-cuenta/cruces/sugerencias?tipo=devolucion-debito|consumo-devolucion&idTarjeta=`

```json
{
  "sugerencias": [
    {
      "tipo": "devolucion-debito", "idTarjeta": 1,
      "origen": { "medio": "bna", "idMovimiento": 9426, "fecha": "2025-09-17", "importe": 966654.20, "concepto": "OTROS CONCEPTOS-VS" },
      "destino": { "medio": "bna", "idMovimiento": 18093, "fecha": "2025-09-01", "importe": 966654.20, "concepto": "PM/TOT. RES. AGRONACION" },
      "diasDiferencia": 16, "diferenciaImporte": 0.0, "puntaje": 0.93
    }
  ]
}
```

Solo lectura. Reglas: `devolucion-debito` empareja una devolución bancaria sin contacto con un pago a una tarjeta del mismo importe (tolerancia $0,01) en ±45 días; `consumo-devolucion` empareja un ingreso de la billetera "Devolución de dinero…" con un consumo sin proveedor del mismo importe en ±45 días. Las candidatas se ordenan por `puntaje` (cercanía de fecha e igualdad de importe, descendente). Un movimiento ya cruzado no se sugiere.

## 5. Aprobar un cruce

`POST /api/tarjetas-cuenta/cruces` (rol de escritura)

```json
{ "tipo": "devolucion-debito", "idTarjeta": 1, "sugerido": true,
  "origen": { "medio": "bna", "idMovimiento": 9426 },
  "destino": { "medio": "bna", "idMovimiento": 18093 } }
```

```json
{ "tipo": "consumo-devolucion", "idTarjeta": 4, "sugerido": true,
  "origen": { "medio": "mercado-libre", "idMovimiento": 20 },
  "idLineaConsumo": 505 }
```

Respuesta `201`: `{ "idCruce": 7, "tipo": "...", "importe": 249999.00, "usuario": "sergio", "fecha": "2026-10-06T16:05:00" }`.

Validaciones (`422`): el importe de la devolución debe igualar el del débito o la línea (tolerancia $0,01); la devolución no puede superar el débito; la línea debe ser de la tarjeta indicada. `409`: el movimiento ya está en un cruce vigente. Efecto inmediato: un cruce `devolucion-debito` agrega la fila `Devolución` (deuda) a la cuenta de la tarjeta; uno `consumo-devolucion` marca el consumo como `cruzado-con-devolucion` y deja de informarse en las categorías (e) e (i).

## 6. Deshacer un cruce

`DELETE /api/tarjetas-cuenta/cruces/{idCruce}` (rol de escritura) → `204`. Baja lógica: registra usuario y fecha; el movimiento vuelve a estar disponible. `404` si no existe; `409` si ya estaba deshecho.

## 7. Historial de cruces

`GET /api/tarjetas-cuenta/cruces?idTarjeta=&incluirDeshechos=false` → lista de cruces con `usuario`, `fecha`, `sugerido`, `deshecho`, `usuarioDeshecho`, `fechaDeshecho` (FR-022).

## Cambios en endpoints existentes

- `GET /api/tesoreria/mercado-libre/movimientos` (movimientos de la billetera en Tesorería): cada movimiento suma `esConducto: bool` y `idOperacionPar: string | null`. No se modifica ningún otro campo.
- `GET /api/tarjetas/{idTarjeta}/movimientos` (008): sin cambios; sigue disponible hasta migrar la pantalla.
- `GET /api/cuentas-corrientes/…` (listado general): sin cambios de contrato; las filas nuevas aparecen con `origen` `Tarjeta consumo`, `Tarjeta cargo`, `Tarjeta devolución` y `Mercado Pago`, y el resolutor de orígenes devuelve para ellas una referencia `linea-consumo`, `resumen`, `cruce` o `mercado-libre`.
