"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { anularRecuento, fetchRecuentos } from "@/services/remitosApi";
import { ApiError } from "@/services/apiClient";
import { filterInputClass } from "@/components/ui/FilterBar";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { useToast } from "@/components/ui/Toast";

const aFecha = (v: string) => String(v).slice(0, 10).split("-").reverse().join("/");

/** Recuentos físicos grabados. Anular uno deshace sus ajustes en las órdenes y sus faltantes/sobrantes sin imputar. */
export function RecuentosListado({ onAnulado }: { onAnulado: () => void }) {
  const { showToast } = useToast();
  const { data, refetch } = useQuery({ queryKey: ["recuentos"], queryFn: fetchRecuentos, staleTime: 0 });
  const [anulando, setAnulando] = useState<number | null>(null);
  const [motivo, setMotivo] = useState("");

  async function anular(id: number) {
    try {
      await anularRecuento(id, motivo);
      showToast("Recuento anulado: se deshicieron sus ajustes.", "success");
      setAnulando(null);
      setMotivo("");
      refetch();
      onAnulado();
    } catch (e) {
      showToast(e instanceof ApiError ? e.message : "No se pudo anular el recuento.", "danger");
    }
  }

  if (!data?.length) return null;
  return (
    <div className="space-y-2">
      <h2 className="text-sm font-medium">Recuentos físicos</h2>
      <div className="overflow-x-auto rounded-md border border-border">
        <table className="min-w-full divide-y divide-border text-xs">
          <thead className="bg-surface-sunken text-left">
            <tr>
              {["Fecha", "Motivo", "Productos contados", "Con diferencia", "Ajustes en órdenes", "Sin imputar", ""].map((h) => (
                <th key={h} className="whitespace-nowrap px-1.5 py-1 font-medium text-ink-secondary">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {data.map((r) => (
              <tr key={r.idRecuento}>
                <td className="px-1.5 py-1 font-data">{aFecha(r.fecha)}</td>
                <td className="px-1.5 py-1">
                  {r.motivo}
                  {r.anulado && (
                    <span className="ml-1" title={r.motivoAnulacion ?? undefined}>
                      <StatusBadge label="Anulado" tone="danger" />
                    </span>
                  )}
                </td>
                <td className="px-1.5 py-1 text-right font-data">{r.productos}</td>
                <td className="px-1.5 py-1 text-right font-data">{r.conDiferencia}</td>
                <td className="px-1.5 py-1 text-right font-data">{r.ajustesOrden}</td>
                <td className="px-1.5 py-1 text-right font-data">{r.sinImputar}</td>
                <td className="px-1.5 py-1">
                  {r.anulado ? null : anulando === r.idRecuento ? (
                    <span className="flex items-center gap-1">
                      <input className={`${filterInputClass} w-36 px-1 py-0.5 text-xs`} placeholder="Motivo" value={motivo} onChange={(e) => setMotivo(e.target.value)} />
                      <button type="button" disabled={!motivo.trim()} className="text-xs text-status-danger underline disabled:opacity-40" onClick={() => anular(r.idRecuento)}>
                        OK
                      </button>
                      <button type="button" className="text-xs text-ink-secondary" onClick={() => setAnulando(null)}>
                        ✕
                      </button>
                    </span>
                  ) : (
                    <button type="button" className="text-xs text-ink-secondary underline hover:text-status-danger" onClick={() => setAnulando(r.idRecuento)}>
                      Anular
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
