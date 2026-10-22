"""Cuentas de socios: pagos Particular L / S de Access que faltaban o diferían (Sergio 22/10/2026, revisión uno por uno).

- Irma Miranda 31/03/2021 $10.104 (Particular L): sueldo de marzo-2021 pagado por Lucy; el resumen Supervielle de Lucy muestra
  transferencias de $10.104 el 02/03/21 (febrero, ya en la planilla) y el 31/03/21. Devolución a favor de Lucy.
- Ebox S.A. 26/11/2021 $69.999 (Particular S): TV Philips 50" FC 0004-00044990, compra particular de Sergio pagada por la
  empresa; la fila "Compra Televisor" de la planilla estaba sin importe. AsignacionGasto de Sergio.
- Armando Mori 02/12/2022: el ICBC de Sergio debitó $8.214 (transf. 02-12); la planilla decía $8.314. Se corrige el movimiento 2079.
Valuación como la planilla (50% kg novillo / 50% US$). Idempotente.
"""
from datetime import date

from scripts.socios_valuacion_036 import cot, cotizaciones
from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.vinculos.backup import backup_verificado

USUARIO = 'Sergio (036, particulares 22/10/2026)'


def main():
    _assert_target_is_wc()
    nov, dol = cotizaciones()
    val = lambda m, f: (round(m * 0.5 / cot(dol, f), 4), round(m * 0.5 / cot(nov, f), 4))
    nuevos = [
        (2, 'Devolucion', 10104.0, date(2021, 3, 31), None, None, 'Supervielle', 'Irma Miranda – Sueldo Marzo 2021 (transferencia Supervielle de Lucy 31/03/21)'),
        (1, 'AsignacionGasto', 69999.0, date(2021, 11, 26), 'CompraParticular', 2143514465, 'Efectivo',
         'Ebox S.A. – TV Philips 50" FC 0004-00044990: compra particular de Sergio pagada por la empresa'),
    ]
    st = []
    for s, t, m, f, o, io, medio, motivo in nuevos:
        if fetch_all('SELECT 1 x FROM dbo.MovimientosCuentaSocio WHERE IdSocio=? AND Importe=? AND CONVERT(date,Fecha)=? AND Anulada=0', (s, m, f.isoformat())):
            continue
        usd, kg = val(m, f)
        st.append(('INSERT INTO dbo.MovimientosCuentaSocio (IdSocio,Tipo,Importe,ImporteUSD,ImporteKgCarne,Fecha,Origen,IdOrigen,Medio,Motivo,Usuario,Anulada) '
                   'VALUES (?,?,?,?,?,?,?,?,?,?,?,0)', (s, t, m, usd, kg, f.isoformat(), o, io, medio, motivo, USUARIO)))
    usd, kg = val(8214.0, date(2022, 12, 2))
    st.append(('UPDATE dbo.MovimientosCuentaSocio SET Importe=8214, ImporteUSD=?, ImporteKgCarne=?, Motivo=? WHERE IdMovimiento=2079 AND Importe=8314',
               (usd, kg, 'Armando Mori – Trabajos Hacienda (ICBC 02/12/2022 $8.214; la planilla decía $8.314)')))
    print(backup_verificado('socios-particulares-036'))
    with reconciliation_transaction():
        execute_write_transaction(st)
    from src.features.cuentas_socios.repository import calcular_saldo
    for s in (1, 2):
        print(s, calcular_saldo(s))


if __name__ == '__main__': main()
