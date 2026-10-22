"use client";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { SoloLectura } from "@/components/auth/SoloLectura";
import { OperacionCajaForm, hoyCaja, nombresCaja } from "./OperacionCajaForm";
import { previewImportacionCaja, confirmarImportacionCaja, type DecisionImportacionCaja, type LoteCaja } from "@/services/cajasEfectivoApi";
import { formatFecha, formatMoneda } from "@/lib/format";

export function ImportacionCajaPanel() {
  const cache = useQueryClient();
  const [archivo, setArchivo] = useState<File | null>(null);
  const [libro, setLibro] = useState("CajasGiamigli");
  const [fecha, setFecha] = useState(hoyCaja());
  const [lote, setLote] = useState<LoteCaja | null>(null);
  const [decisiones, setDecisiones] = useState<Record<number, DecisionImportacionCaja>>({});
  const [clasificar, setClasificar] = useState<number | null>(null);
  const [page, setPage] = useState(1);
  const [negativo, setNegativo] = useState(false);
  const preview = useMutation({ mutationFn: () => previewImportacionCaja(archivo!, libro, fecha), onSuccess: l => { setLote(l); setDecisiones({}); setPage(1); setClasificar(null); } });
  const confirmar = useMutation({ mutationFn: () => confirmarImportacionCaja(lote!.idLote, Object.values(decisiones), negativo), onSuccess: async l => { setLote(l); setDecisiones({}); setClasificar(null); await cache.invalidateQueries({ predicate: q => q.queryKey[0] !== "auth" }); } });
  function decision(id: number, patch: Partial<DecisionImportacionCaja>) {
    setDecisiones(prev => ({ ...prev, [id]: { ...(prev[id] ?? { idFila: id, accion: "pendiente" }), ...patch } }));
  }
  const seleccionada = lote?.filas.find(f => f.idFila === clasificar);
  return <SoloLectura><section className="space-y-4 rounded border border-border p-4"><h3 className="font-semibold">Convivencia con la planilla</h3><p>Importar identifica las filas y propone vínculos. Ningún archivo original se modifica. Las coincidencias dudosas se revisan antes de crear movimientos.</p>
    <form className="flex flex-wrap items-end gap-3" onSubmit={e => { e.preventDefault(); preview.mutate(); }}>
      <label>Libro<select className="block rounded border border-border p-2" value={libro} onChange={e => setLibro(e.target.value)}><option value="CajasGiamigli">Cajas Giamigli</option><option value="CondominioLSC">Caja Condominio (exportación XLSX sin macros)</option></select></label>
      <label>Corte<input className="block rounded border border-border p-2" type="date" required value={fecha} onChange={e => setFecha(e.target.value)} /></label>
      <label>Archivo XLSX<input className="block" type="file" accept=".xlsx" required onChange={e => setArchivo(e.target.files?.[0] ?? null)} /></label>
      <button className="rounded border border-border p-2 disabled:opacity-50" disabled={!archivo || preview.isPending}>{preview.isPending ? "Leyendo…" : "Previsualizar archivo"}</button>
    </form>
    {(preview.error || confirmar.error) && <p role="alert" className="text-status-danger">{(preview.error || confirmar.error)?.message}</p>}
    {lote && <><p>Lote {lote.idLote} · {lote.estado} · corte {formatFecha(lote.fechaCorte)} · {lote.filas.length} filas</p>
      <div className="grid gap-3 md:grid-cols-3">{Object.entries(lote.comparacion).map(([box, c]) => c && <div className="rounded border border-border p-3" key={box}><h4 className="font-semibold">{nombresCaja[box as keyof typeof nombresCaja]}</h4><p>Sistema: {formatMoneda(Number(c.saldoSistema))}</p><p>Planilla: {c.saldoPlanilla === null ? "Sin saldo cacheado verificable" : formatMoneda(Number(c.saldoPlanilla))}</p><p>Diferencia: {c.diferencia === null ? "No calculable" : formatMoneda(Number(c.diferencia))}</p><p>{c.pendientes} filas pendientes · {c.soloSistema.length} movimientos sin vínculo a estas filas</p><p>Diferencias de contenido: {c.modificadas.length} · ambiguas: {c.ambiguas.length} · excluidas: {c.excluidas.length}</p><p className="text-sm">{c.cobertura}</p></div>)}</div>
      <div className="overflow-x-auto"><table className="w-full text-sm"><thead><tr>{["Origen", "Fecha", "Concepto", "Importe", "Estado", "Decisión"].map(x => <th className="p-2 text-left" key={x}>{x}</th>)}</tr></thead><tbody>{lote.filas.slice((page - 1) * 50, page * 50).map(f => {
        const d = decisiones[f.idFila]; const resuelta = f.estado === "Vinculada" || f.estado === "Excluida";
        return <tr key={f.idFila} className="border-t border-border"><td className="p-2">{f.hoja} · fila {f.fila}</td><td className="p-2">{formatFecha(f.datos.fecha)}</td><td className="p-2">{f.datos.concepto}<p>{f.motivo}</p></td><td className="p-2">{f.datos.importe == null ? "Sin importe" : formatMoneda(Number(f.datos.importe))}</td><td className="p-2">{f.estado}{d?.operacion && " · clasificada"}{!!f.diferenciasVinculo?.length && ` · difiere ${f.diferenciasVinculo.join(", ")}`}</td><td className="space-y-2 p-2">
          {resuelta ? <span>{f.idMovimiento ? `Vinculada al movimiento ${f.idMovimiento}` : "Excluida con motivo"}</span> : lote.estado !== "Confirmado" && <>
            <select className="rounded border border-border p-2" value={d?.accion ?? "pendiente"} onChange={e => decision(f.idFila, { accion: e.target.value as DecisionImportacionCaja["accion"] })}><option value="pendiente">Dejar pendiente</option><option value="vincular">Vincular existente</option><option value="importar">Crear operación</option><option value="excluir">Excluir con motivo</option></select>
            {d?.accion === "vincular" && <select className="block rounded border border-border p-2" value={d.idMovimiento ?? 0} onChange={e => decision(f.idFila, { idMovimiento: Number(e.target.value) })}><option value={0}>Elegir coincidencia</option>{f.candidatas.filter(c => !c.anulada).map(c => <option value={c.idMovimiento} key={c.idMovimiento}>{c.concepto} · movimiento {c.idMovimiento}</option>)}</select>}
            {(d?.accion === "excluir" || d?.accion === "importar" || d?.accion === "vincular") && <input className="block rounded border border-border p-2" value={d?.motivo ?? ""} placeholder="Motivo / evidencia" maxLength={255} onChange={e => decision(f.idFila, { motivo: e.target.value })} />}
            {d?.accion === "importar" && <><button type="button" className="block underline" onClick={() => setClasificar(f.idFila)}>{d.operacion ? "Revisar clasificación" : "Clasificar y previsualizar"}</button>{(f.candidatas.length > 0 || f.estado === "Modificada") && <label className="block"><input type="checkbox" checked={d.confirmarDistinto ?? false} onChange={e => decision(f.idFila, { confirmarDistinto: e.target.checked })} /> Confirmo que es una operación distinta y lo justifico en el motivo</label>}</>}
          </>}
        </td></tr>;
      })}</tbody></table></div>
      <div className="flex gap-3"><button disabled={page === 1} onClick={() => setPage(p => p - 1)}>Anterior</button><span>Página {page} de {Math.max(1, Math.ceil(lote.filas.length / 50))}</span><button disabled={page * 50 >= lote.filas.length} onClick={() => setPage(p => p + 1)}>Siguiente</button></div>
      {seleccionada && <OperacionCajaForm key={`${lote.idLote}:${seleccionada.idFila}`} caja={seleccionada.datos.caja} initial={{ fecha: seleccionada.datos.fecha ?? undefined, importe: seleccionada.datos.importe ?? undefined, concepto: seleccionada.datos.concepto, cuenta: seleccionada.datos.cuenta }} onPrepared={body => { decision(seleccionada.idFila, { accion: "importar", operacion: body }); setClasificar(null); }} />}
      {lote.estado !== "Confirmado" && <div className="space-y-2"><p>Se guardan juntas las filas resueltas. Las pendientes pueden continuarse después. Si cambió el contexto, deberán actualizarse sus vistas previas.</p>
        {Object.entries(lote.comparacion).map(([box, c]) => { if (!c) return null; const cambio = Object.values(decisiones).filter(d => d.accion === "importar" && d.operacion).reduce((sum, d) => {
          const o = d.operacion!.operacion; const ingreso = ["aporte", "cobro", "extraccion_banco", "retorno_sueldo_opcion_a"].includes(o.tipo); const v = Number(o.importe) * (ingreso ? 1 : -1);
          return sum + (o.caja === box ? v : o.cajaDestino === box || o.cajaContraparte === box ? -v : 0);
        }, 0); return <p key={box}>{nombresCaja[box as keyof typeof nombresCaja]}: saldo al corte con las filas elegidas {formatMoneda(Number(c.saldoSistema) + cambio)}</p>; })}
        <label className="block"><input type="checkbox" checked={negativo} onChange={e => setNegativo(e.target.checked)} /> Confirmo si el conjunto de filas deja saldo negativo en alguna caja.</label>
        <button className="rounded border border-border p-2 disabled:opacity-50" disabled={confirmar.isPending || Object.keys(decisiones).length === 0 || Object.values(decisiones).some(d => d.accion === "importar" && !d.operacion)} onClick={() => confirmar.mutate()}>{confirmar.isPending ? "Confirmando…" : "Confirmar decisiones del lote"}</button>
      </div>}
    </>}
  </section></SoloLectura>;
}
