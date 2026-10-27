"use client";

import { formatFechaHora } from "@/lib/format";
import { ETIQUETA_CORRIDA, type Corrida } from "@/services/bovedaApi";

const COLOR: Record<string, string> = {
  ok: "text-agro",
  en_curso: "text-finance",
  incompleta: "text-ink-muted",
  salteada: "text-ink-muted",
};

const ORIGEN: Record<Corrida["origen"], string> = {
  programada: "Programada",
  manual: "Manual",
  migrada037: "Semanal / manual (037)",
};

/** Historial de corridas de portales (042, US6; también la vista de peajes de Compras). */
export function CorridasTabla({ corridas, conPortal = false, vacio = "Todavía no hay corridas." }: {
  corridas: Corrida[];
  conPortal?: boolean;
  vacio?: string;
}) {
  if (corridas.length === 0) return <p className="py-4 text-sm text-ink-muted">{vacio}</p>;
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-ink-muted">
          <th className="py-2 pr-3">Inicio</th>
          {conPortal && <th className="py-2 pr-3">Portal</th>}
          <th className="py-2 pr-3">Origen</th>
          <th className="py-2 pr-3">Resultado</th>
          <th className="py-2 pr-3 text-right">Nuevos</th>
          <th className="py-2 pr-3 text-right">Ya estaban</th>
          <th className="py-2 pr-3 text-right">Cargados</th>
          <th className="py-2 pr-3 text-right">Pendientes</th>
        </tr>
      </thead>
      <tbody>
        {corridas.map((c) => (
          <tr key={c.idCorrida} className="border-b border-border/60 align-top">
            <td className="py-2 pr-3 whitespace-nowrap">{formatFechaHora(c.inicio)}</td>
            {conPortal && <td className="py-2 pr-3">{c.portal}</td>}
            <td className="py-2 pr-3">{ORIGEN[c.origen]}{c.usuario && c.origen === "manual" ? ` (${c.usuario})` : ""}</td>
            <td className="py-2 pr-3">
              <span className={COLOR[c.estado] ?? "text-red-700"}>{ETIQUETA_CORRIDA[c.estado] ?? c.estado}</span>
              {c.mensaje && <div className="mt-1 max-w-md text-xs text-ink-secondary">{c.mensaje}</div>}
            </td>
            <td className="py-2 pr-3 text-right">{c.nuevos}</td>
            <td className="py-2 pr-3 text-right">{c.existentes}</td>
            <td className="py-2 pr-3 text-right">{c.cargados}</td>
            <td className="py-2 pr-3 text-right">{c.pendientes}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
