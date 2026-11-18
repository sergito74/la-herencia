"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { SoloLectura } from "@/components/auth/SoloLectura";
import { formatFecha } from "@/lib/format";
import { actualizarListadosEstudio, fetchListadosEstudio } from "@/services/tesoreriaApi";

/** 18/11/2026: planillas de conciliación bancaria que el Estudio usa desde Dropbox (Bancos/…). El sistema las regenera solo
 * cuando cambian los datos (cada 3 horas mientras está abierto, y al cargar un extracto); el botón fuerza la actualización. */
export function ListadosEstudio() {
  const { data, refetch } = useQuery({ queryKey: ["listados-estudio"], queryFn: fetchListadosEstudio });
  const [ocupado, setOcupado] = useState(false);
  const [aviso, setAviso] = useState<{ tono: "ok" | "error"; texto: string } | null>(null);

  async function actualizar() {
    setOcupado(true); setAviso(null);
    try {
      const r = await actualizarListadosEstudio();
      const fallidos = r.filter(x => !x.ok);
      setAviso(fallidos.length
        ? { tono: "error", texto: fallidos.map(f => `${f.banco}: ${f.detalle}`).join(" · ") }
        : { tono: "ok", texto: "Listo: las planillas del Estudio quedaron actualizadas en Dropbox." });
      await refetch();
    } catch (e) { setAviso({ tono: "error", texto: e instanceof Error ? e.message : "No se pudieron actualizar" }); }
    finally { setOcupado(false); }
  }

  return <section className="mb-4 rounded-lg border border-border bg-surface p-4 shadow-sm">
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 className="text-base font-semibold text-ink-primary">Informes para el Estudio</h2>
        <p className="text-sm text-ink-secondary">Conciliaciones de bancos y tarjetas en Dropbox (Giamigli de Bolivar SA › Bancos). El sistema las mantiene al día solo cuando cambian los datos.</p>
      </div>
      <SoloLectura>
        <button onClick={actualizar} disabled={ocupado}
          className="rounded-md bg-finance font-medium text-white shadow-sm transition-colors hover:bg-finance/90 disabled:opacity-60 px-4 py-2 text-sm">
          {ocupado ? "Actualizando…" : "Actualizar ahora"}
        </button>
      </SoloLectura>
    </div>
    <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
      {(data ?? []).map(l => <div key={l.archivo} className="rounded-md border border-border bg-surface-sunken/50 px-3 py-2">
        <p className="text-sm font-medium text-ink-primary">{l.banco}</p>
        <p className="text-xs text-ink-secondary">{l.actualizada ? `Actualizada el ${formatFecha(l.actualizada)} a las ${l.actualizada.slice(11, 16)} h` : "Todavía no se generó"}</p>
      </div>)}
    </div>
    {aviso && <p role={aviso.tono === "error" ? "alert" : "status"} className={`mt-3 rounded-md px-3 py-2 text-sm ${aviso.tono === "ok" ? "bg-status-success-bg text-status-success" : "bg-status-danger-bg text-status-danger"}`}>{aviso.texto}</p>}
  </section>;
}
