"use client";

import { PageHeader } from "@/components/ui/PageHeader";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { fetchCatalogosOrdenes } from "@/services/ordenesApi";
import { PlanificacionAgricolaListado } from "@/components/planificacion/PlanificacionAgricolaListado";

export default function PlanificacionAgricolaPage() {
  const queryClient = useQueryClient();
  const { data: catalogos } = useQuery({ queryKey: ["ordenes", "catalogos"], queryFn: fetchCatalogosOrdenes });

  return (
    <main className="mx-auto max-w-none px-6 py-3">
      <PageHeader titulo="Planificación agrícola" ayuda="Qué cultivo va en cada lote, campaña por campaña. Las órdenes de trabajo la usan para sugerir los lotes." />
      <div>
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
