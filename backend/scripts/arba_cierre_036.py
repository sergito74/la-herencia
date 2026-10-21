"""ARBA (12): cierre de la cuenta (Sergio 21/10/2026).

- Ajuste "diferencia histórica IIBB 2011-2018 (declarado vs. informado por agentes)" de $1.249,70: con las 100 DDJJ cargadas
  (arba_iibb_ddjj_036) el IIBB del sistema daba $697.307,80 a favor y el aviso de deuda ARBA $696.058,10.
- Saldo externo = aviso de deuda IIBB 21/10/2026 (saldo a favor $696.058,10); inmobiliario y automotor con deuda $0.
- Ficha cerrada: al corte 30/09/2026 el saldo = saldo a favor IIBB; la patente cuota 8/2026 (09/10/2026, $174.161,30) es
  posterior al corte (su pago entra con el extracto de octubre).
Idempotente.
"""
from datetime import date

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.auditoria_cuentas.bimonetaria import cargar_cuenta, invalidar
from src.features.revision_cuentas import evidencia, fichas
from src.features.vinculos.backup import backup_verificado

C = 12
USUARIO = 'Sergio (036, revisión 21/10/2026)'
MOTIVO = 'ARBA: diferencia histórica IIBB 2011-2018 (declarado vs. informado por agentes)'
NOTA = ('Conciliada 21/10/2026 contra avisos de deuda ARBA: IIBB a favor $696.058,10 (100 DDJJ 12/2011-2025 del portal, '
        'importe = impuesto − percepciones − retenciones; recaudaciones bancarias = las informadas por ARBA), inmobiliario y '
        'automotor $0. Patente Taos cuota 8/2026 posterior al corte. Ajuste histórico IIBB 2011-2018 $1.249,70.')


def main():
    _assert_target_is_wc()
    print(backup_verificado('arba-cierre-036'))
    if not fetch_all('SELECT 1 x FROM dbo.AjustesCuentaCorriente WHERE IdContacto=? AND Motivo=?', (C, MOTIVO)):
        with reconciliation_transaction():
            execute_write_transaction([('INSERT INTO dbo.AjustesCuentaCorriente (IdContacto,Fecha,Lado,Importe,Motivo,Usuario,FechaAlta) '
                                        'VALUES (?,?,?,?,?,?,SYSDATETIME())', (C, '2018-12-31', 'Deuda', 1249.70, MOTIVO, USUARIO))])
        invalidar()
    filas = cargar_cuenta(C, refrescar=True)['filas']
    al_corte = [f for f in filas if f['fecha'] <= date(2026, 9, 30)][-1]['saldoPesos']
    print('saldo al corte', round(al_corte, 2), '| hoy', round(filas[-1]['saldoPesos'], 2))
    fichas._asegurar_fila(C, USUARIO)
    if not fetch_all('SELECT 1 x FROM dbo.RevisionSaldosExternos WHERE IdContacto=? AND Anulado=0', (C,)):
        evidencia.crear_saldo_externo(C, date(2026, 9, 30), 696058.10, 'Pesos', 'portal',
                                      'Aviso de deuda ARBA IIBB 21/10/2026 (mail) + DDJJ del portal (backups/arba-iibb-20261021)',
                                      'Saldo a favor IIBB; inmobiliario y automotor con deuda $0', USUARIO)
    fichas.confirmar_inventario(C, [
        {'tipo': 'estado-proveedor', 'disponible': True, 'detalle': 'Avisos de deuda ARBA 21/10/2026: IIBB, inmobiliario 011-007957-5, automotor AG964SV'},
        {'tipo': 'certificado', 'disponible': True, 'detalle': 'DDJJ IIBB 12/2011-2026 y deducciones por agente (portal ARBA, solo lectura)'},
        {'tipo': 'extracto', 'disponible': True, 'detalle': 'Pagos y recaudaciones IIBB en Galicia/BNA'},
    ], USUARIO)
    # C1/C6 no aplican 1 a 1: las recaudaciones bancarias y los pagos IIBB se aplican al saldo de las DDJJ (ARBA no detalla
    # qué pago cancela cada período); el saldo total coincide con el aviso de deuda.
    motivo = ('Recaudaciones bancarias y pagos IIBB sin boleta 1 a 1: ARBA los aplica al saldo de las DDJJ (deducciones y '
              'compensaciones de saldo a favor); el saldo total = aviso de deuda ARBA 21/10/2026.')
    print(fichas.cambiar_estado(C, {'estado': 'cerrada-con-excepcion', 'nota': NOTA, 'motivoExcepcion': motivo}, USUARIO).get('estado'))


if __name__ == '__main__': main()
