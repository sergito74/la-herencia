"use client";

import { useQuery } from "@tanstack/react-query";

import { fetchReferenciaOrigen, type Medio } from "@/services/tesoreriaApi";
import { StatusBadge } from "@/components/ui/StatusBadge";

/**
 * Renders the 3 explicit estados of the origin-reference heuristic
 * (FR-004, FR-005, SC-002): sin coincidencia / coincidencia única /
 * ambigua (with every candidate listed, never picking one by default).
 * Estados con `StatusBadge` (design/agroux-frontend-redesign.md §4.2):
 * sin_coincidencia→neutral, coincidencia_unica→success, ambigua→warning.
 */
export function ReferenciaOrigen({ medio, idMovimiento }: { medio: Medio; idMovimiento: number }) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["tesoreria-referencia", medio, idMovimiento],
    queryFn: () => fetchReferenciaOrigen(medio, idMovimiento),
  });

  if (isLoading) return <span className="text-xs text-ink-secondary">Buscando referencia…</span>;
  if (isError) return <span className="text-xs text-status-danger">Error al buscar referencia</span>;
  if (!data) return null;

  if (data.estado === "sin_coincidencia") {
    return <StatusBadge label="Sin coincidencia" tone="neutral" />;
  }

  if (data.estado === "coincidencia_unica") {
    const c = data.candidatas[0];
    return (
      <div className="space-y-1">
        <StatusBadge label="Coincidencia única" tone="success" />
        <p className="text-xs text-ink-secondary">
          Compra #{c.idCompra} ({c.numeroDocumento ?? "—"}) — {c.proveedor ?? "—"}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-1">
      <StatusBadge label={`Ambigua — ${data.candidatas.length} candidatas`} tone="warning" />
      <ul className="list-disc pl-4 text-xs text-ink-secondary">
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
