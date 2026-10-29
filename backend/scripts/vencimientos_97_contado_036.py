"""036 — compras chicas (97), 29/10/2026: 5 facturas de contado con el vencimiento cargado un año después de la emisión.

Sergio aprobó dejarlas en Contado (sin vencimiento), que es como el formulario de compras representa esa condición.
Uso (desde backend/): python -m scripts.vencimientos_97_contado_036 [--aplicar]
"""

from __future__ import annotations

import json
import sys

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all
from src.features.vinculos.backup import backup_verificado

REGLA = "vencimientos-97-contado-036"

if __name__ == "__main__":
    _assert_target_is_wc()
    filas = fetch_all(
        "SELECT v.IdVencimiento AS iv, c.IdDeuda AS id, c.[Nro Documento] AS nro, c.Fecha AS f, v.[Fecha de vencimiento] AS v "
        "FROM dbo.Compras c JOIN dbo.[Vencimiento Compras] v ON v.IdCompra = c.IdDeuda "
        "WHERE c.IdContacto = 97 AND DATEDIFF(day, c.Fecha, v.[Fecha de vencimiento]) BETWEEN 360 AND 370", ())
    for f in filas:
        print(f["id"], f["nro"], f["f"], "vencía", f["v"])
    assert len(filas) == 5, "se esperaban 5 vencimientos"
    if "--aplicar" not in sys.argv:
        raise SystemExit("Simulación: usar --aplicar para grabar.")
    respaldo = backup_verificado(REGLA)
    execute_write_transaction(
        [("DELETE FROM dbo.[Vencimiento Compras] WHERE IdVencimiento = ?", (f["iv"],)) for f in filas]
        + [("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) "
            "VALUES (?,'aplicada',?,'Claude036',SYSDATETIME(),'Claude036',SYSDATETIME(),?,?)",
            (REGLA, json.dumps(filas, default=str), respaldo,
             "5 compras chicas de contado tenían vencimiento a un año; quedan en Contado (aprobado por Sergio 29/10/2026)."))])
    print("Aplicado. Respaldo:", respaldo)
