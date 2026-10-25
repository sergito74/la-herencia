"""036: tres movimientos BNA del Condominio LSC sin asiento en su cuenta de socio (Sergio 25/10/2026: «H: Adelante»),
y registro de la identificación de los 12 depósitos BNA sin contacto 2011–2014 (J).

H (evidencia: Movimientos LSC.xlsx > Movs y Movimientos Condominios.xlsx > Extracto Banco del Condominio):
- BNA 18635 21/03/2012 −$4.134 «COBRADO POR CAJA» = Movs 430 «Pago IVA e IIBB» del Condominio en efectivo: Giamigli pagó
  un impuesto del Condominio → Debe (AsignacionGasto) del socio 3. Sin prueba de reintegro.
- BNA 10348 27/03/2012 +$5.971,50 = transferencia del Condominio «Transferencia al Campo» (Extracto Banco 372) → Haber.
- BNA 11240 13/02/2014 +$10.000 = transferencia del Condominio «Transferencia a Giamigli» (Extracto Banco 1188) → Haber.
J: solo deja constancia en AuditoriaCorrecciones; los depósitos siguen sin contacto (el cobro ya está en la cuenta del
cliente; contacto 0 evita duplicarlo). Inspección por defecto. Idempotente.
"""

import argparse
import json
from datetime import date
from decimal import Decimal

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all
from src.features.cuentas_socios.valuacion import a_fecha
from src.features.vinculos.backup import backup_verificado

RULE = "condominio-h-bna-036"
ORIGEN = "BNACondominio036"
H = [
    (18635, "AsignacionGasto", "Giamigli pagó IVA e IIBB del Condominio con un cheque propio cobrado por caja (Movs fila 430, 21/03/2012); sin reintegro probado."),
    (10348, "Devolucion", "Condominio LSC — aporte: transferencia del Condominio a Giamigli «Transferencia al Campo» (Extracto Banco fila 372)."),
    (11240, "Devolucion", "Condominio LSC — aporte: transferencia del Condominio a Giamigli «Transferencia a Giamigli» (Extracto Banco fila 1188)."),
]
J = {
    "identificados": {9885: "pago 110 Las Heras (depósito del cliente)", 9890: "pago 111 Las Heras (depósito del cliente)",
                      10640: "cobro 408 en efectivo", 10906: "pago 450 Las Heras (depósito del cliente)",
                      10990: "cobros 449+451 en efectivo", 11076: "cobro 477 en efectivo (banco +0,10)",
                      11533: "cobros 696+697+698 en efectivo"},
    "probables": {11245: "efectivo del cobro Pastorino 551 (20/02/2014, $11.212)", 11272: "efectivo del cobro Pastorino 560 (11/03/2014, $6.000)",
                  10431: "efectivo de la caja Giamigli", 10509: "efectivo de la caja Giamigli", 10857: "caja Giamigli (transferencia)"},
}


def plan():
    filas = []
    for bna, tipo, motivo in H:
        b = fetch_all("SELECT CONVERT(date,[Fecha / Hora Mov#]) f, Importe FROM dbo.[Movimientos BNA] WHERE IdMovimientoBNA=? AND IdContacto=549", (bna,))
        assert b, bna
        if fetch_all("SELECT 1 x FROM dbo.MovimientosCuentaSocio WHERE Anulada=0 AND Origen=? AND IdOrigen=?", (ORIGEN, bna)):
            continue
        imp, f = abs(Decimal(str(b[0]["Importe"]))), date.fromisoformat(str(b[0]["f"]))
        v = a_fecha(imp, f)
        filas.append({"bna": bna, "tipo": tipo, "fecha": f, "importe": imp, "usd": Decimal(str(v["importeUSD"])),
                      "kg": Decimal(str(v["importeKgCarne"])), "motivo": motivo})
    return filas


def run(aplicar=False):
    _assert_target_is_wc()
    if fetch_all("SELECT 1 x FROM dbo.AuditoriaCorrecciones WHERE Regla=? AND Estado='aplicada'", (RULE,)):
        return {"estado": "ya_aplicado_sin_escrituras"}
    filas = plan()
    res = {"estado": "inspeccion", "filas": filas, "j": J}
    if not aplicar:
        return res
    res["backup"] = backup_verificado("condominio_h_bna_036")
    st = [("INSERT INTO dbo.MovimientosCuentaSocio (IdSocio,Tipo,Importe,ImporteUSD,ImporteKgCarne,Fecha,Origen,IdOrigen,Medio,Motivo,Usuario) "
           "VALUES (3,?,?,?,?,?,?,?,'Banco Nación',?,'Claude036')",
           (f["tipo"], f["importe"], f["usd"], f["kg"], f["fecha"].isoformat(), ORIGEN, f["bna"], f["motivo"])) for f in filas]
    st.append(("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) "
               "VALUES (?,'aplicada',?,'Claude036',SYSDATETIME(),'Claude036',SYSDATETIME(),?,?)",
               (RULE, json.dumps({"H": [f["bna"] for f in filas], "J": J}, ensure_ascii=False), res["backup"],
                "Socio 3: Debe 4.134 (BNA 18635), Haber 5.971,50 (10348) y 10.000 (11240). J: 7 depósitos BNA identificados y 5 probables, sin contacto.")))
    execute_write_transaction(st)
    res["estado"] = "aplicado"
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--aplicar", action="store_true")
    print(json.dumps(run(ap.parse_args().aplicar), default=str, ensure_ascii=False, indent=1))
