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

**Salida**: además de la impresión en consola, deja un CSV en el directorio de trabajo (`conciliacion_historico_<timestamp>.csv`) con una fila por movimiento procesado, para que el usuario pueda auditar la corrida completa fuera de la terminal.
