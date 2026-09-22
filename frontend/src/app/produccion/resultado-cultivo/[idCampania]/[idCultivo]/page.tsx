"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";

import { ResultadoCultivoView } from "@/components/resultado-cultivo/ResultadoCultivoView";
import { BackLink } from "@/components/ui/BackLink";
import { fetchDetalleCostos, fetchResultadoCultivo } from "@/services/resultadoCultivoApi";

export default function DetalleResultadoCultivoPage() {
  const params = useParams<{ idCampania: string; idCultivo: string }>();
  const idCampania = Number(params.idCampania);
  const idCultivo = Number(params.idCultivo);
  const parametrosValidos = Number.isInteger(idCampania) && Number.isInteger(idCultivo);
  const resultado = useQuery({
    staleTime: 0,
    refetchOnMount: "always",
    queryKey: ["resultado-cultivo", "cultivo", idCampania, idCultivo],
    queryFn: () => fetchResultadoCultivo(idCampania, idCultivo),
    enabled: parametrosValidos,
  });
  const costos = useQuery({
    staleTime: 0,
    refetchOnMount: "always",
    queryKey: ["resultado-cultivo", "costos", idCampania, idCultivo],
    queryFn: () => fetchDetalleCostos(idCampania, idCultivo),
    enabled: parametrosValidos,
  });

  return (
    <main className="mx-auto max-w-none px-8 py-6">
      <BackLink href="/produccion/resultado-cultivo">Volver al resultado de campaña</BackLink>
      <div className="mt-6">
        <ResultadoCultivoView
          datos={resultado.data}
          costos={costos.data}
          cargando={resultado.isPending || costos.isPending}
          error={!parametrosValidos || resultado.isError || costos.isError}
          onReintentar={() => {
            void resultado.refetch();
            void costos.refetch();
          }}
        />
      </div>
    </main>
  );
}
