"use client";

import { formatFechaHora } from "@/lib/format";
import { ETIQUETA_CORRIDA, type Portal } from "@/services/bovedaApi";

/** Barra de avance: determinada si se conoce el total, indeterminada (animada) si no. */
export function BarraAvance({ hecho, total }: { hecho: number | null; total: number | null }) {
  const conTotal = total !== null && total > 0 && hecho !== null;
  const pct = conTotal ? Math.min(100, Math.round((hecho! / total!) * 100)) : 0;
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-surface-sunken" role="progressbar"
      aria-valuemin={0} aria-valuemax={100} aria-valuenow={conTotal ? pct : undefined}>
      {conTotal ? (
        <div className="h-full rounded-full bg-finance transition-all duration-500" style={{ width: `${Math.max(pct, 3)}%` }} />
      ) : (
        <div className="h-full w-1/3 animate-[avance_1.2s_ease-in-out_infinite] rounded-full bg-finance" />
      )}
    </div>
  );
}

function resumenCorrida(p: Portal): string {
  const c = p.ultimaCorrida!;
  const partes = [`${c.nuevos} nuevos`];
  if (c.existentes) partes.push(`${c.existentes} ya estaban`);
  if (c.cargados) partes.push(`${c.cargados} cargados en Compras`);
  if (c.pendientes) partes.push(`${c.pendientes} para cargar a mano`);
  return partes.join(" · ");
}

/** Qué está pasando con la sincronización de una cuenta, en palabras (042, pedido de Sergio 27/10/2026). */
export function EstadoSincronizacion({ portal }: { portal: Portal }) {
  if (portal.enCurso) {
    const pr = portal.progreso;
    return (
      <div className="min-w-[14rem] space-y-1">
        <div className="flex items-center justify-between gap-2 text-xs">
          <span className="font-medium text-finance">Sincronizando…</span>
          {pr?.total ? <span className="text-ink-secondary">{pr.hecho ?? 0} de {pr.total}</span> : null}
        </div>
        <BarraAvance hecho={pr?.hecho ?? null} total={pr?.total ?? null} />
        <p className="text-xs text-ink-secondary">{pr?.paso ?? "Empezando…"}</p>
      </div>
    );
  }
  if (portal.enCola) {
    return (
      <div className="min-w-[14rem] space-y-1">
        <span className="text-xs font-medium text-ink-secondary">En cola: espera a que termine la cuenta anterior</span>
        <div className="h-2 w-full rounded-full bg-surface-sunken" />
      </div>
    );
  }
  if (portal.recordatorio) {
    return (
      <span className="text-xs font-medium text-amber-800">
        {portal.recordatorio}{" "}
        <a href={portal.url} target="_blank" rel="noreferrer" className="text-finance underline">
          Abrir la página
        </a>
      </span>
    );
  }
  const c = portal.ultimaCorrida;
  if (!c) {
    return <span className="text-xs text-ink-muted">{portal.motivoNoSincroniza ? "—" : "Nunca se sincronizó"}</span>;
  }
  const ok = c.estado === "ok";
  return (
    <div className="space-y-0.5 text-xs">
      <div className={ok ? "text-agro" : c.estado === "incompleta" ? "text-ink-muted" : "text-red-700"}>
        {ok ? "✓ Sincronizada" : ETIQUETA_CORRIDA[c.estado] ?? c.estado} · {formatFechaHora(c.fin ?? c.inicio)}
      </div>
      {ok ? <div className="text-ink-secondary">{resumenCorrida(portal)}</div>
        : c.mensaje && <div className="max-w-sm text-ink-secondary">{c.mensaje}</div>}
    </div>
  );
}

/** Columna "Sincronización automática": si existe, si está activa y cuándo es la próxima. */
export function SincronizacionAutomatica({ portal }: { portal: Portal }) {
  // Sin acción posible del usuario: se informa en gris, no como alerta.
  if (portal.motivoNoSincroniza === "Próximamente" || portal.motivoNoSincroniza?.startsWith("No se puede automatizar")) {
    return <span className="text-xs text-ink-muted">{portal.motivoNoSincroniza}</span>;
  }
  if (portal.motivoNoSincroniza) return <span className="text-xs text-red-700">{portal.motivoNoSincroniza}</span>;
  const p = portal.programacion;
  if (p?.suspendida) return <span className="text-xs text-red-700">Pausada: {p.motivoSuspension}</span>;
  if (!p || p.frecuencia === "desactivada") return <span className="text-xs text-ink-secondary">Disponible · solo manual</span>;
  return (
    <span className="text-xs text-ink-secondary">
      Activa · próxima {formatFechaHora(p.proximaCorrida)}
    </span>
  );
}
