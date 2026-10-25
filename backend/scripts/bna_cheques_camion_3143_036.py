"""BNA: 3 cheques Maignal 122750-52 ($3.143, venta del camión) depositados 04/10, 08/11 y 06/12/2012, sin contacto.

La planilla Movs del Condominio los anota «Cheque Venta Camion - Depósito Nación» por $3.134 (dígitos invertidos);
Maignal/Cuotas y pagos Venta Maignal.xlsx, hoja Listado Cheques, los lista por $3.143 con vencimientos 25/09-25/11/2012.
Sergio 25/10/2026: buscar en la planilla de Maignal. Se asignan a 549 como el resto de los cheques del camión. Idempotente.
"""
import json
import os

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.auditoria_cuentas.bimonetaria import cargar_cuenta, invalidar
from src.features.vinculos.backup import backup_verificado

IDS = (10626, 10668, 10721)
USUARIO = 'Sergio (036, cheques camión 3143, 25/10/2026)'


def main():
    _assert_target_is_wc()
    filas = fetch_all('SELECT IdMovimientoBNA i, Importe m FROM dbo.[Movimientos BNA] WHERE ISNULL(IdContacto,0)=0 AND IdMovimientoBNA IN (' + ','.join(map(str, IDS)) + ')')
    if not filas:
        print('ya aplicado'); return
    st = []
    for f in filas:
        st += [("UPDATE dbo.[Movimientos BNA] SET IdContacto=549, Contacto='Condominio LSC' WHERE IdMovimientoBNA=? AND ISNULL(IdContacto,0)=0", (f['i'],)),
]
    resp = backup_verificado('bna-cheques-camion-3143-036'); print(resp)
    st.append(("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) "
               "VALUES ('asignar-contacto-sin-contacto','aplicada',?,?,SYSDATETIME(),?,SYSDATETIME(),?,?)",
               (json.dumps({'tabla': 'Movimientos BNA', 'ids': [f['i'] for f in filas], 'contacto': 549}), USUARIO, USUARIO, os.path.basename(resp),
                'Cheques Maignal 3143 (venta camión) depositados en BNA 2012 = aporte del Condominio LSC; planilla Movs los anota 3134')))
    with reconciliation_transaction():
        execute_write_transaction(st)
    invalidar()
    print(len(filas), 'asignados', round(sum(float(f['m']) for f in filas), 2), '| 549', cargar_cuenta(549, refrescar=True)['saldoPesos'])


if __name__ == '__main__': main()
