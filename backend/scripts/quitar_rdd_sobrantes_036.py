"""036, 30/10/2026: notas internas de redondeo del 30/09 que sobran después de los redondeos factura por factura del 29-30/10.
Cada una cancelaba centavos que ahora ya están corregidos en las facturas; al quedar, desplazan la cuenta del cero
(EESS Saladillo +$4,00 con la RDC de $4,82). Se borran las que acercan el saldo al cero o al pendiente real; las demás
(Agrovet, La Comarca, Jáuregui, 115, 465) siguen haciendo falta. Luego se actualiza el SaldoAlCierre de las fichas cerradas
cuyo cambio vino solo de esos redondeos.
Uso (desde backend/): python -m scripts.quitar_rdd_sobrantes_036 [--aplicar]
"""
import json
import sys

from scripts.inventario_cuentas_externas_036 import saldo_a
from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_one
from src.features.auditoria_cuentas import bimonetaria
from src.features.vinculos.backup import backup_verificado

NOTAS = {2143523812: 30, 2143523810: 273, 2143523817: 467, 2143523814: 228}

if __name__ == "__main__":
    _assert_target_is_wc()
    for i, ct in NOTAS.items():
        assert fetch_one("SELECT 1 x FROM dbo.Compras WHERE IdDeuda = ? AND IdContacto = ? AND [Nro Documento] LIKE 'RD%-260930'", (i, ct))
    antes = {ct: round(saldo_a(ct, "2026-09-30")[0], 2) for ct in NOTAS.values()}
    print("antes", antes)
    if "--aplicar" not in sys.argv:
        raise SystemExit("Simulación: usar --aplicar para grabar.")
    respaldo = backup_verificado("quitar-rdd-sobrantes-036")
    stmts = []
    for i in NOTAS:
        stmts += [(f"DELETE FROM dbo.{t} WHERE IdCompra = ?", (i,)) for t in ("Det_Compras", "[Vencimiento Compras]")]
        stmts.append(("DELETE FROM dbo.Compras WHERE IdDeuda = ?", (i,)))
    stmts.append(("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) "
                  "VALUES ('quitar-rdd-sobrantes-036','aplicada',?,'Claude036',SYSDATETIME(),'Claude036',SYSDATETIME(),?,?)",
                  (json.dumps({"notas": NOTAS, "saldosAntes": antes}), respaldo,
                   "Notas internas de redondeo del 30/09 que sobraban tras el redondeo factura por factura (EESS Saladillo, "
                   "Carrefour, 467, Martin Silva Rossi).")))
    execute_write_transaction(stmts)
    bimonetaria.invalidar()
    print("despues", {ct: round(saldo_a(ct, "2026-09-30")[0], 2) for ct in NOTAS.values()})
