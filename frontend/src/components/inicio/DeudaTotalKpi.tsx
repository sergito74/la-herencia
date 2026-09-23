"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { fetchSaldos } from "@/services/cuentasCorrientesApi";
import { KpiCard } from "@/components/ui/KpiCard";
import { formatMoneda } from "@/lib/format";

/**
 * Deuda total a proveedores: suma de los saldos negativos del listado
 * agregado de 014 (`/api/cuentas-corrientes/saldos`). No suma los saldos a
 * favor — eso no es "deuda" (FR-001). Falla de forma aislada: si el fetch
 * no resuelve, este componente simplemente no renderiza nada, sin afectar
 * al resto de la pantalla de inicio (FR-005).
 */
export function DeudaTotalKpi() {
  const { data, isError } = useQuery({
    queryKey: ["inicio-deuda-total"],
    queryFn: () => fetchSaldos("saldo"),
  });

  if (isError) return null;
  if (!data) return <KpiCard label="Deuda total a proveedores" value="…" />;

  const deudaTotal = data.items
    .filter((s) => s.saldoParcial != null && s.saldoParcial < 0)
    .reduce((acc, s) => acc + (s.saldoParcial ?? 0), 0);

  return (
    <Link href="/finanzas/cuentas-corrientes/saldos">
      <KpiCard
        label="Deuda total a proveedores"
        value={formatMoneda(deudaTotal)}
        tone={deudaTotal < 0 ? "danger" : "success"}
      />
    </Link>
  );
}
