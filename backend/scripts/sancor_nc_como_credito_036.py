"""036, 30/10/2026: las NC B de Sancor 00035-00006907 ($1.895,78) y 00030-00003040 ($813,44) del 28/07/2026 se cargaron
hoy desde la bandeja como "Factura B" con importe positivo (sumaban deuda). El PDF dice "B NOTA DE CREDITO": se pasan a
Nota de Crédito con importe negativo, como las demás NC del sistema. Uso: python -m scripts.sancor_nc_como_credito_036 [--aplicar]
"""
import json
import sys

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all
from src.features.auditoria_cuentas import bimonetaria
from src.features.vinculos.backup import backup_verificado

NC = {2143525180: "00035-00006907", 2143525181: "00030-00003040"}

if __name__ == "__main__":
    _assert_target_is_wc()
    filas = fetch_all(f"SELECT IdDeuda i,[Nro Documento] n,[Tipo documento] t FROM dbo.Compras WHERE IdDeuda IN ({','.join(map(str, NC))}) AND IdContacto=171", ())
    assert {r["i"]: r["n"] for r in filas} == NC and all(r["t"] == "Factura" for r in filas), filas
    antes = bimonetaria.cargar_cuenta(171, refrescar=True)["saldoPesos"]
    print("antes", antes)
    if "--aplicar" not in sys.argv:
        raise SystemExit("Simulación")
    respaldo = backup_verificado("sancor-nc-como-credito-036")
    stmts = []
    for i in NC:
        stmts.append(("UPDATE dbo.Compras SET [Tipo documento]='Nota de Crédito' WHERE IdDeuda=?", (i,)))
        stmts.append(("UPDATE dbo.Det_Compras SET [Precio Unitario]=-ABS([Precio Unitario]) WHERE IdCompra=?", (i,)))
    stmts.append(("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) "
                  "VALUES ('sancor-nc-como-credito-036','aplicada',?,'Claude036',SYSDATETIME(),'Claude036',SYSDATETIME(),?,?)",
                  (json.dumps(NC), respaldo, "NC B de Sancor 28/07/2026 cargadas como factura: pasan a Nota de Crédito negativa.")))
    execute_write_transaction(stmts)
    bimonetaria.invalidar()
    print("despues", bimonetaria.cargar_cuenta(171, refrescar=True)["saldoPesos"])
