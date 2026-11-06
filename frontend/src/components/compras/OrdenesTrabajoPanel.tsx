"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { SoloLectura } from "@/components/auth/SoloLectura";
import { useToast } from "@/components/ui/Toast";
import { formatFecha, formatMonto, formatNumero } from "@/lib/format";
import { ApiError } from "@/services/apiClient";
import { fetchOrdenesTrabajoCompra, fijarOrdenesTrabajoCompra, type RepartoContratista } from "@/services/comprasApi";

export const ordenesTrabajoKey = (idCompra: number) => ["compras-ordenes-trabajo", idCompra];

/** 048: órdenes de trabajo que originó esta factura del contratista. Al guardar, el sistema reparte el costo por
 *  la superficie de las órdenes (cultivo/campaña) — no se imputa a mano. Las NC/ND siguen a su factura. */
export function OrdenesTrabajoPanel({ idCompra }: { idCompra: number }) {
  const qc = useQueryClient();
  const { showToast } = useToast();
  const { data } = useQuery({ queryKey: ordenesTrabajoKey(idCompra), queryFn: () => fetchOrdenesTrabajoCompra(idCompra) });
  const [tildadas, setTildadas] = useState<Set<number>>(new Set());

  useEffect(() => {
    if (data) setTildadas(new Set(data.ordenes.filter((o) => o.vinculada).map((o) => o.idOrden)));
  }, [data]);

  const guardar = useMutation({
    mutationFn: () => fijarOrdenesTrabajoCompra(idCompra, [...tildadas]),
    onSuccess: () => {
      showToast("Órdenes de trabajo guardadas: el costo quedó imputado a sus cultivos.", "success");
      qc.invalidateQueries({ queryKey: ordenesTrabajoKey(idCompra) });
      qc.invalidateQueries({ queryKey: ["ordenes"] });
      qc.invalidateQueries({ queryKey: ["resultado-cultivo"] });
    },
    onError: (e) => showToast(e instanceof ApiError ? e.message : "No se pudieron guardar las órdenes.", "danger"),
  });

  if (!data || !data.esContratista) return null;
  if (data.esNotaCreditoDebito) {
    return (
      <section className="mt-3 rounded border border-border p-3 text-sm text-ink-secondary">
        <h3 className="font-medium text-ink">Órdenes de trabajo</h3>
        Se imputa igual que su factura: relacionala en Documentos relacionados.
        <Reparto filas={data.reparto} />
      </section>
    );
  }
  if (!data.esDocumentoDeLabor) return null;

  const cambio =
    data.ordenes.some((o) => o.vinculada !== tildadas.has(o.idOrden));

  return (
    <section className="mt-3 rounded border border-border p-3">
      <h3 className="text-sm font-medium">Órdenes de trabajo de esta factura</h3>
      {data.ordenes.length === 0 ? (
        <p className="mt-1 text-sm text-ink-secondary">Este contratista no tiene órdenes ejecutadas.</p>
      ) : (
        <ul className="mt-2 max-h-56 space-y-1 overflow-y-auto text-sm">
          {data.ordenes.map((o) => (
            <li key={o.idOrden}>
              <label className="flex items-start gap-2">
                <input
                  type="checkbox"
                  className="mt-1"
                  checked={tildadas.has(o.idOrden)}
                  onChange={(e) => {
                    const s = new Set(tildadas);
                    if (e.target.checked) s.add(o.idOrden);
                    else s.delete(o.idOrden);
                    setTildadas(s);
                  }}
                />
                <span>
                  {formatFecha(o.fecha)} · {o.labor ?? "Labor"} · {formatNumero(o.hectareas, { max: 1 })} ha
                  {o.lotes ? <span className="text-ink-secondary"> · Lotes {o.lotes}</span> : null}
                  {o.tieneOtraFactura && !o.vinculada ? (
                    <span className="ml-1 text-xs text-ink-secondary">(ya tiene otra factura)</span>
                  ) : null}
                </span>
              </label>
            </li>
          ))}
        </ul>
      )}
      <SoloLectura>
        <button
          type="button"
          onClick={() => guardar.mutate()}
          disabled={!cambio || guardar.isPending}
          className="mt-2 rounded bg-finance px-3 py-1.5 text-sm text-white disabled:opacity-50"
        >
          Guardar órdenes
        </button>
      </SoloLectura>
      <Reparto filas={data.reparto} />
    </section>
  );
}

function Reparto({ filas }: { filas: RepartoContratista[] }) {
  if (filas.length === 0) return null;
  return (
    <div className="mt-3 text-sm">
      <p className="font-medium">Costo imputado</p>
      <table className="mt-1 w-full">
        <tbody>
          {filas.map((f, i) => (
            <tr key={i} className="border-t border-border">
              <td className="py-1">{f.cultivo ?? "Sin cultivo"} {f.campania ?? ""}</td>
              <td className="py-1 text-ink-secondary">{f.lote ? `Lote ${f.lote}` : ""}</td>
              <td className="py-1 text-right">$ {formatMonto(f.importe)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
