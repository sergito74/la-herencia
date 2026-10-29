"use client";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ContactoSelect } from "@/components/ui/ContactoSelect";
import { SoloLectura } from "@/components/auth/SoloLectura";
import { formatMoneda, formatFecha } from "@/lib/format";
import { listarTrabajos, obtenerTrabajo, guardarTrabajo, liquidacionesTrabajo, vincularTrabajo, desvincularTrabajo,
  type Trabajo, type TrabajoInput, type Filtros } from "@/services/trabajosEventualesApi";

const input = "rounded border border-border bg-white px-2 py-1.5 text-sm";
const boton = "rounded border border-border px-3 py-1.5 text-sm hover:bg-surface-sunken disabled:opacity-50";
const errorTexto = (e: unknown) => e instanceof Error ? e.message : "No se pudo completar la operación";

function Formulario({ trabajo, onGuardado, cerrar }: { trabajo?: Trabajo; onGuardado: (t: Trabajo) => void; cerrar: () => void }) {
  const [datos, setDatos] = useState<TrabajoInput>(trabajo ?? { idContacto: 0, fecha: new Date().toLocaleDateString("sv-SE"), descripcion: "",
    dias: 1, jornal: 0, viaticos: 0, redondeo: 0, estadoPago: "Pendiente", numeroRecibo: null, observaciones: null });
  const [nombre, setNombre] = useState(trabajo?.trabajador ?? "");
  const [error, setError] = useState(""); const [ocupado, setOcupado] = useState(false);
  const poner = <K extends keyof TrabajoInput>(campo: K, valor: TrabajoInput[K]) => setDatos(d => ({ ...d, [campo]: valor }));
  async function guardar(e: React.FormEvent) { e.preventDefault(); setOcupado(true); setError("");
    try { onGuardado(await guardarTrabajo(datos, trabajo?.idTrabajo)); } catch(e) { setError(errorTexto(e)); } finally { setOcupado(false); }
  }
  return <form onSubmit={guardar} className="space-y-4 rounded-lg border border-border bg-surface p-5">
    <h2 className="text-lg font-semibold">{trabajo ? "Editar trabajo" : "Nuevo trabajo eventual"}</h2>
    <div className="grid gap-3 md:grid-cols-3">
      <ContactoSelect label="Trabajador" tipoContacto="Empleado" value={datos.idContacto || null} razonSocial={nombre}
        onChange={(id,n) => { poner("idContacto", id ?? 0); setNombre(n ?? ""); }} />
      <label className="text-sm">Fecha<input required type="date" className={`${input} block w-full`} value={datos.fecha.slice(0,10)} onChange={e=>poner("fecha",e.target.value)} /></label>
      <label className="text-sm">Estado de pago<select className={`${input} block w-full`} value={datos.estadoPago} onChange={e=>poner("estadoPago",e.target.value as "Pendiente"|"Pagado")}><option>Pendiente</option><option>Pagado</option></select></label>
    </div>
    <label className="block text-sm">Labor realizada<input required maxLength={500} className={`${input} block w-full`} value={datos.descripcion} onChange={e=>poner("descripcion",e.target.value)} /></label>
    <div className="grid gap-3 md:grid-cols-4">{([["dias","Días trabajados","0.0001"],["jornal","Jornal ($)","0.01"],["viaticos","Viáticos ($)","0.01"],["redondeo","Ajuste de redondeo ($)","0.01"]] as const).map(([campo,label,step])=>
      <label key={campo} className="text-sm">{label}<input required type="number" step={step} min={campo === "redondeo" ? undefined : campo === "dias" ? "0.0001" : "0"} className={`${input} block w-full`} value={datos[campo]} onChange={e=>poner(campo,Number(e.target.value))} /></label>)}</div>
    <p className="text-sm font-medium">Total del trabajo: {formatMoneda(Math.round((datos.dias*datos.jornal+datos.viaticos)*100)/100+datos.redondeo)}</p>
    <div className="grid gap-3 md:grid-cols-2"><label className="text-sm">Número de recibo<input className={`${input} block w-full`} maxLength={40} value={datos.numeroRecibo ?? ""} onChange={e=>poner("numeroRecibo",e.target.value || null)} /></label>
    <label className="text-sm">Observaciones<input className={`${input} block w-full`} maxLength={1000} value={datos.observaciones ?? ""} onChange={e=>poner("observaciones",e.target.value || null)} /></label></div>
    {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
    <div className="flex gap-2"><button disabled={ocupado || !datos.idContacto} className="rounded bg-finance px-4 py-2 text-sm text-white">{ocupado ? "Guardando…" : "Guardar trabajo"}</button><button type="button" className={boton} onClick={cerrar}>Cancelar</button></div>
  </form>;
}

function Detalle({ id, onEditar, onCambio, salarioInicial }: { id: number; onEditar: (t: Trabajo)=>void; onCambio: ()=>void; salarioInicial?: number }) {
  const qc = useQueryClient(); const [salario,setSalario]=useState(salarioInicial ?? 0); const [importe,setImporte]=useState("");
  const [error,setError]=useState(""); const [ocupado,setOcupado]=useState(false);
  const { data:t,isLoading,isError }=useQuery({queryKey:["trabajo-eventual",id],queryFn:()=>obtenerTrabajo(id)});
  const { data:liqs }=useQuery({queryKey:["liquidaciones-trabajo",id],queryFn:()=>liquidacionesTrabajo(id)});
  async function actuar(fn:()=>Promise<unknown>) {setOcupado(true);setError("");try {await fn(); await qc.invalidateQueries({queryKey:["trabajo-eventual",id]});await qc.invalidateQueries({queryKey:["liquidaciones-trabajo",id]});onCambio();setImporte("");}catch(e){setError(errorTexto(e));}finally{setOcupado(false);}}
  if(isLoading)return <p>Cargando detalle…</p>; if(isError||!t)return <p role="alert">No se pudo cargar el trabajo.</p>;
  return <section className="space-y-4 rounded-lg border border-border bg-surface p-5">
    <div className="flex flex-wrap justify-between gap-2"><div><h2 className="text-lg font-semibold">{t.trabajador} · {formatFecha(t.fecha)}</h2><p>{t.descripcion}</p></div><SoloLectura><button className={boton} onClick={()=>onEditar(t)}>Editar trabajo</button></SoloLectura></div>
    <p className="text-sm">{t.dias} días × {formatMoneda(t.jornal)} · Viáticos {formatMoneda(t.viaticos)}{t.redondeo ? ` · Redondeo ${formatMoneda(t.redondeo)}` : ""}</p>
    <div className="flex flex-wrap gap-6 text-sm"><span>Total <strong>{formatMoneda(t.total)}</strong></span><span>Incluido en liquidaciones <strong>{formatMoneda(t.vinculado)}</strong></span><span>Sin vincular <strong>{formatMoneda(t.sinVincular)}</strong></span></div>
    <p className="text-sm text-ink-secondary">{t.estadoPago}{t.origen ? " según la planilla" : ""}{t.numeroRecibo ? ` · Recibo ${t.numeroRecibo}` : ""}{t.observaciones ? ` · ${t.observaciones}` : ""}</p>
    <h3 className="font-medium">Liquidaciones relacionadas</h3>
    {t.vinculos?.length ? t.vinculos.map(v=><div key={v.idSalario} className="flex flex-wrap items-center gap-3 text-sm"><Link className="text-finance underline" href={`/personal/remuneraciones?empleado=${encodeURIComponent(t.trabajador)}&highlight=${v.idSalario}`}>{v.periodo} · {formatFecha(v.fecha)}</Link><strong>{formatMoneda(v.importe)}</strong><SoloLectura><button disabled={ocupado} className={boton} onClick={()=>actuar(()=>desvincularTrabajo(id,v.idSalario))}>Quitar vínculo</button></SoloLectura></div>) : <p className="text-sm text-ink-secondary">Todavía no se vinculó a una liquidación.</p>}
    <SoloLectura>{t.sinVincular>0 && <form className="flex flex-wrap items-end gap-2" onSubmit={e=>{e.preventDefault();actuar(()=>vincularTrabajo(id,salario,Number(importe)));}}>
      <label className="text-sm">Liquidación del trabajador<select required className={`${input} block max-w-lg`} value={salario||""} onChange={e=>setSalario(Number(e.target.value))}><option value="">Elegir liquidación…</option>{liqs?.filter(l=>l.disponible>0 && !t.vinculos?.some(v=>v.idSalario===l.idSalario)).map(l=><option key={l.idSalario} value={l.idSalario}>{l.periodo} · {formatFecha(l.fecha)} · disponible {formatMoneda(l.disponible)}</option>)}</select></label>
      <label className="text-sm">Importe a vincular<input required type="number" min="0.01" max={Math.min(t.sinVincular,liqs?.find(l=>l.idSalario===salario)?.disponible ?? t.sinVincular)} step="0.01" className={`${input} block w-40`} value={importe} onChange={e=>setImporte(e.target.value)} /></label>
      <button disabled={ocupado||!salario} className={boton}>Vincular importe</button>
    </form>}</SoloLectura>
    {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
    <p className="text-xs text-ink-secondary">Vincular identifica lo incluido en un recibo. No genera otro gasto ni registra un pago. Un importe sin vincular no significa que esté impago.</p>
    <Link href={`/personal/remuneraciones?empleado=${encodeURIComponent(t.trabajador)}`} className="text-sm text-finance underline">Ver remuneraciones del trabajador</Link>
  </section>;
}

export function TrabajosEventuales() {
  const qs=useSearchParams(); const qc=useQueryClient();
  const [contacto,setContacto]=useState<number|null>(Number(qs.get("idContacto"))||null);const [nombre,setNombre]=useState(qs.get("empleado")??"");
  const [filtros,setFiltros]=useState<Filtros>({idContacto:Number(qs.get("idContacto"))||undefined,idSalario:Number(qs.get("idSalario"))||undefined,page:1});
  const [desde,setDesde]=useState("");const [hasta,setHasta]=useState("");const [estado,setEstado]=useState("");const [vinculacion,setVinculacion]=useState("");
  const [id,setId]=useState<number|null>(null);const [form,setForm]=useState<Trabajo|"nuevo"|null>(null);
  const {data,isLoading,isError,refetch}=useQuery({queryKey:["trabajos-eventuales",filtros],queryFn:()=>listarTrabajos(filtros)});
  useEffect(()=>{ if(id) document.getElementById("detalle-trabajo")?.scrollIntoView({behavior:"smooth",block:"start"}); },[id]);
  const refrescar=()=>{void qc.invalidateQueries({queryKey:["trabajos-eventuales"]});void qc.invalidateQueries({queryKey:["trabajo-eventual"]});};
  return <main className="mx-auto max-w-none space-y-5 px-8 py-6">
    <div className="flex flex-wrap items-start justify-between gap-3"><div><h1 className="text-2xl font-semibold">Trabajos eventuales</h1><p className="mt-1 text-sm text-ink-secondary">Labores, jornales, viáticos y su relación con las liquidaciones del personal.</p></div><div className="flex gap-3"><Link className={boton} href={`/personal/remuneraciones${nombre?`?empleado=${encodeURIComponent(nombre)}`:""}`}>Remuneraciones</Link><SoloLectura><button className={boton} onClick={()=>setForm("nuevo")}>Nuevo trabajo</button></SoloLectura></div></div>
    {filtros.idSalario && <div className="flex flex-wrap items-center gap-3 rounded border border-border p-3 text-sm"><span>Trabajos vinculados a la liquidación seleccionada.</span><button className="text-finance underline" onClick={()=>setFiltros(f=>({...f,idSalario:undefined,page:1}))}>Ver todos los trabajos del trabajador</button></div>}
    <form className="flex flex-wrap items-end gap-3" onSubmit={e=>{e.preventDefault();setId(null);setFiltros({idContacto:contacto??undefined,desde,hasta,estadoPago:estado,vinculacion,page:1});}}>
      <ContactoSelect label="Trabajador" tipoContacto="Empleado" value={contacto} razonSocial={nombre} onChange={(i,n)=>{setContacto(i);setNombre(n??"");}} />
      <label className="text-sm">Desde<input type="date" className={`${input} block`} value={desde} onChange={e=>setDesde(e.target.value)}/></label><label className="text-sm">Hasta<input type="date" className={`${input} block`} value={hasta} onChange={e=>setHasta(e.target.value)}/></label>
      <label className="text-sm">Pago<select className={`${input} block`} value={estado} onChange={e=>setEstado(e.target.value)}><option value="">Todos</option><option>Pendiente</option><option>Pagado</option></select></label>
      <label className="text-sm">Liquidación<select className={`${input} block`} value={vinculacion} onChange={e=>setVinculacion(e.target.value)}><option value="">Todas</option><option value="sin">Sin vincular</option><option value="parcial">Parcial</option><option value="completo">Vinculado</option></select></label><button className={boton}>Buscar</button>
    </form>
    {form && <SoloLectura><Formulario key={form==="nuevo"?"nuevo":form.idTrabajo} trabajo={form==="nuevo"?undefined:form} cerrar={()=>setForm(null)} onGuardado={t=>{setForm(null);setId(t.idTrabajo);refrescar();}} /></SoloLectura>}
    {data && <div className="grid gap-3 sm:grid-cols-3">{([["Total trabajos",data.resumen.totalTrabajos],["Incluido en liquidaciones",data.resumen.totalVinculado],["Sin vincular",data.resumen.sinVincular]] as const).map(([titulo,valor])=><div key={titulo} className="rounded-lg border border-border p-4"><p className="text-xs text-ink-secondary">{titulo}</p><strong className="text-xl">{formatMoneda(valor)}</strong></div>)}</div>}
    {id && <div id="detalle-trabajo" className="scroll-mt-20"><Detalle key={id} id={id} onEditar={setForm} onCambio={refrescar} salarioInicial={Number(qs.get("idSalario"))||undefined}/></div>}
    {isLoading ? <p>Cargando trabajos…</p> : isError ? <p role="alert">No se pudieron cargar los trabajos. <button className="underline" onClick={()=>refetch()}>Reintentar</button></p> : data && <>
      <div className="overflow-x-auto rounded-lg border border-border"><table className="w-full text-sm"><thead className="bg-surface-sunken"><tr>{["Fecha","Trabajador / labor","Días","Jornal","Viáticos","Total","Liquidado","Pago / recibo",""] .map((h,i)=><th key={i} className="p-3 text-left">{h}</th>)}</tr></thead><tbody>{data.items.map(t=><tr key={t.idTrabajo} className={`border-t border-border ${id===t.idTrabajo?"bg-blue-50":""}`}><td className="whitespace-nowrap p-3">{formatFecha(t.fecha)}</td><td className="p-3"><strong>{t.trabajador}</strong><div className="text-xs text-ink-secondary">{t.descripcion}</div></td><td className="p-3">{t.dias}</td><td className="whitespace-nowrap p-3">{formatMoneda(t.jornal)}</td><td className="whitespace-nowrap p-3">{formatMoneda(t.viaticos)}</td><td className="whitespace-nowrap p-3 font-medium">{formatMoneda(t.total)}</td><td className="whitespace-nowrap p-3">{formatMoneda(t.vinculado)}</td><td className="p-3">{t.estadoPago}{t.numeroRecibo ? ` · ${t.numeroRecibo}` : ""}</td><td className="p-3"><button className="text-finance underline" onClick={()=>{setId(t.idTrabajo);setForm(null);}}>Ver detalle</button></td></tr>)}</tbody></table>{!data.items.length && <p className="p-6 text-ink-secondary">No hay trabajos para estos filtros.</p>}</div>
      <div className="flex items-center gap-3 text-sm"><span>{data.total} trabajos · Página {filtros.page??1}</span><button className={boton} disabled={(filtros.page??1)<=1} onClick={()=>setFiltros(f=>({...f,page:(f.page??1)-1}))}>Anterior</button><button className={boton} disabled={(filtros.page??1)*50>=data.total} onClick={()=>setFiltros(f=>({...f,page:(f.page??1)+1}))}>Siguiente</button></div>
    </>}

  </main>;
}
