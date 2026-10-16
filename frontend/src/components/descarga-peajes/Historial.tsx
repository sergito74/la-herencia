"use client";

import { useQuery } from "@tanstack/react-query";
import { Fragment, useState } from "react";

import { DocumentosLista } from "@/components/descarga-peajes/DocumentosLista";
import { TablaPortales } from "@/components/descarga-peajes/EjecucionEnCurso";
import { formatFecha } from "@/lib/format";
import { ETIQUETA_EJECUCION, getEjecucion, getEjecuciones, type Ejecucion } from "@/services/descargaPeajesApi";

const POR_PAGINA = 20;

function hora(iso: string): string {
  const m = iso.match(/T(\d{2}:\d{2})/);
  return m ? m[1] : "";
}

function duracion(e: Ejecucion): string {
  if (!e.fin) return "—";
  const seg = Math.max(0, Math.round((Date.parse(e.fin) - Date.parse(e.inicio)) / 1000));
  return seg < 60 ? `${seg} s` : `${Math.floor(seg / 60)} min ${seg % 60} s`;
}

function Detalle({ id }: { id: number }) {
  const q = useQuery({ queryKey: ["descarga-peajes", "ejecucion", id], queryFn: () => getEjecucion(id) });
  if (!q.data) return <p className="py-2 text-sm text-ink-muted">Cargando…</p>;
  return (
    <div className="space-y-3 bg-surface-sunken/40 p-3">
      {q.data.mensaje && <p className="text-sm text-red-700">{q.data.mensaje}</p>}
      <TablaPortales portales={q.data.portales} />
      <DocumentosLista documentos={q.data.documentos} vacio="Esta ejecución no bajó documentos." />
    </div>
  );
}

/** Historial de ejecuciones manuales y semanales (US3). */
export function Historial() {
  const [desde, setDesde] = useState(0);
  const [abierta, setAbierta] = useState<number | null>(null);
  const q = useQuery({
    queryKey: ["descarga-peajes", "ejecuciones", desde],
    queryFn: () => getEjecuciones(POR_PAGINA, desde),
  });

  return (
    <section className="rounded-md border border-border bg-surface p-4">
      <h2 className="mb-2 text-base font-semibold">Historial</h2>
      {q.isError && <p className="text-sm text-red-700">No se pudo cargar el historial.</p>}
      {q.data && q.data.items.length === 0 && <p className="text-sm text-ink-muted">Todavía no hubo ejecuciones.</p>}
      {q.data && q.data.items.length > 0 && (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-ink-muted">
              <th className="py-2 pr-3">Fecha</th>
              <th className="py-2 pr-3">Origen</th>
              <th className="py-2 pr-3">Duración</th>
              <th className="py-2 pr-3">Estado</th>
              <th className="py-2 pr-3 text-right">Nuevos</th>
              <th className="py-2 pr-3 text-right">Cargados</th>
              <th className="py-2 pr-3 text-right">Pendientes</th>
              <th className="py-2" />
            </tr>
          </thead>
          <tbody>
            {q.data.items.map((e) => {
              const suma = (k: "nuevos" | "cargados" | "pendientes") => e.portales.reduce((s, p) => s + p[k], 0);
              const errores = e.portales.filter((p) => p.estado === "error").map((p) => p.portal);
              return (
                <Fragment key={e.idEjecucion}>
                  <tr className="border-b border-border/60">
                    <td className="py-2 pr-3 whitespace-nowrap">
                      {formatFecha(e.inicio)} {hora(e.inicio)}
                    </td>
                    <td className="py-2 pr-3">
                      {e.origen === "semanal" ? "Semanal" : `Manual${e.usuario ? ` (${e.usuario})` : ""}`}
                    </td>
                    <td className="py-2 pr-3">{duracion(e)}</td>
                    <td className="py-2 pr-3">
                      {ETIQUETA_EJECUCION[e.estado]}
                      {errores.length > 0 && <span className="text-xs text-red-700"> · error en {errores.join(", ")}</span>}
                    </td>
                    <td className="py-2 pr-3 text-right">{suma("nuevos")}</td>
                    <td className="py-2 pr-3 text-right">{suma("cargados")}</td>
                    <td className="py-2 pr-3 text-right">{suma("pendientes")}</td>
                    <td className="py-2 text-right">
                      <button
                        type="button"
                        className="text-finance hover:underline"
                        onClick={() => setAbierta(abierta === e.idEjecucion ? null : e.idEjecucion)}
                      >
                        {abierta === e.idEjecucion ? "Ocultar" : "Ver detalle"}
                      </button>
                    </td>
                  </tr>
                  {abierta === e.idEjecucion && (
                    <tr>
                      <td colSpan={8}>
                        <Detalle id={e.idEjecucion} />
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      )}
      {q.data && q.data.total > POR_PAGINA && (
        <div className="mt-3 flex items-center gap-3 text-sm">
          <button type="button" disabled={desde === 0} onClick={() => setDesde(Math.max(0, desde - POR_PAGINA))}
            className="text-finance disabled:text-ink-muted">
            ← Más recientes
          </button>
          <button type="button" disabled={desde + POR_PAGINA >= q.data.total} onClick={() => setDesde(desde + POR_PAGINA)}
            className="text-finance disabled:text-ink-muted">
            Más antiguas →
          </button>
        </div>
      )}
    </section>
  );
}
