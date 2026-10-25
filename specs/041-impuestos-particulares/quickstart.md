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
