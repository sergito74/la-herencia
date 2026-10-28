import sys, json
from collections import defaultdict
sys.path.insert(0,'.')
from src.db.connection import fetch_all
fecha, monto = {}, {}
for f in fetch_all("SELECT IdMovimientoBNA i,[Fecha / Hora Mov#] f,Importe m FROM dbo.[Movimientos BNA]",()):
    fecha[('bna',f['i'])]=f['f'].date(); monto[('bna',f['i'])]=abs(float(f['m'] or 0))
for f in fetch_all("SELECT IdMovimiento i,Fecha f,ISNULL([Créditos],0)-ISNULL([Débitos],0) m FROM dbo.[Movimientos Galicia]",()):
    fecha[('galicia',f['i'])]=f['f'].date(); monto[('galicia',f['i'])]=abs(float(f['m'] or 0))
for f in fetch_all("SELECT IdPagoEfectivo i,Fecha f,[Importe imputado] m FROM dbo.vw_PagosEfectivoVigentes",()):
    fecha[('efectivo',f['i'])]=f['f'].date(); monto[('efectivo',f['i'])]=abs(float(f['m'] or 0))
apps=fetch_all("""SELECT a.IdAplicacion id,a.OrigenMovimiento medio,a.IdMovimientoOrigen mov,a.IdDocumentoAplicado doc,a.ImporteAplicado imp,
 a.Usuario u,a.Origen o,c.IdContacto ct,c.Fecha ff,v.ImporteDocumento tot,v.Moneda mon,v.[Tipo de Cambio] tc,c.[Tipo documento] td
 FROM dbo.AplicacionesPago a JOIN dbo.Compras c ON c.IdDeuda=a.IdDocumentoAplicado JOIN dbo.vw_Compras_ImporteDocumento v ON v.IdDeuda=c.IdDeuda
 WHERE a.Anulada=0 AND a.TipoDocumento='CompraDeuda'""",())
docs=defaultdict(list)
for f in fetch_all("""SELECT c.IdDeuda d,c.IdContacto ct,c.Fecha ff,v.ImporteDocumento tot,v.Moneda mon,v.[Tipo de Cambio] tc FROM dbo.Compras c
 JOIN dbo.vw_Compras_ImporteDocumento v ON v.IdDeuda=c.IdDeuda""",()):
    t=float(f['tot'] or 0)*(float(f['tc']) if f['mon']=='Dolares' and f['tc'] else 1)
    docs[f['ct']].append((f['d'],f['ff'].date() if f['ff'] else None,round(t,2)))
razon={r['i']:r['r'] for r in fetch_all("SELECT IdContacto i,[Razon Social] r FROM dbo.Contactos",())}
C=defaultdict(lambda: defaultdict(int)); porpago=defaultdict(list); apdoc=defaultdict(float); totdoc={}
ej=defaultdict(list)
for a in apps:
    ct=a['ct']; c=C[ct]; c['n']+=1
    if a['u']=='sistema-conciliacion-020': c['r020']+=1
    if a['o']=='fifo-032': c['fifo']+=1
    t=float(a['tot'] or 0)*(float(a['tc']) if a['mon']=='Dolares' and a['tc'] else 1); totdoc[a['doc']]=t
    apdoc[a['doc']]+=float(a['imp'])
    k=(a['medio'],a['mov'])
    if a['medio'] in('bna','galicia','efectivo') and k in fecha and a['ff']:
        lag=(fecha[k]-a['ff'].date()).days
        porpago[(ct,)+k].append((a['doc'],a['ff'].date(),float(a['imp']),a['id']))
        if lag>180 and fecha[k].year>=2025: c['lag2526']+=1; c['$lag2526']+=int(float(a['imp']))
        if lag<-90: c['$antic']+=int(float(a['imp']))
        if lag>365: c['lag365']+=1
        elif lag>180: c['lag180']+=1
        elif lag>90: c['lag90']+=1
        if lag<-90: c['antic90']+=1
        if lag>180 and len(ej[ct])<3: ej[ct].append(f"app {a['id']} pago {k[0]}#{k[1]} {fecha[k]} -> doc {a['doc']} {a['ff'].date()} ${float(a['imp']):,.2f}")
for d,ap in apdoc.items():
    if ap>totdoc[d]+1: C[next(a['ct'] for a in apps if a['doc']==d)]['sobre']+=1
# fragmentacion con match unívoco + cruces de orden
pagos_ct=defaultdict(list)
for key,ls in porpago.items():
    ct,medio,mov=key; m=monto.get((medio,mov),0); fp=fecha[(medio,mov)]
    docsap=sorted(set((d,ff) for d,ff,_,_ in ls))
    pagos_ct[ct].append((fp,max(ff for _,ff in docsap),min(ff for _,ff in docsap)))
    exacto=[d for d,ff,t in docs[ct] if ff and abs(t-m)<0.02 and abs((fp-ff).days)<=60]
    usados={d for d,_ in docsap}
    montos_ct=[t for _,_,t in docs[ct]]
    if len(exacto)==1 and not (usados & set(exacto)) and sum(1 for t in montos_ct if abs(t-m)<0.02)<=2:
        C[ct]['matchIgnorado']+=1; C[ct]['$match']+=int(m)
        if fp.year>=2025: C[ct]['match2526']+=1; C[ct]['$match2526']+=int(m)
        if len(ej[ct])<6: ej[ct].append(f"pago {medio}#{mov} {fp} ${m:,.2f} aplicado a {len(usados)} doc(s) viejos; existe doc {exacto[0]} de importe idéntico")
for ct,ps in pagos_ct.items():
    ps.sort(); inv=0
    for i in range(1,len(ps)):
        if ps[i][1] < ps[i-1][2]: inv+=1   # pago posterior aplicado entero a docs anteriores a los del pago previo
    C[ct]['inversiones']=inv
out=[]
for ct,c in C.items():
    rojo=c['r020']+c['matchIgnorado']+c['lag365']+c['sobre']
    amar=c['lag180']+c['inversiones']
    est='ROJA' if c['matchIgnorado'] or c['sobre'] or c['r020']>0 and (c['lag180']+c['lag365']) or c['lag365']>2 else ('AMARILLA' if amar or c['lag365'] or c['r020'] else 'VERDE')
    out.append(dict(ct=ct,razon=razon.get(ct),est=est,**c,ej=ej[ct]))
json.dump(out,open(sys.argv[1],'w',encoding='utf-8'),ensure_ascii=False,default=str,indent=0)
from collections import Counter
print(Counter(o['est'] for o in out))
for o in sorted(out,key=lambda o:(o['est']!='ROJA',-(o['matchIgnorado']*5+o['lag365']+o['r020']+o['sobre']*5)))[:80]:
    print(o['est'],o['ct'],(o['razon'] or '')[:30],{k:o[k] for k in ('n','r020','fifo','lag180','lag365','lag2526','$lag2526','antic90','$antic','matchIgnorado','$match','match2526','$match2526','sobre') if o.get(k)})
