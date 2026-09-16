"use client";

import { useQuery } from "@tanstack/react-query";

import { fetchReferenciaOrigen, type Medio } from "@/services/tesoreriaApi";

/**
 * Renders the 3 explicit estados of the origin-reference heuristic
 * (FR-004, FR-005, SC-002): sin coincidencia / coincidencia única /
 * ambigua (with every candidate listed, never picking one by default).
 */
export function ReferenciaOrigen({ medio, idMovimiento }: { medio: Medio; idMovimiento: number }) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["tesoreria-referencia", medio, idMovimiento],
    queryFn: () => fetchReferenciaOrigen(medio, idMovimiento),
  });

  if (isLoading) return <span className="text-xs text-slate-500">Buscando referencia…</span>;
  if (isError) return <span className="text-xs text-red-700">Error al buscar referencia</span>;
  if (!data) return null;

  if (data.estado === "sin_coincidencia") {
    return <span className="text-xs italic text-slate-500">Sin coincidencia</span>;
  }

  if (data.estado === "coincidencia_unica") {
    const c = data.candidatas[0];
    return (
      <span className="text-xs text-emerald-700">
        Compra #{c.idCompra} ({c.numeroDocumento ?? "—"}) — {c.proveedor ?? "—"}
      </span>
    );
  }

  return (
    <div className="text-xs text-amber-700">
      <p className="font-semibold">Ambigua — {data.candidatas.length} candidatas:</p>
      <ul className="list-disc pl-4">
        {data.candidatas.map((c) => (
          <li key={c.idCompra}>
            Compra #{c.idCompra} ({c.numeroDocumento ?? "—"}) — {c.proveedor ?? "—"} —{" "}
            {c.fecha ?? "—"} — {c.importe ?? "—"}
          </li>
        ))}
      </ul>
    </div>
  );
}
