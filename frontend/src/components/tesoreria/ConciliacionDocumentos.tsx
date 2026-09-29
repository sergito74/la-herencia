"use client";

import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError } from "@/services/apiClient";
import {
  buscarDocumentos, fetchCandidatosDocumentos, fetchPreviewDocumentos,
  postConciliacionLote, postSinDocumento, quitarEstadoConciliacion, quitarConciliacion,
  type ReferenciaDocumento, type EstadoConciliacionResponse,
} from "@/services/conciliacionTesoreriaApi";
import type { Medio } from "@/services/tesoreriaApi";
import { formatMoneda, formatFecha } from "@/lib/format";
import { useToast } from "@/components/ui/Toast";
import { SoloLectura } from "@/components/auth/SoloLectura";

const clave = (d: ReferenciaDocumento) => `${d.origen}:${d.idOrigen}`;
export function ConciliacionDocumentos({medio,idMovimiento,estado,onSaved}: {
  medio: Medio; idMovimiento: number; estado: EstadoConciliacionResponse; onSaved: () => void;
}) {
  const cache = useQueryClient();
  const {showToast} = useToast();
  const [texto,setTexto] = useState("");
  const [busqueda,setBusqueda] = useState("");
  const [seleccion,setSeleccion] = useState<ReferenciaDocumento[]>([]);
  const [aceptar,setAceptar] = useState(false);
  const [sinDocumento,setSinDocumento] = useState(false);
  const [motivo,setMotivo] = useState("Impuesto");
  const [detalle,setDetalle] = useState("");
  const [guardando,setGuardando] = useState(false);
  useEffect(() => { setAceptar(false); },[seleccion]);
  const pendiente = estado.estado === "sin_conciliar" || estado.estado === "parcialmente_conciliado";
  useEffect(() => { const t = setTimeout(() => setBusqueda(texto.trim()),300); return () => clearTimeout(t); },[texto]);
  const candidatos = useQuery({queryKey:["conciliacion-documentos-candidatos",medio,idMovimiento],
    queryFn:() => fetchCandidatosDocumentos(medio,idMovimiento),enabled:pendiente});
  const buscar = useQuery({queryKey:["conciliacion-documentos-buscar",busqueda],
    queryFn:() => buscarDocumentos(busqueda),enabled:pendiente && busqueda.length>=2});
  const preview = useQuery({queryKey:["conciliacion-documentos-preview",medio,idMovimiento,seleccion],
    queryFn:() => fetchPreviewDocumentos(medio,idMovimiento,seleccion),enabled:pendiente && seleccion.length>0 && !sinDocumento});
  const docs = busqueda.length>=2 ? buscar.data : candidatos.data?.documentos;
  const error = busqueda.length>=2 ? buscar.error : candidatos.error;
  const cargando = busqueda.length>=2 ? buscar.isFetching : candidatos.isFetching;
  const motivos = sinDocumento ? ["Impuesto","Interes","CompraNoCargada","Otro"] : ["Impuesto","Redondeo","AjusteTipoCambioSinNota","Otro"];
  function refrescar() {
    ["conciliacion-documentos-candidatos","conciliacion-documentos-buscar","conciliacion-documentos-preview",
     "tarjetas-conciliacion","tarjetas-resumenes","conciliacion-candidatos","traspaso-interno-estado"].forEach(key => cache.invalidateQueries({queryKey:[key]}));
    // Los nombres de consultas históricas de Tarjetas varían por pantalla.
    cache.invalidateQueries({predicate:q => q.queryKey.some(k => typeof k === "string" && (k.includes("tarjeta") || k.includes("conciliacion")))});
    onSaved();
  }
  async function guardar(quitar=false) {
    setGuardando(true);
    try {
      const razon = {motivo,detalle:detalle.trim() || null};
      if (quitar) await quitarEstadoConciliacion(medio,idMovimiento);
      else if (sinDocumento) await postSinDocumento(medio,idMovimiento,razon);
      else await postConciliacionLote(medio,idMovimiento,seleccion,aceptar ? razon : null);
      setSeleccion([]); setAceptar(false); setSinDocumento(false);
      refrescar(); showToast(quitar ? "Estado quitado; se conservaron las imputaciones." : "Conciliación guardada.","success");
    } catch (e) {
      showToast(e instanceof ApiError ? e.message : "No se pudo guardar la conciliación.","danger");
      refrescar();
    } finally { setGuardando(false); }
  }
  async function quitarLinea(idConciliacion: number) {
    setGuardando(true);
    try {
      await quitarConciliacion(medio,idMovimiento,idConciliacion);
      refrescar(); showToast("Conciliación quitada.","success");
    } catch (e) {
      showToast(e instanceof ApiError ? e.message : "No se pudo quitar la conciliación.","danger");
    } finally { setGuardando(false); }
  }
  const listaConciliaciones = estado.conciliaciones.length > 0 && (
    <div className="space-y-1 rounded border border-border p-2">
      <p className="font-medium">Cargado hasta ahora:</p>
      {estado.conciliaciones.map(c => (
        <div key={c.idConciliacion} className="flex items-center justify-between gap-2">
          <span>{c.contacto ?? c.idContacto} · {formatMoneda(c.importe)}
            {c.tipoOrigenDocumento && ` · ${c.tipoOrigenDocumento} #${c.idOrigenDocumento}`}
          </span>
          <SoloLectura>
            <button type="button" disabled={guardando} className="text-finance underline disabled:opacity-50" onClick={() => quitarLinea(c.idConciliacion)}>
              Quitar
            </button>
          </SoloLectura>
        </div>
      ))}
    </div>
  );
  if (estado.auditoria) return <div className="space-y-2 text-xs">
    {listaConciliaciones}
    <p>{estado.auditoria.estado === "SinDocumento" ? "Sin documento" : "Diferencia aceptada"}: {estado.auditoria.motivo} {estado.auditoria.detalle}</p>
    {estado.auditoria.importeDiferencia != null && <p>Diferencia: {formatMoneda(estado.auditoria.importeDiferencia)}</p>}
    <p>{estado.auditoria.usuario} · {formatFecha(estado.auditoria.fecha)}</p>
    <SoloLectura><button type="button" disabled={guardando} className="text-finance underline" onClick={() => guardar(true)}>Quitar estado (conservar pagos)</button></SoloLectura>
  </div>;
  if (!pendiente) return <div className="space-y-3 text-xs">
    {listaConciliaciones}
    <p>Saldo del movimiento: <strong>{formatMoneda(estado.saldoPendiente)}</strong></p>
  </div>;
  return <div className="space-y-3 text-xs">
    {listaConciliaciones}
    <p>Saldo del movimiento: <strong>{formatMoneda(estado.saldoPendiente)}</strong></p>
    <label className="block">Buscar proveedor, contraparte o número
      <input className="mt-1 w-full rounded border border-border p-2" maxLength={100} value={texto} onChange={e=>setTexto(e.target.value)} placeholder="Escribí al menos 2 caracteres" />
    </label>
    {cargando && <p role="status">Buscando documentos…</p>}
    {error && <p role="alert">{error instanceof Error ? error.message : "No se pudieron buscar documentos."}</p>}
    {!cargando && !error && docs?.length===0 && <p>No hay coincidencias. Probá otro proveedor o número, o usá la carga manual.</p>}
    {candidatos.data?.sugerencias.map((s,i)=><button key={i} type="button" className="mr-2 rounded border border-border p-2" onClick={()=>{setSeleccion(s.documentos);setSinDocumento(false);}}>
      Usar coincidencia {i+1} ({s.documentos.length} documentos)
    </button>)}
    <div className="max-h-56 overflow-y-auto space-y-1">
      {docs?.map(d=><label key={clave(d)} className="flex items-start gap-2 rounded border border-border p-2">
        <input type="checkbox" checked={seleccion.some(s=>clave(s)===clave(d))} disabled={guardando || sinDocumento}
          onChange={e=>setSeleccion(prev=>e.target.checked ? [...prev,{origen:d.origen,idOrigen:d.idOrigen}].slice(0,20) : prev.filter(s=>clave(s)!==clave(d)))} />
        <span><strong>{d.contraparte || "Sin contraparte"}</strong> · {d.origen} #{d.idOrigen}<br/>
          {d.tipoDocumento} {d.numeroDocumento} · {formatFecha(d.fecha)}<br/>
          Original: {d.importeOriginal.toLocaleString("es-AR",{minimumFractionDigits:2})} {d.moneda || "Pesos"} · Saldo: {formatMoneda(d.saldoPendiente)}<br/>
          {d.vinculosPrevios>0 && `${d.vinculosPrevios} imputaciones previas (Tesorería y Tarjetas)`}
        </span>
      </label>)}
    </div>
    {seleccion.length>0 && <div><p>Seleccionados ({seleccion.length}/20):</p>{seleccion.map(d=><button type="button" key={clave(d)} className="mr-2 underline" onClick={()=>setSeleccion(s=>s.filter(x=>clave(x)!==clave(d)))}>{clave(d)} ×</button>)}</div>}
    {preview.isFetching && seleccion.length>0 && <p>Calculando reparto…</p>}
    {preview.error && <p role="alert">{preview.error instanceof Error ? preview.error.message : "No se pudo calcular el reparto."}</p>}
    {!sinDocumento && seleccion.length>0 && preview.data && <div className="rounded border border-border p-2 space-y-1">
      <p>{preview.data.estado === "exacta" ? "Cierra exacto" : preview.data.pagoParcial ? "Pago parcial de los documentos: reparto proporcional" : "Queda saldo pendiente del movimiento"}</p>
      {preview.data.imputados.map(i=><p key={clave(i)}>{clave(i)}: {formatMoneda(i.importeImputado)}</p>)}
      <p>Diferencia: {formatMoneda(preview.data.diferencia)}</p>
      {preview.data.tcImplicito!=null && <p>Tipo de cambio implícito: {preview.data.tcImplicito.toFixed(2)}</p>}
      {preview.data.estado!=="exacta" && <label className="flex gap-2"><input type="checkbox" checked={aceptar} onChange={e=>{setAceptar(e.target.checked);setMotivo("Impuesto");}}/>Aceptar diferencia y cerrar el movimiento</label>}
      {aceptar && <p>Se conserva el saldo documental no pagado. Esta decisión no modifica la factura.</p>}
    </div>}
    {estado.conciliaciones.length===0 && <label className="flex gap-2"><input type="checkbox" checked={sinDocumento} onChange={e=>{setSinDocumento(e.target.checked);setAceptar(false);setMotivo("Impuesto");}}/>Este movimiento no tiene documento</label>}
    {(aceptar || sinDocumento) && <div className="space-y-2">
      <label className="block">Motivo <select className="rounded border border-border p-1" value={motivo} onChange={e=>setMotivo(e.target.value)}>{motivos.map(m=><option key={m}>{m}</option>)}</select></label>
      <label className="block">Detalle {motivo==="Otro" && "(obligatorio)"}<textarea className="block w-full rounded border border-border p-2" value={detalle} maxLength={255} onChange={e=>setDetalle(e.target.value)}/></label>
    </div>}
    <button type="button" className="rounded bg-finance px-3 py-2 text-white disabled:opacity-50"
      disabled={guardando || !pendiente || (!sinDocumento && (!seleccion.length || !preview.data || !!preview.error || preview.isFetching)) || ((aceptar || sinDocumento) && motivo==="Otro" && !detalle.trim())}
      onClick={()=>guardar()}>{guardando ? "Guardando…" : sinDocumento ? "Confirmar sin documento" : "Confirmar conciliación"}</button>
  </div>;
}
