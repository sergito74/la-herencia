"""036: cierre del remanente de la caja Giamigli 2011–2015 (Sergio 25/10/2026).

1. Inmobiliario nov-2011 (Impuesto 70, $2.810, ARBA 12): lo pagó el BNA por débito Link (mov. 10196, 04/11/2011, sin
   contacto). El pago en efectivo 208 (10/11/2011) era una carga errónea: se borra (con snapshot en la auditoría, como en
   los demás duplicados de 036), se anula su egreso de caja 1333 y el débito 10196 pasa al contacto ARBA.
2. Remanente no identificado (mov. 1947) = efectivo que puso Lucy en la caja sin registrar en 2011–2013 («muy
   probablemente... sobre todo Lucy»; «Todo a Lucy»). El movimiento pasa a «Aporte en efectivo Lucy» fechado el 24/05/2013
   (mínimo del saldo acumulado sin aportes) y se acredita en la cuenta de Lucy (socio 2), valuado a esa fecha.
Saldo de la caja al 13/07/2015 y final sin cambios. Idempotente.
"""

import json
from decimal import Decimal

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all
from src.features.cuentas_socios.valuacion import a_fecha
from src.features.vinculos.backup import backup_verificado

RULE = "caja-giamigli-arba-lucy-036"
REMANENTE, CAJA_208, PAGO, BNA, ARBA = 1947, 1333, 208, 10196, 12
FECHA_APORTE = "2013-05-24"


def main():
    _assert_target_is_wc()
    if fetch_all("SELECT 1 x FROM dbo.AuditoriaCorrecciones WHERE Regla=? AND Estado='aplicada'", (RULE,)):
        print("ya aplicado"); return
    pago = fetch_all("SELECT * FROM dbo.[Pagos efectivo] WHERE IdPagoEfectivo=? AND IdContacto=? AND [Importe imputado]=2810", (PAGO, ARBA))
    assert pago and not fetch_all("SELECT 1 x FROM dbo.AplicacionesPago WHERE OrigenMovimiento='efectivo' AND IdMovimientoOrigen=? AND Anulada=0", (PAGO,))
    assert fetch_all("SELECT 1 x FROM dbo.[Movimientos BNA] WHERE IdMovimientoBNA=? AND Importe=-2810 AND ISNULL(IdContacto,0)=0", (BNA,))
    rem = Decimal(str(fetch_all("SELECT Importe FROM dbo.MovimientosCajaEfectivo WHERE IdMovimiento=? AND Anulada=0", (REMANENTE,))[0]["Importe"]))
    aporte = rem - Decimal("2810")
    v = a_fecha(aporte, __import__("datetime").date.fromisoformat(FECHA_APORTE))
    antes = fetch_all("SELECT SUM(Importe) s, SUM(CASE WHEN Fecha<'2015-07-14' THEN Importe END) s1507 FROM dbo.MovimientosCajaEfectivo WHERE Caja='GiamigliSA' AND Anulada=0")[0]
    backup = backup_verificado("caja_giamigli_arba_lucy_036")
    print(backup)
    st = [
        ("UPDATE dbo.MovimientosCajaEfectivo SET Anulada=1 WHERE IdMovimiento=? AND IdPagoEfectivo=?", (CAJA_208, PAGO)),
        ("DELETE FROM dbo.[Pagos efectivo] WHERE IdPagoEfectivo=? AND IdContacto=?", (PAGO, ARBA)),
        ("UPDATE dbo.[Movimientos BNA] SET IdContacto=?, Contacto='ARBA' WHERE IdMovimientoBNA=? AND ISNULL(IdContacto,0)=0", (ARBA, BNA)),
        ("UPDATE dbo.MovimientosCajaEfectivo SET Importe=?, Fecha=?, Concepto=?, Detalle=? WHERE IdMovimiento=?",
         (aporte, FECHA_APORTE, "Aporte en efectivo Lucy (no registrado)",
          "Efectivo puesto por Lucy en la caja 2011–2013 sin registro; remanente de la reconstrucción (Sergio 25/10/2026)", REMANENTE)),
        ("INSERT INTO dbo.MovimientosCuentaSocio (IdSocio,Tipo,Importe,ImporteUSD,ImporteKgCarne,Fecha,Origen,IdOrigen,Medio,Motivo,Usuario) "
         "VALUES (2,'Devolucion',?,?,?,?,'CajaGiamigli036',?,'Efectivo',?,'Claude036')",
         (aporte, Decimal(str(v["importeUSD"])), Decimal(str(v["importeKgCarne"])), FECHA_APORTE, REMANENTE,
          "Lucy — aporte en efectivo a la caja de Giamigli 2011–2013 no registrado (remanente de la reconstrucción de caja; Sergio 25/10/2026)")),
        ("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) "
         "VALUES (?,'aplicada',?,'Claude036',SYSDATETIME(),'Claude036',SYSDATETIME(),?,?)",
         (RULE, json.dumps({"pagoBorrado": pago[0], "bna": BNA, "cajaAnulada": CAJA_208, "remanente": REMANENTE, "aporteLucy": str(aporte)}, default=str),
          backup, f"Inmobiliario nov-2011 pagado por BNA {BNA}: pago 208 borrado. Remanente de caja {rem} → aporte Lucy {aporte}.")),
    ]
    execute_write_transaction(st)
    despues = fetch_all("SELECT SUM(Importe) s, SUM(CASE WHEN Fecha<'2015-07-14' THEN Importe END) s1507 FROM dbo.MovimientosCajaEfectivo WHERE Caja='GiamigliSA' AND Anulada=0")[0]
    print("caja antes", antes, "después", despues, "| aporte Lucy", aporte, "US$", v["importeUSD"])


if __name__ == "__main__":
    main()
