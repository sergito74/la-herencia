"""ARBA (12): inmobiliario y patente según los "Aviso de Deudas" de ARBA al 21/10/2026 (Documents/La Herencia/
Administracion y gestion/ARBA/{Inmobiliario,Patente}), ambos con deuda $0 = todas las cuotas pagadas.
Importe de cada cuota = pago del banco (ARBA lista la deuda original, sin el descuento por buen cumplimiento).
- Inmobiliario 011-007957-5: cuotas 02-04/2025 estaban a $664.328,80 -> pagos 717.807,30 / 717.807,30 / 1.437.586,60;
  faltaban 01/2026 (937.936,80) y 02/2026 (1.005.296,00) y el complementario del 12/06/2026 (BNA $376.755,30).
- Patente AG-964-SV (VW Taos 2025): faltaban cuotas 1-5/2025 y 1, 2 y 7/2026 (pagos "ARBA AUTOM.").
Idempotente.
"""
from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.auditoria_cuentas.bimonetaria import cargar_cuenta, invalidar
from src.features.vinculos.backup import backup_verificado

C = 12
CORRIGE = {1168: 717807.30, 1169: 717807.30, 1170: 1437586.60}
INMOB = [('2019-01-25', '04 2017', 23215.90),  # cuota 4/2017 (las 1-3 de 2017 son de $23.215,90), pagada tarde: BNA 25/01/2019 DEB.TRAN.INTERB-LINK
         ('2026-03-16', '01 2026', 937936.80), ('2026-06-09', '02 2026', 1005296.00),
         ('2026-06-12', 'Complementario 2026', 376755.30)]
PATENTE = [('2025-04-08', 1, 2025, 357417.00), ('2025-07-16', 2, 2025, 558803.60), ('2025-07-16', 3, 2025, 540413.20),
           ('2025-09-09', 4, 2025, 513392.50), ('2025-11-10', 5, 2025, 513392.50), ('2026-03-09', 1, 2026, 148766.40),
           ('2026-04-08', 2, 2026, 152680.90), ('2026-09-08', 7, 2026, 170967.50)]


def main():
    _assert_target_is_wc()
    print(backup_verificado('arba-inmob-patente-036'))
    st = [('UPDATE dbo.Impuestos SET Importe=? WHERE IdImpuesto=? AND IdOrganismo=? AND IdTipoImpuesto=6', (imp, i, C)) for i, imp in CORRIGE.items()]
    for f, per, imp in INMOB:
        if not fetch_all('SELECT 1 x FROM dbo.Impuestos WHERE IdOrganismo=? AND IdTipoImpuesto=6 AND [Periodo liquidado]=?', (C, per)):
            st.append(('INSERT INTO dbo.Impuestos (Fecha,IdOrganismo,IdTipoImpuesto,[Periodo liquidado],[Numero de documento],Importe) '
                       "VALUES (?,?,6,?,'011-007957-5',?)", (f, C, per, imp)))
    for f, n, a, imp in PATENTE:
        per = f'Cuota {n}/{a} - Patente AG964SV'
        if not fetch_all('SELECT 1 x FROM dbo.Impuestos WHERE IdOrganismo=? AND IdTipoImpuesto=26 AND [Periodo liquidado]=?', (C, per)):
            st.append(('INSERT INTO dbo.Impuestos (Fecha,IdOrganismo,IdTipoImpuesto,[Periodo liquidado],Importe) VALUES (?,?,26,?,?)', (f, C, per, imp)))
    with reconciliation_transaction():
        execute_write_transaction(st)
    invalidar()
    print('saldo', round(cargar_cuenta(C, refrescar=True)['saldoPesos'], 2))


if __name__ == '__main__': main()
