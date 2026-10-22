# API — 039 Contratos de pastaje

Prefijo `/api/pastaje`. JSON; importes Decimal como cadena; fechas ISO. Escrituras requieren rol con escritura (403 para Lectura). Concurrencia optimista con `version`.

## Índice INMAG
- `GET /indice-inmag?desde&hasta` → `[{fecha, indice, cabIngresadas, origen, nota}]`
- `POST /indice-inmag/actualizar` `{desde?, hasta?}` → `{agregados, sinIndice:[fechas], errores}` (default últimos 10 días)
- `PUT /indice-inmag/{fecha}` `{indice, nota}` → carga/corrección manual (nota obligatoria, historial)

## Contratos
- `GET /contratos?estado` → tarjetas: `{id, cliente, estado, cabezasActuales:[{categoria, cabezas}], tarifas, inmagUltimo, promedioMesCurso, estimadoMesCurso, proximoPaso, alertas}`
- `POST /contratos` / `PUT /contratos/{id}` → ficha completa con tarifas[]
- `GET /contratos/{id}` → condiciones + resumen mensual (`meses:[{periodo, devengado, liquidado, facturado, cobrado, saldo, estado, diferencia}]`)
- `POST /contratos/{id}/archivo-contrato` (multipart)

## Bitácora
- `GET /contratos/{id}/bitacora` → movimientos + cabezas vigentes por fecha
- `POST /contratos/{id}/bitacora` `{fecha, tipo, idTipoHacienda, cabezas, numeroDte?, observacion?}` → para `recuento` devuelve `{diferencia}`
- `POST /bitacora/{idMovimiento}/anular` `{motivo, version}`

## Liquidaciones
- `GET /contratos/{id}/liquidaciones/preview?periodo=YYYY-MM` → cálculo en vivo (tramos, índices usados, precio, neto, IVA, total, bloqueos)
- `POST /contratos/{id}/liquidaciones` `{periodo}` → borrador
- `POST /liquidaciones/generar-mes` `{periodo}` → borradores para todos los contratos con hacienda (lo invoca la tarea del día 1)
- `POST /liquidaciones/{id}/confirmar` `{version}` → fija y genera PDF; 409 si bloqueada (sin índice)
- `POST /liquidaciones/{id}/ajuste` → liquidación de ajuste (original vs recalculado) + PDF
- `GET /liquidaciones/{id}/pdf`
- `GET /liquidaciones/{id}/texto-factura` → `{detalle, neto, iva, total}` sugeridos para ARCA

## Comprobantes
- `POST /comprobantes/leer` (multipart PDF) → datos leídos + comparación con liquidación + advertencias (emisor ≠ Giamigli, cliente ≠ contrato, importes ≠)
- `POST /comprobantes` `{...datos confirmados, idLiquidacion | idComprobanteAsociado, archivoToken}` → 409 duplicado
- `GET /contratos/{id}/comprobantes` → grilla con cobrado/saldo
- `POST /comprobantes/{id}/anular` `{motivo, version}` (bloqueado si tiene cobros aplicados)

Cobros y retenciones: endpoints existentes de aplicaciones de pago / cajas con `tipoDocumento: "Pastaje"`.
