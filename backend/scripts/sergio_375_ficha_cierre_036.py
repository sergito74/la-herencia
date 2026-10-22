"""Ficha de revisión del contacto 375 (Sergio empleado): cierre con saldo pendiente justificado (Sergio 22/10/2026).

Saldo −$1.800.000 = sueldo de septiembre-2026 (recibo formal) cuyo pago no está registrado (se paga en octubre; extractos hasta
30/09). Todo lo demás conciliado: recibos formales vs pagos; no-sueldo al contacto socio 5670; sueldos no cobrados (2011-2012,
2013-abr-2016, opción A jun-2016–sep-2017, jun-2018 parcial) con ajuste por período. Idempotente.
"""
from datetime import date

from src.db.connection import _assert_target_is_wc
from src.db.connection import fetch_all
from src.features.revision_cuentas import evidencia, fichas

C = 375
USUARIO = 'Sergio (036, cierre cuenta 375 22/10/2026)'
NOTA = ('Cuenta de Sergio EMPLEADO, conciliada 22/10/2026: recibos formales del Estudio vs pagos. Lo que no es sueldo pasó al '
        'contacto 5670 "Sergio Giamberardini (socio)" y a su cuenta de socio. Sueldos no cobrados (renuncia de Sergio) cancelados '
        'con ajuste por período: 2011-2012, ene-2013 a abr-2016, jun-2016 a sep-2017 (cobrados y devueltos a caja, opción A), '
        'saldo de jun-2018. Saldo −$1.800.000 = sueldo de septiembre 2026, pago en octubre (fuera del extracto). Detalle: '
        'specs/036-revision-sistematica-cuentas/sergio-375-pendientes-resumen-20261022.md')


def main():
    _assert_target_is_wc()
    fichas._asegurar_fila(C, USUARIO)
    fichas.confirmar_inventario(C, [
        {'tipo': 'certificado', 'disponible': True, 'detalle': 'Recibos de sueldo PDF del Estudio Criado (Personal/Recibos) y Empleados.xlsx'},
        {'tipo': 'extracto', 'disponible': True, 'detalle': 'Extractos BNA/Galicia de Giamigli y personales de Sergio y Lucy; comprobantes de transferencia'},
        {'tipo': 'dropbox', 'disponible': True, 'detalle': 'Cajas Giamigli.xlsx (Caja Efectivo, Cuenta Sergio, Cuenta Cond LSC)'},
    ], USUARIO)
    if not fetch_all('SELECT 1 x FROM dbo.RevisionSaldosExternos WHERE IdContacto=? AND Anulado=0', (C,)):
        evidencia.crear_saldo_externo(C, date(2026, 9, 30), -1800000.0, 'Pesos', 'pdf',
                                      'Personal/Recibos/2026/2026 09 Sergio Giamberardini.pdf (neto $1.800.000)',
                                      'Sueldo de septiembre 2026 liquidado, pago en octubre (fuera del extracto al 30/09)', USUARIO)
    motivo = ('Retención de Ganancias feb-2024 ($9.248,64) figura como pago sin factura: se pagó $700.000 con neto $690.752; '
              'el excedente se compensó con ajuste interno y es deuda de Sergio en su cuenta de socio (mov. 2131).')
    print(fichas.cambiar_estado(C, {'estado': 'cerrada-con-excepcion', 'nota': NOTA, 'motivoExcepcion': motivo}, USUARIO).get('estado'))


if __name__ == '__main__': main()
