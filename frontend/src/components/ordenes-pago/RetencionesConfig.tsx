'use client';
import { useState } from 'react';
import { useMutation,useQuery,useQueryClient } from '@tanstack/react-query';
import { SoloLectura } from '@/components/auth/SoloLectura';
import { ContactoSelect } from '@/components/ui/ContactoSelect';
import { formatFecha } from '@/lib/format';
import { actualizarPadron,agregarExclusion,borrarExclusion,exclusionesRetencion,guardarRubroRetencion,regimenesRetencion,rubrosRetencion,type RubroRetencion } from '@/services/ordenesPagoApi';
import { boton,campo,hoy } from './FormularioOrdenPago';

const ESTADOS=['Borrador','Validado contador','Ratificado estudio'] as const;

function FilaRubro({r,regimenes}:{r:RubroRetencion;regimenes:{codRegimen:number;concepto:string}[]}) {
 const qc=useQueryClient();
 const [cod,setCod]=useState(r.codRegimen);const [estado,setEstado]=useState(r.estado);const [obs,setObs]=useState(r.observaciones??'');
 const cambiado=cod!==r.codRegimen||estado!==r.estado||obs!==(r.observaciones??'');
 const guardar=useMutation({mutationFn:()=>guardarRubroRetencion(r.idRubro,{codRegimen:cod,estado,observaciones:obs||null}),onSuccess:()=>qc.invalidateQueries({queryKey:['ret-rubros']})});
 return <tr className="border-t"><td className="p-2">{r.rubro}</td>
  <td><select aria-label={`Concepto de ${r.rubro}`} className={`${campo} w-full`} value={cod??''} onChange={e=>setCod(e.target.value?Number(e.target.value):null)}><option value="">No corresponde retener</option>{regimenes.map(x=><option key={x.codRegimen} value={x.codRegimen}>{x.codRegimen} · {x.concepto}</option>)}</select></td>
  <td><select aria-label={`Estado de ${r.rubro}`} className={campo} value={estado} onChange={e=>setEstado(e.target.value as RubroRetencion['estado'])}>{ESTADOS.map(x=><option key={x}>{x}</option>)}</select></td>
  <td><input aria-label={`Observaciones de ${r.rubro}`} className={`${campo} w-full`} maxLength={300} value={obs} onChange={e=>setObs(e.target.value)}/></td>
  <td className="p-2"><SoloLectura><button className={campo} disabled={!cambiado||guardar.isPending} onClick={()=>guardar.mutate()}>Guardar</button></SoloLectura>{guardar.isError&&<span role="alert" className="text-red-700"> {guardar.error.message}</span>}</td></tr>;
}

