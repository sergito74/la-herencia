"""Cumo Store (615): compra particular de Sergio pagada por Giamigli (Sergio 22/10/2026).

Factura 0004-00000201 del 14/11/2025 (Protector auditivo, $29.699,10), comprada por Mercado Libre junto con otros productos,
facturada a Giamigli y pagada con la Visa Galicia de Giamigli (línea 712 MERPAGO*MERCADOLIBRE del 13/11/2025). En el sistema:
factura con línea negativa "Compra particular" (total 0), la tarjeta imputa $29.699,10 y el asiento Particular S (Pagos efectivo
2548) compensa la cuenta del proveedor (saldo 0). Faltaba la deuda de Sergio con Giamigli: el movimiento 1 era de prueba
(validación 021) y se anuló el 21/10. Se agrega la AsignacionGasto real a la fecha de la factura, valorizada como la planilla
(50% kg novillo / 50% US$). Idempotente.
"""
from datetime import date

from scripts.socios_valuacion_036 import cot, cotizaciones
from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.vinculos.backup import backup_verificado

COMPRA = 2143515240
IMPORTE = 29699.10
FECHA = date(2025, 11, 14)


def main():
    _assert_target_is_wc()
    if fetch_all("SELECT 1 x FROM dbo.MovimientosCuentaSocio WHERE IdSocio=1 AND Origen='CompraParticular' AND IdOrigen=? AND Anulada=0", (COMPRA,)):
        print('ya cargado'); return
    nov, dol = cotizaciones()
    kg, usd = round(IMPORTE * 0.5 / cot(nov, FECHA), 4), round(IMPORTE * 0.5 / cot(dol, FECHA), 4)
    print(backup_verificado('cumo-store-deuda-sergio-036'))
    with reconciliation_transaction():
        execute_write_transaction([(
            "INSERT INTO dbo.MovimientosCuentaSocio (IdSocio,Tipo,Importe,ImporteUSD,ImporteKgCarne,Fecha,Origen,IdOrigen,Medio,Motivo,Usuario,Anulada) "
            "VALUES (1,'AsignacionGasto',?,?,?,?,'CompraParticular',?,'Visa Galicia',?,?,0)",
            (IMPORTE, usd, kg, FECHA.isoformat(), COMPRA,
             'Cumo Store FC 0004-00000201 (14/11/2025, Mercado Libre): compra particular de Sergio pagada con la Visa Galicia de Giamigli',
             'Sergio (036, socios 22/10/2026)'))])
    print('cargado', IMPORTE, 'kg', kg, 'US$', usd)


if __name__ == '__main__': main()
