"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";

import { Button } from "@/components/ui/Button";
import { SideDrawer } from "@/components/ui/SideDrawer";
import { formatFecha } from "@/lib/format";
import { apiGet, apiPost } from "@/services/apiClient";

export interface ProblemaControl { tipo: string; idCompra: number | null; documento: string; detalle: string }
export interface EstadoControl { fecha: string | null; controlando: boolean; problemas: ProblemaControl[]; error: string | null }

export function useControlCostos() {
  return useQuery({
    queryKey: ["imputacion-control"],
    queryFn: () => apiGet<EstadoControl>("/api/imputacion/control"),
    refetchInterval: (q) => (q.state.data?.controlando ? 10_000 : 5 * 60_000),
  });
}

/** Control de costos en panel lateral, agrupado por tipo y en ámbar: son tareas, no errores (auditoría 18/11/2026). */
export function ControlDrawer({ open, onClose }: { open: boolean; onClose: () => void }) {
  const qc = useQueryClient();
  const { data } = useControlCostos();
  const controlar = useMutation({
    mutationFn: () => apiPost<EstadoControl>("/api/imputacion/control/controlar", {}),
    onSuccess: (d) => qc.setQueryData(["imputacion-control"], d),
  });
  if (!open || !data) return null;
  const grupos = new Map<string, ProblemaControl[]>();
  data.problemas.forEach((p) => grupos.set(p.tipo, [...(grupos.get(p.tipo) ?? []), p]));
  const hora = data.fecha ? `${formatFecha(data.fecha)} ${data.fecha.slice(11, 16)} h` : null;
  return (
    <SideDrawer open onClose={onClose} maxWidthClass="max-w-2xl" title="Control de costos"
      subtitulo={hora ? `Último control: ${hora}` : "Controlando…"}>
      <div className="space-y-4 text-sm">
        <div className="flex items-center justify-between gap-3">
          <p className="text-ink-secondary">{data.problemas.length ? "Mientras esto no se resuelva, el costo de algún cultivo puede no ser exacto." : "Todo cierra."}</p>
          <Button size="sm" disabled={data.controlando || controlar.isPending} onClick={() => controlar.mutate()}>
            {data.controlando || controlar.isPending ? "Controlando…" : "Controlar ahora"}</Button>
        </div>
        {[...grupos].map(([tipo, ps]) => (
          <details key={tipo} open={grupos.size <= 2} className="rounded-md border border-status-warning/40 bg-status-warning-bg/40">
            <summary className="cursor-pointer px-3 py-2 font-medium text-ink-primary">{tipo} <span className="ml-1 rounded-full bg-status-warning px-1.5 text-[11px] font-semibold text-white">{ps.length}</span></summary>
            <ul className="divide-y divide-border border-t border-border bg-surface">
              {ps.map((p, i) => (
                <li key={i} className="space-y-0.5 px-3 py-2">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-medium">{p.documento}</span>
                    {p.idCompra && <Link className="text-xs font-medium text-finance hover:underline" href={`/compras/${p.idCompra}/editar`}>Abrir la compra</Link>}
                  </div>
                  <p className="text-xs text-ink-secondary">{p.detalle}</p>
                </li>
              ))}
            </ul>
          </details>
        ))}
      </div>
    </SideDrawer>
  );
}
