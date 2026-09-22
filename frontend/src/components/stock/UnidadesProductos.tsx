"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { confirmarUnidades, fetchProductosPorConfirmar, fetchUnidades, setUnidadBase } from "@/services/remitosApi";
import { ApiError } from "@/services/apiClient";
import { filterInputClass } from "@/components/ui/FilterBar";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { useToast } from "@/components/ui/Toast";

/**
 * Revisión de la unidad base de cada producto. Se propuso a partir del uso histórico en
 * remitos (litros / kilos); acá se corrige o se confirma. El stock de un producto se lleva
 * siempre en su unidad base.
 */
export function UnidadesProductos() {
  const qc = useQueryClient();
  const { showToast } = useToast();
  const { data, isLoading, isError, refetch } = useQuery({ queryKey: ["productos-por-confirmar"], queryFn: fetchProductosPorConfirmar, staleTime: 0 });
  const { data: unidades } = useQuery({ queryKey: ["unidades"], queryFn: fetchUnidades, staleTime: Infinity });
  const [elegidos, setElegidos] = useState<number[]>([]);
  const bases = (unidades ?? []).filter((u) => u.esBase);

  function refrescar() {
    qc.invalidateQueries({ queryKey: ["productos-por-confirmar"] });
    qc.invalidateQueries({ queryKey: ["existencias"] });
  }

  async function cambiar(id: number, unidad: string) {
    try {
      await setUnidadBase(id, unidad);
      showToast("Unidad base confirmada.", "success");
      refrescar();
    } catch (e) {
      showToast(e instanceof ApiError ? e.message : "No se pudo cambiar la unidad.", "danger");
    }
  }

  async function confirmar(ids: number[]) {
    try {
      const r = await confirmarUnidades(ids);
      showToast(`${r.confirmadas} unidades confirmadas.`, "success");
      setElegidos([]);
      refrescar();
    } catch (e) {
      showToast(e instanceof ApiError ? e.message : "No se pudo confirmar.", "danger");
    }
  }

  if (isLoading) return <LoadingState />;
  if (isError || !data) return <ErrorState message="No se pudieron cargar los productos." onRetry={() => refetch()} />;
  if (data.length === 0) return <EmptyState message="Todas las unidades base están confirmadas." />;

  return (
    <div className="space-y-3">
      <p className="text-sm text-ink-secondary">
        {data.length} productos con la unidad base propuesta según su uso histórico. Cambiar la unidad la confirma; «Confirmar» acepta la propuesta tal cual. Las que se
        infirieron por tipo (porque solo se remitaron en bolsas o packs) conviene revisarlas.
      </p>
      <div className="flex gap-2">
        <button type="button" disabled={elegidos.length === 0} onClick={() => confirmar(elegidos)} className="rounded-sm bg-finance px-4 py-2 text-sm text-white hover:opacity-90 disabled:opacity-40">
          Confirmar seleccionados ({elegidos.length})
        </button>
        <button type="button" onClick={() => confirmar(data.filter((p) => !p.origen?.startsWith("inferida")).map((p) => p.idProducto))} className="rounded-sm border border-finance px-4 py-2 text-sm text-finance hover:bg-finance-light">
          Confirmar todas las de uso histórico
        </button>
      </div>
      <table className="w-full text-sm">
        <thead className="text-left text-xs text-ink-secondary">
          <tr>
            <th className="w-8" />
            <th className="py-1 pr-2">Producto</th>
            <th className="pr-2">Tipo</th>
            <th className="pr-2 text-right">Renglones</th>
            <th className="pr-2">Unidad base</th>
            <th>Origen de la propuesta</th>
          </tr>
        </thead>
        <tbody>
          {data.map((p) => (
            <tr key={p.idProducto} className="border-t border-border">
              <td className="py-1">
                <input type="checkbox" checked={elegidos.includes(p.idProducto)} onChange={() => setElegidos((prev) => (prev.includes(p.idProducto) ? prev.filter((x) => x !== p.idProducto) : [...prev, p.idProducto]))} aria-label={`Elegir ${p.producto}`} />
              </td>
              <td className="pr-2">{p.producto}</td>
              <td className="pr-2 text-ink-secondary">{p.tipo}</td>
              <td className="pr-2 text-right font-data">{p.renglones}</td>
              <td className="pr-2">
                <select className={`${filterInputClass} px-1.5 py-0.5 text-xs`} value={p.unidadBase} onChange={(e) => cambiar(p.idProducto, e.target.value)}>
                  {bases.map((u) => (
                    <option key={u.codigo} value={u.codigo}>
                      {u.codigo}
                    </option>
                  ))}
                </select>
              </td>
              <td className={`text-xs ${p.origen?.startsWith("inferida") ? "text-status-warning" : "text-ink-secondary"}`}>{p.origen}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
