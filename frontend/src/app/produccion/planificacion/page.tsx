"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";

import { fetchCatalogosOrdenes } from "@/services/ordenesApi";
import { PlanificacionAgricolaListado } from "@/components/planificacion/PlanificacionAgricolaListado";
import { BackLink } from "@/components/ui/BackLink";

export default function PlanificacionAgricolaPage() {
  const queryClient = useQueryClient();
  const { data: catalogos } = useQuery({ queryKey: ["ordenes", "catalogos"], queryFn: fetchCatalogosOrdenes });

  return (
    <main className="mx-auto max-w-none px-8 py-6">
      <BackLink href="/">Volver al inicio</BackLink>
      <h1 className="mt-2 text-2xl font-semibold">Planificación agrícola</h1>
      <p className="mt-4 text-sm text-ink-secondary">
        Qué cultivo va en cada lote, campaña por campaña. Las órdenes de trabajo la usan para sugerir los lotes.
      </p>
      <div className="mt-4">
        {catalogos ? (
          <PlanificacionAgricolaListado
            items={catalogos.planAgricola}
            lotes={catalogos.lotes}
            cultivos={catalogos.cultivos}
            campanias={catalogos.campanias}
            onCambio={() => queryClient.invalidateQueries({ queryKey: ["ordenes", "catalogos"] })}
          />
        ) : (
          <p className="text-ink-secondary">Cargando…</p>
        )}
      </div>
    </main>
  );
}
