"use client";
import { useState } from "react";

/** Aviso de una línea que se despliega (18/11/2026): resume el estado en una frase y deja el detalle a un clic, para
 * que los avisos no ocupen la pantalla antes que el contenido (patrón de Stripe/Linear). */
export function Callout({ tono = "info", titulo, resumen, accion, defaultAbierto = false, children }: {
  tono?: "info" | "ok" | "aviso" | "error";
  titulo: React.ReactNode;
  resumen?: React.ReactNode;
  accion?: React.ReactNode;
  defaultAbierto?: boolean;
  children?: React.ReactNode;
}) {
  const [abierto, setAbierto] = useState(defaultAbierto);
  const colores = {
    info: "border-border bg-surface",
    ok: "border-status-success/30 bg-status-success-bg/60",
    aviso: "border-status-warning/40 bg-status-warning-bg/70",
    error: "border-status-danger/40 bg-status-danger-bg/70",
  }[tono];
  const punto = { info: "bg-finance", ok: "bg-status-success", aviso: "bg-status-warning", error: "bg-status-danger" }[tono];
  return (
    <section className={`mb-3 rounded-lg border ${colores} px-4 py-2.5 text-sm`}>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <span aria-hidden className={`h-2 w-2 shrink-0 rounded-full ${punto}`} />
        <strong className="font-semibold text-ink-primary">{titulo}</strong>
        {resumen && <span className="text-ink-secondary">{resumen}</span>}
        <span className="ml-auto flex items-center gap-2">
          {children && (
            <button type="button" onClick={() => setAbierto((v) => !v)} aria-expanded={abierto}
              className="rounded-md px-2 py-1 text-xs font-medium text-finance hover:bg-finance-light">
              {abierto ? "Ocultar" : "Ver detalle"}
            </button>
          )}
          {accion}
        </span>
      </div>
      {abierto && children && <div className="mt-3 border-t border-border/70 pt-3">{children}</div>}
    </section>
  );
}
