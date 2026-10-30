'use client';
import { useEffect,useState } from 'react';
import { useMutation,useQuery } from '@tanstack/react-query';
import { ContactoSelect } from '@/components/ui/ContactoSelect';
import { formatFecha,formatMoneda } from '@/lib/format';
import { facturasOP,listarOP,movimientosOP,obtenerOP,pdfOP,vincularOP,type ReciboOP,type AplicacionOP } from '@/services/ordenesPagoApi';
import { campo,boton,hoy,ImporteInput } from './FormularioOrdenPago';

export function VincularReciboModal({recibo,cerrar,guardado}:{recibo:ReciboOP;cerrar:()=>void;guardado:()=>void}) {
 const [contacto,setContacto]=useState(recibo.idContacto);
 const [nombre,setNombre]=useState(recibo.proveedor);
 const [numero,setNumero]=useState(recibo.numero??'');
 const [fecha,setFecha]=useState(recibo.fecha??hoy());
 const [total,setTotal]=useState(recibo.total??0);
 const [op,setOP]=useState<number|null>(null);
 const [items,setItems]=useState<AplicacionOP[]>([]);
 const [retencion,setRetencion]=useState(0);const [certificado,setCertificado]=useState('');const [anticipo,setAnticipo]=useState(0);
 const [mov,setMov]=useState(''); const [factura,setFactura]=useState('');const [importe,setImporte]=useState(0);
 const fs=useQuery({queryKey:['op-facturas-recibo',contacto,op],queryFn:()=>facturasOP(contacto!,op??undefined,true),enabled:!!contacto});
 const ms=useQuery({queryKey:['op-movimientos',contacto],queryFn:()=>movimientosOP(contacto!),enabled:!!contacto});
 const os=useQuery({queryKey:['op-emitidas',contacto],enabled:!!contacto,queryFn:async()=>{
  const [e,p]=await Promise.all([listarOP({idContacto:contacto!,estado:'Emitida'}),listarOP({idContacto:contacto!,estado:'Pagada'})]);
  return {items:[...e.items,...p.items],total:e.total+p.total};}});
 const detalle=useQuery({queryKey:['op',op],queryFn:()=>obtenerOP(op!),enabled:!!op});
 const cent=(n:number)=>Math.round(n*100);
 // T025: preselecciona la única OP cuyo total o neto coincide con el recibo.
 const [auto,setAuto]=useState(false);
 useEffect(()=>{if(auto||op||!os.data||!total)return;
  const c=os.data.items.filter(o=>cent(o.importeTotal)===cent(total)||cent(o.importeTotal-o.retencionGanancias)===cent(total));
  setAuto(true);if(c.length===1){setOP(c[0].idOrdenPago);setRetencion(c[0].retencionGanancias);}},[os.data,total,op,auto]);
 // y precarga el reparto neto con el único pago real por ese neto.
 useEffect(()=>{if(!detalle.data?.repartoNeto||!ms.data||items.length)return;
  const neto=detalle.data.repartoNeto.reduce((a,b)=>a+b.importe,0);
  const m=ms.data.filter(x=>cent(x.importe)===cent(neto));
  if(m.length===1)setItems(detalle.data.repartoNeto.map(p=>({origenMovimiento:m[0].origenMovimiento,idMovimiento:m[0].idMovimiento,idCompra:p.idCompra,importe:p.importe})));
 },[detalle.data,ms.data,items.length]);
 const suma=items.reduce((a,b)=>a+b.importe,0);
 const pendiente=Math.round((total-suma-retencion-anticipo)*100)/100;
 const guardar=useMutation({mutationFn:()=>vincularOP(recibo.idDocumentoNuevo,{idContacto:contacto!,numero,fecha,total,moneda:'ARS',idOrdenPago:op,aplicaciones:items,retencion,certificadoRetencion:certificado||null,anticipo}),onSuccess:guardado});
 function agregar(){const [origen,id]=mov.split(':');if(!id||!factura||importe<=0)return;setItems(v=>[...v,{origenMovimiento:origen as AplicacionOP['origenMovimiento'],idMovimiento:Number(id),idCompra:Number(factura),importe}]);setImporte(0);}
 return <section className="rounded-xl border bg-white p-5 space-y-4" aria-label="Vincular recibo">
  <div className="flex justify-between"><h2 className="text-xl font-semibold">Vincular recibo</h2><button className={campo} onClick={cerrar}>Cerrar</button></div>
  <p className="text-sm text-slate-600">Revisá el original y confirmá qué pagos y facturas respalda. Los importes se comparan en pesos.</p>
  <div className="grid xl:grid-cols-2 gap-5"><div><a className="text-emerald-700 underline" href={pdfOP(recibo.idDocumentoNuevo)} target="_blank" rel="noreferrer">Abrir PDF original</a><iframe className="mt-2 w-full h-[650px] border" title="PDF del recibo" src={pdfOP(recibo.idDocumentoNuevo)}/></div>
   <form className="space-y-4" onSubmit={e=>{e.preventDefault();guardar.mutate();}}>
    <ContactoSelect value={contacto} razonSocial={nombre} label="Proveedor del recibo" onChange={(id,n)=>{setContacto(id);setNombre(n);setItems([]);setOP(null);setMov('');setFactura('');}}/>
    <div className="flex flex-wrap gap-2"><label>Número <input required maxLength={50} className={campo} value={numero} onChange={e=>setNumero(e.target.value)}/></label><label>Fecha <input required type="date" className={campo} value={fecha} onChange={e=>setFecha(e.target.value)}/></label><label>Total del recibo <ImporteInput required className={campo} value={total} onChange={setTotal}/></label></div>
    <label className="block">Orden de pago <select className={`${campo} w-full`} value={op??''} onChange={e=>{const id=Number(e.target.value)||null;setOP(id);setItems([]);setRetencion(os.data?.items.find(o=>o.idOrdenPago===id)?.retencionGanancias??0);}}><option value="">Sin orden previa</option>{os.data?.items.map(o=><option value={o.idOrdenPago} key={o.idOrdenPago}>OP {String(o.idOrdenPago).padStart(6,'0')} · {formatMoneda(o.importeTotal)}{o.estado==='Pagada'?' · Pagada':''}{cent(o.importeTotal)===cent(total)||cent(o.importeTotal-o.retencionGanancias)===cent(total)?' · Coincide con el recibo':''}</option>)}</select></label>
    {detalle.data&&<div className="rounded bg-emerald-50 p-3 text-sm">Facturas de la orden: {detalle.data.facturas.map(f=>`${f.numero}: ${formatMoneda(f.importe)}`).join(' · ')}</div>}
    <h3 className="font-semibold">Distribuir pagos reales entre facturas</h3>
    <select aria-label="Pago real" className={`${campo} w-full`} value={mov} onChange={e=>setMov(e.target.value)}><option value="">Elegir pago de Tesorería</option>{ms.data?.map(m=><option key={`${m.origenMovimiento}:${m.idMovimiento}`} value={`${m.origenMovimiento}:${m.idMovimiento}`}>{m.origenMovimiento==='bna'?'Banco Nación':m.origenMovimiento==='galicia'?'Galicia':'Efectivo'} · {formatFecha(m.fecha)} · {formatMoneda(m.importe)} · Disponible {formatMoneda(m.disponible)}</option>)}</select>
    <select aria-label="Factura a cancelar" className={`${campo} w-full`} value={factura} onChange={e=>setFactura(e.target.value)}><option value="">Elegir factura</option>{fs.data?.filter(f=>!detalle.data||detalle.data.facturas.some(x=>x.idCompra===f.idCompra)).map(f=><option value={f.idCompra} key={f.idCompra}>{f.numero||'Sin número'}{f.moneda==='Dolares'?' (US$)':''} · {formatFecha(f.fecha)} · Saldo {formatMoneda(f.saldo)}</option>)}</select>
    <div className="flex gap-2"><ImporteInput aria-label="Importe a aplicar" className={campo} value={importe} onChange={setImporte}/><button type="button" className={campo} disabled={!mov||!factura||importe<=0} onClick={agregar}>Agregar aplicación</button></div>
    {items.map((a,i)=><div key={i} className="flex gap-2 justify-between border-b text-sm py-2"><span>{a.origenMovimiento} → {fs.data?.find(f=>f.idCompra===a.idCompra)?.numero} · {formatMoneda(a.importe)}</span><button type="button" onClick={()=>setItems(v=>v.filter((_,j)=>j!==i))}>Quitar</button></div>)}
    <div className="flex flex-wrap gap-2">
     <label>Retención de Ganancias <ImporteInput className={campo} value={retencion} disabled={!!op} onChange={setRetencion}/></label>
     <label>Nro. de certificado <input className={campo} maxLength={30} placeholder={op?'Opcional, puede llegar después':'Requerido si hay retención'} value={certificado} onChange={e=>setCertificado(e.target.value)}/></label>
     <label>Anticipo sin factura <ImporteInput className={campo} value={anticipo} onChange={setAnticipo}/></label>
    </div>
    <p className="font-semibold">Pagos aplicados: {formatMoneda(suma)} · Retención: {formatMoneda(retencion)} · Anticipo: {formatMoneda(anticipo)} · Por distribuir: {formatMoneda(pendiente)}</p>
    <p className="text-sm text-slate-600">Si el pago ya estaba aplicado exactamente a esa factura, se adjunta el recibo sin duplicarlo. Con orden de pago, la retención es la de la orden: los pagos cubren el neto y la retención termina de cancelar la factura. El anticipo queda registrado y se imputa después en Cuentas corrientes.</p>
    {(fs.isFetching||ms.isFetching||os.isFetching)&&<p>Cargando opciones…</p>}
    {[fs.error,ms.error,os.error,detalle.error,guardar.error].filter(Boolean).map((e,i)=><p key={i} role="alert" className="text-red-700">{e?.message}</p>)}
    <button className={boton} disabled={guardar.isPending||!contacto||(!items.length&&!anticipo)||pendiente!==0}>Confirmar vinculación</button>
   </form></div>
 </section>;
}
