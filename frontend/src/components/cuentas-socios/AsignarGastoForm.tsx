"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { asignarGasto, fetchComprasParticularesCandidatas } from "@/services/cuentasSociosApi";
import { ApiError } from "@/services/apiClient";
import { SoloLectura } from "@/components/auth/SoloLectura";
import { filterInputClass } from "@/components/ui/FilterBar";
import { useToast } from "@/components/ui/Toast";
import { formatMoneda } from "@/lib/format";

/** Acción "Asignar a un socio…" (021 US1, T020): busca compras
 * "particulares" (research.md §3) sin asignación vigente y genera el
 * movimiento de deuda en la cuenta del socio elegido. El importe puede
 * ser el total de la compra (100% personal) o solo una parte (split
 * parcial, cuando queda un remanente real de deuda con el proveedor). */
export function AsignarGastoForm({ idSocio, onAsignado }: { idSocio: number; onAsignado: () => Promise<void> | void }) {
  const { showToast } = useToast();
  const [abierto, setAbierto] = useState(false);
  const [proveedor, setProveedor] = useState("");
  const [buscado, setBuscado] = useState("");
  const [motivo, setMotivo] = useState("");
  const [asignando, setAsignando] = useState<number | null>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["compras-particulares-candidatas", buscado],
    queryFn: () => fetchComprasParticularesCandidatas(buscado || undefined),
    enabled: abierto,
  });

  async function asignar(idCompra: number) {
    setAsignando(idCompra);
    try {
      await asignarGasto(idSocio, idCompra, motivo || undefined);
      showToast("Gasto asignado al socio.", "success");
      setAbierto(false);
      setMotivo("");
      await onAsignado();
    } catch (e) {
      showToast(e instanceof ApiError ? e.message : "Error al asignar el gasto.", "danger");
    } finally {
      setAsignando(null);
    }
  }

  return (
    <SoloLectura>
      <div className="relative">
        <button
          type="button"
          onClick={() => setAbierto((v) => !v)}
          className="rounded border border-border px-3 py-1.5 text-sm hover:bg-surface-sunken"
        >
          {abierto ? "Cancelar" : "Asignar a un socio…"}
        </button>

        {abierto && (
          <div className="absolute z-10 mt-2 w-[28rem] space-y-3 rounded-md border border-border bg-surface p-4 shadow-lg">
            <p className="text-sm text-ink-secondary">
              Compras particulares (gastos personales pagados por la empresa, total o parcial) sin asignar todavía.
            </p>
            <input
              className={filterInputClass}
              placeholder="Filtrar por proveedor…"
              value={proveedor}
              onChange={(e) => setProveedor(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") setBuscado(proveedor);
              }}
            />
            <input
              className={filterInputClass}
              placeholder="Motivo (opcional)"
              value={motivo}
              onChange={(e) => setMotivo(e.target.value)}
            />

            {isLoading && <p className="text-sm text-ink-secondary">Buscando…</p>}
            {isError && <p className="text-sm text-status-danger">Error al buscar compras.</p>}

            {data && data.compras.length === 0 && (
              <p className="text-sm text-ink-secondary">Sin compras particulares pendientes de asignar.</p>
            )}

            {data && data.compras.length > 0 && (
              <ul className="max-h-64 divide-y divide-border overflow-y-auto">
                {data.compras.map((c) => (
                  <li key={c.idCompra} className="flex items-center justify-between gap-2 py-2 text-sm">
                    <div>
                      <p className="font-medium">{c.proveedor ?? "—"}</p>
                      <p className="text-ink-secondary">
                        {c.fecha?.slice(0, 10)} · {c.numeroDocumento ?? "—"} · {formatMoneda(c.importePersonal)}
                      </p>
                    </div>
                    <button
                      type="button"
                      disabled={asignando === c.idCompra}
                      onClick={() => asignar(c.idCompra)}
                      className="shrink-0 rounded bg-finance px-2 py-1 text-xs text-white disabled:opacity-50"
                    >
                      {asignando === c.idCompra ? "…" : "Asignar"}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </SoloLectura>
  );
}
