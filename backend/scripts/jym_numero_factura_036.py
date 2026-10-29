"""036 — Jáuregui y Morales (48), 29/10/2026: la factura del 07/03/2023 ($11.200) estaba cargada con el número de la
del 11/01/2023 (00008-00001462). Según el PDF (20230307_JaureguiYMorales 002.pdf) es la 00009-00017433. No cambia saldos.
Uso (desde backend/): python -m scripts.jym_numero_factura_036 [--aplicar]
"""

from __future__ import annotations

import sys

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all
from src.features.vinculos.backup import backup_verificado

ID_DEUDA, ANTES, DESPUES = 2143514048, "00008-00001462", "00009-00017433"

if __name__ == "__main__":
    _assert_target_is_wc()
    fila = fetch_all("SELECT [Nro Documento] AS n, Fecha AS f FROM dbo.Compras WHERE IdDeuda = ? AND IdContacto = 48", (ID_DEUDA,))
    assert fila and fila[0]["n"] == ANTES, fila
    print(fila[0])
    if "--aplicar" not in sys.argv:
        raise SystemExit("Simulación: usar --aplicar para grabar.")
    respaldo = backup_verificado("jym-numero-factura-036")
    execute_write_transaction([
        ("UPDATE dbo.Compras SET [Nro Documento] = ? WHERE IdDeuda = ?", (DESPUES, ID_DEUDA)),
        ("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) "
         "VALUES ('jym-numero-factura-036','aplicada',?,'Claude036',SYSDATETIME(),'Claude036',SYSDATETIME(),?,?)",
         (f'{{"IdDeuda": {ID_DEUDA}, "antes": "{ANTES}", "despues": "{DESPUES}"}}', respaldo,
          "Factura J y M 07/03/2023: número corregido según el PDF (aprobado por Sergio 29/10/2026).")),
    ])
    print("Aplicado. Respaldo:", respaldo)
