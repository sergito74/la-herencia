"use client";
import Link from "next/link";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { SoloLectura } from "@/components/auth/SoloLectura";
import { formatCantidad, formatFecha } from "@/lib/format";
import { fetchPlanillaMatias, leerPlanillaMatias } from "@/services/ordenesApi";

/** 18/11/2026: lectura de la planilla de órdenes de pulverización de Matías (solapa "orden pulv LH"). Las órdenes
 * nuevas se crean Planificadas, con los productos del stock elegidos por FIFO; acá se ve qué se creó, qué falta comprar
 * y qué no se pudo cargar porque la planilla no cierra. */
export function PlanillaMatias() {
  const qc = useQueryClient();
  const [ocupado, setOcupado] = useState(false);
  const [error, setError] = useState("");
  const { data } = useQuery({ queryKey: ["planilla-matias"], queryFn: fetchPlanillaMatias });

  async function leer() {
    setOcupado(true); setError("");
    try {
      const r = await leerPlanillaMatias();
      qc.setQueryData(["planilla-matias"], r);
      await qc.invalidateQueries({ queryKey: ["ordenes"] });
    } catch (e) { setError(e instanceof Error ? e.message : "No se pudo leer la planilla"); }
    finally { setOcupado(false); }
  }

  const creadas = data?.creadas ?? [], revisar = data?.paraRevisar ?? [], cambiadas = data?.cambiadas ?? [];
  return <section className="mb-3 space-y-2 rounded-lg border border-border bg-surface p-3 text-sm">
    <div className="flex flex-wrap items-center gap-3">
      <strong>Órdenes de Matías</strong>
      <span className="text-ink-secondary">{data?.leida ? `Planilla leída el ${formatFecha(data.leida)} a las ${data.leida.slice(11, 16)}` : "Todavía no se leyó la planilla"}</span>
      <SoloLectura><button className="rounded border border-border px-3 py-1 hover:bg-surface-sunken disabled:opacity-50" disabled={ocupado} onClick={leer}>{ocupado ? "Leyendo…" : "Leer la planilla de Matías"}</button></SoloLectura>
    </div>
    {creadas.map(c => <p key={c.fecha}>
      Orden del {formatFecha(c.fecha)} cargada{c.idOrden ? <> como <Link className="text-finance underline" href={`/produccion/ordenes/${c.idOrden}/editar`}>orden {c.idOrden}</Link></> : ""}.
      {c.faltantes.length > 0 && <span className="text-amber-800"> Falta stock: {c.faltantes.map(f => `${f.producto} ${formatCantidad(f.falta)}`).join(", ")}.</span>}
    </p>)}
    {revisar.map(r => <div key={r.fecha} className="text-amber-800">
      <p>La orden del {formatFecha(r.fecha)} no se cargó porque la planilla no cierra:</p>
      <ul className="ml-5 list-disc">{r.problemas.map(p => <li key={p}>{p}</li>)}</ul>
    </div>)}
    {cambiadas.map(c => <p key={c.fecha} className="text-amber-800">La orden del {formatFecha(c.fecha)} ({c.idOrden}) cambió en la planilla después de cargarla: revisala.</p>)}
    {error && <p role="alert" className="text-red-700">{error}</p>}
  </section>;
}
