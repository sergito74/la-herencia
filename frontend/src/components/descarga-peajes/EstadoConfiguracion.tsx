"use client";

import { formatFecha } from "@/lib/format";
import type { EstadoConfiguracion as Estado } from "@/services/descargaPeajesApi";

const INSTALADOR = "powershell -ExecutionPolicy Bypass -File C:\\dev\\LaHerencia\\backend\\scripts\\instalar_descarga_peajes.ps1";

/** Credenciales por portal (sí/no, nunca valores) y tarea semanal (US4, FR-013/014). */
export function EstadoConfiguracion({ estado }: { estado: Estado | undefined }) {
  if (!estado) return null;
  const faltan = estado.portales.some((p) => !p.credenciales) || !estado.tarea.instalada;
  const proxima = estado.tarea.proximaCorrida;
  return (
    <section className="rounded-md border border-border bg-surface p-4">
      <h2 className="mb-2 text-base font-semibold">Configuración</h2>
      <div className="flex flex-wrap gap-4 text-sm">
        {estado.portales.map((p) => (
          <span key={p.portal} className="flex items-center gap-1">
            <span className={p.credenciales ? "text-agro" : "text-amber-700"}>{p.credenciales ? "●" : "○"}</span>
            {p.portal}: {p.credenciales ? "configurado" : "sin configurar"}
          </span>
        ))}
        <span className="flex items-center gap-1">
          <span className={estado.tarea.instalada ? "text-agro" : "text-amber-700"}>
            {estado.tarea.instalada ? "●" : "○"}
          </span>
          Tarea semanal:{" "}
          {estado.tarea.instalada
            ? proxima
              ? `próxima corrida ${formatFecha(proxima)} ${proxima.slice(11, 16)}`
              : "instalada"
            : "no instalada"}
        </span>
      </div>
      {faltan && (
        <p className="mt-2 text-xs text-ink-secondary">
          Para configurar credenciales y la tarea semanal, correr una vez en PowerShell:{" "}
          <code className="rounded-sm bg-surface-sunken px-1">{INSTALADOR}</code>
        </p>
      )}
    </section>
  );
}
