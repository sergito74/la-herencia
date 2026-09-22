"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";

import { ConsolidadoCampaniaView } from "@/components/resultado-cultivo/ConsolidadoCampaniaView";
import { SelectorCampania } from "@/components/resultado-cultivo/SelectorCampania";
import { SelectorCultivo } from "@/components/resultado-cultivo/SelectorCultivo";
import { BackLink } from "@/components/ui/BackLink";
import { fetchCampanias, fetchResultadoCampania } from "@/services/resultadoCultivoApi";

export default function ResultadoCultivoPage() {
  const router = useRouter();
  const [campaniaElegida, setCampaniaElegida] = useState<number | null>(null);
  const campanias = useQuery({ queryKey: ["resultado-cultivo", "campanias"], queryFn: fetchCampanias });
  const idCampania = campaniaElegida ?? campanias.data?.campaniaActualId ?? null;
  const resultado = useQuery({
    staleTime: 0,
    refetchOnMount: "always",
    queryKey: ["resultado-cultivo", "campania", idCampania],
    queryFn: () => fetchResultadoCampania(idCampania!),
    enabled: idCampania !== null,
  });

  const cambiarCampania = (id: number) => {
    setCampaniaElegida(id);
  };

  return (
    <main className="mx-auto max-w-none px-8 py-6">
      <BackLink href="/produccion/ordenes">Volver a Producción</BackLink>
      <h1 className="mt-2 text-2xl font-semibold">Resultado de cultivo</h1>
      <p className="mt-1 text-ink-secondary">
        Costos, ventas y márgenes de cada campaña, con detalle por cultivo.
      </p>

      <div className="mt-6 flex flex-wrap items-end gap-4">
        <SelectorCampania
          campanias={campanias.data?.campanias ?? []}
          seleccionada={idCampania}
          cargando={campanias.isPending}
          onChange={cambiarCampania}
        />
        <SelectorCultivo
          cultivos={resultado.data?.cultivos ?? []}
          onChange={(idCultivo) => {
            if (idCampania !== null && idCultivo !== null) {
              router.push(`/produccion/resultado-cultivo/${idCampania}/${idCultivo}`);
            }
          }}
        />
      </div>

      <div className="mt-6">
        <ConsolidadoCampaniaView
          datos={resultado.data}
          cargando={campanias.isPending || resultado.isPending}
          error={campanias.isError || resultado.isError}
          onReintentar={() => (campanias.isError ? campanias.refetch() : resultado.refetch())}
          idCultivoSeleccionado={null}
        />
      </div>
    </main>
  );
}
