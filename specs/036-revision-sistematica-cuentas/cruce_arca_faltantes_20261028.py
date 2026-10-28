import json, sys, re, unicodedata
from collections import Counter, defaultdict
from datetime import date, timedelta
sys.path.insert(0,'.')
from src.db.connection import fetch_all
res=json.load(open(sys.argv[1],encoding='utf-8'))
def norm(s): return re.sub(r'[^a-z0-9]','',unicodedata.normalize('NFKD',s or '').encode('ascii','ignore').decode().lower())
razon={r['i']:r['r'] for r in fetch_all("SELECT IdContacto i,[Razon Social] r FROM Contactos",())}
cuit={r['i']:re.sub(r'\D','',r['c'] or '') for r in fetch_all("SELECT IdContacto i,[CUIT/CUIL] c FROM Contactos",())}
compras=fetch_all("SELECT c.IdDeuda,c.IdContacto,c.Fecha,c.[Nro Documento] nro,c.Moneda,v.ImporteDocumento tot FROM Compras c JOIN vw_Compras_ImporteDocumento v ON v.IdDeuda=c.IdDeuda",())
por_ct=defaultdict(list)
for w in compras: por_ct[w['IdContacto']].append(w)
# CUIT emisor -> contacto: por CUIT cargado, o aprendido de los que cruzaron con número
ok=json.load(open(sys.argv[1],encoding='utf-8'))
cuit2ct={}
for k,v in cuit.items():
    if len(v)==11: cuit2ct.setdefault(v,k)
for r in res:
    if r.get('ct') and 'CUIT_DISTINTO' not in r['estado']: cuit2ct.setdefault(r['cuit'],r['ct'])
def tot_ars(r): return r['total']*(r['tc'] if r['moneda']!='$' else 1)
out=Counter(); falt=[]; amb_ok=0
for r in res:
    if r['estado']=='AMBIGUO':
        cs=[w for w in compras if w['IdDeuda'] in {c[0] for c in r['candidatos']}]
        hit=[w for w in cs if str(w['Fecha'].date())==r['fecha'] or abs(abs(float(w['tot'] or 0))-abs(tot_ars(r)))<1 or abs(abs(float(w['tot'] or 0))-abs(r['total']))<0.05]
        if len(hit)==1: amb_ok+=1; cuit2ct.setdefault(r['cuit'],hit[0]['IdContacto']); continue
        out['ambiguo_sin_resolver']+=1; falt.append(('AMBIGUO',r,None)); continue
for r in res:
    if r['estado']!='NO_EN_WC': continue
    ct=cuit2ct.get(r['cuit'])
    if ct is None:
        n=norm(r['emisor'])[:10]
        m=[k for k,v in razon.items() if n and norm(v)[:10]==n]
        ct=m[0] if len(m)==1 else None
    f=date.fromisoformat(r['fecha'])
    if ct:
        hit=[w for w in por_ct[ct] if abs((w['Fecha'].date()-f).days)<=10 and (abs(abs(float(w['tot'] or 0))-abs(tot_ars(r)))<1 or abs(abs(float(w['tot'] or 0))-abs(r['total']))<0.05)]
        if hit:
            out['cargado_otro_numero']+=1; falt.append(('OTRO_NUMERO',r,(ct,hit[0]['IdDeuda'],hit[0]['nro'],str(hit[0]['Fecha'].date())))); continue
    out['falta_en_wc']+=1; falt.append(('FALTA',r,ct))
print('ambiguos resueltos',amb_ok, dict(out))
json.dump([[a,b,c] for a,b,c in falt],open(sys.argv[2],'w',encoding='utf-8'),ensure_ascii=False,indent=1,default=str)
print('== FALTA en WC (por emisor)')
g=defaultdict(list)
for a,r,ct in falt:
    if a=='FALTA': g[(r['emisor'],ct)].append(r)
for (em,ct),ls in sorted(g.items(),key=lambda x:-len(x[1])):
    print(f"{em[:34]:34} ct={ct} n={len(ls)} total=${sum(tot_ars(x) for x in ls):,.0f} | "+'; '.join(f"{x['fecha']} t{x['tipo']} {x['pv']}-{x['nro']} {x['moneda']}{x['total']:,.2f}" for x in ls[:4]))
print('== AMBIGUOS sin resolver'); [print('  ',r['fecha'],r['emisor'][:30],r['pv'],r['nro'],r['total']) for a,r,c in falt if a=='AMBIGUO'][:5]
