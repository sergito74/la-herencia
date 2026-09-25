# Contrato: script de esquema

`backend/scripts/crear_tablas_cuentas_socios.py`

Mismo patrón que `crear_tabla_aplicaciones_pago.py` (019): DDL idempotente (`IF OBJECT_ID(...) IS NULL`), sin flag `--apply` (no hace falta, es idempotente por diseño), nunca corre contra `LaHerencia`.

```
.venv\Scripts\python.exe -m scripts.crear_tablas_cuentas_socios
```

Crea, en este orden:
1. `dbo.Socios` (si no existe) + inserta las 4 filas fijas (Sergio, Lucy, Cond LSC, Ceci) si la tabla está vacía — idempotente, no duplica si se corre dos veces.
2. `dbo.MovimientosCuentaSocio` (si no existe) + el índice único filtrado sobre `(Origen, IdOrigen)`.
3. `dbo.AuditoriaReflejoSocio` (si no existe).

Uso (desde backend/): correr una vez tras mergear la feature, antes de que el backend intente usar estas tablas. Requiere backup de `WC` verificado antes de correr (Constitución, Principio II) por ser un cambio de esquema, aunque sea aditivo y de bajo riesgo (tablas nuevas, no toca ninguna existente).
