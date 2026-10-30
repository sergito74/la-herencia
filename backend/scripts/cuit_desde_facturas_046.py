"""046: completa el CUIT de proveedores que no lo tenían, tomado del PDF de sus propias facturas y validado en el padrón
de ARCA (necesario para la retención de Ganancias). Uso (desde backend/): python -m scripts.cuit_desde_facturas_046 <json> [--aplicar]
El JSON lo arma el relevamiento del 30/10/2026: CUIT más frecuente en los PDF, con dígito verificador y presente en el padrón.
"""
import json
import sys

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all
from src.features.vinculos.backup import backup_verificado

NOMBRE_COINCIDE = {402, 214, 158}  # Electro Zafiro, DER, 2JM: una sola aparición pero el padrón tiene la misma razón social
# T020: sin CUIT legible en los PDF, nombre único en el padrón (YPF Debenedetti: OPESSA, 2 de 5 facturas).
EXTRA = {287: ('33714360049', 'PC ELECTRO TIGRE SRL'), 176: ('30708610506', 'EDECAN SOCIEDAD ANONIMA'),
         282: ('30678774495', 'OPERADORA DE ESTACIONES DE SERVICIO')}

if __name__ == '__main__':
    _assert_target_is_wc()
    filas = [r for r in json.load(open(sys.argv[1], encoding='utf-8')) if r['seguro'] or r['id'] in NOMBRE_COINCIDE]
    filas += [{'id': i, 'rs': '', 'cuit': c, 'padron': (n,)} for i, (c, n) in EXTRA.items()]
    filas = [r for r in filas if not fetch_all("SELECT 1 x FROM dbo.Contactos WHERE IdContacto=? AND LEN([CUIT/CUIL])=11", (r['id'],))]
    for r in filas:
        print(r['id'], r['rs'], r['cuit'], r['padron'][0])
    print(len(filas), 'contactos')
    if '--aplicar' not in sys.argv:
        raise SystemExit('Simulación: usar --aplicar para grabar.')
    respaldo = backup_verificado('cuit-desde-facturas-046')
    stmts = [("UPDATE dbo.Contactos SET [CUIT/CUIL]=? WHERE IdContacto=? AND ([CUIT/CUIL] IS NULL OR LEN([CUIT/CUIL])<11)",
              (r['cuit'], r['id'])) for r in filas]
    stmts.append(("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) "
                  "VALUES ('cuit-desde-facturas-046','aplicada',?,'Claude046',SYSDATETIME(),'Claude046',SYSDATETIME(),?,?)",
                  (json.dumps({r['id']: r['cuit'] for r in filas}), respaldo,
                   f'CUIT de {len(filas)} proveedores tomado de sus facturas PDF y validado en el padrón de ARCA.')))
    execute_write_transaction(stmts)
    print('Aplicado. Respaldo:', respaldo)
