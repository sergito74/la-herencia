"use client";
import { BackfillRevision } from './BackfillRevision';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { organismosBackfill, diagnosticoBackfill } from '@/services/backfillImpuestosApi';
import { formatMoneda } from '@/lib/format';
const ars=(v:string)=>formatMoneda(Number(v));
export function BackfillDiagnostico(){
 const [id,setId]=useState(0);const [page,setPage]=useState(1);
 const orgs=useQuery({queryKey:['backfill-organismos'],queryFn:organismosBackfill});
 const q=useQuery({queryKey:['backfill-diagnostico',id,page],queryFn:()=>diagnosticoBackfill(id,page),enabled:id>0});
 const d=q.data;
 return <section className="space-y-4">
  <label className="block">Organismo <select className="ml-2 rounded border p-2" value={id} onChange={e=>{setId(Number(e.target.value));setPage(1);}}><option value={0}>Elegir organismo</option>{orgs.data?.items.map(o=><option key={o.idOrganismo} value={o.idOrganismo}>{o.organismo}</option>)}</select></label>
  {orgs.isError&&<p role="alert">No se pudieron cargar los organismos. <button onClick={()=>orgs.refetch()}>Reintentar</button></p>}
  {id>0&&q.isLoading&&<p>Cargando diagnóstico de todo el histórico…</p>}
  {q.isError&&<p role="alert">{q.error.message} <button onClick={()=>q.refetch()}>Reintentar</button></p>}
  {d&&<><div className="flex flex-wrap gap-6 rounded border p-4"><span>Saldo actual: <strong>{ars(d.saldoActual)}</strong></span><span>Faltantes confirmados: <strong>{ars(d.totalFaltanteConfirmado)}</strong></span><span>Saldo proyectado: <strong>{ars(d.saldoProyectado)}</strong></span></div>
  <p>Todo el histórico · {d.total} movimientos. Los pendientes requieren revisión y no generan boletas.</p>
  <ul>{Object.entries(d.totalesPorEstado).map(([k,v])=><li key={k}>{k}: {v.cantidad} · {ars(v.importe)}</li>)}</ul>
  {d.advertencias.map(a=><p key={a} className="text-amber-800">{a}</p>)}
  <p className="text-sm">Movimientos sin contacto en los seis medios (fuera de este organismo): {d.sinContacto}. Asignarlos desde Tesorería antes de evaluarlos.</p>
  {!d.items.length?<p>No hay movimientos para mostrar.</p>:<div className="overflow-x-auto"><table className="w-full text-sm"><thead><tr>{['Fecha','Medio / referencia','Concepto','Importe ARS','Estado','Motivo'].map(x=><th key={x} className="p-2 text-left">{x}</th>)}</tr></thead><tbody>{d.items.map(p=><tr className="border-t" key={`${p.medio}:${p.idMovimiento}`}><td className="p-2">{p.fecha??'Sin fecha'}</td><td className="p-2">{p.medio} #{p.idMovimiento}</td><td className="p-2">{p.concepto}</td><td className="p-2 whitespace-nowrap">{ars(p.importe)}</td><td className="p-2">{p.estado}</td><td className="p-2">{p.motivo}</td></tr>)}</tbody></table></div>}
  <div className="flex gap-4"><button disabled={page===1} onClick={()=>setPage(page-1)}>Anterior</button><span>Página {page} de {Math.max(1,Math.ceil(d.total/d.pageSize))}</span><button disabled={page*d.pageSize>=d.total} onClick={()=>setPage(page+1)}>Siguiente</button></div>
  <BackfillRevision key={id} organismoId={id}/></>}
 </section>;
}
