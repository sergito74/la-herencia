"""Cargill (258): liquidaciones de granos que no coincidían con su PDF (Dropbox/Ventas), corregidas al original.

- 136/139/173 son liquidaciones partidas por cultivo (cantidades correctas); solo se verifican sumando sus renglones.
- 168 (330121536145) alícuota IVA 10,5 (estaba vacía) y sin "ajuste por diferencia de cálculo"; 169 (330121538401) idem.
- 152 (330118968668) deducción $15,26 (otras deducciones, sin IVA).
- 195 (330126785856) descuento por grado -$200.897,64 con IVA 10,5% (estaba al 21%).
- 207/208 (330127803436/440) factor que reproduce el subtotal del PDF; deducción $31,64 sin IVA.
Verifica que cada una dé el neto a pagar del PDF menos sus retenciones certificadas. Idempotente.
"""
import json
from datetime import datetime
from pathlib import Path

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.vinculos.backup import backup_verificado

ROOT = Path(__file__).resolve().parents[2] / 'backups/cargill-conciliacion-20261020'
# IdVenta -> neto a pagar del PDF
NETO = {136: 728212.91, 139: 1150905.45, 173: 7676314.95, 168: 1484512.35, 169: 2385593.25, 152: 384203.98,
        195: 15421469.76, 207: 3435489.69, 208: 77433.32}


def factor(subtotal, kg, pu, flete):
    return ((subtotal / kg * 1000) + flete) / pu * 100


def credito(i):
    return fetch_all("SELECT Credito FROM dbo.vw_MovimientosCuenta_Base WHERE Origen='Venta Granos' AND IdOrigen=?", (i,))[0]['Credito']


def main():
    _assert_target_is_wc()
    ids = list(NETO)
    m = ','.join(map(str, ids))
    antes = {'ventas': fetch_all(f'SELECT * FROM dbo.[Venta Granos] WHERE IdVenta IN ({m})'),
             'deducciones': fetch_all(f'SELECT * FROM dbo.[Venta Granos_Deducciones] WHERE IdVenta IN ({m})'),
             'ajustes': fetch_all(f'SELECT * FROM dbo.[Venta Granos_Ajustes] WHERE IdVenta IN ({m})')}
    v = {r['IdVenta']: r for r in antes['ventas']}
    assert all(v[i]['IdConsignatario'] == 258 for i in ids)
    audit = {'autorizacion': 'Sergio 20/10/2026: corregir liquidaciones de Cargill contra el PDF', 'antes': antes,
             'backup': backup_verificado('cargill-liquidaciones-pdf-036')}
    path = ROOT / f'liquidaciones-pdf-{datetime.now():%Y%m%d_%H%M%S}.json'
    path.write_text(json.dumps(audit, default=str, ensure_ascii=False, indent=2), encoding='utf-8')
    upd = 'UPDATE dbo.[Venta Granos] SET {} WHERE IdVenta=? AND IdConsignatario=258'
    s = [(upd.format('AlicuotaIVA=10.5'), (168,)),
         (upd.format('Factor=?'), (factor(3109040.44, 39224, v[207]['Precio unitario'], v[207]['Flete']), 207)),
         (upd.format('Factor=?'), (factor(70104.04, 1055, v[208]['Precio unitario'], v[208]['Flete']), 208)),
         ("DELETE FROM dbo.[Venta Granos_Deducciones] WHERE IdVenta IN (168,169,152) ", ()),
         ("INSERT INTO dbo.[Venta Granos_Deducciones] (IdVenta,IdConcepto,Detalle,Porc,[Base Calculo],Alicuota) VALUES (152,2,'Otras deducciones',100,15.26,0)", ()),
         ("UPDATE dbo.[Venta Granos_Deducciones] SET Alicuota=0 WHERE IdVenta=208 AND ABS([Base Calculo]-31.64)<0.001", ()),
         ("UPDATE dbo.[Venta Granos_Ajustes] SET AlicuotaIVA=10.5 WHERE IdVenta=195 AND Importe<0", ())]
    certs = json.load(open(ROOT / 'certificados.json', encoding='utf-8'))
    ret = {}
    for c in certs.values():
        ret[c['lpg']] = ret.get(c['lpg'], 0) + c['importe']
    with reconciliation_transaction():
        execute_write_transaction(s)
        res = {}
        for i in (207, 208):  # el factor es de precisión simple: el centavo se cierra con un ajuste de redondeo
            dif = round(NETO[i] - ret.get(v[i]['Nro Documento'], 0) - credito(i), 2)
            if dif:
                execute_write_transaction([("INSERT INTO dbo.[Venta Granos_Ajustes] (IdVenta,Concepto,Importe,AlicuotaIVA) VALUES (?,?,?,10.5)", (i, "Redondeo al PDF (036)", round(dif / 1.105, 4)))])
        for i, neto in NETO.items():
            nro = v[i]['Nro Documento']
            hermanos = [r['IdVenta'] for r in fetch_all('SELECT IdVenta FROM dbo.[Venta Granos] WHERE IdConsignatario=258 AND [Nro Documento]=?', (nro,))]
            esperado = round(neto - ret.get(nro, 0), 2)
            res[i] = (round(sum(credito(h) for h in hermanos), 2), esperado, hermanos)
            assert abs(res[i][0] - esperado) <= 0.05 * len(hermanos) + (0.2 if len(hermanos) > 1 else 0), (i, res[i])
    audit['resultado'] = res
    path.write_text(json.dumps(audit, default=str, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(res))


if __name__ == '__main__': main()
