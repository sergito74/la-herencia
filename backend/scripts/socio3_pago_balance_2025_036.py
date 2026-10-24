"""036: «Pago Balance Giamigli» 2025 en la cuenta de socio del Condominio (socio 3). Confirmado por Sergio (24/10/2026).

Mismo formato que el de 2024 (asientos 2781–2784): el Condominio paga el balance (caja Condominio 3225, $1.456.200,
10/09/2025) = Haber del Condominio; Giamigli transfiere a cada socio su tercio por Galicia ($485.400 c/u, movimientos
2781 Ceci, 2782 Sergio, 2783 Lucy) = Debe del Condominio «<socio> — Retiro por aporte pago balance».
Valuación 50% US$ / 50% kg INMAG a la fecha (regla posterior al 16/03/2020). Inspección por defecto.
"""

import argparse
import json
from datetime import date
from decimal import Decimal

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all
from src.features.cuentas_socios.valuacion import a_fecha
from src.features.vinculos.backup import backup_verificado

RULE = "socio3-pago-balance-2025-036"
FECHA = date(2025, 9, 10)
FILAS = [
    ("Devolucion", Decimal("1456200"), "Efectivo", "Condominio LSC — Pago Balance Giamigli 2025 (caja Condominio 3225)", 3225),
    ("AsignacionGasto", Decimal("485400"), "Banco Galicia", "Sergio — Retiro por aporte pago balance (Galicia 2782)", 2782),
    ("AsignacionGasto", Decimal("485400"), "Banco Galicia", "Lucy — Retiro por aporte pago balance (Galicia 2783)", 2783),
    ("AsignacionGasto", Decimal("485400"), "Banco Galicia", "Ceci — Retiro por aporte pago balance (Galicia 2781)", 2781),
]


def run(aplicar=False):
    _assert_target_is_wc()
    if fetch_all("SELECT 1 x FROM dbo.AuditoriaCorrecciones WHERE Regla=? AND Estado='aplicada'", (RULE,)):
        return {"estado": "ya_aplicado_sin_escrituras"}
    caja = fetch_all("SELECT Importe FROM dbo.MovimientosCajaEfectivo WHERE IdMovimiento=3225 AND Anulada=0")
    banco = fetch_all("SELECT IdMovimiento, [Débitos] d FROM dbo.[Movimientos Galicia] WHERE IdMovimiento IN (2781,2782,2783)")
    assert caja and Decimal(str(caja[0]["Importe"])) == -FILAS[0][1]
    assert len(banco) == 3 and all(Decimal(str(b["d"])) == FILAS[1][1] for b in banco)
    assert not fetch_all("SELECT 1 x FROM dbo.MovimientosCuentaSocio WHERE IdSocio=3 AND Anulada=0 AND Importe=1456200")
    plan = []
    for tipo, imp, medio, motivo, ref in FILAS:
        v = a_fecha(imp, FECHA)
        plan.append((tipo, imp, Decimal(str(v["importeUSD"])), Decimal(str(v["importeKgCarne"])), medio, motivo, ref))
    res = {"estado": "inspeccion", "plan": plan}
    if not aplicar:
        return res
    res["backup"] = backup_verificado("socio3_pago_balance_2025_036")
    stmts = [("INSERT INTO dbo.MovimientosCuentaSocio (IdSocio,Tipo,Importe,ImporteUSD,ImporteKgCarne,Fecha,Origen,IdOrigen,Medio,Motivo,Usuario) "
              "VALUES (3,?,?,?,?,?,'PagoBalance2025',?,?,?,'Claude036')", (t, i, u, k, FECHA.isoformat(), r, m, mo)) for t, i, u, k, m, mo, r in plan]
    stmts.append(("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) "
                  "VALUES (?,'aplicada',?,'Claude036',SYSDATETIME(),'Claude036',SYSDATETIME(),?,?)",
                  (RULE, json.dumps({"caja": 3225, "galicia": [2781, 2782, 2783]}), res["backup"],
                   "Pago Balance 2025 confirmado por Sergio: Haber Condominio 1.456.200 y tres retiros de 485.400 (Sergio, Lucy, Ceci).")))
    execute_write_transaction(stmts)
    res["estado"] = "aplicado"
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--aplicar", action="store_true")
    print(json.dumps(run(ap.parse_args().aplicar), default=str, ensure_ascii=False, indent=1))
