"""036 — Jáuregui y Morales (48), 29/10/2026: 27 facturas con el total cargado con centavos distintos al del ticket.

Sergio: los centavos no se cancelan con pagos; la factura se lleva al TOTAL del comprobante. Cada total lo leí del
ticket (escaneos verificados uno por uno, planilla redondeos-jauregui-20261029.xlsx). Método Cargill
(`cargill_fracciones_036`): se escalan los precios de los renglones para que el total sea exacto. Idempotente.
Uso (desde backend/): python -m scripts.jym_redondeo_tickets_036 [--aplicar]
"""

from __future__ import annotations

import json
import sys

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all
from src.features.vinculos.backup import backup_verificado

TICKET = {
    "0004-00032677": 485.45, "0004-00035358": 270.00, "0005-00042237": 433.00, "0005-00050058": 535.00,
    "0005-00055333": 519.99, "0006-00003415": 650.00, "0005-00059888": 570.00, "0005-00062142": 820.00,
    "0005-00063549": 1010.01, "0005-00064033": 720.00, "0006-00024640": 739.99, "0006-00025352": 500.00,
    "0006-00029396": 749.99, "0006-00030333": 382.65, "0006-00032069": 850.00, "0006-00032428": 400.00,
    "0006-00033151": 830.01, "0005-00066804": 950.00, "0007-00012021": 46239.98, "0006-00092546": 1524.80,
    "0006-00107907": 5100.96, "00009-00025375": 5000.36, "00009-00030596": 6000.07, "00009-00036746": 6907.05,
    "00011-00006045": 1299000.00, "00008-00010792": 27999.99, "0011-00013090": 2329000.00,
}


def estado() -> list[dict]:
    return fetch_all(
        "SELECT c.IdDeuda AS i, c.[Nro Documento] AS n, t.GranTotal AS g, t.TotalDetalleCompra AS d, v.ImporteDocumento AS v "
        "FROM dbo.Compras c JOIN dbo.vw_Cns_Total_Compra t ON t.IdDeuda = c.IdDeuda "
        "JOIN dbo.vw_Compras_ImporteDocumento v ON v.IdDeuda = c.IdDeuda "
        f"WHERE c.IdContacto = 48 AND c.[Nro Documento] IN ({','.join('?' * len(TICKET))})", tuple(TICKET))


if __name__ == "__main__":
    _assert_target_is_wc()
    filas = estado()
    assert len(filas) == len(TICKET), f"se esperaban {len(TICKET)} facturas, hay {len(filas)}"
    pendientes = [f for f in filas if abs(float(f["v"]) - TICKET[f["n"]]) > 0.004]
    for f in pendientes:
        print(f["n"], float(f["v"]), "->", TICKET[f["n"]])
    if "--aplicar" not in sys.argv or not pendientes:
        raise SystemExit("Simulación: usar --aplicar para grabar." if pendientes else "Nada pendiente.")
    respaldo = backup_verificado("jym-redondeo-tickets-036")
    stmts = []
    for f in pendientes:
        g, d = float(f["g"]), float(f["d"])
        assert abs(d) > 1e-6, f["n"]
        stmts.append(("UPDATE dbo.Det_Compras SET [Precio Unitario] = [Precio Unitario] * ? WHERE IdCompra = ?",
                      ((TICKET[f["n"]] - (g - d)) / d, f["i"])))
    stmts.append(("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) "
                  "VALUES ('jym-redondeo-tickets-036','aplicada',?,'Claude036',SYSDATETIME(),'Claude036',SYSDATETIME(),?,?)",
                  (json.dumps({f["n"]: [float(f["v"]), TICKET[f["n"]]] for f in pendientes}), respaldo,
                   f"{len(pendientes)} facturas J y M llevadas al TOTAL del ticket (aprobado por Sergio 29/10/2026).")))
    execute_write_transaction(stmts)
    mal = [(f["n"], float(f["v"]), TICKET[f["n"]]) for f in estado() if abs(float(f["v"]) - TICKET[f["n"]]) > 0.004]
    print("Aplicado. Respaldo:", respaldo, " Quedan distintas del ticket:", mal)
