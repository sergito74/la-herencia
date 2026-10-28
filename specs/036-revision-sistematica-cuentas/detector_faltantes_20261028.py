import sys, statistics as st
from collections import defaultdict
from datetime import date, timedelta
sys.path.insert(0,'.')
from src.db.connection import fetch_all
desde=date(2020,1,1)
fac=defaultdict(list)
for f in fetch_all("""SELECT c.IdContacto ct,c.Fecha f,v.ImporteDocumento t,c.[Tipo documento] td FROM Compras c JOIN vw_Compras_ImporteDocumento v ON v.IdDeuda=c.IdDeuda
 WHERE c.Fecha>=? AND c.[Tipo documento] NOT LIKE 'Nota de C%'""",(desde,)):
    fac[f['ct']].append((f['f'].date(),float(f['t'] or 0)))
pag=defaultdict(list)
for q in ("SELECT IdContacto ct,[Fecha / Hora Mov#] f,Importe m FROM [Movimientos BNA] WHERE Importe<0 AND [Fecha / Hora Mov#]>=?",
          "SELECT IdContacto ct,Fecha f,-ISNULL([Débitos],0) m FROM [Movimientos Galicia] WHERE ISNULL([Débitos],0)>0 AND Fecha>=?",
          "SELECT IdContacto ct,Fecha f,-[Importe imputado] m FROM vw_PagosEfectivoVigentes WHERE Fecha>=?"):
    for f in fetch_all(q,(desde,)):
        if f['ct']: pag[f['ct']].append((f['f'].date(),abs(float(f['m'] or 0))))
razon={r['i']:r['r'] for r in fetch_all("SELECT IdContacto i,[Razon Social] r FROM Contactos",())}
hoy=date(2026,10,28); res=[]
for ct,ls in fac.items():
    meses=sorted({(d.year,d.month) for d,_ in ls})
    if len(meses)<12: continue
    fechas=sorted(d for d,_ in ls)
    # ciclo: mediana de distancia entre meses con factura
    idx=[y*12+m for y,m in meses]; gaps=[b-a for a,b in zip(idx,idx[1:])]
    ciclo=st.median(gaps[-24:])
    if ciclo>3: continue
    cobertura=len(meses)/(idx[-1]-idx[0]+1)
    if ciclo==1 and cobertura<0.8: continue
    huecos=[]
    for a,b in zip(idx,idx[1:]):
        if b-a>ciclo*1.5:
            for k in range(a+int(ciclo),b,int(ciclo)):
                y,m=divmod(k-1,12); m+=1
                ini=date(y,m,1); fin=(ini+timedelta(days=32*int(ciclo))).replace(day=1)
                p=[x for x in pag[ct] if ini<=x[0]<fin+timedelta(days=45)]
                huecos.append((f"{m:02d}/{y}", "con pago" if p else "sin pago"))
    # atraso actual
    prox=idx[-1]+int(ciclo); ult=meses[-1]
    atraso = (hoy.year*12+hoy.month) > prox
    ultmonto=[t for d,t in ls if (d.year,d.month)==ult][-1]
    res.append((ct,razon.get(ct),int(ciclo),round(cobertura*100),huecos,f"{ult[1]:02d}/{ult[0]}",atraso,ultmonto))
res.sort(key=lambda r:-len(r[4]))
for r in res:
    print(f"{r[0]} | {r[1]} | ciclo {r[2]}m | cobertura {r[3]}% | ult {r[5]} ${r[7]:,.0f}{' | ATRASADA' if r[6] else ''} | huecos {len(r[4])}: " + ', '.join(f'{h}({p})' for h,p in r[4]))
