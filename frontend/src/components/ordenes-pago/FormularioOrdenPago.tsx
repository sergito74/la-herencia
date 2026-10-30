'use client';
import { useState } from 'react';
import { useMutation,useQuery } from '@tanstack/react-query';
import { ContactoSelect } from '@/components/ui/ContactoSelect';
import { formatFecha,formatMoneda,numeroAEdicionLocal,normalizarNumeroPegado,parseNumeroLocal } from '@/lib/format';
import { facturasOP,guardarOP,proponerRetencion,type OrdenOP,type MedioOP,type PropuestaRetencion } from '@/services/ordenesPagoApi';

export const campo='rounded border border-slate-300 px-3 py-2 text-sm';
export const boton='rounded bg-emerald-700 px-4 py-2 text-sm text-white disabled:opacity-50';
/** Importe en formato local (miles '.', decimales ','); nunca type=number. */
export function ImporteInput({value,onChange,className=`${campo} w-36`,...rest}:{value:number|null|undefined;onChange:(n:number)=>void;className?:string;'aria-label'?:string;disabled?:boolean;required?:boolean}) {
 const [texto,setTexto]=useState(value?numeroAEdicionLocal(value):'');
 const [previo,setPrevio]=useState(value);
 if(value!==previo){setPrevio(value);if(parseNumeroLocal(texto)!==(value??0))setTexto(value?numeroAEdicionLocal(value):'');}
 return <input {...rest} inputMode="decimal" className={className} value={texto} onChange={e=>{const t=normalizarNumeroPegado(e.target.value);setTexto(t);onChange(Math.round(parseNumeroLocal(t)*100)/100);}}/>;
}
export const hoy=()=>new Date().toLocaleDateString('en-CA');

