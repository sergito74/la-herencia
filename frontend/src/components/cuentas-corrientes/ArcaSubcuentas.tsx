"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchArca, guardarArca, historialArca, MovimientoArca, ParteArca, urlDocumentoArca } from "@/services/arcaApi";
import { formatFecha, formatMoneda } from "@/lib/format";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { SoloLectura } from "@/components/auth/SoloLectura";
import Link from "next/link";
import { ArcaFiscal } from './ArcaFiscal';

const monto = (v: string) => formatMoneda(Number(v));

function origenHref(m: MovimientoArca) {
  if (m.origen === 'Impuestos') return `/finanzas/impuestos?highlight=${m.idOrigen}`;
  const medio = ({'Galicia':'galicia', 'Banco Nacion':'bna', 'Pagos efectivo':'efectivo'} as Record<string,string>)[m.origen];
  return medio ? `/finanzas/tesoreria?medio=${medio}&highlight=${m.idOrigen}` : undefined;
}

export function ArcaSubcuentas({fechaDesde, fechaHasta}: {fechaDesde: string; fechaHasta: string}) {
  const [vista, setVista] = useState<'mayor' | 'fiscal'>('mayor');
  const [subcuenta, setSubcuenta] = useState("");
  const [page, setPage] = useState(1);
  const [editando, setEditando] = useState<MovimientoArca | null>(null);
  const [partes, setPartes] = useState<ParteArca[]>([]);
  const [motivo, setMotivo] = useState("");
  const qc = useQueryClient();
  const cuenta = useQuery({queryKey: ["arca", fechaDesde, fechaHasta, subcuenta, page],
    queryFn: () => fetchArca({fechaDesde: fechaDesde || undefined, fechaHasta: fechaHasta || undefined, subcuenta: subcuenta || undefined, page})});
  const historia = useQuery({queryKey: ["arca-historial", editando?.origen, editando?.idOrigen],
    queryFn: () => historialArca(editando!), enabled: !!editando});
  const guardar = useMutation({mutationFn: (automatico: boolean) => guardarArca(editando!, automatico ? [] : partes, motivo),
    onSuccess: async () => {
      await qc.invalidateQueries({queryKey: ["arca"]});
      await qc.invalidateQueries({queryKey: ["arca-historial"]});
      setEditando(null);
    }});
  const d = cuenta.data;
  function abrir(m: MovimientoArca) {
    guardar.reset(); setEditando(m); setPartes(m.partes.map(p => ({...p}))); setMotivo("");
  }
  function cambiar(i: number, campo: keyof ParteArca, valor: string) {
    setPartes(prev => prev.map((p, n) => n === i ? {...p, [campo]: valor} : p));
  }
  function elegir(clave: string) { setSubcuenta(clave); setPage(1); }
  const nombres = Object.fromEntries((d?.resumen ?? []).map(r => [r.clave, r.nombre]));
  return <section aria-label="Subcuentas de ARCA" className="space-y-4">
    <div className="flex gap-4" aria-label="Vista de ARCA">
      <button type="button" aria-pressed={vista === 'mayor'} onClick={() => setVista('mayor')} className="rounded border border-border px-3 py-2">Mayor financiero</button>
      <button type="button" aria-pressed={vista === 'fiscal'} onClick={() => setVista('fiscal')} className="rounded border border-border px-3 py-2">Cuenta fiscal SCT</button>
    </div>
    {vista === 'fiscal' ? <ArcaFiscal /> : <>
    <div>
      <h3 className="text-lg font-semibold">Subcuentas de ARCA</h3>
      <p className="text-sm text-ink-secondary">Saldos contables al {fechaHasta ? formatFecha(fechaHasta) : "último movimiento"}. Positivo: créditos menos débitos; pendiente de conciliación fiscal.</p>
      <p className="text-xs text-ink-secondary">Débitos: obligaciones y devoluciones cobradas. Créditos: pagos y compensaciones registradas.</p>
    </div>
    {cuenta.isLoading && <LoadingState />}
    {cuenta.isError && <ErrorState message={cuenta.error.message} />}
    {d && <>
      <button type="button" onClick={() => elegir("")} aria-pressed={!subcuenta}
        className={`rounded border p-3 text-left ${!subcuenta ? "border-finance bg-surface-sunken" : "border-border"}`}>
        <span className="block text-sm">Toda ARCA</span><strong>{monto(d.saldoTotal)}</strong>
      </button>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-3">
        {d.resumen.map(r => <button type="button" key={r.clave} onClick={() => elegir(r.clave)} aria-pressed={subcuenta === r.clave}
          className={`rounded border p-3 text-left ${subcuenta === r.clave ? "border-finance bg-surface-sunken" : "border-border bg-surface"}`}>
          <span className="block text-sm">{r.nombre}</span>
          <strong>{monto(r.saldo)}</strong><span className="ml-2 text-xs text-ink-secondary">{r.cantidad} movimientos</span>
          <span className="block text-xs text-ink-secondary">Débitos {monto(r.deuda)} · Créditos {monto(r.credito)}</span>
        </button>)}
      </div>
      <div className="flex flex-wrap gap-4 text-sm">
        <strong>{subcuenta ? nombres[subcuenta] : "Toda ARCA"}</strong>
        <span>Apertura anterior al período: {monto(d.apertura)}</span>
        <span>Saldo al corte: {monto(d.saldoSeleccion)}</span>
        <span>{d.total} movimientos del período</span>
      </div>
      <div className="overflow-x-auto rounded border border-border">
        <table className="w-full text-sm"><thead className="bg-surface-sunken"><tr>
          {['Fecha','Concepto / documento','Subcuenta','Débitos','Créditos','Saldo','Origen',''].map((h,i) => <th key={i} className="p-2 text-left">{h}</th>)}
        </tr></thead><tbody>{d.items.map(m => <tr key={`${m.origen}-${m.idOrigen}`} className="border-t border-border align-top">
          <td className="whitespace-nowrap p-2">{formatFecha(m.fecha)}</td>
          <td className="p-2"><span className="block">{m.detalle || m.documento || "Sin concepto identificado"}</span><span className="text-xs text-ink-secondary">{m.documento} · {m.numeroDocumento || "Sin número"}</span>
            {m.documentos?.map(doc => <a key={doc.idDocumento} className="block text-xs text-finance underline" href={urlDocumentoArca(doc.idDocumento)} target="_blank" rel="noreferrer" title={doc.esOriginal ? "PDF descargado de ARCA" : "Copia del formulario consultado en el portal"}>{doc.tipo}{doc.numero ? ` · ${doc.numero}` : ""} (PDF)</a>)}
          </td>
          <td className="p-2">{m.partes.map(p => <span className="block" key={p.subcuenta}>{nombres[p.subcuenta]}{m.partes.length > 1 ? ` · ${monto(String(Number(p.credito)-Number(p.deuda)))}` : ""}</span>)}<span className="text-xs text-ink-secondary">{m.revisarReparto ? "El original cambió: revisar reparto" : m.manual ? "Clasificación registrada" : "Por concepto del original"}</span></td>
          <td className="whitespace-nowrap p-2 text-right">{monto(m.deuda)}</td><td className="whitespace-nowrap p-2 text-right">{monto(m.credito)}</td><td className="whitespace-nowrap p-2 text-right">{monto(m.saldo)}</td>
          <td className="p-2">{origenHref(m) ? <Link className="text-finance underline" href={origenHref(m)!}>{m.origen} #{m.idOrigen}</Link> : `${m.origen} #${m.idOrigen}`}</td>
          <td className="p-2"><SoloLectura><button type="button" className="text-finance underline" onClick={() => abrir(m)}>Clasificar / repartir</button></SoloLectura></td>
        </tr>)}{d.items.length === 0 && <tr><td colSpan={8} className="p-6 text-center">Sin movimientos para este período y subcuenta.</td></tr>}</tbody></table>
      </div>
      <div className="flex items-center gap-4">
        <button type="button" disabled={page <= 1} onClick={() => setPage(page-1)} className="disabled:opacity-40">Anterior</button>
        <span>Página {page} de {Math.max(1, Math.ceil(d.total/d.pageSize))}</span>
        <button type="button" disabled={page*d.pageSize >= d.total} onClick={() => setPage(page+1)} className="disabled:opacity-40">Siguiente</button>
      </div>
    </>}
    </>}
    {editando && <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" role="dialog" aria-modal="true" aria-labelledby="arca-editar">
      <div className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded bg-surface p-6 shadow-xl">
        <h3 id="arca-editar" className="text-lg font-semibold">Clasificar / repartir movimiento</h3>
        <p className="my-3 text-sm">{editando.origen} #{editando.idOrigen} · {formatFecha(editando.fecha)} · {editando.detalle}</p>
        <p className="mb-3 text-sm">Importes originales: débitos {monto(editando.deudaOriginal)} · créditos {monto(editando.creditoOriginal)}. El reparto debe conservar ambos totales.</p>
        {partes.map((p,i) => <div key={i} className="mb-3 grid grid-cols-1 gap-2 sm:grid-cols-4">
          <label className="text-sm">Subcuenta<select aria-label={`Subcuenta ${i+1}`} value={p.subcuenta} onChange={e => cambiar(i,'subcuenta',e.target.value)} className="w-full rounded border border-border bg-surface p-2">{d?.resumen.map(r => <option key={r.clave} value={r.clave}>{r.nombre}</option>)}</select></label>
          <label className="text-sm">Débitos<input aria-label={`Débitos ${i+1}`} type="number" min="0" step="0.0001" value={p.deuda} onChange={e => cambiar(i,'deuda',e.target.value)} className="w-full rounded border border-border bg-surface p-2" /></label>
          <label className="text-sm">Créditos<input aria-label={`Créditos ${i+1}`} type="number" min="0" step="0.0001" value={p.credito} onChange={e => cambiar(i,'credito',e.target.value)} className="w-full rounded border border-border bg-surface p-2" /></label>
          <button type="button" disabled={partes.length === 1 || guardar.isPending} onClick={() => setPartes(prev => prev.filter((_,n) => n!==i))}>Quitar parte</button>
        </div>)}
        <button type="button" disabled={partes.length >= (d?.resumen.length ?? 0) || guardar.isPending} className="text-finance underline" onClick={() => setPartes([...partes,{subcuenta: d?.resumen.find(r => !partes.some(p => p.subcuenta===r.clave))?.clave ?? 'por-identificar', deuda:'0',credito:'0'}])}>+ Agregar parte</button>
        <label className="my-4 block text-sm">Motivo / respaldo<textarea aria-label="Motivo de clasificación" value={motivo} maxLength={500} onChange={e => setMotivo(e.target.value)} className="mt-1 w-full rounded border border-border bg-surface p-2" /></label>
        {guardar.isError && <p role="alert" className="mb-3 text-status-danger">{guardar.error.message}</p>}
        <div className="flex flex-wrap gap-4">
          <button type="button" disabled={guardar.isPending || motivo.trim().length < 3} onClick={() => guardar.mutate(false)} className="rounded bg-finance px-3 py-2 text-white disabled:opacity-40">{guardar.isPending ? 'Guardando…' : 'Guardar clasificación'}</button>
          <button type="button" disabled={guardar.isPending || motivo.trim().length < 3} onClick={() => guardar.mutate(true)} className="text-finance underline">Volver al criterio automático</button>
          <button type="button" disabled={guardar.isPending} onClick={() => setEditando(null)}>Cerrar</button>
        </div>
        <details className="mt-5 text-sm"><summary>Historial de clasificación</summary>
          {historia.isLoading && <p>Cargando…</p>}{historia.isError && <p>No se pudo cargar el historial.</p>}
          {historia.data?.length === 0 && <p>Sin clasificaciones manuales anteriores.</p>}
          {historia.data?.map(h => <div key={h.version} className="border-b border-border py-2"><strong>Versión {h.version}</strong> · {h.usuario} · {formatFecha(h.fecha)}<p>{h.motivo}</p><p>{JSON.parse(h.reparto).map((p: ParteArca) => `${nombres[p.subcuenta]}: débitos ${monto(p.deuda)}, créditos ${monto(p.credito)}`).join(' · ') || 'Vuelta al criterio automático'}</p></div>)}
        </details>
      </div>
    </div>}
  </section>;
}
