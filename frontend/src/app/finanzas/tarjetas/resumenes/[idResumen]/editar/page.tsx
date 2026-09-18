"use client";

import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";

import { fetchResumenDetalle } from "@/services/tarjetasResumenesApi";
import { ResumenForm } from "@/components/tarjetas-resumenes/ResumenForm";
import { ErrorState, LoadingState } from "@/components/ui/States";

export default function EditarResumenPage() {
  const params = useParams<{ idResumen: string }>();
  const idResumen = Number(params.idResumen);
  const router = useRouter();

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["tarjeta-resumen-detalle-edicion", idResumen],
    queryFn: () => fetchResumenDetalle(idResumen),
  });

  return (
    <main className="mx-auto max-w-none px-8 py-3">
      <button type="button" onClick={() => router.back()} className="text-sm text-finance underline">
        ← Volver a Resúmenes
      </button>
      <h1 className="mt-1 text-base font-semibold">Editar resumen</h1>

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
