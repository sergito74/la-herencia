# Contrato: script de conciliación histórica

`backend/scripts/conciliar_historico_cuentas_corrientes.py`

```
.venv\Scripts\python.exe -m scripts.conciliar_historico_cuentas_corrientes            # dry-run
.venv\Scripts\python.exe -m scripts.conciliar_historico_cuentas_corrientes --apply     # escribe
.venv\Scripts\python.exe -m scripts.conciliar_historico_cuentas_corrientes --contacto 123  # limita a un contacto (debug/validación puntual)
```

**Dry-run (default)**: recorre todos los movimientos de tesorería sin aplicaciones vigentes en el rango 2015-09-01 hacia atrás hasta el inicio de datos, agrupa por contacto, imprime:
- Total de movimientos procesados
- Cuántos generarían aplicación exacta
- Cuántos generarían aplicación de mejor esfuerzo (con el detalle de diferencia)
- Cuántos quedarían sin aplicar (excepciones), con contacto y motivo (`sin contacto identificable` | `sin documentos candidatos`)

No escribe nada en `WC`.

**`--apply`**: ejecuta lo mismo que el dry-run pero además inserta las filas correspondientes en `AplicacionesPago` (`Origen='automatica-exacta'` o `'automatica-mejor-esfuerzo'`, `Usuario='sistema-conciliacion-020'`). Requiere backup de `WC` verificado antes de correr (Constitución, Principio II) — el script no lo verifica por sí mismo, es responsabilidad del operador antes de invocarlo.

**Idempotencia**: antes de generar una aplicación para un movimiento, el script vuelve a chequear que no tenga aplicaciones vigentes (misma condición que la 019 usa para "estado de movimiento"); si ya las tiene (por ejemplo, cargadas manualmente o por una corrida anterior de este mismo script), lo saltea.

**Salida**: además de la impresión en consola, deja un CSV en el directorio de trabajo (`conciliacion_historico_<timestamp>.csv`) con una fila por movimiento procesado, para que el usuario pueda auditar la corrida completa fuera de la terminal. También persiste el resultado en `dbo.ConciliacionHistoricoLog` (`WC`) para que la pantalla de revisión (US2) no tenga que reprocesar el histórico en cada consulta.

---

## Contrato: script de verificación de saldos contra LaHerencia (US3)

`backend/scripts/comparar_saldo_laherencia.py`

```
.venv\Scripts\python.exe -m scripts.comparar_saldo_laherencia            # dry-run
.venv\Scripts\python.exe -m scripts.comparar_saldo_laherencia --apply    # guarda en SaldosReferenciaAccess
```

Lee, en modo **estrictamente solo lectura**, el saldo actual por contacto desde `dbo.vw_MovimientosCuenta_Saldo` en la base **`LaHerencia`** (no `WC`) — ver research.md §2: los `.accdb` de Access son un front-end enlazado por ODBC a esa misma base, que sigue viva y recibiendo carga real en producción. Usa una conexión dedicada, separada de la que usa el resto del backend, y reutiliza el guard `_assert_read_only` de `src/db/connection.py` para que sea imposible ejecutar algo que no sea `SELECT` contra la base protegida.

Compara ese saldo contra el saldo actual de `WC` (`cuentas_corrientes.get_saldos_todos()`, sin modificar). Con `--apply`, guarda el resultado (upsert por `IdContacto`) en `dbo.SaldosReferenciaAccess` (en `WC`) para que `GET /api/conciliacion-historico/saldos` no tenga que releer `LaHerencia` en cada consulta.

**Dry-run (default)**: imprime cuántos contactos están dentro de tolerancia (0.5% relativo, mínimo $1) y el detalle de los que no, sin escribir nada.
