"""ARBA (12): Ingresos Brutos según las DDJJ presentadas (portal ARBA, solo lectura, autorizado por Sergio 21/10/2026).

Fuentes (backups/arba-iibb-20261021/): detalle de las 93 DDJJ mensuales 2019-2026 (impuesto determinado, deducciones) y
descarga de deducciones por período (B bancarias, P percepciones, R retenciones); aviso de deuda IIBB 21/10/2026 (saldo a
favor $696.058,10).
Modelo (acordado con Sergio):
- Una boleta de Ingresos Brutos (Impuestos tipo 7) por DJ con impuesto o deducciones, número = comprobante ARBA,
  importe = impuesto determinado − percepciones − retenciones (esas deducciones ya están en las cuentas de proveedores y
  clientes). Las recaudaciones bancarias (B) y los pagos ya son créditos en ARBA; así el saldo IIBB del sistema = ARBA.
- Reemplaza las boletas IIBB cargadas desde 2019 (1056-1059, 1162, 1165), que quedan sustituidas por las de las DDJJ.
- BNA 14323 (10/07/2025, RECAUDACION ARBA $3.074,51) estaba en Argerami Cesar (13): pasa a ARBA.
Uso: --simular (default) muestra el saldo resultante; --aplicar escribe (respaldo verificado). Idempotente.
"""
import json
import sys
from collections import defaultdict
from datetime import date

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc
from src.features.vinculos.backup import backup_verificado

C = 12
EVID = r'C:\dev\LaHerencia\backups\arba-iibb-20261021'
VIEJAS = (1056, 1057, 1058, 1059, 1162, 1165)
SALDO_ARBA = 696058.10
USUARIO = 'Sergio (036, revisión 21/10/2026)'


def plan():
    ddjj = json.load(open(EVID + r'\ddjj.json'))
    ded = json.load(open(EVID + r'\deducciones.json'))
    pr, b = defaultdict(float), defaultdict(float)
    for x in ded:
        (b if x['tipo'] == 'B' else pr)[(x['anio'], x['mes'])] += x['imp']
    out = []
    for x in ddjj:
        k = (x['anio'], x['mes'])
        imp, contrib = x['impuesto'] or 0, x['contrib'] or 0
        if not imp and not contrib:
            continue
        # sin archivo de deducciones (02/2019) o con diferencia (05-06/2019, todo retenciones): deducciones no bancarias = total − B
        no_banc = contrib - b[k]
        neto = round(imp - no_banc, 2)
        vto = date(x['anio'] + (x['mes'] == 12), x['mes'] % 12 + 1, 15)
        out.append((vto, f"{x['mes']:02d} {x['anio']}", x['nro'], neto, imp, round(no_banc, 2), round(b[k], 2)))
    return out


def saldo(cur):
    cur.execute('SELECT ROUND(SUM(Credito)-SUM(Deuda),2) FROM dbo.vw_MovimientosCuenta_Base WHERE IdContacto=?', C)
    return float(cur.fetchone()[0] or 0)


def main():
    _assert_target_is_wc()
    aplicar = '--aplicar' in sys.argv
    filas = plan()
    if aplicar:
        print(backup_verificado('arba-iibb-ddjj-036'))
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=False)
    cur = conn.cursor()
    try:
        antes = saldo(cur)
        cur.execute("UPDATE dbo.[Movimientos BNA] SET IdContacto=? WHERE IdMovimientoBNA=14323 AND IdContacto=13", C)
        if cur.rowcount:
            cur.execute("INSERT INTO dbo.ReasignacionesContacto (Origen,IdOrigen,IdContactoAnterior,IdContactoNuevo,Motivo,Usuario,Fecha) "
                        "VALUES ('BNA',14323,13,?,?,?,SYSDATETIME())", C,
                        'RECAUDACION ARBA 10/07/2025 $3.074,51: deducción bancaria de la DJ IIBB 07/2025 (descarga de deducciones ARBA)', USUARIO)
        cur.execute('DELETE FROM dbo.Impuestos WHERE IdOrganismo=? AND IdTipoImpuesto=7 AND IdImpuesto IN (' + ','.join(map(str, VIEJAS)) + ')', C)
        for vto, per, nro, neto, imp, no_banc, banc in filas:
            cur.execute('SELECT 1 FROM dbo.Impuestos WHERE IdOrganismo=? AND IdTipoImpuesto=7 AND [Numero de documento]=?', C, nro)
            if cur.fetchone():
                continue
            cur.execute('INSERT INTO dbo.Impuestos (Fecha,IdOrganismo,IdTipoImpuesto,[Periodo liquidado],[Numero de documento],Importe,[Documento Original]) '
                        'VALUES (?,?,7,?,?,?,?)', vto.isoformat(), C, per, nro, neto, EVID + rf'\det_{nro}.txt')
        despues = saldo(cur)
        cur.execute("SELECT ROUND(SUM(Importe),2) FROM dbo.Impuestos WHERE IdOrganismo=? AND IdTipoImpuesto=26 AND Fecha>'2026-09-30'", C)
        patente_post = float(cur.fetchone()[0] or 0)
        print(f'DDJJ {len(filas)} | saldo ARBA antes {antes:,.2f} -> después {despues:,.2f} (sin patente posterior al corte {despues + patente_post:,.2f}) | ARBA IIBB a favor {SALDO_ARBA:,.2f}')
        for f in filas:
            print('  ', f[1], f[2], 'neto', f[3], '(imp', f[4], '- no bancarias', f[5], '| bancarias', f[6], ')')
        conn.commit() if aplicar else conn.rollback()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == '__main__': main()
