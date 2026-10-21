"""Cierre al centavo de cuentas en dólares con saldo cero real (Sergio 21/10/2026: Folgado, Nación Seguros, La Bragadense,
Sunanco, ASP, Nidera). Los residuos son redondeos del último pago:
- pesos: nota interna de diferencia de cambio (respuesta 15) vinculada a la última factura en dólares;
- dólares (cuentas valuadas contra el libro del proveedor): la valuación del último pago se corrige por el centavo.
Idempotente.
"""
from datetime import date

from scripts.nd_interna_tc_036 import crear
from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.auditoria_cuentas.bimonetaria import cargar_cuentas, invalidar
from src.features.vinculos.backup import backup_verificado

NOTAS = {420: [(date(2026, 3, 30), 2.53, '00011-00001105', 'Redondeo cierre Folgado')],
         289: [(date(2023, 5, 15), -1.13, '63288 1', 'Redondeo cierre Nación Seguros')],
         472: [(date(2022, 4, 12), 0.01, '1001-00032980', 'Redondeo cierre La Bragadense')]}
VALUACION = [(420, 'Galicia', 3119, 211.75, 211.73), (289, 'Tarjetas', 5536, 27.94, 27.93),
             (449, 'Galicia', 612, 8900.9452, 8900.7452), (17, 'Banco Nacion', 14378, 335.45, 335.43),
             # Nidera: estado de cuenta del portal al 31/08/2020 (mail SUNANCO "Facturas Nidera") solo tiene abiertas las FC
             # 0301-4242/4243 (US$ 9.387,35): el cheque 3620051 del 01/07/2020 canceló US$ 10.686,71, sin saldo a favor.
             (303, 'Banco Nacion', 16666, 10693.54, 10686.71)]
NOTA = 'Redondeo de cierre al centavo (auditoría US$ 21/10/2026)'


def main():
    _assert_target_is_wc()
    print(backup_verificado('cierre-centavos-usd-036'))
    with reconciliation_transaction():
        for c, ajustes in NOTAS.items():
            print(c, crear(c, ajustes))
        for c, o, i, antes, despues in VALUACION:
            execute_write_transaction([('UPDATE dbo.ValuacionProveedor SET Dolares=?,Nota=? WHERE IdContacto=? AND Origen=? AND IdOrigen=? AND ABS(Dolares-?)<0.00005',
                                        (despues, NOTA, c, o, i, antes))])
    invalidar()
    for c, x in cargar_cuentas([420, 289, 472, 449, 17, 303]).items():
        print(c, x['saldoPesos'], x['saldoDolares'])


if __name__ == '__main__': main()
