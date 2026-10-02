# API Contract: Recálculo FIFO

El prefijo de todas las rutas es `/api/recalculo-fifo`. Todas requieren sesión. Las que escriben exigen el rol admin, que hoy tiene solo Sergio, y responden 403 a cualquier otro usuario.

## Ejecuciones

| Método | Ruta | Descripción |
| --- | --- | --- |
| POST | `/ejecuciones` | Body: `{alcance: "todos" \| [idContacto]}`. Crea una simulación y devuelve `{idEjecucion, resumen}`. No escribe en `AplicacionesPago`. |
| GET | `/ejecuciones` | Lista las ejecuciones con su estado y resumen. |
| GET | `/ejecuciones/{id}` | Devuelve la cabecera y el resumen. |
| POST | `/ejecuciones/{id}/aplicar` | Body opcional: `{contactos: [id]}`, para aplicar solo esos contactos. Hace el respaldo verificado, aplica y devuelve `{aplicados, sinCambios, omitidos}`. Responde 409 si la ejecución no está `simulada` o si los datos cambiaron desde la simulación. Responde 422 si incluye contactos que pasan de cerrar a no cerrar y no viene `confirmarEmpeoran: true`. |
| POST | `/ejecuciones/{id}/revertir` | Restaura las aplicaciones anteriores. Responde 409 si la ejecución no está `aplicada`. |
| POST | `/ejecuciones/{id}/descartar` | Marca como descartada una ejecución `simulada`. |

## Contactos de una ejecución

| Método | Ruta | Descripción |
| --- | --- | --- |
| GET | `/ejecuciones/{id}/contactos?filtro=todos\|cierra\|no-cierra\|mejora\|empeora\|excepcion&orden=volumen&pagina&tamanio` | Lista por contacto: aplicado antes y después, si cierra, tendencia, controles fallidos y marcas. |
| GET | `/ejecuciones/{id}/contactos/{idContacto}` | Detalle: débitos con lo aplicado antes y después, créditos, aplicaciones propuestas con su regla y la línea de tiempo del saldo. |
| PATCH | `/ejecuciones/{id}/contactos/{idContacto}/excepcion` | Body: `{estado: "pendiente" \| "resuelta", nota}`. |

## Saldo inicial y duplicados

| Método | Ruta | Descripción |
| --- | --- | --- |
| GET | `/saldos-iniciales?estado=estimado` | Lista los saldos iniciales propuestos. |
| POST | `/saldos-iniciales/{idContacto}` | Body: `{accion: "confirmar" \| "rechazar", importe?}`. Solo admin. |
| GET | `/duplicados?estado=propuesto` | Lista los pares de contactos con su criterio. |
| POST | `/duplicados/{idContacto}` | Body: `{accion: "confirmar" \| "descartar", idContactoPrincipal}`. Solo admin. |

## Operatoria continua

| Método | Ruta | Descripción |
| --- | --- | --- |
| POST | `/cola/procesar` | Recalcula los contactos encolados. Lo invoca el frontend al entrar y cada hora. Devuelve `{aplicados, propuestas}`. |
| GET | `/propuestas` | Lista los contactos cuyo recálculo continuo no pasó los controles. |
| PATCH | `/compras/{idDeuda}/suspension` | Body: `{suspendida: bool}`. Suspende o libera una factura (FR-025). |

## Saldos y aviso

| Método | Ruta | Descripción |
| --- | --- | --- |
| GET | `/api/cuentas-corrientes/contactos/{id}/saldo-por-vencimiento` | Devuelve `{moneda, vencido, tramos: [{vencimiento, importe}], anticipo}`. |
| GET | `/aviso-vencimientos` | Devuelve `{mostrar: bool, desde, hasta, items: [{contacto, documento, vencimiento, importe, moneda}]}`. `mostrar` es true el primer ingreso de cada lunes. Cubre los vencimientos de los próximos 15 días. |
| POST | `/aviso-vencimientos/visto` | Marca el aviso de la semana como visto. |

## Errores

Todas las rutas responden con el formato estándar del proyecto: `{"detail": "mensaje en español"}`.
