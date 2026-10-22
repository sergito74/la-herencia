"""Cuenta de Sergio separada en dos (Sergio 22/10/2026, punto 1 aprobado).

- Contacto 375 "Sergio Giamberardini" = Sergio EMPLEADO: solo recibos de sueldo, sus pagos y retenciones; debe cerrar en 0.
- Contacto nuevo "Sergio Giamberardini (socio)" = lado bancario de su cuenta de socio: transferencias que no son sueldo
  (compensaciones "Devolución por aporte pagos varios", retiros, préstamos y aportes, retiros del Condominio, cobros devueltos a
  caja). La cuenta de socio valuada (MovimientosCuentaSocio / pantalla Cuentas de socios) sigue siendo el registro de esos
  movimientos; este contacto no lleva saldo propio a conciliar.
Movimientos 2020-2026 del 375 que no pagan ningún recibo de sueldo y tienen contraparte en la cuenta de socio o en Cuenta Cond
LSC (verificado uno por uno el 22/10) se reasignan al contacto socio. Casos parciales con AjustesCuentaCorriente:
  - Galicia 267 (29/10/2021, $140.000 en lote): $70.000 sueldo de Sergio (queda en 375) + $70.000 de Lucy → 375 Deuda / 390 Crédito.
  - Galicia 683 (01/08/2022, $400.000 en lote, devolución por aporte de ambos) → contacto socio; $200.000 de Lucy → socio Deuda / 390 Crédito.
  - Retención Ganancias feb-2024 ($9.248,64): pagaron $700.000 con neto $690.752; el excedente ya es deuda de Sergio en su cuenta
    de socio (mov. 2131) → 375 Deuda.
  - P31 Galicia 2782 (10/09/2025, $485.400 "Reembolso gastos"): compensación de gastos de Giamigli pagados por Sergio (confirmado);
    se agrega a su cuenta de socio y se reasigna.
Queda en el 375 sin resolver: Galicia 1390 (05/09/2023, $30.000, P18) y la historia 2011-2019. Idempotente.
"""
from datetime import date

from scripts.socios_valuacion_036 import cot, cotizaciones
from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, fetch_one, reconciliation_transaction
from src.features.auditoria_cuentas.bimonetaria import cargar_cuenta, invalidar
from src.features.vinculos.backup import backup_verificado

USUARIO = 'Sergio (036, cuenta 375 separada 22/10/2026)'
NOMBRE = 'Sergio Giamberardini (socio)'
# (Origen en la vista, IdOrigen)
A_SOCIO = [('Banco Nacion', i) for i in (18464, 18468, 18470, 18471, 18474, 18476, 18404)] + \
          [('Galicia', i) for i in (28, 154, 205, 231, 263, 683, 815, 872, 972, 982, 1097, 1187, 1305, 1409, 2098, 2158, 2199,
                                    2252, 2320, 2523, 2708, 2782, 2882, 2928, 2946, 2974, 3053, 3067, 3096, 3182, 3301, 3349, 3401)] + \
          [('Conciliación Tesorería', 1250)]


def contacto_socio() -> int:
    f = fetch_one('SELECT IdContacto AS i FROM dbo.Contactos WHERE [Razon Social]=?', (NOMBRE,))
    if f:
        return f['i']
    r = execute_write_transaction([("INSERT INTO dbo.Contactos ([Tipo Contacto],[Razon Social],EsContratistaLabores) OUTPUT INSERTED.IdContacto "
                                    "VALUES ('Multiple',?,0)", (NOMBRE,))])
    return r[0]


def main():
    _assert_target_is_wc()
    print(backup_verificado('sergio-cuenta-socio-contacto-036'))
    print('antes 375', cargar_cuenta(375, refrescar=True)['saldoPesos'], '| 390', cargar_cuenta(390)['saldoPesos'])
    with reconciliation_transaction():
        cs = contacto_socio()
        st = []
        for origen, io in A_SOCIO:
            ult = fetch_one('SELECT TOP 1 IdContactoNuevo AS n FROM dbo.ReasignacionesContacto WHERE Origen=? AND IdOrigen=? ORDER BY IdReasignacion DESC', (origen, io))
            if ult and ult['n'] == cs:
                continue
            st.append(('INSERT INTO dbo.ReasignacionesContacto (Origen,IdOrigen,IdContactoAnterior,IdContactoNuevo,Motivo,Usuario,Fecha) '
                       'VALUES (?,?,375,?,?,?,SYSDATETIME())',
                       (origen, io, cs, 'No es sueldo: movimiento de la cuenta de socio de Sergio (375 queda solo como empleado)', USUARIO)))
        ajustes = [(375, date(2021, 10, 29), 'Deuda', 70000.0, 'Galicia 267: débito en lote; $70.000 fueron a Lucy (extracto Galicia de Lucy)'),
                   (390, date(2021, 10, 29), 'Credito', 70000.0, 'Galicia 267 (cuenta de Sergio): parte de Lucy del débito en lote del 29/10/2021'),
                   (cs, date(2022, 8, 1), 'Deuda', 200000.0, 'Galicia 683: débito en lote; $200.000 fueron a Lucy (extracto Galicia de Lucy)'),
                   (390, date(2022, 8, 1), 'Credito', 200000.0, 'Galicia 683 (cuenta socio de Sergio): parte de Lucy del débito en lote del 01/08/2022'),
                   (375, date(2024, 2, 29), 'Deuda', 9248.64, 'Feb-2024: pagado $700.000, neto del recibo $690.752; excedente en cuenta de socio (mov. 2131)')]
        for c, f, lado, imp, mot in ajustes:
            if not fetch_all('SELECT 1 x FROM dbo.AjustesCuentaCorriente WHERE IdContacto=? AND Fecha=? AND Lado=? AND Importe=?', (c, f.isoformat(), lado, imp)):
                st.append(('INSERT INTO dbo.AjustesCuentaCorriente (IdContacto,Fecha,Lado,Importe,Motivo,Usuario) VALUES (?,?,?,?,?,?)',
                           (c, f.isoformat(), lado, imp, mot, USUARIO)))
        F = date(2025, 9, 10)
        if not fetch_all("SELECT 1 x FROM dbo.MovimientosCuentaSocio WHERE IdSocio=1 AND Importe=485400 AND CONVERT(date,Fecha)=? AND Anulada=0", (F.isoformat(),)):
            nov, dol = cotizaciones()
            st.append(("INSERT INTO dbo.MovimientosCuentaSocio (IdSocio,Tipo,Importe,ImporteUSD,ImporteKgCarne,Fecha,Origen,IdOrigen,Medio,Motivo,Usuario,Anulada) "
                       "VALUES (1,'AsignacionGasto',485400,?,?,?,'Galicia',2782,'Galicia',?,?,0)",
                       (round(485400 * 0.5 / cot(dol, F), 4), round(485400 * 0.5 / cot(nov, F), 4), F.isoformat(),
                        'Giamigli – Devolución por aporte pagos varios (reembolso de gastos de Giamigli pagados por Sergio)', USUARIO)))
        if st:
            execute_write_transaction(st)
    invalidar()
    print('contacto socio', cs, '| 375', cargar_cuenta(375, refrescar=True)['saldoPesos'], '| socio', cargar_cuenta(cs, refrescar=True)['saldoPesos'],
          '| 390', cargar_cuenta(390, refrescar=True)['saldoPesos'])


if __name__ == '__main__': main()
