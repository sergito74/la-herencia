'use client';
import { CuotasInfo, cuotasPendientes, esAdelanto } from './CuotasInfo';
import { useEffect, useRef, useState } from 'react';
import { useMutation,useQuery } from '@tanstack/react-query';
import { ContactoSelect } from '@/components/ui/ContactoSelect';
import { formatFecha,formatMoneda,formatNumero,numeroAEdicionLocal,normalizarNumeroPegado,parseNumeroLocal } from '@/lib/format';
import { facturasOP,guardarOP,proponerRetencion,type OrdenOP,type MedioOP,type PropuestaRetencion } from '@/services/ordenesPagoApi';

export const campo='rounded border border-slate-300 px-3 py-2 text-sm';
export const boton='rounded bg-emerald-700 px-4 py-2 text-sm text-white disabled:opacity-50';
/** Importe en formato local (miles '.', decimales ','); nunca type=number. */
export function ImporteInput({value,onChange,className=`${campo} w-36`,...rest}:{value:number|null|undefined;onChange:(n:number)=>void;className?:string;'aria-label'?:string;disabled?:boolean;required?:boolean}) {
 const [texto,setTexto]=useState(value?numeroAEdicionLocal(value):'');
 const [previo,setPrevio]=useState(value);
 if(value!==previo){setPrevio(value);if(parseNumeroLocal(texto)!==(value??0))setTexto(value?numeroAEdicionLocal(value):'');}
 const [foco,setFoco]=useState(false);
 // Sin foco se ve como moneda ($ 775.226,22); al entrar, el número solo para editar.
 return <input {...rest} inputMode="decimal" className={`${className} text-right`} value={foco?texto:(value?formatMoneda(value):'')} onFocus={()=>setFoco(true)} onBlur={()=>setFoco(false)} onChange={e=>{const t=normalizarNumeroPegado(e.target.value);setTexto(t);onChange(Math.round(parseNumeroLocal(t)*100)/100);}}/>;
}
export const hoy=()=>new Date().toLocaleDateString('en-CA');