export function FormularioOrdenPago({orden,cerrar,guardado}:{orden?:OrdenOP;cerrar:()=>void;guardado:()=>void}) {
 const [contacto,setContacto]=useState<number|null>(orden?.idContacto??null);
 const [nombre,setNombre]=useState<string|null>(orden?.proveedor??null);
 const [fecha,setFecha]=useState(orden?.fecha??hoy());
 const [pago,setPago]=useState(orden?.fechaPago??hoy());
 const [nota,setNota]=useState(orden?.observaciones??'');
 const [seleccion,setSeleccion]=useState<Record<number,number>>(Object.fromEntries(orden?.facturas.map(f=>[f.idCompra,f.importe])??[]));
 const [medios,setMedios]=useState<MedioOP[]>(orden?.medios??[{medio:'Transferencia',cuenta:'',importe:0}]);
 const [propuesta,setPropuesta]=useState<PropuestaRetencion|null>(orden?.retenciones?.length?{condicion:{retiene:true},lineas:orden.retenciones,total:orden.retencionGanancias,avisos:[]}:null);
 const facturasBody=()=>Object.entries(seleccion).map(([idCompra,importe])=>({idCompra:Number(idCompra),importe}));
 const calcular=useMutation({mutationFn:()=>proponerRetencion({idContacto:contacto!,fechaPago:pago,facturas:facturasBody(),excluirOrden:orden?.idOrdenPago}),onSuccess:setPropuesta});
 const cambiarSeleccion:typeof setSeleccion=v=>{setSeleccion(v);setPropuesta(null);};
 const q=useQuery({queryKey:['op-facturas',contacto,orden?.idOrdenPago],queryFn:()=>facturasOP(contacto!,orden?.idOrdenPago),enabled:!!contacto});
 const total=Object.values(seleccion).reduce((a,b)=>a+b,0);
 const retencion=propuesta?.total??0;
 const diferencia=Math.round((total-retencion-medios.reduce((a,b)=>a+b.importe,0))*100)/100;
 const guardar=useMutation({mutationFn:()=>guardarOP({idContacto:contacto!,fecha,fechaPago:pago,moneda:'ARS',observaciones:nota,
   facturas:facturasBody(),medios,retenciones:propuesta?.lineas??[],version:orden?.version},orden?.idOrdenPago),onSuccess:guardado});
 return <section className="rounded-xl border bg-white p-5 space-y-4" aria-label="Confeccionar orden de pago">
  <h2 className="text-xl font-semibold">{orden?'Editar borrador':'Nueva orden de pago'}</h2>
  <p className="text-sm text-slate-600">Importes en pesos. La orden prepara el pago; no envía dinero ni cancela facturas.</p>
  <form className="space-y-4" onSubmit={e=>{e.preventDefault();guardar.mutate();}}>
   <ContactoSelect value={contacto} razonSocial={nombre} label="Proveedor" onChange={(id,n)=>{setContacto(id);setNombre(n);cambiarSeleccion({});}}/>
   <div className="flex flex-wrap gap-4"><label>Fecha <input required aria-label="Fecha de orden" className={campo} type="date" value={fecha} onChange={e=>setFecha(e.target.value)}/></label>
   <label>Pago previsto <input required aria-label="Fecha de pago prevista" className={campo} type="date" value={pago} onChange={e=>{setPago(e.target.value);setPropuesta(null);}}/></label></div>
   {q.isFetching&&<p>Cargando facturas…</p>}{q.isError&&<p role="alert">{q.error.message}</p>}
   {contacto&&q.data?.length===0&&<p>No hay facturas en pesos con saldo pendiente para este proveedor.</p>}
   <div className="overflow-auto max-h-80"><table className="w-full text-sm"><thead><tr><th>Factura</th><th>Fecha</th><th>Saldo</th><th>En otras órdenes</th><th>A pagar</th></tr></thead><tbody>
    {q.data?.map(f=><tr key={f.idCompra} className="border-b"><td className="p-2"><label><input type="checkbox" aria-label={`Seleccionar ${f.numero}`} disabled={f.disponible<=0} checked={f.idCompra in seleccion} onChange={e=>cambiarSeleccion(v=>{const n={...v};if(e.target.checked)n[f.idCompra]=f.disponible;else delete n[f.idCompra];return n;})}/> {f.numero||'Sin número'}</label></td><td>{formatFecha(f.fecha)}</td><td>{formatMoneda(f.saldo)}</td><td>{formatMoneda(f.reservado)}</td><td><ImporteInput aria-label={`Importe ${f.numero}`} disabled={!(f.idCompra in seleccion)} value={seleccion[f.idCompra]} onChange={n=>cambiarSeleccion(v=>({...v,[f.idCompra]:n}))}/></td></tr>)}
   </tbody></table></div>
   <section className="rounded border border-slate-200 p-3 space-y-2" aria-label="Retención de Ganancias">
    <div className="flex flex-wrap items-center gap-3"><h3 className="font-semibold">Retención de Ganancias</h3>
     <button type="button" className={campo} disabled={!contacto||total<=0||calcular.isPending} onClick={()=>calcular.mutate()}>{calcular.isPending?'Consultando ARCA…':'Calcular retención'}</button></div>
    {!propuesta&&<p className="text-sm text-slate-600">Calculala antes de guardar: usa el simulador de ARCA y suma los pagos del mes al proveedor.</p>}
    {calcular.isError&&<p role="alert" className="text-red-700">{calcular.error.message}</p>}
    {propuesta&&!propuesta.condicion.retiene&&<p>No corresponde retener: {propuesta.condicion.motivo}</p>}
    {propuesta?.condicion.aviso&&<p className="text-amber-800">{propuesta.condicion.aviso}</p>}
    {propuesta?.condicion.retiene&&propuesta.lineas.length===0&&<p>Las facturas elegidas no tienen conceptos alcanzados por la retención.</p>}
    {!!propuesta?.lineas.length&&<table className="w-full text-sm"><thead><tr><th className="text-left">Concepto</th><th>Base de este pago</th><th>Pagos anteriores del mes</th><th>No sujeto</th><th>Alícuota</th><th>Retenciones anteriores</th><th>A retener</th></tr></thead><tbody>
     {propuesta.lineas.map(l=><tr key={l.codRegimen} className="border-t"><td>{l.concepto}</td><td className="text-right">{formatMoneda(l.basePago)}</td><td className="text-right">{formatMoneda(l.pagosAnteriores)}</td><td className="text-right">{formatMoneda(l.noSujeto)}</td><td className="text-right">{l.alicuota?`${String(l.alicuota).replace('.',',')}%`:'Escala'}</td><td className="text-right">{formatMoneda(l.retencionesAnteriores)}</td><td className="text-right font-semibold">{formatMoneda(l.retencion)}</td></tr>)}
    </tbody></table>}
    {propuesta?.avisos.map(a=><p key={a} className="text-sm text-slate-600">{a}</p>)}
    {propuesta&&<p className="text-sm text-slate-600">Es una propuesta: confirmala antes de emitir. El certificado lo emite el estudio contable.</p>}
   </section>
   <h3 className="font-semibold">Medios de pago previstos</h3>
   {medios.map((m,i)=><div key={i} className="flex flex-wrap gap-2">
    <select aria-label={`Medio ${i+1}`} className={campo} value={m.medio} onChange={e=>setMedios(v=>v.map((x,j)=>j===i?{...x,medio:e.target.value as MedioOP['medio']}:x))}>{['Transferencia','Efectivo','Cheque'].map(x=><option key={x}>{x}</option>)}</select>
    <input required maxLength={150} aria-label={`Cuenta ${i+1}`} placeholder="Banco, caja o cheque previsto" className={`${campo} flex-1`} value={m.cuenta} onChange={e=>setMedios(v=>v.map((x,j)=>j===i?{...x,cuenta:e.target.value}:x))}/>
    <ImporteInput required aria-label={`Importe del medio ${i+1}`} value={m.importe} onChange={n=>setMedios(v=>v.map((x,j)=>j===i?{...x,importe:n}:x))}/>
    {medios.length>1&&<button type="button" onClick={()=>setMedios(v=>v.filter((_,j)=>i!==j))}>Quitar</button>}</div>)}
   <button type="button" className={campo} onClick={()=>setMedios(v=>[...v,{medio:'Transferencia',cuenta:'',importe:0}])}>Agregar medio</button>
   <p className="font-semibold">Facturas: {formatMoneda(total)} · Retención: {formatMoneda(retencion)} · Neto a pagar: {formatMoneda(total-retencion)} · Falta distribuir: {formatMoneda(diferencia)}</p>
   <label className="block">Observaciones<textarea aria-label="Observaciones" className={`${campo} block w-full`} maxLength={1000} value={nota} onChange={e=>setNota(e.target.value)}/></label>
   {guardar.isError&&<p role="alert" className="text-red-700">{guardar.error.message}</p>}
   <div className="flex gap-3"><button className={boton} disabled={guardar.isPending||!contacto||total<=0||!propuesta||diferencia!==0}>Guardar borrador</button><button type="button" className={campo} onClick={cerrar}>Cancelar</button></div>
  </form>
 </section>;
}
