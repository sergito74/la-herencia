"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { SoloLectura } from "@/components/auth/SoloLectura";
import { Button } from "@/components/ui/Button";
import { Callout } from "@/components/ui/Callout";
import { formatFecha } from "@/lib/format";
import { actualizarListadosEstudio, fetchListadosEstudio } from "@/services/tesoreriaApi";

const cuando = (iso?: string | null) => (iso ? `${formatFecha(iso)} ${iso.slice(11, 16)}` : "nunca");

/** 18/11/2026: informes de conciliación de bancos y tarjetas que el Estudio usa desde Dropbox (Bancos/…). El sistema
 * los regenera solo cuando cambian los datos; acá se ven en una línea y el detalle queda a un clic. */
export function ListadosEstudio({ modo = "barra" }: { modo?: "barra" | "chip" } = {}) {
  const [abierto, setAbierto] = useState(false);
  const { data, refetch } = useQuery({ queryKey: ["listados-estudio"], queryFn: fetchListadosEstudio });
  const [ocupado, setOcupado] = useState(false);
  const [error, setError] = useState("");
  const lista = data ?? [];
  const faltan = lista.filter((l) => !l.actualizada);
  const ultima = lista.map((l) => l.actualizada ?? "").sort().at(-1);

  async function actualizar() {
    setOcupado(true); setError("");
    try {
      const r = await actualizarListadosEstudio();
      const fallidos = r.filter((x) => !x.ok);
      if (fallidos.length) setError(fallidos.map((f) => `${f.banco}: ${f.detalle}`).join(" · "));
      await refetch();
    } catch (e) { setError(e instanceof Error ? e.message : "No se pudieron actualizar"); }
    finally { setOcupado(false); }
  }

  if (modo === "chip") {
    const tono = error ? "bg-status-danger" : faltan.length ? "bg-status-warning" : "bg-status-success";
    return (
      <div className="relative">
        <button type="button" onClick={() => setAbierto((v) => !v)} aria-expanded={abierto}
          title={`Informes del Estudio en Dropbox: ${faltan.length ? `${faltan.length} sin generar` : "al día"} · ${cuando(ultima)} h`}
          className="inline-flex h-7 items-center gap-1.5 rounded-full border border-border bg-surface px-2.5 text-xs text-ink-secondary hover:bg-surface-sunken">
          <span aria-hidden className={`h-2 w-2 rounded-full ${tono}`} />
          {error ? "Estudio: error" : faltan.length ? `Estudio: ${faltan.length} sin generar` : "Estudio al día"}
        </button>
        {abierto && (
          <div className="absolute left-0 z-30 mt-1 w-[26rem] space-y-2 rounded-lg border border-border bg-surface p-3 text-sm shadow-lg">
            <p className="text-xs text-ink-secondary">Informes de bancos y tarjetas en Dropbox; el sistema los regenera solo cuando cambian los datos.</p>
            <ul className="space-y-0.5">
              {lista.map((l) => <li key={l.archivo} className="flex justify-between gap-3"><span>{l.banco}</span><span className="text-ink-muted">{cuando(l.actualizada)}</span></li>)}
            </ul>
            {error && <p className="text-xs text-status-danger">{error}</p>}
            <SoloLectura><Button size="sm" onClick={actualizar} disabled={ocupado}>{ocupado ? "Actualizando…" : "Actualizar ahora"}</Button></SoloLectura>
          </div>
        )}
      </div>
    );
  }
  return (
    <Callout tono={error ? "error" : faltan.length ? "aviso" : "info"}
      titulo="Informes del Estudio"
      resumen={error || (faltan.length ? `${faltan.length} sin generar` : `al día · ${lista.length} informes de bancos y tarjetas en Dropbox · ${cuando(ultima)} h`)}
      accion={<SoloLectura><Button size="sm" onClick={actualizar} disabled={ocupado}>{ocupado ? "Actualizando…" : "Actualizar"}</Button></SoloLectura>}>
      <p className="mb-2 text-xs text-ink-secondary">Dropbox › Giamigli de Bolivar SA › Bancos. El sistema los regenera solo cuando cambian los datos (cada 3 horas y al cargar un extracto).</p>
      <ul className="grid gap-x-6 gap-y-1 text-sm sm:grid-cols-2 lg:grid-cols-4">
        {lista.map((l) => <li key={l.archivo} className="flex justify-between gap-3"><span>{l.banco}</span><span className="text-ink-muted">{cuando(l.actualizada)}</span></li>)}
      </ul>
    </Callout>
  );
}
