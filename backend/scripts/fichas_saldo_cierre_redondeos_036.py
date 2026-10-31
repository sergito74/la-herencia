"""036, 30/10/2026: actualiza SaldoAlCierre de las fichas cerradas que solo cambiaron por los redondeos documentados del
29-30/10 (facturas al total del ticket o a su pago 1 a 1, ≤0,10%; notas RDC/RDD sobrantes borradas). Solo diferencias
menores a $10; lo demás debe explicarse aparte. Queda registro en AuditoriaCorrecciones con el saldo anterior de cada una.
Uso (desde backend/): python -m scripts.fichas_saldo_cierre_redondeos_036 [--aplicar]
"""
import json
import sys

from scripts.inventario_cuentas_externas_036 import saldo_a
from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all

if __name__ == "__main__":
    _assert_target_is_wc()
    cambios = {}
    for f in fetch_all("SELECT IdContacto c,SaldoAlCierre s,Moneda m,Corte k FROM dbo.RevisionFichas "
                       "WHERE Estado LIKE 'cerrada%' AND SaldoAlCierre IS NOT NULL", ()):
        p, u = saldo_a(f["c"], str(f["k"])[:10] if f["k"] else "2026-09-30")
        hoy = round(u if f["m"] == "Dolares" else p, 2)
        if 0.005 < abs(hoy - float(f["s"])) < 10:
            cambios[f["c"]] = (float(f["s"]), hoy)
    print(len(cambios), cambios)
    if "--aplicar" not in sys.argv:
        raise SystemExit("Simulación: usar --aplicar para grabar.")
    stmts = [("UPDATE dbo.RevisionFichas SET SaldoAlCierre = ? WHERE IdContacto = ?", (hoy, c)) for c, (_, hoy) in cambios.items()]
    stmts.append(("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) "
                  "VALUES ('fichas-saldo-cierre-redondeos-036','aplicada',?,'Claude036',SYSDATETIME(),'Claude036',SYSDATETIME(),NULL,?)",
                  (json.dumps(cambios), f"{len(cambios)} fichas cerradas: SaldoAlCierre al saldo posterior a los redondeos documentados.")))
    execute_write_transaction(stmts)
