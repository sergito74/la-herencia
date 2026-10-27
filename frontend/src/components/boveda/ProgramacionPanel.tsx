"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { EstadoSincronizacion } from "@/components/boveda/EstadoSincronizacion";
import { formatFechaHora } from "@/lib/format";
import { correrAhora, programar, type Frecuencia, type Portal } from "@/services/bovedaApi";

const DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];
const inputCls = "rounded-md border border-border bg-surface px-2 py-1 text-sm";

/** Periodicidad de un portal y "Correr ahora" (042, US2, T025). Las corridas
 * programadas ocurren solo con la aplicación abierta; lo atrasado corre una
 * vez al abrirla. */
export function ProgramacionPanel({ portal }: { portal: Portal }) {
  const qc = useQueryClient();
  const p = portal.programacion;
  const [frecuencia, setFrecuencia] = useState<Frecuencia>(p?.frecuencia ?? "semanal");
  const [diaSemana, setDiaSemana] = useState<number>(p?.diaSemana ?? 1);
  const [diaMes, setDiaMes] = useState<number>(p?.diaMes ?? 1);
  const [hora, setHora] = useState(p?.hora ?? "07:00");
  const refrescar = () => qc.invalidateQueries({ queryKey: ["boveda"] });
  const guardar = useMutation({
    mutationFn: () => programar(portal.idPortal, {
      frecuencia,
      diaSemana: frecuencia === "semanal" ? diaSemana : null,
      diaMes: frecuencia === "mensual" ? diaMes : null,
      hora,
    }),
    onSuccess: refrescar,
  });
  const correr = useMutation({ mutationFn: () => correrAhora(portal.idPortal), onSuccess: refrescar });

  if (!portal.conector.disponible) {
    if (portal.motivoNoSincroniza?.startsWith("No se puede automatizar")) {
      return <p className="text-sm text-ink-muted">{portal.motivoNoSincroniza}.</p>;
    }
    return <p className="text-sm text-ink-muted">La sincronización automática de esta cuenta va a estar disponible próximamente. Mientras tanto podés abrir el portal y entrar a mano.</p>;
  }

  return (
    <div className="space-y-3 text-sm">
      <p className="text-ink-secondary">
        {p?.suspendida ? (
          <span className="text-red-700">Suspendida: {p.motivoSuspension}</span>
        ) : p?.proximaCorrida ? (
          <>Próxima corrida: <strong>{formatFechaHora(p.proximaCorrida)}</strong> (con la aplicación abierta).</>
        ) : (
          "Sin corridas programadas."
        )}
      </p>
      <form className="flex flex-wrap items-end gap-2" onSubmit={(e) => { e.preventDefault(); guardar.mutate(); }}>
        <label className="text-xs">Frecuencia
          <select className={`${inputCls} block`} value={frecuencia} onChange={(e) => setFrecuencia(e.target.value as Frecuencia)}>
            <option value="desactivada">Desactivada</option>
            <option value="diaria">Diaria</option>
            <option value="semanal">Semanal</option>
            <option value="mensual">Mensual</option>
          </select>
        </label>
        {frecuencia === "semanal" && (
          <label className="text-xs">Día
            <select className={`${inputCls} block`} value={diaSemana} onChange={(e) => setDiaSemana(Number(e.target.value))}>
              {DIAS.map((d, i) => <option key={d} value={i + 1}>{d}</option>)}
            </select>
          </label>
        )}
        {frecuencia === "mensual" && (
          <label className="text-xs">Día del mes
            <select className={`${inputCls} block`} value={diaMes} onChange={(e) => setDiaMes(Number(e.target.value))}>
              {Array.from({ length: 28 }, (_, i) => <option key={i} value={i + 1}>{i + 1}</option>)}
            </select>
          </label>
        )}
        {frecuencia !== "desactivada" && (
          <label className="text-xs">Hora
            <input type="time" required className={`${inputCls} block`} value={hora} onChange={(e) => setHora(e.target.value)} />
          </label>
        )}
        <button type="submit" disabled={guardar.isPending} className="rounded-md bg-finance px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50">
          Guardar programación
        </button>
        <button type="button" disabled={correr.isPending || portal.enCurso || portal.enCola || !!portal.motivoNoSincroniza}
          title={portal.motivoNoSincroniza ?? undefined}
          onClick={() => correr.mutate()}
          className="rounded-md border border-border px-3 py-1.5 text-xs disabled:opacity-50">
          {portal.enCurso ? "Sincronizando…" : portal.enCola ? "En cola…" : "Sincronizar ahora"}
        </button>
      </form>
      <div className="rounded-md border border-border p-2"><EstadoSincronizacion portal={portal} /></div>
      {guardar.isError && <p className="text-xs text-red-700">{guardar.error.message}</p>}
      {correr.isError && <p className="text-xs text-red-700">{correr.error.message}</p>}
    </div>
  );
}
