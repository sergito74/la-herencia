"""Redondeos acumulados de cuentas en pesos con saldo cero real (Sergio 21/10/2026). Cada residuo es la suma de centavos
de pagos que no coincidieron con la factura (tarjetas, transferencias) a lo largo de los años; se cierra con una nota
interna de redondeo al 30/09/2026 (corte), con la clasificación de la última factura anterior al corte.
Signo: saldo a favor del proveedor -> NC interna (RDC); a favor nuestro -> ND interna (RDD). Idempotente.
"""
from datetime import date

from scripts.nd_interna_tc_036 import crear
from src.db.connection import _assert_target_is_wc, reconciliation_transaction
from src.features.auditoria_cuentas.bimonetaria import cargar_cuentas, invalidar
from src.features.vinculos.backup import backup_verificado

CORTE = date(2026, 9, 30)
# contacto: (residuo en pesos = saldo sin las facturas posteriores al corte, factura de referencia)
RESIDUOS = {5: (-0.15, '0003-00068465'), 273: (-0.05, '15895-00001527'), 465: (-0.05, '2182-00158186'),
            30: (-4.82, '08930-00072632'), 48: (-3.30, '0009-00108040'), 228: (-0.03, '00002-00006422'),
            276: (1.01, '0840-00723836'), 306: (0.29, '0758-00444694'), 467: (0.01, '00002-00000723')}


def main():
    _assert_target_is_wc()
    print(backup_verificado('redondeos-cuentas-pesos-036'))
    with reconciliation_transaction():
        for c, (residuo, fc) in RESIDUOS.items():
            # residuo negativo (deuda de más) -> NC por ese importe; positivo -> ND
            print(c, crear(c, [(CORTE, residuo, fc, 'Redondeo acumulado')], prefijos=('RDD', 'RDC'), texto='Redondeo', ajusta=False))
    invalidar()
    for c, x in cargar_cuentas(list(RESIDUOS)).items():
        print(c, x['saldoPesos'])


if __name__ == '__main__': main()
