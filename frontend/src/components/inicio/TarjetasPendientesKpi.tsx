"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { fetchPendientes } from "@/services/tarjetasResumenesApi";
import { KpiCard } from "@/components/ui/KpiCard";
import { formatCantidad } from "@/lib/format";

/**
 * Líneas de resumen de tarjeta pendientes de conciliar (009,
 * `/api/tarjetas-resumenes/pendientes`). Solo pide 1 fila (`pageSize: 1`) —
 * el indicador usa `total`, no `items`, así que no hace falta traer la
 * bandeja completa. Falla de forma aislada (FR-005).
 */
export function TarjetasPendientesKpi() {
  const { data, isError } = useQuery({
    queryKey: ["inicio-tarjetas-pendientes"],
    queryFn: () => fetchPendientes({ page: 1, pageSize: 1 }),
  });

  if (isError) return null;
  if (!data) return <KpiCard label="Líneas de tarjeta sin conciliar" value="…" />;

  return (
    <Link href="/finanzas/tarjetas/conciliacion">
      <KpiCard
        label="Líneas de tarjeta sin conciliar"
        value={formatCantidad(data.total)}
        tone={data.total > 0 ? "warning" : "success"}
      />
    </Link>
  );
}
