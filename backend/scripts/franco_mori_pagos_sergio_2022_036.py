"""Franco (379) y Mori (376), oct-dic 2022: sueldo = neto del recibo formal; la diferencia la pagó Sergio en efectivo (Sergio 22/10/2026).

Reemplaza la bonificación negativa de franco_mori_sueldos_2022_036. Sergio: a los empleados no se les firman recibos por más
de lo que cobran ni se les quedó debiendo; la caja de Giamigli no lo pagó. Por lo tanto cobraron el neto formal completo y la
diferencia con los pagos registrados la pagó Sergio en efectivo, sin anotarla:
  Franco oct+nov-22: formal $12.659, pagado $10.000 (ICBC 02/12)        → Sergio $2.659 (02/12/2022)
  Mori oct+nov-22:   formal $27.579, pagado $26.600 (recibo 5)          → Sergio $979   (02/12/2022)
  Mori dic-22:       formal $20.999, pagado $18.400 (recibos 9 y 10)    → Sergio $2.599 (12/01/2023)
Bonificación de esos meses = 0; pago Particular S a cada trabajador; Devolución a favor de Sergio en su cuenta de socio.
Idempotente.
"""
from datetime import date

from scripts.socios_valuacion_036 import cot, cotizaciones
from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.auditoria_cuentas.bimonetaria import cargar_cuenta, invalidar
from src.features.vinculos.backup import backup_verificado

USUARIO = 'Sergio (036, revisión 22/10/2026)'
SALARIOS = (1829633045, 1829633089, 1829633038, 1829633050, 1829633051)
PAGOS = [(379, 'Franco Rodriguez', 2659.0, date(2022, 12, 2), 'oct+nov 2022'),
         (376, 'Armando Mori', 979.0, date(2022, 12, 2), 'oct+nov 2022 (recibo 5)'),
         (376, 'Armando Mori', 2599.0, date(2023, 1, 12), 'dic 2022 (recibos 9 y 10)')]


def main():
    _assert_target_is_wc()
    nov, dol = cotizaciones()
    st = [('UPDATE dbo.Remuneraciones SET [Bonificacion adicional]=0 WHERE IdSalario IN (' + ','.join(map(str, SALARIOS)) + ')', ())]
    for c, nombre, m, f, per in PAGOS:
        if not fetch_all("SELECT 1 x FROM dbo.[Pagos efectivo] WHERE IdContacto=? AND Caja='Particular S' AND [Importe imputado]=? AND CONVERT(date,Fecha)=?", (c, m, f.isoformat())):
            st.append(("INSERT INTO dbo.[Pagos efectivo] (IdContacto,IdTipoMovimiento,IdFormaPago,Fecha,Cuenta,Caja,[Importe imputado]) "
                       "VALUES (?,1,30,?,'Blue','Particular S',?)", (c, f.isoformat(), m)))
        if not fetch_all('SELECT 1 x FROM dbo.MovimientosCuentaSocio WHERE IdSocio=1 AND Importe=? AND CONVERT(date,Fecha)=? AND Anulada=0', (m, f.isoformat())):
            st.append(('INSERT INTO dbo.MovimientosCuentaSocio (IdSocio,Tipo,Importe,ImporteUSD,ImporteKgCarne,Fecha,Medio,Motivo,Usuario,Anulada) '
                       "VALUES (1,'Devolucion',?,?,?,?,'Efectivo',?,?,0)",
                       (m, round(m * 0.5 / cot(dol, f), 4), round(m * 0.5 / cot(nov, f), 4), f.isoformat(),
                        f'{nombre} – diferencia hasta el neto del recibo formal {per}, pagada por Sergio en efectivo', USUARIO)))
    print(backup_verificado('franco-mori-pagos-sergio-2022-036'))
    with reconciliation_transaction():
        execute_write_transaction(st)
    invalidar()
    for c in (376, 379):
        print(c, 'saldo', cargar_cuenta(c, refrescar=True)['saldoPesos'])
    from src.features.cuentas_socios.repository import calcular_saldo
    print('Sergio', calcular_saldo(1))


if __name__ == '__main__': main()
