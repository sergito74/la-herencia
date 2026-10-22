"""Cuenta 375 (Sergio empleado): sueldos de jun-2016 a sep-2017 cobrados por transferencia y devueltos en efectivo a la caja
el mismo día — Opción A de Sergio (22/10/2026): sueldo NO cobrado + traspaso de fondos BNA → caja (no es aporte de socio).

Evidencia: Movimientos BNA (DEB.TRAN.INTERB-LINK a la CA de Sergio) ↔ MovimientosCajaEfectivo ("Ingreso Efectivo" /
"Retorno|Devolución Sueldo Sergio <mes>"), mismo importe, 0–8 días. Comprobante del 28/07/2016: "CONCEPTO: RETIRO EFECTIVO".
Para cada par: el débito BNA sale del 375 (IdContacto NULL, como los traspasos internos; fila guardada en AuditoriaCorrecciones
y referencia en el Detalle del movimiento de caja) y la liquidación del mes se cancela con un Ajuste Interno (Crédito) "no
cobrado". 30/06 y 28/07/2016 ($33.000) eran retiros de efectivo para la caja; sueldos mayo–julio 2016 ($28.434) no cobrados.
Fuera de este script (pendiente): mar-2017 (P13, $21.000 pagado vs $17.735 devuelto), 10/04/2017 $16.000 sin retorno,
14/06/2017 $30.000 (P14), y nov-2017 en adelante (la planilla ya lo registra como préstamo de Sergio que se devuelve). Idempotente.
"""
import json
import os

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, fetch_one, reconciliation_transaction
from src.features.auditoria_cuentas.bimonetaria import cargar_cuenta, invalidar
from src.features.vinculos.backup import backup_verificado

USUARIO = 'Sergio (036, opción A retornos 22/10/2026)'
# (IdMovimientoBNA, IdMovimiento caja)
PARES = [(18411, 88), (18412, 89), (18413, 100), (18414, 114), (18415, 140), (18416, 160), (18417, 191), (18418, 208),
         (18419, 227), (18420, 236), (18423, 287), (18424, 296), (18426, 315), (18427, 342), (18428, 364), (18429, 384)]
# Liquidaciones no cobradas (IdSalario): mayo, junio, julio y agosto-2016 … septiembre-2017 (sin marzo-2017, P13)
SALARIOS = [1829632579, 1829632580, 1829632585, 1829633092, 1829633093, 1829633094, 1829632593, 1829632603, 1829632604,
            1829632602, 1829633096, 1829633097, 1829633098, 1829633099, 1829633100, 1829633101]


def main():
    _assert_target_is_wc()
    resp = backup_verificado('sergio-retornos-sueldo-2016-2017-036')
    st = []
    for bna, caja in PARES:
        f = fetch_one('SELECT * FROM dbo.[Movimientos BNA] WHERE IdMovimientoBNA=? AND IdContacto=375', (bna,))
        if not f:
            continue
        fila = {k: (str(v) if hasattr(v, 'isoformat') else v) for k, v in f.items() if k != 'SSMA_TimeStamp'}
        st += [("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) "
                "VALUES ('traspaso-bna-caja-via-sergio','aplicada',?,?,SYSDATETIME(),?,SYSDATETIME(),?,?)",
                (json.dumps({'tabla': 'Movimientos BNA', 'fila': fila, 'caja': caja}, ensure_ascii=False), USUARIO, USUARIO, os.path.basename(resp),
                 f'BNA {bna} → CA de Sergio → efectivo → caja (mov. {caja}) el mismo día: traspaso de fondos, no pago de sueldo (opción A)')),
               ('UPDATE dbo.[Movimientos BNA] SET IdContacto=NULL, Contacto=NULL WHERE IdMovimientoBNA=? AND IdContacto=375', (bna,)),
               ("UPDATE dbo.MovimientosCajaEfectivo SET Detalle=? WHERE IdMovimiento=? AND Detalle IS NULL",
                (f'Traspaso desde BNA (mov. {bna}) vía la cuenta de Sergio; sueldo no cobrado (opción A)', caja))]
    for s in fetch_all('SELECT IdSalario i,[Fecha de pago] f,[Periodo liquidado] p FROM dbo.Remuneraciones WHERE IdContacto=375 AND IdSalario IN ('
                       + ','.join(map(str, SALARIOS)) + ')'):
        neto = fetch_one("SELECT Deuda AS d FROM dbo.vw_MovimientosCuenta_Base WHERE Origen='Remuneraciones' AND IdOrigen=?", (s['i'],))['d']
        mot = f'Sueldo {s["p"]} no cobrado: cobrado y devuelto a caja / retiro para caja, opción A (IdSalario {s["i"]})'
        if not fetch_all('SELECT 1 x FROM dbo.AjustesCuentaCorriente WHERE IdContacto=375 AND Motivo=?', (mot,)):
            st.append(("INSERT INTO dbo.AjustesCuentaCorriente (IdContacto,Fecha,Lado,Importe,Motivo,Usuario) VALUES (375,?,'Credito',?,?,?)",
                       (s['f'].date().isoformat() if hasattr(s['f'], 'date') else s['f'], float(neto), mot, USUARIO)))
    if not st:
        print('ya aplicado'); return
    print('antes 375', cargar_cuenta(375, refrescar=True)['saldoPesos'])
    with reconciliation_transaction():
        execute_write_transaction(st)
    invalidar()
    print('375', cargar_cuenta(375, refrescar=True)['saldoPesos'])


if __name__ == '__main__': main()
