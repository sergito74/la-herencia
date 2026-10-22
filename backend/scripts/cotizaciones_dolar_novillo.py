"""Cotizaciones en WC, independientes de "Parametros financieros.xlsx" (Sergio 22/10/2026).

Fuentes (las que cita la planilla Cajas Giamigli):
- Dólar BNA: api.errepar.com/syserrepar/apidolar/api/CotizacionesBNAII/byDates (billete y divisa, compra/venta).
  Tabla existente dbo.[Dolar BNA] (Fecha, Comp_billete, Vend_billete, Prom_billete, Comp_Divisa, Vend_Divisa, Prom_Divisa):
  se completa hasta ayer (solo días que faltan).
- Índice Novillo (INMAG sugerido para arrendamientos, Mercado Agroganadero): www.mercadoagroganadero.com.ar/dll/hacienda2.dll/
  haciinfo000013 (POST txtFechaIni/txtFechaFin). Tabla nueva dbo.IndiceNovillo (Fecha, CabIngresadas, Importe, Indice); los días
  sin índice (menos de 300 novillos) quedan con Indice NULL, como en la fuente.
Uso: python -m scripts.cotizaciones_dolar_novillo [--desde AAAA-MM-DD]  (re-corrible; por defecto completa lo que falta).
"""
import html
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all

UA = {'User-Agent': 'Mozilla/5.0'}
DOLAR_API = 'https://api.errepar.com/syserrepar/apidolar/api/CotizacionesBNAII/byDates?fechaInicial={}&fechaFinal={}'
MAG = 'https://www.mercadoagroganadero.com.ar/dll/hacienda2.dll/haciinfo000013'
INICIO_NOVILLO = date(2020, 3, 1)


def _num(s):
    s = (s or '').strip()
    if not s or s in ('S/D', '-') or s.startswith('-'):
        return None
    return float(s.replace('.', '').replace(',', '.')) if ',' in s else float(s)


def _entero(s):
    # Cantidades enteras con '.' de miles ("6.316"); _num las leería como decimales.
    s = (s or '').strip().replace('.', '')
    return int(s) if s.isdigit() else 0


def crear_tabla_novillo():
    import pyodbc
    from src.db.connection import CONNECTION_STRING
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=True)
    conn.cursor().execute("IF OBJECT_ID('dbo.IndiceNovillo') IS NULL CREATE TABLE dbo.IndiceNovillo ("
                                "Fecha date NOT NULL PRIMARY KEY, CabIngresadas int NULL, Importe decimal(20,2) NULL, Indice decimal(18,3) NULL, "
                                "Fuente varchar(60) NOT NULL DEFAULT 'mercadoagroganadero.com.ar', FechaCarga datetime2 NOT NULL DEFAULT SYSDATETIME())")
    conn.close()


def novillo(desde: date, hasta: date) -> list[tuple]:
    out = []
    ini = desde
    while ini <= hasta:
        fin = min(date(ini.year, 12, 31), hasta)
        datos = urllib.parse.urlencode({'ID': '', 'CP': '', 'FLASH': '', 'USUARIO': 'SIN IDENTIFICAR', 'OPCIONMENU': '', 'OPCIONSUBMENU': '',
                                        'txtFechaIni': ini.strftime('%d/%m/%Y'), 'txtFechaFin': fin.strftime('%d/%m/%Y')}).encode()
        t = urllib.request.urlopen(urllib.request.Request(MAG, data=datos, headers=UA), timeout=120).read().decode('latin-1')
        for f, cab, imp, ind in re.findall(r'<TD Align="Center">\w\w&nbsp;(\d\d/\d\d/\d{4})</TD><TD Align="Right">([^<]*)</TD><TD Align="Right">([^<]*)</TD>'
                                           r'<TD Align="Center">([^<]*)</TD>', t):
            out.append((datetime.strptime(f, '%d/%m/%Y').date(), _entero(cab), _num(imp), _num(html.unescape(ind).replace('*', '').strip())))
        ini = fin + timedelta(days=1)
    return out


def dolar(desde: date, hasta: date) -> list[tuple]:
    out = {}
    ini = desde
    while ini <= hasta:
        fin = min(ini + timedelta(days=365), hasta)
        r = json.loads(urllib.request.urlopen(urllib.request.Request(DOLAR_API.format(ini, fin), headers=UA), timeout=120).read())
        for x in r.get('data', []):
            f = datetime.fromisoformat(x['fecha'][:19]).date()
            bc, bv, dc, dv = (_num(x[k]) for k in ('billeteCompra', 'billeteVenta', 'divisaCompra', 'divisaVenta'))
            out[f] = (f, bc, bv, (bc + bv) / 2 if bc and bv else None, dc, dv, (dc + dv) / 2 if dc and dv else None)
        ini = fin + timedelta(days=1)
    return sorted(out.values())


def main():
    _assert_target_is_wc()
    ayer = date.today() - timedelta(days=1)
    desde_arg = next((datetime.strptime(a.split('=')[1], '%Y-%m-%d').date() for a in sys.argv if a.startswith('--desde=')), None)
    # Dólar
    ult = fetch_all('SELECT MAX(Fecha) f FROM dbo.[Dolar BNA]')[0]['f']
    d0 = desde_arg or ((ult.date() if hasattr(ult, 'date') else ult) - timedelta(days=10))
    filas = dolar(d0, ayer)
    existentes = {(r['f'].date() if hasattr(r['f'], 'date') else r['f']): r for r in fetch_all('SELECT Fecha f, Prom_billete p FROM dbo.[Dolar BNA] WHERE Fecha>=?', (d0,))}
    dif = [(f, existentes[f]['p'], p) for f, _, _, p, *_ in filas if f in existentes and p and existentes[f]['p'] and abs(existentes[f]['p'] - p) > 0.01]
    nuevas = [x for x in filas if x[0] not in existentes and x[3]]
    nuevas and execute_write_transaction([('INSERT INTO dbo.[Dolar BNA] (Fecha,Comp_billete,Vend_billete,Prom_billete,Comp_Divisa,Vend_Divisa,Prom_Divisa) VALUES (?,?,?,?,?,?,?)',
                                (x[0].isoformat(),) + x[1:]) for x in nuevas])
    print(f'Dólar BNA: {len(nuevas)} días agregados ({nuevas[0][0] if nuevas else "-"} a {nuevas[-1][0] if nuevas else "-"}); diferencias con lo existente: {dif[:5]}')
    # Novillo
    crear_tabla_novillo()
    ultn = fetch_all('SELECT MAX(Fecha) f FROM dbo.IndiceNovillo')[0]['f']
    n0 = desde_arg or ((datetime.fromisoformat(str(ultn)).date() + timedelta(days=1)) if ultn else INICIO_NOVILLO)
    filas = novillo(n0, ayer)
    hechas = {datetime.fromisoformat(str(r['f'])).date() for r in fetch_all('SELECT Fecha f FROM dbo.IndiceNovillo WHERE Fecha>=?', (n0.isoformat(),))}
    nuevas = [x for x in filas if x[0] not in hechas]
    nuevas and execute_write_transaction([('INSERT INTO dbo.IndiceNovillo (Fecha,CabIngresadas,Importe,Indice) VALUES (?,?,?,?)', (x[0].isoformat(),) + x[1:]) for x in nuevas])
    con = [x for x in nuevas if x[3]]
    print(f'Índice Novillo: {len(nuevas)} días agregados, {len(con)} con índice ({con[0][0] if con else "-"} a {con[-1][0] if con else "-"})')


if __name__ == '__main__': main()