export function RetencionesConfig() {
 const qc=useQueryClient();
 const rubros=useQuery({queryKey:['ret-rubros'],queryFn:rubrosRetencion});
 const regimenes=useQuery({queryKey:['ret-regimenes'],queryFn:regimenesRetencion,staleTime:3600_000});
 const exclusiones=useQuery({queryKey:['ret-exclusiones'],queryFn:exclusionesRetencion});
 const [contacto,setContacto]=useState<number|null>(null);const [nombre,setNombre]=useState<string|null>(null);
 const [desde,setDesde]=useState(hoy());const [hasta,setHasta]=useState(hoy());const [obs,setObs]=useState('');
 const refrescar=()=>qc.invalidateQueries({queryKey:['ret-exclusiones']});
 const alta=useMutation({mutationFn:()=>agregarExclusion({idContacto:contacto!,desde,hasta,observaciones:obs}),onSuccess:()=>{refrescar();setObs('');}});
 const baja=useMutation({mutationFn:borrarExclusion,onSuccess:refrescar});
 const padron=useMutation({mutationFn:actualizarPadron});
 const pendientes=rubros.data?.filter(r=>r.estado==='Borrador').length??0;
 return <div className="space-y-6">
  <section className="rounded border bg-white p-4 space-y-2"><h2 className="font-semibold">Padrón de ARCA</h2>
   <p className="text-sm text-slate-600">Situación de cada proveedor en Ganancias y monotributo, según el padrón público de ARCA. Se actualiza cada semana.</p>
   <SoloLectura><button className={boton} disabled={padron.isPending} onClick={()=>padron.mutate()}>{padron.isPending?'Descargando padrón…':'Actualizar padrón'}</button></SoloLectura>
   {padron.data&&<p role="status">Padrón al {formatFecha(padron.data.actualizado)}: {padron.data.encontrados} de {padron.data.contactosConCuit} proveedores con CUIT.</p>}
   {padron.isError&&<p role="alert" className="text-red-700">{padron.error.message}</p>}
  </section>
  <section className="rounded border bg-white p-4 space-y-2"><h2 className="font-semibold">Concepto de retención por rubro</h2>
   <p className="text-sm text-slate-600">Borrador armado por el sistema: lo valida el contador y lo ratifica el estudio contable. {pendientes>0&&`${pendientes} rubros en borrador.`}</p>
   {(rubros.isFetching||regimenes.isFetching)&&<p>Cargando…</p>}{[rubros.error,regimenes.error].filter(Boolean).map((e,i)=><p key={i} role="alert" className="text-red-700">{e?.message}</p>)}
   <div className="overflow-auto max-h-[600px]"><table className="w-full text-sm"><thead className="bg-slate-50"><tr><th className="p-2 text-left">Rubro</th><th className="text-left">Concepto de ARCA</th><th>Estado</th><th className="text-left">Observaciones</th><th></th></tr></thead><tbody>
    {rubros.data?.map(r=><FilaRubro key={r.idRubro} r={r} regimenes={regimenes.data??[]}/>)}
   </tbody></table></div>
  </section>
  <section className="rounded border bg-white p-4 space-y-3"><h2 className="font-semibold">Certificados de exclusión</h2>
   <p className="text-sm text-slate-600">Proveedores con certificado de exclusión de Ganancias vigente: no se les retiene mientras dure la vigencia.</p>
   <SoloLectura><form className="flex flex-wrap items-end gap-3" onSubmit={e=>{e.preventDefault();alta.mutate();}}>
    <div className="min-w-72"><ContactoSelect value={contacto} razonSocial={nombre} label="Proveedor" onChange={(id,n)=>{setContacto(id);setNombre(n);}}/></div>
    <label>Desde <input required type="date" className={campo} value={desde} onChange={e=>setDesde(e.target.value)}/></label>
    <label>Hasta <input required type="date" className={campo} value={hasta} onChange={e=>setHasta(e.target.value)}/></label>
    <label>Observaciones <input className={campo} maxLength={300} value={obs} onChange={e=>setObs(e.target.value)}/></label>
    <button className={boton} disabled={!contacto||alta.isPending}>Agregar</button></form></SoloLectura>
   {[alta.error,baja.error,exclusiones.error].filter(Boolean).map((e,i)=><p key={i} role="alert" className="text-red-700">{e?.message}</p>)}
   <table className="w-full text-sm"><thead><tr><th className="text-left">Proveedor</th><th>Desde</th><th>Hasta</th><th className="text-left">Observaciones</th><th></th></tr></thead><tbody>
    {exclusiones.data?.map(x=><tr key={x.idExclusion} className="border-t"><td className="p-2">{x.proveedor}</td><td className="text-center">{formatFecha(x.desde)}</td><td className="text-center">{formatFecha(x.hasta)}</td><td>{x.observaciones}</td><td><SoloLectura><button className={campo} onClick={()=>baja.mutate(x.idExclusion)}>Quitar</button></SoloLectura></td></tr>)}
   </tbody></table>{exclusiones.data?.length===0&&<p className="text-slate-600">No hay certificados de exclusión cargados.</p>}
  </section>
 </div>;
}

