"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";

import { fetchCatalogosOrdenes } from "@/services/ordenesApi";
import { PlanificacionAgricolaListado } from "@/components/planificacion/PlanificacionAgricolaListado";
import { RemitosSubNav } from "@/components/remitos/RemitosSubNav";

export default function PlanificacionAgricolaPage() {
  const queryClient = useQueryClient();
  const { data: catalogos } = useQuery({ queryKey: ["ordenes", "catalogos"], queryFn: fetchCatalogosOrdenes });

  return (
    <main className="mx-auto max-w-none px-8 py-6">
      <h1 className="text-2xl font-semibold">Planificación agrícola</h1>
      <div className="mt-4">
        <RemitosSubNav />
      </div>
      <p className="mt-4 text-sm text-ink-secondary">
        Qué lote se destina a qué Cultivo/Campaña, según lo definido con los asesores. Las Órdenes de Trabajo usan esta
        planificación para sugerir los lotes de un Cultivo/Campaña.
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
