"use client";
import Link from "next/link";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/services/apiClient";
import { SoloLectura } from "@/components/auth/SoloLectura";
import { formatMoneda } from "@/lib/format";

type Calculo = { netoRecibo:number;adicional:number;feriados:number;redondeo:number;totalAdicional:number;registrado:number;totalACobrar:number;periodo:string;adicionalSeparado:number|null;registradoSeparado:number;puedeGuardar:boolean };
export function AdicionalSierra({ idSalario }: { idSalario:number }) {
  const [abierto,setAbierto]=useState(false);const [error,setError]=useState("");const [ocupado,setOcupado]=useState(false);const qc=useQueryClient();
  const ruta=`/api/remuneraciones/${idSalario}/adicional`;
  const {data:d,isLoading,isError,refetch}=useQuery({queryKey:["adicional-sierra",idSalario],queryFn:()=>apiGet<Calculo>(ruta),enabled:abierto});
  const total=d?.totalAdicional??0;
  async function guardar(){setOcupado(true);setError("");try{await apiPost(ruta,{});await refetch();await qc.invalidateQueries({queryKey:["remuneraciones"]});await qc.invalidateQueries({queryKey:["trabajos-eventuales"]});}catch(e){setError(e instanceof Error?e.message:"No se pudo guardar el adicional");}finally{setOcupado(false);}}
  return <div className="min-w-36"><button className="text-finance underline" onClick={()=>setAbierto(!abierto)}>{abierto?"Cerrar adicional":"Calcular adicional"}</button>
    {abierto&&<div className="mt-2 min-w-72 space-y-2 rounded border border-border bg-surface p-3 text-xs whitespace-normal">
      {isLoading?<p>Cargando…</p>:isError||!d?<p>No se pudo consultar el adicional. <button className="underline" onClick={()=>refetch()}>Reintentar</button></p>:<>
        <strong>Fuera de recibo · {d.periodo}</strong>
        <p>Neto del recibo: {formatMoneda(d.netoRecibo)}</p><p>Adicional 30%: {formatMoneda(d.adicional)}</p><p>Feriados 8,5%: {formatMoneda(d.feriados)}</p>
        <p className="text-ink-secondary">Cada parte se redondea al múltiplo de $5 más cercano.</p>
        <p>Redondeo a la centena siguiente: {formatMoneda(d.redondeo)}</p>
        <p><strong>Total adicional: {formatMoneda(total)}</strong></p><p>Total a cobrar: {formatMoneda(d.netoRecibo+total)}</p>
        <p className="text-ink-secondary">Adicional ya registrado: {formatMoneda(d.registrado+d.registradoSeparado)}</p>
        {d.adicionalSeparado && <p>Registrado por separado. <Link className="text-finance underline" href={`/personal/remuneraciones?empleado=Marcelo%20Sierra&highlight=${d.adicionalSeparado}`}>Ver adicional registrado</Link></p>}
        <SoloLectura>{d.puedeGuardar && <button disabled={ocupado||total<0} className="rounded bg-finance px-3 py-1.5 text-white disabled:opacity-50" onClick={guardar}>{ocupado?"Guardando…":"Guardar adicional"}</button>}</SoloLectura>
        <p className="text-ink-secondary">Se guarda en esta liquidación, separado del recibo. El pago se registra desde Tesorería.</p>
      </>}{error&&<p role="alert" className="text-red-700">{error}</p>}
    </div>}
  </div>;
}
