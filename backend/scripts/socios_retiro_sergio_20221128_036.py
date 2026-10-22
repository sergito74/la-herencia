"""Cuenta de Sergio: retiro de efectivo de $18.500 de la caja el 28/11/2022 (confirmado por Sergio 22/10/2026).

La hoja Caja Efectivo Pesos registra el 28/11/2022 "Trabajos Hacienda Recibo 5" (Mori $8.500) y "Recibo 6" (Franco $10.000),
pero los recibos 5 y 6 se pagaron por transferencia el 02/12/2022 (Galicia Giamigli $18.386 + ICBC Sergio $8.214 a Mori;
ICBC Sergio $10.000 a Franco; comprobantes encontrados por Sergio). Los recuentos de caja confirman que el efectivo salió:
Sergio lo retiró y no lo cargó en la planilla. Se registra como deuda de Sergio. Idempotente.
Las salidas de caja quedan imputadas a Mori/Franco hasta que se revisen sus cuentas (pendiente).
"""
from datetime import date

from scripts.socios_valuacion_036 import cot, cotizaciones
from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.vinculos.backup import backup_verificado

F = date(2022, 11, 28)


def main():
    _assert_target_is_wc()
    if fetch_all("SELECT 1 x FROM dbo.MovimientosCuentaSocio WHERE IdSocio=1 AND Importe=18500 AND CONVERT(date,Fecha)=? AND Anulada=0", (F.isoformat(),)):
        print('ya cargado'); return
    nov, dol = cotizaciones()
    print(backup_verificado('socios-retiro-sergio-20221128-036'))
    with reconciliation_transaction():
        execute_write_transaction([(
            'INSERT INTO dbo.MovimientosCuentaSocio (IdSocio,Tipo,Importe,ImporteUSD,ImporteKgCarne,Fecha,Medio,Motivo,Usuario,Anulada) '
            "VALUES (1,'AsignacionGasto',18500,?,?,?,'Efectivo',?,?,0)",
            (round(18500 * 0.5 / cot(dol, F), 4), round(18500 * 0.5 / cot(nov, F), 4), F.isoformat(),
             'Sergio Giamberardini – Retiro efectivo de caja 28/11/2022 (anotado en la caja como recibos 5 Mori $8.500 y 6 Franco $10.000, '
             'que se pagaron por transferencia el 02/12/2022)', 'Sergio (036, socios 22/10/2026)'))])
    from src.features.cuentas_socios.repository import calcular_saldo
    print(calcular_saldo(1))


if __name__ == '__main__': main()
