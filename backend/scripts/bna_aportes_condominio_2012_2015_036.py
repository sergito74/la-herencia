"""BNA: 17 depósitos/transferencias 2012–2015 sin contacto = aportes del Condominio LSC a Giamigli (Sergio 22/10/2026).

Coinciden en fecha (±4 días) e importe con "Aportes Campo" (Movimientos Condominios.xlsx) o "Transferencia al Campo / a
Giamigli" (Movimientos LSC.xlsx, hoja Movs). Se asignan al contacto 549 (Condominio LSC) con log en ReasignacionesContacto
(log en AuditoriaCorrecciones: la FK no admite contacto anterior 0). Total $278.971,50. Idempotente.
"""
import json
import os

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.auditoria_cuentas.bimonetaria import cargar_cuenta, invalidar
from src.features.vinculos.backup import backup_verificado

IDS = (10295, 10324, 10339, 10348, 10746, 10790, 10825, 10830, 10863, 10888, 11101, 11119, 11240, 11254, 11295, 11300, 11790)
USUARIO = 'Sergio (036, caja condominio 22/10/2026)'


def main():
    _assert_target_is_wc()
    filas = fetch_all('SELECT IdMovimientoBNA i, Importe m FROM dbo.[Movimientos BNA] WHERE ISNULL(IdContacto,0)=0 AND IdMovimientoBNA IN (' + ','.join(map(str, IDS)) + ')')
    if not filas:
        print('ya aplicado'); return
    st = []
    for f in filas:
        st += [("UPDATE dbo.[Movimientos BNA] SET IdContacto=549, Contacto='Condominio LSC' WHERE IdMovimientoBNA=? AND ISNULL(IdContacto,0)=0", (f['i'],)),
]
    resp = backup_verificado('bna-aportes-condominio-036'); print(resp)
    st.append(("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) "
               "VALUES ('asignar-contacto-sin-contacto','aplicada',?,?,SYSDATETIME(),?,SYSDATETIME(),?,?)",
               (json.dumps({'tabla': 'Movimientos BNA', 'ids': [f['i'] for f in filas], 'contacto': 549}), USUARIO, USUARIO, os.path.basename(resp),
                'Depósitos BNA 2012-2015 sin contacto = aportes del Condominio LSC (Aportes Campo / Movimientos LSC)')))
    with reconciliation_transaction():
        execute_write_transaction(st)
    invalidar()
    print(len(filas), 'asignados', round(sum(float(f['m']) for f in filas), 2), '| 549', cargar_cuenta(549, refrescar=True)['saldoPesos'])


if __name__ == '__main__': main()
