"use client";

import { useQuery } from "@tanstack/react-query";

import { formatFechaHora } from "@/lib/format";
import { getEstadoRutina } from "@/services/documentosNuevosApi";

const ESTADO: Record<string, string> = {
  en_curso: "En curso",
  ok: "Terminó bien",
  con_problemas: "Terminó con cuentas a revisar",
  incompleta: "Se cortó antes de terminar",
};

/** Rutina diaria de documentos nuevos (043, FR-013): corre sola a las 7:00 y a las 14:00, sin botón. */
export function RutinaPanel() {
  const q = useQuery({ queryKey: ["documentos-nuevos", "rutina"], queryFn: getEstadoRutina, refetchInterval: 60 * 1000 });
  if (!q.data) return null;
  const u = q.data.ultima;

  return (
    <section className="rounded-md border border-border bg-surface px-3 py-2 text-sm">
      <h2 className="font-semibold">Rutina diaria (7:00 y 14:00)</h2>
      <p className="text-ink-secondary">
        Trae lo nuevo de las cuentas y de los mails, y lo deja para revisar en el menú de cada módulo.
        {q.data.proxima && <> Próxima: <strong>{formatFechaHora(q.data.proxima)}</strong>.</>}
      </p>
      {u ? (
        <p className="mt-1 text-ink-secondary">
          Última: {formatFechaHora(u.inicio)} · {ESTADO[u.estado] ?? u.estado} · {u.cuentasCorridas} cuentas
          {u.cuentasConProblemas ? ` (${u.cuentasConProblemas} con problemas)` : ""} · {u.mailsLeidos} mails ·{" "}
          {u.documentosNuevos} documentos nuevos ({u.cargadosSolos} cargados solos, {u.paraCargarAMano} para cargar a mano)
          {u.mensaje && <span className="block text-amber-900">{u.mensaje}</span>}
        </p>
      ) : (
        <p className="mt-1 text-ink-muted">Todavía no corrió.</p>
      )}
    </section>
  );
}
