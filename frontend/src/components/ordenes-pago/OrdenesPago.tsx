'use client';
import { PageHeader } from '@/components/ui/PageHeader';
import { useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { useQuery,useMutation,useQueryClient } from '@tanstack/react-query';
import { SoloLectura } from '@/components/auth/SoloLectura';
import { ContactoSelect } from '@/components/ui/ContactoSelect';
import { formatFecha,formatMoneda } from '@/lib/format';
import { listarOP,obtenerOP,recibosOP,estadoOP,pdfOP,mailEstudioOP,conciliarEmitidas,type OrdenOP,type ReciboOP } from '@/services/ordenesPagoApi';
import { FormularioOrdenPago,campo,boton } from './FormularioOrdenPago';
import { VincularReciboModal } from './VincularReciboModal';
import { RetencionesConfig } from './RetencionesConfig';
import { FacturasAPagar } from './FacturasAPagar';

export function OrdenesPago() {
 const params=useSearchParams();
 const qc=useQueryClient();
 const [tab,setTab]=useState(params.has('recibo')?'recibos':params.get('tab')??'pendientes');
 const [inicial,setInicial]=useState<{idContacto:number;proveedor:string|null;facturas:Record<number,number>}|undefined>(undefined);
 const [contacto,setContacto]=useState<number|null>(null);const [nombre,setNombre]=useState<string|null>(null);
 const [estado,setEstado]=useState('');const [revisados,setRevisados]=useState(false);const [page,setPage]=useState(1);
 const [form,setForm]=useState<OrdenOP|true|null>(null);const [recibo,setRecibo]=useState<ReciboOP|null>(null);const [id,setId]=useState<number|null>(null);
 const [mensaje,setMensaje]=useState('');
 const [elegidas,setElegidas]=useState<number[]>([]);
 const lleva=(o:OrdenOP)=>o.retencionGanancias>0&&o.estado!=='Anulada';
 const mail=useMutation({mutationFn:mailEstudioOP,onSuccess:({avisos,outlook},ids)=>{const n=ids.length===1?'1 orden':`${ids.length} órdenes`;setMensaje((outlook?`Mail a Karen abierto en Outlook con ${n} y las facturas adjuntas: revisalo y envialo (también quedó en Borradores).`:`Outlook no respondió: se descargó el mail con ${n}; abrilo con doble clic, revisalo y envialo.`)+(avisos.length?` Atención: ${avisos.join('; ')}.`:''));}});
 const ordenes=useQuery({queryKey:['ordenes-pago',contacto,estado,page],queryFn:()=>listarOP({idContacto:contacto??undefined,estado:estado||undefined,page})});
 const recibos=useQuery({queryKey:['recibos-pago',contacto,revisados,page],queryFn:()=>recibosOP({idContacto:contacto??undefined,revisados,page})});
 const detalle=useQuery({queryKey:['op',id],queryFn:()=>obtenerOP(id!),enabled:!!id});
 function refrescar(){for(const key of ['facturas-a-pagar','ordenes-pago','recibos-pago','op','op-facturas','op-facturas-recibo','op-emitidas','op-movimientos','documentos-nuevos'])qc.invalidateQueries({queryKey:[key]});}
 const cambio=useMutation({mutationFn:({id,accion}:{id:number;accion:'emitir'|'anular'})=>estadoOP(id,accion),onSuccess:o=>{refrescar();setMensaje(`Orden ${String(o.idOrdenPago).padStart(6,'0')}: ${o.estado.toLowerCase()}.`);}});
 const conciliar=useMutation({mutationFn:conciliarEmitidas,onSuccess:r=>{refrescar();setMensaje(r.pagadas.length?`${r.pagadas.length} órdenes pasaron a pagadas con su débito real.`:'No hay débitos nuevos que coincidan con órdenes emitidas.'+(r.ambiguas.length?` ${r.ambiguas.length} con más de un débito posible: vinculalas desde su recibo.`:''));}});
 const total=tab==='ordenes'?ordenes.data?.total:recibos.data?.total;
 return <main className="mx-auto max-w-[1600px] space-y-3 px-6 py-3">
  <PageHeader titulo="Pagos" ayuda="Facturas a pagar por vencimiento, órdenes de pago a proveedores y vinculación de sus recibos." />
  <div className="flex gap-3"><button className={tab==='pendientes'?boton:campo} onClick={()=>setTab('pendientes')}>Facturas a pagar</button><button className={tab==='ordenes'?boton:campo} onClick={()=>{setTab('ordenes');setPage(1);}}>Órdenes de pago</button><button className={tab==='recibos'?boton:campo} onClick={()=>{setTab('recibos');setPage(1);}}>Recibos de proveedores</button><button className={tab==='retenciones'?boton:campo} onClick={()=>setTab('retenciones')}>Retenciones</button></div>
  {tab==='retenciones'&&<RetencionesConfig/>}
  {tab==='pendientes'&&!form&&<FacturasAPagar idContacto={contacto} crearOrden={s=>{setInicial(s);setForm(true);setId(null);setRecibo(null);window.scrollTo({top:0,behavior:'smooth'});}}/>}
  {mensaje&&<p role="status" className="rounded bg-emerald-50 p-3">{mensaje}</p>}
  {tab!=='retenciones'&&tab!=='pendientes'&&<>
  <div className="rounded border bg-white p-4 flex flex-wrap items-end gap-4"><div className="min-w-72"><ContactoSelect value={contacto} razonSocial={nombre} label="Filtrar por proveedor" onChange={(id,n)=>{setContacto(id);setNombre(n);setPage(1);}}/></div>
   {tab==='ordenes'?<><select aria-label="Estado de las órdenes" className={campo} value={estado} onChange={e=>{setEstado(e.target.value);setPage(1);}}><option value="">Todos los estados</option>{['Borrador','Emitida','Pagada','Anulada'].map(x=><option key={x}>{x}</option>)}</select><button className={campo} disabled={!elegidas.length||mail.isPending} onClick={()=>mail.mutate(elegidas)}>{mail.isPending?'Preparando…':`Mail al estudio con las tildadas (${elegidas.length})`}</button><SoloLectura><button className={boton} onClick={()=>{setInicial(undefined);setForm(true);setRecibo(null);setId(null);}}>Nueva orden</button><button className={campo} disabled={conciliar.isPending} onClick={()=>conciliar.mutate()}>{conciliar.isPending?'Buscando…':'Buscar pagos realizados'}</button></SoloLectura></>:<label><input type="checkbox" checked={revisados} onChange={e=>{setRevisados(e.target.checked);setPage(1);}}/> Incluir recibos revisados</label>}
  </div>
  <p className="text-sm text-slate-600">Importes en pesos; las compras en dólares se toman al tipo de cambio de la factura.</p></>}
  {form&&<SoloLectura><FormularioOrdenPago key={form===true?`nuevo-${inicial?.idContacto??''}`:form.idOrdenPago} orden={form===true?undefined:form} inicial={form===true?inicial:undefined} cerrar={()=>{setForm(null);setInicial(undefined);}} guardado={()=>{setForm(null);setInicial(undefined);setTab('ordenes');refrescar();setMensaje('Borrador guardado. Podés revisarlo y emitirlo desde el detalle.');}}/></SoloLectura>}
  {recibo&&<SoloLectura><VincularReciboModal key={recibo.idDocumentoNuevo} recibo={recibo} cerrar={()=>setRecibo(null)} guardado={()=>{setRecibo(null);refrescar();setMensaje('Recibo vinculado y aplicaciones confirmadas.');}}/></SoloLectura>}
  {detalle.data&&<section className="rounded border bg-white p-5 space-y-3"><div className="flex justify-between"><h2 className="font-semibold">OP {String(detalle.data.idOrdenPago).padStart(6,'0')} · {detalle.data.proveedor} · {detalle.data.estado}</h2><button onClick={()=>setId(null)}>Cerrar detalle</button></div>
   <p>Pago previsto {formatFecha(detalle.data.fechaPago)} · {formatMoneda(detalle.data.importeTotal)}</p>
   <ul>{detalle.data.facturas.map(f=><li key={f.idCompra}><a className="underline" href={`/compras/${f.idCompra}/editar`}>{f.numero||'Factura sin número'}</a> · {formatMoneda(f.importe)}</li>)}</ul>
   {detalle.data.retencionGanancias>0&&<p>Retención de Ganancias: {formatMoneda(detalle.data.retencionGanancias)} ({detalle.data.retenciones?.map(r=>r.concepto).join(' · ')}) · Neto a pagar {formatMoneda(detalle.data.importeTotal-detalle.data.retencionGanancias)}</p>}
   <table className="text-sm"><thead><tr className="text-left text-slate-600"><th className="pr-6 font-normal">Fecha de pago / vencimiento</th><th className="pr-6 font-normal">Medio</th><th className="text-right font-normal">Importe</th></tr></thead>
    <tbody>{[...detalle.data.medios].sort((a,b)=>(a.fecha??detalle.data!.fechaPago??'').localeCompare(b.fecha??detalle.data!.fechaPago??'')).map((m,i)=><tr key={i}><td className="pr-6">{formatFecha(m.fecha??detalle.data!.fechaPago)}</td><td className="pr-6">{m.medio}: {m.cuenta}</td><td className="text-right">{formatMoneda(m.importe)}</td></tr>)}
    <tr className="border-t font-medium"><td className="pr-6">Total</td><td/><td className="text-right">{formatMoneda(detalle.data.medios.reduce((s,m)=>s+m.importe,0))}</td></tr></tbody></table>
   {lleva(detalle.data)&&<p><button className="text-emerald-700 underline" disabled={mail.isPending} onClick={()=>mail.mutate([detalle.data!.idOrdenPago])}>Preparar mail al estudio para el certificado de retención</button> <span className="text-sm text-slate-600">(se abre en Outlook listo para revisar y enviar, con las facturas adjuntas; para varias órdenes en un mismo mail, tildalas en el listado)</span></p>}<p>{detalle.data.observaciones}</p>
   <SoloLectura><div className="flex gap-3">{detalle.data.estado==='Borrador'&&<><button className={campo} onClick={()=>{setForm(detalle.data!);setId(null);}}>Editar</button><button className={boton} disabled={cambio.isPending} onClick={()=>cambio.mutate({id:detalle.data!.idOrdenPago,accion:'emitir'})}>Emitir orden</button></>}{['Borrador','Emitida'].includes(detalle.data.estado)&&<button className={campo} disabled={cambio.isPending} onClick={()=>cambio.mutate({id:detalle.data!.idOrdenPago,accion:'anular'})}>Anular orden</button>}</div></SoloLectura>
  </section>}
  {[ordenes.error,recibos.error,detalle.error,cambio.error,conciliar.error,mail.error].filter(Boolean).map((e,i)=><p key={i} role="alert" className="text-red-700">{e?.message}</p>)}
  {tab!=='retenciones'&&tab!=='pendientes'&&<>
  {(tab==='ordenes'?ordenes.isFetching:recibos.isFetching)&&<p>Cargando…</p>}
  <section className="overflow-auto rounded border bg-white"><table className="w-full text-sm"><thead className="bg-slate-50"><tr>{tab==='ordenes'&&<th className="p-2" title="Para el mail al estudio">Mail</th>}<th className="p-3 text-left">{tab==='ordenes'?'Orden':'Recibo'}</th><th>Proveedor</th><th>Fecha</th><th>Importe ARS</th><th>Estado</th><th>Acciones</th></tr></thead><tbody>
   {tab==='ordenes'?ordenes.data?.items.map(o=><tr className="border-t" key={o.idOrdenPago}><td className="p-2 text-center">{lleva(o)&&<input type="checkbox" aria-label={`Incluir OP ${o.idOrdenPago} en el mail al estudio`} checked={elegidas.includes(o.idOrdenPago)} onChange={e=>setElegidas(x=>e.target.checked?[...x,o.idOrdenPago]:x.filter(i=>i!==o.idOrdenPago))}/>}</td><td className="p-3">OP {String(o.idOrdenPago).padStart(6,'0')}</td><td>{o.proveedor}</td><td>{formatFecha(o.fecha)}</td><td className="text-right">{formatMoneda(o.importeTotal)}</td><td className="text-center">{o.estado}</td><td className="p-2"><button className={campo} onClick={()=>{setId(o.idOrdenPago);setForm(null);}}>Ver detalle</button></td></tr>):recibos.data?.items.map(r=><tr className={`border-t ${String(r.idDocumentoNuevo)===params.get('recibo')?'bg-amber-50':''}`} key={r.idDocumentoNuevo}><td className="p-3">{r.numero||'Por identificar'}</td><td>{r.proveedor||'Proveedor por confirmar'}</td><td>{formatFecha(r.fecha)}</td><td className="text-right">{r.total===null?'Por confirmar':formatMoneda(r.total)}</td><td className="text-center">{r.idRecibo?'Vinculado':r.revisado?'Revisado':'Pendiente'}</td><td className="p-2"><a className="underline mr-3" href={pdfOP(r.idDocumentoNuevo)} target="_blank" rel="noreferrer">PDF</a>{r.idOrdenPago&&<button className={campo} onClick={()=>setId(r.idOrdenPago)}>Ver orden</button>}{!r.revisado&&<SoloLectura><button className={campo} onClick={()=>{setRecibo(r);setForm(null);}}>Vincular</button></SoloLectura>}</td></tr>)}
  </tbody></table>{total===0&&<p className="p-6 text-slate-600">{tab==='ordenes'?'No hay órdenes de pago con estos filtros.':'No hay recibos pendientes con estos filtros.'}</p>}</section>
  <div className="flex items-center gap-4"><button className={campo} disabled={page<=1} onClick={()=>setPage(p=>p-1)}>Anterior</button><span>{total??0} resultados · Página {page}</span><button className={campo} disabled={page*50>=(total??0)} onClick={()=>setPage(p=>p+1)}>Siguiente</button></div></>}
 </main>;
}