/** `inicial`: orden nueva que arranca desde "Facturas a pagar" con el proveedor y las facturas ya elegidas. */
export function FormularioOrdenPago({orden,inicial,cerrar,guardado}:{orden?:OrdenOP;inicial?:{idContacto:number;proveedor:string|null;facturas:Record<number,number>};cerrar:()=>void;guardado:()=>void}) {
 const [contacto,setContacto]=useState<number|null>(orden?.idContacto??inicial?.idContacto??null);
 const [nombre,setNombre]=useState<string|null>(orden?.proveedor??inicial?.proveedor??null);
 const [fecha,setFecha]=useState(orden?.fecha??hoy());
 const [pago,setPago]=useState(orden?.fechaPago??hoy());
 const [nota,setNota]=useState(orden?.observaciones??'');
 const [seleccion,setSeleccion]=useState<Record<number,number>>(orden?Object.fromEntries(orden.facturas.map(f=>[f.idCompra,f.importe])):inicial?.facturas??{});
 const [medios,setMedios]=useState<MedioOP[]>(orden?.medios??[{medio:'Transferencia',cuenta:'',importe:0}]);
 // Facturas en cuotas (Sergio 12/11/2026): la orden sale por el total de la factura con un medio por cuota. La retención
 // se calcula como ARCA (total sin IVA) y se resta del pago; si la cuota 1 es un adelanto, se resta de la cuota 2.
 const [planAuto,setPlanAuto]=useState(!orden);
 const editarMedios:typeof setMedios=v=>{setPlanAuto(false);setMedios(v);};
 const [adelantos,setAdelantos]=useState<Record<number,boolean>>({});
 const [propuesta,setPropuesta]=useState<PropuestaRetencion|null>(orden?.retenciones?.length?{condicion:{retiene:true},lineas:orden.retenciones,total:orden.retencionGanancias,avisos:[]}:null);
 const facturasBody=()=>Object.entries(seleccion).map(([idCompra,importe])=>({idCompra:Number(idCompra),importe}));
 const calcular=useMutation({mutationFn:()=>proponerRetencion({idContacto:contacto!,fechaPago:pago,facturas:facturasBody(),excluirOrden:orden?.idOrdenPago}),onSuccess:setPropuesta});
 const cambiarSeleccion:typeof setSeleccion=v=>{setSeleccion(v);setPropuesta(null);};
 const q=useQuery({queryKey:['op-facturas',contacto,orden?.idOrdenPago],queryFn:()=>facturasOP(contacto!,orden?.idOrdenPago),enabled:!!contacto});
 const total=Object.values(seleccion).reduce((a,b)=>a+b,0);
 const retencion=propuesta?.total??0;
 const diferencia=Math.round((total-retencion-medios.reduce((a,b)=>a+b.importe,0))*100)/100;
 // Sugerencia del pago: al abrir una orden nueva marca si la cuota 1 es un adelanto.
 const sugerido=useRef(false);
 useEffect(()=>{if(orden||sugerido.current||!q.data)return;sugerido.current=true;
  setAdelantos(x=>{const n={...x};q.data!.filter(f=>f.idCompra in seleccion).forEach(f=>{n[f.idCompra]=esAdelanto(f);});return n;});
 // eslint-disable-next-line react-hooks/exhaustive-deps
 },[q.data]);
 const neto=Math.round((total-retencion)*100)/100;
 // Medios sugeridos (hasta que se editen a mano): una factura en cuotas pagada completa → un medio por cuota con su fecha
 // (transferencia la primera, cheque/eCheq las siguientes) y la retención restada de la cuota 2 si la 1 es adelanto,
 // si no de la primera; en otro caso, un medio con el neto.
 useEffect(()=>{if(!planAuto||!q.data)return;
  const elegidas=q.data.filter(f=>f.idCompra in seleccion);
  const f=elegidas.length===1?elegidas[0]:null;
  const pend=f?cuotasPendientes(f):[];
  if(f&&pend.length>1&&Math.abs(seleccion[f.idCompra]-f.disponible)<0.01){
   const idx=adelantos[f.idCompra]&&pend.length>1?1:0;
   setMedios(pend.map((c,i)=>({medio:i===0?'Transferencia':'Cheque',cuenta:i===0?'Banco Galicia':'eCheq Banco Galicia',fecha:c.fecha.slice(0,10),
     importe:Math.round((c.saldo-(i===idx?retencion:0))*100)/100})));
  }else if(neto>0)setMedios(m=>[{...(m[0]??{medio:'Transferencia',cuenta:''}),importe:neto,fecha:null}]);
 // eslint-disable-next-line react-hooks/exhaustive-deps
 },[q.data,seleccion,retencion,adelantos,planAuto]);
 const guardar=useMutation({mutationFn:()=>guardarOP({idContacto:contacto!,fecha,fechaPago:pago,moneda:'ARS',observaciones:nota,
   facturas:facturasBody(),medios,retenciones:(propuesta?.lineas??[]).filter(l=>!l.diferida).map(({diferida:_d,...l})=>l),version:orden?.version},orden?.idOrdenPago),onSuccess:guardado});
 return <section className="rounded-xl border bg-white p-5 space-y-4" aria-label="Confeccionar orden de pago">
  <h2 className="text-xl font-semibold">{orden?'Editar borrador':'Nueva orden de pago'}</h2>
  <p className="text-sm text-slate-600">Importes en pesos; las facturas en dólares se pasan a pesos al tipo de cambio de la factura. La orden prepara el pago; no envía dinero ni cancela facturas.</p>
  <form className="space-y-4" onSubmit={e=>{e.preventDefault();guardar.mutate();}}>
   <ContactoSelect value={contacto} razonSocial={nombre} label="Proveedor" onChange={(id,n)=>{setContacto(id);setNombre(n);cambiarSeleccion({});}}/>
   <div className="flex flex-wrap gap-4"><label>Fecha <input required aria-label="Fecha de orden" className={campo} type="date" value={fecha} onChange={e=>setFecha(e.target.value)}/></label>
   <label>Pago previsto <input required aria-label="Fecha de pago prevista" className={campo} type="date" value={pago} onChange={e=>{setPago(e.target.value);setPropuesta(null);}}/></label></div>
   {q.isFetching&&<p>Cargando facturas…</p>}{q.isError&&<p role="alert">{q.error.message}</p>}
   {contacto&&q.data?.length===0&&<p>No hay facturas en pesos con saldo pendiente para este proveedor.</p>}
   <div className="overflow-auto max-h-80"><table className="w-full text-sm"><thead><tr><th>Factura</th><th>Fecha</th><th>Vencimiento</th><th>Saldo</th><th>En otras órdenes</th><th>A pagar</th></tr></thead><tbody>
    {q.data?.map(f=><tr key={f.idCompra} className="border-b"><td className="p-2"><label><input type="checkbox" aria-label={`Seleccionar ${f.numero}`} disabled={f.disponible<=0} checked={f.idCompra in seleccion} onChange={e=>cambiarSeleccion(v=>{const n={...v};if(e.target.checked){n[f.idCompra]=f.disponible;setAdelantos(x=>({...x,[f.idCompra]:esAdelanto(f)}));}else delete n[f.idCompra];return n;})}/> {f.numero||'Sin número'}</label>{f.moneda==='Dolares'&&!!f.tc&&<span className="block text-xs text-slate-600">Factura en US$ · {formatMoneda(f.total/f.tc,'Dolares')} al TC {formatNumero(f.tc)}</span>}</td><td>{formatFecha(f.fecha)}</td><td>{formatFecha(f.fechaVto??f.fecha)}<CuotasInfo f={f}/>{(f.cuotas?.length??0)>1&&f.idCompra in seleccion&&<label className="block text-xs"><input type="checkbox" checked={!!adelantos[f.idCompra]} onChange={e=>setAdelantos(x=>({...x,[f.idCompra]:e.target.checked}))}/> La cuota 1 es un adelanto (la retención se resta de la cuota 2)</label>}</td><td>{formatMoneda(f.saldo)}</td><td>{formatMoneda(f.reservado)}</td><td><ImporteInput aria-label={`Importe ${f.numero}`} disabled={!(f.idCompra in seleccion)} value={seleccion[f.idCompra]} onChange={n=>cambiarSeleccion(v=>({...v,[f.idCompra]:n}))}/></td></tr>)}
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
     {propuesta.lineas.map(l=><tr key={l.codRegimen} className="border-t"><td>{l.concepto}</td><td className="text-right">{formatMoneda(l.basePago)}</td><td className="text-right">{formatMoneda(l.pagosAnteriores)}</td><td className="text-right">{formatMoneda(l.noSujeto)}</td><td className="text-right">{l.alicuota?`${String(l.alicuota).replace('.',',')}%`:'Escala'}</td><td className="text-right">{formatMoneda(l.retencionesAnteriores)}</td><td className={`text-right font-semibold ${l.diferida?"text-amber-800":""}`}>{formatMoneda(l.retencion)}{l.diferida&&<span className="block text-xs font-normal">se descuenta en la cuota 2</span>}</td></tr>)}
    </tbody></table>}
    {propuesta?.avisos.map(a=><p key={a} className="text-sm text-slate-600">{a}</p>)}
    {propuesta&&<p className="text-sm text-slate-600">Es una propuesta: confirmala antes de emitir. El certificado lo emite el estudio contable.</p>}
   </section>
   <h3 className="font-semibold">Medios de pago previstos</h3>
   {medios.map((m,i)=><div key={i} className="flex flex-wrap gap-2">
    <select aria-label={`Medio ${i+1}`} className={campo} value={m.medio} onChange={e=>editarMedios(v=>v.map((x,j)=>j===i?{...x,medio:e.target.value as MedioOP['medio']}:x))}>{['Transferencia','Efectivo','Cheque'].map(x=><option key={x}>{x}</option>)}</select>
    <input required maxLength={150} aria-label={`Cuenta ${i+1}`} placeholder="Banco, caja o cheque previsto" className={`${campo} flex-1`} value={m.cuenta} onChange={e=>editarMedios(v=>v.map((x,j)=>j===i?{...x,cuenta:e.target.value}:x))}/>
    <ImporteInput required aria-label={`Importe del medio ${i+1}`} value={m.importe} onChange={n=>editarMedios(v=>v.map((x,j)=>j===i?{...x,importe:n}:x))}/>
    <input type="date" aria-label={`Fecha del medio ${i+1}`} title="Fecha de pago o vencimiento del cheque" className={campo} value={m.fecha??""} onChange={e=>editarMedios(v=>v.map((x,j)=>j===i?{...x,fecha:e.target.value||null}:x))}/>
    {medios.length>1&&<button type="button" onClick={()=>editarMedios(v=>v.filter((_,j)=>i!==j))}>Quitar</button>}</div>)}
   <button type="button" className={campo} onClick={()=>editarMedios(v=>[...v,{medio:'Transferencia',cuenta:'',importe:0}])}>Agregar medio</button>
   <p className="font-semibold">Facturas: {formatMoneda(total)} · Retención: {formatMoneda(retencion)} · Neto a pagar: {formatMoneda(total-retencion)} · Falta distribuir: {formatMoneda(diferencia)}{Math.abs(diferencia)>0.005&&medios.length>0&&<button type="button" className="ml-2 text-sm font-normal text-finance underline" onClick={()=>editarMedios(m=>m.map((x,i)=>i===m.length-1?{...x,importe:Math.round((x.importe+diferencia)*100)/100}:x))}>Completar con el último medio</button>}</p>
   <label className="block">Observaciones<textarea aria-label="Observaciones" className={`${campo} block w-full`} maxLength={1000} value={nota} onChange={e=>setNota(e.target.value)}/></label>
   {guardar.isError&&<p role="alert" className="text-red-700">{guardar.error.message}</p>}
   <div className="flex gap-3"><button className={boton} disabled={guardar.isPending||!contacto||total<=0||!propuesta||diferencia!==0}>Guardar borrador</button><button type="button" className={campo} onClick={cerrar}>Cancelar</button></div>
  </form>
 </section>;
}
