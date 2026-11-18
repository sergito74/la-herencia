"use client";

import { PageHeader } from "@/components/ui/PageHeader";

import { retornoResumenes } from "@/lib/tarjetasNavigation";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";

import { fetchResumenDetalle } from "@/services/tarjetasResumenesApi";
import { ResumenForm } from "@/components/tarjetas-resumenes/ResumenForm";
import { ErrorState, LoadingState } from "@/components/ui/States";

export default function EditarResumenPage() {
  const params = useParams<{ idResumen: string }>();
  const idResumen = Number(params.idResumen);
  const router = useRouter();
  const returnParam = useSearchParams().get("returnTo");
  const retorno = retornoResumenes(returnParam);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["tarjeta-resumen-detalle-edicion", idResumen],
    queryFn: () => fetchResumenDetalle(idResumen),
  });

  return (
    <main className="mx-auto max-w-none px-6 py-3">
      <PageHeader titulo={<>Editar resumen</>} onVolver={() => returnParam ? router.push(retorno) : router.back()} />

      {isLoading && <LoadingState />}
      {isError && <ErrorState message="Ocurrió un error al cargar el resumen." onRetry={() => refetch()} />}

      {data && (
        <div className="mt-2">
          <ResumenForm mode="edicion" idResumen={idResumen} initial={data} />
        </div>
      )}
    </main>
  );
}
