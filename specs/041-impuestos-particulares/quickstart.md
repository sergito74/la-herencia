# Quickstart — 041 Impuestos particulares

| # | Escenario | Esperado |
|---|---|---|
| 1 | Migrar 3206 | Carga Condominio $8.852,10; Debe manual del 25/10 anulado; Haber 13/11/2017 vinculado; estado «devuelto»; saldo del Condominio igual que antes |
| 2 | Cuenta corriente ARBA | Mismo saldo antes y después |
| 3 | Flujo de caja nov-2017 | Salida BNA comp. 4394 en rubro «Cuenta de socios», no en «Impuestos» |
| 4 | Carga parcial 60% | Solo esa parte sale de costos |
| 5 | Carga que supera el importe | 409 |
| 6 | Cuenta de socio cerrada | pide confirmación |
| 7 | Partida ya en el padrón | aviso con el titular |
| 8 | Baja de impuesto con carga | 409 |
| 9 | Anulación | Debe anulado; vuelve a costos |
| 10 | Rol Lectura | 403 en escrituras |

Comandos: `python -m pytest tests -q -k 041`, `npx tsc --noEmit`, `python -m scripts.migrar_impuestos_particulares_041` (inspección) / `--aplicar`.


## Casos de integridad agregados tras el análisis

| # | Escenario | Esperado |
|---|---|---|
| 11 | Repetir POST parcial con igual UUID/cuerpo, incluso concurrentemente | Una sola carga y un solo Debe; respuesta del mismo recurso |
| 12 | UUID ya usado con otro cuerpo; repetir después de anular | 409 por cuerpo distinto; repetición original devuelve estado anulado sin recrear |
| 13 | Haber 1000 repartido 600/400 entre cargas del mismo socio | Ambos vínculos válidos; otro importe 1 rechazado por capacidad |
| 14 | Haber de otro socio, anulado o reutilizado; importe superior al pendiente | 409, sin filas parciales ni recorte automático |
| 15 | Editar datos financieros o borrar una boleta con cargas | 409; metadatos descriptivos siguen editables |
| 16 | Editar/anular Haber vinculado o Debe ligado desde socios u operación de origen | 409; primero desvincular/anular desde impuesto, sin eludir el origen |
| 17 | Anular carga con devolución; anular un vínculo y volver a vincular | Haber conservado, vínculos auditados y capacidad liberada; nueva fila/clave para revincular |
| 18 | Partida única, compartida y sin cargas vigentes; declaración Oscar | Propuesta única, aviso ambiguo o ninguna propuesta; Oscar solo socio 3 |
| 19 | Dos manuales candidatos, uno fuera de tres días o solo fecha de creación cercana | Solo candidatos con fecha histórica dentro de tres días, selección explícita; sin anulación automática |
| 20 | Reintentar creación de un Haber desde impuesto | Un solo Haber/vínculo, origen DevImpParticular compatible con varchar(20) |
| 21 | 3206 devuelto nominal, valuaciones de fechas diferentes | Conservar 501,5354 USD Debe / 505,8343 USD Haber; no ajustar diferencia 4,2989 USD ni saldo del Condominio |

Las pruebas de estos escenarios son simuladas. DDL y migración real se inspeccionan y respaldan por separado. En navegador, no crear ni anular registros financieros reales como prueba automática.
