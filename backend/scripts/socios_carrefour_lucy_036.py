"""Cuenta de Lucy: Carrefour 30/10/2020 FC 6990-00001484 (Sergio 22/10/2026).

Ticket $7.083,95 pagado entero con la Mastercard BNA de la empresa; $3.580,67 son productos particulares de Lucy (Particular L
de Access, Debe de la planilla). La fila de la planilla no se había migrado porque tenía además un Haber de $4.284,23 sin
respaldo (error, confirmado por Sergio; se borró de la planilla). Se agrega la AsignacionGasto de Lucy. Idempotente.
"""
from datetime import date

from scripts.socios_valuacion_036 import cot, cotizaciones
from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.vinculos.backup import backup_verificado

F = date(2020, 10, 30)


def main():
    _assert_target_is_wc()
    if fetch_all('SELECT 1 x FROM dbo.MovimientosCuentaSocio WHERE IdSocio=2 AND Importe=3580.67 AND CONVERT(date,Fecha)=? AND Anulada=0', (F.isoformat(),)):
        print('ya cargado'); return
    nov, dol = cotizaciones()
    print(backup_verificado('socios-carrefour-lucy-036'))
    with reconciliation_transaction():
        execute_write_transaction([(
            'INSERT INTO dbo.MovimientosCuentaSocio (IdSocio,Tipo,Importe,ImporteUSD,ImporteKgCarne,Fecha,Origen,IdOrigen,Medio,Motivo,Usuario,Anulada) '
            "VALUES (2,'AsignacionGasto',3580.67,?,?,?,'CompraParticular',2143512958,'Mastercard BNA',?,?,0)",
            (round(3580.67 * 0.5 / cot(dol, F), 4), round(3580.67 * 0.5 / cot(nov, F), 4), F.isoformat(),
             'Carrefour FC 6990-00001484: compra particular de Lucy pagada con la Mastercard BNA de la empresa', 'Sergio (036, socios 22/10/2026)'))])
    from src.features.cuentas_socios.repository import calcular_saldo
    print(calcular_saldo(2))


if __name__ == '__main__': main()
