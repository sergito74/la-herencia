"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { SoloLectura } from "@/components/auth/SoloLectura";
import { NumberInput } from "@/components/ui/NumberInput";
import { SideDrawer } from "@/components/ui/SideDrawer";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { formatCantidad, formatFecha } from "@/lib/format";
import { actualizarInmag, cargarInmagManual, indiceInmag } from "@/services/pastajeApi";

import { btnPrimario, btnSecundario, indice, inputCls } from "./comunes";

const DIAS = ["Do", "Lu", "Ma", "Mi", "Ju", "Vi", "Sá"];

function rango(periodo: string): { desde: string; hasta: string; dias: string[] } {
  const [a, m] = periodo.split("-").map(Number);
  const n = new Date(a, m, 0).getDate();
  const dias = Array.from({ length: n }, (_, i) => `${periodo}-${String(i + 1).padStart(2, "0")}`);
  return { desde: dias[0], hasta: dias[n - 1], dias };
}

/** Índice INMAG por día del mes: los días sin remate (o con menos de 300 novillos) quedan en "—". */
export function IndicePanel({ periodoInicial }: { periodoInicial?: string }) {
  const cache = useQueryClient();
  const [periodo, setPeriodo] = useState(periodoInicial ?? new Date().toISOString().slice(0, 7));
  const [manual, setManual] = useState<string | null>(null);
  const [valor, setValor] = useState<number | null>(null);
  const [nota, setNota] = useState("");
  const r = rango(periodo);
  const q = useQuery({ queryKey: ["pastaje", "inmag", periodo], queryFn: () => indiceInmag(r.desde, r.hasta) });
  const act = useMutation({ mutationFn: actualizarInmag, onSuccess: () => cache.invalidateQueries({ queryKey: ["pastaje"] }) });
  const carga = useMutation({
    mutationFn: () => cargarInmagManual(manual!, String(valor), nota),
    onSuccess: () => {
      setManual(null);
      cache.invalidateQueries({ queryKey: ["pastaje"] });
    },
  });
  const porFecha = new Map((q.data ?? []).map((d) => [d.fecha, d]));
  const valores = (q.data ?? []).map((d) => Number(d.indice));
  const promedio = valores.length ? valores.reduce((a, b) => a + b, 0) / valores.length : null;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <label className="text-sm">
          Mes
          <input type="month" className="ml-2 rounded-sm border border-border bg-surface px-2 py-1" value={periodo} onChange={(e) => setPeriodo(e.target.value)} />
        </label>
        <SoloLectura>
          <button className={btnSecundario} disabled={act.isPending} onClick={() => act.mutate()}>
            {act.isPending ? "Consultando el Mercado…" : "Actualizar ahora"}
          </button>
        </SoloLectura>
      </div>
      {act.data && <p role="status" className="text-sm">Se agregaron {act.data.agregados} días.</p>}
      {act.error && <p role="alert" className="text-sm text-status-danger">{(act.error as Error).message}</p>}
      <p className="text-sm text-ink-secondary">
        Fuente: Mercado Agroganadero de Cañuelas (I.N.M.A.G.). Se carga solo todos los días a las 19 h. Promedio simple del mes: <span className="font-data">{promedio ? indice(promedio.toFixed(2)) : "—"}</span> (la liquidación usa solo los días con hacienda en el campo).
      </p>
      {q.isLoading && <LoadingState />}
      {q.isError && <ErrorState message={(q.error as Error).message} onRetry={() => q.refetch()} />}
      {q.isSuccess && (
        <table className="min-w-full max-w-xl text-sm">
          <thead className="text-left text-xs uppercase text-ink-secondary">
            <tr><th className="py-1">Día</th><th className="text-right">INMAG $/kg</th><th className="text-right">Cabezas ingresadas</th><th>Origen</th><th /></tr>
          </thead>
          <tbody className="divide-y divide-border">
            {r.dias.map((f) => {
              const d = porFecha.get(f);
              const dow = new Date(`${f}T12:00:00`).getDay();
              if (!d && (dow === 0 || dow === 6)) return null;
              return (
                <tr key={f}>
                  <td className="py-1">{DIAS[dow]} {formatFecha(f)}</td>
                  <td className="font-data text-right tabular-nums">{d ? indice(d.indice) : "—"}</td>
                  <td className="font-data text-right tabular-nums">{d?.cabIngresadas ? formatCantidad(d.cabIngresadas) : "—"}</td>
                  <td className="pl-3">{d ? (d.origen === "manual" ? `Manual: ${d.nota}` : "Automático") : "Sin índice publicado"}</td>
                  <td>
                    <SoloLectura>
                      <button className="text-xs underline" onClick={() => { setManual(f); setValor(d ? Number(d.indice) : null); setNota(""); }}>
                        {d ? "Corregir" : "Cargar"}
                      </button>
                    </SoloLectura>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
      <SideDrawer open={manual !== null} onClose={() => setManual(null)} title={`INMAG del ${manual ? formatFecha(manual) : ""}`}>
        <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); carga.mutate(); }}>
          <label className="block text-sm">Valor $/kg<NumberInput className={inputCls} value={valor} maxDecimales={3} onChange={setValor} required /></label>
          <label className="block text-sm">Nota (obligatoria: de dónde sale el valor)<input autoFocus required className={inputCls} value={nota} onChange={(e) => setNota(e.target.value)} /></label>
          <p className="text-xs text-ink-secondary">Si el mes ya está liquidado, el cambio aparece como diferencia para resolver con un ajuste.</p>
          {carga.error && <p role="alert" className="text-sm text-status-danger">{(carga.error as Error).message}</p>}
          <button className={btnPrimario} disabled={!valor || !nota || carga.isPending}>Guardar</button>
        </form>
      </SideDrawer>
    </div>
  );
}
