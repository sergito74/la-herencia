"""Irma Miranda (46): sueldos pagados por los socios (planilla "Cajas Giamigli.xlsx", Sergio 21/10/2026: a Irma no se le debe
nada).
- Ajustes de sueldo ya migrados a la cuenta del socio pero sin vincular a Irma: 2221 (Sergio 11/12/2025, $2.667, ajuste
  noviembre 2025), 2242 (Sergio 06/03/2026, $14.544, ajuste febrero 2026), 2769 (Lucy 15/09/2026, $24.229, ajuste agosto 2026).
- Sueldo septiembre 2026 ($244.274) pagado por Lucy el 01/10/2026 (Banco Galicia), posterior a la migración: se carga en la
  cuenta de Lucy y se vincula.
- Redondeo residual (junio 2025 se pagó $40 menos que el recibo, marzo 2026 $27 más): ajuste interno de cierre.
Idempotente.
"""
from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.auditoria_cuentas.bimonetaria import cargar_cuenta, invalidar
from src.features.vinculos.backup import backup_verificado

C = 46
VINCULAR = (2221, 2242, 2769)
MOTIVO_SEP = 'Irma Miranda — Sueldo Septiembre 2026'


def main():
    _assert_target_is_wc()
    print(backup_verificado('irma-miranda-036'))
    with reconciliation_transaction():
        st = [("INSERT INTO dbo.PagosSocioProveedor (IdMovimientoSocio,IdContacto,Criterio,FechaAlta) VALUES (?,?,'revision-036',SYSDATETIME())", (m, C))
              for m in VINCULAR if not fetch_all('SELECT 1 x FROM dbo.PagosSocioProveedor WHERE IdMovimientoSocio=?', (m,))]
        if st:
            execute_write_transaction(st)
        if not fetch_all('SELECT 1 x FROM dbo.MovimientosCuentaSocio WHERE IdSocio=2 AND Motivo=? AND Anulada=0', (MOTIVO_SEP,)):
            i = execute_write_transaction([("INSERT INTO dbo.MovimientosCuentaSocio (IdSocio,Tipo,Importe,Fecha,Medio,Motivo,Usuario,Anulada,ImporteUSD,ImporteKgCarne) "
                                            "OUTPUT INSERTED.IdMovimiento VALUES (2,'Devolucion',244274,'2026-10-01','Banco Galicia',?,'Sergio (036, revisión 21/10/2026)',0,0,0)",
                                            (MOTIVO_SEP,))])[0]
            execute_write_transaction([("INSERT INTO dbo.PagosSocioProveedor (IdMovimientoSocio,IdContacto,Criterio,FechaAlta) VALUES (?,?,'revision-036',SYSDATETIME())", (i, C))])
    invalidar()
    saldo = round(cargar_cuenta(C, refrescar=True)['saldoPesos'], 2)
    if abs(saldo) >= 0.005 and not fetch_all("SELECT 1 x FROM dbo.AjustesCuentaCorriente WHERE IdContacto=? AND Motivo LIKE 'Irma: redondeo%'", (C,)):
        with reconciliation_transaction():
            execute_write_transaction([("INSERT INTO dbo.AjustesCuentaCorriente (IdContacto,Fecha,Lado,Importe,Motivo,Usuario,FechaAlta) VALUES (?,?,?,?,?,?,SYSDATETIME())",
                                        (C, '2026-10-01', 'Credito' if saldo < 0 else 'Deuda', abs(saldo),
                                         'Irma: redondeo de sueldos pagados por los socios (jun-2025 -$40, mar-2026 +$27 y centavos). Sergio 21/10/2026: no se le debe nada.',
                                         'Sergio (036, revisión 21/10/2026)'))])
        invalidar()
    print('saldo', cargar_cuenta(C, refrescar=True)['saldoPesos'])


if __name__ == '__main__': main()
